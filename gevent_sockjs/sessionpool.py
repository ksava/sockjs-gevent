import uuid
import gevent

from heapq import heappush, heappop
from datetime import datetime, timedelta


class BaseSession(object):
    """
    A generic session, extend this or roll your own.
    """
    expires = timedelta(seconds=1)
    forever = False

    def __init__(self):
        self.expires_at = datetime.now() + self.expires
        self.expired = False
        self.session_id = self.generate_uid()

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

    def expire(self):
        """
        Manually expire a session.
        """
        self.expired = True
        self.forever = False

    def post_delete(self):
        pass


class SessionPool(object):
    """
    A garbage collected Session Pool.
    """
    gc_cycle = 2.0

    def __init__(self):
        self.sessions = dict()
        self.pool = []
        self.gcthread = gevent.Greenlet(self._gc_sessions)

    def start_gc(self):
        """
        Start the session pool garbage collector. This is broken
        out into a seperate function to give you more granular
        control on the context this thread is spawned in.
        """
        if not self.gcthread.started:
            self.gcthread.start()
            return self.gcthread
        else:
            print "Rejected attempt to start multiple garbage \
            collectors on SessionPool instance."

    def _gc_sessions(self):
        while True:
            gevent.sleep(self.gc_cycle)
            self.gc()

    def add(self, session):
        session.cycle = None
        self.sessions[session.session_id] = session

        if not session.expired:
            heappush(self.pool, session)

    def get(self, session_id):
        """
        Get active sessions by their session id.
        """
        session = self.sessions.get(session_id, None)

        if not session.expired:
            return session

    def remove(self, session_id):
        session = self.sessions.get(session_id, None)

        if session:
            session.post_delete()
            del self.sessions[session_id]

    def shutdown(self):
        """
        Manually expire all sessions in the pool.
        """
        while self.pool:
            head = heappop(self.pool)
            head.expired = True

    def __del__(self):
        """
        On Python interpreter garbage collection expire all sessions, not
        guaranteed to run!
        """
        self.shutdown()

    def gc(self):
        """
        Rearrange the heap flagging active sessions with the id
        of this collection iteration. This data-structure is
        time-independent so we sessions can be added to and from
        without the need to lock the pool.
        """

        if len(self.pool) == 0:
            return

        current_time = datetime.now()

        while self.pool:
            head = self.pool[0]

            # Every session is fresh
            if head.cycle == current_time or head.expires_at > current_time:
                break

            head = heappop(self.pool)

            # Flag the session with the id of this GC cycle
            head.cycle = current_time

            # Session is to be GC'd immedietely
            if head.expired:
                del self.sessions[head.session_id]
                head.post_delete()
                continue

            if not head.forever and head.expires_at < current_time:
                del self.sessions[head.session_id]
                head.post_delete()
            else:
                heappush(self.pool, head)
