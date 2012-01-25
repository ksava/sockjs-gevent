import session
from handler import SockJSHandler
from router import SockJSRouter, SockJSConnection
from sessionpool import SessionPool

from gevent.pywsgi import WSGIServer

class SockJSServer(WSGIServer):

    session_backend = session.MemorySession
    handler_class = SockJSHandler

    def __init__(self, *args, **kwargs):
        self.trace = kwargs.pop('trace', False)

        super(SockJSServer, self).__init__(*args, **kwargs)
        self.session_pool = SessionPool()
        self.session_pool.start_gc()

        # hack to get the server inside the router
        self.application.server = self

    def kill(self):
        super(SockJSServer, self).kill()
        self.session_pool.shudown()

    def del_session(self, uid):
        del self.sessions[uid]

    def get_session(self, session_id='', create_if_null=False):
        """
        Return an existing or new client Session.
        """

        # TODO: assert session_id has sufficent entropy
        #assert len(session_id) > 3

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

def devel_server():
    """
    A local server with code reload. Should only be used for
    development.
    """

    class Echo(SockJSConnection):

        def on_message(self, message):
            pass

    class DisabledWebsocket(SockJSConnection):

        disallowed_transports = ('websocket',)

        def on_message(self, message):
            pass

    class Close(SockJSConnection):

        disallowed_transports = ()

        def on_open(self, session):
            session.kill()

        def on_message(self, message):
            pass

    import gevent.monkey
    gevent.monkey.patch_all()

    # Need to moneky patch the threading module to
    # use greenlets
    import werkzeug.serving

    @werkzeug.serving.run_with_reloader
    def runServer(*args):

        router = SockJSRouter({
            'echo': Echo,
            'close': Close,
            'disabled_websocket_echo': DisabledWebsocket,
        })

        try:
            sockjs = SockJSServer(('',8081), router, trace=True)
            sockjs.serve_forever()
        except KeyboardInterrupt:
            sockjs.kill()

if __name__ == '__main__':
    devel_server()
