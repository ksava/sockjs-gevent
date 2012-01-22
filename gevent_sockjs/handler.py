import sys
import re
import datetime
import time
import traceback
from gevent.pywsgi import WSGIHandler

import protocol

from errors import Http404, Http500

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


    # Raw write actions
    # -----------------

    def prep_response(self):
        self.time_start = time.time()
        self.status = None

        self.headers = []
        self.headers_sent = False

        self.result = None
        self.response_use_chunked = False
        self.response_length = 0

    def write_text(self, text):
        self.prep_response()
        self.content_type = ("Content-Type", "text/plain; charset=UTF-8")

        self.headers += [self.content_type]
        self.start_response("200 OK", self.headers)

        #self.write(text)
        self.result = [text]
        self.process_result()

    def write_html(self, html):
        self.prep_response()
        self.content_type = ("Content-Type", "text/html; charset=UTF-8")

        self.headers += [self.content_type]
        self.start_response("200 OK", self.headers)

        self.result = [html]
        self.process_result()

    def write_nothing(self):
        self.prep_response()
        self.start_response("204 NO CONTENT", self.headers)

        self.result = [None]
        self.process_result()

    def write_iframe(self):
        self.prep_response()
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
        self.result = [html]
        self.process_result()

    def greeting(self):
        self.write_text('Welcome to SockJS!\n')

    def do404(self):
        self.prep_response()

        self.content_type = ("Content-Type", "text/plain; charset=UTF-8")
        self.headers += [self.content_type]

        self.start_response("404 NOT FOUND", self.headers)
        self.result = ['404 Error: Page not found']
        self.process_result()

        self.time_finish = time.time()
        self.log_request()

    def do500(self, stacktrace=None):
        """
        Handle 500 errors, if we're in an exception context then
        print the stack trace is SockJSServer has trace=True.
        """

        self.prep_response()

        if self.server.trace:
            # If we get an explicit stack trace use that,
            # otherwise grab it from the current frame.

            if stacktrace:
                pretty_trace = stacktrace
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()
                stack_trace = traceback.format_exception(exc_type, exc_value, exc_tb)
                pretty_trace = str('\n'.join(stack_trace))

            self.start_response("500 INTERNAL SERVER ERROR", self.headers)
            self.result = [pretty_trace]
            self.process_result()

            self.time_finish = time.time()
            self.log_request()
        else:
            self.content_type = ("Content-Type", "text/plain; charset=UTF-8")
            self.headers += [self.content_type]

            self.start_response("500 INTERNAL SERVER ERROR", self.headers)
            self.result = ['500: Interneal Server Error']
            self.process_result()

            self.time_finish = time.time()
            self.log_request()

    def enable_caching(self):
        d = datetime.datetime.now() + datetime.timedelta(days=365)
        s = datetime.timedelta(days=365).total_seconds()

        self.headers += [
            ('Cache-Control', 'max-age=%d, public' % s),
            ('Expires', d.strftime('%a, %d %b %Y %H:%M:%S')),
            ('access-control-max-age', s),
        ]

    def handle_one_response(self):
        path = self.environ.get('PATH_INFO')
        meth = self.environ.get("REQUEST_METHOD")

        self.router = self.server.application
        self.session_pool = self.server.session_pool

        # Static URLs
        # -----------

        if self.GREETING_RE.match(path):
            return self.greeting()

        if self.IFRAME_RE.match(path):
            return self.write_iframe()

        #if self.INFO_RE.match)path):
            #pass

        session_url = self.URL_FORMAT.match(path)

        if session_url:
            tokens = session_url.groupdict()

            route       = tokens['route']
            session_uid = tokens['session_id']
            server      = tokens['server_id']
            transport   = tokens['transport']

            try:
                # Router determines the downlink route as a
                # function of the given url parameters.
                downlink = self.router.route(route, session_uid, server, transport)

                # A downlink is some data-dependent connection
                # to the client taken as a result of a request.
                raw_request_data = self.wsgi_input.readline()
                downlink(self, meth, raw_request_data)

            except Http404:
                return self.do404()
            except Http500 as e:
                return self.do500(e.stacktrace)
            except Exception:
                return self.do500()

        else:
            self.do404()
