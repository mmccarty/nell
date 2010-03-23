from datetime                  import datetime, timedelta, date
from math                      import asin, acos, cos, sin
from tools                     import TimeAccounting
from django.conf               import settings
from django.db                 import models
from django.http               import QueryDict
from settings                  import ANTIOCH_SERVER_URL
from utilities.receiver        import ReceiverCompile
from utilities                 import TimeAgent, UserInfo, NRAOBosDB
from utilities                 import ScorePeriod

import calendar
import pg
from sets                      import Set
import urllib2
import simplejson as json
import sys
import reversion

def first(results, default = None):
    return default if len(results) == 0 else results[0]

def str2dt(str):
    "'YYYY-MM-DD hh:mm:ss' to datetime object"
    if str is None:
        return None

    if ' ' in str:
        dstr, tstr = str.split(' ')
        y, m, d    = map(int, dstr.split('-'))
        time       = tstr.split(':')
        h, mm, ss  = map(int, map(float, time))
        return datetime(y, m, d, h, mm, ss)

    y, m, d   = map(int, str.split('-'))
    return datetime(y, m, d)

def strStr2dt(dstr, tstr):
    return str2dt(dstr + ' ' + tstr) if tstr else str2dt(dstr)
        
def dt2str(dt):
    "datetime object to YYYY-MM-DD hh:mm:ss string"
    if dt is None:
        return None
    else:    
        return dt.strftime("%Y-%m-%d %H:%M:%S")

def d2str(dt):
    "datetime object to YYYY-MM-DD string"
    if dt is None:
        return None
    else:    
        return dt.strftime("%Y-%m-%d")

def t2str(dt):
    "datetime object to hh:mm string"
    if dt is None:
        return None
    else:    
        return dt.strftime("%H:%M")

def range_to_days(ranges):
    dates = []
    for rstart, rend in ranges:
        if rend - rstart > timedelta(days = 1):
            start = rstart
            end   = rstart.replace(hour = 0, minute = 0, second = 0) + timedelta(days = 1)
            while start < rend and end < rend:
                if end - start >= timedelta(days = 1):
                    dates.append(start)
                start = end
                end   = end + timedelta(days = 1)
    return dates

def overlaps(dt1, dt2):
    start1, end1 = dt1
    start2, end2 = dt2

    if start1 < end2 and start2 < end1:
        return True
    else:
        return False

def find_intersections(events):
    """
    Takes a list of lists of datetime tuples of the form (start, end) 
    representing sets of events, finds the intersections of all the
    sets, and returns a list of datetime tuples of the form (start, end)
    describing the intersections.  All datetime tuples are assumed to be 
    in the same timezone.
    """
    start = 0; end = 1
    intersections = []
    for b in events[0]:
        for set in events[1:]:
            if any([overlaps(b, s) for s in set]):
                intersections.extend(
                    [(max([b[start], s[start]]), min([b[end], s[end]])) \
                     for s in set if overlaps(b, s)])
            else:
                return [] # No intersections for all sets.

    return intersections

def consolidate_events(events):
    """
    Takes a list of datetime tuples of the form (start, end) and
    reduces it to the smallest list that fully describes the events.
    All datetime tuples are assumed to be in the same timezone.
    """
    if len(events) == 1:
        return events
    else:
        return combine_events(consolidate_overlaps(events))

def consolidate_overlaps(events):
    reduced = []
    for (begin1, end1) in events:
        begin = begin1
        end   = end1
        for (begin2, end2) in events:
            if (begin1, end1) != (begin2, end2) and \
               begin1 < end2 and begin2 < end1:
                begin = min([begin, begin1, begin2])
                end   = max([end, end1, end2])
        if (begin, end) not in reduced:
            reduced.append((begin, end))            
    return reduced

def combine_events(events):
    if len(events) in (0, 1):
        return events 

    events = sorted(events)
    combined = [events[0]]
    for (begin2, end2) in events[1:]:
        begin1, end1 = combined[-1]
        if begin2 == end1:
            combined[-1] = (begin1, end2)
        else:
            combined.append((begin2, end2))
    return combined

jsonMap = {"authorized"     : "status__authorized"
         , "between"        : "time_between"
         , "backup"         : "status__backup"
         , "pcode"          : "project__pcode"
         , "complete"       : "status__complete"
         , "coord_mode"     : "target__system__name"
         , "enabled"        : "status__enabled"
         , "freq"           : "frequency"
         , "grade"          : "allotment__grade"
         , "id"             : "id"
         , "name"           : "name"
         , "orig_ID"        : "original_id"
         , "receiver"       : "receiver_group__receivers__abbreviation"
         , "PSC_time"       : "allotment__psc_time"
         , "req_max"        : "max_duration"
         , "req_min"        : "min_duration"
         , "science"        : "observing_type__type"
         , "sem_time"       : "allotment__max_semester_time"
         , "source"         : "target__source"
         , "source_h"       : "target__horizontal"
         , "source_v"       : "target__vertical"
         , "total_time"     : "allotment__total_time"
         , "type"           : "session_type__type"
               }

class Role(models.Model):
    role = models.CharField(max_length = 32)

    class Meta:
        db_table = "roles"

    def __unicode__(self):
        return self.role

class User(models.Model):
    original_id = models.IntegerField(null = True, blank = True)
    pst_id      = models.IntegerField(null = True, blank = True)
    username    = models.CharField(max_length = 32, null = True, blank = True)
    sanctioned  = models.BooleanField(default = False)
    first_name  = models.CharField(max_length = 32)
    last_name   = models.CharField(max_length = 150)
    contact_instructions = models.TextField(null = True, blank = True)
    role                 = models.ForeignKey(Role)

    class Meta:
        db_table = "users"

    def __str__(self):
        return "%s, %s" % (self.last_name, self.first_name)

    def update_from_post(self, fdata):
        role  = first(Role.objects.filter(role = fdata.get('role')))
        self.role        = role
        self.username    = fdata.get('username')
        sanctioned       = fdata.get('sanctioned')
        self.sanctioned  = sanctioned.lower() == 'true' if sanctioned is not None else sanctioned
        self.first_name  = fdata.get('first_name')
        self.last_name   = fdata.get('last_name')
        self.contact_instructions   = fdata.get('contact_instructions')
        self.save()

    def jsondict(self):
        projects = ','.join([i.project.pcode for i in self.investigator_set.all()])
        return {'id' : self.id
              , 'username'   : self.username
              , 'first_name' : self.first_name
              , 'last_name'  : self.last_name
              , 'sanctioned' : self.sanctioned
              , 'projects'   : projects
              , 'role'       : self.role.role
                }

    def name(self):
        return self.__str__()

    def isAdmin(self):
        return self.role.role == "Administrator"

    def isOperator(self):
        return self.role.role == "Operator"

    def getStaticContactInfo(self, use_cache = True):
        return UserInfo().getProfileByID(self, use_cache)

    def getReservations(self, use_cache = True):
        return NRAOBosDB().getReservationsByUsername(self.username, use_cache)

    def getPeriods(self):
        retval = []
        for i in self.investigator_set.all():
            retval.extend(i.project.getPeriods())
        return sorted(list(Set(retval)))

    def getPeriodsByProject(self):
        """
        Returns a dictionary of project: [periods] associated with this
        user sorted by start date.
        """
        retval = {}
        for i in self.investigator_set.all():
            retval[i.project] = i.project.getPeriods()
        return retval

    def getUpcomingPeriods(self, dt = datetime.now()):
        "What periods might this observer have to observe soon?"
        return [p for p in self.getPeriods() if p.start >= dt]

    def getUpcomingPeriodsByProject(self, dt = datetime.now()):
        "What periods might this observer have to observe soon?"
        retval = {}
        for project, period in self.getPeriodsByProject().items():
            retval[project] = [p for p in period if p.start >= dt]
        return retval

    def getObservedPeriods(self, dt = datetime.now()):
        "What periods associated w/ this observer have been observed?"
        return [p for p in self.getPeriods() if p.start < dt]

    def getObservedPeriodsByProject(self, dt = datetime.now()):
        "What periods associated w/ this observer have been observed?"
        retval = {}
        for project, period in self.getPeriodsByProject().items():
            retval[project] = [p for p in period if p.start < dt]
        return retval

    def isInvestigator(self, pcode):
        "Is this user an investigator on the given project?"
        return pcode in [i.project.pcode for i in self.investigator_set.all()]

    def isFriend(self, pcode):
        "Is this user a friend for the given project?"
        return pcode in [p.pcode for p in self.project_set.all()]

    def canViewProject(self, pcode):
        "A user can view project info if he's an inv, friend, admin, or op."
        return self.isInvestigator(pcode) \
            or self.isFriend(pcode) \
            or self.isAdmin() \
            or self.isOperator()

    def canViewUser(self, user):
        """
        A user can view another user if they share the same project (by being
        an investigator or friend), or if they are admin or op.
        """
        upcodes = [i.project.pcode for i in user.investigator_set.all()]
        shared_projects = [p for p in upcodes if self.isFriend(p) \
                                              or self.isInvestigator(p)]
        return shared_projects != [] or self.isAdmin() or self.isOperator()                                      
# TBF: Remove this when we are sure we don't need this local email
#      table anymore.
class Email(models.Model):
    user  = models.ForeignKey(User)
    email = models.CharField(max_length = 255)

    class Meta:
        db_table = "emails"

class Semester(models.Model):
    semester = models.CharField(max_length = 64)

    def __unicode__(self):
        return self.semester

    def start(self):
        # A starts in February, B in June, C in October
        start_months = {"A": 2, "B": 6, "C": 10}

        year  = 2000 + int(self.semester[:2])
        month = start_months[self.semester[-1]]

        return datetime(year, month, 1)

    def end(self):
        # A ends in May, B in September, C in January
        end_months = {"A": 5, "B": 9, "C": 1}

        year   = 2000 + int(self.semester[:2])
        if self.semester[-1] == "C":
            year += 1
        month  = end_months[self.semester[-1]]
        _, day = calendar.monthrange(year, month)

        return datetime(year, month, day)

    def eventjson(self, id):
        return {
            "id"   : id
          , "title": "".join(["Start of ", self.semester])
          , "start": self.start().isoformat()
        }

    @staticmethod
    def getFutureSemesters(today = datetime.today()):
        "Returns a list of Semesters that start on or after the given date."
        return sorted([s for s in Semester.objects.all() if s.start() >= today]
                     , lambda x, y: cmp(x.start(), y.start()))

    @staticmethod
    def getPreviousSemesters(today = datetime.today()):
        """
        Returns a list of Semesters that occur prior to the given date
        not including the current semester as defined by the given date.
        """
        return sorted([s for s in Semester.objects.all() if s.start() <= today]
                     , lambda x, y: cmp(x.start(), y.start()))

    @staticmethod
    def getCurrentSemester(today = datetime.today()):
        "Returns the current Semester."
        return Semester.getPreviousSemesters(today)[-1]

    class Meta:
        db_table = "semesters"

class Project_Type(models.Model):
    type = models.CharField(max_length = 64)

    def __unicode__(self):
        return self.type

    class Meta:
        db_table = "project_types"

class Allotment(models.Model):
    psc_time          = models.FloatField(help_text = "Hours")
    total_time        = models.FloatField(help_text = "Hours")
    max_semester_time = models.FloatField(help_text = "Hours")
    grade             = models.FloatField(help_text = "0.0 - 4.0")
    ignore_grade      = models.NullBooleanField(null = True, default = False, blank = True)

    base_url = "/sesshuns/allotment/"

    def __unicode__(self):
        return "(%d) Total: %5.2f, Grade: %5.2f, PSC: %5.2f, Max: %5.2f" % \
                                       (self.id
                                      , float(self.total_time)
                                      , float(self.grade)
                                      , float(self.psc_time)
                                      , float(self.max_semester_time)
                                      ) 

    def get_absolute_url(self):
        return "/sesshuns/allotment/%i/" % self.id

    class Meta:
        db_table = "allotment"
        
class Project(models.Model):
    semester         = models.ForeignKey(Semester)
    project_type     = models.ForeignKey(Project_Type)
    allotments       = models.ManyToManyField(Allotment, through = "Project_Allotment")
    pcode            = models.CharField(max_length = 32)
    name             = models.CharField(max_length = 150)
    thesis           = models.BooleanField()
    complete         = models.BooleanField()
    start_date       = models.DateTimeField(null = True, blank = True)
    end_date         = models.DateTimeField(null = True, blank = True)
    friend           = models.ForeignKey(User, null = True, blank = True)
    accounting_notes = models.TextField(null = True, blank = True)
    notes            = models.TextField(null = True, blank = True)
    schedulers_notes = models.TextField(null = True, blank = True)

    base_url = "/sesshuns/project/"

    def __unicode__(self):
        return "%s, %s, %s" % (self.pcode, self.semester, self.name)

    def __str__(self):
        return self.pcode

    def is_maintenance(self):
        return self.name == 'Maintenance' 

    def get_allotments_display(self):
        return self.allotments.all()

    def getObservedTime(self):
        return TimeAccounting().getTime("observed", self)

    def getTimeBilled(self):
        return TimeAccounting().getTime("time_billed", self)

    def getSumTotalTime(self):
        return TimeAccounting().getProjectTotalTime(self)

    def getTimeRemainingFromCompleted(self):
        return TimeAccounting().getTimeRemainingFromCompleted(self)

    def getTimeRemaining(self):
        return TimeAccounting().getTimeRemaining(self)

    def init_from_post(self, fdata):
        self.update_from_post(fdata)

    def update_from_post(self, fdata):
        fproj_type = fdata.get("type", "science")
        p_type     = first(Project_Type.objects.filter(type = fproj_type))
        fsemester  = fdata.get("semester", "09C")
        semester   = first(Semester.objects.filter(semester = fsemester))

        self.semester         = semester
        self.project_type     = p_type
        self.pcode            = fdata.get("pcode", "")
        self.name             = fdata.get("name", "")
        self.thesis           = fdata.get("thesis", "false") == "true"
        self.complete         = fdata.get("complete", "false") == "true"
        self.notes            = fdata.get("notes", "")
        self.schedulers_notes = fdata.get("schd_notes", "")

        self.save()

        totals   = map(float, fdata.get("total_time", "0.0").split(', '))
        pscs     = map(float, fdata.get("PSC_time", "0.0").split(', '))
        max_sems = map(float, fdata.get("sem_time", "0.0").split(', '))
        grades   = map(float, fdata.get("grade", "4.0").split(', '))
        
        assert len(totals) == len(pscs) and \
               len(totals) == len(max_sems) and \
               len(totals) == len(grades)

        num_new = len(totals)
        num_cur = len(self.allotments.all())
        if num_new > num_cur:
            for i in range(num_new - num_cur):
                a = Allotment(psc_time = 0.0
                            , total_time = 0.0
                            , max_semester_time = 0.0
                            , grade             = 0.0
                              )
                a.save()

                pa = Project_Allotment(project = self, allotment = a)
                pa.save()
        elif num_new < num_cur:
            for a in self.allotments.all()[:(num_cur - num_new)]:
                a.delete()
                
        allotment_data = zip(totals, pscs, max_sems, grades)
        for data, a in zip(allotment_data, self.allotments.all()):
            t, p, m, g = data
            a.total_time        = t
            a.psc_time          = p
            a.max_semester_time = m
            a.grade             = g
            a.save()
        
        self.save()

    def jsondict(self):
        totals   = ', '.join([str(a.total_time) for a in self.allotments.all()])
        pscs     = ', '.join([str(a.psc_time) for a in self.allotments.all()])
        max_sems = ', '.join([str(a.max_semester_time) for a in self.allotments.all()])
        grades   = ', '.join([str(a.grade) for a in self.allotments.all()])

        pi = '; '.join([i.user.name() for i in self.investigator_set.all()
                        if i.principal_investigator])
        co_i = '; '.join([i.user.name() for i in self.investigator_set.all()
                        if not i.principal_investigator])

        return {"id"           : self.id
              , "semester"     : self.semester.semester
              , "type"         : self.project_type.type
              , "total_time"   : totals
              , "PSC_time"     : pscs
              , "sem_time"     : max_sems
              , "remaining"    : self.getTimeRemaining()
              , "grade"        : grades
              , "pcode"        : self.pcode
              , "name"         : self.name
              , "thesis"       : self.thesis
              , "complete"     : self.complete
              , "pi"           : pi
              , "co_i"         : co_i
              , "notes"        : self.notes if self.notes is not None else ""
              , "schd_notes"   : self.schedulers_notes \
                                 if self.schedulers_notes is not None else ""
                }

    def principal_contact(self):
        "Who is the principal contact for this Project?"
        pc = None
        for inv in self.investigator_set.all():
            # if more then one, it's arbitrary
            if inv.principal_contact:
                pc = inv.user
        return pc        

    def principal_investigator(self):
        "Who is the principal investigator for this Project?"
        pc = None
        for inv in self.investigator_set.all():
            # if more then one, it's arbitrary
            if inv.principal_investigator:
                pc = inv.user
        return pc    

    def normalize_investigators(self):
        """
        Adjusts the priority field of all the project's investigators
        to a standard form in response to any possible change.
        """

        priority = 1
        for i in self.investigator_set.order_by('priority').all():
            if i.observer:
                i.priority = priority
                priority += 1
            else:
                i.priority = 999
            i.save()

    def rcvrs_specified(self):
        "Returns an array of rcvrs for this project, w/ out their relations"
        # For use in recreating Carl's reports
        rcvrs = []
        for s in self.sesshun_set.all():
            rs = s.rcvrs_specified()
            for r in rs:
                if r not in rcvrs:
                    rcvrs.append(r)
        return rcvrs            

    def getPeriods(self):
        "What are the periods associated with this project, vis. to observer?"
        return sorted([p for s in self.sesshun_set.all()
                         for p in s.period_set.all()
                         if p.state.abbreviation not in ['P','D']])

    def getUpcomingPeriods(self, dt = datetime.now()):
        "What periods are associated with this project in the future?"
        return [p for p in self.getPeriods() if p.start > dt] 


    def getPastPeriods(self, dt = datetime.now()):
        "What periods are associated with this project in the past?"
        return [p for p in self.getPeriods() if p.start <= dt] 

    def has_schedulable_sessions(self):
        sessions = [s for s in self.sesshun_set.all() if s.schedulable()]
        return True if sessions != [] else False

    def get_observers(self):
        return [i for i in self.investigator_set.order_by('priority').all() \
                if i.observer]

    def get_sanctioned_observers(self):
        return [i for i in self.investigator_set.order_by('priority').all() \
                if i.observer and i.user.sanctioned]

    def has_sanctioned_observers(self):
        return True if self.get_sanctioned_observers() != [] else False

    def transit(self):
        "Returns true if a single one of it's sessions has this flag true"
        sessions = [s for s in self.sesshun_set.all() if s.transit()]
        return True if sessions != [] else False

    def nighttime(self):
        "Returns true if a single one of it's sessions has this flag true"
        sessions = [s for s in self.sesshun_set.all() if s.nighttime()]
        return True if sessions != [] else False

    def anyCompleteSessions(self):
        "Returns true if a single session has been set as complete"
        sessions = [s for s in self.sesshun_set.all() if s.status.complete]
        return True if sessions != [] else False

    def get_prescheduled_days(self, start, end):
        """
        Returns a list of binary tuples of the form (start, end) that
        describe the whole days when this project cannot observe 
        because other projects already have scheduled telescope periods
        during the time range specified by the start and end arguments.
        """
        return range_to_days(self.get_prescheduled_times(start, end))

    def get_prescheduled_times(self, start, end):
        """
        Returns a list of binary tuples of the form (start, end) that
        describe when this project cannot observe because other 
        projects already have scheduled telescope periods during
        the time range specified by the start and end arguments.
        """
        times = [(d.start, d.start + timedelta(hours = d.duration)) \
                 for p in Project.objects.all() \
                 for d in p.getPeriods() \
                 if p != self and \
                    d.state.abbreviation == 'S' and \
                    overlaps((d.start, d.end()), (start, end))]
        return consolidate_events(times)

    def get_blackout_dates(self, start, end):
        """
        A project is 'blacked out' when all of its sanctioned observers
        are unavailable.  Returns a list of tuples describing the whole days
        where the project is 'blacked out' in UTC.
        """
        return range_to_days(self.get_blackout_times(start, end))

    def get_blackout_times(self, start, end):
        """
        A project is 'blacked out' when all of its sanctioned observers
        are unavailable.  Returns a list of tuples describing the time ranges
        where the project is 'blacked out' in UTC.
        """
        if not self.has_sanctioned_observers():
            return []

        blackouts = [o.user.blackout_set.all() \
                     for o in self.get_sanctioned_observers()]

        # Change all to UTC.
        utcBlackouts = []
        for set in blackouts:
            utc = []
            for b in set:
                utc.extend(b.generateDates(start, end))
            utcBlackouts.append(utc)

        if len(utcBlackouts) == 1: # One observer runs the show.
            return sorted(utcBlackouts[0])

        return consolidate_events(find_intersections(utcBlackouts))

    def get_receiver_blackout_ranges(self, start, end):
        """
        Returns a list of tuples of the form (start, end) where
        start and end are datetime objects that denote the 
        beginning and ending of a period where no receivers are available
        for any session in a project.  If there is a receiver available
        at all times for any session, an empty list is returned.  If there
        are no session for a project, an empty list is returned.
        """

        # Find all the required receiver sets for this project and schedule.
        # E.g. for one session:
        #     [[a, b, c], [x, y, z]] = (a OR b OR c) AND (x OR y OR z)
        required = [s.receiver_group_set.all() for s in self.sesshun_set.all()]
        if required == []:
            return [] # No sessions, no problem

        schedule = Receiver_Schedule.extract_schedule(start, (end - start).days)

        if schedule == {}: # No receiver schedule present!
            return [(start, None)]

        # Go through the schedule and determine blackout ranges.
        ranges = []
        for date, receivers in sorted(schedule.items()):
            receivers = Set(receivers)
            if not any([all([Set(g.receivers.all()).intersection(receivers) \
                        for g in set]) for set in required]):
                # No session has receivers available. Begin drought.
                if not ranges or ranges[-1][1] is not None:
                    ranges.append((date, None))
            else:
                # A session has receivers available. End drought, if present.
                if ranges and ranges[-1][1] is None:
                    start, _ = ranges.pop(-1)
                    ranges.append((start, date))
        return ranges

    def get_receiver_blackout_dates(self, start, end):
        # Change date ranges into individual days.
        blackouts = []
        for rstart, rend in self.get_receiver_blackout_ranges(start, end):
            counter = rstart.replace(hour = 0)
            while counter < (rend or end):
                blackouts.append(counter)
                counter = counter + timedelta(days = 1)
 
        return blackouts

    def get_observed_periods(self, dt = datetime.now()):
        "What periods have been observed on this project?"
        return self.getPastPeriods(dt)

    def get_allotment(self, grade):
        "Returns the allotment that matches the specified grade"
        # TBF watch out - this is a float!
        epsilon = 1e-3
        for a in self.allotments.all():
            diff = abs(a.grade - grade)
            if diff < epsilon:
                return a
        return None # uh-oh

    def get_windows(self):
        # TBF no filtering here, ALL windows!
        return sorted([w for s in self.sesshun_set.all()
                         for w in s.window_set.all()
                         if s.session_type.type == 'windowed']
                     , key = lambda x : x.start_date)

    def get_active_windows(self):
        "Returns current and future windows."
        wins = self.get_windows()
        now = datetime.utcnow()
        today = date(now.year, now.month, now.day)
        return [ w for w in wins
                 if today < (w.start_date + timedelta(days = w.duration)) ]

    class Meta:
        db_table = "projects"

class Project_Allotment(models.Model):
    project = models.ForeignKey(Project)
    allotment = models.ForeignKey(Allotment)

    class Meta:
        db_table = "projects_allotments"

class Repeat(models.Model):
    repeat = models.CharField(max_length = 32)

    def __str__(self):
        return self.repeat

    class Meta:
        db_table = "repeats"
        
class TimeZone(models.Model):
    timeZone = models.CharField(max_length = 128)

    def __str__(self):
        return self.timeZone
        
    def utcOffset(self):
        "Returns a timedelta representing the offset from UTC."
        offset = int(self.timeZone[4:]) if self.timeZone != "UTC" else 0
        return timedelta(hours = offset)
 
    class Meta:
        db_table = "timezones"
        
class Blackout(models.Model):
    user         = models.ForeignKey(User)
    start_date   = models.DateTimeField(null = True, blank = True)
    end_date     = models.DateTimeField(null = True, blank = True)
    repeat       = models.ForeignKey(Repeat)
    until        = models.DateTimeField(null = True, blank = True)
    description  = models.CharField(null = True, max_length = 1024, blank = True)

    def __unicode__(self):
        return "%s Blackout for %s: %s - %s" % \
               (self.repeat.repeat, self.user, self.start_date, self.end_date)

    def isActive(self, date = datetime.utcnow()):
        """
        Takes a UTC datetime object and returns a Boolean indicating whether
        this blackout's effective date range is effective on this date.
        """

        if self.start_date is None:
            return False # Never started, not active
        
        if self.start_date >= date:
            return True # Happens in the future

        if not self.end_date and self.start_date <= date:
            return True # Started on/before date, never ends

        if self.start_date <= date and self.end_date >= date:
            return True # Starts on/before date, ends on/after date

        if self.repeat.repeat != "Once":
            if not self.until and self.start_date <= date:
                return True # Started on/before date, repeats forever

            if self.until and self.until >= date and self.start_date <= date:
                return True # Started on/before date, repeats on/after date

        return False

    def generateDates(self, calstart, calend):
        """
        Takes two UTC datetimes representing a period of time on the calendar.
        Returns a list of (datetime, datetime) tuples representing all the
        events generated by this blackout in that period.
        """

        # take care of simple scenarios first
        if self.start_date is None or self.end_date is None:
            return [] # What does it mean to have None in start or end?

        if self.start_date > calend:
            return [] # Outside this time period - hasn't started yet

        start       = self.start_date
        end         = self.end_date
        until       = min(self.until, calend) if self.until else calend
        periodicity = self.repeat.repeat
        dates       = []
        
        if periodicity == "Once":
            dates.append((start, end))
        elif periodicity == "Weekly":
            while start <= until:
                if start >= calstart:
                    dates.append((start, end))

                start = start + timedelta(days = 7)
                end   = end   + timedelta(days = 7)
        elif periodicity == "Monthly":
            while start <= until:
                if start >= calstart:
                    dates.append((start, end))

                if start.month == 12: # Yearly wrap around
                    start.month = 0; start.year = start.year + 1

                start = datetime(year   = start.year
                               , month  = start.month + 1
                               , day    = start.day
                               , hour   = start.hour
                               , minute = start.minute)
                end   = datetime(year   = end.year
                               , month  = end.month + 1
                               , day    = end.day
                               , hour   = end.hour
                               , minute = end.minute)
        return dates

    def eventjson(self, calstart, calend, id = None):
        calstart = datetime.fromtimestamp(float(calstart))
        calend   = datetime.fromtimestamp(float(calend))
        dates    = self.generateDates(calstart, calend)
        title    = "%s: %s" % (self.user.name()
                             , self.description or "blackout")
        return [{
            "id"   : self.id
          , "title": title
          , "start": d[0].isoformat() if d[0] else None
          , "end"  : d[1].isoformat() if d[1] else None
        } for d in dates]

    class Meta:
        db_table = "blackouts"

class Investigator(models.Model):
    project                = models.ForeignKey(Project)
    user                   = models.ForeignKey(User)
    observer               = models.BooleanField(default = False)
    principal_contact      = models.BooleanField(default = False)
    principal_investigator = models.BooleanField(default = False)
    priority               = models.IntegerField(default = 1)

    def __unicode__(self):
        return "%s (%d) for %s; obs : %s, PC : %s, PI : %s" % \
            ( self.user
            , self.user.id
            , self.project.pcode
            , self.observer
            , self.principal_contact
            , self.principal_investigator )

    def jsondict(self):
        return {"id"         : self.id
              , "name"       : "%s, %s" % (self.user.last_name, self.user.first_name)
              , "pi"         : self.principal_investigator
              , "contact"    : self.principal_contact
              , "remote"     : self.user.sanctioned
              , "observer"   : self.observer
              , "priority"   : self.priority
              , "project_id" : self.project.id
              , "user_id"    : self.user.id
               }

    def init_from_post(self, fdata):
        p_id    = int(float(fdata.get("project_id")))
        u_id    = int(float(fdata.get("user_id")))
        project = first(Project.objects.filter(id = p_id)) or first(Project.objects.all())
        user    = first(User.objects.filter(id = u_id)) or first(User.objects.all())
        self.project                = project
        self.user                   = user
        self.observer               = fdata.get('observer', 'false').lower() == 'true'
        self.principal_contact      = fdata.get('contact', 'false').lower() == 'true'
        self.principal_investigator = fdata.get('pi', 'false').lower() == 'true'
        self.priority               = int(float(fdata.get('priority', 1)))
        self.save()

        self.user.sanctioned        = fdata.get('remote', 'false').lower() == 'true'
        self.user.save()

    def update_from_post(self, fdata):
        self.init_from_post(fdata)

    def name(self):
        return self.user

    def project_name(self):
        return self.project.pcode

    def projectBlackouts(self):
        return sorted([b for b in self.user.blackout_set.all()
                       if b.isActive()])
    
    class Meta:
        db_table = "investigators"

class Session_Type(models.Model):
    type = models.CharField(max_length = 64)

    def __unicode__(self):
        return self.type
    
    class Meta:
        db_table = "session_types"

    @staticmethod
    def get_type(type):
        return first(Session_Type.objects.filter(type = type))

class Observing_Type(models.Model):
    type = models.CharField(max_length = 64)

    def __unicode__(self):
        return self.type

    class Meta:
        db_table = "observing_types"

class Receiver(models.Model):
    name         = models.CharField(max_length = 32)
    abbreviation = models.CharField(max_length = 32)
    freq_low     = models.FloatField(help_text = "GHz")
    freq_hi      = models.FloatField(help_text = "GHz")

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = "receivers"

    def full_description(self):
        return "(%s) %s: %5.2f - %5.2f" % (self.abbreviation
                                         , self.name
                                         , self.freq_low
                                         , self.freq_hi)

    def jsondict(self):
        return self.abbreviation

    def in_band(self, frequency):
        "Does the given freq fall into this rcvr's freq range?"
        return self.freq_low <= frequency <= self.freq_hi

    @staticmethod
    def get_abbreviations():
        return [r.abbreviation for r in Receiver.objects.all()]

    @staticmethod
    def get_rcvr(abbreviation):
        "Convenience method for getting a receiver object by abbreviation"
        return first(Receiver.objects.filter(abbreviation = abbreviation))

    #@staticmethod
    #def get_rcvr_by_name(name):
    #    "Convenience method for getting a receiver object by abbreviation"
    #    return first(Receiver.objects.filter(name = name))


class Receiver_Schedule(models.Model):
    receiver   = models.ForeignKey(Receiver)
    start_date = models.DateTimeField(null = True, blank = True)

    def __unicode__(self):
        return "%s on %s" % \
          ( self.receiver.name
          , self.start_date)

    class Meta:
        db_table = "receiver_schedule"

    @staticmethod
    def jsondict(schedule):
        jschedule = {}
        for d in schedule:
            jd = None if d is None else d.strftime("%m/%d/%Y")
            jschedule[jd] = [r.jsondict() for r in schedule[d]]
        return jschedule

    @staticmethod
    def jsondict_diff(schedule):
        jsonlist = []
        for day, up, down in schedule:
            jd = None if day is None else day.strftime("%m/%d/%Y")
            jup   = [r.jsondict() for r in up]
            jdown = [r.jsondict() for r in down]
            jsonlist.append(dict(day = jd, up = jup, down = jdown))
        return dict(diff_schedule = jsonlist)    

    @staticmethod
    def diff_schedule(schedule):
        """
        Given a schedule (produced from 'extract_schedule') produces a 
        logically equivalent schedule, but in the form of deltas: it shows
        for each listed date, what rcvrs are coming up and going down.
        """
        diff = []
        # sort the schedule
        sch = sorted(schedule.items())
        prevRcvrs = []
        for day, rcvrs in sch:
            up = [r for r in rcvrs if r not in prevRcvrs]
            down = [r for r in prevRcvrs if r not in rcvrs]
            prevRcvrs = rcvrs
            diff.append((day, up, down))
        return diff

    @staticmethod
    def extract_diff_schedule(startdate = None, days = None):
        sch = Receiver_Schedule.extract_schedule(startdate, days)
        return Receiver_Schedule.diff_schedule(sch)

    @staticmethod
    def extract_schedule(startdate = None, days = None):
        """
        Returns the entire receiver schedule starting at 'startdate' and
        ending 'days' after the 'startdate'.  The schedule is of the form:
        {
           start_date : [<receivers available>]
        }
        where start_date is a datetime object and [<receivers available>] is
        a list of Receiver objects.
        """
        startdate = startdate or datetime(2009, 10, 1, 0, 0, 0)
        schedule  = dict()
        prev      = Receiver_Schedule.previousDate(startdate)

        if prev is None:
            schedule[startdate] = [] # Empty schedule on/before this date
            prev = startdate

        if days is not None:
            enddate = startdate + timedelta(days = days)
            rs = Receiver_Schedule.objects.filter(
                                          start_date__gte = prev
                                                 ).filter(
                                          start_date__lte = enddate)
        else:
            rs = Receiver_Schedule.objects.filter(start_date__gte = prev)

        for s in rs:
            schedule.setdefault(s.start_date, []).append(s.receiver)

        return schedule

    @staticmethod
    def previousDate(date):
        try:
            prev = Receiver_Schedule.objects.filter(start_date__lt = date).order_by('-start_date')[0].start_date
        except IndexError:
            prev = None

        return prev
 
    @staticmethod
    def mostRecentDate(date):
        "Identical to previous date, but includes given date"
        try:
            prev = Receiver_Schedule.objects.filter(start_date__lte = date).order_by('-start_date')[0].start_date
        except IndexError:
            prev = None

        return prev

    @staticmethod
    def available_rcvrs_end_of_day(date):
        dt = Receiver_Schedule.mostRecentDate(date)
        return Receiver_Schedule.available_receivers(dt)

    @staticmethod
    def available_rcvrs_start_of_day(date):
        dt = Receiver_Schedule.previousDate(date)
        return Receiver_Schedule.available_receivers(dt)
        
    @staticmethod
    def available_receivers(date):
        "Returns rcvrs given rcvr change date"

        if date is not None:
            schd = Receiver_Schedule.objects.filter(start_date = date)
            rcvrs = [p.receiver for p in schd]
        else:
            rcvrs = []
        return rcvrs    

    @staticmethod
    def change_schedule(date, up, down, end_of_day = False):
        """
        Here we change the receiver schedule according to the given rcvrs
        that go up and down on the given date.  Uses extract schedule to 
        determine what rcvrs are up on this given date so that the rcvr 
        schedule can be changed using these deltas.  Raises errors if rcvrs are
        specified to go up that are already up, or down that aren't up.
        """
       
        # TBF: how to error check before creating new RS entry?
        # TBF: this code is twice as long as it should be - there
        # are patterns for up & down params that can be refactored out
        # TBF: won't remove the commented out prints until we know we're done

        # is this a new date?
        rss = Receiver_Schedule.objects.filter(start_date = date)
        if len(rss) == 0:
            # make a copy of the previous date
            prev = Receiver_Schedule.previousDate(date)
            prev_rs = Receiver_Schedule.objects.filter(start_date = prev)
            for p in prev_rs:
                rs = Receiver_Schedule(start_date = date
                                     , receiver   = p.receiver)
                rs.save()                     
            rss = Receiver_Schedule.objects.filter(start_date = date)

        # compare old diff to new diff (up and down params)
        diffs = Receiver_Schedule.extract_diff_schedule(startdate = date)
        dt, old_ups, old_downs = first([d for d in diffs if d[0] == date])
        #print "original diff: ", old_ups, old_downs

        # what used to go up, that no longer does?
        remove_ups = Set(old_ups).difference(Set(up))
        # what is going up that didn't before?
        add_ups = Set(up).difference(Set(old_ups))
        #print "UP Sets: ", remove_ups, add_ups

        # what used to go down, that no longer does?
        remove_downs = Set(old_downs).difference(Set(down))
        # what is going down that didn't before?
        add_downs = Set(down).difference(Set(old_downs))
        #print "DOWN Sets: ", remove_downs, add_downs

        # convert the sets to two lists of rcvrs: ups & downs
        ups = [u for u in add_ups]
        for d in remove_downs:
            if d not in ups:
                ups.append(d)
        #print "UP list: ", ups        
        downs = [d for d in add_downs]
        for u in remove_ups:
            if u not in downs:
                downs.append(u)
        #print "DOWN list: ", downs        


        # TBF: should we even error check?
        #for u in up:
        #    if u in available:
        #        return (False, "Receiver %s is already up on %s" % (u, date))
        #for d in down:
        #    if d not in available:
        #        return (False
        #        , "Receiver %s cannot come down on %s, is not up." % (d, date))

 
        # now alter the subsequent dates on the schedule:
        schedule = Receiver_Schedule.extract_schedule(date)
        dates = sorted(schedule.keys())
        # remove the rcvr(s) we just took down from all subsequent dates, 
        # until they dissappear on their own
        for d in downs:
            #print "d in down: ", d
            for dt in dates:
                if dt >= date:
                    #print "down schd date: ", dt
                    #, [r.abbreviation for r in schedule[dt]]
                    if d in schedule[dt]:
                        # shouldn't be there anymore!
                        gone =Receiver_Schedule.objects.filter(start_date = dt
                                                             , receiver = d)
                        for g in gone:
                            #print "deleting: ", g
                            g.delete()
                    else:
                        break
        # add the rcvr(s) we just put up to all subsequent dates, 
        # until they show up on their own
        for u in ups:
            #print "u in up: ", u
            for dt in dates:
                if dt >= date:
                    #print "up schd date: ", dt
                    #, [r.abbreviation for r in schedule[dt]]
                    if u not in schedule[dt]:
                        # should be there now!
                        new = Receiver_Schedule(start_date = dt, receiver = u)
                        new.save()
                        #print "new: ", new
                    else:
                        break

        # return success 
        return (True, None)

    @staticmethod
    def delete_date(date):
        "Remove all entries for the given date, and change subsequent schedule"
 
        # first check that this date is in the schedule
        rs = Receiver_Schedule.objects.filter(start_date = date)
        if len(rs) == 0:
            return (False, "Date is not in Receiver Schedule: %s" % date)

        # we first reconcile the schedule to this change by reversing all
        # the changes that were meant to happen on this day:
        diff_schedule = Receiver_Schedule.extract_diff_schedule(startdate = date)
        day, ups, downs = first([d for d in diff_schedule if d[0] == date])
        
        # reverse it!
        s, msg = Receiver_Schedule.change_schedule(day, downs, ups, end_of_day = True)
        if not s:
            return (False, msg)

        # now we can clean up
        rs = Receiver_Schedule.objects.filter(start_date = date)
        for r in rs:
            r.delete()

        return (True, None)    

    @staticmethod
    def shift_date(from_date, to_date):
        "Move all entries for the given date to a new date"

        # make sure the dates given are valid: you aren't allowed to shift
        # a date beyond the neighboring dates
        # NOTE: ensure you get all dates you need by explicity starting way back
        start = from_date - timedelta(days = 365)
        schedule = Receiver_Schedule.extract_schedule(startdate = start)
        dates = sorted(schedule.keys())
        if from_date not in dates:
            return (False, "Original date not in Receiver Schedule")
        from_index = dates.index(from_date)
        prev_date = dates[from_index-1] if from_index != 0 else None
        next_date = dates[from_index+1] if from_index != len(dates)-1 else None
        if prev_date is None or next_date is None or to_date >= next_date or to_date <= prev_date:
            return (False, "Cannot shift date to or past other dates")

        # we must be clear to shift the date    
        rs = Receiver_Schedule.objects.filter(start_date = from_date)
        for r in rs:
            r.start_date = to_date
            r.save()
        
        return (True, None)
        
class Parameter(models.Model):
    name = models.CharField(max_length = 64)
    type = models.CharField(max_length = 32)

    def __unicode__(self):
        return "%s : %s" % (self.name, self.type)

    class Meta:
        db_table = "parameters"

class Status(models.Model):
    enabled    = models.BooleanField()
    authorized = models.BooleanField()
    complete   = models.BooleanField()
    backup     = models.BooleanField()

    def __unicode__(self):
        return "(%d) e: %s; a: %s; c: %s; b: %s" % \
            (self.id, self.enabled, self.authorized, self.complete, self.backup) 
   
    class Meta:
        db_table = "status"
    
class Sesshun(models.Model):
    
    project            = models.ForeignKey(Project)
    session_type       = models.ForeignKey(Session_Type)
    observing_type     = models.ForeignKey(Observing_Type)
    allotment          = models.ForeignKey(Allotment)
    status             = models.ForeignKey(Status)
    original_id        = models.IntegerField(null = True, blank = True)
    name               = models.CharField(null = True
                                        , max_length = 64
                                        , blank = True)
    frequency          = models.FloatField(null = True, help_text = "GHz", blank = True)
    max_duration       = models.FloatField(null = True, help_text = "Hours", blank = True)
    min_duration       = models.FloatField(null = True, help_text = "Hours", blank = True)
    time_between       = models.FloatField(null = True, help_text = "Hours", blank = True)
    accounting_notes   = models.TextField(null = True, blank = True)
    notes              = models.TextField(null = True, blank = True)

    restrictions = "Unrestricted" # TBF Do we still need restrictions?

    base_url = "/sesshuns/sesshun/"

    def __unicode__(self):
        return "(%d) %s : %5.2f GHz, %5.2f Hrs, Rcvrs: %s, status: %s" % (
                  self.id
                , self.name if self.name is not None else ""
                , float(self.frequency) if self.frequency is not None else float(0.0)
                , float(self.allotment.total_time)
                      if self.allotment.total_time is not None else float(0.0)
                , self.receiver_list()
                , self.status)

    def get_absolute_url(self):
        return "/sesshuns/sesshun/%i/" % self.id

    def receiver_list(self):
        "Returns a string representation of the rcvr logic."
        return " AND ".join([rg.__str__() for rg in self.receiver_group_set.all()])

    def receiver_list_simple(self):
        "Returns a string representation of the rcvr logic, simplified"
        # ignore rcvr groups that have no rcvrs!  TBF: shouldn't happen!
        rgs = [ rg for rg in self.receiver_group_set.all() if len(rg.receivers.all()) != 0]
        if len(rgs) == 1:
            # no parens needed
            ls = " OR ".join([r.abbreviation for r in rgs[0].receivers.all()])
        else:
            # we can't simplify this anymore
            ls = self.receiver_list()
        return ls

    def rcvrs_specified(self):
        "Returns an array of rcvrs for this sesshun, w/ out their relations"
        # For use in recreating Carl's reports
        rcvrs = []
        for rg in self.receiver_group_set.all():
            rs = [r.abbreviation for r in rg.receivers.all()]
            for r in rs:
                if r not in rcvrs:
                    rcvrs.append(r)
        return rcvrs        

    def grade(self):
        return self.allotment.grade

    def num_rcvr_groups(self):
        return len(self.receiver_group_set.all())

    def schedulable(self):
        "A simple check for all explicit flags"
        return (self.status.enabled) and \
               (self.status.authorized) and \
               (not self.status.complete) and \
               (not self.project.complete)

    def delete(self):
        self.allotment.delete()
        super(Sesshun, self).delete()

    def set_base_fields(self, fdata):
        fsestype = fdata.get("type", "open")
        fobstype = fdata.get("science", "testing")
        proj_code = fdata.get("pcode", "GBT09A-001")

        p  = first(Project.objects.filter(pcode = proj_code).all()
                 , Project.objects.all()[0])
        st = first(Session_Type.objects.filter(type = fsestype).all()
                 , Session_Type.objects.all()[0])
        ot = first(Observing_Type.objects.filter(type = fobstype).all()
                 , Observing_Type.objects.all()[0])

        self.project          = p
        self.session_type     = st
        self.observing_type   = ot
        self.original_id      = \
            self.get_field(fdata, "orig_ID", None, lambda x: int(float(x)))
        self.name             = fdata.get("name", None)
        self.frequency        = fdata.get("freq", None)
        self.max_duration     = TimeAgent.rndHr2Qtr(float(fdata.get("req_max", 12.0)))
        self.min_duration     = TimeAgent.rndHr2Qtr(float(fdata.get("req_min",  3.0)))
        self.time_between     = fdata.get("between", None)

    def get_field(self, fdata, key, defaultValue, cast):
        "Some values from the JSON dict we know we need to type cast"
        value = fdata.get(key, defaultValue)
        if cast != bool:
            return value if value is None else cast(value)
        else:
            return value == "true"

    def init_from_post(self, fdata):
        self.set_base_fields(fdata)

        allot = Allotment(psc_time          = fdata.get("PSC_time", 0.0)
                        , total_time        = fdata.get("total_time", 0.0)
                        , max_semester_time = fdata.get("sem_time", 0.0)
                        , grade             = fdata.get("grade", 4.0)
                          )
        allot.save()
        self.allotment        = allot

        status = Status(
                   enabled    = self.get_field(fdata, "enabled", True, bool)
                 , authorized = self.get_field(fdata, "authorized", True, bool)
                 , complete   = self.get_field(fdata, "complete", True, bool) 
                 , backup     = self.get_field(fdata, "backup", True, bool) 
                        )
        status.save()
        self.status = status
        self.save()
        
        proposition = fdata.get("receiver")
        self.save_receivers(proposition)
        
        system = first(System.objects.filter(name = "J2000").all()
                     , System.objects.all()[0])

        v_axis = fdata.get("source_v", None)
        h_axis = fdata.get("source_h", None)
        
        target = Target(session    = self
                      , system     = system
                      , source     = fdata.get("source", None)
                      , vertical   = v_axis
                      , horizontal = h_axis
                        )
        target.save()
        self.save()

    def save_receivers(self, proposition):
        abbreviations = [r.abbreviation for r in Receiver.objects.all()]
        # TBF catch errors and report to user
        rc = ReceiverCompile(abbreviations)
        ands = rc.normalize(proposition)
        for ors in ands:
            rg = Receiver_Group(session = self)
            rg.save()
            for rcvr in ors:
                rcvrId = Receiver.objects.filter(abbreviation = rcvr)[0]
                rg.receivers.add(rcvrId)
                rg.save()

    def update_from_post(self, fdata):
        self.set_base_fields(fdata)
        self.save()

        self.allotment.psc_time          = fdata.get("PSC_time", 0.0)
        self.allotment.total_time        = fdata.get("total_time", 0.0)
        self.allotment.max_semester_time = fdata.get("sem_time", 0.0)
        self.allotment.grade             = fdata.get("grade", 4.0)
        self.allotment.save()
        self.save()

        self.status.enabled    = self.get_field(fdata, "enabled", True, bool) 
        self.status.authorized = self.get_field(fdata, "authorized", True, bool)
        self.status.complete   = self.get_field(fdata, "complete", True, bool) 
        self.status.backup     = self.get_field(fdata, "backup", True, bool) 
        self.status.save()
        self.save()

        self.update_bool_obs_param(fdata, "transit", "Transit", self.transit())
        self.update_bool_obs_param(fdata, "nighttime", "Night-time Flag", \
            self.nighttime())
        self.update_lst_exclusion(fdata)    

        proposition = fdata.get("receiver", None)
        if proposition is not None:
            self.receiver_group_set.all().delete()
            self.save_receivers(proposition)

        system = first(System.objects.filter(name = "J2000").all()
                     , System.objects.all()[0])

        v_axis = fdata.get("source_v", None)
        h_axis = fdata.get("source_h", None)

        t            = first(self.target_set.all())
        t.system     = system
        t.source     = fdata.get("source", None)
        t.vertical   = v_axis if v_axis is not None else t.vertical
        t.horizontal = h_axis if h_axis is not None else t.horizontal
        t.save()

        self.save()

    def update_bool_obs_param(self, fdata, json_name, name, old_value):
        """
        Generic method for taking a json dict and converting its given
        boolean field into a boolean observing parameter.
        """

        new_value = self.get_field(fdata, json_name, False, bool)
        tp = Parameter.objects.filter(name=name)[0]
        if old_value is None:
            if new_value:
                obs_param =  Observing_Parameter(session = self
                                               , parameter = tp
                                               , boolean_value = True
                                                )
                obs_param.save()
        else:
            obs_param = self.observing_parameter_set.filter(parameter=tp)[0]
            if new_value:
                obs_param.boolean_value = True
                obs_param.save()
            else:
                obs_param.delete()

    def update_lst_exclusion(self, fdata):
        """
        Converts the json representation of the LST exclude flag
        to the model representation.
        """
        lowParam = first(Parameter.objects.filter(name="LST Exclude Low"))
        hiParam  = first(Parameter.objects.filter(name="LST Exclude Hi"))
        
        # json dict string representation
        lst_ex_string = fdata.get("lst_ex", None)
        if lst_ex_string:
            # unwrap and get the float values
            lowStr, highStr = lst_ex_string.split("-")
            low = float(lowStr)
            high = float(highStr)
            assert low <= high

        # get the model's string representation
        current_lst_ex_string = self.get_LST_exclusion_string()

        if current_lst_ex_string == "":
            if lst_ex_string:
                # create a new LST Exlusion range
                obs_param =  Observing_Parameter(session = self
                                               , parameter = lowParam
                                               , float_value = low 
                                                )
                obs_param.save()
                obs_param =  Observing_Parameter(session = self
                                               , parameter = hiParam
                                               , float_value = high 
                                                )
                obs_param.save()
            else:
                # they are both none, nothing to do
                pass
        else:
            # get the current model representation (NOT the string) 
            lowObsParam = \
                first(self.observing_parameter_set.filter(parameter=lowParam))
            highObsParam = \
                first(self.observing_parameter_set.filter(parameter=hiParam))
            if lst_ex_string:
                lowObsParam.float_value = low
                lowObsParam.save()
                highObsParam.float_value = high
                highObsParam.save()
            else:
                lowObsParam.delete()
                highObsParam.delete()


    def get_LST_exclusion_string(self):
        "Converts pair of observing parameters into low-high string"
        lowParam = first(Parameter.objects.filter(name="LST Exclude Low"))
        hiParam  = first(Parameter.objects.filter(name="LST Exclude Hi"))
        lows  = self.observing_parameter_set.filter(parameter=lowParam)
        highs = self.observing_parameter_set.filter(parameter=hiParam)
        # make sure there aren't more then 1
        assert len(lows) < 2
        assert len(highs) < 2
        # make sure they make a pair, or none at all
        assert len(lows) == len(highs)
        # LST Exlcusion isn't set?
        if len(lows) == 0 and len(highs) == 0:
            return ""
        low = first(lows)
        high = first(highs)
        return "%.2f-%.2f" % (low.float_value, high.float_value)

    def get_ra_dec(self):
        target = first(self.target_set.all())
        if target is None:
            return None, None
        return target.vertical, target.horizontal

    def set_dec(self, new_dec):
        target = first(self.target_set.all())
        if target is None:
            return
        target.horizontal = new_dec
        target.save()

    def get_ignore_ha(self):
        # TBF:  Need specification of ignore_ha
        return False
        
    def get_receiver_req(self):
        nn = Receiver.get_abbreviations()
        rc = ReceiverCompile(nn)

        rcvrs = [[r.abbreviation \
                     for r in rg.receivers.all()] \
                         for rg in self.receiver_group_set.all()]
        return rc.denormalize(rcvrs)

    def get_ha_limit_blackouts(self, startdate, days):
        # TBF: Not complete or even correct yet.

        targets = [(t.horizontal, t.vertical) for t in self.target_set.all()]

        # startdate, days, self.frequency, targets
        #url       = "?"
        #blackouts = json.load(urlllib.urlopen(url))['blackouts']

        #return consolidate_events(find_intersections(blackouts))

    def getObservedTime(self):
        return TimeAccounting().getTime("observed", self)

    def getTimeBilled(self):
        return TimeAccounting().getTime("time_billed", self)

    def getTimeRemaining(self):
        return TimeAccounting().getTimeRemaining(self)

    def jsondict(self):
        d = {"id"         : self.id
           , "pcode"      : self.project.pcode
           , "type"       : self.session_type.type
           , "science"    : self.observing_type.type
           , "total_time" : self.allotment.total_time
           , "PSC_time"   : self.allotment.psc_time
           , "sem_time"   : self.allotment.max_semester_time
           , "remaining"  : self.getTimeRemaining()
           , "grade"      : self.allotment.grade
           , "orig_ID"    : self.original_id
           , "name"       : self.name
           , "freq"       : self.frequency
           , "req_max"    : self.max_duration
           , "req_min"    : self.min_duration
           , "between"    : self.time_between
           , "enabled"    : self.status.enabled
           , "authorized" : self.status.authorized
           , "complete"   : self.status.complete
           , "backup"     : self.status.backup
           , "transit"    : self.transit() or False
           , "nighttime"  : self.nighttime() or False
           , "lst_ex"     : self.get_LST_exclusion_string() or ""
           , "receiver"   : self.get_receiver_req()
            }

        target = first(self.target_set.all())
        if target is not None:
            d.update({"source"     : target.source
                    , "coord_mode" : target.system.name
                    , "source_h"   : target.horizontal
                    , "source_v"   : target.vertical
                      })

        #  Remove all None values
        for k, v in d.items():
            if v is None:
                _ = d.pop(k)

        return d

    def transit(self):
        """
        Returns True or False if has 'Transit' observing parameter,
        else None if not.
        """
        return self.has_bool_obs_param("Transit")

    def nighttime(self):
        """
        Returns True or False if has 'Night-time Flag' observing parameter,
        else None if not.
        """
        return self.has_bool_obs_param("Night-time Flag")

    def has_bool_obs_param(self, name):
        tp = Parameter.objects.filter(name=name)[0]
        top = self.observing_parameter_set.filter(parameter=tp)
        return top[0].boolean_value if top else None

    class Meta:
        db_table = "sessions"

class Receiver_Group(models.Model):
    session        = models.ForeignKey(Sesshun)
    receivers      = models.ManyToManyField(
                                  Receiver
                                , db_table = "receiver_groups_receivers")

    class Meta:
        db_table = "receiver_groups"

    def __unicode__(self):
        return "Rcvr Group for Sess: (%s): %s" % \
               (self.session.id,
                " ".join([r.abbreviation for r in self.receivers.all()]))

    def __str__(self):
        return "(%s)" % \
               " OR ".join([r.abbreviation for r in self.receivers.all()])

class Observing_Parameter(models.Model):
    session        = models.ForeignKey(Sesshun)
    parameter      = models.ForeignKey(Parameter)
    string_value   = models.CharField(null = True, max_length = 64, blank = True)
    integer_value  = models.IntegerField(null = True, blank = True)
    float_value    = models.FloatField(null = True, blank = True)
    boolean_value  = models.NullBooleanField(null = True, blank = True)
    datetime_value = models.DateTimeField(null = True, blank = True)

    class Meta:
        db_table = "observing_parameters"
        unique_together = ("session", "parameter")

    def value(self):
        if self.parameter.type == "string":
            return self.string_value
        elif self.parameter.type == "integer":
            return self.integer_value
        elif self.parameter.type == "float":
            return self.float_value
        elif self.parameter.type == "boolean":
            return self.boolean_value
        elif self.parameter.type == "datetime":
            return self.datetime_value
        else:
            return None

    def __unicode__(self):
        if self.string_value is not None:
            value = self.string_value
        elif self.integer_value is not None:
            value = str(self.integer_value)
        elif self.float_value is not None:
            value = str(self.float_value)
        elif self.boolean_value is not None:
            value = str(self.boolean_value)
        elif self.datetime_value is not None:
            value = str(self.datetime_value)
        else:
            value = ""
        return "%s with value %s for Sesshun (%d)" % (self.parameter
                                                    , value
                                                    , self.session.id)

class System(models.Model):
    name   = models.CharField(max_length = 32)
    v_unit = models.CharField(max_length = 32)
    h_unit = models.CharField(max_length = 32)

    def __unicode__(self):
        return "%s (%s, %s)" % (self.name, self.v_unit, self.h_unit)

    class Meta:
        db_table = "systems"

class Target(models.Model):
    session    = models.ForeignKey(Sesshun)
    system     = models.ForeignKey(System)
    source     = models.CharField(null = True, max_length = 32, blank = True)
    vertical   = models.FloatField(null = True, blank = True)
    horizontal = models.FloatField(null = True, blank = True)

    def __str__(self):
        return "%s at %s : %s" % (self.source
                                , self.horizontal
                                , self.vertical
                                  )

    def __unicode__(self):
        return "%s @ (%5.2f, %5.2f), Sys: %s" % \
            (self.source
           , float(self.horizontal)
           , float(self.vertical)
           , self.system)

    def get_horizontal(self):
        "Returns the horizontal component in sexigesimal form."
        if self.horizontal is None:
            return ""

        horz = TimeAgent.rad2hr(self.horizontal)
        mins = (horz - int(horz)) * 60
        secs = (mins - int(mins)) * 60
        if abs(secs - 60.) < 0.1:
            mins = int(mins) + 1
            if abs(mins - 60.) < 0.1:
                mins = 0.0
                horz = int(horz) + 1
            secs = 0.0
        return "%02i:%02i:%04.1f" % (int(horz), int(mins), secs)

    def get_vertical(self):
        if self.vertical is None:
            return ""

        degs = TimeAgent.rad2deg(self.vertical)

        if degs < 0:
            degs = abs(degs)
            sign = "-"
        else:
            sign = " "

        mins = (degs - int(degs)) * 60
        secs = (mins - int(mins)) * 60
        return "%s%02i:%02i:%04.1f" % (sign, int(degs), int(mins), secs)


    class Meta:
        db_table = "targets"

class Period_Accounting(models.Model):

    # XX notation is from Memo 11.2
    scheduled             = models.FloatField(help_text = "Hours") # SC
    not_billable          = models.FloatField(help_text = "Hours"  # NB
                                       , default = 0.0) 
    other_session_weather = models.FloatField(help_text = "Hours"  # OS1
                                       , default = 0.0) 
    other_session_rfi     = models.FloatField(help_text = "Hours"  # OS2
                                       , default = 0.0) 
    other_session_other   = models.FloatField(help_text = "Hours"  # OS3
                                       , default = 0.0) 
    lost_time_weather     = models.FloatField(help_text = "Hours"  # LT1
                                       , default = 0.0) 
    lost_time_rfi         = models.FloatField(help_text = "Hours"  # LT2
                                       , default = 0.0) 
    lost_time_other       = models.FloatField(help_text = "Hours"  # LT3
                                       , default = 0.0) 
    short_notice          = models.FloatField(help_text = "Hours"  # SN
                                       , default = 0.0) 
    description           = models.TextField(null = True, blank = True)

    class Meta:
        db_table = "periods_accounting"

    def __unicode__(self):
        return "Id (%d); SC:%5.2f OT:%5.2f NB:%5.2f OS:%5.2f LT:%5.2f SN:%5.2f" % \
            (self.id
           , float(self.scheduled)
           , float(self.observed())
           , float(self.not_billable)
           , float(self.other_session())
           , float(self.lost_time())
           , float(self.short_notice))

    def observed(self):
        "OT = SC - OS - LT"
        return self.scheduled - self.other_session() - self.lost_time()

    def other_session(self):
        "OS = OS1 + OS2 + OS3"
        return self.other_session_weather + \
               self.other_session_rfi + \
               self.other_session_other

    def lost_time(self):
        "LT = LT1 + LT2 + LT3"
        return self.lost_time_weather + \
               self.lost_time_rfi + \
               self.lost_time_other

    def time_billed(self):
        "TB = OT - NB"
        return self.observed() - self.not_billable

    def unaccounted_time(self):
        "UT=SC-OT-OS-LT; should always be zero."
        return self.scheduled - self.observed() - self.other_session() \
            - self.lost_time()

    def set_changed_time(self, reason, time):
        "Determines which field to assign the time to."
        self.__setattr__(reason, time)

    def get_time(self, name):
        # method or attribute?  TBF: how to REALLY do this?
        if self.__dict__.has_key(name):
            return self.__getattribute__(name)
        else:
            return self.__getattribute__(name)()

    def update_from_post(self, fdata):    
        fields = ['not_billable'
                , 'other_session_weather'
                , 'other_session_rfi'
                , 'other_session_other'
                , 'lost_time_weather'
                , 'lost_time_rfi'
                , 'lost_time_other'
                ]
        for field in fields:        
            value = fdata.get(field, None)
            if value is not None:
                self.set_changed_time(field, value)
        self.save()

    def jsondict(self):
        description = self.description if self.description is not None else ""
        return {"id"                    : self.id
              , "scheduled"             : self.scheduled
              , "observed"              : self.observed()
              , "not_billable"          : self.not_billable
              , "time_billed"           : self.time_billed()
              , "other_session"         : self.other_session()
              , "other_session_weather" : self.other_session_weather
              , "other_session_rfi"     : self.other_session_rfi
              , "other_session_other"   : self.other_session_other
              , "lost_time"             : self.lost_time()
              , "lost_time_weather"     : self.lost_time_weather
              , "lost_time_rfi"         : self.lost_time_rfi
              , "lost_time_other"       : self.lost_time_other
              , "unaccounted_time"      : self.unaccounted_time()
              , "short_notice"          : self.short_notice
              , "description"           : description}

    def validate(self):
        "Checks for invalid results, and returns info"
        for f in ["time_billed", "observed"]:
            if self.get_time(f) < 0.0:
                msg = "%s cannot be negative.  Please check times." % f
                return (False, msg)
        # valid!        
        return (True, None)        

    def of_interest(self):
        """
        Time Accounting fields can be used to see if a Period has undergone
        any kind of interesting change.
        """
        # check the description?  No, this could get filled out under
        # even normal circumstances.
        # Basically, by checking that the time_billed != scheduled time, 
        # we are checking for non-zero fields in other_session, time_lost,
        # etc.
        return self.time_billed() != self.scheduled or self.short_notice != 0.0

class Period_State(models.Model):
    name         = models.CharField(max_length = 32)
    abbreviation = models.CharField(max_length = 32)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = "period_states"

    def jsondict(self):
        return self.abbreviation

    @staticmethod
    def get_abbreviations():
        return [s.abbreviation for s in Period_State.objects.all()]

    @staticmethod
    def get_names():
        return [s.name for s in Period_State.objects.all()]

    @staticmethod
    def get_state(abbr):
        "Short hand for getting state by abbreviation"
        return first(Period_State.objects.filter(abbreviation = abbr))


class Period(models.Model):
    session    = models.ForeignKey(Sesshun)
    accounting = models.ForeignKey(Period_Accounting, null=True)
    state      = models.ForeignKey(Period_State, null=True)
    start      = models.DateTimeField(help_text = "yyyy-mm-dd hh:mm")
    duration   = models.FloatField(help_text = "Hours")
    score      = models.FloatField(null = True, editable=False, blank = True)
    forecast   = models.DateTimeField(null = True, editable=False, blank = True)
    backup     = models.BooleanField()
    moc_ack    = models.BooleanField(default = False)
    receivers  = models.ManyToManyField(Receiver, through = "Period_Receiver")

    class Meta:
        db_table = "periods"
    
    @staticmethod
    def create(*args, **kws):
        """
        Recomended way of 'overriding' the constructor.  Here we want to make
        sure that all new Periods init their rcvrs correctly.
        """
        p = Period(**kws)
        # don't save & init rcvrs unless you can
        if not kws.has_key("session"):
            # need the session first!
            return p
        p.save()
        p.init_rcvrs_from_session()
        return p
            
    def end(self):
        "The period ends at start + duration"
        return self.start + timedelta(hours = self.duration)

    def on_day(self, day):
        "Does this period ever take place on the specified day (a datetime)?"
        next_day = day + timedelta(days = 1)
        return (self.end() > day) and (self.start < next_day)

    def __unicode__(self):
        return "Period for Session (%d): %s for %5.2f Hrs (%s)" % \
            (self.session.id, self.start, self.duration, self.state.abbreviation)

    def __str__(self):
        return "%s: %s for %5.2f Hrs" % \
            (self.session.name, self.start, self.duration)

    def __cmp__(self, other):
        return cmp(self.start, other.start)

    def display_name(self):
        return self.__str__()

    def isDeleted(self):
        return self.state.abbreviation == 'D'

    def isScheduled(self):
        return self.state.abbreviation == 'S'

    def isPending(self):
        return self.state.abbreviation == 'P'

    def isCompleted(self):
        return self.state.abbreviation == 'C'

    def init_from_post(self, fdata, tz):
        self.from_post(fdata, tz)

    def update_from_post(self, fdata, tz):
        self.from_post(fdata, tz)
        # TBF: should we do this?
        if self.accounting is not None:
            self.accounting.update_from_post(fdata)

    def from_post(self, fdata, tz):

        handle = fdata.get("handle", "")
        if handle:
            self.session = self.handle2session(handle)
        else:
            try:
                maintenance = first(Project.objects.filter(pcode='Maintenance'))
                self.session = first(Sesshun.objects.filter(project=maintenance))
            except:
                self.session  = Sesshun.objects.get(id=fdata.get("session", 1))
        now           = dt2str(TimeAgent.quarter(datetime.utcnow()))
        date          = fdata.get("date", None)
        time          = fdata.get("time", "00:00")
        if date is None:
            self.start = now
        else:
            self.start = TimeAgent.quarter(strStr2dt(date, time + ':00'))
            if tz == 'ET':
                self.start = TimeAgent.est2utc(self.start)
        self.duration = TimeAgent.rndHr2Qtr(float(fdata.get("duration", "0.0")))
        self.score    = 0.0
        self.forecast = TimeAgent.quarter(datetime.utcnow())
        self.backup   = True if fdata.get("backup", None) == 'true' else False
        stateAbbr = fdata.get("state", "P")
        self.state = first(Period_State.objects.filter(abbreviation=stateAbbr))
        self.moc_ack = fdata.get("moc_ack", self.moc_ack)

        # how to initialize scheduled time? when they get published!
        # so, only create an accounting object if it needs it.
        if self.accounting is None:
            pa = Period_Accounting(scheduled = 0.0)
            pa.save()
            self.accounting = pa

        self.save()

        # now that we have an id (from saving), we can specify the relation
        # between this period and assocaited rcvrs
        self.update_rcvrs_from_post(fdata)

        # rescore! TBF: do we *always* do this?
        ScorePeriod().run(self.id)

    def update_rcvrs_from_post(self, fdata):

        # clear them out
        rps = Period_Receiver.objects.filter(period = self)
        for rp in rps:
            rp.delete()

        # insert the new ones: what are they?
        rcvrStr = fdata.get("receivers", "")
        if rcvrStr == "":
            # use the sessions receivers - this will happen on init
            if self.session is not None:
                rcvrAbbrs = self.session.rcvrs_specified()
            else:
                rcvrAbbrs = []
        else:    
            rcvrAbbrs = rcvrStr.split(",")

        # now that we have their names, put them in the DB    
        for r in rcvrAbbrs:
            rcvr = first(Receiver.objects.filter(abbreviation = r.strip()))
            if rcvr is not None:
                rp = Period_Receiver(receiver = rcvr, period = self)
                rp.save()
            
    def init_rcvrs_from_session(self):
        "Use the session's rcvrs for the ones associated w/ this period."
        if self.session is None:
            return
        rcvrAbbrs = self.session.rcvrs_specified()
        for r in rcvrAbbrs:
            rcvr = first(Receiver.objects.filter(abbreviation = r.strip()))
            if rcvr is not None:
                rp = Period_Receiver(receiver = rcvr, period = self)
                rp.save()


    def handle2session(self, h):
        n, p = h.rsplit('(', 1)
        name = n.strip()
        pcode, _ = p.split(')', 1)
        return Sesshun.objects.filter(project__pcode__exact=pcode).get(name=name)

    def toHandle(self):
        if self.session.original_id is None:
            original_id = ""
        else:
            original_id = str(self.session.original_id)
        return "%s (%s) %s" % (self.session.name
                             , self.session.project.pcode
                             , original_id)

    def eventjson(self, id):
        end = self.start + timedelta(hours = self.duration)

        return {
                "id"   : id
              , "title": "".join(["Observing ", self.session.name])
              , "start": self.start.isoformat()
              , "end"  : end.isoformat()
        }

    def jsondict(self, tz):
        start = self.start if tz == 'UTC' else TimeAgent.utc2est(self.start)
        w = self.get_window()
        js =   {"id"           : self.id
              , "session"      : self.session.jsondict()
              , "handle"       : self.toHandle()
              , "stype"        : self.session.session_type.type[0].swapcase()
              , "date"         : d2str(start)
              , "time"         : t2str(start)
              , "lst"          : str(TimeAgent.dt2tlst(self.start))
              , "duration"     : self.duration
              , "score"        : self.score
              , "forecast"     : dt2str(self.forecast)
              , "backup"       : self.backup
              , "moc_ack"      : self.moc_ack
              , "state"        : self.state.abbreviation
              , "windowed"     : True if w is not None else False
              , "wdefault"     : self.is_windowed_default() \
                                     if w is not None else None
              , "wstart"       : d2str(w.start_date) if w is not None else None
              , "wend"         : d2str(w.last_date()) if w is not None else None
              , "receivers"    : self.get_rcvrs_json()
                }
        # include the accounting but keep the dict flat
        if self.accounting is not None:
            accounting_js = self.accounting.jsondict()
            # make sure the final jsondict has only one 'id'
            accounting_id = accounting_js.pop('id')
            accounting_js.update({'accounting_id' : accounting_id})
            js.update(accounting_js)
        return js

    def get_rcvr_ranges(self):
        ranges = ["%5.2f - %5.2f".strip() % (r.freq_low, r.freq_hi) for r in self.receivers.all()]
        return ", ".join(ranges)

    def receiver_list(self):
        return self.get_rcvrs_json()

    def get_rcvrs_json(self):
        rcvrs = [r.abbreviation for r in self.receivers.all()]
        return ", ".join(rcvrs)

    def moc_met(self):
        """
        Returns a Boolean indicated if MOC are met (True) or not (False).
        Only bothers to calculate MOC for open and windowed sessions whose
        end time is not already past.
        """
        # TBF: When correctly calculating MOC for < 2 GHz observations,
        #      remove this hack.
        if self.session.frequency <= 2.:
            return True

        if self.session.session_type.type not in ("open", "windowed") or \
           self.end() < datetime.utcnow():
            return True

        url = ANTIOCH_SERVER_URL + \
              "/moc?session_id=" + \
              `self.session.id` + \
              "&start=" + \
              self.start.isoformat().replace("T", "+").replace(":", "%3A")
        try:
            antioch_cnn = urllib2.build_opener().open(url)
            moc = json.loads(antioch_cnn.read(0x4000))['moc']
        except:
            moc = True

        return moc

    def has_required_receivers(self):

        # Find all the required receiver sets for this period and schedule.
        # E.g. for one session:
        #     [[a, b, c], [x, y, z]] = (a OR b OR c) AND (x OR y OR z)
        required = [self.session.receiver_group_set.all()]
        if required == []:
            return False # No receivers, problem!

        schedule = Receiver_Schedule.extract_schedule(self.start, 0)
        if schedule == {}:
            return False # no schedule, no required rcvrs!
        # should return a single date w/ rcvr list
        items = schedule.items()
        assert len(items) == 1
        dt, receivers = items[0]

        receivers = Set(receivers)
        if not any([all([Set(g.receivers.all()).intersection(receivers) \
                        for g in set]) for set in required]):
            # No receivers available. 
            return False
        else:
            return True

    def move_to_deleted_state(self):
        "all in the name"
        self.state = Period_State.get_state("D")
        self.save()

    def move_to_scheduled_state(self):
        "worker for publish method: pending -> scheduled, and init time accnt."
        if self.state.abbreviation == "P":
            self.state = first(Period_State.objects.filter(abbreviation = 'S'))
            self.accounting.scheduled = self.duration
            self.accounting.save()
            self.save()

    def publish(self):
        "pending state -> scheduled state: and init the time accounting"
        # NOTE: it would be ideal to 'publish' a period's associated
        # window (reconcile it, really).  But we haven't been able to
        # get that to work properly, so windowed periods must be handled
        # elsewhere when publishing.
        if not self.is_windowed():
            if self.state.abbreviation == 'P':
                self.move_to_scheduled_state()


    def delete(self):
        "Keep non-pending periods from being deleted."
        if self.state.abbreviation != 'P':
            self.move_to_deleted_state()
        else:
            models.Model.delete(self)  # pending can really get removed!

    def remove(self):
        "A backdoor method for really deleting!"
        models.Model.delete(self)

    def is_windowed(self):
        return self.session.session_type.type == "windowed"

    def has_valid_windows(self):
        """
        If a period belongs to a Windowed Session, then it should be assigned
        to a Window as either a 'default_period' or a 'period'
        """
        if self.session.session_type.type != "windowed":
            return False # who cares?

        default_windows = self.default_window.all()
        windows = self.window.all()

        # neither one of these should point to more then one window
        if len(default_windows) > 1 or len(windows) > 1:
            return False

        # this period should be assigned to at least one window
        if len(default_windows) == 0 and len(windows) == 0:
            return False
        
        return True

    def get_default_window(self):
        "Get the window this period is a default period for."
        if self.is_windowed() and self.has_valid_windows():
            return first(self.default_window.all())
        else:
            return None

    def get_window(self):
        "Get the window this period is either default or choosen period for."
        if self.is_windowed() and self.has_valid_windows():
            if len(self.default_window.all()) == 1:
                return first(self.default_window.all())
            else:
                return first(self.window.all())
        else:
            return None

    def is_windowed_default(self):
        "Is this period the default period for a window? If not, is the choosen"
        # assume error checking done before hand
        # self.is_windowed() and self.has_valid_windows()
        if len(self.default_window.all()) == 1:
            return True
        else:
            return False

    @staticmethod
    def get_periods(start, duration, ignore_deleted = True):
        "Returns all periods that overlap given time interval (start, minutes)"
        end = start + timedelta(minutes = duration)
        # there is no Period.end in the database, so, first cast a wide net.
        # we can do this because periods won't last more then 16 hours ...
        beforeStart = start - timedelta(days = 1)
        afterEnd    = end   + timedelta(days = 1)
        some = Period.objects.filter(start__gt = beforeStart
                                   , start__lt = afterEnd).order_by('start')
        # now widdle this down to just the periods that overlap  
        ps = [p for p in some if (p.start >= start and p.end() <= end) \
                              or (p.start <= start and p.end() > start) \
                              or (p.start < end    and p.end() >= end)]
        if ignore_deleted:                      
            ps = [p for p in ps if p.state.abbreviation != 'D']
        return ps
          
        
    @staticmethod    
    def in_time_range(begin, end, ignore_deleted = True):
        """
        Returns all periods in a time range, taking into account that periods
        can overlap into the first day.
        """
        # TBF: why doesn't ps.query.group_by = ['start'] work?
        day_before = begin - timedelta(days = 1)
        ps = Period.objects.filter(start__gt = day_before
                                 , start__lt = end).order_by('start')
        if ignore_deleted:                      
            ps = [p for p in ps if p.state.abbreviation != 'D']
        return ps

    @staticmethod
    def publish_periods(start, duration):
        """
        Due to problems we encountered with the relationship between
        periods and windows in the DB, we can't reconcile windows
        from within a period's publish method, we must take this approach.
        """

        periods = Period.get_periods(start, duration)

        # publishing moves any period whose state is Pending to Scheduled,
        # and initializes time accounting (scheduled == period duration).
        wids = []
        for p in periods:
            if p.session.session_type.type != 'windowed':
                p.publish()
                p.save()
            else:
                # don't publish this period, instead, find out what window
                # it belongs to so we can reconcile it latter.
                # what window does it belong to?
                w = p.get_window()
                if w is not None and w.id not in wids:
                    wids.append(w.id)

        # now reconcile any windows
        for wid in wids:
            window = first(Window.objects.filter(id = wid))
            window.reconcile()
            window.save()
    
class Period_Receiver(models.Model):
    period = models.ForeignKey(Period)
    receiver = models.ForeignKey(Receiver)

    class Meta:
        db_table = "periods_receivers"

# TBF: temporary table/class for scheduling just 09B.  We can safely
# dispose of this after 09B is complete.  Delete Me!
class Project_Blackout_09B(models.Model):
    project      = models.ForeignKey(Project)
    requester    = models.ForeignKey(User)
    start_date   = models.DateTimeField(null = True, blank = True)
    end_date     = models.DateTimeField(null = True, blank = True)
    description  = models.CharField(null = True, max_length = 512, blank = True)

    def __unicode__(self):
        return "Blackout for %s: %s - %s" % (self.project.pcode, self.start_date, self.end_date)

    class Meta:
        # Note: using upper case B at the end of this name causes
        # problems with postrgreSQL
        db_table = "project_blackouts_09b"

class Window(models.Model):
    session  = models.ForeignKey(Sesshun)
    default_period = models.ForeignKey(Period, related_name = "default_window", null = True, blank = True)
    period = models.ForeignKey(Period, related_name = "window", null = True, blank = True)
    start_date =  models.DateField(help_text = "yyyy-mm-dd hh:mm:ss")
    duration   = models.IntegerField(help_text = "Days")

    def __unicode__(self):
        return "Window (%d) for Sess (%d)" % \
            (self.id
           , self.session.id)

    def __str__(self):
        name = self.session.name if self.session is not None else "None"
        #default_period = self.default_period.__str__() if self.default_period is not None else "None"
        return "Window for %s, from %s for %d days, default: %s, period: %s" % \
            (name
           , self.start_date.strftime("%Y-%m-%d")
           , self.duration
           , self.default_period
           , self.period)

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

    # TBF: is this correct?
    def is_published(self):
        return self.default_period and self.default_period.abbreviaton in ['S', 'C']

    # TBF: refactor this to use the state method
    def is_scheduled_or_completed(self):
        period = self.period if self.period is not None and self.period.state.abbreviation in ['S', 'C'] else None
        if period is None:
            period = self.default_period if self.default_period is not None and self.default_period.state.abbreviation in ['S', 'C'] else None
        return period

    ##################################################################
    # state will return the state of the window, or none if the window
    # is not in a legal state.  The truth table is as follows, where
    # 'D' is deleted, 'P' pending, 'S' scheduled, and 'C' completed:
    #
    #    period                default_period         state
    #    None                  P                      P
    #    S                     D                      S
    #    S                     S                      S
    #    C                     C                      C
    #    C                     D                      C
    #    P                     P                      P*
    #
    # Any other combinaton returns None
    #
    # * This is legal, but Antioch won't accept a window in this state
    ##################################################################
    def state(self):
        "A Windows state is a combination of the state's of it's Periods"

        # TBF: need to check that these make sense
        deleted   = Period_State.get_state("D")
        pending   = Period_State.get_state("P")
        scheduled = Period_State.get_state("S")
        completed = Period_State.get_state("C")

        if self.default_period:
            if self.default_period.isPending() and self.period is None:
                # initial state windows are in when created
                return pending
            else:
                if self.period:
                    if self.default_period.isCompleted() and self.period.isCompleted():
                        return completed
                    if self.default_period.isPending() and self.period.isPending():
                        return pending
                    if self.default_period.isDeleted() and self.period.isScheduled():
                        return scheduled
                    if self.default_period.isScheduled() and self.period.isScheduled():
                        return scheduled
                    if self.default_period.isDeleted() and self.period.isCompleted():
                        return completed
                # We have a default period, it is not pending, and
                # none of the other conditions is met.
                return None
        else:
            # No default period!
            return None

    state.short_description = 'Window State'

    def dual_pending_state(self):
        """
        Returns true if both period and default_period exist and are
        in a Pending state
        """
        if self.default_period and self.period:
            if self.default_period.isPending() and self.period.isPending():
                return True
        return False

    dual_pending_state.short_description = 'Window special pending state'

    def reconcile(self):
        """
        Similar to publishing a period, this moves a window from an inital,
        or transitory state, to a final scheduled state.
        Move the default period to deleted, and publish the scheduled period.
        """

        deleted   = Period_State.get_state("D")
        pending   = Period_State.get_state("P")
        scheduled = Period_State.get_state("S")
        
        # raise an error?
        assert self.default_period is not None

        # if this has already been reconciled, or is in an invalid
        # state, don't do anything.
        state = self.state()
        if state is None or state == scheduled:
            return

        if self.period is not None:
            # use this period as the scheduled one!
            self.default_period.move_to_deleted_state()
            self.default_period.save()
            self.period.move_to_scheduled_state()
            self.period.save()
        else:
            # use the default period!
            self.default_period.move_to_scheduled_state()
            self.default_period.save()
            self.period = self.default_period
            self.period.save()

        self.save()    

    def jsondict(self):
        js = {  "id"             : self.id
              , "handle"         : self.toHandle()
              , "session"        : self.session.jsondict()
              , "start"          : self.start_date.strftime("%Y-%m-%d")
              , "end"            : self.end().strftime("%Y-%m-%d")
              , "duration"       : self.duration
              }
        # we need to do this so that the window explorer can work with
        # a 'flat' json dictionary
        self.add_period_json(js, "default", self.default_period)
        self.add_period_json(js, "choosen", self.period)
        return js    

    def add_period_json(self, jsondict, type, period):
        "Adss part of the given period's json to given json dict"

        if period is None:
            keys = ['date', 'time', 'duration', 'state', 'period']
            for k in keys:
                key = "%s_%s" % (type, k)
                jsondict[key] = None
        else:
            pjson = period.jsondict('UTC')
            jsondict["%s_%s" % (type, "date")] = pjson['date']
            jsondict["%s_%s" % (type, "time")] = pjson['time']
            jsondict["%s_%s" % (type, "duration")]   = pjson['duration']
            jsondict["%s_%s" % (type, "state")]      = pjson['state']

    def handle2session(self, h):
        n, p = h.rsplit('(', 1)
        name = n.strip()
        pcode, _ = p.split(')', 1)
        return Sesshun.objects.filter(project__pcode__exact=pcode).get(name=name)

    def toHandle(self):
        if self.session is None:
            return ""
        if self.session.original_id is None:
            original_id = ""
        else:
            original_id = str(self.session.original_id)
        return "%s (%s) %s" % (self.session.name
                             , self.session.project.pcode
                             , original_id)

    def init_from_post(self, fdata):
        self.from_post(fdata)

    def update_from_post(self, fdata):
        self.from_post(fdata)

    def from_post(self, fdata):

        # most likely, we'll be specifying sessions for windows in the same
        # manner as we do for periods
        handle = fdata.get("handle", "")
        if handle:
            self.session = self.handle2session(handle)
        else:
            try:
                maintenance = first(Project.objects.filter(pcode='Maintenance'))
                self.session = first(Sesshun.objects.filter(project=maintenance))
            except:
                self.session  = Sesshun.objects.get(id=fdata.get("session", 1))

         # get the date
        date = fdata.get("start", datetime.utcnow().strftime("%Y-%m-%d"))
        self.start_date = datetime.strptime(date, "%Y-%m-%d").date()

        # TBF: why is this going back and forth as a float?
        self.duration = int(float(fdata.get("duration", "1.0")))

        # we are working with a 'flat' dictionary that has only a few
        # of the specified fields for it's two periods.
        self.period_from_post(fdata, "default", self.session)
        self.period_from_post(fdata, "choosen", self.session)
       
        self.save()

    def period_from_post(self, fdata, type, sesshun):
        "Update or create a period for a window based on post data."

        try:
            dur = float(fdata.get("%s_%s" % (type, "duration"), None))
            duration = TimeAgent.rndHr2Qtr(dur)
            date = fdata.get("%s_%s" % (type, "date"), None)
            time = fdata.get("%s_%s" % (type, "time"), None)
            now           = dt2str(TimeAgent.quarter(datetime.utcnow()))
            if date is None:
                start = now
            else:
                start = TimeAgent.quarter(strStr2dt(date, time + ':00'))
        except:
            duration = None
            start = None

        # do we have a period of this type yet?
        if type == "default":
            p = self.default_period
        elif type == "choosen":
            p = self.period
        else:
            raise "unknown type"

        if p is None:
            # try to create it from given info
            if start is not None and duration is not None \
                and sesshun is not None:
               # create it! reuse the period code!
               p = Period.create()
               pfdata = dict(date = date
                           , time = time
                           , duration = duration
                           , handle = self.toHandle())
               p.init_from_post(pfdata, 'UTC')
               if type == "default":
                  self.default_period = p
                  self.default_period.save()

               elif type == "choosen":
                  self.period = p
                  self.period.save()
        else:
            # update it
            p.start = start
            p.duration = duration
            p.save()

    def eventjson(self, id):
        end = self.start_date + timedelta(days = self.duration)

        return {
                "id"   : id
              , "title": "".join(["Window ", self.session.name])
              , "start": self.start_date.isoformat()
              , "end"  : end.isoformat()
        }

    def assignPeriod(self, periodId, default):
        "Assign the given period to the default or choosen period"
        p = first(Period.objects.filter(id = periodId))
        if p is None:
            return
        if default:
            self.default_period = p
        else:
            self.period = p
        self.save()

    class Meta:
        db_table = "windows"

class Reservation(models.Model):
    user       = models.ForeignKey(User)
    start_date = models.DateTimeField(help_text = "yyyy-mm-dd hh:mm:ss")
    end_date   = models.DateTimeField(help_text = "yyyy-mm-dd hh:mm:ss")

    class Meta:
        db_table = "reservations"

def register_for_revision():
    register_model(Role)
    register_model(User, follow=['role'])
    register_model(Email, follow=['user'])
    register_model(Semester)
    register_model(Project_Type)
    register_model(Allotment)
    register_model(Project, follow=['semester', 'project_type', 'friend', 'allotments', 'investigator_set'])
    register_model(Project_Allotment, follow=['project', 'allotment'])
    register_model(Repeat)
    register_model(TimeZone)
    register_model(Blackout, follow=['user','repeat'] )
    register_model(Investigator)
    register_model(Session_Type)
    register_model(Observing_Type)
    register_model(Receiver)
    register_model(Receiver_Schedule)
    register_model(Parameter)
    register_model(Status)
    register_model(Sesshun, follow=['target_set','allotment'])
    register_model(Receiver_Group, follow=['receivers'])
    register_model(Observing_Parameter)
    register_model(System)
    register_model(Target)
    register_model(Period_Accounting)
    register_model(Period_State)
    register_model(Period, follow=['accounting', 'state', 'receivers'])
    register_model(Period_Receiver, follow=['period', 'receiver'])
    #Project_Blackout_09B
    register_model(Window)
    #Reservation

def register_model(model, follow = None):
    if not reversion.is_registered(model) and settings.USE_REVERSION:
        print "registering model with reversion: ", model
        if follow is None:
            reversion.register(model)
        else:
            reversion.register(model, follow = follow)

register_for_revision()    
