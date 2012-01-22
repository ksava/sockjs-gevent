import random

import protocol
from errors import *

class Greeting():
    def __init__(self, route):
        self.route = route

    def __call__(self, handler, request_method, raw_request_data):
        handler.greeting()

class InfoHandler():
    def __init__(self, route):
        self.route = route

    def __call__(self, handler, request_method, raw_request_data):

        if request_method == 'GET':
            entropy = random.randint(1, 2**32)

            has_ws = self.route.transport_allowed('websocket')

            handler.enable_nocache()
            handler.enable_cors()

            handler.write_json({
                'cookie_needed' : True,
                'websocket'     : has_ws,
                'origins'       : ['*:*'],
                'entropy'       : entropy,
                'route'         : self.route.__class__.__name__
            })

        elif request_method == 'OPTIONS':
            handler.write_options(['OPTIONS','GET'])

class IFrameHandler():

    def __init__(self, route):
        self.route = route

    def __call__(self, handler, request_method, raw_request_data):

        #if request_method != 'GET':
            #raise Http404()

        cached = handler.environ.get('HTTP_IF_NONE_MATCH')

        # TODO: check this is equal to our MD5
        if cached:
            handler.start_response("304 NOT MODIFIED", handler.headers)
            handler.enable_caching()

            handler.result = [None]
            handler.process_result()
            return

        handler.headers += [
            ('ETag', protocol.IFRAME_MD5),
        ]

        # TODO: actually put this in here
        html = protocol.IFRAME_HTML % ('http',)
        handler.enable_caching()
        handler.write_html(html)
