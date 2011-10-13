# Copyright (C) 2008 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 675 Mass Ave Cambridge, MA 02139, USA.
#
# Correspondence concerning GBT software should be addressed as follows:
#     GBT Operations
#     National Radio Astronomy Observatory
#     P. O. Box 2
#     Green Bank, WV 24944-0002 USA

if __name__ == "__main__":
    import sys
    sys.path[1:1] = [".."]

from utilities.SLATimeAgent   import *
from utilities.TimeAgent      import *
from datetime       import datetime, time, timedelta
import os
import unittest

class TestTimeAgent(unittest.TestCase):

    def test_adjustDateTimeTz(self):
        dt =  datetime(2010,  6,  1,  12,  0,  0)        
        r = adjustDateTimeTz("UTC", dt)
        self.assertEquals("2010-06-01 12:00:00+00:00", "%s" % r)
        r = adjustDateTimeTz("EST", dt)
        self.assertEquals("2010-06-01 07:00:00-05:00", "%s" % r)
        r = adjustDateTimeTz("PST8PDT", dt)
        self.assertEquals("2010-06-01 05:00:00-07:00", "%s" % r)
        # see what the UTC flag does
        r = adjustDateTimeTz("UTC", dt, to_utc = True)
        self.assertEquals("2010-06-01 12:00:00+00:00", "%s" % r)
        r = adjustDateTimeTz("EST", dt, to_utc = True)
        self.assertEquals("2010-06-01 17:00:00+00:00", "%s" % r)

    def test_dt2tlst(self):
        self.assertEquals(time(6, 46, 3)
                        , dt2tlst(datetime(2009, 9, 30, 11, 30)))

        self.assertEquals(time(7, 6, 6)
                        , dt2tlst(datetime(2009, 9, 30, 11, 50)))

    def test_dt2semester(self):
        dt10a1 = datetime(2010,  5, 31, 23, 59, 59)
        dt10b1 = datetime(2010,  6,  1,  0,  0,  0)
        dt10b2 = datetime(2010,  9, 30, 23, 59, 59)
        dt10c1 = datetime(2010, 10,  1,  0,  0,  0)
        dt10c2 = datetime(2010, 12, 15, 12,  0,  0)
        dt10c3 = datetime(2011,  1, 31, 23, 59, 59)
        dt11a1 = datetime(2011,  2,  1,  0,  0,  0)
        dt11a2 = datetime(2011,  6, 30, 23, 59, 59)
        dt11b1 = datetime(2011,  7,  1,  0,  0,  0)
        dt11b2 = datetime(2011, 12, 15, 12,  0,  0)
        dt11b3 = datetime(2012,  1, 31, 23, 59, 59)
        dt12a1 = datetime(2012,  2,  1,  0,  0,  0)
        dt12a2 = datetime(2012,  3,  1,  0,  0,  0)
        dt12a3 = datetime(2012,  7, 31, 23, 59, 59)
        dt12b1 = datetime(2012,  8,  1,  0,  0,  0)
        dt12b2 = datetime(2012, 12, 15, 12,  0,  0)
        dt12b3 = datetime(2013,  1, 31, 23, 59, 59)
        dt13a1 = datetime(2013,  2,  1,  0,  0,  0)

        self.assertEqual('10A', dt2semester(dt10a1))
        self.assertEqual('10B', dt2semester(dt10b1))
        self.assertEqual('10B', dt2semester(dt10b2))
        self.assertEqual('10C', dt2semester(dt10c1))
        self.assertEqual('10C', dt2semester(dt10c2))
        self.assertEqual('10C', dt2semester(dt10c3))
        self.assertEqual('11A', dt2semester(dt11a1))
        self.assertEqual('11A', dt2semester(dt11a2))
        self.assertEqual('11B', dt2semester(dt11b1))
        self.assertEqual('11B', dt2semester(dt11b2))
        self.assertEqual('11B', dt2semester(dt11b3))
        self.assertEqual('12A', dt2semester(dt12a1))
        self.assertEqual('12A', dt2semester(dt12a2))
        self.assertEqual('12A', dt2semester(dt12a3))
        self.assertEqual('12B', dt2semester(dt12b1))
        self.assertEqual('12B', dt2semester(dt12b2))
        self.assertEqual('12B', dt2semester(dt12b3))
        self.assertEqual('13A', dt2semester(dt13a1))

    def test_range_to_days(self):

        firstDay = datetime(2011, 8, 1)
        start = datetime(2011, 8, 1, 12) 
        end   = datetime(2011, 8, 5, 6)
        r = [(start, end)]
        days = range_to_days(r)
        # 8/1 and 8/5 are NOT completely covered by these datetimes,
        # so they AREN'T in the list
        exp = [firstDay + timedelta(days = i) for i in range(1,4)]
        self.assertEquals(exp, days)

        start = datetime(2011, 8, 1) 
        end   = datetime(2011, 8, 2)
        r = [(start, end)]
        days = range_to_days(r)
        exp = [firstDay]
        self.assertEquals(exp, days)

        start = datetime(2011, 8, 1) 
        end   = datetime(2011, 8, 5)
        r = [(start, end)]
        days = range_to_days(r)
        exp = [firstDay + timedelta(days = i) for i in range(0,4)]
        self.assertEquals(exp, days)

        start = datetime(2011, 8, 1, 6) 
        end   = datetime(2011, 8, 5)
        r = [(start, end)]
        days = range_to_days(r)
        exp = [firstDay + timedelta(days = i) for i in range(1,4)]
        self.assertEquals(exp, days)

        start = datetime(2011, 8, 1) 
        end   = datetime(2011, 8, 5, 6)
        r = [(start, end)]
        days = range_to_days(r)
        exp = [firstDay + timedelta(days = i) for i in range(0,4)]
        self.assertEquals(exp, days)


if __name__ == "__main__":
    unittest.main()
