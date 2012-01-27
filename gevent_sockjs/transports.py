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

        for msg in messages:
            self.conn.on_message(msg)

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

        self.session.unlock()

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
        elif self.session.is_expired():
            close_error = protocol.close_frame(3000, "Go away!")
            handler.write_text(close_error)
            return []
        elif self.session.is_locked():
            lock_error = protocol.close_frame(2010, "Another connection still open")
            handler.write_text(lock_error)
            return []
        else:
            self.session.lock()
            return [gevent.spawn(self.poll, handler)]

class XHRStreaming(PollingTransport):
    direction = 'recv'

class JSONPolling(PollingTransport):
    direction = 'recv'

class HTMLFile(BaseTransport):
    direction = 'recv'

class IFrame(BaseTransport):
    direction = 'reccv'

class EventSource(BaseTransport):
    direction = 'send'

class WebSocket(BaseTransport):
    direction = 'bi'

    def poll(self, socket):
        """
        Spin lock the thread until we have a message on the
        gevent queue.
        """

        while not self.session.expired:
            messages = self.session.get_messages()
            messages = self.encode(messages)

            socket.send(protocol.message_frame(messages))

        close_error = protocol.close_frame(3000, "Go away!")
        socket.send(close_error)

        # Session expires, so unlock
        #self.session.unlock()

    def put(self, socket):

        while not self.session.expired:
            messages = socket.receive()

            for msg in messages:
                self.session.add_message(msg)

            self.session.incr_hits()

        # Session expires, so unlock
        #self.session.unlock()

    def __call__(self, socket, request_method, raw_request_data):

        socket.send('o')

        if self.session.is_expired():
            close_error = protocol.close_frame(3000, "Go away!")
            socket.send(close_error)
            socket.close()
            return []
        #elif self.session.is_locked():
            #lock_error = protocol.close_frame(2010, "Another connection still open")
            #socket.send(lock_error)
            #socket.close()
            #return []

        # Otherwise spin our threads.
        self.session.lock()
        return [
            gevent.spawn(self.poll, socket),
            gevent.spawn(self.put, socket),
        ]
