import transports
from errors import Http404, Http500

route_table = {

     # Ajax Tranports
     # ==============
    'xhr'           : transports.XHRPolling,
    'xhr_send'      : transports.XHRSend,
    'xhr_streaming' : transports.XHRSend,
    'jsonp'         : transports.JSONPolling,
    'jsonp_send'    : transports.JSONPolling,

    # WebSockets
    # ===============
    'websocket'    : transports.WebSocket,

    # File Transports
    # ===============
    'eventsource'   : transports.HTMLFile,
    'htmlfile'      : transports.HTMLFile,
    'iframe'        : transports.IFrame,

}

class SockJSRoute(object):

    allowed_transports = []

    def __init__(self):
        self.allowed = set(self.allowed_transports)

    def transport_allowed(self, transport):
        return transport in self.allowed

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
            self.session.expire()
        else:
            raise Exception("Tried to close closed session")

class SockJSRouter(object):

    routes = {}

    def __init__(self, applications):
        """
        Set up the routing table for the specific routes attached
        to this server.
        """
        for route, server in applications.iteritems():
            self.routes[route] = server()

    def route(self, route, session_uid, server, transport):
        """
        Return the downlink transport to the client resulting
        from request.
        """

        route_handle = self.routes.get(route, None)

        if not route_handle:
            raise Http500()

        transport_cls = route_table.get(transport)

        session = self.server.get_session(session_uid, \
            create_if_null=True)

        # Initialize the transport and call, any side-effectful
        # code is the __init__ method, the communication is
        # invoked by __call__ method.

        downlink = transport_cls(session)
        downlink.on_message = route_handle.on_message

        if session.is_new:
            route_handle.on_open(session)
            session.timeout.rawlink(route_handle.on_close)

        return downlink
