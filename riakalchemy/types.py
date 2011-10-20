class RiakType(object):
    def __init__(self, required=False):
        self.required = required

    def clean(self, value):
        return value

    def validate(self, value):
        return True

class String(RiakType):
    pass

class Integer(RiakType):
    def clean(self, value):
        return int(value)
