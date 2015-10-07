import sys
from collections import defaultdict
import argparse
import logging


import monocle
from monocle import _o, Return, launch
monocle.init("twisted")
from monocle.stack import eventloop
from monocle.stack.network import add_service
from monocle.stack.network.http import HttpServer
import daemon

from db import SubscriptionDb

DEFAULT_PORT = 8888
log = logging.getLogger(__name__)
s = HttpServer(DEFAULT_PORT)
server = None

# Things that would be cool:
# 1. I should have put all this in a docker container and sent that

#API:
# subscribe: POST /<topic>/<username> -> 200
# unsubscribe: DELETE /<topic>/<username> -> 200 404
# publish: POST /<topic> -> 200
# retrieve: GET /<topic>/<username> -> 200, 204, 404

class Message(object):
    def __init__(self, data, ref_count):
        self.data = data
        self.ref_count = ref_count


class Server(object):
    def __init__(self, db):
        self.db = db
        self.messages = defaultdict(dict)
        self.topic_last_message_id = defaultdict(int)
        self.topic_to_user_offsets = defaultdict(dict) # subscriptions


    @_o
    def load_subscriptions(self):
        subscriptions = yield self.db.get_subscriptions()
        for topic, username in subscriptions:
            self.topic_to_user_offsets[topic][username] = 0

    def pop_message(self, topic, message_id):
        message = self.messages[topic].get(message_id, None)
        if message:
            message.ref_count -= 1
            if message.ref_count <= 0:
                self.messages[topic].pop(message_id)
        return message

    @_o
    def subscribe(self, request, topic, username):
        log.info("subscribe %s to %s", topic, username)
        if username not in self.topic_to_user_offsets[topic]:
            last_message_id = self.topic_last_message_id[topic]
            self.topic_to_user_offsets[topic][username] = last_message_id
            self.db.add_subscription(topic, username)
        yield Return(200, {}, "Subscription succeeded")

    @_o
    def unsubscribe(self, request, topic, username):
        log.info("unsubscribe %s from %s", topic, username)
        # if the topic doesn't exist, return 404
        try:
            user_last_message_id = self.topic_to_user_offsets[topic].pop(
                username)
            last_message_id = self.topic_last_message_id[topic]
            num_msgs = 0
            for message_id in range(user_last_message_id + 1,
                                    last_message_id + 1):
                self.pop_message(topic, message_id)
                num_msgs += 1
            log.debug("removed %s messages for %s", num_msgs, username)
            self.db.remove_subscription(topic, username)
            yield Return(200, {}, "")
        except KeyError:
            yield Return(404, {}, "")

    @_o
    def publish(self, request, topic):
        log.info("publish to topic %s", topic)
        if topic in self.topic_to_user_offsets:
            self.topic_last_message_id[topic] += 1
            message_id = self.topic_last_message_id[topic]
            msg = Message(request.body,
                          len(self.topic_to_user_offsets[topic]))
            self.messages[topic][message_id] = msg
        yield Return(200, {}, "")

    @_o
    def retrieve(self, request, topic, username):
        log.info("retrieve %s for %s", topic, username)
        try:
            last_message_id = self.topic_to_user_offsets[topic][username]
        except KeyError:
            yield Return(404, {}, "")

        next_message_id = last_message_id + 1
        message = self.pop_message(topic, next_message_id)
        if message:
            self.topic_to_user_offsets[topic][username] += 1
            yield Return(200, {}, message.data)
        else:
            yield Return(204, {}, "")


#
# Http Requset Routing
#
@s.post("/:topic/:username")
def handle_subscribe(request, topic, username):
    response = yield server.subscribe(request, topic, username)
    yield Return(response)

@s.delete("/:topic/:username")
def handle_unsubscribe(request, topic, username):
    response = yield server.unsubscribe(request, topic, username)
    yield Return(response)

@s.post("/:topic")
def handle_publish(request, topic):
    response = yield server.publish(request, topic)
    yield Return(response)

@s.get("/:topic/:username")
def handle_retrieve(request, topic, username):
    response = yield server.retrieve(request, topic, username)
    yield Return(response)


def setup_logging(logfile_path):
    global log
    standard_log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s[%(funcName)s:"
    "%(lineno)s] - %(levelname)s - %(message)s")

    if not logfile_path:
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(logfile_path)
    handler.setFormatter(standard_log_formatter)
    root = logging.getLogger()
    # only see warnings and above from imported libs
    root.setLevel(logging.WARNING)
    root.addHandler(handler)
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    log.debug("starting up logging")

def parse_args():
    parser = argparse.ArgumentParser(description='A simple Http Message Queue')
    parser.add_argument(
        "-d", "--daemonize",
        action = "store_true", default=False,
        help='run as a daemon in the background')
    parser.add_argument(
        "-P", "--pidfile", metavar="FILE",
         default="/var/run/httpmq.pid",
         help="when used with --daemonize, "
         "write backgrounded Process ID to FILE [default: %(default)s]")
    parser.add_argument(
        "-l", "--logfile", metavar="FILE",
        help="Output to a logfile instead of stdout")
    # parser.add_argument(
    #     "-p", "--port",
    #     default=DEFAULT_PORT, type=int,
    #     help="Server port")
    parser.add_argument(
        "-f", "--file", metavar="FILE",
        dest="sql_filename",
        help="sqlite database file")

    args = parser.parse_args()
    return args


@_o
def main():
    global server
    try:
        args = parse_args()
        setup_logging(args.logfile)
        if args.daemonize:
            daemon.daemonize(args.pidfile)

        db = SubscriptionDb(args.sql_filename)
        yield db.create_database()
        server = Server(db)
        yield server.load_subscriptions()
        add_service(s)
    except Exception as e:
        log.exception(e)

if __name__ == '__main__':
    launch(main)
    eventloop.run()
