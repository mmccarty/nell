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

from datetime import datetime, timedelta

from test_utils              import NellTestCase
from scheduler.models         import *
from utils                   import create_sesshun
from nell.utilities              import TimeAccounting

class TestTimeAccounting(NellTestCase):

    def setUp(self):
        super(TestTimeAccounting, self).setUp()

        # this project has no allotments!
        self.project = Project.objects.order_by('pcode').all()[0]

        # setup some periods
        self.start = datetime(2000, 1, 1, 0)
        self.end   = self.start + timedelta(hours = 12)
        times = [(datetime(2000, 1, 1, 0), 5.0, "one")
               , (datetime(2000, 1, 1, 5), 3.0, "two")
               , (datetime(2000, 1, 1, 8), 4.0, "three")
               ]
        self.ps = []
        state = Period_State.objects.get(abbreviation = 'P')
        for start, dur, name in times:
            # each session has grade 4, time = 3 
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
        self.assertEqual(-12., dct['remaining'])
        self.assertEqual(0, len(dct['times']))
        # construct a new dict to test against
        sess = {}
        for sdct in dct['sessions']:
            sess[sdct['name']] = {'remaining' : sdct['remaining']
                                , 'grade' : sdct['grade']
                                , 'total_time' : sdct['total_time']
                                #, 'periods' : sdct['periods']
                                }
        exp = {'one' : {'grade' : 4.0
                      , 'total_time' : 3.0
                      , 'remaining' : -2.0 # 3 - 5 
                        }
             , 'two' : {'grade' : 4.0
                      , 'total_time' : 3.0
                      , 'remaining' : 0.0 # 3 - 3
                       }
             , 'three':{'grade' : 4.0
                     , 'total_time' : 3.0
                     , 'remaining' : -1.0 # 3 - 4
                       }
              }
        for key, values in sess.items():
            self.assertEqual(exp[key], values)

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

