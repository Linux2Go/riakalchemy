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
    >>> from riakalchemy.types import String, Integer

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

Before we can start using this, we need to connect to Riak.

    >>> riakalchemy.connect()

Let's create a Person object:

    >>> person = Person()
    >>> person.name = 'Soren Hansen'
    >>> person.age = '30'
    >>> person.save()
    >>> person
    <Person name='Soren Hansen' age=30>

As we didn't provide a key, Riak assigned one automatically:

	>>> person.key # doctest: +SKIP
	'NUD2opa92uFD9JaFefXktCxzEUW'

We can delete the object again like so:

	>>> person.delete()

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

## Running the tests ##

At the moment, python-riak's TestServer doesn't support 2I, so we need
access to a real Riak. To run the tests against a real Riak, use:

>     $ RIAKALCHEMY_SYSTEM_RIAK_PORT=8098 nosetests .
