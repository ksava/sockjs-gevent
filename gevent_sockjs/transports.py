import socket
import gevent
import urllib2
import urlparse
from socket import error as socketerror

import protocol
from errors import *

from geventwebsocket.websocket import Closed, WebSocketError

class BaseTransport(object):

    def __init__(self, session, conn):
        self.session = session
        self.conn = conn

    def encode(self, data):
        """
        Wrapper around the protocol's frame encoding.
        """
        return protocol.encode(data)

    def decode(self, data):
        """
        Wrapper around the protocol's frame decoding.
        """
        return protocol.decode(data)

    def write_frame(self, data):
        """
        Write the data in a frame specifically for this
        transport. Deals with the edge cases of formatting the
        messages for the transports. Things like \n characters
        and Javascript callback frames.
        """
        raise NotImplemented()

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

        if request_method == 'OPTIONS':
            handler.write_options(['OPTIONS', 'POST'])
            return []

        if raw_request_data == '':
            handler.do500(message='Payload expected.')
            return

        try:
            messages = self.decode(raw_request_data)
        except InvalidJSON:
            handler.do500(message='Broken JSON encoding.')
            return

        for msg in messages:
            self.conn.on_message(msg)

        handler.content_type = ("Content-Type", "text/plain; charset=UTF-8")
        handler.headers = [handler.content_type]
        handler.enable_cookie()
        handler.enable_cors()

        handler.write_nothing()

        return []

class JSONPSend(BaseTransport):
    direction = 'recv'

    def __call__(self, handler, request_method, raw_request_data):

        if request_method == 'OPTIONS':
            handler.write_options(['OPTIONS', 'POST'])
            return []


        qs = urlparse.parse_qs(raw_request_data)

        using_formdata = True

        # Do we have a Payload?
        try:
            if qs.has_key('d'):
                using_formdata = True
                payload = qs['d']
            else:
                using_formdata = False
                payload = urllib2.unquote(raw_request_data)
        except Exception as e:
            handler.do500(message='Payload expected.')
            return

        # Confirm that this at least looks like a JSON array
        if not using_formdata:
            if not ('[' in payload and ']' in payload):
                handler.do500(message='Payload expected.')
                return

        try:
            if using_formdata:
                messages = self.decode(payload[0])
            else:
                messages = self.decode(payload)
        except InvalidJSON:
            handler.do500(message='Broken JSON encoding.')

        for msg in messages:
            self.conn.on_message(msg)

        handler.content_type = ("Content-Type", "text/plain; charset=UTF-8")
        handler.enable_cookie()
        handler.enable_nocache()
        handler.write_text('ok')

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

    def poll(self, handler):
        """
        Spin lock the thread until we have a message on the
        gevent queue.
        """
        messages = self.session.get_messages(timeout=self.TIMING)
        messages = self.encode(messages)

        self.session.unlock()

        handler.start_response("200 OK", [
            ("Access-Control-Allow-Origin", "*"),
            ("Connection", "close"),
            self.content_type,
        ])

        handler.write_text(self.write_frame(messages))

    def __call__(self, handler, request_method, raw_request_data):
        """
        On the first poll, send back the open frame, one
        subsequent calls actually poll the queue.
        """

        if request_method == 'OPTIONS':
            handler.write_options(['OPTIONS', 'POST'])
            return []

        if self.session.is_new():
            handler.enable_cookie()
            handler.enable_cors()
            handler.write_js(protocol.OPEN)
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

    def write_frame(self, data):
        raise NotImplemented()

# Polling Transports
# ==================
#
# Poll for new messages on the server.

class XHRPolling(PollingTransport):

    direction = 'recv'

    TIMING = 2
    content_type = ("Content-Type", "text/html; charset=UTF-8")

    def write_frame(self, data):
        return protocol.message_frame(data) + '\n'

class JSONPolling(PollingTransport):
    direction = 'recv'

    content_type = ("Content-Type", "text/plain; charset=UTF-8")

    def write_frame(self, data):
        frame = protocol.json.dumps(protocol.message_frame(data))
        return """%s(%s);\r\n""" % ( self.callback, frame)

    def __call__(self, handler, request_method, raw_request_data):

        try:
            callback_param = handler.environ.get("QUERY_STRING").split('=')[1]
            self.callback = urllib2.unquote(callback_param)
        except IndexError:
            handler.do500(message='"callback" parameter required')
            return

        if request_method == 'OPTIONS':
            handler.write_options(['OPTIONS', 'POST'])
            return []

        if self.session.is_new():
            handler.enable_nocache()
            handler.enable_cookie()
            handler.enable_cors()
            open_frame = '%s("o");\r\n' % self.callback

            handler.write_js(open_frame)
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

    TIMING = 2
    CUTOFF = 10240

    prelude = 'h' *  2048 + '\n'

    def poll(self, handler):
        """
        Spin lock the thread until we have a message on the
        gevent queue.
        """

        writer = handler.socket.makefile()
        written = 0

        try:
            while True:
                messages = self.session.get_messages(timeout=self.TIMING)
                messages = self.encode(messages)

                frame = protocol.message_frame(messages) + '\n'
                chunk = handler.raw_chunk(frame)

                writer.write(chunk)
                writer.flush()
                written += len(chunk)

                zero_chunk = handler.raw_chunk('')
                writer.write(zero_chunk)

                if written > self.CUTOFF:
                    zero_chunk = handler.raw_chunk('')
                    writer.write(zero_chunk)
                    break

        except socket.error:
            self.session.expire()

    def stream(self, handler):
        content_type = ("Content-Type", "application/javascript; charset=UTF-8")

        handler.enable_cookie()
        handler.enable_cors()

        # https://groups.google.com/forum/#!msg/sockjs/bl3af2zqc0A/w-o3OK3LKi8J
        if handler.request_version == 'HTTP/1.1':

            handler.headers += [
                content_type,
                ("Transfer-Encoding", "chunked"),
                ('Connection', 'keep-alive'),
            ]

        elif handler.request_version == 'HTTP/1.0':

            handler.headers += [
                content_type,
                ('Connection', 'close'),
            ]

        # Use very low level api here, since we want more granular
        # control over our response

        handler.start_response("200 OK", handler.headers)

        headers = handler.raw_headers()

        try:
            writer = handler.socket.makefile()
            writer.write(headers)
            writer.flush()

            prelude_chunk = handler.raw_chunk(self.prelude)
            open_chunk = handler.raw_chunk('o\n')

            writer.write(prelude_chunk)
            writer.write(open_chunk)

            writer.flush()
            writer.close()

        except socket.error:
            self.session.expire()

    def __call__(self, handler, request_method, raw_request_data):
        """
        """
        return [
            gevent.spawn(self.stream, handler),
            gevent.spawn(self.poll, handler),
        ]

class HTMLFile(BaseTransport):
    direction = 'recv'

class IFrame(BaseTransport):
    direction = 'recv'

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

        close_error = protocol.close_frame(3000, "Go away!", newline=False)
        socket.send(close_error)

        # Session expires, so unlock
        socket.close()
        self.session.unlock()

    def put(self, socket):

        wsprotocol = socket.protocol

        while not self.session.is_expired():
            try:
                messages = socket.receive() # blocking
            # geventwebsocket doesn't wrap these failure modes
            # into nice exceptions so we have to catch base Python
            # Exceptions. :(

            # Ignore invalid frames
            except ValueError:
                continue
            except TypeError:
                continue
            # Ignore empty frames
            except WebSocketError:
                continue
            # If the peer closes early then a fobj.read attribute
            # won't exist so ignore.
            except AttributeError:
                break
            #except socketerror:
                #break

            # Hybi = Closed
            # Hixie = None

            if isinstance(messages, Closed) or messages is None:
                break

            try:
                messages = protocol.decode(messages)
            except InvalidJSON:
                # When user sends broken data - broken JSON for example, the
                # server must terminate the ws connection.
                break

            for msg in messages:
                self.conn.on_message(msg)

            self.session.incr_hits()

        # Session expires, so unlock
        socket.close()
        self.session.unlock()
        self.session.expire()

    def __call__(self, socket, request_method, raw_request_data):

        socket.send('o')

        if self.session.is_expired():
            close_error = protocol.close_frame(3000, "Go away!", newline=False)
            socket.send(close_error)
            socket.close()
            return []
        #elif self.session.is_locked():
            #lock_error = protocol.close_frame(2010, "Another connection still open")
            #socket.send(lock_error)
            #socket.close()
            #return []

        self.session.lock()

        return [
            gevent.spawn(self.poll, socket),
            gevent.spawn(self.put, socket),
        ]

class RawWebSocket(BaseTransport):
    direction = 'bi'

    def poll(self, socket):

        while not self.session.is_expired():
            messages = self.session.get_messages()

            for message in messages:
                socket.send(message)

        socket.close()

    def put(self, socket):

        while not self.session.is_expired():
            # Just read atomic strings and do what the connection
            # wants.

            message = socket.receive() # blocking

            if isinstance(message, Closed) or message is None:
                break

            self.conn.on_message([message])

            self.session.incr_hits()

        socket.close()

    def __call__(self, socket, request_method, raw_request_data):

        if self.session.is_expired():
            socket.close()
            return []

        return [
            gevent.spawn(self.poll, socket),
            gevent.spawn(self.put, socket),
        ]
