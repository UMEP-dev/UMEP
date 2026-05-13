##
# <p>Copyright (c) 2006-2012 Stephen John Machin, Lingfo Pty Ltd</p>
# <p>This module is part of the xlrd package, which is released under a BSD-style licence.</p>
##

# timemachine.py -- adaptation for single codebase.
# Currently supported: 2.6 to 2.7, 3.2+
# usage: from timemachine import *

from __future__ import print_function

import sys

python_version = sys.version_info[:2]  # e.g. version 2.6 -> (2, 6)

if python_version >= (3, 0):
    # Python 3
    def BYTES_LITERAL(x):
        return x.encode("latin1")

    def UNICODE_LITERAL(x):
        return x

    def BYTES_ORD(byte):
        return byte

    def fprintf(f, fmt, *vargs):
        fmt = fmt.replace("%r", "%a")
        if fmt.endswith("\n"):
            print(fmt[:-1] % vargs, file=f)
        else:
            print(fmt % vargs, end=" ", file=f)

    # xlwt: isinstance(obj, EXCEL_TEXT_TYPES)
    EXCEL_TEXT_TYPES = (str, bytes, bytearray)
    REPR = ascii
    xrange = range

    def unicode(b, enc):
        return b.decode(enc)

    def ensure_unicode(s):
        return s

    unichr = chr
else:
    # Python 2
    def BYTES_LITERAL(x):
        return x

    def UNICODE_LITERAL(x):
        return x.decode("latin1")

    BYTES_ORD = ord

    def fprintf(f, fmt, *vargs):
        if fmt.endswith("\n"):
            print(fmt[:-1] % vargs, file=f)
        else:
            print(fmt % vargs, end=" ", file=f)

    try:
        # xlwt: isinstance(obj, EXCEL_TEXT_TYPES)
        EXCEL_TEXT_TYPES = basestring
    except NameError:
        EXCEL_TEXT_TYPES = (str, unicode)
    REPR = repr
    xrange = xrange
    # following used only to overcome 2.x ElementTree gimmick which
    # returns text as `str` if it's ascii, otherwise `unicode`
    ensure_unicode = unicode  # used only in xlsx.py
