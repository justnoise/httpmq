Installing:
This is a standard python package and can be installed using pip.

pip install "git+https://github.com/justnoise/httpmq#egg=httpmq"

The package will also install a number of requirements (twisted,
monocle, etc.) and requirements for those requirements.  I suggest
setting up a virtualenv to isolate those changes from your system.

Running:
It's pretty easy to run the server:

python message_server.py storage.dat

Design
There are two obvious ways to handle the storage and distribution of messages:

The most obvious and traditional approach is to have a queue for each user subscribed to a topic.  When a message arrives, you find all the subscribers for the topic and deliver the message to their queue.  The downside of this approach is, for topics with a lot of subscribers, you have to deliver the message lots of times for each publish command.  Users might not pick up their messages for a long time and, in a very large system, this will eat up all the memory on your machine.

An alternative is to (1) add a count of the number of subscribers who need to receive a message and (2) keep track of the last messsage a subscriber has received.  Each topic and user combination only needs to keep track of the last message received.  The downside of this is managing when to delete the message.  When a subscriber unsubscribes from a topic, you must decrement the reference count for all messages they haven't received yet.  It's a bit more bookkeeping but that's the price you pay.

The backing store for keeping track of subscriptions is sqlite. I could have used the shelve module where topics would be keys and sets of subscribers as the values.  You'd have to re-serialize the entire set for each subscription change which isn't idea.  Subscriptions are saved with each change cause servers go down unexpectedly.

Messages aren't persisted but it woudn't be hard to add that in.  We would simply need to add a "last_message_id" field to the subscription table and a new table to hold messages and a small amount of logic to push the correct info to the DB.

Tests
These make it perfect. Nothing can go wrong... acn og wrong... wrongggggggggggg

What got left out
In a production system, we would probably want to add more logging.  I've found that logging messages grow organically as a system is developed and tested.  Telemetry data (e.g. statsd) would also be helpful to see actions happening in the system in real time.  You'd also want to be monitoring the box this sits on and the system itself.

While I've used the daemon package a number of times before, daemonizing the message server hung he process at 100% cpu usage on my mac.  I need to investigate why this happend.  For now, I've commented out that functionality.

With another bit of effort and some more time, it would be cool to put the whole thing in a docker container and use flocker for the storage.  Would be a good thing to do at some point but not this point
