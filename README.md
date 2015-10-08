## What Is It
It's a simple HTTP Publish/Subscribe Server.

## Installing
This is a standard python package and can be installed using pip.

`pip install git+https://github.com/justnoise/httpmq#egg=httpmq`

Note: if you are starting from scratch on a machine, you'll need to set up a number of things.  For example, on ubuntu you'll need:
* `sudo apt-get update`
* `sudo apt-get install python-pip python-dev build-essential`
* `sudo pip install --upgrade pip`
* `sudo apt-get install libffi-dev`
* `sudo apt-get install git`

The httpmq package will also install a number of requirements (twisted, monocle, requests, etc.) and requirements for those requirements.  I suggest setting up a virtualenv to isolate those changes from your system:
```
sudo pip install virtualenvwrapper
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv httpmq
pip install git+https://github.com/justnoise/httpmq#egg=httpmq
```

## Running
After installing, it's pretty easy to run the server:

`httpmq storage_file.dat`

## Design
There are two obvious ways to handle the storage and distribution of messages:

The most obvious and traditional approach is to have a queue for each user subscribed to a topic.  When a message arrives, you find all the subscribers for the topic and deliver the message to each subscriber's queue.  The downside of this approach is, for topics with a lot of subscribers, you have to deliver the message to lots of queues for each publish command.  Users might not pick up their messages for a long time and, in a very large system, this will eat up all the memory on your machine.

An alternative approach is to (1) keep track of the number of subscribers who need to receive a message (a reference_count) and (2) keep track of the last messsage a subscriber has received and (3) use an incrementing id for each message in a topic.  Using this system, each topic and user combination only needs to keep track of the last message received.  The downside of this is managing when to delete a message.  When a subscriber unsubscribes from a topic, you must decrement the reference count for all messages they haven't received yet.  It's a slight bit more bookkeeping but that's the price you pay.

## Nice Things
The backing store for keeping track of subscriptions is sqlite. I could have used the shelve module where topics would be keys and the values are sets containing the topic's subscribers.  You'd have to re-serialize the entire set for each subscription change.  That isn't ideal.

Messages aren't persisted but it wouldn't be hard to add that in.  We would simply need to add a "last_message_id" field to the subscription table and a new table to hold messages and a small amount of logic to keep track of everything.

It's async, using twisted and monocle on the backend.

There are tests. These make it perfect. Nothing can go wrong... acn og wrong... wrongggggggggggg

## What Got Left Out
In a production system, we would probably want to add more logging.  I've found that logging messages grow organically as a system is developed and tested.  Telemetry data (e.g. statsd) would allow you to see actions happening in the system in real-time.  You'd also want to be monitoring the machine httpmq runs on and the process itself.

It would be great to include an upstart or systemd script to make sure people are always running this great piece of software.

While I've used the daemon package a number of times before, daemonizing the message server hung he process at 100% cpu usage on my mac (but works fine on linux).  I need to investigate why its failing on mac.  For now, I've commented out that functionality.  I usually don't like keeping around commented code in a system but I want to remember to get in and debug that after sending this off.

Finally, with another bit of effort and some more time, it would be cool to put the whole thing in a docker container and use flocker to keep track of the storage file	.  Would be a good thing to do at some point but not this point.
