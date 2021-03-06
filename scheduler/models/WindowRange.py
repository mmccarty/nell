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

from django.db  import models
from datetime   import datetime, timedelta

from nell.utilities         import TimeAgent, SLATimeAgent, AnalogSet
from Window                 import Window

class WindowRange(models.Model):
    window     = models.ForeignKey(Window) 
    start_date = models.DateField(help_text = "yyyy-mm-dd hh:mm:ss")
    duration   = models.IntegerField(help_text = "Days")

    def __unicode__(self):
        return "WindowRange (%d) for Win (%d)" % \
            (self.id
           , self.window.id)

    def __str__(self):
        name = self.window.session.name if (self.window is not None and self.window.session is not None) else "None"
        return "WindowRange for %s, from %s for %d days" % \
            (name, self.start_date, self.duration)

    def last_date(self):
        "Ex: start = 1/10, duration = 2 days, last_date = 1/11"
        return self.start_date + timedelta(days = self.duration - 1)

    def inWindow(self, date):
        return (self.start_date <= date) and (date <= self.last_date())

    def inWindowDT(self, dt):
        "Compares datetimes"
        return self.start_datetime() <= dt and dt < self.end_datetime()

    def start_datetime(self):
        return TimeAgent.date2datetime(self.start_date)

    def end_datetime(self):
        "We want this to go up to the end of the last_date day"
        return TimeAgent.date2datetime(self.start_date) + timedelta(days = self.duration)

    def isInWindow(self, period):
        "Does the given period overlap at all in window"
        return AnalogSet.overlaps((self.start_datetime(), self.end_datetime())
                                , (period.start, period.end()))

        return False

    def lstInRange(self, lst, buffer = 0):
        "Does a given LST fit in this range?"

        # Note, WTF: this really only applies to ranges of 1 day,
        # since any lst (0-24 hrs) will fit in a range of >2 
        # days, but wtf.

        assert buffer >= 0.0 and buffer <= 24.0

        # Convert the relative lst to the absolute UTC time
        # for the first day of the window range, and the last
        lstUTCStart = SLATimeAgent.RelativeLST2AbsoluteTime(lst, now = self.start_datetime())
        lstUTCEnd = SLATimeAgent.RelativeLST2AbsoluteTime(lst
            , now = self.start_datetime() + timedelta(days = self.duration - 1) )

        # include the buffer for the range ends
        utcStart = self.start_datetime() + timedelta(minutes = buffer*60.0)
        utcEnd   = self.end_datetime()   - timedelta(minutes = buffer*60.0)

        #print "comparing UTCs at start: ", lstUTCStart, utcStart 
        #print "comparing UTCs at end: ", lstUTCEnd, utcEnd 

        return (lstUTCStart >= utcStart) and (lstUTCEnd <= utcEnd)
    
  
    class Meta:
        db_table  = "window_ranges"
        app_label = "scheduler"
      
