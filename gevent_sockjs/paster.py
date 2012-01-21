import gevent
import gevent.monkey


# For paste.deploy server instantiation (egg:gevent_sockjs#server)
def sockjs_server_runner(wsgi_app, global_conf, **kw):
    gevent.monkey.patch_all()

    def runner():
        from gevent_sockjs.server import SockJSServer
        host = kw.get('host', '0.0.0.0')
        port = int(kw.get('port', 8080))
        server = SockJSServer((host, port), wsgi_app)
        print('Starting SockJS server on http://%s:%s' % (host, port))
        server.serve_forever()

    jobs = [gevent.spawn(runner)]
    gevent.joinall(jobs)
