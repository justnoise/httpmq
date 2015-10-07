import logging
import sqlite3
from twisted.enterprise import adbapi
import monocle
from monocle import _o, Return, launch
monocle.init("twisted")
from monocle.stack import eventloop

log = logging.getLogger(__name__)


class SubscriptionDb(object):
    def __init__(self, filename):
        self.db = adbapi.ConnectionPool(
            "sqlite3", filename, check_same_thread=False)

    @_o
    def create_database(self):
        log.info("creating subscription database")
        qry = """create table if not exists subscription
        (topic varchar(1024),
        username varchar(1024),
        primary key (topic, username))"""
        yield self.db.runQuery(qry)

    @_o
    def add_subscription(self, topic, username):
        qry = "insert into subscription values (?, ?)"
        try:
            yield self.db.runQuery(qry, (topic, username))
        except sqlite3.IntegrityError as e:
            log.warn("not adding duplicate row: %s|%s", topic, username)
        except Exception as e:
            log.exception(e)

    @_o
    def remove_subscription(self, topic, username):
        qry = """delete from subscription where
        topic = ?
        and username = ?"""
        try:
            yield self.db.runQuery(qry, (topic, username))
        except Exception as e:
            log.exception(e)

    @_o
    def get_subscriptions(self):
        qry = "select topic, username from subscription"
        results = yield self.db.runQuery(qry)
        yield Return(results)

@_o
def test():
    db = SubscriptionDb(filename="test.sqlite")
    yield db.create_database()
    yield db.add_subscription("awesome", "bob")
    yield db.add_subscription("awesome", "bob")
    yield db.remove_subscription("awesome", "bob")
    yield db.add_subscription("awesome", "bob")
    subscriptions = yield db.get_subscriptions()
    print subscriptions


if __name__ == "__main__":
    launch(test)
    eventloop.run()
