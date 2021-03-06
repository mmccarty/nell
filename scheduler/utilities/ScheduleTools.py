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

from datetime                   import datetime, timedelta
from scheduler.models           import *
from scheduler.models.utils     import *
from nell.utilities             import TimeAgent

class ScheduleTools(object):

    def __init__(self):
        #self.score = Score()
        
        # Scheduling Range == 0:00 (TIMEZONE) of the first day specified to
        # 8 AM EST of the last day specified
        #self.schedulingStart = 8 # EST
        self.schedulingEnd   = 8 # EST

    def getUTCHour(self, dt, estHour):
        dtEst = datetime(dt.year, dt.month, dt.day, estHour)
        dtUtc = TimeAgent.est2utc(dtEst)
        return dtUtc.hour
        
    def getSchedulingRange(self, firstDay, timezone, days):
        """
        Converts given time range (start dt, days) to 'scheduling range' 
        (start dt, minutes)
        """

        startHour = 0 if timezone == 'UTC' else self.getUTCHour(firstDay, 0)
        start = datetime(firstDay.year
                       , firstDay.month
                       , firstDay.day
                       , startHour
                        )

        lastDay = firstDay + timedelta(days = days)

        end   = datetime(lastDay.year
                       , lastDay.month
                       , lastDay.day
                       , self.getUTCHour(lastDay, self.schedulingEnd)
                        )

        duration = TimeAgent.dtDiffMins(end, start)

        return (start, duration)

    def changeSchedule(self, start, duration, sesshun, reason, desc):
        """
        Change the schedule, and take care of all the time accounting.
        This is meant for use in such cases as examplified in Memo 11.2.
        Right now, this only handles substituting one session for one
        or more sessions, where the time taken is accounted to one of these
        Reasons:
            time to other session due to weather
            time to other session due to rfi
            time to other session due to other reason
        and the time given to the new session is marked as short notice.
        Note that the times are not *assigned*, but instead times and descs.
        are incremented, so as not to overwrite previous changes.
        """

        # get rid of this once develompent has stablized.
        debug = False

        if debug:
            print "changeSchedule: "
            print start, duration, sesshun

        # tag the description
        nowStr = datetime.now().strftime("%Y-%m-%d %H:%M")    
        descHead = " [Insert Period (%s) " % nowStr 
        # dictionary of who gave and who got, where:
        # descDct[gave/got] = [(desc. of original period, time, period id)]
        descDct = dict(gave_time = [], got_time = [])

        # what periods are we affecting?
        duration_mins = duration * 60.0
        ps = Period.get_periods(start, duration_mins)
        if debug:
            print "len(ps): ", len(ps)
            for p in ps:
                print p 

        scheduledPeriods = [p for p in ps if p.state.abbreviation == 'S']
        if len(scheduledPeriods) != len(ps):
            msg = "All affected Periods must be in the Scheduled State"
            return (False, msg)

        # first, adjust each of the affected periods - including time accnting
        end = start + timedelta(hours = duration)
        for p in ps:
            need_scoring = False
            if debug:
                print "changing period: ", p
                print "comparing period: ", p.start, p.end()
                print "w/:               ", start, end 
            if p.start >= start and p.end() <= end:
                if debug:
                    print "delete period!"
                # this entire period is being replaced
                descDct["gave_time"].append((p.__str__(), p.duration, p.id))
                other_sess_time = p.duration
                p.delete() # the Deleted State!
            elif p.start >= start and p.end() > end:
                if debug:
                    print "start period later"
                # we're chopping off the beginning of this period
                new_duration = TimeAgent.timedelta2frachours(p.end() - end)
                other_sess_time = p.duration - new_duration
                descDct["gave_time"].append((p.__str__(),other_sess_time, p.id))
                p.duration = new_duration
                p.start = end
                need_scoring = True
            elif p.start < start and p.end() > end:
                if debug:
                    print "bi-secting period"
                # we're chopping out the middle of a period: we fix this
                # by adjusting the period, then creating a new one
                descDct["gave_time"].append((p.__str__(), duration, p.id))
                original_duration = p.duration
                original_end      = p.end()
                p.duration = TimeAgent.timedelta2frachours(start - p.start)
                # the new one
                new_dur = TimeAgent.timedelta2frachours(original_end - end)
                accounting = Period_Accounting(scheduled = new_dur
                                             , short_notice = new_dur
                                             , description = "" #description
                                               )
                accounting.save()                             
                pending = Period_State.objects.get(abbreviation = 'P')
                period_2cd_half = Period.create(session  = p.session
                                       , start    = end
                                       , duration = new_dur
                                       , state    = pending
                                       , score    = 0.0
                                       , forecast = end
                                       , accounting = accounting 
                                         )
                init_rcvrs_from_session(period_2cd_half.session, period_2cd_half)
                self.reinitScore(period_2cd_half)
                period_2cd_half.save()                         
                # the original period is really giving up time to the 
                # bi-secting new period, and the new second half!
                other_sess_time = duration + new_dur
                need_scoring = True
            elif p.start < start and p.end() > start:
                if debug:
                    print "shorten period"
                # we're chopping off the end of this period
                new_duration = TimeAgent.timedelta2frachours(start - p.start)
                other_sess_time = p.duration - new_duration
                descDct["gave_time"].append((p.__str__(),other_sess_time, p.id))
                p.duration = new_duration
                need_scoring = True
                         
            else:
                raise "not covered"
            # now change this periods time accounting
            if p is not None:
                if debug:
                    print "changes: ", p
                # increment values: don't overwrite them!
                value = p.accounting.get_time(reason)
                p.accounting.set_changed_time(reason, value + other_sess_time)
                p.accounting.save()
                if need_scoring:
                    self.reinitScore(p)
                p.save()

        # finally, anything to replace it with?
        if sesshun is not None:
            # create a period for this
            pa = Period_Accounting(scheduled    = duration
                                 , short_notice = duration
                                 , description  = "") #description)
            pa.save()   
            scheduled = Period_State.objects.get(abbreviation = 'S')
            p = Period.create(session    = sesshun
                            , start      = start
                            , duration   = duration
                            , score      = 0.0
                            , state      = scheduled
                            , forecast   = start
                            , accounting = pa)
            init_rcvrs_from_session(p.session, p)
            self.reinitScore(p)
            p.save()    
            descDct["got_time"].append((p.__str__(),p.duration, p.id))

        # in all cases, give the description of entire event:
        self.assignDescriptions(descDct, descHead, desc)

        return (True, None)

    def assignDescriptions(self, descDct, descHead, desc):
        """
        Given a dictionary of which periods gave how much time to who,
        when the transfer occured, and the details provided by the user,
        create the verbal description of this, and apply it to all concerned
        periods.
        """

        # create the description
        description = ""
        if len(descDct["got_time"]) > 0:
            description = descHead + "Period %s got %5.2f hours from: " %\
                (descDct["got_time"][0][0]
               , descDct["got_time"][0][1])
        else:
            description = descHead + "No Period got time from: " 
        for p, hrs, pid in descDct["gave_time"]:
            description += "%s (%5.2f hours) " % (p, hrs)
        description += "] " + desc 

        # now assign the description to all affected periods
        for who in ["got_time", "gave_time"]:
            for pname, hrs, pid in descDct[who]:
                p = Period.objects.get(id = pid)
                old = p.accounting.description \
                    if p.accounting.description is not None else ""
                p.accounting.description = old + description
                p.accounting.save()

    def shiftPeriodBoundaries(self
                            , period
                            , start_boundary
                            , time
                            , neighbor
                            , reason
                            , desc):
        """
        Shifts the boundary between a given period and it's neighbors:
           * period_id - the period obj. whose boundary we first adjust
           * start_boundary - boolean, true for start, false for end
           * time - new time for that boundary
           * neighbor - period affected (can't be None)
           * reason - other_session_weather, *_rfi, or *_other
           * desc - the description to put into time accounting
        After periods are adjusted, time accounting is adjusted appropriately
        """
       
        # if there isn't a neighbor, then this change should be done by hand
        if neighbor is None:
            return (False, "Cannot shift period boundary if there is a neighboring gap in the schedule.")

        if period.state.abbreviation != 'S' or \
           neighbor.state.abbreviation != 'S':
            return (False, "Affected Periods should be in the Scheduled State")   
        # get the time range affected
        original_time = period.start if start_boundary else period.end()
        diff_hrs = TimeAgent.dtDiffHrs(original_time, time) #self.get_time_diff_hours(original_time, time)

        # check for the no-op
        if original_time == time:
            return (False, "Time given did not change Periods duration")

        # create the tag used for all descriptions in time accounting
        nowStr = datetime.now().strftime("%Y-%m-%d %H:%M")    
        descHead = " [Shift Period Bnd. (%s) " % nowStr 
        # dictionary of who gave and who got, where:
        # descDct[gave/got] = [(desc. of original period, time, period id)]
        descDct = {}

        # figure out the stuff that depends on which boundary we're moving
        if start_boundary:
            if time >= period.end():
                return (False, "Cannot start this period after it ends.")
            period_growing = True if time < original_time else False
        else:
            if time <= period.start:
                return (False, "Cannot shrink period past its start time.")
            period_growing = True if time > original_time else False

        if period_growing:
            # what to do with the period?
            # give time!
            # take notes for later    
            descDct["got_time"] = [(period.__str__(), diff_hrs, period.id)]
            descDct["gave_time"] = []
            period.accounting.short_notice += diff_hrs
            period.accounting.scheduled += diff_hrs
            period.duration += diff_hrs
            if start_boundary:
                period.start = time
            # what to do w/ the other periods    
            # what are the other periods affected (can be many when growing) 
            # (ignore original period causing affect) 
            range_time = time if start_boundary else original_time
            affected_periods = [p for p in \
                Period.get_periods(range_time, diff_hrs * 60.0) \
                    if p.id != period.id]
            for p in affected_periods:
                if p.start >= period.start and p.end() <= period.end():
                    # remove this period; 
                    descDct["gave_time"].append((p.__str__(), p.duration, p.id))
                    value = p.accounting.get_time(reason)
                    p.accounting.set_changed_time(reason, value + p.duration)
                    p.delete() # The Deleted state!
                else:
                    # give part of this periods time to the affecting period
                    other_time_point = p.end() if start_boundary else p.start
                    other_time = TimeAgent.dtDiffHrs(other_time_point, time)
                    descDct["gave_time"].append((p.__str__(), other_time, p.id))
                    value = p.accounting.get_time(reason)
                    p.accounting.set_changed_time(reason, value + other_time)
                    p.duration -= other_time 
                    if not start_boundary:
                        p.start = time
                    self.reinitScore(p)
                p.accounting.save()
                p.save()
        else: 
            # period is shrinking
            # what to do w/ the period?
            # take time!
            # take notes for later    
            descDct["gave_time"]  = [(period.__str__(), diff_hrs, period.id)]   
            value = period.accounting.get_time(reason)
            period.accounting.set_changed_time(reason, value + diff_hrs)
            period.duration -= diff_hrs
            if start_boundary:
                period.start = time
            # what to do w/ the other affected period (just one!)?
            # give it time!
            # take notes for later
            descDct["got_time"] = [(neighbor.__str__(), diff_hrs, neighbor.id)]
            neighbor.accounting.short_notice += diff_hrs
            neighbor.accounting.scheduled += diff_hrs
            neighbor.accounting.save()
            neighbor.duration += diff_hrs
            if not start_boundary:
                neighbor.start = time
            self.reinitScore(neighbor)
            neighbor.save()    
        
        # in all cases:
        self.reinitScore(period)
        period.accounting.save()
        period.save()
        
        # in all cases, give the description of entire event:
        self.assignDescriptions(descDct, descHead, desc)

        return (True, None)
        
    def reinitScore(self, period):
        now = TimeAgent.quarter(datetime.utcnow())
        if now < period.start:
            period.reinit_score()
