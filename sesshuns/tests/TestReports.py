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

from datetime                import datetime
from scheduler.models        import *
from test_utils              import NellTestCase
from tools.reports  import *
from scheduler.tests.utils                   import create_sesshun
import sys

from tools.reports.CompletionReport  import GenerateReport as completionReport
from tools.reports.BlackoutReport  import GenerateBlackoutReport
from tools.reports.DBHealthReport  import GenerateReport as dbHealth
#from tools.reports.NFSReport  import GenerateReport as nsfReport
from tools.reports.ProjectReport  import GenerateProjectReport
from tools.reports.ProjTimeAcctReport  import GenerateProjectTimeAccountingReport
from tools.reports.ScheduleReport import ScheduleReport
from tools.reports.SessionReport  import GenerateReport as sessionReport
from tools.reports.StartEndReport  import get_projects_between_start_end 
from tools.reports.WeeklyReport  import GenerateReport as weeklyReport
from tools.reports.WindowsReport  import WindowsReport 

# This breaks the one unit test class per class pattern, since this 
# is a single test class for all the reports, but wtf.

class TestReports(NellTestCase):

    def setUp(self):
        super(TestReports, self).setUp()

        # setup some data to report on
        
        # period dates
        dt1 = datetime(2010, 1, 1, 0)
        dt2 = datetime(2010, 1, 1, 2)
        dt3 = datetime(2010, 1, 1, 5)
        dt4 = datetime(2010, 1, 1, 6)
        dt5 = datetime(2010, 1, 1, 8)

        scheduled = Period_State.get_state("S")

        # an L band sesssion
        self.s1 = create_sesshun()
        self.s1.name = "One"
        self.s1.save()

        rg = Receiver_Group(session = self.s1)
        L = (Receiver.get_rcvr('L'))
        rg.save()
        rg.receivers.add(L)
        rg.save()

        # two periods for this session
        dur = 2.0
        pa = Period_Accounting(scheduled = dur)
        pa.save()
        p = Period(session = self.s1
                 , start = dt1
                 , duration = dur
                 , state = scheduled
                 , accounting = pa
                  )
        p.save()
        pg = Period_Receiver(period = p, receiver = L)
        pg.save()

        dur = 1.0
        pa = Period_Accounting(scheduled = dur, lost_time_rfi = 0.5)
        pa.save()
        p = Period(session = self.s1
                 , start = dt3
                 , duration = dur
                 , state = scheduled
                 , accounting = pa
                  )
        p.save()
        pg = Period_Receiver(period = p, receiver = L)
        pg.save()

        # an X band session
        self.s2 = create_sesshun()
        self.s2.name = "Two"
        self.s2.save()

        rg = Receiver_Group(session = self.s2)
        rg.save()
        X = Receiver.get_rcvr('X')
        rg.receivers.add(X)
        rg.save()

        # two periods for this session
        dur = 3.0
        pa = Period_Accounting(scheduled = dur)
        pa.save()
        p = Period(session = self.s2
                 , start = dt2
                 , duration = dur
                 , state = scheduled
                 , accounting = pa
                  )
        p.save()
        pg = Period_Receiver(period = p, receiver = X)
        pg.save()

        dur = 2.0
        pa = Period_Accounting(scheduled = dur, not_billable = 0.5)
        pa.save()
        p = Period(session = self.s2
                 , start = dt4
                 , duration = dur
                 , state = scheduled
                 , accounting = pa
                  )
        p.save()
        pg = Period_Receiver(period = p, receiver = X)
        pg.save()

    def test_rcvrTimeAccntReport(self):

        r = RcvrTimeAccntReport()
        r.quietReport = True # shhh!

        start = datetime(2010, 1, 1)
        end = datetime(2010, 1, 2)
        r.report(start, end)
        ls = "".join(r.reportLines)
        
        l = "NS      0.00      0.00      0.00      0.00      0.00      0.00"
        self.assertTrue(l in ls)

        l = "L      3.00      2.50      0.00      2.50      0.50      0.00"
        self.assertTrue(l in ls)
        l = "X      5.00      4.50      0.50      5.00      0.00      0.00"
        self.assertTrue(l in ls)

    def test_windowsReport(self):

        wr = WindowsReport(filename = "WindowsReport.txt")
        wr.quietReport = True
        wr.report()

    def test_weeklyReport(self):

        wr = weeklyReport(datetime(2010, 1, 1))

    def test_startEndReport(self):
        # make it quiet
        orig = sys.stdout
        sys.stdout = open("test_completionReport.txt", 'w')

        start = datetime(2010, 1, 1)
        end   = datetime(2010, 1, 7)
        results = get_projects_between_start_end(start, end)

        sys.stdout = orig

    def test_sessionReport(self):

        sr = sessionReport(datetime.today())

    def test_blackoutReport(self):

        br = GenerateBlackoutReport()

    def test_completionReport(self):

        # make it quiet
        orig = sys.stdout
        sys.stdout = open("test_completionReport.txt", 'w')
        cr = completionReport(datetime.today())
        sys.stdout = orig

    def test_dbHealthReport(self):

        db = dbHealth()
 
    def test_projectReport(self):

        pr = GenerateProjectReport()

    def test_projTimeAcctReport(self):

        # make it quiet
        orig = sys.stdout
        sys.stdout = open("test_projTimeAcctReport.txt", 'w')

        p = Project.objects.all()[0]
        tr = GenerateProjectTimeAccountingReport(p.pcode)

        sys.stdout = orig
 
    def test_scheduleReport(self):

        sr = ScheduleReport()
        sr.quietReport = True
        start = datetime(2010, 1, 1)
        days = 30
        sr.report(start, days)
        ls = "".join(sr.reportLines)

        result = """Start (ET)   |      UT      |  LST  |  (hr) | T | S |    PI     | Rx        | Session
--------------------------------------------------------------------------------------
Dec 31 19:00 | Jan 01 00:00 | 01:20 |  2.00 | O | S | Unknown   | L         | One
Dec 31 21:00 | Jan 01 02:00 | 03:21 |  3.00 | O | S | Unknown   | X         | Two
Jan 01 00:00 | Jan 01 05:00 | 06:21 |  1.00 | O | S | Unknown   | L         | One
Jan 01 01:00 | Jan 01 06:00 | 07:21 |  2.00 | O | S | Unknown   | X         | Two"""
        self.assertTrue(result in ls)

    def xtest_nsfReport(self):
        
        argv = ["program", "1", "2010"]
        quarters = {
            1: [10, 11, 12]
          , 2: [1, 2, 3]
          , 3: [4, 5, 6]
          , 4: [7, 8, 9]
                   }

        quarter     = int(argv[1])
        fiscal_year = int(argv[2])
    
        months = quarters[quarter]
        year   = fiscal_year if quarter != 1 else fiscal_year - 1
    
        #nsfReport('Q%dFY%d' % (quarter, fiscal_year)
        #             , [datetime(year, m, 1) for m in months])
