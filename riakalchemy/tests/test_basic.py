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
except ValueError:
    use_system_riak = False
    riak_port = 10229


class _BasicTests(unittest.TestCase):
    def _create_class(self, searchable=False, last_name_required=False):
        _searchable = searchable

        class Person(RiakObject):
            searchable = _searchable
            bucket_name = 'users1'

            first_name = String()
            last_name = String(required=last_name_required)
            age = Integer()

        return Person

    def _create_object(self, searchable=False,
                       last_name_required=False, **kwargs):
        Person = self._create_class(searchable=searchable,
                                    last_name_required=last_name_required)
        person = Person(**kwargs)
        return Person, person

    def test_create_object(self):
        """Can create object"""
        self._create_object()

    def _incomplete_value_set(self):
        return {'first_name': 'soren',
                'age': 31}

    def _set_values_on_init(self, values, searchable=False,
                            last_name_required=False):
        return self._create_object(searchable=searchable,
                                   last_name_required=last_name_required,
                                   **values)

    def _create_object_and_update(self, values):
        cls, obj = self._create_object()
        obj.update(values)
        return cls, obj

    def _object_create_and_setattr(self, values):
        cls, obj = self._create_object()
        for k, v in values.iteritems():
            setattr(obj, k, v)
        return cls, obj

    def _verify_values(self, obj, values):
        for k, v in values.iteritems():
            self.assertEquals(getattr(obj, k), v)

    def test_set_incomplete_values_on_init(self):
        """Set incomplete set of values at __init__ time"""
        values = self._incomplete_value_set()
        cls, obj = self._set_values_on_init(values)
        self._verify_values(obj, values)
        obj.save()
        self.addCleanup(obj.delete)
        self._verify_values(obj, values)

    def test_object_update_incomplete(self):
        """Set incomplete set of values using .update()"""
        values = self._incomplete_value_set()
        cls, obj = self._create_object_and_update(values)
        self._verify_values(obj, values)
        obj.save()
        self.addCleanup(obj.delete)
        self._verify_values(obj, values)

    def test_object_setattr_incomplete(self):
        """Set incomplete set of values using attribute access"""
        values = self._incomplete_value_set()
        cls, obj = self._object_create_and_setattr(values)
        self._verify_values(obj, values)
        obj.save()
        self.addCleanup(obj.delete)
        self._verify_values(obj, values)

    def test_save_and_retrieve_object(self):
        """Create object, retrieve it again by key"""
        values = self._incomplete_value_set()
        cls, obj = self._set_values_on_init(values)
        obj.save()
        self.addCleanup(obj.delete)
        cls.get(obj.key)
        self._verify_values(obj, values)

    def test_save_delete_retrieve_failes(self):
        """Create object, delete it, attempt to retrieve it again by key"""
        values = self._incomplete_value_set()
        cls, obj = self._set_values_on_init(values)
        obj.save()
        obj_key = obj.key
        obj.delete()
        self.assertRaises(NoSuchObjectError, cls.get, obj_key)

    def test_integer_clean(self):
        """Integer passed as a string will be converted on .clean()"""
        values = self._incomplete_value_set()
        values['age'] = '32'
        cls, obj = self._set_values_on_init(values)
        obj.clean()
        self.assertEquals(type(obj.age), int)
        self.assertEquals(obj.age, 32)

    def test_invalid_integer_rejected(self):
        """Integer field set to value that cannot be cast to int fails"""
        values = self._incomplete_value_set()
        values['age'] = 'this is not a number'
        cls, obj = self._set_values_on_init(values)
        self.assertRaises(ValidationError, obj.clean)

    def test_missing_field_rejected(self):
        """Unset required field causes .clean() to fail"""
        values = self._incomplete_value_set()
        cls, obj = self._set_values_on_init(values, last_name_required=True)
        self.assertRaises(ValidationError, obj.clean)

    def _test_retrieve_by_values(self, searchable):
        values = self._incomplete_value_set()
        cls, obj = self._set_values_on_init(searchable=searchable,
                                            values=values)
        obj.save()
        self.addCleanup(obj.delete)

        results = cls.get(**values).all()
        self.assertEquals(len(results), 1)
        self._verify_values(obj, values)

    def test_retrieve_by_values_searchable(self):
        self._test_retrieve_by_values(searchable=True)

    def test_retrieve_by_values_non_searchable(self):
        self._test_retrieve_by_values(searchable=False)

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


class RiakBackedTests(_BasicTests):
    test_server_started = False

    def setUp(self):
        if not use_system_riak and not self.__class__.test_server_started:
            riakalchemy.connect(test_server=True, port=riak_port)
            self.__class__.test_server_started = True
        else:
            riakalchemy.connect(test_server=False, port=riak_port)
