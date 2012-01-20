import uuid

import gevent

from gevent.queue import Queue
from gevent.event import Event


class Session(object):
    """
    Base class for Session objects. Provides for different
    backends for queueing messages for sessions.

    Subclasses are expected to overload the add_message and
    get_messages to reflect their storage system.
    """

    def __str__(self):
        result = ['session_id=%r' % self.session_id]

        if self.connected:
            result.append('connected')
        else:
            result.append('disconnected')

        if self.queue.qsize():
            result.append('queue[%s]' % self.queue.qsize())
        if self.hits:
            result.append('hits=%s' % self.hits)
        if self.heartbeats:
            result.append('heartbeats=%s' % self.heartbeats)

        return ' '.join(result)

    def incr_hits(self):
        self.hits += 1

        if self.hits > 0:
            self.connected = True

        self.clear_disconnect_timeout()

    def is_new(self):
        return self.hits == 0

    def clear_disconnect_timeout(self):
        self.timeout.set()

    def heartbeat(self):
        self.clear_disconnect_timeout()
        self.heartbeats += 1
        return self.heartbeats

    def add_message(self, msg):
        raise NotImplemented()

    def get_messages(self, **kwargs):
        raise NotImplemented()

    def kill(self):
        raise NotImplemented()


class MemorySession(Session):
    """
    In memory session with a outgoing gevent Queue as the message
    store.
    """

    timer = 10.0

    def __init__(self, server, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.server = server

        self.queue = Queue()

        self.hits = 0
        self.heartbeats = 0
        self.connected = False
        self.timeout = Event()

        self.wsgi_app_greenlet = None
        self.sent_connected = False

        def disconnect_timeout():
            self.timeout.clear()

            if self.timeout.wait(self.timer):
                gevent.spawn(disconnect_timeout)
            else:
                self.server.flush_session(self.session_id)
                self.kill()

        gevent.spawn(disconnect_timeout)

    def add_message(self, msg):
        self.clear_disconnect_timeout()
        self.queue.put_nowait(msg)

    def get_messages(self, **kwargs):
        return self.queue.get(**kwargs)

    def kill(self):
        if self.connected:
            self.connected = False
        else:
            pass


#class RedisSession(Session):
    #pass
