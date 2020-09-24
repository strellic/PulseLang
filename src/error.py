# PulseLang Error Handler

import sys

errors = 0

def error(linenum, error, filename=None):
    global errors
    if not filename:
        msg = "{}: {}".format(linenum, error)
    else:
        msg = "{}:{}: {}".format(filename, linenum, error)

    print(msg, file=sys.stderr)
    errors += 1

def errors_reported():
    return errors

def clear_errors():
    global errors
    errors = 0
