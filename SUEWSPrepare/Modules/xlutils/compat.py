import sys

PY3 = sys.version_info[0] >= 3

if PY3:
    unicode = str
    basestring = str
    xrange = range
else:
    unicode = unicode
    basestring = basestring
    xrange = xrange
