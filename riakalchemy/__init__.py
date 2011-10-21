__version__ = '0.1a'

import json
from riakalchemy.exceptions import ValidationError
from riakalchemy.types import RiakType
import riak
from riak.mapreduce import RiakLink

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

    def __init__(self, **kwargs):
        self.update(kwargs)
        self._riak_obj = None
        self.key = None

    @classmethod
    def load(cls, riak_obj):
        obj = cls(**riak_obj.get_data())
        obj.key = riak_obj.get_key()
        obj._riak_obj = riak_obj
        return obj

    def __getattr__(self, key):
        if key in self._meta and self._meta[key].link_type:
            retval = []
            links = self._riak_obj.get_links()
            for link in links:
                if link.get_tag() == key:
                    cls = _registry.class_by_bucket_name(link.get_bucket())
                    retval += [cls.load(link.get())]
            return retval

        raise AttributeError('No such key: %s' % (key,))

    def json(self):
        return json.dumps(dict((k, getattr(self, k)) for k in self._meta))

    def update(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)

    def clean(self):
        if self._riak_obj:
            links = self._riak_obj.get_links()
        else:
            links = []

        for field in self._meta:
            if self._meta[field].required and not hasattr(self, field):
                raise ValidationError('"%s" is required, but not set' %
                                      (field,))
            if self._meta[field].link_type:
                value = getattr(self, field, [])
                for rel in value:
                    if not isinstance(rel, RiakObject):
                        raise ValidationError('%s attribute of %s must be another '
                                              'RiakObject' %
                                              (field, self.__class__.__name__))
                for link in links:
                    if link.get_tag() == field:
                        self._riak_obj.remove_link(link)

                for link in value:
                    links += [RiakLink(link.bucket_name, link.key, tag=field)]
            else:
                setattr(self, field, self._meta[field].clean(getattr(self, field)))

            if hasattr(self, field):
                self._meta[field].validate(getattr(self, field))
        self._links = links

    @classmethod
    def get(cls, key=None, **kwargs):
        if key:
            bucket = client.bucket(cls.bucket_name)
            obj = bucket.get(key)
            return cls.load(obj)

        if cls.searchable:
            return cls.get_search(**kwargs)
        else:
            return cls.get_mr(**kwargs)

    @classmethod
    def get_search(cls, **kwargs):
        terms = ' AND '.join(['%s:"%s"' % (k,v) for k,v in kwargs.iteritems()])
        query = client.search(cls.bucket_name, terms)
        return RiakObjectQuery(query, cls, True)

    @classmethod
    def get_mr(cls, **kwargs):
        query = client.add(cls.bucket_name)
        terms = ' && '.join(['true'] + ['data.%s=="%s"' % (k,v) for k,v in kwargs.iteritems()])
        map_func = """function(v) {
                          var data = JSON.parse(v.values[0].data);
                          if(%s) {
                              return [v.key];
                          }
                          return [];
                      }""" % (terms,)

        print map_func
        query.map(map_func)
        return RiakObjectQuery(query, cls, False)

    def save(self):
        self.clean()
        bucket = client.bucket(self.bucket_name)

        # Ideally, this should live in the metaclass, but since we don't
        # have a connection there yet..
        if self.searchable:
            bucket.enable_search()

        data_dict = dict((k, getattr(self, k)) for k in self._meta
                                                if not self._meta[k].link_type)
        if self._riak_obj:
            self._riak_obj.set_data(data_dict)
        else:
            self._riak_obj = bucket.new(self.key, data=data_dict)

        # Remove all existing links
        for l in self._riak_obj.get_links():
            self._riak_obj.remove_link(l)

        # ..and add the new set of links
        for l in self._links:
            self._riak_obj.add_link(l)

        self._riak_obj.store()
        self.key = self._riak_obj.get_key()

class RiakObjectQuery(object):
    def __init__(self, query, cls, gives_links):
        self.query = query
        self.cls = cls
        self.gives_links = gives_links

    def all(self):
        if self.gives_links:
            unwrap = lambda x: x.get()
        else:
            bucket = client.bucket(self.cls.bucket_name)
            unwrap = lambda x: bucket.get(x)
        return [self.cls.load(unwrap(x)) for x in self.query.run()]

client = None
_test_server = None

def connect(host='127.0.0.1', port=8098, test_server=False):
    global client
    if test_server:
        global _test_server
        from riak.test_server import TestServer
        import tempfile
        tmpdir = tempfile.mkdtemp()
        _test_server = TestServer(bin_dir="/usr/sbin",
                                  tmp_dir=tmpdir,
                                  riak_core={"web_port": port})
        _test_server.cleanup()
        _test_server.prepare()
        _test_server.start()

    client = riak.RiakClient(host=host, port=port)

def _clear_test_connection():
    global _test_server
    _test_server.recycle()
