from riakalchemy.exceptions import ValidationError

class RiakType(object):
    link_type = False

    def __init__(self, required=False):
        self.required = required

    def clean(self, value):
        return value

    def validate(self, value):
        return True

class Dict(RiakType):
    pass

class String(RiakType):
    pass

class Integer(RiakType):
    def clean(self, value):
        try:
            return int(value)
        except ValueError:
            raise ValidationError("%r could not be cast to integer" % (value,))

class RelatedObjects(RiakType):
    link_type = True
    def __init__(self, backref=False, **kwargs):
        super(RelatedObjects, self).__init__(**kwargs)
        self.backref = backref
