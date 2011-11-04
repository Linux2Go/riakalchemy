import os
import unittest2 as unittest

import riakalchemy
from riakalchemy import RiakObject
from riakalchemy.exceptions import ValidationError, NoSuchObjectError
from riakalchemy.types import String, Integer, RelatedObjects

system_riak = os.environ.get('RIAKALCHEMY_SYSTEM_RIAK_PORT', '')

try:
    riak_port = int(system_riak)
    use_system_riak = True
    supports_indexes = True
except ValueError:
    use_system_riak = False
    supports_indexes = False
    riak_port = 10229

class BasicTests(unittest.TestCase):
    test_server_started = False

    def setUp(self):
        if not use_system_riak:
            if  not self.__class__.test_server_started:
                riakalchemy.connect(test_server=True, port=riak_port)
                self.__class__.test_server_started = True
            else:
                riakalchemy._clear_test_connection()
        else:
            riakalchemy.connect(test_server=False, port=riak_port)

    def test_create_save_retrieve_delete(self):
        """Create, save, retrieve, and delete an object"""

        class Person1(RiakObject):
            bucket_name = 'users1'

            first_name = String()
            last_name = String()

        user = Person1(first_name='soren', last_name='hansen')
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        user.save()
        user = Person1.get(user.key)
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        user.delete()
        self.assertRaises(NoSuchObjectError, Person1.get, user.key)

    def test_create_save_delete(self):
        """Create, save, and delete an object"""
        class Person2(RiakObject):
            bucket_name = 'users2'

            first_name = String()
            last_name = String()

        user = Person2(first_name='soren', last_name='hansen')
        self.assertEquals(user.first_name, 'soren')
        self.assertEquals(user.last_name, 'hansen')
        user.save()
        user.delete()
        self.assertRaises(NoSuchObjectError, Person2.get, user.key)

    def test_integer_clean(self):
        class Person3(RiakObject):
            bucket_name = 'users3'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person3(first_name='soren', last_name='hansen', age='32')
        self.assertEquals(user.age, '32')
        user.clean()
        self.assertEquals(user.age, 32)

    def test_not_all_fields_set(self):
        class Person4(RiakObject):
            bucket_name = 'users4'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person4(first_name='soren', age=30)
        user.save()
        self.addCleanup(user.delete)

    def test_integer_validation(self):
        class Person5(RiakObject):
            bucket_name = 'users5'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person5(first_name='soren', last_name='hansen', age='foobar')
        self.assertRaises(ValueError, user.clean)

    def test_store_retrieve_expensive(self):
        class Person6(RiakObject):
            bucket_name = 'users6'

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person6(first_name='soren', last_name='hansen', age=31)
        user.save()
        self.addCleanup(user.delete)
        users = Person6.get(first_name='soren', last_name='hansen').all()
        self.assertEquals(len(users), 1)
        self.assertEquals(users[0].first_name, 'soren')
        self.assertEquals(users[0].last_name, 'hansen')
        self.assertEquals(users[0].age, 31)

    def test_store_retrieve_cheap(self):
        class Person7(RiakObject):
            bucket_name = 'users7'
            searchable = True

            first_name = String()
            last_name = String()
            age = Integer()

        user = Person7(first_name='soren', last_name='hansen', age=31)
        user.save()
        self.addCleanup(user.delete)
        users = Person7.get(first_name='soren', last_name='hansen').all()
        self.assertEquals(len(users), 1)
        self.assertEquals(users[0].first_name, 'soren')
        self.assertEquals(users[0].last_name, 'hansen')
        self.assertEquals(users[0].age, 31)

    def test_required_fields(self):
        class Person8(RiakObject):
            bucket_name = 'users8'
            searchable = True

            first_name = String(required=True)
            last_name = String()

        user = Person8(last_name='hansen', age=31)
        self.assertRaises(ValidationError, user.save)
        user.first_name = 'soren'
        user.save()
        self.addCleanup(user.delete)

    def test_relation(self):
        class Person9(RiakObject):
            bucket_name = 'users9'
            searchable = True

            first_name = String(required=True)
            last_name = String()
            manager = RelatedObjects()

        user1 = Person9(first_name='jane', last_name='smith')
        user1.save()
        self.addCleanup(user1.delete)
        user2 = Person9(first_name='john', last_name='smith')
        user2.manager = [user1]
        user2.save()
        self.addCleanup(user2.delete)
        user2_key = user2.key
        user2 = Person9.get(user2_key)
        user2_manager = user2.manager[0]
        self.assertEquals(user2_manager.first_name, 'jane')
        self.assertEquals(user2_manager.last_name, 'smith')

    def test_pre_post_hooks(self):
        global post_save_has_run, pre_delete_has_run, post_delete_has_run
        post_save_has_run = False
        pre_delete_has_run = False
        post_delete_has_run = False

        class Person10(RiakObject):
            bucket_name = 'users10'
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

        user = Person10(first_name='jane', last_name='smith')
        user.save()
        self.addCleanup(user.delete)
        self.assertTrue(post_save_has_run)
        # Verify that the hook is run
        self.assertEquals(user.first_name, 'JANE')

        # ..and verify that it was run before we stored the object
        user = Person10.get(user.key)
        self.assertEquals(user.first_name, 'JANE')

        # First delete should be prevented by the exception
        self.assertRaises(Exception, user.delete)
        user = Person10.get(user.key)

        # Second delete should go through just fine
        user.delete()
        self.assertRaises(NoSuchObjectError, Person10.get, user.key)

        self.assertTrue(post_delete_has_run)

    @unittest.skipUnless(supports_indexes, "Secondary Indexes not support by "
                                           "the current backend")
    def test_back_relation(self):
        class Person11(RiakObject):
            bucket_name = 'users11'

            first_name = String(required=True)
            last_name = String()
            manager = RelatedObjects(backref=True)

        user1 = Person11(first_name='jane', last_name='smith')
        user1.save()
        self.addCleanup(user1.delete)
        user2 = Person11(first_name='john', last_name='smith')
        user2.manager = [user1]
        user2.save()
        self.addCleanup(user2.delete)

        user3 = Person11(first_name='peter', last_name='smith')
        user3.manager = [user1]
        user3.save()
        self.addCleanup(user3.delete)

        persons = Person11.get(manager=user1).all()
        self.assertEquals(len(persons), 2)

        # We don't know the order they've come back in, but they have
        # the same last name
        self.assertEquals(persons[0].last_name, user2.last_name)
        self.assertEquals(persons[0].last_name, user3.last_name)
        self.assertNotEquals(persons[0].first_name, persons[1].first_name)
        self.assertIn(persons[0].first_name, [persons[0].first_name,
                                              persons[1].first_name])
        self.assertIn(persons[1].first_name, [persons[0].first_name,
                                              persons[1].first_name])
