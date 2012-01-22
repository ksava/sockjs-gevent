class Http404(Exception):

    def __str__(self):
        return '404: Page not found'

class Http500(Exception):
    """
    Exception for catching exceptions, also has a slot for a
    stack trace string.
    """

    def __init__(self, stacktrace=None):
        if stacktrace:
            self.message = stacktrace
            self.stacktrace = stacktrace
        else:
            self.message = "500: Internal Server Error"
            self.stacktrace = None
        assert isinstance(self.message, basestring)

    def __str__(self):
        return self.message
