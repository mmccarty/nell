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

from datetime import datetime, date, timedelta

from scheduler.models import Semester as DSSSemester
from scheduler.models import Project
from scheduler.models import Period as DSSPeriod

from utilities import AnalogSet
from utilities import TimeAgent
from utilities import SLATimeAgent as sla

from pht.tools.Sun import Sun

class Times(object):

    """
    This class simply makes the management of the different
    quantities we'll be calculating a lot easier.
    """
    
    def __init__(self
        , total = 0.0
        , gc = 0.0
        , lowFreq = 0.0
        , hiFreq1 = 0.0
        , hiFreq2 = 0.0
        ):

        self.total = total
        self.gc = gc
        self.lowFreq = lowFreq 
        self.hiFreq1 = hiFreq1
        self.hiFreq2 = hiFreq2

    def __str__(self):

        return "Total: %5.2f, GC: %5.2f, LF: %5.2f, HF1: %5.2f, HF2: %5.2f" % \
            (self.total, self.gc, self.lowFreq, self.hiFreq1, self.hiFreq2)

    def __repr__(self):
        return self.__str__()

    def __add__(self, other):
        "Override addition to add all the fields"
        return Times( \
            total = self.total + other.total
          , gc = self.gc + other.gc
          , lowFreq = self.lowFreq + other.lowFreq
          , hiFreq1 = self.hiFreq1 + other.hiFreq1
          , hiFreq2 = self.hiFreq2 + other.hiFreq2
        )

    def __sub__(self, other):
        "Override addition to add all the fields"
        return Times( \
            total = self.total - other.total
          , gc = self.gc - other.gc
          , lowFreq = self.lowFreq - other.lowFreq
          , hiFreq1 = self.hiFreq1 - other.hiFreq1
          , hiFreq2 = self.hiFreq2 - other.hiFreq2
        )

    def __eq__(self, other):
        "Override equality to compare all the fields"
        return self.eq(self.total, other.total) \
            and self.eq(self.gc, other.gc) \
            and self.eq(self.lowFreq, other.lowFreq) \
            and self.eq(self.hiFreq1, other.hiFreq1) \
            and self.eq(self.hiFreq2, other.hiFreq2)

    def eq(self, v1, v2):
        "Are these floats almost equal?"
        eps = 1e10-3
        return abs(v1 - v2) < eps

class SemesterTimeAccounting(object):

    """
    This class is responsible for determining many complicated
    time accounting quantities.
    For each quantity, there are two types: total, and those covered
    by the Galactic Center.
    """

    def __init__(self, semester):


        self.sun = Sun()

        self.semester = DSSSemester.objects.get(semester = semester)

        # Galactic Center goes from 15 to 20 hours [,)
        self.gcHrs = (15, 21) 

        # initialize all the buckets we'll be calculating
        self.totalAvailableHrs = (None, None)
        self.maintHrs = None
        self.shutdownHrs = None
        self.testHrs = None

    def checkTimes(self):

        preAssigned = self.maintHrs + self.shutdownHrs + self.testHrs
        avail = preAssigned  + self.astronomyAvailableHrs
        assert avail.total == self.totalAvailableHrs[0]

        
    def calculateTimeAccounting(self):

        # how many hours in this semester?
        days = self.getSemesterDays(self.semester)
        totalHrs = days * 24
        totalGCHrs = self.getGCHrs(totalHrs)
        self.totalAvailableHrs = (totalHrs, totalGCHrs)  

        # how much has been pre-assigned for this semester?
        # first, find the periods
        self.maintPeriods = self.getMaintenancePeriods()
        #self.testingPeriods = self.getTestingPeriods()
        self.shutdownPeriods = self.getShutdownPeriods()
        self.testSessions = self.getTestSessions()

        # now calculate their hours
        self.maintHrs = self.getHours(self.maintPeriods)
        self.shutdownHrs = self.getHours(self.shutdownPeriods)
        self.testHrs = self.getSessionHours(self.testSessions)

        # so, how much does that leave left for real astronomy?
        self.astronomyAvailableHrs = None
        # add up maintHrs, shutdownHrs, testHrs, total and GC, 
        # then subtract those from the totalAvailableHrs
        preAssigned = self.maintHrs + self.shutdownHrs + self.testHrs
        total = self.totalAvailableHrs[0]
        avail = Times(total = total 
                    , gc = self.totalAvailableHrs[1]
                    , lowFreq = total * 0.50
                    , hiFreq1 = total * 0.25
                    , hiFreq2 = total * 0.25
                     )
        self.astronomyAvailableHrs = avail - preAssigned             


        # in order to calculate these
        self.lowFreqAvailableHrs = (None, None) # TBF
        self.highFreq1AvailableHrs = (None, None) # TBF
        self.highFreq2AvailableHrs = (None, None) # TBF

    def getSemesterDays(self, semester = None):    
        "How many days in the given semester?"
        if semester is None:
            s = self.semester
        else:    
            s = DSSSemester.objects.get(semester = semester)
        return (s.end() - s.start()).days

    def getGCHrs(self, hrs):
        """
        Given a uniformly distributed number of hours, how many would
        fall within the Galactic Center range?
        """
        gcHrs = (self.gcHrs[1] - self.gcHrs[0]) 
        return hrs * (gcHrs/24.)

    def getMaintenancePeriods(self):
        "What maintenance periods have been scheduled for this semester?"
        return self.getProjectPeriods('Maintenance')

    def getTestSessions(self):
        # TBF
        return []
    
    def getShutdownPeriods(self):
        "What shutdown periods have been scheduled for this semester?"
        return self.getProjectPeriods('Shutdown')

    def getProjectPeriods(self, pcode):    
        ps = DSSPeriod.objects.filter( \
            session__project__pcode = pcode
          , start__gt = self.semester.start()
          , start__lt = self.semester.end()).exclude( \
              state__name = 'Deleted').order_by('start')    
        return ps 

    def getHours(self, periods):

        allHrs = Times()            
        for p in periods:
            hrs = self.getPeriodHours(p)
            # update the totals
            allHrs += hrs

        return allHrs        
            
    def getPeriodHours(self, period):
        """
        Determines how much of ther various types of time these periods 
        add up.  These types include:
           * how much lies in the galactic center?
           * how much gets billed to each frequency bin?
        Uses their duration, since we'll be looking at mostly pending
        periods, who won't have any time billed yet.
        """

        dur = period.duration
        start = period.start
        end = period.end()

        dayHrs, nightHrs = self.getHrsInDayTime(start, end)
        gcHrs, nonGCHrs  = self.getHrsInGC(start, end)

        # day time periods don't bill against high freq 2
        lowFreqHrs = .50 * dayHrs
        hiFreq1Hrs = .50 * dayHrs
        hiFreq2Hrs = 0.0 
        # night time periods DO!
        lowFreqHrs += .50 * nightHrs
        hiFreq1Hrs += .25 * nightHrs
        hiFreq2Hrs += .25 * nightHrs

        return Times(total = dur
                  , gc = gcHrs
                  , lowFreq= lowFreqHrs
                  , hiFreq1= hiFreq1Hrs
                  , hiFreq2= hiFreq2Hrs
                  )       

    def getHrsInDayTime(self, start, end):
        "Split up given time range by PTCS day and night time hours."
        dur = TimeAgent.dtDiffHrs(start, end)
        startDate = date(start.year, start.month, start.day)
        #rise, set = self.sun.getRiseSet(date1)
        # cast a wide net: compute the rise and set times for any days
        # that might be covered by the given time range
        days = (end - start).days + 2
        dayTimes = []
        for day in range(days):
            dt = startDate + timedelta(days = day)
            dayTimes.append(self.sun.getPTCSRiseSet(dt))
        # where does our given time range intersect with day time?    
        ints = AnalogSet.intersects([dayTimes, [(start, end)]])
        if len(ints) > 0:
            # some day time
            day = 0.0
            for intersection in ints:
                td = intersection[1] - intersection[0]
                day += TimeAgent.timedelta2frachours(td)
            # the rest must be night time    
            night = abs(dur - day) 
        else:
            # our range is all night time.
            day = 0.0
            night = dur 
        return (day, night)

    def fltEqual(self, flt1, flt2):
        eps = 1e-3
        return abs(flt1 - flt2) < eps

    def getHrsInGC(self, start, end):
        "Split up given time range by Galactic Center overlap."
        dur = TimeAgent.dtDiffHrs(start, end)
        # convert local time range to LST range
        lstStart = sla.Absolute2RelativeLST(start)
        lstEnd = sla.Absolute2RelativeLST(end)
        # be simplistic about the overalp
        if lstEnd < lstStart:
            lstEnd += 24.0
            
        # what's the overlap with the Galactice Center?
        if AnalogSet.overlaps((lstStart, lstEnd), self.gcHrs):
            overlap = AnalogSet.intersect((lstStart, lstEnd), self.gcHrs)
            # if our range is entirely in GC, avoid calculations
            if self.fltEqual(overlap[0], lstStart) \
                and self.fltEqual(overlap[1], lstEnd):
                gcHrs = dur
                nonGcHrs = 0
            else:    
               # otherwise we need to convert back to hours - 
               # one way to do this is via fractions
               frac = (overlap[1] - overlap[0]) / (lstEnd - lstStart)
               gcHrs = dur * frac
               nonGcHrs = (1.0 - frac) * dur
        else:
            gcHrs = 0
            nonGcHrs = dur
        return (gcHrs, nonGcHrs)

    def getSessionHours(self, session):

        freq2key = {'LF' : 'lowFreq'
                  , 'HF1' : 'hiFreq1'
                  , 'HF2' : 'hiFreq2'
                   }
        allHrs = Times()          
        for s in session:
            timeType = freq2key[s.determineFreqCategory()]
            # TBF
            #allHrs.__settimeType] += s.allotment.allocated_time
            allHrs.total  += s.allotment.allocated_time
            allHrs.gc     += self.getGCHoursFromSession(s)

        return allHrs    
            
    def getGCHoursFromSession(self, session):
        # TBF: use max/min LST as compared to the Galctic Center
        return 0.0

            

    
        
