# Copyright (C) 2011 Associated Universities, Inc. Washington DC, USA.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# 
# Correspondence concerning GBT software should be addressed as follows:
#       GBT Operations
#       National Radio Astronomy Observatory
#       P. O. Box 2
#       Green Bank, WV 24944-0002 USA

import sys
import traceback
from django.http import HttpResponse
import inspect
import simplejson as json


def formatExceptionInfo(maxTBlevel=5):
    """
    Obtains information from the last exception thrown and extracts
    the exception name, data and traceback, returning them in a tuple
    (string, string, [string, string, ...]).  The traceback is a list
    which will be 'maxTBlevel' deep.
    """
    cla, exc, trbk = sys.exc_info()
    excName = cla.__name__
    excArgs = exc.__str__()
    excTb = traceback.format_tb(trbk, maxTBlevel)
    return (excName, excArgs, excTb)


def printException(formattedException):
    """
    Takes the tuple provided by 'formatExceptionInfo' and prints it
    out exactly as an uncaught exception would be in an interactive
    python shell.
    """
    print "Traceback (most recent call last):"

    for i in formattedException[2]:
        print i,

    print "%s: %s" % (formattedException[0], formattedException[1])


def exceptionJSONdict(formattedException):
    jd = {"exception_type"      : formattedException[0],
          "exception_args"      : formattedException[1],
          "exception_traceback" : formattedException[2]}
    return jd


def JSONExceptionInfo(msg = None):
    jd = exceptionJSONdict(formatExceptionInfo()) # get this first, in case of trouble below

    try:
        frame = inspect.currentframe()            # the stack frame for this function
        oframes = inspect.getouterframes(frame)   # the list of frames leading to call of this function
        caller = oframes[1]                       # We're interested in the caller of this function
        fname = caller[3]                         # Calling function's name

        if msg == None:
            msg = 'Uncaught exception in'
    except:
        msg   = "Oops, error in JSONExceptionInfo, can't process error!"
        fname = ""
    finally:
        del frame
        del oframes

    return HttpResponse(json.dumps({'error': '%s %s' % (msg, fname),
                                      'exception_data': jd}), mimetype = "text/plain")
