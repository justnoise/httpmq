import functools

import monocle
monocle.init("twisted")
from monocle.twisted_stack.utils import cb_to_df
from twisted.trial.unittest import TestCase

from server import Server, Message


def twistedtest_o(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return cb_to_df(monocle.o(f)(*args, **kwargs))
    return wrapper


class FakeDb(object):
    # installing the mock library involves upgrading setuptools...  I
    # wanted to make setting up dependencies easy so we'll fake out
    # the db instead.
    def add_subscription(self, *a):
        pass
    def remove_subscription(self, *a):
        pass


class FakeRequest(object):
    def __init__(self, body):
        self.body = body


class TestServer(TestCase):
    def setUp(self):
        self.s = Server(FakeDb())
        self.topic = "topic1"
        self.username = "user1"
        self.msg_data = "fake_data"
        self.req = FakeRequest(self.msg_data)

    def test_pop_message(self):
        msg = self.s.pop_message(self.topic, 1)
        self.assertEqual(msg, None)
        test_msg = Message(self.msg_data, 2)
        self.s.messages[self.topic][1] = test_msg
        self.assertEqual(len(self.s.messages[self.topic]), 1)
        msg = self.s.pop_message(self.topic, 1)
        self.assertEqual(msg, test_msg)
        self.assertEqual(msg.ref_count, 1)
        self.assertEqual(len(self.s.messages[self.topic]), 1)
        msg = self.s.pop_message(self.topic, 1)
        self.assertEqual(len(self.s.messages[self.topic]), 0)

    @twistedtest_o
    def test_subscribe(self):
        message_id = 3
        self.s.topic_last_message_id[self.topic] = message_id
        response = yield self.s.subscribe(self.req, self.topic, self.username)
        self.assertEqual(self.s.topic_to_user_offsets[self.topic][self.username], message_id)
        self.assertEqual(response[0], 200)

    @twistedtest_o
    def test_unsubscribe_no_subscription(self):
        response = yield self.s.unsubscribe(self.req, self.topic, self.username)
        self.assertEqual(response[0], 404)
        yield self.s.subscribe(self.req, self.topic, "another_user")
        response = yield self.s.unsubscribe(self.req, self.topic, self.username)
        self.assertEqual(response[0], 404)

    @twistedtest_o
    def test_unsubscribe_no_messages(self):
        yield self.s.subscribe(self.req, self.topic, self.username)
        response = yield self.s.unsubscribe(self.req, self.topic, self.username)
        self.assertEqual(response[0], 200)

    @twistedtest_o
    def test_unsubscribe_with_messages(self):
        yield self.s.subscribe(self.req, self.topic, self.username)
        response = yield self.s.publish(self.req, self.topic)
        self.assertEqual(len(self.s.messages[self.topic]), 1)
        response = yield self.s.unsubscribe(self.req, self.topic, self.username)
        self.assertEqual(len(self.s.messages[self.topic]), 0)
        self.assertEqual(response[0], 200)

    @twistedtest_o
    def test_unsubscribe_after_retrieve(self):
        yield self.s.subscribe(self.req, self.topic, self.username)
        yield self.s.subscribe(self.req, self.topic, "user2")
        response = yield self.s.publish(self.req, self.topic)
        response = yield self.s.publish(self.req, self.topic)
        response = yield self.s.publish(self.req, self.topic)
        self.assertEqual(len(self.s.messages[self.topic]), 3)
        response = yield self.s.retrieve(self.req, self.topic, self.username)
        self.assertEqual(len(self.s.messages[self.topic]), 3)
        response = yield self.s.unsubscribe(self.req, self.topic, self.username)
        self.assertEqual(len(self.s.messages[self.topic]), 3)
        for message in self.s.messages[self.topic].values():
            self.assertEqual(message.ref_count, 1)
        self.assertEqual(response[0], 200)

    @twistedtest_o
    def test_publish_no_subscribers(self):
        response = yield self.s.publish(self.req, self.topic)
        self.assertEqual(response[0], 200)
        self.assertEqual(len(self.s.messages[self.topic]), 0)

    @twistedtest_o
    def test_publish_with_subscribers(self):
        yield self.s.subscribe(self.req, self.topic, "user1")
        yield self.s.subscribe(self.req, self.topic, "user2")
        response = yield self.s.publish(self.req, self.topic)
        self.assertEqual(response[0], 200)
        self.assertEqual(len(self.s.messages[self.topic]), 1)
        msg = self.s.messages[self.topic][1]
        self.assertEqual(msg.data, self.msg_data)
        self.assertEqual(msg.ref_count, 2)

    @twistedtest_o
    def test_retrieve(self):
        yield self.s.subscribe(self.req, self.topic, self.username)
        response = yield self.s.publish(self.req, self.topic)
        response = yield self.s.retrieve(self.req, self.topic, self.username)
        self.assertEqual(response[0], 200)
        self.assertEqual(response[2], self.msg_data)
        self.assertEqual(len(self.s.messages[self.topic]), 0)
        response = yield self.s.retrieve(self.req, self.topic, self.username)
        self.assertEqual(response[0], 204)

    @twistedtest_o
    def test_retrieve_no_subscribers(self):
        response = yield self.s.retrieve(self.req, self.topic, self.username)
        self.assertEqual(response[0], 404)
