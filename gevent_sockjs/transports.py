from gevent.queue import Empty

import protocol

class BaseTransport(object):

    def __init__(self, handler):
        self.content_type = ("Content-Type", "text/plain; charset=UTF-8")
        self.handler = handler

    def encode(self, data):
        return protocol.encode(data)

    def decode(self, data):
        return protocol.decode(data)

    def write(self, data):
        if data is None:
            length = 0
        else:
            length = len(data)

        if not self.handler.has_header('Content-Length'):
            self.handler.response_headers.append(('Content-Length', length))

        self.handler.write(data)

    def write_multipart(self, data):
        self.handler.write(data)

    def start_response(self, *args, **kwargs):
        self.handler.start_response(*args, **kwargs)


class PollingTransport(BaseTransport):
    """
    Long polling derivative transports, used for XHRPolling and
    JSONPolling.

    Subclasses overload the write_frame method for their
    respective serialization methods.
    """

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
        self.write('')

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

    def post(self, session, action):
        if action == 'xhr_send':
            data = self.handler.wsgi_input.readline()#.replace("data=", "")

            messages = self.decode(data)

            for msg in messages:
                session.add_message(messages)

            self.content_type = ("Content-Type", "text/html; charset=UTF-8")
            self.start_response("204 NO CONTENT", [])
            self.write(None)

        elif action == 'xhr':
            self.get(session, action)

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


class XHRPollingTransport(PollingTransport):
    pass


class JSONPolling(PollingTransport):
    pass


class HTMLFileTransport(BaseTransport):
    pass


class IFrameTransport(BaseTransport):
    pass


class WebSocketTransport(BaseTransport):

    def connect(self, session, request_method, action):
        pass
