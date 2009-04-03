from TimeAgent          import TimeAgent

from datetime import datetime, timedelta
import copy

class GenOpportunity:
    def __init__(self, window = None, start_time = None, duration = None):
        self.window     = window
        self.start_time = start_time
        self.duration   = duration

STEPSIZE = 15

class OpportunityGenerator:
    def __init__(self, now):
        self.now = now or datetime.utcnow()
        self.opportunities = []

    def generate(self, window, sesshun, ha_limit):

        # Prepare to generate the opportunites day by day:
        # Start at the begining of the Window, or Now, whichever is bigger.
        # TBF: again, why are we truncating the start time to the day?
        orig_start = datetime(window.start_time.year,
                              window.start_time.month,
                              window.start_time.day)
        orig_end   = orig_start + timedelta(days = window.duration)

        start_day = max( datetime(orig_start.year,
                                  orig_start.month,
                                  orig_start.day)
                       , datetime(self.now.year,
                                  self.now.month,
                                  self.now.day))
        duration  = (orig_end - datetime(start_day.year,
                                         start_day.month,
                                         start_day.day)).days
        duration  = 0 if duration < 0 else duration
        for day_no in xrange(duration):
            day = start_day + timedelta(days = day_no)
            transit = \
                   TimeAgent.RelativeLST2AbsoluteTime(sesshun.ra, day)

            # What kind of windowing are we dealing with?
            if sesshun.restrictions == 'UTC':
                # Opportunities begin at the hour specified by the window start
                # and continue for the sesshun's min duration.
                begin = day + timedelta(hours = window.start_time.hour,
                                        minutes = window.start_time.minute)
                end   = begin + timedelta(minutes = sesshun.min_duration)

            if sesshun.restrictions == 'Transit':
                # Opportunities are centered around the transit time, for the
                # sesshun min duration.
                begin = transit - \
                         timedelta(minutes = sesshun.min_duration / 2)
                end   = begin + timedelta(minutes = sesshun.min_duration)

            if sesshun.restrictions == 'Unrestricted':
                # Opportunities are only generated for where the hour angle
                # limits allow us to observe.
                # Find the recommended hour angle limits
                limit = int(sesshun.hourAngleAtHorizon()) if sesshun.ignore_HA /
                                                          else ha_limit

                begin = max(transit - timedelta(hours = limit), start_day)
                end   = min(transit + timedelta(hours = limit),
                            start_day + timedelta(days = duration))

                # Need to handle wrap-around?
                if limit >= 12:
                    end += timedelta(
                        minutes = sesshun.min_duration - STEPSIZE)

            # Generate the opportunities in 15-min increments, in the range
            # specified, for this particular day.
            self.opportunities.extend(self.generate_daily(sesshun, window, begin, end))
            return self.opportunities

    def generate_daily(self, sesshun, window, begin, end):
        """
        Attach all the opportunities to sesshun that will fit between
        begin and end.
        """
        opportunities = []
        begin  = TimeAgent.quarter(begin)
        end    = TimeAgent.quarter(end)
        duration = timedelta(minutes = sesshun.min_duration)
        step = timedelta(minutes = STEPSIZE)
        while begin + duration <= end:
            oppt = GenOpportuntiy(window, begin, sesshun.min_duration)
            opportunities.append(oppt)
            begin += step
        return opportunities

