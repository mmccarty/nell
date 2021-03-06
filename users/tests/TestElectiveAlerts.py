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

from test_utils             import NellTestCase
from tools.alerts           import ElectiveAlerts
from scheduler.models       import *
from scheduler.httpadapters import *
from scheduler.tests.utils  import create_sesshun, create_blackout

class TestElectiveAlerts(NellTestCase):

    def setUp(self):
        super(TestElectiveAlerts, self).setUp()

        # setup a project with:
        #   * two users with blackouts
        #   * two elective sessions
        #   * limited receiver availability

        # make the calendar look like this:
        # electives:
        #   1: 4/2,4/3,4/7,4/9  &   2: 4/8,4/14,4/20

        # user 1 blackouts:
        # 4/1 - 4/3
        # 4/5 - 4/7

        # user 2 blackouts:
        # 4/1 - 4/4
        # 4/3 - 4/8

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
        self.user1 = User(sanctioned = True)
        self.user1.save()

        self.investigator1 =  Investigator(project  = self.project
                                         , user     = self.user1
                                         , observer = True)
        self.investigator1.save()

        # Create the second user (on project)
        self.user2 = User(sanctioned = True)
        self.user2.save()

        self.investigator2 =  Investigator(project  = self.project
                                         , user     = self.user2
                                         , observer = True)
        self.investigator2.save()

        # Create Investigator1's blackouts.
        blackout11 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 4, 1, 11),
                                     end    = datetime(2009, 4, 4, 20))

        blackout12 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 4, 5, 18),
                                     end    = datetime(2009, 4, 8,  9))

        blackout13 = create_blackout(user   = self.user1,
                                     repeat = 'Once',
                                     start  = datetime(2009, 4,  9,  2),
                                     end    = datetime(2009, 4, 17,  9))

        # Create Investigator2's blackouts.
        blackout21 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 4, 1, 11),
                                     end    = datetime(2009, 4, 5, 11))

        blackout22 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 4, 6, 18),
                                     end    = datetime(2009, 4, 8, 10))

        blackout23 = create_blackout(user   = self.user2,
                                     repeat = 'Once',
                                     start  = datetime(2009, 4, 13, 18),
                                     end    = datetime(2009, 4, 25, 13))

        # make a session
        self.sesshun = create_sesshun()
        self.sesshun.session_type = \
            Session_Type.objects.get(type = "elective")
        self.sesshun.project = self.project
        # '1070' available 4/6 - 4/16
        SessionHttpAdapter(self.sesshun).save_receivers('1070')
        self.sesshun.save()

        # make the first elective
        self.elective1 = Elective(session = self.sesshun, complete = False)
        self.elective1.save()

        # make periods for it (10:15-14:15)
        dates = ['2009-04-02', '2009-04-03', '2009-04-07', '2009-04-09']
        for date in dates:
            fdata = {'session'  : self.sesshun.id
                   , 'date'     : date
                   , 'time'     : '10:00'
                   , 'duration' : 4.0
                   , 'backup'   : False}
            period = Period()
            period_adapter = PeriodHttpAdapter(period)
            period_adapter.init_from_post(fdata, 'UTC')

            # link the period and elective
            period.elective = self.elective1
            period.save()

        # make the second elective
        self.elective2 = Elective(session = self.sesshun, complete = False)
        self.elective2.save()

        # make periods for it (09:30-13:30)
        dates = ['2009-04-08', '2009-04-14', '2009-04-20']
        for date in dates:
            fdata = {'session'  : self.sesshun.id
                   , 'date'     : date
                   , 'time'     : '09:30'
                   , 'duration' : 4.5
                   , 'backup'   : False}
            period = Period()
            period_adapter = PeriodHttpAdapter(period)
            period_adapter.init_from_post(fdata, 'UTC')

            # link the period and elective
            period.elective = self.elective2
            period.save()

        # setup a receiver schedule
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

        # so:
        #  schedulable periods on            : 4/7, 4/8, 4/9, 4/14
        #  schedulable periods not blacked on:      4/8, 4/9
        #  schedulable periods     blacked on: 4/7,           4/14

    def testGetBlackedOutElectivePeriods(self):
        wa = ElectiveAlerts()
        periods = self.sesshun.period_set.all()

        now   = datetime(2009, 4, 7, 12)
        stats = wa.getBlackedOutElectivePeriods(now, self.sesshun.elective_set.all())
        exp = [(self.elective1, [periods[2]])
             , (self.elective2, [periods[5]])]
        self.assertEquals(exp, stats)

        now   = datetime(2009, 4, 8, 12)
        stats = wa.getBlackedOutElectivePeriods(now, self.sesshun.elective_set.all())
        exp = [(self.elective2, [periods[5]])]
        self.assertEquals(exp, stats)

    def testFindBlackoutAlerts(self):
        wa = ElectiveAlerts()
        now   = datetime(2009, 3, 24, 0)
        periods = self.sesshun.period_set.all()

        # stage 1 check on 3/24 reveals blacked-out period on 4/14
        alerts = wa.findBlackoutAlerts(1, now, self.sesshun.elective_set.all())
        exp = [(self.elective2, [periods[5]], 1)]
        self.assertEquals(exp, alerts)

        # stage 2 check on 3/24 reveals blacked-out period on 4/7
        alerts = wa.findBlackoutAlerts(2, now, self.sesshun.elective_set.all())
        exp = [(self.elective1, [periods[2]], 2)]
        self.assertEquals(exp, alerts)

