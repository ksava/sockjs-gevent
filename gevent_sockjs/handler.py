import sys
import re
import datetime
import time
import traceback
import random

import gevent
from gevent.pywsgi import WSGIHandler
from Cookie import SimpleCookie

import protocol

from errors import Http404, Http500

class SockJSHandler(WSGIHandler):
    """
    Basic request handling.
    """

    # Sessioned urls
    DYNAMIC_FORMAT = re.compile(r"""
        ^/(?P<route>[^/]+)/        # sockjs route, alphanumeric not empty
        (?P<server_id>[^/.]+)/     # load balancer id, alphanumeric not empty, without (.)
        (?P<session_id>[^/.]+)/    # session id, alphanumeric not empty, without (.)
        (?P<transport>[^/.]+)$     # transport string, (Example: xhr | jsonp ... )
        """, re.X)

    STATIC_FORMAT = re.compile(r"""
        ^/(?P<route>[^/]+)(/)?     # sockjs route, alphanumeric not empty
        (?P<suffix>[^/]+)?$        # url suffix ( Example: / , info, iframe.html )
    """, re.X)

    # Raw write actions
    # -----------------

    def prep_response(self):
        """
        The default headers.
        """
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

        self.result = [text]
        self.process_result()

    def write_json(self, json):
        self.content_type = ("Content-Type", "application/json; charset=UTF-8")

        self.headers += [self.content_type]
        self.start_response("200 OK", self.headers)

        self.result = [protocol.encode(json)]
        self.log_request()
        self.process_result()

    def write_html(self, html):
        self.content_type = ("Content-Type", "text/html; charset=UTF-8")

        self.headers += [self.content_type]
        self.start_response("200 OK", self.headers)

        self.result = [html]
        self.process_result()

    def write_options(self, allowed_methods):
        self.headers += [
            ('Access-Control-Allow-Methods',(', '.join(allowed_methods)))
        ]

        self.enable_caching()
        self.enable_cookie()
        self.enable_cors()
        self.write_nothing()

    def write_nothing(self):
        self.start_response("204 NO CONTENT", self.headers)

        self.result = [None]
        self.process_result()

    def greeting(self):
        self.write_text('Welcome to SockJS!\n')

    def do404(self, message=None, cookie=False):
        self.prep_response()

        self.content_type = ("Content-Type", "text/plain; charset=UTF-8")
        self.headers += [self.content_type]

        if cookie:
            self.enable_cookie()

        self.start_response("404 NOT FOUND", self.headers)

        if message:
            self.result = [message]
        else:
            self.result = ['404 Error: Page not found']

        self.process_result()

        self.wsgi_input._discard()

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
        else:
            self.content_type = ("Content-Type", "text/plain; charset=UTF-8")
            self.headers += [self.content_type]

            self.start_response("500 INTERNAL SERVER ERROR", self.headers)
            self.result = ['500: Interneal Server Error']

        self.process_result()
        self.time_finish = time.time()
        self.log_request()

    # Header Manipulation
    # -------------------

    def enable_cors(self):
        origin = self.environ.get("HTTP_ORIGIN", '*')

        self.headers += [
            ('access-control-allow-origin', origin),
            ('access-control-allow-credentials', 'true')
        ]

    def enable_nocache(self):
        self.headers += [
            ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
            # Implied:
            #('Expires', False),
            #('Last-Modified', False),
        ]

    def enable_cookie(self, cookies=None):
        if cookies:
            for cookie in cookies:
                k, v = cookie.output().split(':')
                self.headers += [(k,v)]
        else:
            cookie = SimpleCookie()
            cookie['JSESSIONID'] = 'dummy'
            cookie['JSESSIONID']['path'] = '/'
            k, v = cookie.output().split(':')
            self.headers += [(k,v)]

    def enable_caching(self):
        d = datetime.datetime.now() + datetime.timedelta(days=365)
        s = datetime.timedelta(days=365).total_seconds()

        self.headers += [
            ('Cache-Control', 'max-age=%d, public' % s),
            ('Expires', d.strftime('%a, %d %b %Y %H:%M:%S')),
            ('access-control-max-age', int(s)),
        ]

    def handle_one_response(self):
        path = self.environ.get('PATH_INFO')
        meth = self.environ.get("REQUEST_METHOD")

        self.router = self.server.application
        self.session_pool = self.server.session_pool

        # Static URLs
        # -----------

        static_url = self.STATIC_FORMAT.match(path)
        dynamic_url = self.DYNAMIC_FORMAT.match(path)

        if static_url:
            tokens = static_url.groupdict()

            route       = tokens['route']
            suffix      = tokens['suffix']

            try:
                handler = self.router.route_static(route, suffix)
                raw_request_data = self.wsgi_input.readline()
                self.wsgi_input._discard()

                self.prep_response()
                handler(self, meth, raw_request_data)
            except Http404 as e:
                return self.do404(e.message)
            except Http500 as e:
                return self.do500(e.stacktrace)

        elif dynamic_url:
            tokens = dynamic_url.groupdict()

            route       = tokens['route']
            session_uid = tokens['session_id']
            server      = tokens['server_id']
            transport   = tokens['transport']

            try:
                # Router determines the downlink route as a
                # function of the given url parameters.
                downlink = self.router.route_dynamic(
                    route,
                    session_uid,
                    server,
                    transport
                )

                # A downlink is some data-dependent connection
                # to the client taken as a result of a request.
                raw_request_data = self.wsgi_input.readline()

                self.prep_response()
                threads = downlink(self, meth, raw_request_data)

                gevent.joinall(threads)

            except Http404 as e:
                return self.do404(e.message, cookie=True)
            except Http500 as e:
                return self.do500(e.stacktrace)
            except Exception:
                return self.do500()

        else:
            self.do404()
