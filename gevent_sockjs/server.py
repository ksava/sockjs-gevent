import session
from handler import SockJSHandler
from sessionpool import SessionPool

from gevent.pywsgi import WSGIServer

class SockJSServer(WSGIServer):
    """
    The base SockJS server, subclases gevent.pywsgi.WSGIServer
    """

    session_backend = session.MemorySession
    handler_class = SockJSHandler

    def __init__(self, *args, **kwargs):
        """
        Initialize the SockJS server

        Options:
            listener    : ( address, port )
            application : The SockJS router instance
            trace       : Show stack traces on 500 status code

        Example::
            sockjs = SockJSServer(('',8081), router)
            sockjs.serve_forever()

        """
        self.trace = kwargs.pop('trace', False)

        super(SockJSServer, self).__init__(*args, **kwargs)
        self.session_pool = SessionPool()
        self.session_pool.start_gc()

        # hack to get the server inside the router
        self.application.server = self

    def del_session(self, uid):
        del self.sessions[uid]

    def get_session(self, session_id='', create_if_null=False):
        """
        Return an existing or initialize a new session with the
        session id passed.
        """

        # Is it an existing session?
        session = self.session_pool.get(session_id)

        # Otherwise let the client choose their session_id, if
        # this transport direction allows
        if create_if_null and session is None:
            session = self.session_backend(self, session_id)
            self.session_pool.add(session)
        elif session:
            session.incr_hits()

        return session

    def kill(self):
        """
        Shutdown the server, block to inform the sessions that
        they are closing.
        """
        self.session_pool.shudown()
        super(SockJSServer, self).kill()
