# Object Mapper for Riak #

## What is RiakAlchemy ##

RiakAlchemy is an object mapper for Riak written in Python. It's
supposed to make it easy to create data types that you can move between
Riak and Python. It's rather crude so far, but that'll probably change
as my needs (or yours!) arise. Notably, it has no conflict
resolution/sibling reconciliation logic.

## Quick Start Guide ##

To get Riak set up, see the <a href="#configuring-riak">Configuring
Riak for RiakAlchemy</a> section further down.

Let's create a data type:

    >>> import riakalchemy
    >>> from riakalchemy.types import String, Integer, RelatedObjects

    >>> class Person(riakalchemy.RiakObject):
    ...     # bucket_name is the name of the Riak bucket that will hold these objects
    ...     bucket_name = 'people'
    ...
    ...     # A couple of attributes
    ...     name = String()
    ...     age = Integer()
    ...
    ...     # And a handy __repr__ method (entirely optional!)
    ...     def __repr__(self):
    ...         return '<Person name=%r age=%r>' % (self.name, self.age)

Pretty straight forward.

Before we can start using this, we need to connect to Riak. You can safely
leave out the `test_server` and `port` arguments. The defaults for connect()
matches the defaults for Riak.

    >>> riakalchemy.connect(test_server=True, port=9876)

Let's create a Person object:

    >>> person = Person()
    >>> person.name = 'Soren Hansen'
    >>> person.age = '30'
    >>> person.save()
    >>> person
    <Person name='Soren Hansen' age=30>

(Note that the age was provided as a string, but got turned into an int())

As we didn't provide a key, Riak assigned one automatically:

    >>> person_key = person.key
    >>> person_key # doctest: +SKIP
    'NUD2opa92uFD9JaFefXktCxzEUW'

We can delete the object again like so:

    >>> person.delete()
    >>> Person.get(person_key)
    Traceback (most recent call last):
        ...
    NoSuchObjectError

Those are the bare essentials. Let's expand a bit on this:

## Related (linked) objects ##

Let's define a new Person type:

    >>> class Person(riakalchemy.RiakObject):
    ...     bucket_name = 'people'
    ...
    ...     name = String()
    ...     age = Integer()
    ...     clients = RelatedObjects()
    ...
    ...     def __repr__(self):
    ...         return '<Person name=%r age=%r>' % (self.name, self.age)

We've added a `clients` attribute of the RelatedObjects type. Let's create a couple of these objects:

    >>> john = Person(name='John Doe', age=30)
    >>> john.save()
    >>> jane = Person(name='Jane Doe', age=29)
    >>> jane.save()
    >>> john.clients
    []
    >>> john.clients.append(jane)
    >>> john.save()
    >>> john.clients
    [<Person name='Jane Doe' age=29>]

<!--
	>>> john.delete()
	>>> jane.delete()

-->

Behind the scenes, a link is added from the John key in Riak to the Jane key. The link is tagged as `clients`. When you access `john.clients`, all the links from the john key tagged as `clients` are returned in a list. It's worth noting that these are always lists. If you want only one element in the list, it's up to you to make sure that's always true.

With the person type defined this way, it's easy to find every one of John's clients, but there's no way to find every Person who has Jane as their client.

    >>> class Person(riakalchemy.RiakObject):
    ...     bucket_name = 'people'
    ...
    ...     name = String()
    ...     age = Integer()
    ...     clients = RelatedObjects(backref=True)
    ...
    ...     def __repr__(self):
    ...         return '<Person name=%r age=%r>' % (self.name, self.age)


See we added `backref=True` to the RelatedObjects definition.

Let's take it for a spin:

    >>> james = Person(name='James Doe', age=31)
    >>> james.save()
    >>> john = Person(name='John Doe', age=30)
    >>> john.save()
    >>> jane = Person(name='Jane Doe', age=29)
    >>> jane.save()
    >>> james.clients = [jane]
    >>> james.save()
    >>> john.clients = [jane]
    >>> john.save()
    >>> Person.get(clients=jane).all() # doctest: +SKIP
    [<Person name=u'James Doe' age=31>, <Person name=u'John Doe' age=30>]

<!---
    >>> people = Person.get(clients=jane).all()
    >>> len(people)
    2
    >>> james in people
    True
    >>> john in people
    True

-->

Behind the scenes, this is achieved by adding a secondary index on the objects as well as creating the link. So, when we added `jane` as a client for each for `james` and `john`, they both got a secondary index added to them: `clients_bin:people/<jane's key>`. This means that the `jane` object is not touched at all (saving a couple of round trips), and it also means that the operation is atomic.

Just for good measure, let's see it working with multiple backrefs. So, we make John a client for James's:

    >>> james.clients.append(john)
    >>> james.save()

We can still see who Jane is a client of:

    >>> Person.get(clients=jane).all() # doctest: +SKIP
    [<Person name=u'James Doe' age=31>, <Person name=u'John Doe' age=30>]

<!--
    >>> people = Person.get(clients=jane).all()
    >>> len(people)
    2
    >>> james in people
    True
    >>> john in people
    True

-->
And John is now also a client of James:

    >>> Person.get(clients=john).all()
    [<Person name=u'James Doe' age=31>]

Removing people from these relationships also works:

    >>> james.clients.remove(jane)
    >>> james.save()
    >>> Person.get(clients=jane).all()
    [<Person name=u'John Doe' age=30>]

<!--

    >>> jane.delete()
	>>> john.delete()
	>>> james.delete()

-->
That should be enough to get you started! Enjoy!

## <a name="configuring-riak">Configuring Riak for RiakAlchemy</a> ##

You need to do tweak Riak a little bit for RiakAlchemy to work.
Namely, you need to enable Riak Search, use the eleveldb storage
backend, and set the delete policy to immediate.

### Enabling Riak Search ###

Somewhere in your `app.config`, you'll find this:

>     %% Riak Search Config
>     {riak_search, [
>                 %% To enable Search functionality set this 'true'.
>                 {enabled, false}
>                ]},

You guessed it: Change the "false" to "true".

### Use eleveldb storage ###

Somewhere in the `riak_kv` section of your `app.config`, you can see:

>     {storage_backend, riak_kv_bitcask_backend},

Change that to:

>     {storage_backend, riak_kv_eleveldb_backend},

### Set the delete policy to immediate ###

Somewhere in your `riak_kv` section, add:

>     {delete_mode, immediate}

### Scripted configuration ###

You can make all these config changes with this single command assuming
your existing `app.config` is unmodified from when you installed Riak.

>     sudo sed -e '/^ {riak_kv/ a {delete_mode, immediate},' \
>              -e 's/storage_backend, riak_kv_bitcask_backend/storage_backend, riak_kv_eleveldb_backend/' \
>              -e '/^ {riak_search/,+2 s/enabled, false/enabled, true/' -i.bak /etc/riak/app.config

## Running the tests ##

At the moment, python-riak's TestServer doesn't support 2I, so we need
access to a real Riak. To run the tests against a real Riak, use:

>     $ RIAKALCHEMY_SYSTEM_RIAK_PORT=8098 nosetests .

### Virtualenv ###

The `tools/` directory has a script to easily create a virtualenv for you:

>     $ tools/setup_virtualenv.sh

Once it's done, you can run the unit tests in the virtualenv like so:

>     $ RIAKALCHEMY_SYSTEM_RIAK_PORT=8098 .tools/venv_wrap.sh nosetests
