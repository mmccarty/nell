from django.db  import models
from datetime   import datetime, timedelta

from nell.utilities import TimeAgent

from common import *
from Window import Window

class WindowRange(models.Model):
    window     = models.ForeignKey(Window, null = True)
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

    def end(self):
        return self.last_date()

    def last_date(self):
        "Ex: start = 1/10, duration = 2 days, last_date = 1/11"
        return self.start_date + timedelta(days = self.duration - 1)

    def inWindow(self, date):
        return (self.start_date <= date) and (date <= self.last_date())

    def start_datetime(self):
        return TimeAgent.date2datetime(self.start_date)

    def end_datetime(self):
        "We want this to go up to the last second of the last_date"
        dt = TimeAgent.date2datetime(self.last_date())
        return dt.replace(hour = 23, minute = 59, second = 59)

    def isInWindow(self, period):
        "Does the given period overlap at all in window"

        # need to compare date vs. datetime objs
        #winStart = datetime(self.start_date.year
        # with what we have in memory
        #                  , self.start_date.month
        #                  , self.start_date.day)
        #winEnd = winStart + timedelta(days = self.duration)                  
        return overlaps((self.start_datetime(), self.end_datetime())
                      , (period.start, period.end()))

        return False

    def eventjson(self, id):
        #end = self.start_date + timedelta(days = self.duration)

        return {
                "id"   :     id
              , "title":     "".join(["Window ", self.window.session.name])
              , "start":     self.start_date.isoformat()
              , "end"  :     self.end().isoformat()
              , "className": 'window'
        }

    class Meta:
        db_table  = "window_ranges"
        app_label = "sesshuns"
      
