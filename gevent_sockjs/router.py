import re
import transports
import static

from errors import *

# Route Tables
# ============

class RegexRouter(object):
    """
    A hybrid hash table, regex matching table.

    Tries to do O(1) hash lookup falls back on
    worst case O(n) regex matching.
    """
    _re = []
    _dct = {}

    def __init__(self, dct):
        for k, v in dct.iteritems():
            try:
                self._re.append((re.compile(k),v))
            except:
                pass
            self._dct[k] = v

    def __getitem__(self, k):
        if self._dct.has_key(k):
            return self._dct[k]
        else:
            for r, v in self._re:
                if r.match(k):
                    return v
        raise KeyError(k)

static_routes = RegexRouter({
    None                       : static.Greeting,
    'info'                     : static.InfoHandler,
    r'iframe[0-9-.a-z_]*.html' : static.IFrameHandler,
})


dynamic_routes = {

     # Ajax Tranports
     # ==============
    'xhr'           : transports.XHRPolling,
    'xhr_send'      : transports.XHRSend,
    'xhr_streaming' : transports.XHRStreaming,
    'jsonp'         : transports.JSONPolling,
    'jsonp_send'    : transports.JSONPSend,

    # WebSockets
    # ===============
    'websocket'     : transports.WebSocket,
    'rawwebsocket'  : transports.RawWebSocket,

    # File Transports
    # ===============
    'eventsource'   : transports.EventSource,
    'htmlfile'      : transports.HTMLFile,
    'iframe'        : transports.IFrame,
}

class SockJSConnection(object):

    disallowed_transports = tuple()

    def __init__(self, session):
        self.session = session

    @classmethod
    def transport_allowed(cls, transport):
        return transport not in cls.disallowed_transports

    # Event Callbacks
    # ===============

    def on_open(self, request):
        pass

    def on_message(self, message):
        raise NotImplementedError()

    def on_close(self):
        pass

    def on_error(self, exception):
        raise NotImplementedError()

    # Server side actions
    # ===================

    def send(self, message):
        if self.session:
            self.session.add_message(message)
        else:
            raise Exception("Tried to send message over closed session")

    def broadcast(self, channel, message):
        raise NotImplementedError()

    def close(self):
        if self.session:
            self.session.interrupt()
        else:
            raise Exception("Tried to close closed session")

class SockJSRouter(object):

    routes = {}

    def __init__(self, applications):
        """
        Set up the routing table for the specific routes attached
        to this server.
        """
        for route, connection in applications.iteritems():
            self.routes[route] = connection

    def route_static(self, route, suffix):
        try:
            route_handle = self.routes[route]
        except:
            raise Http404('No such route')

        try:
            handle_cls = static_routes[suffix]
        except KeyError:
            raise Http404('No such static page ' + str(suffix))

        return handle_cls(route_handle)

    def route_dynamic(self, route, session_uid, server, transport):
        """
        Return the downlink transport to the client resulting
        from request.
        """

        try:
            conn_cls = self.routes[route]
        except:
            raise Http500('No such route')

        try:
            transport_cls = dynamic_routes[transport]
        except:
            raise Http500('No such transport')

        if transport_cls.direction == 'send':
            create_if_null = False
        elif transport_cls.direction in ('recv', 'bi'):
            create_if_null = True
        else:
            raise Exception('Could not determine direction')

        session = self.server.get_session(session_uid, \
            create_if_null)

        if not session:
            raise Http404()

        # Initialize the transport and call, any side-effectful
        # code is the __init__ method, the communication is
        # invoked by __call__ method.

        conn = conn_cls(session)
        downlink = transport_cls(session, conn)

        if session.is_new:
            conn.on_open(session)
            session.timeout.rawlink(lambda g: conn.on_close())

        return downlink

    def __call__(self, environ, start_response):
        raise NotImplemented()
