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
    python gevent_sockjs/devserver.py

To run tests
------------

Will create a `sockjs` virtualenv in either your WORKON_HOME or in
the currrent directory if you don't have virtualenvwrapper.

    make tests/Makefile
    setup.py test

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
    test_xhr_server_encodes (tests.JSONEncoding) ... ok
    test_content_types (tests.JsonPolling) ... FAIL
    test_invalid_json (tests.JsonPolling) ... ok
    test_no_callback (tests.JsonPolling) ... ok
    test_transport (tests.JsonPolling) ... ok
    test_closeSession (tests.Protocol) ... ok
    test_simpleSession (tests.Protocol) ... ok
    test_close (tests.RawWebsocket) ... ERROR
    test_transport (tests.RawWebsocket) ... ERROR
    test_anyValue (tests.SessionURLs) ... ok
    test_invalidPaths (tests.SessionURLs) ... ok
    test_broken_json (tests.WebsocketHixie76) ... FAIL
    test_close (tests.WebsocketHixie76) ... ok
    test_empty_frame (tests.WebsocketHixie76) ... ok
    test_headersSanity (tests.WebsocketHixie76) ... ok
    test_reuseSessionId (tests.WebsocketHixie76) ... FAIL
    test_transport (tests.WebsocketHixie76) ... ok
    test_httpMethod (tests.WebsocketHttpErrors) ... ok
    test_invalidConnectionHeader (tests.WebsocketHttpErrors) ...  ok
    test_invalidMethod (tests.WebsocketHttpErrors) ... ok
    test_verifyOrigin (test_protocol.WebsocketHttpErrors) ... ok
    test_broken_json (tests.WebsocketHybi10) ... FAIL
    test_close (tests.WebsocketHybi10) ... ok
    test_firefox_602_connection_header (tests.WebsocketHybi10) ... ok
    test_headersSanity (tests.WebsocketHybi10) ... ok
    test_transport (tests.WebsocketHybi10) ... FAIL
    test_content_types (tests.XhrPolling) ... ok
    test_invalid_json (tests.XhrPolling) ... ok
    test_invalid_session (tests.XhrPolling) ... ok
    test_jsessionid (tests.XhrPolling) ... ok
    test_options (tests.XhrPolling) ... ok
    test_transport (tests.XhrPolling) ... ok
    test_options (tests.XhrStreaming) ... ok
    test_response_limit (tests.XhrStreaming) ... FAIL
    test_transport (tests.XhrStreaming) ... ok

Test Coverage
=============

    Name                        Stmts   Miss  Cover
    -----------------------------------------------
    gevent_sockjs/errors           21     13    38%
    gevent_sockjs/handler         211    175    17%
    gevent_sockjs/protocol         56     26    54%
    gevent_sockjs/router           87     53    39%
    gevent_sockjs/server           53     25    53%
    gevent_sockjs/session          73     45    38%
    gevent_sockjs/sessionpool      58     42    28%
    gevent_sockjs/static           37     25    32%
    gevent_sockjs/transports      102     62    39%
    -----------------------------------------------
    TOTAL                         698    466    33%
