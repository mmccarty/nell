from datetime           import datetime, timedelta
from django.test.client import Client
import simplejson as json

from sesshuns.models                        import *
from server.test_utils.NellTestCase         import NellTestCase
from server.utilities.DBReporter            import DBReporter
from server.utilities.Generate              import Generate
from server.utilities.OpportunityGenerator  import OpportunityGenerator, GenOpportunity
from server.utilities.database              import DSSPrime2DSS
from server.utilities.receiver              import ReceiverCompile

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

class TestCadence(NellTestCase):

    def setUp(self):
        super(TestCadence, self).setUp()
        self.client = Client()
        s = Sesshun()
        s.init_from_post({})
        s.save()
        self.s = s

    def test_gen_windows(self):
        sd = datetime(2009, 4, 28)
        c = Cadence(session = self.s
                  , start_date = sd
                  , repeats    = 4
                  , intervals  = "1,2,3,5"
                  , full_size  = "1,1,1,1"
                    )
        c.save()
        c.gen_windows()

        expected = ((sd,                       24)
                  , (sd + timedelta(days = 1), 24)
                  , (sd + timedelta(days = 2), 24)
                  , (sd + timedelta(days = 4), 24)
                    )
        for i, w in enumerate(self.s.window_set.all()):
            o = first(w.opportunity_set.all())
            result = (o.start_time
                    , o.duration
                      )
            self.assertEqual(expected[i], result)
    
        c = Cadence(session = self.s
                  , start_date = sd
                  , repeats    = 3
                  , intervals  = "30"
                  , full_size  = "6"
                    )
        c.save()
        c.gen_windows()

        expected = ((sd,                        6*24)
                  , (sd + timedelta(days = 30), 6*24)
                  , (sd + timedelta(days = 60), 6*24)
                  , (sd + timedelta(days = 90), 6*24)
                    )
        for i, w in enumerate(self.s.window_set.all()):
            o = first(w.opportunity_set.all())
            result = (o.start_time
                    , o.duration
                      )
            self.assertEqual(expected[i], result)
    
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
            start_date = d + timedelta(i)
            for j in range(1,4):
                rs = Receiver_Schedule()
                rs.start_date = start_date
                rs.receiver = Receiver.objects.get(id = i + j)
                rs.save()

    def test_receivers_schedule(self):
        startdate = datetime(2009, 4, 6, 12)
        response = self.client.get('/receivers/schedule',
                                   {"startdate" : startdate,
                                    "duration" : 6})
        self.failUnlessEqual(response.status_code, 200)
        #self.assertEqual(expected, response.content)

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
        fdata["freq"] = "10"
        fdata["source"] = "new source"
        fdata["total_time"] = "99"
        fdata["enabled"] = True 
        s.update_from_post(fdata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(fdata["freq"]))
        self.assertEqual(s.allotment.total_time, float(fdata["total_time"]))
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])

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
        fdata["freq"] = "10.5"
        fdata["source"] = None 
        fdata["total_time"] = "99.9"
        fdata["orig_ID"] = "0.0"
        fdata["enabled"] = "True" 
        s.update_from_post(fdata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(fdata["freq"]))
        self.assertEqual(s.allotment.total_time, float(fdata["total_time"]))
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, True) # "True" -> True
        self.assertEqual(s.original_id, 0) #fdata["orig_ID"]) -- "0.0" -> Int

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

class TestWindow(NellTestCase):

    def setUp(self):
        super(TestWindow, self).setUp()
        self.w = Window(session = create_sesshun(), required = True)
        self.w.save()

    def test_create(self):
        expected = first(Window.objects.filter(id = self.w.id))
        self.assertTrue(expected.required)

    def test_gen_opportunities(self):
        start_time = datetime(2009, 4, 6, 12)
        o = Opportunity(window     = self.w
                      , start_time = start_time
                      , duration   = 4 * 24)
        o.save()

        w = first(Window.objects.filter(id = self.w.id))
        results = [(o.start_time, o.duration) for o in w.gen_opportunities(start_time)]

        expected = [
                     (datetime(2009, 4, 6, 17, 30), 2.0)
                   , (datetime(2009, 4, 6, 17, 45), 2.0)
                   , (datetime(2009, 4, 6, 18, 0), 2.0)
                   , (datetime(2009, 4, 6, 18, 15), 2.0)
                   , (datetime(2009, 4, 6, 18, 30), 2.0)
                   , (datetime(2009, 4, 6, 18, 45), 2.0)
                   , (datetime(2009, 4, 6, 19, 0), 2.0)
                   , (datetime(2009, 4, 6, 19, 15), 2.0)
                   , (datetime(2009, 4, 7, 17, 30), 2.0)
                   , (datetime(2009, 4, 7, 17, 45), 2.0)
                   , (datetime(2009, 4, 7, 18, 0), 2.0)
                   , (datetime(2009, 4, 7, 18, 15), 2.0)
                   , (datetime(2009, 4, 7, 18, 30), 2.0)
                   , (datetime(2009, 4, 7, 18, 45), 2.0)
                   , (datetime(2009, 4, 7, 19, 0), 2.0)
                   , (datetime(2009, 4, 7, 19, 15), 2.0)
                   , (datetime(2009, 4, 8, 17, 30), 2.0)
                   , (datetime(2009, 4, 8, 17, 45), 2.0)
                   , (datetime(2009, 4, 8, 18, 0), 2.0)
                   , (datetime(2009, 4, 8, 18, 15), 2.0)
                   , (datetime(2009, 4, 8, 18, 30), 2.0)
                   , (datetime(2009, 4, 8, 18, 45), 2.0)
                   , (datetime(2009, 4, 8, 19, 0), 2.0)
                   , (datetime(2009, 4, 8, 19, 15), 2.0)
                   , (datetime(2009, 4, 9, 17, 30), 2.0)
                   , (datetime(2009, 4, 9, 17, 45), 2.0)
                   , (datetime(2009, 4, 9, 18, 0), 2.0)
                   , (datetime(2009, 4, 9, 18, 15), 2.0)
                   , (datetime(2009, 4, 9, 18, 30), 2.0)
                   , (datetime(2009, 4, 9, 18, 45), 2.0)
                   , (datetime(2009, 4, 9, 19, 0), 2.0)
                   , (datetime(2009, 4, 9, 19, 15), 2.0)
                   ]

        self.assertEqual(expected, results)

    def test_jsondict(self):
        start_time = datetime(2009, 4, 6, 12)
        o = Opportunity(window     = self.w
                      , start_time = start_time
                      , duration   = 4)
        o.save()
        w = first(Window.objects.filter(id = self.w.id))

        results = w.jsondict(now = start_time)

        expected = {'required'     : True
                  , 'id'           : 1
                  , 'opportunities': [{'duration'  : 4.0
                                     , 'start_time': '2009-04-06 12:00:00'
                                     , 'id'        : 1}
                                      ]
                  , 'receiver'     : []
                    }
        self.assertEqual(expected, results)

        s = w.session
        s.session_type = first(Session_Type.objects.filter(type = 'windowed'))
        o.duration *= 24
        o.save()

        results = w.jsondict(generate = True, now = start_time)

        expected = {'receiver'     : []
                  , 'duration': 96.0
                  , 'start_time': '2009-04-06 12:00:00'
                  , 'required'     : True
                  , 'id'           : 1
                  , 'opportunities': [
                       {"duration": 2.0, "start_time": "2009-04-06 17:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 17:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 19:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 19:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 17:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 17:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 18:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 18:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 18:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 18:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 19:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-07 19:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 17:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 17:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 18:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 18:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 18:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 18:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 19:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-08 19:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 17:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 17:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 18:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 18:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 18:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 18:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 19:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-09 19:15:00"}
                                     ]
                    }
        self.assertEqual(expected, results)

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

    def test_read(self):
        response = self.client.get('/sessions')
        self.failUnlessEqual(response.status_code, 200)

    def test_read_one(self):
        response = self.client.get('/sessions/%s' % self.s.id)
        self.failUnlessEqual(response.status_code, 200)

        r_json = json.loads(response.content)
        self.assertEqual(0.0, r_json["session"]["total_time"])

    def test_read_cadence(self):
        c = Cadence(session    = self.s
                  , start_date = datetime(2009, 4, 22)
                  , repeats    = 4
                  , intervals  = "3"
                    )
        c.save()
        response = self.client.get('/sessions')
        self.failUnlessEqual(response.status_code, 200)

    def test_update(self):
        response = self.client.post('/sessions/1', {'_method' : 'put'})
        self.failUnlessEqual(response.status_code, 200)

    def test_update_cadence(self):
        c = Cadence(session    = self.s
                  , start_date = datetime(2009, 4, 22)
                  , repeats    = 4
                  , intervals  = "3"
                    )
        c.save()
        new_s = datetime(2009, 4, 23)
        new_r = 3
        new_i = "3,4,5,6"
        response = self.client.post('/sessions/1', {'_method'        : 'put'
                                                  , 'cad_start_date' : new_s.strftime("%m/%d/%Y")
                                                  , 'cad_repeats'    : new_r
                                                  , 'cad_intervals'  : new_i
                                                    })
        self.failUnlessEqual(response.status_code, 200)
        cu = first(Cadence.objects.filter(id = c.id))
        self.assertEquals(new_s, cu.start_date)
        self.assertEquals(new_r, cu.repeats)
        self.assertEquals(new_i, cu.intervals)

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
    
class TestCadenceResource(NellTestCase):

    def setUp(self):
        super(TestCadenceResource, self).setUp()
        self.client = Client()
        s = Sesshun()
        s.init_from_post({})
        s.save()
        self.s = s

    def test_create(self):
        sd    = datetime(2009, 4, 1, 12)
        fdata = {
                 "start_date" : sd.strftime("%m/%d/%Y")
               , "repeats"    : 4
               , "intervals"  : "3"
               , "full_size"  : "3"
                 }
        response = self.client.post('/sessions/%s/cadences' % self.s.id, fdata)
        self.failUnlessEqual(response.status_code, 200)

        r_json = json.loads(response.content)
        
        self.assertEqual(r_json["session_id"], self.s.id)
        self.assertEqual(r_json["start_date"], fdata["start_date"])
        self.assertEqual(r_json["repeats"],    fdata["repeats"])
        self.assertEqual(r_json["full_size"],  fdata["full_size"])
        self.assertEqual(r_json["intervals"],  fdata["intervals"])

        self.assertNotEqual(0, len(Window.objects.filter(session = self.s)))

    def test_create_invalid(self):
        sd    = datetime(2009, 4, 1, 12)
        fdata = {
                 "repeats"    : 4
               , "intervals"  : "3"
                 }
        response = self.client.post('/sessions/%s/cadences' % self.s.id, fdata)
        self.failUnlessEqual(response.status_code, 200)

        r_json = json.loads(response.content)
        
        self.assertEqual(r_json["session_id"], self.s.id)
        self.assertEqual(r_json["repeats"],    fdata["repeats"])
        self.assertEqual(r_json["intervals"],  fdata["intervals"])

        self.assertEqual(0, len(Window.objects.filter(session = self.s)))

    def test_read(self):
        sd = datetime(2009, 4, 22)
        c = Cadence(session    = self.s
                  , start_date = sd
                  , repeats    = 4
                  , full_size  = "4"
                  , intervals  = "3"
                    )
        c.save()
        response = self.client.get('/sessions/%s/cadences' % self.s.id)

        r_json = json.loads(response.content)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(r_json["session_id"], self.s.id)
        self.assertEqual(r_json["start_date"], sd.strftime("%m/%d/%Y"))
        self.assertEqual(r_json["repeats"],    c.repeats)
        self.assertEqual(r_json["full_size"],  c.full_size)
        self.assertEqual(r_json["intervals"],  c.intervals)

    def test_update(self):
        sd = datetime(2009, 4, 22)
        c = Cadence(session    = self.s
                  , start_date = sd
                  , repeats    = 4
                  , intervals  = "3"
                  , full_size  = "3"
                    )
        c.save()

        fdata = {"session_id" : str(self.s.id)
               , "start_date" : sd.strftime("%m/%d/%Y")
               , "repeats"    : 4
               , "intervals"  : "3"
               , "full_size"  : "3"
                 }
        fdata.update({'_method' : 'put'})
        response = self.client.post('/sessions/%i/cadences' % self.s.id
                                  , fdata)

        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        s = first(Sesshun.objects.all())
        sd = datetime(2009, 4, 22)
        c = Cadence(session    = self.s
                  , start_date = sd
                  , repeats    = 4
                  , intervals  = "3"
                    )
        c.save()

        response = self.client.post('/sessions/%i/cadences' % s.id, {'_method' : 'delete'})
        self.failUnlessEqual(response.status_code, 200)

        # Make sure that deleting the window deletes all opportunities
        cads = Cadence.objects.filter(session = s)
        self.failUnlessEqual(len(cads), 0)

class TestWindowResource(NellTestCase):

    def setUp(self):
        super(TestWindowResource, self).setUp()
        self.client = Client()
        s = Sesshun()
        s.init_from_post({})
        s.save_receivers('K | (L & S)')
        s.save()

    def test_create(self):
        num_opps = 4
        starts = [datetime(2009, 4, 1, 12) + timedelta(days = d) for d in range(num_opps)]
        fdata = {"session_id" : "1"
               , "start_time" : map(str, starts)
               , "duration"   : [1 + i for i in range(len(starts))]
                 }
        response = self.client.post('/sessions/windows', fdata)

        expected = ["2009-04-01 12:00:00"
                  , "2009-04-02 12:00:00"
                  , "2009-04-03 12:00:00"
                  , "2009-04-04 12:00:00"
                    ]
        
        self.failUnlessEqual(response.status_code, 200)
        r_json = json.loads(response.content)
        results = [r["start_time"] for r in r_json["opportunities"]]
        for e in expected:
            self.assertTrue(e in results)

    def test_read(self):
        s = first(Sesshun.objects.all())
        w = Window(session = s)
        w.init_from_post()

        response = self.client.get('/sessions/1/windows')
        self.failUnlessEqual(response.status_code, 200)
        expected = json.dumps(
            {"windows":
             [
                {"required": False,
                 "id": 1,
                 "opportunities": [],
                 "receiver": [["L", "K"], ["S", "K"]]
                }
             ]
            }
        )
        self.assertEqual(expected, response.content)

    def test_update(self):
        s = first(Sesshun.objects.all())
        w = Window(session = s)
        w.init_from_post()

        num_opps = 4
        starts = [datetime(2009, 4, 10, 12) + timedelta(days = d) for d in range(num_opps)]
        fdata = {"session_id" : "1"
               , "start_time" : map(str, starts)
               , "duration"   : [1 + i for i in range(len(starts))]
                 }
        fdata.update({'_method' : 'put'})
        response = self.client.post('/sessions/windows/%i' % w.id
                                  , fdata)

        self.failUnlessEqual(response.status_code, 200)

        expected = [o.start_time for o in w.opportunity_set.all()]
        self.assertTrue(datetime(2009, 4, 10, 12) in expected)


    def test_delete(self):
        s = first(Sesshun.objects.all())
        w = Window(session = s)
        w.init_from_post()

        response = self.client.post('/sessions/windows/%i' % w.id, {'_method' : 'delete'})
        self.failUnlessEqual(response.status_code, 200)

        # Make sure that deleting the window deletes all opportunities
        opps = Opportunity.objects.filter(window = w)
        self.failUnlessEqual(len(opps), 0)

class TestWindowGenView(NellTestCase):

    def setUp(self):
        super(TestWindowGenView, self).setUp()
        self.client = Client()
        self.w = Window(session = create_sesshun(), required = True)
        self.w.save()
        start_time = datetime(2009, 4, 6, 12)
        o = Opportunity(window     = self.w
                      , start_time = start_time
                      , duration   = 4 * 24)
        o.save()
        s = self.w.session
        s.session_type = first(Session_Type.objects.filter(type = 'windowed'))
        s.save()

        self.w2 = Window(session = create_sesshun(), required = True)
        self.w2.save()
        start_time = datetime(2009, 5, 6, 12)
        o = Opportunity(window     = self.w2
                      , start_time = start_time
                      , duration   = 4 * 24)
        o.save()

    def xtest_read(self):
        now = datetime(2009, 4, 6, 12)
        response = self.client.get('/gen_opportunities', {"now" : now})
        self.failUnlessEqual(response.status_code, 200)
        expected = json.dumps(
             {"windows": [{
                 "receiver": []
               , "duration": 96.0
               , "start_time": "2009-04-06 12:00:00"
               , "required": True
               , "id": 1
               , "opportunities":
                   [{"duration": 2.0, "start_time": "2009-04-06 17:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 17:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 18:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 18:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 18:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 18:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 19:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-06 19:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 17:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 17:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 18:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 18:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 18:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 18:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 19:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-07 19:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 17:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 17:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 18:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 18:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 18:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 18:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 19:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-08 19:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 17:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 17:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 18:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 18:15:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 18:30:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 18:45:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 19:00:00"}
                  , {"duration": 2.0, "start_time": "2009-04-09 19:15:00"}]}
          , {
             "required": True
           , "id": 2
           , "opportunities":
               [{"duration": 96.0, "start_time": "2009-05-06 12:00:00", "id": 2}]
           , "receiver": []
           }]}
           )
        self.assertEqual(expected, response.content)

        response = self.client.get('/gen_opportunities/1')
        self.failUnlessEqual(response.status_code, 200)
        expected = json.dumps({
             "required": True
           , "id": 1
           , "opportunities":
                      [{"duration": 2.0, "start_time": "2009-04-06 17:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 17:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:15:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:30:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 18:45:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 19:00:00"}
                     , {"duration": 2.0, "start_time": "2009-04-06 19:15:00"}
                      ]
                              }
                             )
        self.assertTrue(expected, response.content)

        response = self.client.get('/gen_opportunities/2')
        self.failUnlessEqual(response.status_code, 200)
        expected = json.dumps({
             "required": True
           , "id": 2
            , "opportunities": [{"duration": 4.0, "start_time": "2009-05-06 12:00:00", "id": 2}]
                                 }
                              )
        self.assertTrue(expected, response.content)

class TestGetOptions(NellTestCase):

    def test_get_options(self):
        c = Client()
        response = c.get('/sessions/options')
         
# Testing Utilities

class TestGenerate(NellTestCase):

    def test_create(self):
        #                 open  wind  fixd
        ratio          = (0.45, 0.15, 0.4)
        total_sem_time = 2920 # hours
        g = Generate(2009, ratio, total_sem_time)
        self.assertEqual(g.open_time, ratio[0] * total_sem_time)
        
    def test_generate(self):
        #                 open  wind  fixd
        ratio          = (0.45, 0.15, 0.4)
        total_sem_time = 2920 # hours
        g  = Generate(2009, ratio, total_sem_time)
        ss = g.generate()
        self.assertTrue(len(ss) > 0)
        """
        for s in ss:
            print s.name
            w = first(s.window_set.all())
            for o in w.opportunity_set.all():
                print "\t", o

        windowed = first(Session_Type.objects.filter(type = "windowed"))
        print "Windowed Sessions", len(Sesshun.objects.filter(session_type = windowed))
        print "Opportunities ", len(Opportunity.objects.all())
        """

    def test_generate_session(self):
        #                 open  wind  fixd
        ratio          = (0.45, 0.15, 0.4)
        total_sem_time = 2920 # hours
        g = Generate(2009, ratio, total_sem_time)
        fixed_type = first(Session_Type.objects.filter(type = "fixed"))
        s = g.generate_session(1, "Fixed", fixed_type)
        self.assertNotEqual(s, None)
        self.assertEqual(s.name, "Fixed 1")

class TestOpportunityGenerator(NellTestCase):

    def setUp(self):
        super(TestOpportunityGenerator, self).setUp()
        s = Sesshun()
        s.init_from_post({})
        s.save()

    def test_create(self):
        now = datetime.utcnow()
        og = OpportunityGenerator(now)
        self.assertEqual(now, og.now)

    def test_generate(self):
        now      = datetime(2009, 4, 6, 15, 15)
        gen_opp  = GenOpportunity(start_time = now, duration = 4 * 24)
        og       = OpportunityGenerator(now)
        ha_limit = 3 #hrs
        s        = first(Sesshun.objects.all())

        results  = [(o.start_time, o.duration) for o in og.generate(gen_opp, s, ha_limit)]

        expected = [
                   (datetime(2009, 4, 6, 15, 15), 3.0),
                   (datetime(2009, 4, 6, 15, 30), 3.0),
                   (datetime(2009, 4, 6, 15, 45), 3.0),
                   (datetime(2009, 4, 6, 16, 0), 3.0),
                   (datetime(2009, 4, 6, 16, 15), 3.0),
                   (datetime(2009, 4, 6, 16, 30), 3.0),
                   (datetime(2009, 4, 6, 16, 45), 3.0),
                   (datetime(2009, 4, 6, 17, 0), 3.0),
                   (datetime(2009, 4, 6, 17, 15), 3.0),
                   (datetime(2009, 4, 6, 17, 30), 3.0),
                   (datetime(2009, 4, 6, 17, 45), 3.0),
                   (datetime(2009, 4, 6, 18, 0), 3.0),
                   (datetime(2009, 4, 6, 18, 15), 3.0),
                   (datetime(2009, 4, 6, 18, 30), 3.0),
                   (datetime(2009, 4, 6, 18, 45), 3.0),
                   (datetime(2009, 4, 6, 19, 0), 3.0),
                   (datetime(2009, 4, 6, 19, 15), 3.0),
                   (datetime(2009, 4, 6, 19, 30), 3.0),
                   (datetime(2009, 4, 6, 19, 45), 3.0),
                   (datetime(2009, 4, 6, 20, 0), 3.0),
                   (datetime(2009, 4, 6, 20, 15), 3.0),
                   (datetime(2009, 4, 6, 20, 30), 3.0),
                   (datetime(2009, 4, 6, 20, 45), 3.0),
                   (datetime(2009, 4, 6, 21, 0), 3.0),
                   (datetime(2009, 4, 7, 15, 15), 3.0),
                   (datetime(2009, 4, 7, 15, 30), 3.0),
                   (datetime(2009, 4, 7, 15, 45), 3.0),
                   (datetime(2009, 4, 7, 16, 0), 3.0),
                   (datetime(2009, 4, 7, 16, 15), 3.0),
                   (datetime(2009, 4, 7, 16, 30), 3.0),
                   (datetime(2009, 4, 7, 16, 45), 3.0),
                   (datetime(2009, 4, 7, 17, 0), 3.0),
                   (datetime(2009, 4, 7, 17, 15), 3.0),
                   (datetime(2009, 4, 7, 17, 30), 3.0),
                   (datetime(2009, 4, 7, 17, 45), 3.0),
                   (datetime(2009, 4, 7, 18, 0), 3.0),
                   (datetime(2009, 4, 7, 18, 15), 3.0),
                   (datetime(2009, 4, 7, 18, 30), 3.0),
                   (datetime(2009, 4, 7, 18, 45), 3.0),
                   (datetime(2009, 4, 7, 19, 0), 3.0),
                   (datetime(2009, 4, 7, 19, 15), 3.0),
                   (datetime(2009, 4, 7, 19, 30), 3.0),
                   (datetime(2009, 4, 7, 19, 45), 3.0),
                   (datetime(2009, 4, 7, 20, 0), 3.0),
                   (datetime(2009, 4, 7, 20, 15), 3.0),
                   (datetime(2009, 4, 7, 20, 30), 3.0),
                   (datetime(2009, 4, 7, 20, 45), 3.0),
                   (datetime(2009, 4, 7, 21, 0), 3.0),
                   (datetime(2009, 4, 8, 15, 15), 3.0),
                   (datetime(2009, 4, 8, 15, 30), 3.0),
                   (datetime(2009, 4, 8, 15, 45), 3.0),
                   (datetime(2009, 4, 8, 16, 0), 3.0),
                   (datetime(2009, 4, 8, 16, 15), 3.0),
                   (datetime(2009, 4, 8, 16, 30), 3.0),
                   (datetime(2009, 4, 8, 16, 45), 3.0),
                   (datetime(2009, 4, 8, 17, 0), 3.0),
                   (datetime(2009, 4, 8, 17, 15), 3.0),
                   (datetime(2009, 4, 8, 17, 30), 3.0),
                   (datetime(2009, 4, 8, 17, 45), 3.0),
                   (datetime(2009, 4, 8, 18, 0), 3.0),
                   (datetime(2009, 4, 8, 18, 15), 3.0),
                   (datetime(2009, 4, 8, 18, 30), 3.0),
                   (datetime(2009, 4, 8, 18, 45), 3.0),
                   (datetime(2009, 4, 8, 19, 0), 3.0),
                   (datetime(2009, 4, 8, 19, 15), 3.0),
                   (datetime(2009, 4, 8, 19, 30), 3.0),
                   (datetime(2009, 4, 8, 19, 45), 3.0),
                   (datetime(2009, 4, 8, 20, 0), 3.0),
                   (datetime(2009, 4, 8, 20, 15), 3.0),
                   (datetime(2009, 4, 8, 20, 30), 3.0),
                   (datetime(2009, 4, 8, 20, 45), 3.0),
                   (datetime(2009, 4, 8, 21, 0), 3.0),
                   (datetime(2009, 4, 9, 15, 0), 3.0),
                   (datetime(2009, 4, 9, 15, 15), 3.0),
                   (datetime(2009, 4, 9, 15, 30), 3.0),
                   (datetime(2009, 4, 9, 15, 45), 3.0),
                   (datetime(2009, 4, 9, 16, 0), 3.0),
                   (datetime(2009, 4, 9, 16, 15), 3.0),
                   (datetime(2009, 4, 9, 16, 30), 3.0),
                   (datetime(2009, 4, 9, 16, 45), 3.0),
                   (datetime(2009, 4, 9, 17, 0), 3.0),
                   (datetime(2009, 4, 9, 17, 15), 3.0),
                   (datetime(2009, 4, 9, 17, 30), 3.0),
                   (datetime(2009, 4, 9, 17, 45), 3.0),
                   (datetime(2009, 4, 9, 18, 0), 3.0),
                   (datetime(2009, 4, 9, 18, 15), 3.0),
                   (datetime(2009, 4, 9, 18, 30), 3.0),
                   (datetime(2009, 4, 9, 18, 45), 3.0),
                   (datetime(2009, 4, 9, 19, 0), 3.0),
                   (datetime(2009, 4, 9, 19, 15), 3.0),
                   (datetime(2009, 4, 9, 19, 30), 3.0),
                   (datetime(2009, 4, 9, 19, 45), 3.0),
                   (datetime(2009, 4, 9, 20, 0), 3.0),
                   (datetime(2009, 4, 9, 20, 15), 3.0),
                   (datetime(2009, 4, 9, 20, 30), 3.0),
                   (datetime(2009, 4, 9, 20, 45), 3.0)
                   ]

        self.assertEqual(expected, results)

            
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

