# -*- coding: utf-8 -*-
import sys

try:
    import urllib.request
    urlretrieve = urllib.request.urlretrieve
    urlopen = urllib.request.urlopen
    Request = urllib.request.Request
except ImportError:
    import urllib2
    import urllib
    urlretrieve = urllib.urlretrieve
    urlopen = urllib2.urlopen
    Request = urllib2.Request


def get_input_func():
    return raw_input if sys.version_info[0] == 2 else input
