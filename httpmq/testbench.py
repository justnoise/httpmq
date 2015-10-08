import time
# start up server
# remove all users from table
import requests

host = "localhost"
port = 8888

def make_url(*args):
    return "/".join(["http://{}:{}".format(host, port)] + list(args))

def subscribe(topic, username):
    return requests.post(make_url(topic, username))

def publish(topic, msg):
    return requests.post(make_url(topic), data=msg)

def retrieve(topic, username):
    return requests.get(make_url(topic, username))

def unsubscribe(topic, username):
    return requests.delete(make_url(topic, username))

def check(result, expected_code, expected_text=None):
    print result, expected_code
    msg = "{} != {}".format(result.status_code, expected_code)
    assert result.status_code == expected_code, msg
    if expected_text:
        msg = "{} != {}".format(result.text, expected_text)
        assert result.text == expected_text, msg

def correctness():
    check(publish("t1", "t1m0"), 200)
    check(subscribe("t1", "u1"), 200)
    check(subscribe("t1", "u2"), 200)
    check(subscribe("t1", "u3"), 200)
    check(subscribe("t2", "u1"), 200)
    check(subscribe("t2", "u2"), 200)
    check(publish("t1", "t1m1"), 200)
    check(publish("t1", "t1m2"), 200)
    check(publish("t1", "t1m3"), 200)
    check(publish("t2", "t2m1"), 200)
    check(publish("t2", "t2m2"), 200)
    check(retrieve("t1", "u1"), 200, "t1m1")
    check(retrieve("t1", "u2"), 200, "t1m1")
    check(unsubscribe("t1", "u2"), 200)
    check(unsubscribe("t1", "u2"), 404)
    check(subscribe("t1", "u2"), 200)
    check(retrieve("t1", "u2"), 204)
    check(publish("t1", "t1m4"), 200)
    check(retrieve("t1", "u2"), 200, "t1m4")
    check(retrieve("t1", "u2"), 204)
    check(retrieve("t2", "u2"), 200, "t2m1")
    check(retrieve("t1", "u3"), 200, "t1m1")
    check(retrieve("t2", "u3"), 404)
    print "OK"

def speed(num_msgs):
    check(subscribe("t1", "u1"), 200)
    check(subscribe("t1", "u2"), 200)
    check(subscribe("t1", "u3"), 200)
    check(subscribe("t1", "u4"), 200)
    start = time.time()
    for x in xrange(num_msgs):
        msg = str(x)
        check(subscribe("t1", "u4"), 200)
        check(publish("t1", msg), 200)
        check(retrieve("t1", "u1"), 200, msg)
        check(retrieve("t1", "u2"), 200, msg)
        check(retrieve("t1", "u3"), 200, msg)
        check(retrieve("t1", "u4"), 200, msg)
    end = time.time()
    print "{} messages: {}s".format(num_msgs, end - start)
    msgs_per_sec = (num_msgs * 5)/(end-start)
    print "{} operations/sec".format(msgs_per_sec)

if __name__ == "__main__":
    #correctness_test()
    speed(100)
