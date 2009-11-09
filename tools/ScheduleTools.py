from sesshuns.models import *
from utilities.TimeAgent import dtDiffHrs

class ScheduleTools(object):

    def changeSchedule(self, start, duration, sesshun, reason, description):
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

        # tag the descriptoin
        nowStr = datetime.now().strftime("%Y-%m-%d %H:%M")    
        tag = " [Schedule Change (%s)]: " % nowStr 
        description = tag + description

        # what periods are we affecting?
        duration_mins = duration * 60.0
        ps = Period.get_periods(start, duration_mins)
        if debug:
            print "len(ps): ", len(ps)

        # first, adjust each of the affected periods - including time accnting
        end = start + timedelta(hours = duration)
        for p in ps:
            if debug:
                print "changing period: ", p
                print "comparing period: ", p.start, p.end()
                print "w/:               ", start, end 
            if p.start >= start and p.end() <= end:
                if debug:
                    print "delete period!"
                # this entire period is being replaced
                # TBF: can't do this p.delete()
                # TBF: use state!
                other_sess_time = p.duration
                p.duration = 0
                #p.delete()
                #p = None
            elif p.start >= start and p.end() > end:
                if debug:
                    print "start period later"
                # we're chopping off the beginning of this period
                new_duration = (p.end() - end).seconds / 3600.0
                other_sess_time = p.duration - new_duration
                p.duration = new_duration
                p.start = end
            elif p.start < start and p.end() > end:
                if debug:
                    print "bi-secting period"
                # we're chopping out the middle of a period: we fix this
                # by adjusting the period, then creating a new one
                original_duration = p.duration
                original_end      = p.end()
                p.duration = (start - p.start).seconds / 3600.0
                # the new one
                new_dur = (original_end - end).seconds / 3600.0
                accounting = Period_Accounting(scheduled = new_dur
                                             , short_notice = new_dur
                                             , description = description
                                               )
                accounting.save()                             
                period_2cd_half = Period(session  = p.session
                                       , start    = end
                                       , duration = new_dur
                                       , score    = 0.0
                                       , forecast = end
                                       , accounting = accounting 
                                         )
                period_2cd_half.save()                         
                # the original period is really giving up time to the 
                # bi-secting new period, and the new second half!
                other_sess_time = duration + new_dur
            elif p.start < start and p.end() > start:
                if debug:
                    print "shorten period"
                # we're chopping off the end of this period
                new_duration = (start - p.start).seconds / 3600.0
                other_sess_time = p.duration - new_duration
                p.duration = new_duration
                         
            else:
                raise "not covered"
            # now change this periods time accounting
            if p is not None:
                if debug:
                    print "changes: ", p
                # increment values: don't overwrite them!
                value = p.accounting.get_time(reason)
                p.accounting.set_changed_time(reason, value + other_sess_time)
                desc = p.accounting.description \
                    if p.accounting.description is not None else ""
                p.accounting.description = desc + description
                p.accounting.save()
                p.save()

        # finally, anything to replace it with?
        if sesshun is not None:
            # create a period for this
            pa = Period_Accounting(scheduled    = duration
                                 , short_notice = duration
                                 , description  = description)
            pa.save()                     
            p = Period(session    = sesshun
                     , start      = start
                     , duration   = duration
                     , score      = 0.0
                     , forecast   = start
                     , accounting = pa)
            p.save()    

      # TBF: now we have to rescore all the affected periods!

    def shiftPeriodBoundaries(self, period, start_boundary, time, neighbor, desc):
        """
        Shifts the boundary between a given period and it's neighbors:
           * period_id - the period obj. whose boundary we first adjust
           * start_boundary - boolean, true for start, false for end
           * time - new time for that boundary
           * neighbors - periods affected
        After periods are adjusted, time accounting is adjusted appropriately
        """
       
        # TBF: capture this from user
        reason = "other_session_other"

        # if there isn't a neibhbor, then this change should be done by hand
        if neighbor is None:
            return (False, "Cannot shift period boundary if there is a neighboring gap in the schedule.")

        # get the time range affected
        original_time = period.start if start_boundary else period.end()
        diff_hrs = dtDiffHrs(original_time, time) #self.get_time_diff_hours(original_time, time)

        # check for the no-op
        if original_time == time:
            return (False, "Time given did not change Periods duration")

        # create the tag used for all descriptions in time accounting
        nowStr = datetime.now().strftime("%Y-%m-%d %H:%M")    
        tag = " [Shift Period Bnd. (%s)]: " % nowStr 
        description = tag + desc

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
                    # remove this period; TBF: state -> deleted!
                    value = p.accounting.get_time(reason)
                    p.accounting.set_changed_time(reason, value + p.duration)
                    p.duration = 0.0 # TBF: state!
                else:
                    # give part of this periods time to the affecting period
                    other_time_point = p.end() if start_boundary else p.start
                    #other_time = self.get_time_diff_hours(other_time_point
                    #                                    , time)
                    other_time = dtDiffHrs(other_time_point, time)
                    value = p.accounting.get_time(reason)
                    p.accounting.set_changed_time(reason, value + other_time)
                    p.duration -= other_time 
                    if not start_boundary:
                        p.start = time
                p.accounting.description = description    
                p.accounting.save()
                p.save()
        else: 
            # period is shrinking
            # what to do w/ the period?
            # take time!
            value = period.accounting.get_time(reason)
            period.accounting.set_changed_time(reason, value + diff_hrs)
            period.duration -= diff_hrs
            if start_boundary:
                period.start = time
            # what to do w/ the other affected period (just one!)?
            # give it time!
            #value = neighbor.accounting.get_time(reason)
            #neighbor.accounting.set_changed_time(reason, value + diff_hrs)
            neighbor.accounting.short_notice += diff_hrs
            neighbor.accounting.scheduled += diff_hrs
            neighbor.accounting.description = description
            neighbor.accounting.save()
            neighbor.duration += diff_hrs
            if not start_boundary:
                neighbor.start = time
            neighbor.save()    
        
        # in all cases:
        period.accounting.description = description
        period.accounting.save()
        period.save()

        # TBF: now we have to rescore all the affected periods!

        return (True, None)

               

