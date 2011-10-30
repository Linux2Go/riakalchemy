import unittest

import riakalchemy
from riakalchemy import RiakObject
from riakalchemy.exceptions import ValidationError, NoSuchObjectError
from riakalchemy.types import String, Integer, RelatedObjects

class BasicTests(unittest.TestCase):
    test_server_started = False

    def setUp(self):
        if not self.__class__.test_server_started:
            riakalchemy.connect(test_server=True, port=10229)
            self.__class__.test_server_started = True
        else:
            riakalchemy._clear_test_connection()

    def test_create_save_retrieve_delete(self):
        """Create, save, retrieve, and delete an object"""

        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()

        user = Person(first_name='soren', last_name='hansen')
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        user.save()
        user = Person.get(user.key)
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        user.delete()
        self.assertRaises(NoSuchObjectError, Person.get, user.key)

    def test_create_save_delete(self):
        """Create, save, and delete an object"""
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()

        user = Person(first_name='soren', last_name='hansen')
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        user.save()
        user.delete()
        self.assertRaises(NoSuchObjectError, Person.get, user.key)

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

    def test_not_all_fields_set(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()
            age = Integer()

        Person(first_name='soren', age=30)

    def test_integer_validation(self):
        class Person(RiakObject):
            bucket_name = 'users'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person(first_name='soren', last_name='hansen', age='foobar')
        self.assertRaises(ValueError, user.clean)

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

    def test_relation(self):
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

    def test_pre_post_hooks(self):
        global post_save_has_run, pre_delete_has_run, post_delete_has_run
        post_save_has_run = False
        pre_delete_has_run = False
        post_delete_has_run = False

        class Person(RiakObject):
            bucket_name = 'users'
            searchable = True

            first_name = String()
            last_name = String()

            def pre_save(self):
                self.first_name = self.first_name.upper()

            def post_save(self):
                global post_save_has_run
                post_save_has_run = True

            def pre_delete(self):
                global pre_delete_has_run
                if not pre_delete_has_run:
                    pre_delete_has_run = True
                    raise Exception("Don't save this")

            def post_delete(self):
                global post_delete_has_run
                post_delete_has_run = True

        user = Person(first_name='jane', last_name='smith')
        user.save()
        self.assertTrue(post_save_has_run)
        # Verify that the hook is run
        self.assertEquals(user.first_name, 'JANE')

        # ..and verify that it was run before we stored the object
        user = Person.get(user.key)
        self.assertEquals(user.first_name, 'JANE')

        # First delete should be prevented by the exception
        self.assertRaises(Exception, user.delete)
        user = Person.get(user.key)

        # Second delete should go through just fine
        user.delete()
        self.assertRaises(NoSuchObjectError, Person.get, user.key)

        self.assertTrue(post_delete_has_run)
