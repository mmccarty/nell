from copy                import copy
from datetime            import date, datetime, timedelta
from time                import mktime
from django.conf         import settings
from django.contrib.auth import models as m
from django.test.client  import Client
from django.http         import QueryDict
import simplejson as json
import lxml.etree as et
import MySQLdb as mysql

from httpadapters                 import *
from models                       import *
from nell.test_utils.NellTestCase import NellTestCase
from nell.tools                   import DBReporter, ScheduleTools
from nell.tools                   import IcalAntioch, TimeAccounting
from nell.utilities.database      import DSSPrime2DSS
from nell.utilities.receiver      import ReceiverCompile
from nell.utilities               import UserInfo, NRAOBosDB, UpdateEphemeris
from nell.utilities               import SchedulingNotifier 
from nell.utilities               import PSTMirrorDB, PSTQueryService

# Test field data
fdata = {"total_time": "3"
       , "req_max": "6"
       , "name": "Low Frequency With No RFI"
       , "grade": 4.0
       , "science": "pulsar"
       , "orig_ID": "0"
       , "between": "0"
       , "proj_code": "GBT09A-001"
       , "PSC_time": "2"
       , "sem_time": 0.0
       , "req_min": "2"
       , "freq": 6.0
       , "type": "open"
       , "source" : "blah"
       , "enabled" : False
       , "authorized" : False
       , "complete" : False
       , "backup" : False
       , "lst_ex" : ""
       , "el_limit" : 25.0
         }

def create_sesshun():
    "Utility method for creating a Sesshun to test."

    s = Sesshun()
    s_adapter = SessionHttpAdapter(s)
    s_adapter.set_base_fields(fdata)
    allot = Allotment(psc_time          = float(fdata.get("PSC_time", 0.0))
                    , total_time        = float(fdata.get("total_time", 0.0))
                    , max_semester_time = float(fdata.get("sem_time", 0.0))
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
class TestUser(NellTestCase):
    def setUp(self):
        # TBF: From here down, till noted, is the same code as TestProject
        super(TestUser, self).setUp()

        self.project = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "4.0"
        }
        adapter = ProjectHttpAdapter(self.project)
        adapter.update_from_post(pdata)

        obsRole = first(Role.objects.filter(role = "Observer"))

        # Create Investigator1 and his 3 blackouts.
        self.user1 = User(sanctioned = True, role = obsRole)
        self.user1.save()

        self.investigator1 =  Investigator(project  = self.project
                                         , user     = self.user1
                                         , observer = True)
        self.investigator1.save()

        self.user2 = User(sanctioned = True, role = obsRole)
        self.user2.save()

        self.investigator2 =  Investigator(project  = self.project
                                         , user     = self.user2
                                         , observer = True)
        self.investigator2.save()

        self.sesshun = create_sesshun()
        self.sesshun.project = self.project
        self.sesshun.save()

        # TBF: end of redundant code, now add periods
        #period_data = {"session" : self.sesshun
        #             , "date" 
        state = first(Period_State.objects.filter(abbreviation = 'S'))
        self.period1 = Period(session  = self.sesshun
                            , start    = datetime(2010, 10, 1, 0, 0, 0)
                            , duration = 1.0
                            , state    = state
                            , backup   = False)
        self.period1.save()                    
        self.period2 = Period(session  = self.sesshun
                            , start    = datetime(2010, 10, 2, 5, 0, 0)
                            , duration = 3.5
                            , state    = state
                            , backup   = False)
        self.period2.save()                    

        # add the project friend
        self.user3 = User(sanctioned = True, role = obsRole)
        self.user3.save()
        self.project.friend = self.user3
        self.project.save()

        # add an unrelated user
        self.user4 = User(sanctioned = True, role = obsRole)
        self.user4.save()

    def tearDown(self):
        self.investigator2.delete()
        self.user2.delete()
        self.investigator1.delete()
        self.user1.delete()
        self.period1.remove() #delete()
        self.period2.remove() #delete()
        self.project.delete()
        self.user3.delete()
        self.user4.delete()

    def test_canViewProject(self):

        pcode = self.project.pcode
        self.assertEqual(True, self.user1.canViewProject(pcode))
        self.assertEqual(True, self.user2.canViewProject(pcode))
        self.assertEqual(True, self.user3.canViewProject(pcode))
        self.assertEqual(False, self.user4.canViewProject(pcode))

    def test_canViewUser(self):

        self.assertEqual(True, self.user1.canViewUser(self.user2))
        self.assertEqual(True, self.user2.canViewUser(self.user1))
        self.assertEqual(True, self.user3.canViewUser(self.user1))
        self.assertEqual(True, self.user3.canViewUser(self.user2))
        self.assertEqual(False, self.user1.canViewUser(self.user3))
        self.assertEqual(False, self.user2.canViewUser(self.user3))
        self.assertEqual(False, self.user4.canViewUser(self.user1))
        self.assertEqual(False, self.user4.canViewUser(self.user2))
        self.assertEqual(False, self.user4.canViewUser(self.user3))

    def test_getPeriods(self):
        
        # exp values
        periods = [self.period1, self.period2]
        sep1 = datetime(2010,  9, 1, 0, 0, 0)
        oct2 = datetime(2010, 10, 2, 0, 0, 0)
        dec1 = datetime(2010, 12, 1, 0, 0, 0)

        self.assertEqual(periods, self.user1.getPeriods())
        self.assertEqual(periods, self.user2.getPeriods())
        self.assertEqual(periods, self.user1.getUpcomingPeriods(sep1))
        self.assertEqual(periods, self.user2.getUpcomingPeriods(sep1))
        self.assertEqual([self.period2]
                                , self.user2.getUpcomingPeriods(oct2))
        self.assertEqual([self.period1]
                                , self.user2.getObservedPeriods(oct2))
        self.assertEqual([],      self.user2.getUpcomingPeriods(dec1))

class TestWindow(NellTestCase):
    def setUp(self):
        super(TestWindow, self).setUp()
        self.sesshun = create_sesshun()
        self.sesshun.session_type = Session_Type.get_type("windowed")
        self.sesshun.save()
        dt = datetime(2009, 6, 1, 12, 15)
        pending = first(Period_State.objects.filter(abbreviation = "P"))
        pa = Period_Accounting(scheduled = 0.0)
        pa.save()
        self.default_period = Period(session = self.sesshun
                                   , start = dt
                                   , duration = 5.0
                                   , state = pending
                                   , accounting = pa
                                   )
        self.default_period.save()    
        pjson = PeriodHttpAdapter(self.default_period).jsondict('UTC', 1.1)
        self.fdata = {"session":  1
                    , "start":    "2009-06-01"
                    , "duration": 7
                    , "default_date" : pjson['date'] 
                    , "default_time" : pjson['time'] 
                    , "default_duration" : pjson['duration'] 
                    , "default_state" : pjson['state'] 
                    }

    def test_update_from_post(self):
        w = Window()
        adapter = WindowHttpAdapter(w)
        adapter.init_from_post(self.fdata)
       
        self.assertEqual(w.session, self.sesshun)
        self.assertEqual(w.start_date, date(2009, 6, 1))
        self.assertEqual(w.duration, self.fdata["duration"])
        self.assertEqual(w.default_period.start, self.default_period.start)
        self.assertEqual(w.period, None)

    def test_jsondict(self):
         
        start = datetime(2009, 6, 1)
        startStr = start.strftime("%Y-%m-%d")
        dur   = 7 # days
        end = start + timedelta(days = dur - 1)
        endStr = end.strftime("%Y-%m-%d")
        
        w = Window()
        w.start_date = start
        w.duration = dur
        w.session = self.sesshun
        w.default_period = self.default_period

        w.save()

        adapter = WindowHttpAdapter(w)

        jd = adapter.jsondict()

        self.assertEqual(jd["duration"], dur)
        self.assertEqual(jd["start"], startStr)
        self.assertEqual(jd["end"], endStr)
        self.assertEqual(jd["session"], SessionHttpAdapter(self.sesshun).jsondict())
        self.assertEqual(jd["chosen_period"], None)

        w.delete()

    def test_reconcile(self):

        deleted   = Period_State.get_state("D")
        pending   = Period_State.get_state("P")
        scheduled = Period_State.get_state("S")

        start = datetime(2009, 6, 1)
        dur   = 7 # days
        
        w = Window()
        w.start_date = start
        w.duration = dur
        w.session = self.sesshun
        w.default_period = self.default_period
        w.save()
        w_id = w.id

        # test
        self.assertEquals(w.default_period.state, pending) 
        self.assertEquals(w.state(), pending) 

        # this should move the default_period to scheduled
        # and copy the defatul_period to period
        w.reconcile()

        # test
        # get it fresh from the DB
        w = first(Window.objects.filter(id = w_id)) 
        self.assertEquals(w.default_period.state, scheduled) 
        self.assertTrue(w.period is not None)
        self.assertEquals(w.period.state, scheduled) 
        self.assertEquals(w.period.id, w.default_period.id) 
        self.assertEquals(w.state(), scheduled) 

    def test_reconcile_2(self):

        deleted   = Period_State.get_state("D")
        pending   = Period_State.get_state("P")
        scheduled = Period_State.get_state("S")
       
        # the period to be scheduled
        pa = Period_Accounting(scheduled = 0.0)
        pa.save()
        dt = self.default_period.start - timedelta(days = 2)
        period = Period(session = self.sesshun
                                   , start = dt
                                   , duration = 5.0
                                   , state = pending
                                   , accounting = pa
                                   )
        period.save()    

        start = datetime(2009, 6, 1)
        dur   = 7 # days
        
        w = Window()
        w.start_date = start
        w.duration = dur
        w.session = self.sesshun
        w.default_period = self.default_period
        w.period = period
        w.save()
        w_id = w.id

        # test
        self.assertEquals(w.default_period.state, pending) 
        self.assertEquals(w.period.state, pending) 
        self.assertEquals(w.state(), pending) 

        # this should move the default_period to deleted
        # and the chosen period to scheduled
        w.reconcile()

        # test
        # get it fresh from the DB
        w = first(Window.objects.filter(id = w_id)) 
        self.assertEquals(w.default_period.state, deleted) 
        self.assertTrue(w.period is not None)
        self.assertEquals(w.period.state, scheduled) 
        self.assertEquals(w.state(), scheduled) 

class TestPeriod(NellTestCase):

    def setUp(self):
        super(TestPeriod, self).setUp()
        self.sesshun = create_sesshun()
        self.fdata = {"session":  1
                    , "date":    "2009-6-1"
                    , "time":    "12:15"
                    , "duration": 4.25
                    , "backup":   False
                    , "receivers": "L, X"
                     }

    def test_create(self):
        
        # make sure the sesshun has some rcvrs
        SessionHttpAdapter(self.sesshun).save_receivers("L")

        p = PeriodHttpAdapter.create(session = self.sesshun
                        , start = datetime(2009, 10, 1)
                        , duration = 10.0
                        )

        self.assertEqual(p.session.id, 1)
        self.assertEqual(p.duration, 10.0)
        self.assertEqual(p.receiver_list(), "L")

    def test_update_from_post(self):
        p = Period()
        adapter = PeriodHttpAdapter(p)
        adapter.init_from_post(self.fdata, 'UTC')
        
        self.assertEqual(p.session, self.sesshun)
        self.assertEqual(p.start, datetime(2009, 6, 1, 12, 15))
        self.assertEqual(p.duration, self.fdata["duration"])
        self.assertEqual(p.backup, self.fdata["backup"])
        self.assertEqual(len(p.receivers.all()), 2)
        #self.assertEqual(p.receivers.all(), 2)

    def test_jsondict(self):
         
        start = datetime(2009, 6, 1, 12, 15)
        dur   = 180
        
        pa = Period_Accounting(scheduled = 0)
        pa.save()

        p = Period()
        p.start = start
        p.duration = dur
        p.session = self.sesshun
        p.backup = True
        p.state = first(Period_State.objects.filter(abbreviation = 'P'))
        p.accounting = pa

        p.save()

        L = Receiver.get_rcvr("L")
        X = Receiver.get_rcvr("X")
        pr = Period_Receiver(period = p, receiver = L)
        pr.save()
        pr = Period_Receiver(period = p, receiver = X)
        pr.save()

        jd = PeriodHttpAdapter(p).jsondict('UTC', 1.1)

        self.assertEqual(jd["duration"], dur)
        self.assertEqual(jd["date"], "2009-06-01")
        self.assertEqual(jd["time"], "12:15")
        self.assertEqual(jd["state"], "P")
        self.assertEqual(jd["receivers"], "L, X")

        p.delete()

    def test_windows(self):
        pending = Period_State.get_state('P')

        # create a window w/ a period
        original_type = self.sesshun.session_type
        self.sesshun.session_type = Session_Type.get_type("windowed")

        start = datetime(2009, 6, 1, 12, 15)
        dur   = 180

        p = Period()
        p.start = start
        p.duration = dur
        p.session = self.sesshun
        p.state = pending
        p.accounting = Period_Accounting(scheduled = 0.0)
        p.accounting.save()
        p.save()
        p_id = p.id

        wstart = (start - timedelta(days = 7)).date()
        w = Window(start_date = wstart
                 , duration = 10 # days
                 , session = self.sesshun
                 , default_period = p)
        w.save()         

        # and a period w/ out a window         
        p2 = Period()
        p2.start = start
        p2.duration = dur
        p2.session = self.sesshun
        p2.state = pending
        pa2 = Period_Accounting(scheduled = 0.0)
        pa2.save()
        p2.accounting = pa2
        p2.save()
        p2_id = p2.id

        # test
        self.assertEquals(True,  p.is_windowed())
        self.assertEquals(True,  p.has_valid_windows())
        self.assertEquals(True,  p2.is_windowed())
        self.assertEquals(False, p2.has_valid_windows())
        self.assertEquals(w,     p.get_default_window())
        self.assertEquals(w,     p.get_window())
        self.assertEquals(True,  p.is_windowed_default())

        # now assign this second period as the 'chosen' period for the win.
        w.period = p2
        w.save()

        # test
        self.assertEquals(True,  p2.is_windowed())
        self.assertEquals(True,  p2.has_valid_windows())
        self.assertEquals(None,  p2.get_default_window())
        self.assertEquals(w,     p2.get_window())
        self.assertEquals(False, p2.is_windowed_default())

        # now publish!
        #p.publish()

        # test
        #deleted = Period_State.get_state("D")
        #scheduled = Period_State.get_state("S")
        # get these periods fresh from db again
        #p = first(Period.objects.filter(id = p_id))
        #p2 = first(Period.objects.filter(id = p2_id))
        #self.assertEquals(deleted, p.state)
        #self.assertEquals(scheduled, p2.state)

        # cleanup
        self.sesshun.session_type = original_type 
        w.delete()
        p.delete()
        p2.save()

    def test_get_periods(self):

        # setup some periods
        times = [(datetime(2000, 1, 1, 0), 5.0)
               , (datetime(2000, 1, 1, 5), 3.0)
               , (datetime(2000, 1, 1, 8), 4.0)
               ]
        ps = []
        state = first(Period_State.objects.filter(abbreviation = 'P'))
        for start, dur in times:
            pa = Period_Accounting(scheduled = dur)
            pa.save()
            p = Period( session    = self.sesshun
                      , start      = start
                      , duration   = dur
                      , state      = state
                      , accounting = pa
                      )
            p.save()          
            ps.append(p)

        # now try and retrieve them from the DB:
        # get them all
        dt1 = datetime(2000, 1, 1, 0)
        dur = 12 * 60
        ps1 = Period.get_periods(dt1, dur)
        self.assertEquals(ps1, ps)

        # get them all because the first overlaps
        dt1 = datetime(2000, 1, 1, 1)
        dur = 12 * 60
        ps1 = Period.get_periods(dt1, dur)
        self.assertEquals(ps1, ps)

        # now leave out the first
        dt1 = datetime(2000, 1, 1, 5)
        dur = 12 * 60
        ps1 = Period.get_periods(dt1, dur)
        self.assertEquals(ps1, ps[1:])

        # keep getting the last one too
        dt1 = datetime(2000, 1, 1, 5)
        dur = 6 * 60
        ps1 = Period.get_periods(dt1, dur)
        self.assertEquals(ps1, ps[1:])

        # now just get the middle one
        dt1 = datetime(2000, 1, 1, 5)
        dur = 3 * 60
        ps1 = Period.get_periods(dt1, dur)
        self.assertEquals(ps1, [ps[1]])

        # again, just the middle one
        dt1 = datetime(2000, 1, 1, 6)
        dur = 2 * 60
        ps1 = Period.get_periods(dt1, dur)
        self.assertEquals(ps1, [ps[1]])

        # cleanup
        for p in ps:
            p.delete()

    def test_has_required_receivers(self):
        p = PeriodHttpAdapter.create(session = self.sesshun
                        , start = datetime(2009, 11, 1)
                        , duration = 10.0
                        )

        # No receivers for the session yet.
        self.assertEquals(False, p.has_required_receivers())

        # Make sure the sesshun has some rcvrs
        SessionHttpAdapter(self.sesshun).save_receivers("S")

        # No schedule yet.
        self.assertEquals(False, p.has_required_receivers())

        # Make a schedule.
        rs = Receiver_Schedule()
        rs.start_date = p.start
        rs.receiver   = Receiver.objects.filter(abbreviation = "L")[0]
        rs.save()

        # Receiver still not up on schedule yet.
        self.assertEquals(False, p.has_required_receivers())

        # Make sure the sesshun has a receiver on the schedule.
        rg = Receiver_Group.objects.filter(session = self.sesshun)[0]
        rg.delete()
        SessionHttpAdapter(self.sesshun).save_receivers("L")

        # Receiver now on schedule.
        self.assertEquals(True, p.has_required_receivers())

    def test_has_observed_rcvrs_in_schedule(self):
        p = PeriodHttpAdapter.create(session = self.sesshun
                        , start = datetime(2009, 11, 1)
                        , duration = 10.0
                        )

        # No receivers for the session yet.
        self.assertEquals(False, p.has_observed_rcvrs_in_schedule())

        # Make sure the period has some rcvrs
        #self.sesshun.save_receivers("S")
        adapter = PeriodHttpAdapter(p)
        adapter.update_rcvrs_from_post({"receivers" : "S"})

        # No schedule yet.
        self.assertEquals(False, p.has_observed_rcvrs_in_schedule())

        # Make a schedule.
        rs = Receiver_Schedule()
        rs.start_date = p.start
        rs.receiver   = Receiver.objects.filter(abbreviation = "L")[0]
        rs.save()

        # Receiver still not up on schedule yet.
        self.assertEquals(False, p.has_observed_rcvrs_in_schedule())

        # Make sure the period observed w/ a receiver on the schedule.
        #rg = Receiver_Group.objects.filter(session = self.sesshun)[0]
        #rg.delete()
        #self.sesshun.save_receivers("L")
        adapter.update_rcvrs_from_post({"receivers" : "L"})

        # Receiver now on schedule.
        self.assertEquals(True, p.has_observed_rcvrs_in_schedule())

        # now insist that the period observed w/ two rcvrs, one of which
        # was *not* on the schedule - should return false
        adapter.update_rcvrs_from_post({"receivers" : "L, S"})
        self.assertEquals(False, p.has_observed_rcvrs_in_schedule())

class TestReceiver(NellTestCase):

    def setUp(self):
        super(TestReceiver, self).setUp()
        self.client = Client()
        s = Sesshun()
        adapter = SessionHttpAdapter(s)
        adapter.init_from_post({})
        s.save()

    def test_get_abbreviations(self):
        nn = Receiver.get_abbreviations()
        self.assertTrue(len(nn) > 17)
        self.assertEquals([n for n in nn if n == 'Ka'], ['Ka'])

    def test_save_receivers(self):
        s = Sesshun.objects.all()[0]
        rcvr = ''
        adapter = SessionHttpAdapter(s)
        adapter.save_receivers(rcvr)
        rgs = s.receiver_group_set.all()
        self.assertEqual(0, len(rgs))
        rcvr = 'L'
        adapter.save_receivers(rcvr)
        rgs = s.receiver_group_set.all()
        self.assertEqual(1, len(rgs))
        self.assertEqual(rcvr, rgs[0].receivers.all()[0].abbreviation)

        s.receiver_group_set.all().delete()
        adapter.save_receivers('L | (X & S)')
        rgs = s.receiver_group_set.all().order_by('id')
        #print rgs
        # TBF WTF? now it is S, then it is X??
        #print rgs[0].receivers.all()[1].abbreviation
        self.assertEqual(2, len(rgs))
        #print rgs[0].receivers.all()[0].abbreviation
        #print rgs[0].receivers.all()[1].abbreviation
        #print rgs[1].receivers.all()[0].abbreviation
        #print rgs[1].receivers.all()[1].abbreviation
        print "Receiver Groups", rgs
        rs = rgs[0].receivers.all().order_by('id')
        print "Receivers", [r.abbreviation for r in rs]
        self.assertEqual('L', rs[0].abbreviation)
        self.assertEqual('X', rs[1].abbreviation)
        rs = rgs[1].receivers.all().order_by('id')
        print "Receivers", [r.abbreviation for r in rs]
        self.assertEqual('L', rs[0].abbreviation)
        self.assertEqual('S', rs[1].abbreviation)

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


    def test_extract_diff_schedule(self):
        startdate = datetime(2009, 4, 6, 12)
        duration = 15
        diff = Receiver_Schedule.extract_diff_schedule(startdate = startdate,
                                                       days = duration)
        expected = [datetime(2009, 4, 6, 0, 0)
                  , datetime(2009, 4, 11, 0, 0)
                  , datetime(2009, 4, 16, 0, 0)
                  , datetime(2009, 4, 21, 0, 0)]
        self.assertEqual(expected, [d[0] for d in diff])
        jdiff = Receiver_Schedule.jsondict_diff(diff)
        expected = {'diff_schedule': \
            [{'down': [], 'up': [u'RRI', u'342', u'450'], 'day': '04/06/2009'}
           , {'down': [u'RRI'], 'up': [u'600'], 'day': '04/11/2009'}
           , {'down': [u'342'], 'up': [u'800'], 'day': '04/16/2009'}
           , {'down': [u'450'], 'up': [u'1070'], 'day': '04/21/2009'}]}
        self.assertEqual(expected, jdiff)

    def test_extract_schedule1(self):
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

    def test_extract_schedule2(self):
        """
        Making sure we starting counting duration from the startdate
        rather than some previous receiver change date.
        """

        startdate = datetime(2009, 4, 7, 12)
        duration = 14
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
        self.assertEqual(None,
                         Receiver_Schedule.previousDate(
                             datetime(2009, 4, 1, 0)))

    def test_receivers_schedule(self):
        startdate = datetime(2009, 4, 6, 12)
        response = self.client.get('/receivers/schedule',
                                   {"startdate" : startdate,
                                    "duration" : 7})
        self.failUnlessEqual(response.status_code, 200)
        #expected = '{"diff": [{"down": [], "up": ["RRI", "342", "450"], "day": "04/06/2009"}, {"down": ["RRI"], "up": ["600"], "day": "04/11/2009"}], "receivers": ["RRI", "342", "450", "600", "800", "1070", "L", "S", "C", "X", "Ku", "K", "Ka", "Q", "MBA", "Z", "Hol", "KFPA"], "maintenance": [{"wdefault": null, "wstart": null, "handle": "Maintenance (GBT-M09A) 0", "wend": null, "state": "", "moc_ack": false, "windowed": false, "sscore": null, "cscore": 0.0, "duration": 6.0, "lst": "09:10:57", "session": {"grade": 4.0, "nighttime": false, "transit": false, "sem_time": 100.5, "lst_ex": "", "id": 1, "pcode": "GBT-M09A", "authorized": false, "type": "open", "remaining": 100.5, "total_time": 100.5, "complete": false, "project_complete": "No", "PSC_time": 100.5, "name": "Maintenance", "science": "radar", "orig_ID": 0, "enabled": false, "xi_factor": 1.0, "receiver": "", "backup": false}, "time": "00:00", "date": "2009-04-30", "receivers": "", "forecast": null, "backup": false, "id": 1, "stype": "O"}], "schedule": {"04/11/2009": ["342", "450", "600"], "04/06/2009": ["RRI", "342", "450"]}}'
        expected = '{"diff": [{"down": [], "up": ["RRI", "342", "450"], "day": "04/06/2009"}, {"down": ["RRI"], "up": ["600"], "day": "04/11/2009"}], "receivers": ["RRI", "342", "450", "600", "800", "1070", "L", "S", "C", "X", "Ku", "K", "Ka", "Q", "MBA", "Z", "Hol", "KFPA"], "maintenance": [], "schedule": {"04/11/2009": ["342", "450", "600"], "04/06/2009": ["RRI", "342", "450"]}}'

        self.assertEqual(expected, response.content)

    def test_change_schedule(self):
        "The simplest change: new change date at the end"

        # get the current schedule
        startdate = datetime(2009, 4, 6, 12)
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        dates = sorted(schedule.keys())

        # now add a rcvr change latter in time 
        last_date = dates[-1]
        new_date = last_date + timedelta(days = 5)
        available = schedule[last_date]
        S = available[0]
        L = Receiver.get_rcvr("L")
        # take down S and put up L
        Receiver_Schedule.change_schedule(new_date, [L], [S])

        # make sure it changed appropriately
        new_schd = Receiver_Schedule.extract_schedule(startdate = startdate)
        new_dates = sorted(new_schd.keys())
        self.assertEquals(len(dates) + 1, len(new_dates))
        # nothing before the change changed?
        for i, dt in enumerate(dates):
            self.assertEquals(dt, new_dates[i])
            self.assertEquals(schedule[dt], new_schd[new_dates[i]])

        # now make sure the new change makes sense
        X = Receiver.get_rcvr("X")
        C = Receiver.get_rcvr("C")
        rcvrs = [C, X, L]
        self.assertEquals(rcvrs, new_schd[new_date])

    def test_change_schedule_2(self):
        "A more complicated change"

        # get the current schedule
        startdate = datetime(2009, 4, 6, 12)
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        dates = sorted(schedule.keys())
        #for dt in dates:
        #    print dt, [r.abbreviation for r in schedule[dt]]

        # now add a rcvr change on one of these given days
        change_date = dates[-3]
        #new_date = last_date + timedelta(days = 5)
        available = schedule[change_date]

        L = available[1]
        r342 = Receiver.get_rcvr("342")
        # take down L and put up 342
        Receiver_Schedule.change_schedule(change_date, [r342], [L])

        # make sure it changed appropriately
        new_schd = Receiver_Schedule.extract_schedule(startdate = startdate)
        new_dates = sorted(new_schd.keys())
        self.assertEquals(len(dates), len(new_dates))
        #print "new: "
        #for dt in new_dates:
        #    print [r.abbreviation for r in new_schd[dt]]

        # nothing before the change changed?
        for i, dt in enumerate(dates):
            if dt < change_date:
                self.assertEquals(dt, new_dates[i])
                self.assertEquals(schedule[dt], new_schd[new_dates[i]])

        # now make sure the new change makes sense
        # get last 3 dates
        changed_dates = dates[len(dates)-3:]
        X = Receiver.get_rcvr("X")
        C = Receiver.get_rcvr("C")
        S = Receiver.get_rcvr("S")
        r1070 = Receiver.get_rcvr("1070")
        r800 = Receiver.get_rcvr("800")
        changed_schd = {changed_dates[0] : [r1070, r342, r800]
                      , changed_dates[1] : [C, r342, r800]
                      , changed_dates[2] : [C, X, r342, r800]}
        for dt in changed_dates:
            self.assertEquals(changed_schd[dt], new_schd[dt])

    def test_change_schedule_3(self):
        "More then one change on a given date. "

        # get the current schedule
        startdate = datetime(2009, 4, 6, 12)
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        dates = sorted(schedule.keys())
        #for dt in dates:
        #    print dt, [r.abbreviation for r in schedule[dt]]

        # now add a rcvr change latter in time 
        last_date = dates[-1]
        new_date = last_date + timedelta(days = 5)
        available = schedule[last_date]
        S = available[0]
        C = available[1]
        L = Receiver.get_rcvr("L")
        Q = Receiver.get_rcvr("Q")
        X = Receiver.get_rcvr("X")
        # I. take down S & C and put up L & Q
        Receiver_Schedule.change_schedule(new_date, [L, Q], [S, C])

        # make sure it changed appropriately
        new_schd = Receiver_Schedule.extract_schedule(startdate = startdate)
        new_dates = sorted(new_schd.keys())
        self.assertEquals(len(dates) + 1, len(new_dates))
        # nothing before the change changed?
        for i, dt in enumerate(dates):
            self.assertEquals(dt, new_dates[i])
            self.assertEquals(schedule[dt], new_schd[new_dates[i]])

        # now make sure the new change makes sense
        rcvrs = sorted([L, Q, X])
        rcvrs = sorted([r.abbreviation for r in [L, Q, X]])
        new_rs = sorted([r.abbreviation for r in new_schd[new_date]])
        self.assertEquals(rcvrs, new_rs)
 
        # now specify this same change to this date - nothing should happen
        s, msg = Receiver_Schedule.change_schedule(new_date, [L, Q], [S, C])
        self.assertEquals(True, s)
        self.assertEquals(None, msg)
        new_schd_2 = Receiver_Schedule.extract_schedule(startdate = startdate)
        self.assertEquals(new_schd, new_schd_2)
        new_dates_2 = sorted(new_schd_2.keys())
        #for dt in new_dates_2:
        #    print dt, [r.abbreviation for r in new_schd_2[dt]]

        # II. make a slight modification - don't put up Q and don't put down C
        s, msg = Receiver_Schedule.change_schedule(new_date, [L], [S])
        self.assertEquals(True, s)
        self.assertEquals(None, msg)
        new_schd_3 = Receiver_Schedule.extract_schedule(startdate = startdate)
        new_dates_3 = sorted(new_schd_3.keys())
        #for dt in new_dates_3:
        #    print dt, [r.abbreviation for r in new_schd_3[dt]]
        self.assertEquals(len(new_dates), len(new_dates_3))

        # now make sure the new change makes sense
        rcvrs = sorted([r.abbreviation for r in [L, C, X]])
        new_rs = sorted([r.abbreviation for r in new_schd_3[new_date]])
        self.assertEquals(rcvrs, new_rs)

        
    def test_change_receiver_schedule(self):
        # last rcvr change:
        # 2009-05-11 00:00:00 [u'S', u'C', u'X']

        # successful change
        startdate = datetime(2009, 5, 16)
        response = self.client.post('/receivers/change_schedule',
                                   {"startdate" : startdate
                                  , "up" : "L"
                                  , "down" : "S"
                                   })
        self.failUnlessEqual(response.status_code, 200)

        # do something stupid
        response = self.client.post('/receivers/change_schedule',
                                   {"startdate" : startdate
                                  , "up" : "Bob"
                                  , "down" : "K"
                                   })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("Unrecognized receiver: Bob" in response.content)
        return

        # TBF: are these going to cause errors?
        response = self.client.post('/receivers/change_schedule',
                                   {"startdate" : startdate
                                  , "up" : "Q"
                                  , "down" : "K"
                                   })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("Receiver Rcvr18_26 cannot come down" \
                              in response.content)

        # get the current schedule
        startdate = datetime(2009, 4, 6, 12)
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        dates = sorted(schedule.keys())
        #for dt in dates:
        #    print dt, [r.abbreviation for r in schedule[dt]]
                              
        # specifying something as going that is already up does not cause
        # an error
        response = self.client.post('/receivers/change_schedule',
                                   {"startdate" : startdate
                                  , "up" : "S"
                                  , "down" : "C"
                                   })
        self.failUnlessEqual(response.status_code, 200)

    def test_delete_date(self):
        # get the current schedule
        startdate = datetime(2009, 4, 6, 12)
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        dates = sorted(schedule.keys())
        #for dt in dates:
        #    print dt, [r.abbreviation for r in schedule[dt]]

        # delete a date
        Receiver_Schedule.delete_date(dates[-3])    

        # get the new schedule
        new_schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        new_dates = sorted(new_schedule.keys())

        # should be missing this deleted date
        self.assertEquals(len(new_dates) + 1, len(dates))
        # but schedule should'nt have changed up to this date
        for dt in dates[:4]:
            self.assertEquals(new_schedule[dt], schedule[dt])   
        # does the change make sense?    
        new_rs = []    
        for dt in new_dates[len(new_dates)-3:]:
            new_rs.append(sorted([r.abbreviation for r in new_schedule[dt]]))
        exp_rs = [['1070', '800', 'L']
                , ['800',  'C',   'L']
                , ['800',  'C',   'X']]
        self.assertEquals(exp_rs, new_rs)        
            
    def test_shift_date(self):
        startdate = datetime(2009, 4, 6, 12)
        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        dates = sorted(schedule.keys())

        from_date = dates[-3]
        to_date   = from_date + timedelta(days = 1)
        success, msg = Receiver_Schedule.shift_date(from_date, to_date)
        self.assertEquals(True, success)

        schedule = Receiver_Schedule.extract_schedule(startdate = startdate)
        new_dates = sorted(schedule.keys())
        for i in range(len(dates)-3):
            self.assertEquals(dates[i], new_dates[i])

        self.assertEquals(to_date, new_dates[-3])
        self.assertEquals(dates[-2], new_dates[-2])
        self.assertEquals(dates[-1], new_dates[-1])

        # now test error checking
        from_date = new_dates[-3]
        to_date = from_date + timedelta(days = 12)
        success, msg = Receiver_Schedule.shift_date(from_date, to_date)
        self.assertEquals(False, success)
        self.assertEquals("Cannot shift date to or past other dates", msg)

class TestProject(NellTestCase):
    def setUp(self):
        super(TestProject, self).setUp()

        self.project = Project()
        self.project_adapter = ProjectHttpAdapter(self.project)
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "4.0"
               , "notes"      : "notes"
               , "schd_notes" : "scheduler's notes"
        }
        self.project_adapter.update_from_post(pdata)

        # Create Investigator1 and his 3 blackouts.
        self.user1 = User(sanctioned = True
                        , role = first(Role.objects.filter(role = "Observer"))
                     )
        self.user1.save()

        self.investigator1 =  Investigator(project  = self.project
                                         , user     = self.user1
                                         , observer = True)
        self.investigator1.save()

        self.user2 = User(sanctioned = True
                        , role = first(Role.objects.filter(role = "Observer"))
                     )
        self.user2.save()

        self.investigator2 =  Investigator(project  = self.project
                                         , user     = self.user2
                                         , observer = True)
        self.investigator2.save()

        self.sesshun = create_sesshun()
        self.sesshun.project = self.project
        self.sesshun.save()

        fdata = {'session'  : self.sesshun.id
               , 'date'     : '2009-06-01'
               , 'time'     : '10:00'
               , 'duration' : 1.0
               , 'backup'   : False}
        self.period = Period()
        self.period_adapter = PeriodHttpAdapter(self.period)
        self.period_adapter.init_from_post(fdata, 'UTC')

    def tearDown(self):
        self.investigator2.delete()
        self.user2.delete()
        self.investigator1.delete()
        self.user1.delete()
        self.period.delete()
        self.sesshun.delete()
        self.project.delete()

    def test_get_blackout_times1(self):
        # Create Investigator1's 3 blackouts.
        blackout11 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 18)
                            , end_date   = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 2, 12)
                            , end_date   = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2's 2 blackouts.
        blackout21 = Blackout(user       = self.user2
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        blackout21.save()

        blackout22 = Blackout(user       = self.user2
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 18)
                            , end_date   = datetime(2009, 1, 4, 13))
        blackout22.save()

        # Now we can finally do our test.
        expected = [
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 4, 13))
        ]

        today = datetime(2009, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals(expected, r)

        # Clean up
        blackout22.delete()
        blackout21.delete()
        blackout13.delete()
        blackout12.delete()
        blackout11.delete()

    def test_get_blackout_times2(self):
        # Create Investigator1's 3 blackouts.
        self.investigator1.observer = False
        self.investigator1.save()

        blackout11 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 18)
                            , end_date   = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 2, 12)
                            , end_date   = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2's 2 blackouts.
        self.investigator2.observer = False
        self.investigator2.save()

        blackout21 = Blackout(user       = self.user2
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        blackout21.save()

        blackout22 = Blackout(user       = self.user2
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 18)
                            , end_date   = datetime(2009, 1, 4, 13))
        blackout22.save()

        today = datetime(2009, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals([], r)

        # Clean up
        blackout22.delete()
        blackout21.delete()
        blackout13.delete()
        blackout12.delete()
        blackout11.delete()

        self.investigator2.observer = True
        self.investigator2.save()
        self.investigator1.observer = True
        self.investigator1.save()

    def test_get_blackout_times3(self):
        # Create Investigator1's 3 blackouts.
        blackout11 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 18)
                            , end_date   = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 2, 12)
                            , end_date   = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Investigator 2 has no blackouts - She's available all the time.

        today = datetime(2009, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals([], r)

        # Clean up
        blackout13.delete()
        blackout12.delete()
        blackout11.delete()

    def test_get_blackout_times4(self):
        # Create Investigator1's 3 blackouts.
        blackout11 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        blackout11.save()

        blackout12 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 1, 18)
                            , end_date   = datetime(2009, 1, 4, 18))
        blackout12.save()

        blackout13 = Blackout(user       = self.user1
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 1, 2, 12)
                            , end_date   = datetime(2009, 1, 4, 20))
        blackout13.save()

        # Create Investigator2's 2 blackouts.
        blackout21 = Blackout(user       = self.user2
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 2, 1, 11)
                            , end_date   = datetime(2009, 2, 3, 11))
        blackout21.save()

        blackout22 = Blackout(user       = self.user2
                            , repeat     = first(Repeat.objects.all())
                            , start_date = datetime(2009, 3, 1, 18)
                            , end_date   = datetime(2009, 3, 4, 13))
        blackout22.save()

        today = datetime(2009, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals([], r) # Coordinated blackouts.

        # Clean up
        blackout22.delete()
        blackout21.delete()
        blackout13.delete()
        blackout12.delete()
        blackout11.delete()

    def test_get_receiver_blackout_ranges(self):
        # Schedule = 4/01/2009:   450,   600,  800
        #            4/06/2009:   600,   800, 1070
        #            4/11/2009:   800,  1070,  1_2
        #            4/16/2009:  1070,   1_2,  2_3
        #            4/21/2009:   1_2,   2_3,  4_6
        #            4/26/2009:   2_3,   4_6, 8_10
        #            5/01/2009:   4_6,  8_10, 12_18
        #            5/06/2009:  8_10, 12_18, 18_26
        #            5/11/2009: 12_18, 18_26, 26_40
        start   = datetime(2009, 4, 1, 0)
        end     = datetime(2009, 6, 1, 0)
        rcvr_id = 3
        for i in range(9):
            start_date = start + timedelta(5*i)
            for j in range(1, 4):
                rcvr_id = rcvr_id + 1
                rs = Receiver_Schedule()
                rs.start_date = start_date
                rs.receiver = Receiver.objects.get(id = rcvr_id)
                rs.save()
            rcvr_id = rcvr_id - 2

        # No sessions, no receivers
        blackouts = self.project.get_receiver_blackout_ranges(start, end)
        self.assertEquals([], blackouts)

        # No available receivers at these times: 
        expected = [(datetime(2009, 4, 1), datetime(2009, 4, 11))
                  , (datetime(2009, 5, 1), None)]
        SessionHttpAdapter(self.sesshun).save_receivers('L | (X & S)')

        blackouts = self.project.get_receiver_blackout_ranges(start, end)
        self.assertEquals(expected, blackouts)
        self.sesshun.receiver_group_set.all().delete()

        # No available receivers at these times: 
        expected = [(datetime(2009, 4, 1), datetime(2009, 4, 26))
                  , (datetime(2009, 5, 1), datetime(2009, 5, 6))]
        SessionHttpAdapter(self.sesshun).save_receivers('K | (X & S)')

        blackouts = self.project.get_receiver_blackout_ranges(start, end)
        self.assertEquals(expected, blackouts)
        self.sesshun.receiver_group_set.all().delete()

        # No available receivers at these times: 
        expected = [(datetime(2009, 4, 11), None)]
        SessionHttpAdapter(self.sesshun).save_receivers('600')

        blackouts = self.project.get_receiver_blackout_ranges(start, end)
        self.assertEquals(expected, blackouts)
        self.sesshun.receiver_group_set.all().delete()

        # Always an available receiver.
        SessionHttpAdapter(self.sesshun).save_receivers('(800 | S) | Ku')

        blackouts = self.project.get_receiver_blackout_ranges(start, end)
        self.assertEquals([], blackouts)
        self.sesshun.receiver_group_set.all().delete()

        # Clean up.
        Receiver_Schedule.objects.all().delete()

    def test_get_prescheduled_times(self):
        start = datetime(2009, 6, 1)
        end   = datetime(2009, 6, 2)

        # No periods.
        times = self.project.get_prescheduled_times(start, end)
        self.assertEquals(0, len(times))

        # Now add a project w/ prescheduled times.
        otherproject = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "4.0"
               , "notes"      : "notes"
               , "schd_notes" : "scheduler's notes"
        }
        adapter = ProjectHttpAdapter(otherproject)
        adapter.update_from_post(pdata)

        othersesshun = create_sesshun()
        othersesshun.project = otherproject
        othersesshun.save()

        fdata = {'session'  : othersesshun.id
               , 'date'     : '2009-06-01'
               , 'time'     : '13:00'
               , 'duration' : 1.0
               , 'backup'   : False}
        otherperiod = Period()
        adapter = PeriodHttpAdapter(otherperiod)
        adapter.init_from_post(fdata, 'UTC')
        otherperiod.state = Period_State.objects.filter(abbreviation = 'S')[0]
        otherperiod.save()

        # Test again
        times = self.project.get_prescheduled_times(start, end)
        self.assertEquals(1, len(times))
        self.assertEquals(times[0][0], datetime(2009, 6, 1, 13))
        self.assertEquals(times[0][1], datetime(2009, 6, 1, 14))

        # Clean up
        otherperiod.delete()
        othersesshun.delete()
        otherproject.delete()

    def test_get_prescheduled_days(self):
        start = datetime(2009, 6, 1)
        end   = datetime(2009, 6, 3)

        # No periods.
        days = self.project.get_prescheduled_days(start, end)
        self.assertEquals(0, len(days))

        # Now add a project w/ prescheduled times but not for whole day.
        otherproject = Project()
        pdata = {"semester"   : "09A"
               , "type"       : "science"
               , "total_time" : "10.0"
               , "PSC_time"   : "10.0"
               , "sem_time"   : "10.0"
               , "grade"      : "4.0"
               , "notes"      : "notes"
               , "schd_notes" : "scheduler's notes"
        }
        project_adapter = ProjectHttpAdapter(otherproject)
        project_adapter.update_from_post(pdata)
        otherproject.save()

        othersesshun = create_sesshun()
        othersesshun.project = otherproject
        othersesshun.save()

        fdata = {'session'  : othersesshun.id
               , 'date'     : '2009-06-01'
               , 'time'     : '13:00'
               , 'duration' : 1.0
               , 'backup'   : False}
        otherperiod = Period()
        period_adapter = PeriodHttpAdapter(otherperiod)
        period_adapter.init_from_post(fdata, 'UTC')
        otherperiod.state = Period_State.objects.filter(abbreviation = 'S')[0]
        otherperiod.save()

        # Test again
        days = self.project.get_prescheduled_days(start, end)
        self.assertEquals(0, len(days))

        # Now add a period w/ prescheduled times for whole day.
        fdata = {'session'  : othersesshun.id
               , 'date'     : '2009-05-31'
               , 'time'     : '23:00'
               , 'duration' : 30.0
               , 'backup'   : False}
        anotherperiod = Period()
        period_adapter.load(anotherperiod)
        period_adapter.init_from_post(fdata, 'UTC')
        anotherperiod.state = Period_State.objects.filter(abbreviation = 'S')[0]
        anotherperiod.save()

        # Test again
        days = self.project.get_prescheduled_days(start, end)
        self.assertEquals(1, len(days))
        self.assertEquals(days[0], datetime(2009, 6, 1))

        # Now make that whole day prescheduled period part of the project.
        anotherperiod.session = self.sesshun
        anotherperiod.save()

        # Test again
        days = self.project.get_prescheduled_days(start, end)
        self.assertEquals(0, len(days))

        # Clean up
        anotherperiod.delete()
        otherperiod.delete()
        othersesshun.delete()
        otherproject.delete()

    def test_init_from_post(self):
        p1 = Project()
        p2 = Project()
        self.gitrdone(p1, ProjectHttpAdapter(p1).init_from_post
                    , p2, ProjectHttpAdapter(p2).init_from_post)

        p3 = Project()
        adapter = ProjectHttpAdapter(p3)
        adapter.init_from_post({})

    def test_update_from_post(self):
        p1 = Project()
        p2 = Project()
        self.gitrdone(p1, ProjectHttpAdapter(p1).update_from_post, p2, ProjectHttpAdapter(p2).update_from_post)

    def gitrdone(self, p1, f1, p2, f2):
        "Mike was here."

        p_fdata = {"semester" : "09A"
                 , "type"     : "science"
                 , "total_time" : "10.0"
                 , "PSC_time"   : "10.0"
                 , "sem_time"   : "10.0"
                 , "grade"      : "4.0"
                   }
        f1(p_fdata)
        self.defaultAssertion(p_fdata, p1)
        
        p_fdata1 = {"semester" : "09A"
                 , "type"     : "science"
                 , "total_time" : "10.0, 5.0"
                 , "PSC_time"   : "10.0, 5.0"
                 , "sem_time"   : "10.0, 5.0"
                 , "grade"      : "4.0, 3.0"
                   }
        f2(p_fdata1)
        self.defaultAssertion(p_fdata1, p2)

        p_fdata = {"semester" : "09A"
                 , "type"     : "science"
                 , "total_time" : "10.0, 5.0, 1.0"
                 , "PSC_time"   : "10.0, 5.0, 1.0"
                 , "sem_time"   : "10.0, 5.0, 1.0"
                 , "grade"      : "4.0, 3.0, 2.0"
                   }
        f2(p_fdata)
        self.defaultAssertion(p_fdata, p2)

        f2(p_fdata1)
        self.defaultAssertion(p_fdata1, p2)

    def defaultAssertion(self, p_fdata, p):
        totals = map(float, p_fdata.get("total_time").split(', '))
        pscs     = map(float, p_fdata.get("PSC_time", "").split(', '))
        max_sems = map(float, p_fdata.get("sem_time", "").split(', '))
        grades   = map(float, p_fdata.get("grade", "").split(', '))
        for a in p.allotments.all():
            self.assertTrue(a.total_time in totals)
            self.assertTrue(a.psc_time in pscs)
            self.assertTrue(a.max_semester_time in max_sems)
            self.assertTrue(a.grade in grades)
        
class TestSesshun(NellTestCase):

    def setUp(self):
        super(TestSesshun, self).setUp()
        self.sesshun = create_sesshun()

    def test_get_ha_limit_blackouts(self):
        # With default target.
        startdate = datetime.utcnow()
        days      = 5
        r = self.sesshun.get_ha_limit_blackouts(startdate, days)

        t = Target(session    = self.sesshun
                 , system     = first(System.objects.filter(name = "J2000"))
                 , source     = "test source"
                 , vertical   = 2.3
                 , horizontal = 1.0)
        t.save()

        # TBF: Need to write test.

        t.delete()

    def test_create(self):
        expected = first(Sesshun.objects.filter(id = self.sesshun.id))
        self.assertEqual(expected.allotment.total_time, float(fdata["total_time"]))
        self.assertEqual(expected.name, fdata["name"])

    def test_init_from_post(self):
        s = Sesshun()
        fdata["receiver"] = "((K & Ku) & L)"
        SessionHttpAdapter(s).init_from_post(fdata)
        
        self.assertEqual(s.allotment.total_time, fdata["total_time"])
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])
        self.assertEqual(s.get_LST_exclusion_string(),fdata["lst_ex"]) 

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
        adapter = SessionHttpAdapter(s)
        adapter.init_from_post(fdata)
        
        self.assertEqual(s.frequency, fdata["freq"])
        self.assertEqual(s.allotment.total_time, fdata["total_time"])
        self.assertEqual(s.target_set.get().source, fdata["source"])
        self.assertEqual(s.status.enabled, fdata["enabled"])
        self.assertEqual(s.get_LST_exclusion_string(), fdata["lst_ex"])

        # change a number of things and see if it catches it
        ldata = dict(fdata)
        ldata["freq"] = "10"
        ldata["source"] = "new source"
        ldata["total_time"] = "99"
        ldata["enabled"] = "true"
        ldata["transit"] = "true"
        ldata["nighttime"] = "false"
        ldata["lst_ex"] = "2.00-4.00"
        ldata["receiver"] = "(K & (X | (L | C)))"
        ldata["xi_factor"] = 1.76
        adapter.update_from_post(ldata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(ldata["freq"]))
        self.assertEqual(s.allotment.total_time, float(ldata["total_time"]))
        self.assertEqual(s.target_set.get().source, ldata["source"])
        self.assertEqual(s.status.enabled, ldata["enabled"] == "true")
        self.assertEqual(s.transit(), ldata["transit"] == "true")
        self.assertEqual(s.nighttime(), None)
        self.assertEqual(s.get_LST_exclusion_string(), ldata["lst_ex"])
        self.assertEqual(s.get_min_eff_tsys_factor(), ldata["xi_factor"])
        self.assertEqual(s.get_elevation_limit(),fdata["el_limit"]) 
        rgs = s.receiver_group_set.all()
        self.assertEqual(2, len(rgs))
        self.assertEqual(['K']
                       , [r.abbreviation for r in rgs[0].receivers.all()])
        self.assertEqual(['L', 'C', 'X']
                       , [r.abbreviation for r in rgs[1].receivers.all()])

    def test_update_from_post2(self):
        ss = Sesshun.objects.all()
        s = Sesshun()
        adapter = SessionHttpAdapter(s)
        adapter.init_from_post(fdata)
        
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
        adapter.update_from_post(ldata)
        
        # now get this session from the DB
        ss = Sesshun.objects.all()
        s = ss[1]
        self.assertEqual(s.frequency, float(ldata["freq"]))
        self.assertEqual(s.allotment.total_time, float(ldata["total_time"]))
        self.assertEqual(s.target_set.get().source, ldata["source"])
        self.assertEqual(s.status.enabled, True) # "True" -> True
        self.assertEqual(s.original_id, 0) #ldata["orig_ID"]) -- "0.0" -> Int

class TestBlackout(NellTestCase):

    def setUp(self):
        super(TestBlackout, self).setUp()

        # create some user blackouts    
        self.u = User(first_name = "Test"
                    , last_name  = "User"
                    , role       = first(Role.objects.all())
                      )
        self.u.save()

        once = first(Repeat.objects.filter(repeat = 'Once'))
        self.blackout1 = Blackout(user       = self.u
                            , repeat     = once 
                            , start_date = datetime(2009, 1, 1, 11)
                            , end_date   = datetime(2009, 1, 3, 11))
        self.blackout1.save()

        weekly = first(Repeat.objects.filter(repeat = 'Weekly'))
        self.blackout2 = Blackout(user       = self.u
                            , repeat     = weekly
                            , start_date = datetime(2009, 1, 4, 11)
                            , end_date   = datetime(2009, 1, 4, 13)
                            , until      = datetime(2009, 5, 4, 11))
        self.blackout2.save()

        # create some project blackouts
        semester = first(Semester.objects.filter(semester = "08C"))
        ptype    = first(Project_Type.objects.filter(type = "science"))

        self.pcode = "GBT08C-01"
        self.project = Project(semester = semester
                             , project_type = ptype
                             , pcode = self.pcode
                               )
        self.project.save()                       

        #once = first(Repeat.objects.filter(repeat = 'Once'))
        self.blackout3 = Blackout(project    = self.project
                                , repeat     = once 
                                , start_date = datetime(2008, 10, 1, 11)
                                , end_date   = datetime(2008, 10, 3, 11))
        self.blackout3.save()
        
    def test_eventjson(self):

        # user blackout
        calstart = datetime(2009, 1, 1)
        calend   = datetime(2009, 1, 30)
        json = self.blackout1.eventjson(mktime(calstart.timetuple())
                                      , mktime(calend.timetuple()))
        event = {'className': 'blackout'
               , 'start': '2009-01-01T11:00:00'
               , 'end': '2009-01-03T11:00:00'
               , 'id': 1L
               , 'title': 'Test User: blackout'
               }
        self.assertEqual(event, json[0])       

        # project blackout
        calstart = datetime(2008, 10, 1)
        calend   = datetime(2008, 10, 30)
        json = self.blackout3.eventjson(mktime(calstart.timetuple())
                                      , mktime(calend.timetuple()))
        event = {'className': 'blackout'
               , 'start': '2008-10-01T11:00:00'
               , 'end': '2008-10-03T11:00:00'
               , 'id': 3L
               , 'title': '%s: blackout' % self.pcode
               }
        self.assertEqual(event, json[0]) 

    # TBF
    # test_isActive

    def test_generateDates(self):

        # no repeats are easy ...
        dts = [(self.blackout1.start_date, self.blackout1.end_date)]
        calstart = datetime(2009, 1, 1)
        calend   = datetime(2009, 1, 30)
        gdts = self.blackout1.generateDates(calstart, calend)
        self.assertEquals(dts, gdts)

        # repeats are more complicated
        # how does January look?
        start = self.blackout2.start_date
        end = self.blackout2.end_date
        dts = [(start, end)]
        for i in [1,2,3]:
            dts.append((start + timedelta(days = 7 * i)
                      , end   + timedelta(days = 7 * i)))
        gdts = self.blackout2.generateDates(calstart, calend)
        self.assertEquals(dts, gdts)

        # outside of calendar start/end, but weekly until May
        calstart = datetime(2009, 2, 1)
        calend   = datetime(2009, 2, 28)
        gdts = self.blackout2.generateDates(calstart, calend)
        self.assertEquals(4, len(gdts))

        # should be none in June.
        calstart = datetime(2009, 6, 1)
        calend   = datetime(2009, 6, 30)
        gdts = self.blackout2.generateDates(calstart, calend)
        self.assertEquals(0, len(gdts))

        # should be none in previous June.
        calstart = datetime(2008, 6, 1)
        calend   = datetime(2008, 6, 30)
        gdts = self.blackout2.generateDates(calstart, calend)
        self.assertEquals(0, len(gdts))

        # no repeats are easy ... even for project blackouts
        dts = [(self.blackout3.start_date, self.blackout3.end_date)]
        calstart = datetime(2008, 10, 1)
        calend   = datetime(2008, 10, 30)
        gdts = self.blackout3.generateDates(calstart, calend)
        self.assertEquals(dts, gdts)

    def test_projectBlackout(self):
        "Repeat some of the other tests, but for project blackouts"

        self.assertEquals(self.blackout3.forName(), self.project.pcode)
        self.assertEquals(self.blackout3.forUrlId(), self.project.pcode)

# Testing Views

class TestViews(NellTestCase):

    def test_column_configurations_explorer_post(self):
        data = {'Thesis?': ['false']               , 'Grade(s)': ['false']
              , 'Name': ['false']                  , 'PSC Time(s)': ['false']
              , 'Remaining Time': ['false']        , 'name': ['foo']
              , 'Co-I': ['false']                  , 'Complete?': ['false']
              , 'PCode': ['false']                 , 'Friend': ['false']
              , 'Max. Trimester Time(s)': ['false'], 'Trimester': ['false']
              , 'PI': ['false']                    , 'Type': ['false']
              , 'Total Time(s)': ['false']         , 'explorer': ['/projects']
              }
        c = Client()
        response = c.post('/configurations/explorer/columnConfigs', data)
        self.failUnlessEqual(response.status_code, 200)

    def test_column_configurations_explorer_get(self):
        c = Client()
        response = c.get('/configurations/explorer/columnConfigs', {'explorer': '/project'})
        self.failUnlessEqual(response.status_code, 200)

    def test_filter_combinations_explorer_post(self):
        data = {'Trimester': '08C'
              , 'Project Type': 'science'
              , 'Complete': 'True'
              , 'explorer': '/projects'
              , 'name': 'test'
              }
        c = Client()
        response = c.post('/configurations/explorer/filterCombos', data)
        self.failUnlessEqual(response.status_code, 200)
        r = eval(response.content)
        ec = first(ExplorerConfiguration.objects.filter(id = r['id']))
        self.assertTrue(ec is not None)

    def test_reservations(self):
        c = Client()
        data = {'start' : '6/1/2010'
              , 'days'  : '61'
               }
        response = c.get('/reservations', data)
        self.failUnlessEqual(response.status_code, 200)
        r = eval(response.content)
        self.assertTrue(len(r.get('reservations')) == 0)

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
        adapter = PeriodHttpAdapter(self.p)
        adapter.init_from_post(self.fdata, 'UTC')
        self.p.save()

    # Requires antioch server
    def test_create(self):
        response = self.client.post(self.rootURL + '/UTC', self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    # Requires antioch server
    def test_create_empty(self):
        response = self.client.post(self.rootURL + '/ET')
        self.failUnlessEqual(response.status_code, 200)

    # Requires antioch server
    def test_read(self):
        url = "%s/%s?startPeriods=%s&daysPeriods=%d" % \
                            (self.rootURL 
                           , 'UTC'
                           , self.fdata['date'] + '%20' + self.fdata['time'] + ':00'
                           , 2)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.content[:11], '{"total": 1')

    # Requires antioch server
    def test_read_keywords(self):
        # use a date range that picks up our one period
        url = "%s/%s?startPeriods=%s&daysPeriods=%d" % \
                            (self.rootURL 
                           , 'UTC'
                           , self.fdata['date'] + '%20' + self.fdata['time'] + ':00'
                           , 3)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.content[:11], '{"total": 1')
        # now use a date range that doesn't
        url = "%s/%s?startPeriods=%s&daysPeriods=%d" % (
                                                     self.rootURL 
                                                   , 'UTC'
                                                   , '2009-06-02 00:00:00' 
                                                   , 3)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.content[:11], '{"total": 0')


    # If antioch server running requires it contain the appropriate periods
    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"})
        response = self.client.post('%s/%s/%s' % (self.rootURL
                                                 ,'ET'
                                                 , self.p.id), fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.post('%s/%s/%s' % (self.rootURL
                                                , 'ET'
                                                , self.p.id)
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
        ProjectHttpAdapter(self.p).init_from_post(self.fdata)
        self.p.save()

    def test_create(self):
        response = self.client.post('/projects', self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_create_empty(self):
        response = self.client.post('/projects')
        self.failUnlessEqual(response.status_code, 200)

    def test_create_no_allotment(self):
        # Get copy of fdata in local scope to modify for the purposes
        # of this test.
        fdata = self.fdata.copy()
        fdata.update({'total_time' : ''
                    , 'PSC_time'   : ''
                    , 'sem_time'   : ''
                    , 'grade'      : ''
                      })

        response = self.client.post('/projects', fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/projects')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 2' in response.content)

    def test_read_with_filter(self):
        response = self.client.get('/projects?filterText=09C')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 1' in response.content)
        self.assertTrue('09C' in response.content)
        self.assertTrue('09A' not in response.content)

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
        SessionHttpAdapter(s).init_from_post({})
        s.save()
        self.s = s

    def test_create(self):
        response = self.client.post('/sessions')
        self.failUnlessEqual(response.status_code, 200)

    def test_create2(self):
        fdata = {'req_max': ['6.0']
               , 'grade': ['4.0']
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
        # Next two lines are logically equivalent
        #self.assertEquals(r_json['receiver'], u'(K) & (L | S)')
        self.assertEquals(r_json['receiver'], u'(K & (L | S))')
        # etc
        response = self.client.post('/sessions',
                                    {'receiver' : 'Ka | (342 & S)'})
        self.failUnlessEqual(response.status_code, 200)
        r_json = json.loads(response.content)
        self.assertTrue(r_json.has_key('receiver'))
        # Next two lines are logically equivalent
        #self.assertEquals(r_json['receiver'], u'(342 | Ka) & (S | Ka)')
        self.assertEquals(r_json['receiver'], u'((342 | Ka) & (S | Ka))')

class TestUserResources(NellTestCase):

    def setUp(self):
        super(TestUserResources, self).setUp()
        self.client = Client()
        self.fdata = {
                      }
        self.users = []
        self.users.append(User(original_id = 0
                    , pst_id      = 0
                    , sanctioned  = False
                    , first_name  = 'Foo'
                    , last_name   = 'Bar'
                    , contact_instructions = ""
                    , role  = first(Role.objects.all())
                     ))
        self.users[-1].save()
        self.users.append(User(original_id = 0
                    , pst_id      = 0
                    , sanctioned  = True
                    , first_name  = 'Mike'
                    , last_name   = 'McCarty'
                    , contact_instructions = ""
                    , role  = first(Role.objects.all())
                     ))
        self.users[-1].save()

    def test_create(self):
        fdata = self.fdata
        fdata.update({"original_id" : "99"
                    , "sanctioned" : "True"
                    , "first_name" : "Foogle"
                    , "last_name"  : "Bar"
                    , "contact_instructions" : "Best to call my mom's house.  Ask for Pooh Bear."
                    , "role": "Observer"
                    , "username": "dss" # in tests only 
                     })
        response = self.client.post('/users', fdata)
        self.failUnlessEqual(response.status_code, 200)

        u = first(User.objects.filter(original_id = fdata['original_id']))
        self.assertTrue(u is not None)

        response = self.client.post('/users', {})
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/users')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 2' in response.content)

    def test_read_with_filter(self):
        response = self.client.get('/users?filterText=foo')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 1' in response.content)

    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"
                    , "pst_id"  : "1"
                    , "original_id"  : "12"
                    , "sanctioned" : "True"
                    , "first_name" : "Foo"
                    , "last_name"  : "Bar"
                    , "contact_instructions" : ""
                    , "role": "Observer"
                    , "username": "dss" # in tests only
                     })
        response = self.client.post('/users/%s' % self.users[0].id, fdata)
        self.failUnlessEqual(response.status_code, 200)

class TestInvestigatorResource(NellTestCase):

    def setUp(self):
        super(TestInvestigatorResource, self).setUp()
        self.client = Client()
        p_fdata = {'semester'   : '09C'
                 , 'type'       : 'science'
                 , 'pcode'      : 'mike'
                 , 'name'       : 'mikes awesome project!'
                 , 'PSC_time'   : '100.0'
                 , 'total_time' : '100.0'
                 , 'sem_time'   : '50.0'
                   }
        self.p = Project()
        p_adapter = ProjectHttpAdapter(self.p)
        p_adapter.init_from_post(p_fdata)
        self.p.save()

        self.users = []
        self.users.append(User(original_id = 0
                    , pst_id      = 0
                    , sanctioned  = False
                    , first_name  = 'Foo'
                    , last_name   = 'Bar'
                    , contact_instructions = ""
                    , role  = first(Role.objects.all())
                     ))
        self.users[-1].save()
        self.users.append(User(original_id = 0
                    , pst_id      = 0
                    , sanctioned  = True
                    , first_name  = 'Mike'
                    , last_name   = 'McCarty'
                    , contact_instructions = ""
                    , role  = first(Role.objects.all())
                     ))
        self.users[-1].save()
        self.users.append(User(original_id = 0
                    , pst_id      = 0
                    , sanctioned  = True
                    , first_name  = 'Doless'
                    , last_name   = 'NoProject'
                    , contact_instructions = ""
                    , role  = first(Role.objects.all())
                     ))
        self.users[-1].save()
        self.ins = []
        self.ins.append(Investigator(project                = self.p
                                   , user                   = self.users[0]
                                   , observer               = True
                                   , principal_contact      = False
                                   , principal_investigator = False
                                   , priority               = 2
                                   ))
        self.ins[-1].save()
        self.ins.append(Investigator(project                = self.p
                                   , user                   = self.users[1]
                                   , observer               = True
                                   , principal_contact      = True
                                   , principal_investigator = True
                                   , priority               = 1
                                   ))
        self.ins[-1].save()
        self.fdata = {'name'       : self.users[-1].last_name
                    , 'pi'         : 'False'
                    , 'contact'    : 'False'
                    , 'remote'     : 'False'
                    , 'project_id' : self.p.id
                    , 'user_id'    : self.users[-1].id
                    , 'observer'   : 'true'
                    , 'priority'   : 1
                     }

    def test_create(self):
        response = self.client.post('/investigators' 
                                  , self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_create_empty(self):
        response = self.client.post('/investigators'
                                  , {'project_id' : self.p.id
                                   , 'user_id': self.users[-1].id})
        self.failUnlessEqual(response.status_code, 200)

    def test_read(self):
        response = self.client.get('/investigators'
                                 , {'project_id' : self.p.id})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 2' in response.content)

    def test_read_with_filter(self):
        response = self.client.get(
              '/investigators'
            , {'project_id' : self.p.id
            ,  'filterText' : 'Mike'
            })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"total": 1' in response.content)
        self.assertTrue('McCarty' in response.content)

    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"
                    , "remote"  : "True"
                    })
        response = self.client.post('/investigators/%s' % self.ins[-1].id
                                  , fdata)
        self.failUnlessEqual(response.status_code, 200)

        fdata2 = {u'pi': [u'false'], u'user_id': [u'494.0']
                , u'name': [u'McCarty, Michael'], u'observer': [u'true']
                , u'priority': [u'1.0'], u'contact': [u'false']
                , u'remote': [u'true'], u'project_id': [u'5.0']
                , u'id': [u'995.0'], u'_method': [u'put']}
        response = self.client.post('/investigators/%s' % self.ins[-1].id
                                  , fdata2)
        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.post('/investigators/%s' % self.ins[-1].id
                                  , {"_method" : "delete"})
        self.failUnlessEqual(response.status_code, 200)
        
    
class TestWindowResource(NellTestCase):

    def setUp(self):
        super(TestWindowResource, self).setUp()
        self.client = Client()
        self.sesshun = create_sesshun()
        dt = datetime(2010, 1, 1, 12, 15)
        pending = first(Period_State.objects.filter(abbreviation = "P"))
        pa = Period_Accounting(scheduled = 0)
        pa.save()
        self.default_period = Period(session = self.sesshun
                                   , start = dt
                                   , duration = 5.0
                                   , state = pending
                                   , accounting = pa
                                   )
        self.default_period.save()                           
        p_adapter = PeriodHttpAdapter(self.default_period)
        pjson = p_adapter.jsondict('UTC', 1.1)
        self.fdata = {"session":  self.sesshun.id
                    , "start":    "2010-01-01"
                    , "duration": 7
                    #, "default_period" : self.default_period.id
                    , "default_date" : pjson['date'] 
                    , "default_time" : pjson['time'] 
                    , "default_duration" : pjson['duration'] 
                    , "default_state" : pjson['state'] 
                    }
        self.w = Window()
        w_adapter = WindowHttpAdapter(self.w)
        w_adapter.init_from_post(self.fdata)

    def tearDown(self):
        super(TestWindowResource, self).tearDown()

        # cleanup
        self.w.delete()
        self.default_period.delete()
        self.sesshun.delete()

    def test_create(self):
        response = self.client.post('/windows', self.fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_create_empty(self):
        response = self.client.post('/windows')
        self.failUnlessEqual(response.status_code, 200)

    def test_read_one(self):
        response = self.client.get('/windows/%d' % self.w.id)
        self.failUnlessEqual(response.status_code, 200)

        self.assertTrue('"end": "2010-01-07"' in response.content)

    def test_read_filter(self):
        response = self.client.get('/windows'
                                , {'filterSession' : self.sesshun.name})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"end": "2010-01-07"' in response.content)

        response = self.client.get('/windows'
                                , {'filterSession' : "not_there"})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('{"windows": [], "total": 0}' in response.content)

        #YYYY-MM-DD hh:mm:ss
        response = self.client.get('/windows'
                                , {'filterStartDate' : '2009-12-25' # 00:00:00' 
                                 , 'filterDuration' : 30})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"end": "2010-01-07"' in response.content)

        # make sure we catch overlaps
        response = self.client.get('/windows'
                                , {'filterStartDate' : '2010-01-07' # 00:00:00' 
                                 , 'filterDuration' : 30})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('"end": "2010-01-07"' in response.content)

        response = self.client.get('/windows'
                                , {'filterStartDate' : '2011-05-25' # 00:00:00' 
                                 , 'filterDuration' : 30})
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue('{"windows": [], "total": 0}' in response.content)

    def test_update(self):
        fdata = self.fdata
        fdata.update({"_method" : "put"})
        response = self.client.post('/windows/%s' % self.w.id, fdata)
        self.failUnlessEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.post('/windows/%s' % self.w.id, {"_method" : "delete"})
        self.failUnlessEqual(response.status_code, 200)
        
    
class TestGetOptions(NellTestCase):

    def test_get_options(self):
        create_sesshun()
        c = Client()
        response = c.get('/sessions/options', dict(mode='project_codes'))
        self.assertEquals(response.content,
                          '{"project codes": ["GBT09A-001"], "project ids": [1]}')
        response = c.get('/sessions/options', dict(mode='session_handles', notcomplete='true', enabled='true'))
        self.assertEquals(response.content,
                          '{"ids": [1], "session handles": ["Low Frequency With No RFI (GBT09A-001)"]}')

class TestChangeSchedule(NellTestCase):
    def test_change_schedule(self):
        create_sesshun()
        c = Client()
        response = c.post('/schedule/change_schedule'
                        , dict(duration = "1.0"
                             , start    = "2009-10-11 04:00:00"))

class TestShiftPeriodBoundaries(NellTestCase):
    def setUp(self):
        super(TestShiftPeriodBoundaries, self).setUp()

        # setup some periods
        self.start = datetime(2000, 1, 1, 0)
        self.end   = self.start + timedelta(hours = 12)
        times = [(datetime(2000, 1, 1, 0), 5.0, "one")
               , (datetime(2000, 1, 1, 5), 3.0, "two")
               , (datetime(2000, 1, 1, 8), 4.0, "three")
               ]
        self.ps = []
        for start, dur, name in times:
            s = create_sesshun()
            s.name = name
            s.save()
            pa = Period_Accounting(scheduled = dur)
            pa.save()
            state = first(Period_State.objects.filter(abbreviation = 'S'))
            p = Period( session    = s
                      , start      = start
                      , duration   = dur
                      , state      = state
                      , accounting = pa
                      )
            p.save()          
            self.ps.append(p)

        self.backup = create_sesshun()
        self.backup.name = "backup"
        self.backup.status.backup = True
        self.backup.save()

    def tearDown(self):
        super(TestShiftPeriodBoundaries, self).tearDown()

        for p in self.ps:
            p.session.delete()
            p.remove() #delete()

    def test_shift_period_boundaries(self):
        create_sesshun()
        c = Client()

        period_id = self.ps[1].id
        new_time = self.ps[1].start + timedelta(hours = 1)
        time = new_time.strftime("%Y-%m-%d %H:%M:%S")

        response = c.post('/schedule/shift_period_boundaries'
                        , dict(period_id = period_id
                             , start_boundary = 1
                             , description = "test"
                             , time    = time)) #"2009-10-11 04:00:00"))
        self.failUnless("ok" in response.content)                     

class PeriodsTestCase(NellTestCase):
    "Parent class for test cases that need periods to work with."

    def setUp(self):
        super(PeriodsTestCase, self).setUp()

        # setup some periods
        self.start = datetime(2000, 1, 1, 0)
        self.end   = self.start + timedelta(hours = 12)
        times = [(datetime(2000, 1, 1, 0), 5.0, "one", "S")
               , (datetime(2000, 1, 1, 5), 3.0, "two", "P")
               , (datetime(2000, 1, 1, 8), 4.0, "three", "S")
               ]
        self.ps = []
        for start, dur, name, st in times:
            s = create_sesshun()
            s.name = name
            s.save()
            scheduled = dur if st == "S" else 0.0
            pa = Period_Accounting(scheduled = scheduled)
            pa.save()
            state = first(Period_State.objects.filter(abbreviation = st))
            p = Period( session    = s
                      , start      = start
                      , duration   = dur
                      , state      = state
                      , accounting = pa
                      )
            p.save()          
            self.ps.append(p)

    def tearDown(self):
        super(PeriodsTestCase, self).tearDown()

        for p in self.ps:
            p.session.delete()
            p.remove() #delete()

class TestSchedulingNotifier(PeriodsTestCase):

    def test_examinePeriods(self):

        # TBF: make the test flag actually do something!
        sn = SchedulingNotifier.SchedulingNotifier(test = True)

        sn.examinePeriods(self.ps)
        self.assertEquals(self.ps, sn.observingPeriods)
        self.assertEquals([], sn.changedPeriods)
        self.assertEquals([], sn.deletedPeriods)

    def test_examinePeriods_2(self):

        # TBF: make the test flag actually do something!
        sn = SchedulingNotifier.SchedulingNotifier(test = True)

        # now delete one of these periods
        #p = self.ps[0]
        self.ps[0].state = Period_State.get_state("D")
        self.ps[0].accounting.lost_time_other = self.ps[0].duration
        self.ps[0].save()

        # also create a windowed session with default period that 
        # is in the deleted state
        s = create_sesshun()
        s.session_type = first(Session_Type.objects.filter(type = "windowed"))
        s.save()

        # new default period for a window that is after the original periods
        start_time = self.ps[2].start + timedelta(hours = self.ps[2].duration)
        dur = 3.0 

        pa = Period_Accounting(scheduled = 0)
        pa.save()
        state = first(Period_State.objects.filter(abbreviation = "D"))
        p = Period( session    = s
                  , start      = start_time
                  , duration   = dur
                  , state      = state
                  , accounting = pa
                  )
        p.save()          
        w1 = Window( session = s
                   , start_date = p.start.date() - timedelta(days = 7)
                   , duration = 10 # days
                   , default_period = p
                   , period = None )
        w1.save()  

        ps = [self.ps[0]
            , self.ps[1]
            , self.ps[2]
            , p
             ]
        sn.examinePeriods(ps)
        obsPeriods = self.ps[1:]
        self.assertEquals(obsPeriods, sn.observingPeriods)
        self.assertEquals([self.ps[0]], sn.changedPeriods)
        self.assertEquals([self.ps[0]], sn.deletedPeriods)

class TestSchedulingEmail(PeriodsTestCase):
    "Subclass PeriodsTestCase so that we have Periods to work with."

    def test_scheduling_email(self):

        # TBF: this is a dumb test, since email is always generated for NOW;
        # we need to create some periods for NOW to show up in the email
        url = "/schedule/email"
        response = Client().get(url, dict(duration = 2))
 
        self.failUnless(response.status_code == 200)  

class TestProjectsEmail(PeriodsTestCase):
    "Subclass PeriodsTestCase so that we have Periods to work with."

    def test_projects_email(self):
        pcodes = "GBT09A-001"

        url = "/projects/email"

        response = Client().get(url, dict(pcodes = pcodes))

        self.failUnless(response.status_code == 200)  
        self.failUnless('"PCODES": ["GBT09A-001"]' in response.content)

class TestDeletePending(PeriodsTestCase):
    "Subclass PeriodsTestCase so that we have Periods to work with."

    def test_delete_pending(self):

        # check current state
        ps = Period.objects.order_by("start")
        exp = ["S", "P", "S"]
        self.assertEquals(exp, [p.state.abbreviation for p in ps])
        exp = [5.0, 0.0, 4.0]
        self.assertEquals(exp, [p.accounting.scheduled for p in ps])

        # have to use the scheduling range
        dt = self.ps[0].start - timedelta(days = 1)
        time = dt.strftime("%Y-%m-%d %H:%M:%S")
        tz = "ET"
        duration = 2 #12
        url = "/periods/delete_pending"

        response = Client().post(url, dict(start    = time
                                         , tz       = tz
                                         , duration = duration
                                         ))
        self.failUnless("ok" in response.content)    

        ps = Period.objects.order_by("start")
        exp = ["S", "S"]
        self.assertEquals(exp, [p.state.abbreviation for p in ps])
        exp = [5.0, 4.0]
        self.assertEquals(exp, [p.accounting.scheduled for p in ps])

class TestPublishPeriods(PeriodsTestCase):
    "Subclass PeriodsTestCase so that we have Periods to work with."

    def test_publish_periods_by_id(self):
        # check current state
        ps = Period.objects.order_by("start")
        exp = ["S", "P", "S"]
        self.assertEquals(exp, [p.state.abbreviation for p in ps])
        exp = [5.0, 0.0, 4.0]
        self.assertEquals(exp, [p.accounting.scheduled for p in ps])

        time = self.ps[0].start.strftime("%Y-%m-%d %H:%M:%S")

        url = "/periods/publish/%d" % self.ps[1].id

        # Remember not to embarrass ourselves by tweeting! tweet == False
        response = Client().post(url, dict(tweet = False))
        self.failUnless("ok" in response.content)    

        ps = Period.objects.order_by("start")
        exp = ["S", "S", "S"]
        self.assertEquals(exp, [p.state.abbreviation for p in ps])

    def test_publish_periods(self):
        # check current state
        ps = Period.objects.order_by("start")
        exp = ["S", "P", "S"]
        self.assertEquals(exp, [p.state.abbreviation for p in ps])
        exp = [5.0, 0.0, 4.0]
        self.assertEquals(exp, [p.accounting.scheduled for p in ps])

        # have to use the scheduling range
        dt = self.ps[0].start - timedelta(days = 1)
        time = dt.strftime("%Y-%m-%d %H:%M:%S")
        tz = "ET"
        duration = 2 #12
        url = "/periods/publish"

        # Remember not to embarrass ourselves by tweeting! tweet == False
        response = Client().post(url, dict(start    = time
                                         , tz       = tz
                                         , duration = duration
                                         , tweet    = False)) 
        self.failUnless("ok" in response.content)    

        ps = Period.objects.order_by("start")
        exp = ["S", "S", "S"]
        self.assertEquals(exp, [p.state.abbreviation for p in ps])
        exp = [5.0, 3.0, 4.0]
        self.assertEquals(exp, [p.accounting.scheduled for p in ps])

    def test_publish_periods_with_windows(self):
        # Assign periods to our windows
        # 1 - scheduled -> window 1
        # 2 - pending -> window 2
        # 3 - scheduled -> window 2, make pending
        pending   = Period_State.get_state("P")
        scheduled = Period_State.get_state("S")
        windowed  = Session_Type.objects.filter(type = "windowed")[0]

        p1 = self.ps[0]
        p1.session.session_type = windowed
        p1.session.save()

        w1 = Window( session = p1.session
                   , start_date = p1.start.date() - timedelta(days = 7)
                   , duration = 10 # days
                   , default_period = p1
                   , period = p1 )
        w1.save()           

        p2 = self.ps[1]
        p2.session.session_type = windowed
        p2.session.save()

        p3 = self.ps[2] 
        p3.session.session_type = windowed
        p3.session.save()
        p3.state = pending
        p3.save()

        # NOTE: ovelapping windows for same session - shouldn't matter
        w2 = Window( session = p2.session # NOTE: same session for all 3 periods
                   , start_date = p1.start.date() - timedelta(days = 7)
                   , duration = 10 # days
                   , default_period = p2
                   , period = p3 )
        w2.save()

        # check the states
        self.assertEquals(scheduled, w1.state())
        self.assertEquals(pending, w2.state())

        # remeber that we publish using the scheduling range
        dt = w1.start_date - timedelta(days = 1)
        time = dt.strftime("%Y-%m-%d %H:%M:%S")
        tz = "ET"
        duration = 13 #12
        url = "/periods/publish"

        # Remember not to embarrass ourselves by tweeting! tweet == False
        response = Client().post(url, dict(start    = time
                                         , tz       = tz
                                         , duration = duration
                                         , tweet    = False)) 
        self.failUnless("ok" in response.content)    

        # make sure the states are right now
        for w in Window.objects.order_by("start_date"):
            self.assertEquals(scheduled, w.state())

        # Put things back the way we found them.
        open = Session_Type.objects.filter(type = "open")[0]
        p1.session.session_type = open
        p1.session.save()
        p2.session.session_type = open
        p2.session.save()
        p3.session.session_type = open
        p3.session.save()

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

        self.u = User(first_name = "dss" #"Test"
                    , last_name  = "account" #"User"
                    , pst_id     = 3259
                    , role       = first(Role.objects.all())
                    #, username   = self.auth_user.username
                      )
        self.u.save()
        self.client.login(username = "dss", password = "asdf5!")
        
        self.p = Project()
        adapter = ProjectHttpAdapter(self.p)
        adapter.init_from_post({'semester'   : '09C'
                             , 'type'       : 'science'
                             , 'pcode'      : 'mike' 
                             , 'name'       : 'mikes awesome project!'
                             , 'PSC_time'   : '100.0'
                             , 'total_time' : '100.0'
                             , 'sem_time'   : '50.0'
                               })

        i =  Investigator(project = self.p
                        , user    = self.u
                         )
        i.save()

        fdata2 = copy(fdata)
        fdata2.update({'source_v' : 1.0
                     , 'source_h' : 1.0
                     , 'source'   : 'testing'
                       })
        self.s = Sesshun()
        SessionHttpAdapter(self.s).init_from_post(fdata2)
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
        self.assertTrue("account" in response.content)

    def test_toggle_session(self):
        response = self.post(
            '/project/%s/session/%s/enable' % (self.p.pcode, self.s.id))
        self.failUnlessEqual(response.status_code, 302)
        s = first(Sesshun.objects.filter(id = self.s.id))
        self.assertEqual(s.status.enabled, True)

    def test_toggle_observer(self):
        i_id = first(self.p.investigator_set.all()).id
        response = self.post(
            '/project/%s/investigator/%s/observer' % (self.p.pcode, i_id))
        self.failUnlessEqual(response.status_code, 302)
        i = first(Investigator.objects.filter(id = i_id))
        self.assertEqual(i.observer, True)

    def test_dynamic_contact_form(self):
        response = self.get('/profile/%s/dynamic_contact' % self.u.id)
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
        b.repeat      = first(Repeat.objects.all())
        b.description = "This is a test blackout."
        b.save()
        return b

    def create_blackout_for_project(self):
        b             = Blackout(project = self.p)
        b.start       = datetime(2009, 1, 1)
        b.end         = datetime(2009, 12, 31)
        b.repeat      = first(Repeat.objects.all())
        b.description = "This is a test blackout for a project."
        b.save()
        return b       

    def test_blackout_form(self):

        # user blackout
        response = self.get('/profile/%s/blackout/' % self.u.id)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("Blackout for dss account" in response.content)

        b = self.create_blackout()
        response = self.get('/profile/%s/blackout/%s/' % (self.u.id, b.id))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue(b.description in response.content)

        # project blackout
        response = self.get('/project/%s/blackout/' % self.p.pcode)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("Blackout for mike" in response.content)

        b = self.create_blackout_for_project()
        response = self.get('/project/%s/blackout/%s/' % (self.p.pcode, b.id))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue(b.description in response.content)

    def test_blackout(self):
        # create a blackout
        b     = self.create_blackout()
        start = datetime(2009, 1, 1)
        end   = datetime(2009, 1, 31)
        until = datetime(2010, 1, 31)
        data = {'start'       : start.date().strftime("%m/%d/%Y")
              , 'start_time'   : start.time().strftime("%H:%M")
              , 'end'         : end.date().strftime("%m/%d/%Y")
              , 'end_time'     : end.time().strftime("%H:%M")
              , 'repeats'      : 'Once'
              , 'until'       : until.strftime("%m/%d/%Y")
              , 'until_time'   : until.strftime("%H:%M")
              , 'description' : "This is a test blackout."
              , '_method'     : "PUT"
                }

        # edit it
        response = self.post(
            '/profile/%s/blackout/%s/' % (self.u.id, b.id), data)
        b = first(Blackout.objects.filter(id = b.id))
        self.assertEqual(b.end_date.date().strftime("%m/%d/%Y") , data.get('end'))
        self.assertEqual(b.until.date().strftime("%m/%d/%Y") , data.get('until'))
        self.failUnlessEqual(response.status_code, 302)
        
        # delete it
        response = self.get(
            '/profile/%s/blackout/%s/' % (self.u.id, b.id)
          , {'_method' : 'DELETE'})
        self.failUnlessEqual(response.status_code, 302)
        # shouldn't this delete the blackout?
        b = first(Blackout.objects.filter(id = b.id))
        self.assertEqual(None, b)

        # create a new one
        data['end'] = date(2009, 5, 31).strftime("%m/%d/%Y")
        _ = data.pop('_method')
        response    = self.post(
            '/profile/%s/blackout/' % self.u.id, data)
        self.failUnlessEqual(response.status_code, 302)
        b = first(self.u.blackout_set.all())
        self.assertEqual(b.end_date.date().strftime("%m/%d/%Y"), data.get('end'))
        b.delete()

        # create another new one?
        data['until'] = ''
        response    = self.post(
            '/profile/%s/blackout/' % self.u.id, data)
        self.failUnlessEqual(response.status_code, 302)

    def test_blackout2(self):
        b     = self.create_blackout()
        start = datetime(2009, 1, 1)
        end   = datetime(2009, 1, 31)
        until = datetime(2010, 1, 31)
        data = {'start'       : start.date().strftime("%m/%d/%Y")
              , 'start_time'   : start.time().strftime("%H:%M")
              , 'end'         : end.date().strftime("%m/%d/%Y")
              , 'end_time'     : end.time().strftime("%H:%M")
              , 'repeats'      : 'Once'
              , 'until'       : until.strftime("%m/%d/%Y")
              , 'until_time'   : until.strftime("%H:%M")
              , 'description' : "This is a test blackout."
                }

        response = self.post(
            '/profile/%s/blackout/%s/' % (self.u.id, b.id), data)
        self.failUnlessEqual(response.status_code, 302)
        self.assertTrue("ERROR" not in response.content)

        # test that a blackout can't have a missing end date
        data['end'] = None
        data['end_time'] = None
        response = self.post(
            '/profile/%s/blackout/%s/' % (self.u.id, b.id), data)
        self.failUnlessEqual(response.status_code, 200)
        self.assertTrue("ERROR" in response.content)

    def test_blackout3(self):
        "Like test_blackout, but for a project"

        # create an initial blackout
        b     = self.create_blackout_for_project()
        start = datetime(2009, 1, 1)
        end   = datetime(2009, 1, 31)
        until = datetime(2010, 1, 31)
        data = {'start'       : start.date().strftime("%m/%d/%Y")
              , 'start_time'   : start.time().strftime("%H:%M")
              , 'end'         : end.date().strftime("%m/%d/%Y")
              , 'end_time'     : end.time().strftime("%H:%M")
              , 'repeats'      : 'Once'
              , 'until'       : until.strftime("%m/%d/%Y")
              , 'until_time'   : until.strftime("%H:%M")
              , 'description' : "This is a test project blackout."
              , '_method'     : "PUT"
                }

        # now edit it
        response = self.post(
            '/project/%s/blackout/%s/' % (self.p.pcode, b.id), data)
        b = first(Blackout.objects.filter(id = b.id))
        self.assertEqual(b.end_date.date().strftime("%m/%d/%Y") , data.get('end'))
        self.assertEqual(b.until.date().strftime("%m/%d/%Y") , data.get('until'))
        self.failUnlessEqual(response.status_code, 302)
        
        # now delete it
        response = self.get(
            '/project/%s/blackout/%s/' % (self.p.pcode, b.id)
          , {'_method' : 'DELETE'})
        self.failUnlessEqual(response.status_code, 302)
        # shouldn't this delete the blackout?
        b = first(Blackout.objects.filter(id = b.id))
        self.assertEqual(None, b)

        # now create one 
        data['end'] = date(2009, 5, 31).strftime("%m/%d/%Y")
        _ = data.pop('_method')
        response    = self.post(
            '/project/%s/blackout/' % self.p.pcode, data)
        self.failUnlessEqual(response.status_code, 302)
        b = first(self.p.blackout_set.all())
        self.assertEqual(b.end_date.date().strftime("%m/%d/%Y"), data.get('end'))
        b.delete()

    def test_get_period_day_time(self):

        # create a period
        s = create_sesshun()
        state = first(Period_State.objects.filter(abbreviation = 'S'))
        p = Period(session = s
                 , start = datetime(2009, 9, 9, 12)
                 , duration = 1.0
                 , state = state)
        p.save()         
        day = datetime(2009, 9, 9)
        
        # make sure it comes back in the correct day for UTC
        data = { 'start': day.strftime("%m/%d/%Y")
               , 'days' : 3
               , 'tz'   : 'UTC' }
        response = self.post('/schedule/public', data)
        calendar = response.context['calendar']
        exp = [(datetime(2009, 9, 9), [(datetime(2009, 9, 9, 12), datetime(2009, 9, 9, 13), False, False, p)])
             , (datetime(2009, 9, 10), [])
             , (datetime(2009, 9, 11), [])]

        self.assertEqual(exp, calendar)     

        # make sure it comes back in the correct day for EST
        data = { 'start': day.strftime("%m/%d/%Y")
               , 'days' : 3
               , 'tz'   : 'ET' }
        response = self.post('/schedule/public', data)
        calendar = response.context['calendar']
        exp = [(datetime(2009, 9, 9), [(datetime(2009, 9, 9, 8), datetime(2009, 9, 9, 9), False, False, p)])
             , (datetime(2009, 9, 10), [])
             , (datetime(2009, 9, 11), [])]
        self.assertEqual(exp, calendar)     

        # clean up
        p.remove() #delete()
        s.delete()

    def test_get_period_day_time2(self):

        # create a period
        s = create_sesshun()
        state = first(Period_State.objects.filter(abbreviation = 'S'))
        p = Period(session = s
                 , start = datetime(2009, 9, 2, 1)
                 , duration = 6.0
                 , state = state)
        p.save()         
        day = datetime(2009, 9, 1)

        # make sure it comes back in the correct day for UTC
        data = { 'start' : day.strftime("%m/%d/%Y")
               , 'days' : 3
               , 'tz' : 'UTC' }
        response = self.post('/schedule/public', data)
        calendar = response.context['calendar']
        exp = [(datetime(2009, 9, 1), [])
             , (datetime(2009, 9, 2), [(datetime(2009, 9, 2, 1), datetime(2009, 9, 2, 7), False, False, p)])
             , (datetime(2009, 9, 3), [])]
        self.assertEqual(exp, calendar)     

        # make sure it comes back in the correct day for EST
        data = { 'start' : day.strftime("%m/%d/%Y")
               , 'days' : 3
               , 'tz' : 'ET' }
        response = self.post('/schedule/public', data)
        calendar = response.context['calendar']
        exp = [(datetime(2009, 9, 1), [(datetime(2009, 9, 1, 21), datetime(2009, 9, 2), False, False, p)])
             , (datetime(2009, 9, 2), [(datetime(2009, 9, 2), datetime(2009, 9, 2, 3), False, False, p)])
             , (datetime(2009, 9, 3), [])]
        self.assertEqual(exp, calendar)     

        # show the cutoff: '(..)'
        data = { 'start' : day.strftime("%m/%d/%Y")
               , 'days' : 1
               , 'tz' : 'ET' }
        response = self.post('/schedule/public', data)
        calendar = response.context['calendar']
        exp = [(datetime(2009, 9, 1), [(datetime(2009, 9, 1, 21), datetime(2009, 9, 2), False, True, p)])]
        self.assertEqual(exp, calendar)  

        # clean up
        p.remove() #delete()
        s.delete()

# Testing Utilities
class TestDBReporter(NellTestCase):

    def test_DBReporter(self):
        "imply make sure that no exceptions are raised."
        db = DBReporter(quiet=True)
        db.report()

class TestDSSPrime2DSS(NellTestCase):

    def assert_DB_empty(self):
        # make sure our DB is almost blank 
        projects = Project.objects.all()
        self.assertEquals(1, len(projects))
        ss = Sesshun.objects.all()
        self.assertEquals(0, len(ss))
        users = User.objects.all()
        self.assertEquals(0, len(users))

    def compare_users(self, dbname):

        old = []
        new = []
        fold, fnew = self.compare_users_worker(dbname, "friends", old, new)
        pold, pnew = self.compare_users_worker(dbname, "authors", fold, fnew)
        return (pold, pnew)

    def compare_users_worker(self, dbname, table, old_users, new_users):
        
        db = mysql.connect(host   = "trent.gb.nrao.edu"
                     , user   = "dss"
                     , passwd = "asdf5!"
                     , db     = dbname
                            )
        cursor = db.cursor()
        
        query = "SELECT * FROM %s" % table
        cursor.execute(query)
        
        for row in cursor.fetchall():
            idcol = 3 if table == "friends" else 4 
            id = int(row[idcol])
            user = first(User.objects.filter(original_id = id).all())
            if user is None:
                if id not in new_users:
                    new_users.append(id)
            else:
                if id not in old_users:
                    old_users.append(id)
        
        return (old_users, new_users)

    def test_transfer(self):
 
        self.assert_DB_empty()

        t = DSSPrime2DSS(database = 'dss_prime_unit_tests')
        t.quiet = True
        t.transfer()

        # now test what we've got to make sure the transfer worked:

        # check out the projects
        projects = Project.objects.all()
        # len(93) == 92 + 1 prexisting project in models
        self.assertEquals(93, len(projects))

        # spot check project table
        projects = Project.objects.filter(semester__id = 15).all()
        self.assertEquals(1, len(projects))
        p = projects[0]
        self.assertEquals("GBT05C-027", p.pcode)
        self.assertEquals(False, p.thesis)
        self.assertEquals("Balser", p.friend.last_name)
        allots = p.allotments.all()
        self.assertEquals(1, len(allots))
        a = allots[0]
        self.assertEquals(5.0, a.total_time)
        self.assertEquals(4.0, a.grade)
        invs = p.investigator_set.all()
        self.assertEquals(2, len(invs))
        self.assertEquals("Mangum", invs[0].user.last_name)
        self.assertEquals("Wootten", invs[1].user.last_name)


        ss = p.sesshun_set.all()
        self.assertEquals(1, len(ss))
        s = ss[0]
        self.assertEquals("GBT05C-027-01", s.name)
        self.assertEquals(32.75, s.frequency)
        self.assertEquals(0, len(s.observing_parameter_set.all()))
        self.assertEquals(False, s.status.complete)
        self.assertEquals(5.0, s.allotment.total_time)
        self.assertEquals(4.0, s.allotment.grade)
        tgs = s.target_set.all()
        self.assertEquals(1, len(tgs))
        target = tgs[0]
        self.assertEqual("G34.3,S68N,DR21OH", target.source)
        self.assertAlmostEqual(0.022, target.vertical, 3)
        self.assertAlmostEqual(4.84, target.horizontal, 2)
        
        ss = Sesshun.objects.all()
        self.assertEquals(247, len(ss))

        users = User.objects.all()
        self.assertEquals(287, len(users))

    def test_transfer_only_new_1(self):

        self.assert_DB_empty()

        # populate into an empty DB: not much of a test, really!
        t = DSSPrime2DSS(database = 'dss_prime_unit_tests_2')
        t.quiet = True
        t.transfer_only_new()

        self.assertEquals( 53, len(t.new_projects))
        self.assertEquals(  0, len(t.old_projects))
        self.assertEquals(121, len(t.new_sessions))
        self.assertEquals(  0, len(t.old_sessions))
        self.assertEquals(199, len(t.new_users))
        self.assertEquals(  0, len(t.old_users))

    def test_transfer_only_new_2(self):

        self.assert_DB_empty()

        # populate the DB w/ 09C and earlier stuff
        t = DSSPrime2DSS(database = 'dss_prime_unit_tests')
        t.quiet = True
        t.transfer()

        # now that our model DB is initialized, predict how many new and
        # old users reside in our new source DB.
        old_users, new_users = self.compare_users('dss_prime_unit_tests_2')

        # now make sure we transfer only the new 10A stuff
        t = DSSPrime2DSS(database = 'dss_prime_unit_tests_2')
        t.quiet = True
        t.transfer_only_new()

        self.assertEquals( 53, len(t.new_projects))
        self.assertEquals(  0, len(t.old_projects))
        self.assertEquals(121, len(t.new_sessions))
        self.assertEquals(  0, len(t.old_sessions))
        self.assertEquals(len(new_users), len(t.new_users)) 
        self.assertEquals(len(old_users), len(t.old_users))

class TestReceiverCompile(NellTestCase):

    def setUp(self):

        super(TestReceiverCompile, self).setUp()
        self.nn = Receiver.get_abbreviations()
        self.rc = ReceiverCompile(self.nn)
        
        # normalize:   values[0] -> values[1]
        # denormalize: values[1] -> values[0]
        self.values = [('Q', [['Q']])
                     , ('((L | X) | C)', [['L', 'X', 'C']])
                     , ('(K & (L | S))', [['K'], ['L', 'S']])
                     , ('((342 | K) & (342 | Ka))'
                      , [['342', 'K'], ['342', 'Ka']] )
                     , ('((((L | X) | C) | S) & 342)'
                      , [['L', 'X', 'C', 'S'], ['342']])
                     ]
                    
    def test_pairValues(self):

        self.assertEquals('Q', self.rc.pairValues(['Q'], '|'))
        self.assertEquals('((L | X) | C)'
                         , self.rc.pairValues(['L', 'X', 'C'], '|'))
        self.assertEquals('(((((L | X) | C) | A) | B) | C)'          
                    , self.rc.pairValues(['L', 'X', 'C', 'A', 'B', 'C'], '|'))

    def test_denormalize(self):

        for v in self.values:
            self.assertEquals(v[0], self.rc.denormalize(v[1]))

    def test_symmettry(self):

        for v in self.values:
            self.assertEquals(v[0]
                            , self.rc.denormalize(self.rc.normalize(v[0])))

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

    def test_consolidate_events(self):
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
            # begin = b1 start, end = b5 end
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 4, 20))
        ]

        r = consolidate_events([(s, e) for s, e in zip(starts, ends)])
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

        r = consolidate_events([(s, e) for s, e in zip(starts, ends)])
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

        r = consolidate_events([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        r = consolidate_events([(s, e) for s, e in zip(starts, ends)])
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

        r = consolidate_events([(s, e) for s, e in zip(starts, ends)])
        self.assertEquals(expected, r)

        # No conflicts.
        r = consolidate_events([])
        self.assertEquals([], r)

class TestPSTMirrorDB(NellTestCase):

    # this really isn't a 'unit test' since I'm interacting with PST's
    # Database, but a test is better then no test
    def test_getProfileByID(self):

        db = PSTMirrorDB()
        # 823 - pst_id for pmargani
        info = db.getStaticContactInfoByID(823)

        # expected values
        emails = ['pmargani@nrao.edu'
                , 'paghots@hotmail.com'
                , 'pmargani@gmail.com']
        emailDescs = ['pmargani@nrao.edu (Work)'
                    , 'paghots@hotmail.com (Other)'
                    , 'pmargani@gmail.com (Personal)']
        phones = ['304-456-2202', '304-456-2206']        
        phoneDescs = ['304-456-2202 (Work)', '304-456-2206 (Other)']        
        postals = \
            ['NRAO, PO Box 2, Green Bank, West Virginia, 24944, USA, (Office)'
           , '49 columbus Ave., W. Bridgewater, Massachusetts, 02379, United States, (Other)']
        affiliations = ['National Radio Astronomy Observatory '
                      , 'Oregon, University of']
        self.assertEquals(emails, info['emails'])        
        self.assertEquals(emailDescs, info['emailDescs'])        
        self.assertEquals(phones, info['phones'])
        self.assertEquals(phoneDescs, info['phoneDescs'])
        self.assertEquals(postals, info['postals'])
        self.assertEquals(affiliations, info['affiliations'])
        self.assertEquals('pmargani', info['username'])
        self.assertEquals(True, info['status'])

    def test_getBadProfile(self):
        "Make sure we can handle bogus info."

        db = PSTMirrorDB()
        username = db.getUsername(0)
        self.assertEquals(None, username)

    # this is even more un "unit" test - we're interface with TWO
    # external systems
    def test_compareProfiles(self):
        "Compare the outputs from PSTQueryService & PSTMirrorDB"


        db = PSTMirrorDB()
        # 823 - pst_id for pmargani
        mirror = db.getStaticContactInfoByID(823)

        ui = PSTQueryService()
        xml = ui.getStaticContactInfoByID(823)
        pst = ui.parseUserDict(xml)

        # get rid of any elements that are different
        # by design, status key is different
        mirror.pop('status')
        mirror.pop('first_name')
        mirror.pop('last_name')
        pst.pop('status')
        # for some reason, the XML derived addresses aren't in order
        mirror.pop('postals')
        pst.pop('postals')
        self.assertEquals(mirror, pst)


class TestPSTQueryService(NellTestCase):

    def setUp(self):
        super(TestPSTQueryService, self).setUp()

        self.ui = PSTQueryService()

        self.me = User(first_name = "Paul"
                     , last_name = "Marganian"
                     , role_id = 1
                     , pst_id = 823)
        self.me.save()

        #<?xml version="1.0" encoding="UTF-8"?>
        self.xmlStr =  """
        <nrao:query-result xmlns:nrao="http://www.nrao.edu/namespaces/nrao" >
        <nrao:user id="823" domestic="true" xmlns:nrao="http://www.nrao.edu/namespaces/nrao">
        <nrao:name>
        <nrao:prefix>Mr</nrao:prefix>
        <nrao:first-name>Paul</nrao:first-name>
        <nrao:middle-name>Raffi</nrao:middle-name>
        <nrao:last-name>Marganian</nrao:last-name>
        </nrao:name>
        <nrao:contact-info>
        <nrao:email-addresses>
        <nrao:default-email-address addr="pmargani@nrao.edu">
        <nrao:description>Work</nrao:description>
        </nrao:default-email-address>
        <nrao:additional-email-address addr="paghots@hotmail.com">
        <nrao:description>Other</nrao:description>
        </nrao:additional-email-address>
        <nrao:additional-email-address addr="pmargani@gmail.com">
        <nrao:description>Personal</nrao:description>
        </nrao:additional-email-address>
        </nrao:email-addresses>
        <nrao:postal-addresses>
        <nrao:additional-postal-address>
        <nrao:address-type>Office</nrao:address-type>
        <nrao:streetline>NRAO</nrao:streetline>
        <nrao:streetline>PO Box 2</nrao:streetline>
        <nrao:city>Green Bank</nrao:city>
        <nrao:state>West Virginia</nrao:state>
        <nrao:country>USA</nrao:country>
        <nrao:postal-code>24944</nrao:postal-code>
        </nrao:additional-postal-address>
        <nrao:additional-postal-address>
        <nrao:address-type>Other</nrao:address-type>
        <nrao:streetline>49 columbus Ave.</nrao:streetline>
        <nrao:city>W. Bridgewater</nrao:city>
        <nrao:state>Massachusetts</nrao:state>
        <nrao:country>United States</nrao:country>
        <nrao:postal-code>02379</nrao:postal-code>
        </nrao:additional-postal-address>
        </nrao:postal-addresses>
        <nrao:phone-numbers>
        <nrao:default-phone-number number="304-456-2202">
        <nrao:description>Work</nrao:description>
        </nrao:default-phone-number>
        </nrao:phone-numbers>
        </nrao:contact-info>
        <nrao:affiliation-info>
        <nrao:default-affiliation id="5">
        <nrao:formal-name>National Radio Astronomy Observatory </nrao:formal-name>
        </nrao:default-affiliation>
        <nrao:additional-affiliation id="269">
        <nrao:formal-name>Oregon, University of</nrao:formal-name>
        </nrao:additional-affiliation>
        </nrao:affiliation-info>
        <nrao:misc-info>
        <nrao:user-type>NRAO Staff</nrao:user-type>
        <nrao:web-site>http://www.geocities.com/mangophenomena/</nrao:web-site>
        </nrao:misc-info>
        <nrao:account-info>
        <nrao:account-name>pmargani</nrao:account-name>
        <nrao:encrypted-password>d59c3e6cc6236139bd94307de0e775cc</nrao:encrypted-password>
        <nrao:entry-status>Suspect</nrao:entry-status>
        </nrao:account-info>
        </nrao:user>
        </nrao:query-result>
        """
        self.xml = et.fromstring(self.xmlStr)
        self.xmlDict = \
        {'contact-info': \
            {'phone-numbers':   {'default-phone-number': {'description' : 'Work'
                                                         ,'number' : '304-456-2202'}}
           , 'email-addresses': {'default-email-address': {'description' : 'Work'
                                                          ,'addr' : 'pmargani@nrao.edu'}
                             , 'additional-email-address': [{'description' : 'Other'
                                                            ,'addr' : 'paghots@hotmail.com'}
                                                          , {'description' : 'Personal'
                                                            ,'addr' : 'pmargani@gmail.com'}]}
           , 'postal-addresses': [{'city': 'Green Bank'
                                 , 'streetlines': ['NRAO', 'PO Box 2']
                                 , 'address-type': 'Office'
                                 , 'state': 'West Virginia'
                                 , 'country': 'USA'
                                 , 'postal-code': '24944'}
                                 , {'city': 'W. Bridgewater'
                                 , 'streetlines': ['49 columbus Ave.']
                                 , 'address-type': 'Other'
                                 , 'state': 'Massachusetts'
                                 , 'country': 'United States'
                                 , 'postal-code': '02379'}]                  
            }
            , 'name': {'prefix': 'Mr'
                     , 'first-name': 'Paul'
                     , 'middle-name': 'Raffi'
                     , 'last-name': 'Marganian'}
            , 'account-info': {'account-name': 'pmargani'         
                             , 'entry-status': 'Suspect'}
            , 'id': '823'
            , 'affiliation-info': [("National Radio Astronomy Observatory ", True)
                             , ("Oregon, University of", False)]
        }

    def test_parseUserXML(self):
        i = self.ui.parseUserXML(self.xml) 
        self.assertEqual(i, self.xmlDict)

    def test_parseUserDict(self):
        info = self.ui.parseUserDict(self.xmlDict)
        # expected values
        emails = ['pmargani@nrao.edu'
                , 'paghots@hotmail.com'
                , 'pmargani@gmail.com']
        emailDescs = ['pmargani@nrao.edu (Work)'
                    , 'paghots@hotmail.com (Other)'
                    , 'pmargani@gmail.com (Personal)']
        phones = ['304-456-2202']        
        phoneDescs = ['304-456-2202 (Work)']        
        postals = \
            ['NRAO, PO Box 2, Green Bank, West Virginia, 24944, USA, (Office)'
           , '49 columbus Ave., W. Bridgewater, Massachusetts, 02379, United States, (Other)']
        affiliations = ['National Radio Astronomy Observatory '
                      , 'Oregon, University of']
        self.assertEquals(emails, info['emails'])        
        self.assertEquals(emailDescs, info['emailDescs'])        
        self.assertEquals(phones, info['phones'])
        self.assertEquals(phoneDescs, info['phoneDescs'])
        self.assertEquals(postals, info['postals'])
        self.assertEquals(affiliations, info['affiliations'])
        self.assertEquals('pmargani', info['username'])
        self.assertEquals('Suspect', info['status'])

    # THis is NOT a unit -test: it actually interacts w/ the PST service!
    def test_pstServices(self):
        
        username =  self.ui.getUsername(self.me.pst_id)
        self.assertEquals('pmargani', username)

        id = self.ui.getIdFromUsername(username)
        self.assertEquals(823, id)

        # TBF: for some reason, the returned info has something trivially
        # different then self.xmlDict, but I don't know what.
        info = self.ui.getStaticContactInfoByUserName(username)
        self.assertEquals(self.xmlDict['name'],info['name'])

        info = self.ui.getStaticContactInfoByID(self.me.pst_id)
        self.assertEquals(self.xmlDict['name'],info['name'])

        info = self.ui.getProfileByID(self.me)
        self.assertEquals('pmargani', info['username'])

        
class TestUpdateEphemeris(NellTestCase):

    def testUpdate(self):

        up = UpdateEphemeris.UpdateEphemeris()
        up.quietReport = True

        # the no-op
        up.update()
        self.assertEquals(0, len(up.updates))
        self.assertEquals(0, len(up.errors))

        # let's observe Mars!
        s = create_sesshun()
        target = s.target_set.all()[0]
        target.system = first(System.objects.filter(name = "Ephemeris"))
        target.source = "Mars"
        target.save()

        # make sure we update it!
        up.update()
        self.assertEquals(1, len(up.updates))
        self.assertEquals(0, len(up.errors))

        # now let's observe a famouse comet
        target.source = "C/1995 O1 (Hale-Bopp)"
        target.save()
        up.update()
        self.assertEquals(1, len(up.updates))
        self.assertEquals(0, len(up.errors))

        # make sure we catch errors!
        target.source = "Mr. Nubbles!"
        target.save()
        up.update()
        self.assertEquals(0, len(up.updates))
        self.assertEquals(1, len(up.errors))

        # cleanup
        s.delete()

class TestNRAOBosDB(NellTestCase):

    def setUp(self):
        super(TestNRAOBosDB, self).setUp()

        self.bos = NRAOBosDB()

        #<?xml version="1.0" encoding="utf-8"?>
        self.xmlStr =  """
        <nrao:user domestic="true" id="dbalser" xmlns:nrao="http://www.nrao.edu/namespaces/nrao">
            <nrao:reservation id="2704">
                <nrao:startDate>2009-08-25</nrao:startDate>
                <nrao:endDate>2009-08-28</nrao:endDate>
            </nrao:reservation>
        </nrao:user>
        """
        self.xml = et.fromstring(self.xmlStr)

        self.xmlStr2 = """
        <nrao:reservations domestic="true" xmlns:nrao="http://www.nrao.edu/namespaces/nrao">
            <nrao:reservation id="3407">
                <nrao:user id="1">Mike McCarty</nrao:user>
                <nrao:startDate>2010-07-19</nrao:startDate>
                <nrao:endDate>2010-07-25</nrao:endDate>
            </nrao:reservation>
        </nrao:reservations>
        """
        self.xml2 = et.fromstring(self.xmlStr)

    def test_parseReservationsXML(self):

        dates = self.bos.parseReservationsXML(self.xmlStr)
        exp = [(datetime(2009, 8, 25, 0, 0), datetime(2009, 8, 28, 0, 0))]
        self.assertEqual(dates, exp)

    def test_parseReservationsDateRangeXML(self):

        dates = self.bos.parseReservationsDateRangeXML(self.xmlStr2)
        exp = [('1', 'Mike McCarty', datetime(2010, 7, 19, 0, 0), datetime(2010, 7, 25, 0, 0))]
        self.assertEqual(dates, exp)

class TestScheduleTools(NellTestCase):

    def setUp(self):
        super(TestScheduleTools, self).setUp()

        # setup some periods
        self.start = datetime(2000, 1, 1, 0)
        self.end   = self.start + timedelta(hours = 12)
        times = [(datetime(2000, 1, 1, 0), 5.0, "one")
               , (datetime(2000, 1, 1, 5), 3.0, "two")
               , (datetime(2000, 1, 1, 8), 4.0, "three")
               ]
        self.ps = []
        # init them as Scheduled, so that 'deleting' them just changes state
        state = first(Period_State.objects.filter(abbreviation = 'S'))        
        for start, dur, name in times:
            s = create_sesshun()
            s.name = name
            s.save()
            pa = Period_Accounting(scheduled = dur)
            pa.save()
            p = Period( session    = s
                      , start      = start
                      , duration   = dur
                      , state      = state
                      , accounting = pa
                      )
            p.save()          
            self.ps.append(p)

        self.backup = create_sesshun()
        self.backup.name = "backup"
        self.backup.status.backup = True
        self.backup.save()

    def tearDown(self):
        super(TestScheduleTools, self).tearDown()

        for p in self.ps:
            p.session.delete()
            p.remove() #delete()


    def test_getSchedulingRange(self):

        # scheduling range is 0:00 of timezone of first day
        # to the last day at 8:00 EST 

        # test it in winter time
        dt = datetime(2010, 1, 1)
        days = 2
        expStart = datetime(2010, 1, 1, 0)
        expEnd   = datetime(2010, 1, 3, 13)
        expDur = TimeAgent.dtDiffMins(expStart, expEnd)

        start, dur = ScheduleTools().getSchedulingRange(dt, 'UTC', days)
        self.assertEquals(expStart, start)
        self.assertEquals(expDur, dur)

        # make sure it works in ET too
        expStart = datetime(2010, 1, 1, 5)
        expEnd   = datetime(2010, 1, 3, 13)
        expDur = TimeAgent.dtDiffMins(expStart, expEnd)

        start, dur = ScheduleTools().getSchedulingRange(dt, 'ET', days)
        self.assertEquals(expStart, start)

        # test it in summer time
        dt = datetime(2010, 6, 10)
        days = 3
        expStart = datetime(2010, 6, 10, 0)
        expEnd   = datetime(2010, 6, 13, 12)
        expDur = TimeAgent.dtDiffMins(expStart, expEnd)

        start, dur = ScheduleTools().getSchedulingRange(dt, 'UTC', days)
        self.assertEquals(expStart, start)
        self.assertEquals(expDur, dur)

        # make sure it works in ET too
        expStart = datetime(2010, 6, 10, 4)
        expEnd   = datetime(2010, 6, 13, 12)
        expDur = TimeAgent.dtDiffMins(expStart, expEnd)

        start, dur = ScheduleTools().getSchedulingRange(dt, 'ET', days)
        self.assertEquals(expStart, start)
        self.assertEquals(expDur, dur)

    def test_changeSchedule1(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # try to mirror examples from Memo 11.2
        # Example 2 (Ex. 1 is a no op)
        change_start = self.ps[0].start + timedelta(hours = 2)
        ScheduleTools().changeSchedule(change_start 
                                    , 3.0 
                                    , self.backup
                                    , "other_session_other"
                                    , "SP broke.")
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        # check accounting after changing schedule
        scheduled = [5.0, 3.0, 3.0, 4.0]
        observed  = [2.0, 3.0, 3.0, 4.0]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(observed[i] , p.accounting.observed())
        # check affected periods
        canceled = ps[0]
        backup   = ps[1]
        self.assertEquals(self.start, canceled.start)
        self.assertEquals(2.0, canceled.duration)
        self.assertEquals(3.0, canceled.accounting.other_session_other)
        self.assertTrue("SP broke." in canceled.accounting.description)
        self.assertEquals(3.0, backup.accounting.short_notice)
        self.assertTrue("SP broke." in backup.accounting.description)
        
        tag = "Period backup: 2000-01-01 02:00:00 for  3.00 Hrs got  3.00 hours from: one: 2000-01-01 00:00:00 for  5.00 Hrs ( 3.00 hours)"
        self.assertTrue(tag in backup.accounting.description)
        self.assertTrue(tag in canceled.accounting.description)

    def test_changeSchedule2(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # try to mirror examples from Memo 11.2
        # Example 3 - last 3 hrs of first period replaced w/ nothing 
        change_start = self.ps[0].start + timedelta(hours = 2)
        desc = "SP croaked."
        ScheduleTools().changeSchedule(change_start 
                                    , 3.0 
                                    , None
                                    , "lost_time_other"
                                    , desc)
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        # check accounting after changing schedule
        scheduled = [5.0, 3.0, 4.0]
        observed  = [2.0, 3.0, 4.0]
        times = [p.start for p in self.ps]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(observed[i] , p.accounting.observed())
            self.assertEquals(times[i] , p.start)
        # check affected periods
        canceled = ps[0]
        self.assertEquals(self.start, canceled.start)
        self.assertEquals(2.0, canceled.duration)
        self.assertEquals(3.0, canceled.accounting.lost_time_other)
        self.assertTrue(desc in canceled.accounting.description)

        tag = "No Period got time from: one: 2000-01-01 00:00:00 for  5.00 Hrs ( 3.00 hours)"
        self.assertTrue(tag in canceled.accounting.description)

    def test_changeSchedule3(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # try to mirror examples from Memo 11.2
        # Example 4 (Second Period start early at expense of first)
        change_start = self.ps[1].start - timedelta(hours = 1)
        backup = self.ps[1].session
        desc = "Session Two starting hour early; not billed time for Two."
        ScheduleTools().changeSchedule(change_start 
                                    , 1.0 
                                    , backup
                                    , "other_session_weather"
                                    , desc)
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        # check accounting after changing schedule
        scheduled = [5.0, 1.0, 3.0, 4.0]
        observed  = [4.0, 1.0, 3.0, 4.0]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(observed[i] , p.accounting.observed())
        # check affected periods
        canceled = ps[0]
        backup   = ps[1]
        self.assertEquals(self.start, canceled.start)
        self.assertEquals(4.0, canceled.duration)
        self.assertEquals(1.0, canceled.accounting.other_session_weather)
        self.assertTrue(desc in canceled.accounting.description)
        self.assertEquals(1.0, backup.accounting.short_notice)
        self.assertTrue(desc in backup.accounting.description)                        
        # now, don't bill this new period the hour
        self.assertEquals(1.0, backup.accounting.observed())
        self.assertEquals(1.0, backup.accounting.time_billed())
        backup.accounting.not_billable = 1.0
        backup.accounting.save()
        self.assertEquals(1.0, backup.accounting.observed())
        self.assertEquals(0.0, backup.accounting.time_billed())

    def test_changeSchedule4(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # try to mirror examples from Memo 11.2
        # Example 5 (scheduled first period replaced w/ backup)
        change_start = self.ps[0].start 
        desc = "Hurricane Georges"
        ScheduleTools().changeSchedule(change_start 
                                    , 5.0 
                                    , self.backup
                                    , "other_session_weather"
                                    , desc)
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0, ignore_deleted = False)
        # TBF: how to handle these Periods that r compleletly replaced?
        canceled_ps = [p for p in ps if p.state.abbreviation == 'D']
        ps = [p for p in ps if p.state.abbreviation != 'D']
        # check accounting after changing schedule
        scheduled = [5.0, 3.0, 4.0]
        observed  = [5.0, 3.0, 4.0]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(observed[i] , p.accounting.observed())
        # check affected periods
        canceled = first(Period.objects.filter(state__abbreviation = 'D'))
        backup   = ps[0]
        self.assertEquals(self.start, canceled.start)
        self.assertEquals(5.0, canceled.duration)
        self.assertEquals(5.0, canceled.accounting.other_session_weather)
        self.assertTrue(desc in canceled.accounting.description)
        self.assertEquals(5.0, backup.accounting.short_notice)
        self.assertTrue(desc in backup.accounting.description)

    def test_changeSchedule_end_early(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # have a new session override the last one, and make the middle
        # one end early
        change_start = self.ps[1].start + timedelta(hours = 2.0)
        desc = "fix this bug"
        ScheduleTools().changeSchedule(change_start 
                                    , 5.0 
                                    , self.backup
                                    , "other_session_other"
                                    , desc)
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0, ignore_deleted = False)
        # make sure we don't get deleted period
        ps = [p for p in ps if p.state.abbreviation != 'D']
        self.assertEquals(3, len(ps))

        # check accounting after changing schedule
        scheduled = [5.0, 3.0, 5.0]
        observed  = [5.0, 2.0, 5.0]
        oso       = [0.0, 1.0, 0.0]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(oso[i] , p.accounting.other_session())
            self.assertEquals(observed[i] , p.accounting.observed())
        # check affected periods
        canceled = first(Period.objects.filter(state__abbreviation = 'D'))
        self.assertEquals(canceled.start, self.ps[2].start)
        
    def test_changeSchedule_ultimate_chaos(self):
        "gitrdone!"

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # have a new session start before the first ends, and go all
        # the way to near the end of the last
        # one end early
        change_start = self.ps[0].start + timedelta(hours = 2.0)
        desc = "chaos!"
        ScheduleTools().changeSchedule(change_start 
                                    , 8.0 
                                    , self.backup
                                    , "other_session_other"
                                    , desc)
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0, ignore_deleted = False)
        # make sure we don't get deleted period
        ps = [p for p in ps if p.state.abbreviation != 'D']
        self.assertEquals(3, len(ps))

        # check accounting after changing schedule
        scheduled = [5.0, 8.0, 4.0]
        observed  = [2.0, 8.0, 2.0]
        oso       = [3.0, 0.0, 2.0]
        sn        = [0.0, 8.0, 0.0]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
        # check affected periods
        canceled = first(Period.objects.filter(state__abbreviation = 'D'))
        self.assertEquals(canceled.start, self.ps[1].start)
        
    def test_changeSchedule_bisect(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        # make sure we can handle bi-secting a pre-existing period
        change_start = self.ps[0].start + timedelta(hours = 1.0)
        desc = "bisect!"
        ScheduleTools().changeSchedule(change_start 
                                    , 2.0 
                                    , self.backup
                                    , "other_session_other"
                                    , desc)
        
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        self.assertEquals(5, len(ps))
        # check accounting after changing schedule
        scheduled = [5.0, 8.0, 4.0]
        observed  = [1.0, 2.0, 2.0, 3.0, 4.0]
        oso       = [3.0, 0.0, 2.0]
        sn        = [0.0, 8.0, 0.0]
        for i, p in enumerate(ps):
            #self.assertEquals(scheduled[i], p.accounting.scheduled)
            #self.assertEquals(sn[i],        p.accounting.short_notice)
            #self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())

    def test_shiftPeriodBoundaries_start_later(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        new_start = self.ps[1].start + timedelta(hours = 1.0)
        desc = "starting second period an hour latter"
        ScheduleTools().shiftPeriodBoundaries(self.ps[1]
                                     , True # start boundary
                                     , new_start 
                                     , self.ps[0]
                                     , "other_session_other"
                                     , desc)
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)

        # check accounting after changing schedule
        scheduled = [6.0, 3.0, 4.0]
        observed  = [6.0, 2.0, 4.0]
        oso       = [0.0, 1.0, 0.0]
        sn        = [1.0, 0.0, 0.0]
        dur       = [6.0, 2.0, 4.0]
        starts    = [self.ps[0].start
                   , new_start
                   , self.ps[2].start]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
            self.assertEquals(dur[i],       p.duration)
            self.assertEquals(starts[i],    p.start)

        tag = "Period one: 2000-01-01 00:00:00 for  5.00 Hrs got  1.00 hours from: two: 2000-01-01 05:00:00 for  3.00 Hrs ( 1.00 hours) ]"

        self.assertTrue(desc in ps[0].accounting.description)
        self.assertTrue(desc in ps[1].accounting.description)
        self.assertTrue(tag  in ps[0].accounting.description)
        self.assertTrue(tag  in ps[1].accounting.description)

    def test_shiftPeriodBoundaries_start_earlier(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        new_start = self.ps[1].start - timedelta(hours = 1.0)
        desc = "starting second period an hour early"
        ScheduleTools().shiftPeriodBoundaries(self.ps[1]
                                     , True # start boundary
                                     , new_start 
                                     , self.ps[0]
                                     , "other_session_other"
                                     , desc)
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        # check accounting after changing schedule
        scheduled = [5.0, 4.0, 4.0]
        observed  = [4.0, 4.0, 4.0]
        oso       = [1.0, 0.0, 0.0]
        sn        = [0.0, 1.0, 0.0]
        dur       = [4.0, 4.0, 4.0]
        starts    = [self.ps[0].start
                   , new_start
                   , self.ps[2].start]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
            self.assertEquals(dur[i],       p.duration)
            self.assertEquals(starts[i],    p.start)

        self.assertTrue(desc in ps[0].accounting.description)
        self.assertTrue(desc in ps[1].accounting.description)

    def test_shiftPeriodBoundaries_end_earlier(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        new_end = self.ps[1].end() - timedelta(hours = 1.0)
        desc = "ending second period an hour early"
        ScheduleTools().shiftPeriodBoundaries(self.ps[1]
                                     , False # end boundary
                                     , new_end 
                                     , self.ps[2]
                                     , "other_session_other"
                                     , desc)
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        # check accounting after changing schedule
        scheduled = [5.0, 3.0, 5.0]
        observed  = [5.0, 2.0, 5.0]
        oso       = [0.0, 1.0, 0.0]
        sn        = [0.0, 0.0, 1.0]
        dur       = [5.0, 2.0, 5.0]
        starts    = [self.ps[0].start
                   , self.ps[1].start
                   , new_end]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
            self.assertEquals(dur[i],       p.duration)
            self.assertEquals(starts[i],    p.start)

        self.assertTrue(desc in ps[1].accounting.description)
        self.assertTrue(desc in ps[2].accounting.description)

    def test_shiftPeriodBoundaries_end_latter(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        new_end = self.ps[1].end() + timedelta(hours = 1.0)
        desc = "ending second period an hour latter"
        ScheduleTools().shiftPeriodBoundaries(self.ps[1]
                                     , False # end boundary
                                     , new_end 
                                     , self.ps[2]
                                     , "other_session_other"
                                     , desc)
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0)
        # check accounting after changing schedule
        scheduled = [5.0, 4.0, 4.0]
        observed  = [5.0, 4.0, 3.0]
        oso       = [0.0, 0.0, 1.0]
        sn        = [0.0, 1.0, 0.0]
        dur       = [5.0, 4.0, 3.0]
        starts    = [self.ps[0].start
                   , self.ps[1].start
                   , new_end]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
            self.assertEquals(dur[i],       p.duration)
            self.assertEquals(starts[i],    p.start)

        self.assertTrue(desc in ps[1].accounting.description)
        self.assertTrue(desc in ps[2].accounting.description)

    def test_shiftPeriodBoundaries_start_way_earlier(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        new_start = self.ps[2].start - timedelta(hours = 4.0)
        desc = "starting third period four hours early"
        ScheduleTools().shiftPeriodBoundaries(self.ps[2]
                                     , True # start boundary
                                     , new_start 
                                     , self.ps[1]
                                     , "other_session_other"
                                     , desc)
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0, ignore_deleted = False)
        # check accounting after changing schedule
        names     = ["one", "three", "two"]
        scheduled = [5.0, 8.0, 3.0]
        observed  = [4.0, 8.0, 0.0]
        oso       = [1.0, 0.0, 3.0]
        sn        = [0.0, 4.0, 0.0]
        dur       = [4.0, 8.0, 3.0]
        states    = ['S', 'S', 'D']
        starts    = [self.ps[0].start
                   , new_start
                   , self.ps[1].start]
        for i, p in enumerate(ps):
            self.assertEquals(names[i],     p.session.name)
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
            self.assertEquals(dur[i],       p.duration)
            self.assertEquals(starts[i],    p.start)
            self.assertEquals(states[i],    p.state.abbreviation)
            self.assertTrue(desc in p.accounting.description)

    def test_shiftPeriodBoundaries_end_way_latter(self):

        # check accounting before changing schedule
        scheduled = [5.0, 3.0, 4.0]
        for i, p in enumerate(self.ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(scheduled[i], p.accounting.observed())

        new_end = self.ps[0].end() + timedelta(hours = 4.0)
        desc = "ending first period four hours latter"
        ScheduleTools().shiftPeriodBoundaries(self.ps[0]
                                     , False # end boundary
                                     , new_end 
                                     , self.ps[1]
                                     , "other_session_other"
                                     , desc)
        # get the periods from the DB again for updated values
        ps = Period.get_periods(self.start, 12.0*60.0, ignore_deleted = False)
        # check accounting after changing schedule
        scheduled = [9.0, 3.0, 4.0]
        observed  = [9.0, 0.0, 3.0]
        oso       = [0.0, 3.0, 1.0]
        sn        = [4.0, 0.0, 0.0]
        dur       = [9.0, 3.0, 3.0]
        states    = ['S', 'D', 'S']
        starts    = [self.ps[0].start
                   , self.ps[1].start
                   , new_end]
        for i, p in enumerate(ps):
            self.assertEquals(scheduled[i], p.accounting.scheduled)
            self.assertEquals(sn[i],        p.accounting.short_notice)
            self.assertEquals(oso[i],       p.accounting.other_session())
            self.assertEquals(observed[i],  p.accounting.observed())
            self.assertEquals(dur[i],       p.duration)
            self.assertEquals(starts[i],    p.start)
            self.assertEquals(states[i],    p.state.abbreviation)
            self.assertTrue(desc in p.accounting.description)

class TestTimeAccounting(NellTestCase):

    def setUp(self):
        super(TestTimeAccounting, self).setUp()

        self.project = Project.objects.order_by('pcode').all()[0]

        # setup some periods
        self.start = datetime(2000, 1, 1, 0)
        self.end   = self.start + timedelta(hours = 12)
        times = [(datetime(2000, 1, 1, 0), 5.0, "one")
               , (datetime(2000, 1, 1, 5), 3.0, "two")
               , (datetime(2000, 1, 1, 8), 4.0, "three")
               ]
        self.ps = []
        state = first(Period_State.objects.filter(abbreviation = 'P'))        
        for start, dur, name in times:
            s = create_sesshun()
            s.name = name
            s.save()
            pa = Period_Accounting(scheduled = dur)
            pa.save()
            p = Period( session    = s
                      , start      = start
                      , duration   = dur
                      , state      = state
                      , accounting = pa
                      )
            p.save()          
            self.ps.append(p)

        self.ta = TimeAccounting()

    def tearDown(self):
        super(TestTimeAccounting, self).tearDown()

        for p in self.ps:
            p.session.delete()
            p.delete()

    def test_getTimeLeft(self):

        # Project has no time allotted, and 5 + 3 + 4 = 12 hrs billed
        timeLeft = self.ta.getTimeLeft(self.project)
        self.assertEqual(-12.0, timeLeft)

        names = ["one", "three", "two"]
        times = [-2.0, -1.0, 0.0]

        for i, s in enumerate(self.project.sesshun_set.order_by("name").all()):
            timeLeft = self.ta.getTimeLeft(s)
            self.assertEqual(names[i], s.name)
            self.assertEqual(times[i], timeLeft)


    def test_getTime(self):

        pScheduled = self.ta.getTime('scheduled', self.project)
        self.assertEqual(pScheduled, 12.0)

        pBilled = self.ta.getTime('time_billed', self.project)
        self.assertEqual(pBilled, 12.0)


        pNotBillable = self.ta.getTime('not_billable', self.project)
        self.assertEqual(pNotBillable, 0.0)

        # now change something and watch it bubble up
        self.ps[0].accounting.not_billable = 1.0
        self.ps[0].accounting.save()
        project = Project.objects.order_by('pcode').all()[0]

        pNotBillable = self.ta.getTime('not_billable', self.ps[0].session)
        self.assertEqual(pNotBillable, 1.0)

        pNotBillable = self.ta.getTime('not_billable', project)
        self.assertEqual(pNotBillable, 1.0)

    def test_getTime_2(self):

        # check time dependencies at the project level
        dt1   = self.start + timedelta(hours = 1)
        projCmpSchd = self.ta.getTime('scheduled', self.project, dt1, True)
        self.assertEqual(projCmpSchd, 5.0)
        projUpSchd = self.ta.getTime('scheduled',  self.project, dt1, False)
        self.assertEqual(projUpSchd, 7.0)

        dt2   = self.start + timedelta(hours = 6)
        projCmpSchd = self.ta.getTime('scheduled', self.project, dt2, True)
        self.assertEqual(projCmpSchd, 8.0)
        projUpSchd = self.ta.getTime('scheduled',  self.project, dt2, False)
        self.assertEqual(projUpSchd, 4.0)

        # check time dependencies at the session level
        s1 = self.ps[0].session
        sessCmpSchd = self.ta.getTime('scheduled', s1, dt2, True)
        self.assertEqual(sessCmpSchd, 5.0)
        sessUpSchd = self.ta.getTime('scheduled',  s1, dt2, False)
        self.assertEqual(sessUpSchd, 0.0)

    def test_getUpcomingTimeBilled(self):
        prjUpBilled = self.ta.getUpcomingTimeBilled(self.project)
        self.assertEqual(prjUpBilled, 0.0)

        # change 'now'
        dt = self.start - timedelta(hours = 1)
        prjUpBilled = self.ta.getUpcomingTimeBilled(self.project, now=dt)
        self.assertEqual(prjUpBilled, 12.0)

    def test_getTimeRemainingFromCompleted(self):
        remaining = self.ta.getTimeRemainingFromCompleted(self.project)
        self.assertEqual(remaining, -12.0) # 0 - 12

        remaining = self.ta.getTimeRemainingFromCompleted(self.ps[0].session)
        self.assertEqual(remaining, -2.0) # 3 - 5

    def test_jsondict(self):

        dct = self.ta.jsondict(self.project)
        self.assertEqual(3, len(dct['sessions']))
        self.assertEqual(1, len(dct['sessions'][0]['periods']))

        # test identity
        self.ta.update_from_post(self.project, dct)
        # get it fressh from the DB
        project = Project.objects.order_by('pcode').all()[0]
        dct2 = self.ta.jsondict(project)
        self.assertEqual(dct, dct2)

        # now change something
        dct['sessions'][0]['periods'][0]['not_billable'] = 1.0
        self.ta.update_from_post(project, dct)
        # get it fressh from the DB
        project = Project.objects.order_by('pcode').all()[0]
        dct2 = self.ta.jsondict(project)
        # they're different becuase not_billable bubbles up
        self.assertNotEqual(dct, dct2)
        b = dct2['not_billable'] 
        self.assertEqual(b, 1.0)

    def test_report(self):

        # just make sure it doesn't blow up
        self.ta.quietReport = True
        self.ta.report(self.project)

class TestIcalAntioch(NellTestCase):
        
    def testWriteSchedule(self):

        #ic = IcalAntioch.IcalAntioch(None, None)
        ic = IcalAntioch(None, None)

        pStr = "Period: 18 (0)  at 2006-02-01 00:00:00 for 420 (420) with score of 3.669943 from 2006-02-01 00:00:00 Scheduled  band: X  RA: 4.674547 grade: 4.0"

        dct = ic.parsePeriod(pStr)

        self.assertEquals('18', dct["sName"])
        self.assertEquals('X',  dct["band"])

        dct['id'] = 34
        event = ic.createEvent(dct)

        self.assertTrue(event is not None)
