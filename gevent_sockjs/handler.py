import re
import datetime

import gevent
from gevent.pywsgi import WSGIHandler
from geventwebsocket.handler import WebSocketHandler

import protocol
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

class SockJSHandler(WSGIHandler):
    """
    Basic request handling.
    """

    # Sessioned urls
    URL_FORMAT = re.compile(r"""
        ^/(?P<route>[^/]+)/        # sockjs route, alphanumeric not empty
        (?P<server_id>[^/.]+)/     # load balancer id, alphanumeric not empty, without (.)
        (?P<session_id>[^/.]+)/    # session id, alphanumeric not empty, without (.)
        (?P<transport>[^/.]+)$     # transport string, (Example: xhr | jsonp ... )
        """
    , re.X)

    # Topelevel urls
    GREETING_RE = re.compile(r"^/(?P<route>[^/]+)/?$")
    IFRAME_RE = re.compile(r"^/(?P<route>[^/]+)/iframe[0-9-.a-z_]*.html")

    # Regex tester for valid session ids, provides string sanity
    # check
    SESSION_RE = re.compile(r"^((?!\.).)*$")

    def __init__(self, *args, **kwargs):
        super(SockJSHandler, self).__init__(*args, **kwargs)

    # Raw write actions
    # -----------------

    def write_text(self, text):
        self.content_type = ("Content-Type", "text/plain; charset=UTF-8")

        self.headers += [self.content_type]
        self.start_response("200 OK", self.headers)

        if 'Content-Length' not in self.response_headers_list:
            self.response_headers.append(('Content-Length', len(text)))
            self.response_headers_list.append('Content-Length')

        self.write(text)

    def write_html(self, html):
        self.content_type = ("Content-Type", "text/html; charset=UTF-8")

        self.headers += [self.content_type]
        self.start_response("200 OK", self.headers)

        if 'Content-Length' not in self.response_headers_list:
            self.response_headers.append(('Content-Length', len(html)))
            self.response_headers_list.append('Content-Length')

        self.write(html)

    def write_nothing(self):
        self.start_response("204 NO CONTENT", self.headers)
        self.write(None)

    def greeting(self):
        self.write_text('Welcome to SockJS!\n')

    def do404(self):
        """
        Let the vanilla WSGIHandler deal with the 404.
        """
        return super(SockJSHandler, self).handle_one_response()

    def enable_caching(self):
        d = datetime.datetime.now() + datetime.timedelta(days=365)
        s = datetime.timedelta(days=365).total_seconds()

        self.headers += [
            ('Cache-Control', 'max-age=%d, public' % s),
            ('Expires', d.strftime('%a, %d %b %Y %H:%M:%S')),
            ('access-control-max-age', s),
        ]

    def serve_iframe(self):
        cached = self.environ.get('HTTP_IF_NONE_MATCH')

        # TODO: check this is equal to our MD5
        if cached:
            self.start_response("304 NOT MODIFIED", self.headers)
            self.write(None)
            return

        self.content_type = ("Content-Type", "text/html; charset=UTF-8")
        self.headers += [
            ('ETag', protocol.IFRAME_MD5),
            self.content_type
        ]
        self.enable_caching()

        self.start_response("200 OK", self.headers)

        # TODO: actually put this in here
        html = protocol.IFRAME_HTML % ('http',)

        if 'Content-Length' not in self.response_headers_list:
            self.response_headers.append(('Content-Length', len(html)))
            self.response_headers_list.append('Content-Length')

        self.write(html)

    def handle_one_response(self):
        self.headers = []
        self.status = None
        self.headers_sent = False
        self.result = None
        self.response_length = 0
        self.response_use_chunked = False

        path = self.environ.get('PATH_INFO')

        url_tokens = self.URL_FORMAT.match(path)

        request_method = self.environ.get("REQUEST_METHOD")
        print request_method, path

        # For debugging sessions
        if 'info' in path:
            self.write_html(str(map(str,self.server.sessions.values())))
            return

        # A sessioned call
        if url_tokens:
            url_tokens = url_tokens.groupdict()

            session_uid = url_tokens['session_id']
            server = url_tokens['server_id']
            transport = url_tokens['transport']

        # A toplevel call
        else:
            session = None
            server = None
            transport = None

            if self.GREETING_RE.match(path):
                return self.greeting()
            elif self.IFRAME_RE.match(path):
                self.serve_iframe()

            # A completely invalid url
            else:
                return self.do404()

        # Lookup the direction of the transport and its
        # associated handler
        direction, _ = handler_types.get(transport, (False,False))

        # Is it even a valid url?
        if not url_tokens:
            return self.do404()

        # Did we get a session identifier in the url?
        if session_uid:

            # Ensure the session identifier is actually alphanumeric
            if self.SESSION_RE.match(session_uid):
                # If the user tries to poll on a recv url, then
                # let them create a session if it doesn't yet
                # exist.
                create_if_null = direction == 'bi' or direction == 'recv'

                session = self.server.get_session(session_uid, \
                    create_if_null)

                # Otherwise 404 them since they're trying to poll
                # on a non-existent session.
                if not session:
                    return self.do404()

            else:
                return self.do404()

        else:
            # not a session, greeting, or iframe so 404
            return self.do404()

        # Websockets are a special case... since we need to
        # context switch over to the WebSocketHandler
        if transport == 'websocket':
            self.__class__ = WebSocketHandler
            self.handle_one_response()

        # Do we have a transport?
        if transport:
            direction, transport_cls = handler_types.get(transport, (False,False))
        else:
            return self.do404()

        # Do we have a handler for that transport?
        if transport_cls:
            self.transport = transport_cls(self)
        else:
            return self.do404()

        async_calls = self.transport.connect(session, request_method, transport)
        gevent.joinall(async_calls)
