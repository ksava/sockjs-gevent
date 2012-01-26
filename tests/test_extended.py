#!/usr/bin/env python
"""
"""
import os
import time
import json
import re
import unittest2 as unittest
from utils import GET, GET_async, POST, POST_async, OPTIONS
from utils import WebSocket8Client
import uuid
import nose

# Base URL
# ========

test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r, cookie=False):
        self.assertEqual(r.status, 404)
        if cookie is False:
            self.verify_no_cookie(r)
        elif cookie is True:
            self.verify_cookie(r)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertTrue(r['allow'])
        self.assertFalse(r.body)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Access-Control-Allow-Methods'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)
            self.verify_cookie(r)

    # All transports except WebSockets need sticky session support
    # from the load balancer. Some load balancers enable that only
    # when they see `JSESSIONID` cookie. For all the session urls we
    # must set this cookie.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        self.assertEqual(r['access-control-allow-origin'], origin or '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['Last-Modified'])

    @classmethod
    def tearDownClass(cls):
        """
        Wait five seconds for the current sessions to expire.
        """
        time.sleep(5)

# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    nose.main()
