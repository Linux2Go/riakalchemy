"""
    RiakAlchemy - Object Mapper for Riak

    Copyright (C) 2011  Linux2Go

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 as
    published by the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Where all the magic happens
"""
import json
import riak
import riak.client
from riak.mapreduce import RiakLink

from riakalchemy.exceptions import ValidationError, NoSuchObjectError
from riakalchemy.types import RiakType


class RiakModelRegistry(object):
    def __init__(self):
        self._registry = []

    def register_model(self, cls):
        if cls.__name__ == 'RiakObject':
            return
        self._registry += [cls]

    def class_by_bucket_name(self, bucket_name):
        for model in self._registry:
            if model.bucket_name == bucket_name:
                return model

_registry = RiakModelRegistry()


class RiakObjectMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(RiakObjectMeta, cls).__new__
        meta = {}
        keys = []
        for key in attrs:
            if isinstance(attrs[key], RiakType):
                keys += [key]

        for key in keys:
            meta[key] = attrs.pop(key)

        attrs['_meta'] = meta
        new_class = super_new(cls, name, bases, attrs)
        _registry.register_model(new_class)
        return new_class


class RiakObject(object):
    __metaclass__ = RiakObjectMeta
    searchable = False
    debug = False

    def __init__(self, **kwargs):
        self._links = []
        self.key = None
        self.update(kwargs)
        self._riak_obj = None

    def __cmp__(self, other):
        if type(self) != type(other):
            return False
        return self.key == other.key

    @classmethod
    def load(cls, riak_obj):
        obj = cls(**riak_obj.data)
        obj.key = riak_obj.key
        obj._links = riak_obj.links
        obj._riak_obj = riak_obj
        return obj

    def __getattr__(self, key):
        if key in self._meta and self._meta[key].link_type:
            retval = []
            links = self._riak_obj.links
            for link in links:
                if link[2] == key:
                    cls = _registry.class_by_bucket_name(link[0])
                    retval += [cls.load(client.bucket(link[0]).get(link[1]))]
            setattr(self, key, retval)
            return retval

        raise AttributeError('No such key: %s' % (key,))

    def json(self):
        return json.dumps(dict((k, getattr(self, k)) for k in self._meta))

    def update(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)

    def clean(self):
        for field in self._meta:
            if self._meta[field].required and not hasattr(self, field):
                raise ValidationError('"%s" is required, but not set' %
                                      (field,))

            if self._meta[field].link_type:
                value = getattr(self, field, [])
                for rel in value:
                    if not isinstance(rel, RiakObject):
                        raise ValidationError('%s attribute of %s must be '
                                              'another RiakObject' %
                                              (field, self.__class__.__name__))

                for link in self._links:
                    if link.tag == field:
                        self._riak_obj.links.remove(link)
                        self._links.remove(link)

                for link in value:
                    self._links += [RiakLink(link.bucket_name,
                                             link.key, tag=field)]
            else:
                if hasattr(self, field):
                    value = self._meta[field].clean(getattr(self, field))
                    setattr(self, field, value)

            if hasattr(self, field):
                self._meta[field].validate(getattr(self, field))

    @classmethod
    def get(cls, key=None, **kwargs):
        if key:
            bucket = client.bucket(cls.bucket_name)
            obj = bucket.get(key)
            if not obj.exists:
                raise NoSuchObjectError()
            return cls.load(obj)

        if len(kwargs) == 1:
            field = kwargs.keys()[0]
            if cls._meta[field].link_type and cls._meta[field].backref:
                bucket = client.bucket(cls.bucket_name)
                _2i_key = '%s_bin' % (field,)
                _2i_value = ('%s/%s' % (kwargs[field].bucket_name,
                                        kwargs[field].key))
                index_query = client.index(cls.bucket_name,
                                           _2i_key, _2i_value)
                return RiakObjectQuery(index_query, cls, True)
        elif cls.searchable and kwargs:
            return cls.get_search(**kwargs)
        else:
            return cls.get_mr(**kwargs)

    @classmethod
    def get_search(cls, **kwargs):
        terms = ' AND '.join(['%s:"%s"' % (k, v)
                                               for k, v in kwargs.iteritems()])
        query = client.search(cls.bucket_name, terms)
        return RiakObjectQuery(query, cls, True)

    @classmethod
    def get_mr(cls, **kwargs):
        query = client.add(cls.bucket_name)
        terms = (' && '.join(['data'] +
                 ['data.%s=="%s"' % (k, v) for k, v in kwargs.iteritems()]))
        map_func = """function(v) {
                          json_string = v.values[0].data;
                          if (json_string == '') return [];
                          var data = JSON.parse(json_string);
                          if(%s) {
                              return [v.key];
                          }
                          return [];
                      }""" % (terms,)
        query.map(map_func)
        return RiakObjectQuery(query, cls, False)

    def pre_delete(self):
        pass

    def post_delete(self):
        pass

    def delete(self):
        if self._riak_obj:
            self.pre_delete()
            self._riak_obj.delete()
            self.post_delete()

    def post_save(self):
        pass

    def pre_save(self):
        pass

    def save(self):
        self.pre_save()
        self.clean()
        bucket = client.bucket(self.bucket_name)

        # Ideally, this should live in the metaclass, but since we don't
        # have a connection there yet..
        if self.searchable:
            bucket.enable_search()

        data_dict = dict((k, getattr(self, k)) for k in self._meta
                                                if not self._meta[k].link_type
                                                   and hasattr(self, k))
        if self._riak_obj:
            self._riak_obj.data = data_dict
        else:
            self._riak_obj = bucket.new(self.key, data=data_dict)

        # Remove all existing links and indexes
        self._riak_obj.links = []

        indexes = self._riak_obj.indexes
        for idx in list(indexes):
            self._riak_obj.remove_index(*idx)

        # ..and add the new set of links
        self._riak_obj.links = self._links

        for field in self._meta:
            if self._meta[field].link_type and self._meta[field].backref:
                value = getattr(self, field)
                for link in value:
                    self._riak_obj.add_index('%s_bin' % (field,),
                                             '%s/%s' % (link.bucket_name,
                                                        link.key))

        self._riak_obj.store()
        self.key = self._riak_obj.key
        self.post_save()


class RiakObjectQuery(object):
    def __init__(self, query, cls, gives_links):
        self.query = query
        self.cls = cls
        self.gives_links = gives_links

    def all(self):
        bucket = client.bucket(self.cls.bucket_name)
        if self.gives_links:
            unwrap = lambda x: bucket.get(x[1])
        else:
            unwrap = lambda x: bucket.get(x)
        return [self.cls.load(unwrap(x)) for x in self.query.run()]

client = None
_test_server = None


def reset_registry():
    global _registry
    _registry = RiakModelRegistry()


def connect(host='127.0.0.1', port=8098, test_server=False):
    global client
    if test_server:
        global _test_server
        if _test_server:
            _test_server.cleanup()
            _test_server.stop()
        from riak.test_server import TestServer, Atom
        import tempfile
        tmpdir = tempfile.mkdtemp()
        _test_server = TestServer(bin_dir="/usr/sbin",
                                  tmp_dir=tmpdir,
                                  riak_core={"web_port": port, 'handoff_port': port + 1},
                                  riak_kv={'pb_port': port + 2,
                                           'delete_mode': Atom('immediate')})
        _test_server.cleanup()
        _test_server.prepare()
        _test_server.start()

    client = riak.RiakClient(host=host, http_port=port)


def _clear_test_connection():
    global _test_server
    _test_server.recycle()
