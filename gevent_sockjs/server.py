from weakref import WeakValueDictionary
from gevent.pywsgi import WSGIServer

from gevent_sockjs import session
from gevent_sockjs.handler import SockJSHandler


class SockJSServer(WSGIServer):

    session_backend = session.MemorySession
    handler_class = SockJSHandler

    def __init__(self, *args, **kwargs):
        super(SockJSServer, self).__init__(*args, **kwargs)

        # Use weakrefs so that we don't not GC sessions purely
        # from their references in this session container
        self.sessions = WeakValueDictionary()

        self.namespace = kwargs.get('namespace', '__sockjs__')
        if not self.namespace.startswith('/'):
            self.namespace = '/%s'%self.namespace

    def flush_session(self, lid):
        del self.sessions[lid]

    def get_session(self, session_id='', create_if_null=False):
        """Return an existing or new client Session."""

        # TODO: assert session_id has sufficent entropy
        #assert len(session_id) > 3

        # Is it an existing session?
        session = self.sessions.get(session_id)

        # Otherwise let the client choose their session_id, if
        # this transport direction allows
        if create_if_null and session is None:

            session = self.session_backend(self, session_id)
            self.sessions[session_id] = session

        elif session:
            session.incr_hits()

        return session


if __name__ == '__main__':
    print 'Listening on port 8080'

    class Application(object):
        urls = {}

        def __init__(self):
            self.buffer = []

        def __call__(self, environ, start_response):
            start_response('404 NOT FOUND', [])
            return ['404 Error: Page not found']

    SockJSServer(('', port), Application()).serve_forever()
