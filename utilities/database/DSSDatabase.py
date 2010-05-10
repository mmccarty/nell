from datetime                              import date, datetime, timedelta
from nell.utilities.database.DSSPrime2DSS  import DSSPrime2DSS
from nell.utilities.database.Schedtime2DSS import Schedtime2DSS
from nell.utilities.database.UserNames     import UserNames
from sesshuns.models                       import *

class DSSDatabase(object):

    """
    This class is responsible for populating a DSS database that has already
    been primed with static information (observing types table, etc.) with
    the data necessary for running the DSS for a semester.
    The main tasks are: transferring data from an intermediary DB that
    Carl populates, tranferring raw tables we get from Carl's system, and
    filling in missing information on users (from the PST).
    To prepare the database for a specific trimester (including things like
    rcvr schedules), this class should be extended.
    """

    def __init__(self, database = "dss_prime", interactive = False):

        self.interactive = interactive

        # responsible for data transfers
        self.dss_prime = DSSPrime2DSS(database = database)
        self.schedtime = Schedtime2DSS(database = database)

        # responsible for filling in info on users using the PST
        self.un = UserNames(sys.stderr)

    def create(self, trimester):
        "Method for creating a new DSS database "
        # transfer the stuff that is trimester independent
        self.dss_prime.transfer()
        # user the PST query services to fill in all the user info
        self.get_user_info()
        # transfer the trimester dependent stuff - schedtime table!
        # order here is important because we need the user info
        # to be all there first
        # NOTE: if this fails to find certain users, add them to
        # UserNames.createMissingUsers and run again.
        self.schedtime.transfer_fixed_periods(trimester)


    def append(self, trimester):
        "Method for appending new trimester data to existing DSS database"

        self.dss_prime.transfer_only_new()
        print "Getting user information.  This may take several minutes..."
        self.get_user_info()
        print "Transferring fixed periods..."
        self.schedtime.transfer_fixed_periods(trimester)
        self.schedtime.print_report(trimester)

    def get_user_info(self):
        """
        Here's all the hoops you have to jump through to get our User table
        in sync with the PST.
        """

        # who's missing that really needs to be in here?
        self.un.createMissingUsers()
        self.un.setAdminRoles()

        if self.interactive:
            # first, what's the status?
            print "First, check DB vs. PST."
            print "Are these differences in names acceptable?"
            self.un.confirmUserInfo()
            x = raw_input("Continue and get missing IDs/usernames? CtrlX if not.")
        # TBF: We can't use this anymore because the ID we're getting is
        # the global_id, not the id we use.  We should just wait till we
        # have a mirror of their DB in GB.
        #self.un.getUserNamesFromProjects('QueryAgent', 'iBlertFoo')

        # TBF: can't do this if the above line isn't being run
        #self.un.getUserNamesFromIDs()

        if self.interactive:
            print "Finally, check DB vs. PST one more time: "
            self.un.confirmUserInfo()

            print "Fix the rest."
            print ""
            self.un.findMissingUsers()

    def assign_periods_to_windows(self):
        windows = Window.objects.all()
        for w in windows:
            self.assign_periods_to_window(w)

    def assign_periods_to_window(self, window):
        """
        The cadence table in dss_prime tells us how to set up our window
        time ranges, but it does not tell us how which periods are the 
        default period for each window - it can't, this is an idea that only
        exists in DSS, not in Carl's tools.  So, we have to try and match
        up periods from this session that fall into each window.
        """

        # nothing to do if this window already has one
        if window.default_period is not None:
            return

        # what periods overlap w/ this window?
        ps = Period.get_periods(window.start_datetime()
                              , window.duration * 24 * 60 # minutes
                              , ignore_deleted = False)

        # debug
        #print " periods in win: ", window.start_datetime(), window.duration
        #print ps
        #print " periods for session: ", window.session.period_set.all()
        
        # which of them belong to this session?
        sps = [p for p in ps if p.session == window.session]

        # the only exceptable result is for there to be just one period now:
        # no periods means the window is still un-initialized, and more
        # then one period means a human has to intervene.
        if len(sps) == 1:
            window.default_period = sps[0]
            window.save()
        elif len(sps) == 0:
            # TBF: report un-initialized window
            print "NO PERIOD for window: ", window
            pass
        else:
            # TBF: report multiple periods for window
            print "> 1 PERIOD for window: ", window, sps
            pass

    def validate_receiver_schedule(self):
        "Does this rcvr schedule make sense compared to other items?"
        self.check_periods_and_rcvrs()
        self.check_maintenance_and_rcvrs()

    def check_periods_and_rcvrs(self):
        "compares the periods brought over by schedtime w/ the rcvr schedule."

        # make sure we don't have periods scheduled at times where
        # there isn't a required rcvr available
        ps = Period.objects.all()
        bad = []
        for p in ps:
            if not p.has_required_receivers():
                #print "bad period: ", p
                bad.append(p)
        # report
        for b in bad:
            print "Session (%s, %d) at %s for %f hours needs rcvrs: %s" % \
                (b.session.name
               , b.session.original_id
               , b.start
               , b.duration
               , b.session.receiver_list_simple())
        print "number of periods w/ out required receivers: ", len(bad)

    def check_maintenance_and_rcvrs(self):
        "Are there rcvr changes happening w/ out maintenance days?"
        bad = []
        # cast a wide enough net to make this trimester agnostic
        start = date(2000, 1, 1)
        days = 365 * 20
        schedule = Receiver_Schedule.extract_schedule(start, days)
        changes = schedule.items()
        # the first date is a date, not a datetime, ignore it.
        for dt, rcvrs in changes[1:]:
            # is there a maintanence day this day?
            # well, what are the periods for this day?
            start_day = dt.replace(hour = 0
                                 , minute = 0
                                 , second = 0
                                 , microsecond = 0)
            end_day = start_day + timedelta(days = 1)
            day_periods = Period.objects.filter(start__gt = start_day
                                              , start__lt = end_day)
            # of these, is any one of them a maintenance?
            maintenance = [p for p in day_periods \
                if p.session.project.is_maintenance()]
            if len(maintenance) == 0:
                bad.append(dt)

        print "Rcvr changes w/ out maintenance day: "
        bad.sort()
        for b in bad:
            print b

