import uuid

from gevent.queue import Queue, Empty
from gevent.event import Event

from datetime import datetime, timedelta

class Session(object):
    """
    Base class for Session objects. Provides for different
    backends for queueing messages for sessions.

    Subclasses are expected to overload the add_message and
    get_messages to reflect their storage system.
    """

    # Session's timeout after 5 seconds
    expires = timedelta(seconds=5)

    def __init__(self, server, session_id=None):
        self.expires_at = datetime.now() + self.expires
        self.expired = False
        self.forever = False
        self.session_id = self.generate_uid()

        # Whether this was closed explictly by client vs
        # internally by garbage collection.
        self.interrupted = False

        # When a polling request is closed by a network error - not by
        # server, the session should be automatically closed. When there
        # is a network error - we're in an undefined state. Some messages
        # may have been lost, there is not much we can do about it.
        self.network_error = False

        # Async event, use rawlink to string callbacks
        self.timeout = Event()
        self.locked = Event()

    def generate_uid(self):
        """
        Returns a string of the unique identifier of the session.
        """
        return str(uuid.uuid4())

    def persist(self, extension=None, forever=False):
        """
        Bump the time to live of the session by a given amount,
        or forever.
        """
        self.expired = False

        if forever:
            self.forever = True
            return

        # Slide the expirtaion time one more expiration interval
        # into the future
        if extension is None:
            self.expires_at = datetime.now() + self.expires
        else:
            self.expires_at = datetime.now() + extension

        self.forever = False

    def post_delete(self):
        pass

    def kill(self):
        self.killed = True
        self.expire()

    def expire(self):
        """
        Manually expire a session.
        """
        self.expired = True
        self.forever = False

    def incr_hits(self):
        self.hits += 1

    def is_new(self):
        return self.hits == 0

    def heartbeat(self):
        self.persist()
        self.heartbeats += 1
        return self.heartbeats

    def add_message(self, msg):
        raise NotImplemented()

    def get_messages(self, **kwargs):
        raise NotImplemented()

    def is_locked(self):
        return self.locked.is_set()

    def is_network_error(self):
        return self.network_error

    def is_expired(self):
        return self.expired

    def is_interrupted(self):
        return self.interrupted

    def lock(self):
        self.locked.set()

    def unlock(self):
        self.locked.clear()

    def __str__(self):
        pass

class MemorySession(Session):
    """
    In memory session with a outgoing gevent Queue as the message
    store.
    """

    timer = 10.0

    def __init__(self, server, session_id=None):
        super(MemorySession, self).__init__(server, session_id)
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.server = server

        self.queue = Queue()

        self.hits = 0
        self.heartbeats = 0
        self.connected = False

    def add_message(self, msg):
        self.queue.put_nowait(msg)

    def get_messages(self, **kwargs):
        self.incr_hits()

        if self.queue.empty():
            try:
                return self.queue.get(**kwargs)
            except Empty:
                return []
        else:
            accum = []
            try:
                while not self.queue.empty():
                    accum.append(self.queue.get_nowait())
            finally:
                return accum

    def interrupt(self):
        """
        A kill event trigged through a client accessible endpoint

        Internal expires will not have is_interupted() == True
        """
        self.interrupted = True
        self.kill()

    def kill(self):
        self.connected = False

        # Expire only once
        if not self.expired:
            self.expired = True
            self.timeout.set()
