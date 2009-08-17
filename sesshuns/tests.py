from copy                import copy
from datetime            import date, datetime, timedelta
from django.conf         import settings
from django.contrib.auth import models as m
from django.test.client  import Client
from django.http         import QueryDict
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

class TestPeriod(NellTestCase):

    def setUp(self):
        super(TestPeriod, self).setUp()
        self.sesshun = create_sesshun()
        self.fdata = {"session":  1
                    , "date":    "2009-6-1"
                    , "time":    "12:15"
                    , "duration": 4.25
                    , "backup":   False
                     }

    def test_update_from_post(self):
        p = Period()
        p.init_from_post(self.fdata)
        
        self.assertEqual(p.session, self.sesshun)
        self.assertEqual(p.start, datetime(2009, 6, 1, 12, 15))
        self.assertEqual(p.duration, self.fdata["duration"])
        self.assertEqual(p.backup, self.fdata["backup"])

    def test_jsondict(self):
         
        start = datetime(2009, 6, 1, 12, 15)
        dur   = 180
        
        p = Period()
        p.start = start
        p.duration = dur
        p.session = self.sesshun
        p.backup = True

        p.save()

        jd = p.jsondict()

        self.assertEqual(jd["duration"], dur)
        self.assertEqual(jd["date"], "2009-06-01")
        self.assertEqual(jd["time"], "12:15")

        p.delete()

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
        #print rgs[0].receivers.all()[0].abbreviation
        #print rgs[0].receivers.all()[1].abbreviation
        #print rgs[1].receivers.all()[0].abbreviation
        #print rgs[1].receivers.all()[1].abbreviation
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

class TestProject(NellTestCase):
    def test_get_blackouts1(self):
        p = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "A"
        }
        p.update_from_post(pdata)
        p.save()

        # Create Investigator1 and his 3 blackouts.
        user1 = User(sanctioned = True)
        user1.save()

        investigator1 = Investigators(project  = p
                                    , user     = user1
                                    , observer = True)
        investigator1.save()

        blackout11 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 11)
                            , end    = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 18)
                            , end    = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 2, 12)
                            , end    = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2 and her 2 blackouts.
        user2 = User(sanctioned = True)
        user2.save()

        investigator2 = Investigators(project  = p
                                    , user     = user2
                                    , observer = True)
        investigator2.save()

        blackout21 = Blackout(user   = user2
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 11)
                            , end    = datetime(2009, 1, 3, 11))
        blackout21.save()

        blackout22 = Blackout(user   = user2
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 18)
                            , end    = datetime(2009, 1, 4, 13))
        blackout22.save()

        # Now we can finally do our test.
        expected = [
            (datetime(2009, 1, 2, 12), datetime(2009, 1, 3, 11))
        ]

        r = p.get_blackouts()
        self.assertEquals(expected, r)

        # Clean up
        blackout22.delete()
        blackout21.delete()
        investigator2.delete()
        user2.delete()

        blackout13.delete()
        blackout12.delete()
        blackout11.delete()
        investigator1.delete()
        user1.delete()

        p.delete()

    def test_get_blackouts2(self):
        p = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "A"
        }
        p.update_from_post(pdata)
        p.save()

        # Create Investigator1 and his 3 blackouts.
        user1 = User(sanctioned = True)
        user1.save()

        investigator1 = Investigators(project  = p
                                    , user     = user1
                                    , observer = False) # NOT an observer
        investigator1.save()

        blackout11 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 11)
                            , end    = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 18)
                            , end    = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 2, 12)
                            , end    = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2 and her 2 blackouts.
        user2 = User(sanctioned = True)
        user2.save()

        investigator2 = Investigators(project  = p
                                    , user     = user2
                                    , observer = False) # NOT an observer
        investigator2.save()

        blackout21 = Blackout(user   = user2
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 11)
                            , end    = datetime(2009, 1, 3, 11))
        blackout21.save()

        blackout22 = Blackout(user   = user2
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 18)
                            , end    = datetime(2009, 1, 4, 13))
        blackout22.save()

        r = p.get_blackouts()
        self.assertEquals([], r)

        # Clean up
        blackout22.delete()
        blackout21.delete()
        investigator2.delete()
        user2.delete()

        blackout13.delete()
        blackout12.delete()
        blackout11.delete()
        investigator1.delete()
        user1.delete()

        p.delete()

    def test_get_blackouts3(self):
        p = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "A"
        }
        p.update_from_post(pdata)
        p.save()

        # Create Investigator1 and his 3 blackouts.
        user1 = User(sanctioned = True)
        user1.save()

        investigator1 = Investigators(project  = p
                                    , user     = user1
                                    , observer = True)
        investigator1.save()

        blackout11 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 11)
                            , end    = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 18)
                            , end    = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 2, 12)
                            , end    = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2 and her 2 blackouts.
        user2 = User(sanctioned = True)
        user2.save()

        investigator2 = Investigators(project  = p
                                    , user     = user2
                                    , observer = True)
        investigator2.save()

        # She's available all the time.

        r = p.get_blackouts()
        expected = [
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 3, 11))
          , (datetime(2009, 1, 1, 18), datetime(2009, 1, 4, 18))
          , (datetime(2009, 1, 2, 12), datetime(2009, 1, 4, 20))
        ]
        self.assertEquals(expected, r)

        # Clean up
        investigator2.delete()
        user2.delete()

        blackout13.delete()
        blackout12.delete()
        blackout11.delete()
        investigator1.delete()
        user1.delete()
        p.delete()

    def test_get_blackouts4(self):
        p = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "A"
        }
        p.update_from_post(pdata)
        p.save()

        # Create Investigator1 and his 3 blackouts.
        user1 = User(sanctioned = True)
        user1.save()

        investigator1 = Investigators(project  = p
                                    , user     = user1
                                    , observer = True)
        investigator1.save()

        blackout11 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 11)
                            , end    = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 1, 18)
                            , end    = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user   = user1
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 1, 2, 12)
                            , end    = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2 and her 2 blackouts.
        user2 = User(sanctioned = True)
        user2.save()

        investigator2 = Investigators(project  = p
                                    , user     = user2
                                    , observer = True)
        investigator2.save()

        blackout21 = Blackout(user   = user2
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 2, 1, 11)
                            , end    = datetime(2009, 2, 3, 11))
        blackout21.save()

        blackout22 = Blackout(user   = user2
                            , tz     = first(TimeZone.objects.all())
                            , repeat = first(Repeat.objects.all())
                            , start  = datetime(2009, 3, 1, 18)
                            , end    = datetime(2009, 3, 4, 13))
        blackout22.save()

        r = p.get_blackouts()
        self.assertEquals([], r) # Coordinated blackouts.

        # Clean up
        blackout22.delete()
        blackout21.delete()
        investigator2.delete()
        user2.delete()

        blackout13.delete()
        blackout12.delete()
        blackout11.delete()
        investigator1.delete()
        user1.delete()

        p.delete()

    def test_init_from_post(self):
        p1 = Project()
        p2 = Project()
        self.gitrdone(p1, p1.init_from_post, p2, p2.init_from_post)

        p3 = Project()
        p3.init_from_post({})

    def test_update_from_post(self):
        p1 = Project()
        p2 = Project()
        self.gitrdone(p1, p1.update_from_post, p2, p2.update_from_post)

    def gitrdone(self, p1, f1, p2, f2):
        p_fdata = {"semester" : "09A"
                 , "type"     : "science"
                 , "total_time" : "10.0"
                 , "PSC_time"   : "10.0"
                 , "sem_time"   : "10.0"
                 , "grade"      : "A"
                   }
        f1(p_fdata)
        self.defaultAssertion(p_fdata, p1)
        
        p_fdata1 = {"semester" : "09A"
                 , "type"     : "science"
                 , "total_time" : "10.0, 5.0"
                 , "PSC_time"   : "10.0, 5.0"
                 , "sem_time"   : "10.0, 5.0"
                 , "grade"      : "A, B"
                   }
        f2(p_fdata1)
        self.defaultAssertion(p_fdata1, p2)

        p_fdata = {"semester" : "09A"
                 , "type"     : "science"
                 , "total_time" : "10.0, 5.0, 1.0"
                 , "PSC_time"   : "10.0, 5.0, 1.0"
                 , "sem_time"   : "10.0, 5.0, 1.0"
                 , "grade"      : "A, B, C"
                   }
        f2(p_fdata)
        self.defaultAssertion(p_fdata, p2)

        f2(p_fdata1)
        self.defaultAssertion(p_fdata1, p2)

    def defaultAssertion(self, p_fdata, p):
        totals = map(float, p_fdata.get("total_time").split(', '))
        pscs     = map(float, p_fdata.get("PSC_time", "").split(', '))
        max_sems = map(float, p_fdata.get("sem_time", "").split(', '))
        grades   = map(grade_abc_2_float, p_fdata.get("grade", "").split(', '))
        for a in p.allotments.all():
            self.assertTrue(a.total_time in totals)
            self.assertTrue(a.psc_time in pscs)
            self.assertTrue(a.max_semester_time in max_sems)
            self.assertTrue(a.grade in grades)
        
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
        ldata["enabled"] = "true"
        s.update_from_post(ldata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(ldata["freq"]))
        self.assertEqual(s.allotment.total_time, float(ldata["total_time"]))
        self.assertEqual(s.target_set.get().source, ldata["source"])
        self.assertEqual(s.status.enabled, ldata["enabled"] == "true")

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
        ldata["enabled"] = "true" 
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
            fltGrade = grade_abc_2_float(letter)
            self.assertEqual(num, fltGrade)

    def test_grade_float_2_abc(self):
        s = Sesshun()
        values = [('A',4.0),('B',3.0),('C',2.0)]
        for letter, num in values:
            letterGrade = grade_float_2_abc(num)
            self.assertEqual(letter, letterGrade)

# Testing View Resources

class TestPeriodResource(NellTestCase):

    def setUp(self):
        super(TestPeriodResource, self).setUp()
        self.rootURL = '/periods'
        self.sess = create_sesshun()
        self.client = Client()
        self.fdata = {'session'  : self.sess.id
                    , 'date'    : '2009-06-01'
                    , 'time'    : '00:00'
                    , 'duration' : 1.0
                    , 'backup'   : True}
        self.p = Period()
        self.p.init_from_post(self.fdata)
        self.p.save()

    def test_create(self):
        response = self.client.post(self.rootURL, self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_create_empty(self):
        response = self.client.post(self.rootURL)
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        url = "%s?startPeriods=%s&daysPeriods=%d" % \
                            (self.rootURL 
                           , self.fdata['date'] + '%20' + self.fdata['time'] + ':00'
                           , 2)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.content[:11], '{"total": 1')

    def test_read_keywords(self):
        # use a date range that picks up our one period
        url = "%s?startPeriods=%s&daysPeriods=%d" % \
                            (self.rootURL 
                           , self.fdata['date'] + '%20' + self.fdata['time'] + ':00'
                           , 3)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.content[:11], '{"total": 1')
        # now use a date range that doesn't
        url = "%s?startPeriods=%s&daysPeriods=%d" % (self.rootURL 
                                                   , '2009-06-02 00:00:00' 
                                                   , 3)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.content[:11], '{"total": 0')


    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"})
        response = self.client.post('%s/%s' % (self.rootURL, self.p.id), fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.post('%s/%s' % (self.rootURL, self.p.id)
                                  , {"_method" : "delete"})
        self.failUnlessEqual(response.status_code, 200)

class TestProjectResource(NellTestCase):

    def setUp(self):
        super(TestProjectResource, self).setUp()
        self.client = Client()
        self.fdata = {'semester'   : '09C'
                    , 'type'       : 'science'
                    , 'pcode'      : 'mike'
                    , 'name'       : 'mikes awesome project!'
                    , 'PSC_time'   : '100.0'
                    , 'total_time' : '100.0'
                    , 'sem_time'   : '50.0'
                      }
        self.p = Project()
        self.p.init_from_post(self.fdata)
        self.p.save()

    def test_create(self):
        response = self.client.post('/projects', self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_create_empty(self):
        response = self.client.post('/projects')
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/projects')
        self.failUnlessEqual(response.status_code, 200)

    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"})
        response = self.client.post('/projects/%s' % self.p.id, fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.post('/projects/%s' % self.p.id, {"_method" : "delete"})
        self.failUnlessEqual(response.status_code, 200)
        
    
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
               , 'receiver': ['(K | Ka) | Q']
               , 'backup': ['false']
                 }

        response = self.client.post('/sessions', fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/sessions')
        self.failUnlessEqual(response.status_code, 200)

        response = self.client.get('/sessions', {'limit'     : 50
                                               , 'sortField' : 'null'
                                               , 'sortDir'   : 'NONE'
                                               , 'offset'    : 0
                                                 })
        self.failUnlessEqual(response.status_code, 200)

        response = self.client.get('/sessions', {'limit'     : 50
                                               , 'sortField' : 'null'
                                               , 'sortDir'   : 'NONE'
                                               , 'offset'    : 0
                                               , 'filterType': "Open"
                                               , 'filterFreq': "20"
                                               , 'filterClp' : "True"
                                                 })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("windowed" not in response.content)

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
        create_sesshun()
        c = Client()
        response = c.get('/sessions/options', dict(mode='project_codes'))
        self.assertEquals(response.content,
                          '{"project codes": ["GBT09A-001"]}')
        response = c.get('/sessions/options', dict(mode='session_handles'))
        self.assertEquals(response.content,
                          '{"session handles": ["Low Frequency With No RFI (GBT09A-001)"]}')

# Testing Observers UI

class TestObservers(NellTestCase):

    def setUp(self):
        super(TestObservers, self).setUp()

        # Don't use CAS for authentication during unit tests
        if 'django_cas.backends.CASBackend' in settings.AUTHENTICATION_BACKENDS:
            settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS[:-1]
        if 'django_cas.middleware.CASMiddleware' in settings.MIDDLEWARE_CLASSES:
            settings.MIDDLEWARE_CLASSES      = settings.MIDDLEWARE_CLASSES[:-1]

        self.client = Client()
        
        self.auth_user = m.User.objects.create_user('dss', 'dss@nrao.edu', 'asdf5!')
        self.auth_user.is_staff = True
        self.auth_user.save()

        self.u = User(first_name = "Test"
                    , last_name  = "User"
                    , role       = first(Role.objects.all())
                    , username   = self.auth_user.username
                      )
        self.u.save()
        self.client.login(username = "dss", password = "asdf5!")
        
        self.p = Project()
        self.p.init_from_post({'semester'   : '09C'
                             , 'type'       : 'science'
                             , 'pcode'      : 'mike'
                             , 'name'       : 'mikes awesome project!'
                             , 'PSC_time'   : '100.0'
                             , 'total_time' : '100.0'
                             , 'sem_time'   : '50.0'
                               })
        self.p.save()

        i = Investigators(project = self.p
                        , user    = self.u
                         )
        i.save()

        fdata2 = copy(fdata)
        fdata2.update({'source_v' : 1.0
                     , 'source_h' : 1.0
                     , 'source'   : 'testing'
                       })
        self.s = Sesshun()
        self.s.init_from_post(fdata2)
        self.s.project = self.p
        self.s.save()

    def tearDown(self):
        super(TestObservers, self).tearDown()

    def get(self, url, data = {}):
        """
        Sets the USER extra kwar
        """
        return self.client.get(url, data, USER = self.auth_user.username)

    def post(self, url, data = {}):
        """
        Sets the USER extra kwar
        """
        return self.client.post(url, data, USER = self.auth_user.username)

    def test_profile(self):
        response = self.get('/profile/%s' % self.u.id)
        self.failUnlessEqual(response.status_code, 200)

    def test_project(self):
        response = self.get('/project/%s' % self.p.pcode)
        self.failUnlessEqual(response.status_code, 200)

    def test_search(self):
        response = self.post('/search', {'search' : 'Test'})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("User" in response.content)

    def test_toggle_session(self):
        response = self.post(
            '/project/%s/session/%s/enable' % (self.p.pcode, self.s.name))
        self.failUnlessEqual(response.status_code, 302)
        s = first(Sesshun.objects.filter(id = self.s.id))
        self.assertEqual(s.status.enabled, True)

    def test_toggle_observer(self):
        i_id = first(self.p.investigators_set.all()).id
        response = self.post(
            '/project/%s/investigator/%s/observer' % (self.p.pcode, i_id))
        self.failUnlessEqual(response.status_code, 302)
        i = first(Investigators.objects.filter(id = i_id))
        self.assertEqual(i.observer, True)

    def test_dynamic_contact_form(self):
        response = self.get('/profile/%s/dynamic_contact/form' % self.u.id)
        self.failUnlessEqual(response.status_code, 200)

    def test_dynamic_contact_save(self):
        data = {'contact_instructions' : "I'll be at Bob's house."}
        response = self.post('/profile/%s/dynamic_contact' % self.u.id, data)
        self.failUnlessEqual(response.status_code, 302)
        u = first(User.objects.filter(id = self.u.id))
        self.assertEqual(u.contact_instructions, data.get('contact_instructions'))

    def create_blackout(self):
        b             = Blackout(user = self.u)
        b.start       = datetime(2009, 1, 1)
        b.end         = datetime(2009, 12, 31)
        b.tz          = first(TimeZone.objects.all())
        b.repeat      = first(Repeat.objects.all())
        b.description = "This is a test blackout."
        b.save()
        return b
        
    def test_blackout_form(self):
        response = self.get('/profile/%s/blackout/form' % self.u.id)
        self.failUnlessEqual(response.status_code, 200)

        b = self.create_blackout()
        data = {'_method' : 'PUT'
              , 'id'      : b.id
                }
        response = self.get('/profile/%s/blackout/form' % self.u.id, data)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue(b.description in response.content)

    def test_blackout(self):
        b     = self.create_blackout()
        start = datetime(2009, 1, 1)
        end   = datetime(2009, 1, 31)
        until = datetime(2010, 1, 31)
        data = {'start'       : start.date().strftime("%m/%d/%Y")
              , 'starttime'   : start.time().strftime("%H:%M")
              , 'end'         : end.date().strftime("%m/%d/%Y")
              , 'endtime'     : end.time().strftime("%H:%M")
              , 'tz'          : 'UTC'
              , 'repeat'      : 'Once'
              , 'until'       : until.strftime("%m/%d/%Y")
              , 'untiltime'   : until.strftime("%H:%M")
              , 'description' : "This is a test blackout."
              , '_method'     : 'PUT'
              , 'id'          : b.id
                }

        response = self.post(
            '/profile/%s/blackout' % self.u.id, data)
        b = first(Blackout.objects.filter(id = b.id))
        self.assertEqual(b.end.date().strftime("%m/%d/%Y") , data.get('end'))
        self.failUnlessEqual(response.status_code, 302)
        
        response = self.get(
            '/profile/%s/blackout' % self.u.id
          , {'_method' : 'DELETE', 'id' : b.id})
        self.failUnlessEqual(response.status_code, 302)

        data['end'] = date(2009, 5, 31).strftime("%m/%d/%Y")
        _ = data.pop('_method')
        _ = data.pop('id')
        response    = self.post(
            '/profile/%s/blackout' % self.u.id, data)
        self.failUnlessEqual(response.status_code, 302)
        b = first(self.u.blackout_set.all())
        self.assertEqual(b.end.date().strftime("%m/%d/%Y"), data.get('end'))
        b.delete()

        data['until'] = ''
        response    = self.post(
            '/profile/%s/blackout' % self.u.id, data)
        self.failUnlessEqual(response.status_code, 302)

# Testing Utilities
class TestDBReporter(NellTestCase):

    def test_DBReporter(self):
        "imply make sure that no exceptions are raised."
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
        self.assertEquals(rc.normalize('K | (Ka | Q)'),
                                       [['K', 'Ka', 'Q']])
        try:
            self.assertEquals(rc.normalize('J'), [['J']])
        except ValueError:
            pass
        else:
            self.fail()
        try:
            self.assertEquals(rc.normalize('K | Ka | Q'),
                                           [['K', 'Ka', 'Q']])
            self.assertEquals(rc.normalize('J'), [['J']])
        except SyntaxError:
            pass
        else:
            self.fail()

class TestConsolidateBlackouts(NellTestCase):

    def test_consolidate_blackouts(self):
        starts = [
            datetime(2009, 1, 1, 11)
          , datetime(2009, 1, 1, 11)
          , datetime(2009, 1, 1, 18)
          , datetime(2009, 1, 2, 11)
          , datetime(2009, 1, 2, 12)
        ]
        ends   = [
            datetime(2009, 1, 3, 11)
          , datetime(2009, 1, 3, 11)
          , datetime(2009, 1, 4, 18)
          , datetime(2009, 1, 4, 13)
          , datetime(2009, 1, 4, 20)
        ]
        expected = [
            # begin = b5 start, end = b1 end
            (datetime(2009, 1, 2, 12), datetime(2009, 1, 3, 11))
        ]

        r = consolidate_blackouts([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        starts = [
            datetime(2009, 1, 1, 11)
          , datetime(2009, 1, 1, 11)
        ]
        ends   = [
            datetime(2009, 1, 3, 11)
          , datetime(2009, 1, 3, 11)
        ]
        expected = [
            # begin = b1 start, end = b1 end
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 3, 11))
        ]

        r = consolidate_blackouts([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        starts = [
            datetime(2009, 1, 1, 11)
          , datetime(2009, 1, 4, 11)
        ]
        ends   = [
            datetime(2009, 1, 3, 11)
          , datetime(2009, 1, 5, 11)
        ]
        expected = [
            # nothing to reduce
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 3, 11))
          , (datetime(2009, 1, 4, 11), datetime(2009, 1, 5, 11))
        ]

        r = consolidate_blackouts([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        r = consolidate_blackouts([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        starts = [
            datetime(2009, 1, 1, 11)
        ]
        ends   = [
            datetime(2009, 1, 3, 11)
        ]
        expected = [
            # one conflict
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 3, 11))
        ]

        r = consolidate_blackouts([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        # No conflicts.
        r = consolidate_blackouts([])
        self.assertEquals([], r)
