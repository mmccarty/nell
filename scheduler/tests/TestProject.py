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

from datetime               import datetime, timedelta
from test_utils             import BenchTestCase, timeIt
from scheduler.models       import *
from scheduler.httpadapters import *
from utils                  import create_sesshun, create_blackout

class TestProject(BenchTestCase):

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

        # Create the first user (on project) 
        self.user1 = User(sanctioned = True
                     )
        self.user1.save()

        self.investigator1 =  Investigator(project  = self.project
                                         , user     = self.user1
                                         , observer = True)
        self.investigator1.save()
         
        # Create the second user (on project)
        self.user2 = User(sanctioned = True
                     )
        self.user2.save()

        self.investigator2 =  Investigator(project  = self.project
                                         , user     = self.user2
                                         , observer = True)
        self.investigator2.save()

        # Create the third unsanctioned user (on project)
        self.user3 = User(sanctioned = False
                     )
        self.user3.save()

        self.investigator3 =  Investigator(project  = self.project
                                         , user     = self.user3
                                         , observer = True)
        self.investigator3.save()

        # make a session
        self.sesshun = create_sesshun()
        self.sesshun.project = self.project
        self.sesshun.save()

        # make a period for it
        fdata = {'session'  : self.sesshun.id
               , 'date'     : '2009-06-01'
               , 'time'     : '10:00'
               , 'duration' : 1.0
               , 'backup'   : False}
        self.period = Period()
        self.period_adapter = PeriodHttpAdapter(self.period)
        self.period_adapter.init_from_post(fdata, 'UTC')

    def tearDown(self):
        super(TestProject, self).tearDown()
        self.investigator3.delete()
        self.user3.delete()
        self.investigator2.delete()
        self.user2.delete()
        self.investigator1.delete()
        self.user1.delete()
        self.period.delete()
        self.sesshun.delete()
        self.project.delete()

    @timeIt
    def test_get_blackout_times1(self):
        # Create Investigator1's 3 blackouts.
        blackout11 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 11),
                                     end    = datetime(2009, 1, 3, 11))

        blackout12 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 18),
                                     end    = datetime(2009, 1, 4, 18))

        blackout13 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 2, 12),
                                     end    = datetime(2009, 1, 4, 20))

        # Create Investigator2's 2 blackouts.
        blackout21 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 11),
                                     end    = datetime(2009, 1, 3, 11))

        blackout22 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 18),
                                     end    = datetime(2009, 1, 4, 13))

        # Create Investigator 3's blackouts.
        blackout31 = create_blackout(user   = self.user3,
                                     repeat = 'Once',
                                     start  = datetime(2008, 12, 31, 11),
                                     end    = datetime(2009,  1,  1,  9))

        blackout32 = create_blackout(user   = self.user3,
                                     repeat = 'Once',
                                     start  = datetime(2009,  1,  2, 16),
                                     end    = datetime(2009,  1,  3, 12))

        # stay out of the blackouts range
        expected = []
        today = datetime(2008, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals(expected, r)

        # Now we can finally do our test.
        expected = [
            (datetime(2009, 1, 1, 11), datetime(2009, 1, 4, 13))
        ]

        today = datetime(2009, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals(expected, r)

        # Now complicate things - add project blackouts
        pBlackout1 = create_blackout(project = self.project,
                                     repeat  = 'Once',
                                     start   = datetime(2009, 1, 4, 0),
                                     end     = datetime(2009, 1, 5, 0))
        pBlackout2 = create_blackout(project = self.project,
                                     repeat  = 'Once',
                                     start   = datetime(2009, 1, 6, 0),
                                     end     = datetime(2009, 1, 8, 0))

        # we should see the present result extended by the first 
        # project blackout, in addition to the second blackout
        expected = [
            (datetime(2009, 1, 6, 0),  datetime(2009, 1, 8, 0))
          , (datetime(2009, 1, 1, 11), datetime(2009, 1, 5, 0))
        ]

        r = self.project.get_blackout_times(today, later)
        self.assertEquals(expected, r)

        # complicate things a bit more - use a weekly proj blackout
        pBlackout2.initialize(tz     = 'UTC',
                              repeat = Repeat.objects.get(repeat = 'Weekly'),
                              start  = datetime(2009, 1, 6, 0),
                              end    = datetime(2009, 1, 8, 0),
                              until  = datetime(2010, 1, 1, 0))

        # we should see similar results to before, but now the weeklys
        expected = [
            (datetime(2009, 1, 6,  0), datetime(2009, 1, 8,  0))
          , (datetime(2009, 1, 13, 0), datetime(2009, 1, 15, 0))
          , (datetime(2009, 1, 20, 0), datetime(2009, 1, 22, 0))
          , (datetime(2009, 1, 27, 0), datetime(2009, 1, 29, 0))
          , (datetime(2009, 1, 1, 11), datetime(2009, 1, 5,  0))
        ]

        r = self.project.get_blackout_times(today, later)
        self.assertEquals(expected, r)

        # but what if the investigators show up on site?
        res1 = Reservation(user = self.user3
                         , start_date = datetime(2009, 1, 1, 0)
                         , end_date   = datetime(2009, 1, 2, 0)
                          )
        res1.save()

        expected = [(today, datetime(2009, 1, 1, 9))
                  , (datetime(2009, 1, 2, 16), later)]
        r = self.project.get_unsanctioned_users_blackout_times(today, later)
        self.assertEquals(expected, r)

        expected = [(datetime(2009, 1, 2, 16), datetime(2009, 1, 4, 13))]
        r = self.project.get_users_blackout_times(today, later)
        self.assertEquals(expected, r)

        expected = [
            (datetime(2009, 1, 6,  0), datetime(2009, 1, 8,  0))
          , (datetime(2009, 1, 13, 0), datetime(2009, 1, 15, 0))
          , (datetime(2009, 1, 20, 0), datetime(2009, 1, 22, 0))
          , (datetime(2009, 1, 27, 0), datetime(2009, 1, 29, 0))
          , (datetime(2009, 1, 2, 16), datetime(2009, 1, 5,  0))
        ]
        r = self.project.get_blackout_times(today, later)
        self.assertEquals(expected, r)

        # Q: what is the behavior when blackouts straddle range?
        # A: returned blackouts are NOT truncated
        newLater = datetime(2009, 1, 4, 12)
        r = self.project.get_blackout_times(today, newLater)
        expected = [(datetime(2009, 1, 2, 16), datetime(2009, 1, 5))]
        self.assertEquals(expected, r)

        # Clean up
        res1.delete()
        blackout32.delete()
        blackout31.delete()
        blackout22.delete()
        blackout21.delete()
        blackout13.delete()
        blackout12.delete()
        blackout11.delete()

    def test_get_blackout_times2(self):
        # Create Investigator1's 3 blackouts.
        self.investigator1.observer = False
        self.investigator1.save()

        blackout11 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 11),
                                     end    = datetime(2009, 1, 3, 11))

        blackout12 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 18),
                                     end    = datetime(2009, 1, 4, 18))

        blackout13 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 2, 12),
                                     end    = datetime(2009, 1, 4, 20))

        # Create Investigator2's 2 blackouts.
        self.investigator2.observer = False
        self.investigator2.save()

        blackout21 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 11),
                                     end    = datetime(2009, 1, 3, 11))

        blackout22 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 18),
                                     end    = datetime(2009, 1, 4, 13))

        today = datetime(2009, 1, 1)
        later = today + timedelta(days = 30)
        r = self.project.get_blackout_times(today, later)
        self.assertEquals([], r)

        r = self.project.get_unsanctioned_users_blackout_times(today, later)
        self.assertEquals([(today, later)], r)

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
        blackout11 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 11),
                                     end    = datetime(2009, 1, 3, 11))

        blackout12 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 18),
                                     end    = datetime(2009, 1, 4, 18))

        blackout13 = create_blackout(user  = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 2, 12),
                                     end    = datetime(2009, 1, 4, 20))

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
        blackout11 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 11),
                                     end    = datetime(2009, 1, 3, 11))

        blackout12 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 1, 18),
                                     end    = datetime(2009, 1, 4, 18))

        blackout13 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 1, 2, 12),
                                     end    = datetime(2009, 1, 4, 20))

        # Create Investigator2's 2 blackouts.
        blackout21 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 2, 1, 11),
                                     end    = datetime(2009, 2, 3, 11))

        blackout22 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 3, 1, 18),
                                     end    = datetime(2009, 3, 4, 13))

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

    @timeIt
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
        othersesshun.delete(force = True)
        otherproject.delete(force = True)

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
        days = self.project.get_prescheduled_days(start, start + timedelta(days = 1))
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
        days = self.project.get_prescheduled_days(start, start + timedelta(days = 1))
        self.assertEquals(1, len(days))
        self.assertEquals(days[0], datetime(2009, 6, 1))
        days = self.project.get_prescheduled_days(start + timedelta(days=1)
                                                , start + timedelta(days=2))
        self.assertEquals(0, len(days))

        # Now make that whole day prescheduled period part of the project.
        anotherperiod.session = self.sesshun
        anotherperiod.save()

        # Test again
        days = self.project.get_prescheduled_days(start, end)
        self.assertEquals(0, len(days))
        days = self.project.get_prescheduled_days(start, start + timedelta(days = 1))
        self.assertEquals(0, len(days))

        # Clean up
        anotherperiod.delete()
        otherperiod.delete()
        othersesshun.delete(force = True)
        otherproject.delete(force = True)

    @timeIt
    def test_get_active_windows(self):

        s = self.project.sesshun_set.all()[0]
        s.session_type = Session_Type.objects.get(type = "windowed")
        s.save()

        w = Window(session = s
                 , total_time = 4.0)
        w.save()
        wr1 = WindowRange(start_date = datetime(2006, 10, 1)
                        , duration = 7
                        , window = w)
        wr1.save()                        
        wr2 = WindowRange(start_date = datetime(2006, 10, 10)
                        , duration = 20
                        , window = w)
        wr2.save()                        


        ws = self.project.get_windows()
        self.assertEquals(1, len(ws))

        # windows aren't over yet
        now = datetime(2006, 9, 1)
        ws = self.project.get_active_windows(now = now)
        self.assertEquals(1, len(ws))
        self.assertEquals(w, ws[0])

        # windows are over
        now = datetime(2006, 12, 1)
        ws = self.project.get_active_windows(now = now)
        self.assertEquals(0, len(ws))
                        
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

