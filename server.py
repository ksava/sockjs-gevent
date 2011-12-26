import re
import datetime
from weakref import WeakValueDictionary

import gevent
from gevent.pywsgi import WSGIServer
from gevent.pywsgi import WSGIHandler
from geventwebsocket.handler import WebSocketHandler

import transports
import protocol
import session

handler_types = {
    'websocket'  : transports.WebSocketTransport,

    'xhr'        : transports.XHRPollingTransport,
    'xhr_send'   : transports.XHRPollingTransport,

    'jsonp'      : transports.JSONPolling,
    'jsonp_send' : transports.JSONPolling,

    'htmlfile'   : transports.HTMLFileTransport,
    'iframe'     : transports.IFrameTransport,
}

def toplevel(prefix, s):
    return re.compile('^' + prefix + s + '[/]?$')

def sessioned(prefix, s):
    return toplevel(prefix, '/([^/.]+)/([^/.]+)' + s)

class Router(object):

    base_url = '/echo'

    # Greeting ( terminating match )
    # ------------------------------
    greeting_re    = toplevel(base_url, '')

    # Greeting ( terminating match )
    is_iframe      = toplevel(base_url  ,'/iframe[0-9-.a-z_]*.html')
    is_xhr         = sessioned(base_url , '/xhr')
    is_xhr_send    = sessioned(base_url , '/xhr_send')

    def __init__(self, prefix):
        self.base_url = prefix

    def urls(self):
        return self._urls

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
        self.socketio_connection = False
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
        self.start_response('404 NOT FOUND', [])
        return ['404 Error: Page not found']

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
               # 404
               return super(SockJSHandler, self).handle_one_response()

        # Is it even a valid url?
        if not url_tokens:
            return super(SockJSHandler, self).handle_one_response()

        if session_uid:
            # Ensure the session identifier is actually alphanumeric
            if self.SESSION_RE.match(session_uid):
                session = self.server.get_session(session_uid)
            else:
                return super(SockJSHandler, self).handle_one_response()
        else:
            # not a session, greeting, or iframe so 404
            return super(SockJSHandler, self).handle_one_response()

        # Websockets are a special case... since we need to
        # context switch over to a new Handler
        if transport == 'websocket':
            self.__class__ = WebSocketHandler
            self.handle_one_response()

        # Do we have a transport?
        if transport:
            transport_cls = handler_types.get(transport, False)
        else:
            return super(SockJSHandler, self).handle_one_response()

        # Do we have a handler for that transport?
        if transport_cls:
            self.transport = transport_cls(self)
        else:
            return super(SockJSHandler, self).handle_one_response()

        async_calls = self.transport.connect(session, request_method, transport)
        gevent.joinall(async_calls)

class SockJSServer(WSGIServer):

    session_backend = session.MemorySession

    def __init__(self, *args, **kwargs):

        # Use weakrefs so that we don't not GC sessions purely
        # from their references in this session container
        self.sessions = WeakValueDictionary()

        self.namespace = kwargs.pop('namespace')

        kwargs['handler_class'] = SockJSHandler

        super(SockJSServer, self).__init__(*args, **kwargs)

    def start_accepting(self):
        super(SockJSServer, self).start_accepting()

    def kill(self):
        super(SockJSServer, self).kill()

    def handle(self, socket, address):
        handler = self.handler_class(socket, address, self)
        handler.handle()

    def flush_session(self, lid):
        del self.sessions[lid]

    def get_session(self, session_id=''):
        """Return an existing or new client Session."""

        # TODO: assert session_id has sufficent entropy
        #assert len(session_id) > 3

        # Is it an existing session?
        session = self.sessions.get(session_id)

        # Otherwise let the client choose their session_id
        if session is None:
            session = self.session_backend(self, session_id)

            self.sessions[session_id] = session
        else:
            session.incr_hits()

        return session

class Application(object):
    urls = {}

    def __init__(self):
        self.buffer = []

    def __call__(self, environ, start_response):
        #path = environ['PATH_INFO'].strip('/')

        start_response('404 NOT FOUND', [])
        return ['404 Error: Page not found']

if __name__ == '__main__':
    print 'Listening on port 8080'
    SockJSServer(('', 8081), Application(), namespace="socket.io").serve_forever()
