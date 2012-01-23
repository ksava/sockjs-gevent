import gevent
from gevent.queue import Empty

import protocol

class BaseTransport(object):

    def __init__(self, session, conn):
        self.session = session
        self.conn = conn

    def encode(self, data):
        return protocol.encode(data)

    def decode(self, data):
        return protocol.decode(data)

    def __call__(self, handler, request_method, raw_request_data):
        """
        Downlink function, action taken as a result of the
        specified route.
        """
        raise NotImplemented()

# Receiving Transports
# ====================
#
# Recieve messages from the client, provide them to the session
# object and its callbacks, provide confirmation of any actions
# taken per protocol.

class XHRSend(BaseTransport):
    direction = 'send'

    def __call__(self, handler, request_method, raw_request_data):
        messages = self.decode(raw_request_data)
        #self.on_message(messages)

        for msg in messages:
            self.session.add_message(messages)

        handler.content_type = ("Content-Type", "text/html; charset=UTF-8")
        handler.start_response("204 NO CONTENT", [])
        handler.write_nothing()

        return []

class JSONPSend(BaseTransport):
    direction = 'recv'

    def __call__(self, handler, request_method, raw_request_data):
        messages = self.decode(raw_request_data)

        for msg in messages:
            self.session.add_message(messages)

        self.handler.content_type = ("Content-Type", "text/html; charset=UTF-8")
        self.handler.start_response("204 NO CONTENT", [])
        self.handler.write_nothing()

        return []


class PollingTransport(BaseTransport):
    """
    Long polling derivative transports, used for XHRPolling and
    JSONPolling.

    Subclasses overload the write_frame method for their
    respective serialization methods.
    """
    direction = 'recv'

    TIMING = 5.0

    def write_frame(self, frame, data):
        raise NotImplemented()

    def options(self):
        self.start_response("200 OK", [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Credentials", "true"),
            ("Access-Control-Allow-Methods", "POST, GET, OPTIONS"),
            ("Access-Control-Max-Age", 3600),
            ("Connection", "close"),
            ("Content-Length", 0)
        ])
        self.handler.write_text('')

    def get(self, session, action):
        """
        Spin lock the thread until we have a message on the
        gevent queue.
        """
        try:
            messages = session.get_messages(timeout=self.TIMING)
            messages = self.encode(messages)
        except Empty:
            messages = "[]"

        self.start_response("200 OK", [
            ("Access-Control-Allow-Origin", "*"),
            ("Connection", "close"),
            self.content_type,
        ])

        self.write(protocol.message_frame(messages))

    def connect(self, session, request_method, action):
        """
        Initial starting point for this handler's thread,
        delegates to another method depending on the session,
        request method, and action.
        """
        if session.is_new():
            #self.write(protocol.OPEN)
            self.handler.write_text(protocol.OPEN)
            return

        if request_method == "GET":
            session.clear_disconnect_timeout();
            self.get(session, action)

        elif request_method == "POST":
            return self.post(session, action)

        elif request_method == "OPTIONS":
            return self.options()

        else:
            raise Exception("No support for such method: " + request_method)

# Polling Transports
# ==================
#
# Poll for new messages on the server.

class XHRPolling(PollingTransport):

    direction = 'recv'

    TIMING = 2
    content_type = ("Content-Type", "text/html; charset=UTF-8")

    def poll(self, handler):
        """
        Spin lock the thread until we have a message on the
        gevent queue.
        """

        try:
            messages = self.session.get_messages(timeout=self.TIMING)
            messages = self.encode(messages)
        except Empty:
            messages = "[]"

        handler.start_response("200 OK", [
            ("Access-Control-Allow-Origin", "*"),
            ("Connection", "close"),
            self.content_type,
        ])

        handler.write_text(protocol.message_frame(messages))

    def __call__(self, handler, request_method, raw_request_data):
        """
        On the first poll, send back the open frame, one
        subsequent calls actually poll the queue.
        """
        if self.session.is_new():
            handler.write_text(protocol.OPEN)
            return []
        else:
            return [gevent.spawn(self.poll, handler)]

class XHRStreaming(PollingTransport):
    direction = 'recv'
    pass

class JSONPolling(PollingTransport):
    direction = 'recv'
    pass

class HTMLFile(BaseTransport):
    pass

class IFrame(BaseTransport):
    pass

class EventSource(BaseTransport):
    pass

class WebSocket(BaseTransport):
    pass
