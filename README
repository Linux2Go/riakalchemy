# Object Mapper for Riak #

## Configuring Riak for RiakAlchemy ##

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
