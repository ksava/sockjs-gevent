import weakref
import transports

handler_types = {
    'websocket'  : ('bi', transports.WebSocketTransport),

    'xhr'        : ('recv', transports.XHRPollingTransport),
    'xhr_send'   : ('send', transports.XHRPollingTransport),

    'jsonp'      : ('recv', transports.JSONPolling),
    'jsonp_send' : ('send', transports.JSONPolling),

    'htmlfile'   : ('recv', transports.HTMLFileTransport),
    'iframe'     : ('recv', transports.IFrameTransport),
}


class SockJSRoute(object):

    allowed_transports = []

    def __init__(self, session):
        self.session = weakref.ref(session)
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
        for route, server in applications.iteritems():
            self.routes[route] = server

    def route(self, route, session_uid, server, transport):

        direction, transport_cls = handler_types.get(transport)

        create_if_null = direction in ('bi', 'recv')
        session = self.server.get_session(session_uid, create_if_null)

        route_handle = self.routes.get(route, None)

        if not route:
            raise Exception("No Route")

        #if route.transport_allowed(transport):
            #return route

        return session
