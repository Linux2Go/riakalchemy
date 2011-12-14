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

    The various data types RiakAlchemy understands
"""
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
