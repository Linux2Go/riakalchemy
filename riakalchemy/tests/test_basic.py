import unittest

import riakalchemy
from riakalchemy import RiakObject
from riakalchemy.exceptions import ValidationError
from riakalchemy.types import String, Integer, RelatedObjects

class BasicTests(unittest.TestCase):
    test_server_started = False

    def setUp(self):
        if not self.__class__.test_server_started:
            riakalchemy.connect(test_server=True, port=10229)
            self.__class__.test_server_started = True
        else:
            riakalchemy._clear_test_connection()

    def test_create_object(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()

        user = Person(first_name='soren', last_name='hansen')
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')

    def test_integer_clean(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person(first_name='soren', last_name='hansen', age='32')
        self.assertEquals(user.age, '32')
        user.clean()
        self.assertEquals(user.age, 32)

    def test_integer_validation(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person(first_name='soren', last_name='hansen', age='foobar')
        self.assertRaises(ValueError, user.clean)

    def test_store_retrieve(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person(first_name='soren', last_name='hansen', age=31)
        user.save()
        user = Person.get(user.key)
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        self.assertEquals(user.age, 31)

    def test_store_retrieve_expensive(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person(first_name='soren', last_name='hansen', age=31)
        user.save()
        users = Person.get(first_name='soren', last_name='hansen').all()
        self.assertEquals(len(users), 1)
        self.assertEquals(users[0].first_name, 'soren')
        self.assertEquals(users[0].last_name, 'hansen')
        self.assertEquals(users[0].age, 31)

    def test_store_retrieve_cheap(self):
        class Person(RiakObject):
            bucket_name = 'users'
            searchable = True

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person(first_name='soren', last_name='hansen', age=31)
        user.save()
        users = Person.get(first_name='soren', last_name='hansen').all()
        self.assertEquals(len(users), 1)
        self.assertEquals(users[0].first_name, 'soren')
        self.assertEquals(users[0].last_name, 'hansen')
        self.assertEquals(users[0].age, 31)

    def test_required_fields(self):
        class Person(RiakObject):
            bucket_name = 'users'
            searchable = True

            first_name = String(required=True)
            last_name = String()

        user = Person(last_name='hansen', age=31)
        self.assertRaises(ValidationError, user.save)
        user.first_name = 'soren'
        user.save()

    def test_one_relation(self):
        class Person(RiakObject):
            bucket_name = 'users'
            searchable = True

            first_name = String(required=True)
            last_name = String()
            manager = RelatedObjects()

        user1 = Person(first_name='jane', last_name='smith')
        user1.save()
        user2 = Person(first_name='john', last_name='smith')
        user2.manager = [user1]
        user2.save()
        user2_key = user2.key
        user2 = Person.get(user2_key)
        user2_manager = user2.manager[0]
        self.assertEquals(user2_manager.first_name, 'jane')
        self.assertEquals(user2_manager.last_name, 'smith')

