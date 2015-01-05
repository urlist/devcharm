import sys
import traceback

from django.core.signals import got_request_exception

def exception_printer(sender, **kwargs):
    msg = ''.join(traceback.format_exception(*sys.exc_info()))
    sys.stderr.write(msg)

got_request_exception.connect(exception_printer)
