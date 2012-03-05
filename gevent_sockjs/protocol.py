import hashlib
from errors import *
from simplejson.decoder import JSONDecodeError

# -----------
# Serializer
# -----------

# Fastest

# TODO:
# Should add some caveats about the unicode compatability
# with ujson...
try:
    import ujson
    has_ujson = True
except ImportError:
    has_ujson = False

# Faster
try:
    import simplejson
    has_simplejson = True
except ImportError:
    has_simplejson = False

# Slowest
try:
    import json
    has_json = True
except ImportError:
    # should never happen
    has_json = False

def pick_serializer():
    if has_ujson:
        return ujson
    elif has_simplejson:
        return simplejson
    elif has_json:
        return json

json = pick_serializer()

# Frames
# ------

OPEN      = "o\n"
CLOSE     = "c"
MESSAGE   = "a"
HEARTBEAT = "h\n"

# ------------------

IFRAME_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function(){SockJS.bootstrap_iframe();};
  </script>
  <script src="%s"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>
""".strip()

IFRAME_MD5 = hashlib.md5(IFRAME_HTML).hexdigest()

def encode(message):
    """
    Python to JSON
    """
    # TODO: actually deal with the nuances of escaping and
    # unicode
    if isinstance(message, basestring):
        # Don't both calling json, since its simple
        msg = '["' + message + '"]'
    elif isinstance(message, (object, dict, list)):
        msg = json.dumps(message, separators=(',',':'))
    else:
        raise ValueError("Unable to serialize: %s", str(message))

    return msg

def decode(data):
    """
    JSON to Python
    """
    messages = []
    data = data.decode('utf-8')

    # "a['123', 'abc']" -> [123, 'abc']
    try:
        messages = json.loads(data)
    except JSONDecodeError:
        raise InvalidJSON()

    return messages

def close_frame(code, reason, newline=True):
    if newline:
        return '%s[%d,"%s"]\n' % (CLOSE, code, reason)
    else:
        return '%s[%d,"%s"]' % (CLOSE, code, reason)


def message_frame(data):
    assert isinstance(data, basestring)
    assert '[' in data
    assert ']' in data

    return ''.join([MESSAGE, data])

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

FRAMES = enum( 'CLOSE', 'OPEN', 'MESSAGE', 'HEARTBEAT' )
