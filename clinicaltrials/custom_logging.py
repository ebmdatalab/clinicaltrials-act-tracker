import logging.handlers
import os


class GroupWriteRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A logging filehandler that ensures group writable logs.

    Ref: https://stackoverflow.com/questions/1407474/
    """

    def _open(self):
        umask = os.umask(0o002)
        handle = logging.handlers.RotatingFileHandler._open(self)
        os.umask(umask)
        return handle
