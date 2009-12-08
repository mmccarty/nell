import urllib2
import lxml.etree    as ET
from sesshuns.models import *
from datetime        import datetime

class NRAOBosDB:

    """
    This class is responsible for getting info from the BOS 
    query services.  Thankfully, there is no security to get around.
    """

    __cache = {}

    def __init__(self):

        self.opener = urllib2.build_opener()

        # we must use bostest.cv.nrao.edu because bos.nrao.edu
        # knows nothing about PST users
        #baseUrl ='https://bostest.cv.nrao.edu/resReports/reservationsByPerson/'
        self.baseUrlByPerson = \
            'https://bos.nrao.edu/resReports/reservationsByPerson/'
        #    'https://bostest.cv.nrao.edu/resReports/reservationsByPerson/'

    def reservations(self, project, use_cache = True):
        """
        Constructs a dictionary mapping the project's users to lists of
        reservations, where a reservation is a binary tuple of datetimes
        representing the check-in and check-out dates.
        """
        retval = dict()
        for i in project.investigator_set.all():
            u = i.user
            rs = self.getReservationsByUsername(u.username, use_cache)
            if rs:
                retval[u] = rs
        return retval

    def eventjson(self, project, id):
        """
        Take a Project and a starting id and returns a list of json
        dictionaries representing each reservation.  The keys of the json
        dictionary are: id, title, start, end.
        """
        jsonobjlist = []
        for user, reservations in self.reservations(project).items():
            for start, end in reservations:
                jsonobjlist.append({
                    "id"   : id
                  , "title": "".join([user.name(), " in Green Bank"])
                  , "start": start.isoformat()
                  , "end"  : end.isoformat()
                })
                id = id + 1
        return jsonobjlist, id
 
    def getReservationsByUsername(self, username, use_cache = True):
        """
        Uses BOS query service to return list of reservations for
        username, where a reservation is a binary tuple of datetimes
        representing the check-in and check-out dates.
        """
        if username is None:
            #print "Error: getReservationsByUsername username arg is None"
            return []

        time = 0; info = 1
        now  = datetime.utcnow()

        # The cache considers data stale after 60 minutes.
        if not use_cache or \
           not NRAOBosDB.__cache.has_key(username) or \
           (now - NRAOBosDB.__cache[username][time]).seconds > 60. * 60.:
            url = self.baseUrlByPerson + username
            fh  = self.opener.open(url)
            str = fh.read(0x4000)

            NRAOBosDB.__cache[username] = (now, self.parseReservationsXML(str))

        return NRAOBosDB.__cache[username][info]

    def parseReservationsXML(self, str):
        "Parses XML returned by reservationsByPerson query."
        data = ET.fromstring(str)
        reservations = []
        for i in range(len(data)):
            # TBF: why can't I use self.findTag?
            dates = data[i].getchildren()
            assert 'startDate' in dates[0].tag
            start = self.str2dt(dates[0].text)
            end   = self.str2dt(dates[1].text)
            reservations.append((start, end))
        return reservations

    def str2dt(self, str):
        "YYYY-MM-DD -> DateTime"
        return datetime.strptime(str, "%Y-%m-%d")

    def findTag(self, node, tag):
        value = None
        value_tag = node.find(tag)
        if value_tag is not None:
            value = value_tag.text
        return value  

    def _testSystem(self):
        "for testing purposes."
        users = User.objects.all()

        for u in users:
            if u.username is None:
                continue
            print u, u.username
            url = self.baseUrlByPerson + u.username
        
            # no security!  Ha Ha!
            try:
                fh = self.opener.open(url)
            except:
                print "exception for user, username: ", u, u.username
                continue
            str = fh.read(0x4000)
            data = ET.fromstring(str)
            #print data
            if len(data) > 0:
                print "found a reservation!"
                print len(data)
                print data
                print str


