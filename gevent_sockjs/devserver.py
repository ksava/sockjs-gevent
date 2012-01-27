import gevent.monkey
gevent.monkey.patch_all()

from server import SockJSServer
from router import SockJSRouter, SockJSConnection

# Need to moneky patch the threading module to
# use greenlets
import werkzeug.serving

class Echo(SockJSConnection):

    def on_message(self, message):
        self.send(message)


class DisabledWebsocket(SockJSConnection):

    disallowed_transports = ('websocket',)

    def on_message(self, message):
        pass


class Close(SockJSConnection):

    disallowed_transports = ()

    def on_open(self, session):
        self.close()

    def on_message(self, message):
        pass


router = SockJSRouter({
    'echo': Echo,
    'close': Close,
    'disabled_websocket_echo': DisabledWebsocket,
})

@werkzeug.serving.run_with_reloader
def devel_server():
    """
    A local server with code reload. Should only be used for
    development.
    """

    try:
        sockjs = SockJSServer(('',8081), router, trace=True)
        sockjs.serve_forever()
    except KeyboardInterrupt:
        sockjs.kill()

if __name__ == '__main__':
    devel_server()
