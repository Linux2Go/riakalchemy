__version__ = '0.1a'

from riakalchemy.exceptions import ValidationError
from riakalchemy.types import RiakType
import riak

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
        return new_class

class RiakObject(object):
    __metaclass__ = RiakObjectMeta
    searchable = False

    def __init__(self, **kwargs):
        self.update(kwargs)

    @classmethod
    def load(cls, riak_obj):
        key, dict = riak_obj
        obj = cls(**dict)
        return obj

    def update(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)

    def clean(self):
        for field in self._meta:
            if self._meta[field].required and not hasattr(self, field):
                raise ValidationError('"%s" is required, but not set' %
                                      (field,))

            setattr(self, field, self._meta[field].clean(getattr(self, field)))
            self._meta[field].validate(getattr(self, field))

    @classmethod
    def get(cls, key=None, **kwargs):
        if key:
            bucket = client.bucket(cls.bucket_name)
            obj = bucket.get(key)
            return cls.load((key, obj.get_data()))

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
        terms = ' && '.join(['data.%s=="%s"' % (k,v) for k,v in kwargs.iteritems()])
        map_func = """function(v) {
                          var data = JSON.parse(v.values[0].data);
                          if(%s) {
                              return [[v.key, data]];
                          }
                          return [['foo','bar']];
                      }""" % (terms,)

        query.map(map_func)
        return RiakObjectQuery(query, cls, False)

    def save(self):
        self.clean()
        bucket = client.bucket(self.bucket_name)
        if self.searchable:
            bucket.enable_search()
        obj = bucket.new(None, data=dict((k, getattr(self, k)) for k in self._meta))
        obj.store()
        self.key = obj.get_key()

class RiakObjectQuery(object):
    def __init__(self, query, cls, gives_links):
        self.query = query
        self.cls = cls
        self.gives_links = gives_links

    def all(self):
        if self.gives_links:
            unwrap = lambda x: (x.get_key(), x.get().get_data())
        else:
            unwrap = lambda x: (x)
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
