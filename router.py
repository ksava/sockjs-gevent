import re

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
