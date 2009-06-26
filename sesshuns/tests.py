from datetime           import datetime, timedelta
from django.test.client import Client
from django.http        import QueryDict
import simplejson as json

from models                          import *
from test_utils.NellTestCase         import NellTestCase
from tools                           import DBReporter
from utilities.database              import DSSPrime2DSS
from utilities.receiver              import ReceiverCompile

# Test field data
fdata = {"total_time": "3"
       , "req_max": "6"
       , "name": "Low Frequency With No RFI"
       , "grade": "A"
       , "science": "pulsar"
       , "orig_ID": "0"
       , "between": "0"
       , "proj_code": "GBT09A-001"
       , "PSC_time": "2"
       , "sem_time": 0.0
       , "req_min": "2"
       , "freq": "6"
       , "type": "open"
       , "source" : "blah"
       , "enabled" : False
       , "authorized" : False
       , "complete" : False
       , "backup" : False
         }

def create_sesshun():
    "Utility method for creating a Sesshun to test."

    s = Sesshun()
    s.set_base_fields(fdata)
    allot = Allotment(psc_time          = fdata.get("PSC_time", 0.0)
                    , total_time        = fdata.get("total_time", 0.0)
                    , max_semester_time = fdata.get("sem_time", 0.0)
                    , grade             = 4.0
                      )
    allot.save()
    s.allotment        = allot
    status = Status(
               enabled    = True
             , authorized = True
             , complete   = False
             , backup     = False
                        )
    status.save()
    s.status = status
    s.save()

    t = Target(session    = s
             , system     = first(System.objects.filter(name = "J2000"))
             , source     = "test source"
             , vertical   = 2.3
             , horizontal = 1.0
               )
    t.save()
    return s

# Testing models

class TestReceiver(NellTestCase):

    def setUp(self):
        super(TestReceiver, self).setUp()
        self.client = Client()
        s = Sesshun()
        s.init_from_post({})
        s.save()

    def test_get_abbreviations(self):
        nn = Receiver.get_abbreviations()
        self.assertTrue(len(nn) > 17)
        self.assertEquals([n for n in nn if n == 'Ka'], ['Ka'])

    def test_save_receivers(self):
        s = Sesshun.objects.all()[0]
        rcvr = 'L'
        s.save_receivers(rcvr)
        rgs = s.receiver_group_set.all()
        self.assertEqual(1, len(rgs))
        self.assertEqual(rcvr, rgs[0].receivers.all()[0].abbreviation)

        s.receiver_group_set.all().delete()
        s.save_receivers('L | (X & S)')
        rgs = s.receiver_group_set.all()
        #print rgs
        # TBF WTF? now it is S, then it is X??
        #print rgs[0].receivers.all()[1].abbreviation
        self.assertEqual(2, len(rgs))
        #print rgs[0].receivers.all()[1].abbreviation
        self.assertEqual('L', rgs[0].receivers.all()[0].abbreviation)
        self.assertEqual('X', rgs[0].receivers.all()[1].abbreviation)
        self.assertEqual('L', rgs[1].receivers.all()[0].abbreviation)
        self.assertEqual('S', rgs[1].receivers.all()[1].abbreviation)

class TestReceiverSchedule(NellTestCase):

    def setUp(self):
        super(TestReceiverSchedule, self).setUp()
        self.client = Client()

        d = datetime(2009, 4, 1, 0)
        for i in range(9):
            start_date = d + timedelta(5*i)
            for j in range(1,4):
                rs = Receiver_Schedule()
                rs.start_date = start_date
                rs.receiver = Receiver.objects.get(id = i + j)
                rs.save()

    def test_extract_schedule(self):
        startdate = datetime(2009, 4, 6, 12)
        duration = 15
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate,
                                                      days = duration)
        expected = [datetime(2009, 4, 11, 0, 0)
                  , datetime(2009, 4, 16, 0, 0)
                  , datetime(2009, 4, 6, 0, 0)
                  , datetime(2009, 4, 21, 0, 0)]
        self.assertEqual(expected, schedule.keys())
        jschedule = Receiver_Schedule.jsondict(schedule)
        expected = {'04/11/2009': [u'342', u'450', u'600']
                  , '04/16/2009': [u'450', u'600', u'800']
                  , '04/06/2009': [u'RRI', u'342', u'450']
                  , '04/21/2009': [u'600', u'800', u'1070']}
        self.assertEqual(expected, jschedule)

    def test_previousDate(self):
        self.assertEqual(datetime(2009, 4, 6, 0),
                         Receiver_Schedule.previousDate(
                             datetime(2009, 4, 6, 12)))
        self.assertEqual(datetime(2009, 4, 1, 0),
                         Receiver_Schedule.previousDate(
                             datetime(2009, 4, 5, 23)))
        self.assertEqual(datetime(2009, 5, 11, 0),
                         Receiver_Schedule.previousDate(
                             datetime(2009, 7, 1, 0)))
        self.assertEqual(datetime(2009, 4, 1, 0),
                         Receiver_Schedule.previousDate(
                             datetime(2009, 4, 1, 0)))

    def test_receivers_schedule(self):
        startdate = datetime(2009, 4, 6, 12)
        response = self.client.get('/receivers/schedule',
                                   {"startdate" : startdate,
                                    "duration" : 7})
        self.failUnlessEqual(response.status_code, 200)
        expected = '{"schedule": {"04/11/2009": ["342", "450", "600"], "04/06/2009": ["RRI", "342", "450"]}}'
        self.assertEqual(expected, response.content)

class TestSesshun(NellTestCase):

    def setUp(self):
        super(TestSesshun, self).setUp()
        self.sesshun = create_sesshun()

    def test_create(self):
        expected = first(Sesshun.objects.filter(id = self.sesshun.id))
        self.assertEqual(expected.allotment.total_time, float(fdata["total_time"]))
        self.assertEqual(expected.name, fdata["name"])

    def test_init_from_post(self):
        s = Sesshun()
        s.init_from_post(fdata)
        
        self.assertEqual(s.allotment.total_time, fdata["total_time"])
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])

        # does this still work if you requery the DB?
        ss = Sesshun.objects.all()
        self.assertEqual(2, len(ss))
        s = ss[1]
        # notice the change in type when we compare this way!
        self.assertEqual(s.allotment.total_time, float(fdata["total_time"]))
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])

    def test_update_from_post(self):
        ss = Sesshun.objects.all()
        s = Sesshun()
        s.init_from_post(fdata)
        
        self.assertEqual(s.frequency, fdata["freq"])
        self.assertEqual(s.allotment.total_time, fdata["total_time"])
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])

        # change a number of things and see if it catches it
        ldata = dict(fdata)
        ldata["freq"] = "10"
        ldata["source"] = "new source"
        ldata["total_time"] = "99"
        ldata["enabled"] = True 
        s.update_from_post(ldata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(ldata["freq"]))
        self.assertEqual(s.allotment.total_time, float(ldata["total_time"]))
        self.assertEqual(s.target_set.get().source, ldata["source"])
        self.assertEqual(s.status.enabled, ldata["enabled"])

    def test_update_from_post2(self):
        ss = Sesshun.objects.all()
        s = Sesshun()
        s.init_from_post(fdata)
        
        self.assertEqual(s.frequency, fdata["freq"])
        self.assertEqual(s.allotment.total_time, fdata["total_time"])
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])
        self.assertEqual(s.original_id, int(fdata["orig_ID"]))

        # check to see if we can handle odd types 
        ldata = dict(fdata)
        ldata["freq"] = "10.5"
        ldata["source"] = None 
        ldata["total_time"] = "99.9"
        ldata["orig_ID"] = "0.0"
        ldata["enabled"] = "True" 
        s.update_from_post(ldata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(ldata["freq"]))
        self.assertEqual(s.allotment.total_time, float(ldata["total_time"]))
        self.assertEqual(s.target_set.get().source, ldata["source"])
        self.assertEqual(s.status.enabled, True) # "True" -> True
        self.assertEqual(s.original_id, 0) #ldata["orig_ID"]) -- "0.0" -> Int

    def test_grade_abc_2_float(self):
        s = Sesshun()
        values = [('A',4.0),('B',3.0),('C',2.0)]
        for letter, num in values:
            fltGrade = s.grade_abc_2_float(letter)
            self.assertEqual(num, fltGrade)

    def test_grade_float_2_abc(self):
        s = Sesshun()
        values = [('A',4.0),('B',3.0),('C',2.0)]
        for letter, num in values:
            letterGrade = s.grade_float_2_abc(num)
            self.assertEqual(letter, letterGrade)

# Testing View Resources

class TestSessionResource(NellTestCase):

    def setUp(self):
        super(TestSessionResource, self).setUp()
        self.client = Client()
        s = Sesshun()
        s.init_from_post({})
        s.save()
        self.s = s

    def test_create(self):
        response = self.client.post('/sessions')
        self.failUnlessEqual(response.status_code, 200)

    def test_create2(self):
        fdata = {'req_max': ['6.0']
               , 'grade': ['A']
               , 'req_min': ['2.0']
               , 'sem_time': ['1.0']
               , 'id': ['0']
               , 'source': ['1']
               , 'authorized': ['true']
               , 'between': ['0.0']
               , 'type': ['open']
               , 'total_time': ['1.0']
               , 'coord_mode': ['J2000']
               , 'complete': ['false']
               , 'source_h': ['1']
               , 'source_v': ['1']
               , 'PSC_time': ['1.0']
               , 'freq': ['1.0']
               , 'name': ['All Fields']
               , 'science': ['pulsar']
               , 'orig_ID': ['0']
               , 'enabled': ['false']
               , 'receiver': ['1070']
               , 'backup': ['false']
                 }

        response = self.client.post('/sessions', fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/sessions')
        self.failUnlessEqual(response.status_code, 200)

    def test_read_one(self):
        response = self.client.get('/sessions/%s' % self.s.id)
        self.failUnlessEqual(response.status_code, 200)

        r_json = json.loads(response.content)
        self.assertEqual(0.0, r_json["session"]["total_time"])

    def test_update(self):
        response = self.client.post('/sessions/1', {'_method' : 'put'})
        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.post('/sessions/1', {'_method' : 'delete'})
        self.failUnlessEqual(response.status_code, 200)

    def test_create_rcvr(self):
        response = self.client.post('/sessions', {'receiver' : 'L'})
        self.failUnlessEqual(response.status_code, 200)
        r_json = json.loads(response.content)
        self.assertTrue(r_json.has_key('receiver'))
        self.assertEquals(r_json['receiver'], 'L')
    
    def test_create_rcvrs(self):   # TBF hold until handles multiple rcvrs
        response = self.client.post('/sessions',
                                    {'receiver' : 'K & (L | S)'})
        self.failUnlessEqual(response.status_code, 200)
        r_json = json.loads(response.content)
        self.assertTrue(r_json.has_key('receiver'))
        self.assertEquals(r_json['receiver'], u'(K) & (L | S)')
        # etc
        response = self.client.post('/sessions',
                                    {'receiver' : 'Ka | (342 & S)'})
        self.failUnlessEqual(response.status_code, 200)
        r_json = json.loads(response.content)
        self.assertTrue(r_json.has_key('receiver'))
        self.assertEquals(r_json['receiver'], u'(342 | Ka) & (S | Ka)')
    
class TestGetOptions(NellTestCase):

    def test_get_options(self):
        c = Client()
        response = c.get('/sessions/options')
         
# Testing Utilities

class TestDBReporter(NellTestCase):

    def test_DBReporter(self):
        "Simply make sure that no exceptions are raised."
        db = DBReporter(quiet=True)
        db.report()

class TestDSSPrime2DSS(NellTestCase):

    def test_DSSPrime2DSS(self):
        t = DSSPrime2DSS()
        t.transfer()

class TestReceiverCompile(NellTestCase):

    def test_normalize(self):
        nn = Receiver.get_abbreviations()
        rc = ReceiverCompile(nn)
        self.assertEquals(rc.normalize(u'Q'), [[u'Q']])
        self.assertEquals(rc.normalize('K & (L | S)'),
                                       [['K'], ['L', 'S']])
        self.assertEquals(rc.normalize('342 | (K & Ka)'),
                                       [['342', 'K'], ['342', 'Ka']])
        self.assertEquals(rc.normalize('(L ^ 342) v (K & Ka)'),
                                       [['L', 'K'],   ['L', 'Ka'],
                                        ['342', 'K'], ['342', 'Ka']])
        try:
            self.assertEquals(rc.normalize('J'), [['J']])
        except ValueError:
            pass
        else:
            self.fail()

