
from settings                 import PROXY_PORT
from utilities                import TimeAgent
import urllib
import simplejson as json

class Score(object):

    def __init__(self):
        self.url = "http://trent.gb.nrao.edu:%d/score" % PROXY_PORT

    def periods(self, periodIds):
        """
        Given a list of period ids, returns a dictionary with the
        ids as keys and the values the associated scores.
        """
        pdict = "&pids=".join(map(str, periodIds))
        url = "".join([self.url, "/periods?pids=", pdict])
        try:
            f = urllib.urlopen(url)
        except IOError:
            print "IOError service", url
        else:
            asstr = f.read()
            results = json.loads(asstr)['scores']
            retval = {}
            for d in results:
                retval[d['pid']] = d['score']
            return retval

    def session(self, sessionId, start, durHrs):
        """
        Given a session id, a start time, and duration
        returns its score.
        """
        params = urllib.urlencode(dict(sid      = sessionId
                                     , start    = TimeAgent.quarter(start)
                                     , duration = int(round(4.0*durHrs))*15))
        url = "".join([self.url, "/session?", params])
        try:
            f = urllib.urlopen(url)
        except IOError:
            print "IOError service", url
        else:
            asstr = f.read()
            print json.loads(asstr)['score']
