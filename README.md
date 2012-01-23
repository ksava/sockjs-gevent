gevent-sockjs
=============

A work in progress gevent server backend for SockJS.  General goal is to have a
faithful implemention of @majek's [sockjs-protocol](https://github.com/sockjs/sockjs-protocol) that plays nicely with gevent & green threads.

Somewhat unstable at the moment, does not pass all sockjs-protocol tests.

Running
=======

To run the dev server
---------------------

    pip install -r requirements.txt
    python gevent_sockjs/server.py

To run tests
------------

Will create a `sockjs` virtualenv in either your WORKON_HOME or in
the currrent directory if you don't have virtualenvwrapper.

    make
    nosetests sockjs-protocol-0.2.py

Or manually:

    mkvirtualenv sockjs
    pip install -r tests/test_deps.txt

Test Status:
============

    test_greeting (tests.BaseUrlGreeting) ... ok
    test_notFound (tests.BaseUrlGreeting) ... ok
    test_response_limit (tests.EventSource) ... FAIL
    test_transport (tests.EventSource) ... FAIL
    test_abort_xhr_polling (tests.HandlingClose) ... FAIL
    test_abort_xhr_streaming (tests.HandlingClose) ... FAIL
    test_close_frame (tests.HandlingClose) ... FAIL
    test_close_request (tests.HandlingClose) ... FAIL
    test_no_callback (tests.HtmlFile) ... FAIL
    test_response_limit (tests.HtmlFile) ... FAIL
    test_transport (tests.HtmlFile) ... FAIL
    test_cacheability (tests.IframePage) ... ok
    test_invalidUrl (tests.IframePage) ... ok
    test_queriedUrl (tests.IframePage) ... ok
    test_simpleUrl (tests.IframePage) ... ok
    test_versionedUrl (tests.IframePage) ... ok
    test_basic (tests.InfoTest) ... ok
    test_disabled_websocket (tests.InfoTest) ... ok
    test_entropy (tests.InfoTest) ... ok
    test_options (tests.InfoTest) ... ok
    test_xhr_server_decodes (tests.JSONEncoding) ... ok
    test_xhr_server_encodes (tests.JSONEncoding) ... FAIL
    test_content_types (tests.JsonPolling) ... FAIL
    test_invalid_json (tests.JsonPolling) ... FAIL
    test_no_callback (tests.JsonPolling) ... FAIL
    test_transport (tests.JsonPolling) ... FAIL
    test_closeSession (tests.Protocol) ... FAIL
    test_simpleSession (tests.Protocol) ... ok
    test_close (tests.RawWebsocket) ... ERROR
    test_transport (tests.RawWebsocket) ... ERROR
    test_anyValue (tests.SessionURLs) ... ok
    test_invalidPaths (tests.SessionURLs) ... ok
    test_broken_json (tests.WebsocketHixie76) ... ERROR
    test_close (tests.WebsocketHixie76) ... ERROR
    test_empty_frame (tests.WebsocketHixie76) ... ERROR
    test_headersSanity (tests.WebsocketHixie76) ... FAIL
    test_reuseSessionId (tests.WebsocketHixie76) ... ERROR
    test_transport (tests.WebsocketHixie76) ... ERROR
    test_httpMethod (tests.WebsocketHttpErrors) ... FAIL
    test_invalidConnectionHeader (tests.WebsocketHttpErrors) ... FAIL
    test_invalidMethod (tests.WebsocketHttpErrors) ... FAIL
    test_broken_json (tests.WebsocketHybi10) ... ERROR
    test_close (tests.WebsocketHybi10) ... ERROR
    test_firefox_602_connection_header (tests.WebsocketHybi10) ... FAIL
    test_headersSanity (tests.WebsocketHybi10) ... FAIL
    test_transport (tests.WebsocketHybi10) ... ERROR
    test_content_types (tests.XhrPolling) ... ok
    test_invalid_json (tests.XhrPolling) ... ok
    test_invalid_session (tests.XhrPolling) ... ok
    test_jsessionid (tests.XhrPolling) ... ok
    test_options (tests.XhrPolling) ... ok
    test_transport (tests.XhrPolling) ... ok
    test_options (tests.XhrStreaming) ... ok
    test_response_limit (tests.XhrStreaming) ... FAIL
    test_transport (tests.XhrStreaming) ... FAIL
