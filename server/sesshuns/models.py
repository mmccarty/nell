from datetime              import datetime
from django.db             import models
from django.http import QueryDict

from server.utilities import OpportunityGenerator, TimeAgent

def first(results, default = None):
    return default if len(results) == 0 else results[0]

class Semester(models.Model):
    semester = models.CharField(max_length = 64)

    class Meta:
        db_table = "semesters"

class Project_Type(models.Model):
    type = models.CharField(max_length = 64)

    class Meta:
        db_table = "project_types"

class Allotment(models.Model):
    psc_time          = models.FloatField()
    total_time        = models.FloatField()
    max_semester_time = models.FloatField()

    class Meta:
        db_table = "allotment"
        
class Project(models.Model):
    semester     = models.ForeignKey(Semester)
    project_type = models.ForeignKey(Project_Type)
    #allotment    = models.ForeignKey(Allotment)
    allotments   = models.ManyToManyField(Allotment)
    pcode        = models.CharField(max_length = 32)
    name         = models.CharField(max_length = 60)
    thesis       = models.BooleanField()
    complete     = models.BooleanField()
    ignore_grade = models.BooleanField()
    start_date   = models.DateTimeField(null = True)
    end_date     = models.DateTimeField(null = True)

    class Meta:
        db_table = "projects"

class Session_Type(models.Model):
    type = models.CharField(max_length = 64)

    class Meta:
        db_table = "session_types"

class Observing_Type(models.Model):
    type = models.CharField(max_length = 64)

    class Meta:
        db_table = "observing_types"

class Receiver(models.Model):
    name         = models.CharField(max_length = 32)
    abbreviation = models.CharField(max_length = 32)
    freq_low     = models.FloatField()
    freq_hi      = models.FloatField()

    class Meta:
        db_table = "receivers"

class Parameter(models.Model):
    name = models.CharField(max_length = 64)
    type = models.CharField(max_length = 32)

    class Meta:
        db_table = "parameters"

class Sesshun(models.Model):
    
    project            = models.ForeignKey(Project)
    session_type       = models.ForeignKey(Session_Type)
    observing_type     = models.ForeignKey(Observing_Type)
    allotment          = models.ForeignKey(Allotment)
    original_id        = models.IntegerField(null = True)
    name               = models.CharField(null = True
                                        , max_length = 64)
    frequency          = models.FloatField(null = True)
    max_duration       = models.FloatField(null = True)
    min_duration       = models.FloatField(null = True)
    time_between       = models.FloatField(null = True)
    grade              = models.FloatField(null = True)

    restrictions = "Unrestricted" # TBF Do we still need restrictions?

    def delete(self):
        self.allotment.delete()
        super(Sesshun, self).delete()

    def set_base_fields(self, fdata):
        fsestype = fdata.get("type", "open")
        fobstype = fdata.get("science", "testing")
        frcvr    = fdata.get("receiver", "Rcvr1_2")

        p  = first(Project.objects.filter(pcode = "GBT09A-001").all())
        st = first(Session_Type.objects.filter(type = fsestype).all()
                 , Session_Type.objects.all()[0])
        ot = first(Observing_Type.objects.filter(type = fobstype).all()
                 , Observing_Type.objects.all()[0])

        self.project          = p
        self.session_type     = st
        self.observing_type   = ot
        self.original_id      = fdata.get("orig_ID", None)
        self.name             = fdata.get("name", None)
        self.frequency        = fdata.get("freq", None)
        self.max_duration     = fdata.get("req_max", 8.0)
        self.min_duration     = fdata.get("req_min", 2.0)
        self.time_between     = fdata.get("between", None)

        # grade - UI deals w/ letters (A,B,C) - DB deals with floats
        self.grade            = \
            self.grade_abc_2_float(fdata.get("grade", None))


    def grade_abc_2_float(self, abc):
        grades = {'A' : 4.0, 'B' : 3.0, 'C' : 2.0}
        return grades.get(abc, None)

    def grade_float_2_abc(self, grade):
        grades = ['A', 'B', 'C']
        floats = [4.0, 3.0, 2.0]
        gradeLetter = 'C'
        for i in range(len(grades)):
            if grade >= (floats[i] - 10e-5):
                gradeLetter = grades[i]
                break
        return gradeLetter

    def init_from_post(self, fdata):
        self.set_base_fields(fdata)
        allot = Allotment(psc_time          = fdata.get("PSC_time", 0.0)
                        , total_time        = fdata.get("total_time", 0.0)
                        , max_semester_time = fdata.get("sem_time", 0.0)
                          )
        allot.save()
        self.allotment        = allot
        self.save()
        
        frcvr  = fdata.get("receiver", "Rcvr1_2")
        rcvr   = first(Receiver.objects.filter(name = frcvr).all()
                     , Receiver.objects.all()[0])
        rg     = Receiver_Group(session = self)
        rg.save()
        rg.receiver_group_receiver_set.add(rcvr)
        rg.save()
        
        status = Status(session    = self
                      , enabled    = fdata.get("enabled", True)
                      , authorized = fdata.get("authorized", True)
                      , complete   = fdata.get("complete", True)
                      , backup     = fdata.get("backup", True)
                        )
        status.save()

        system = first(System.objects.filter(name = "J2000").all()
                     , System.objects.all()[0])

        v_axis = fdata.get("v_axis", 2.0) #TBF
        h_axis = fdata.get("h_axis", 2.0) #TBF
        
        target = Target(session    = self
                      , system     = system
                      , source     = fdata.get("source", None)
                      , vertical   = v_axis
                      , horizontal = h_axis
                        )
        target.save()
        self.save()

    def update_from_post(self, fdata):
        self.set_base_fields(fdata)
        
        self.allotment.psc_time          = fdata.get("PSC_time", 0.0)
        self.allotment.total_time        = fdata.get("total_time", 0.0)
        self.allotment.max_semester_time = fdata.get("sem_time", 0.0)

        # TBF DO SOMETHING WITH RECEIVERS!

        self.status_set.get().enabled    = fdata.get("enabled", True)
        self.status_set.get().authorized = fdata.get("authorized", True)
        self.status_set.get().complete   = fdata.get("complete", True)
        self.status_set.get().backup     = fdata.get("backup", True)

        system = first(System.objects.filter(name = "J2000").all()
                     , System.objects.all()[0])

        v_axis = fdata.get("v_axis", 2.0) #TBF
        h_axis = fdata.get("h_axis", 2.0) #TBF

        self.target_set.get().system     = system
        self.target_set.get().source     = fdata.get("source", None)
        self.target_set.get().vertical   = v_axis
        self.target_set.get().horizontal = h_axis

        self.save()

    def get_ra_dec(self):
        target = first(self.target_set.all())
        if target is None:
            return None, None
        return target.vertical, target.horizontal

    def get_ignore_ha(self):
        # TBF:  Need specification of ignore_ha
        return False
        
    def get_receiver_req(self):
        return first(self.receiver_group_set.get().receivers.all())
        
    def jsondict(self):
        status = first(self.status_set.all())
        target = first(self.target_set.all())
        rcvr   = self.get_receiver_req()

        d = {"id"         : self.id
           , "proj_code"  : self.project.pcode
           , "type"       : self.session_type.type
           , "science"    : self.observing_type.type
           , "total_time" : self.allotment.total_time
           , "PSC_time"   : self.allotment.psc_time
           , "sem_time"   : self.allotment.max_semester_time
           , "orig_ID"    : self.original_id
           , "name"       : self.name
           , "freq"       : self.frequency
           , "req_max"    : self.max_duration
           , "req_min"    : self.min_duration
           , "between"    : self.time_between
             }

        # DB deals with floats, UI presents letters (A,B,C)
        if self.grade is not None:
            d.update({"grade" : self.grade_float_2_abc(self.grade)})

        if rcvr is not None:
            d.update({"receiver"   : rcvr.abbreviation})
            
        if status is not None:
            s_d = {"enabled"    : status.enabled
                 , "authorized" : status.authorized
                 , "complete"   : status.complete
                 , "backup"     : status.backup
                   }

        if target is not None:
            d.update({"source" : target.source})

        #  Remove all None values
        for k, v in d.items():
            if v is None:
                _ = d.pop(k)

        return d

    def hourAngleAtHorizon(self):
        "Returns the absolute hour angle in hours at the telescope limits."
        _, dec = self.get_ra_dec()
        lat = TimeAgent.GbtLatitudeInRadians()
        dec = TimeAgent.deg2rad(dec)
        za  = TimeAgent.deg2rad(85)

        # Are we looking at polaris or thereabouts?
        denominator = cos(lat)*cos(dec)
        if abs(denominator) <= 1e-3:
            return 12.0

        cosha = (cos(za) - sin(lat)*sin(dec))/denominator
        # Dropped below the horizon?
        if abs(cosha) >= 1:
            return 12.0
        ha = TimeAgent.rad2hr(acos(cosha))
        return abs(ha)

    class Meta:
        db_table = "sessions"

class Cadence(models.Model):
    session    = models.ForeignKey(Sesshun)
    start_date = models.DateTimeField(null = True)
    end_date   = models.DateTimeField(null = True)
    repeats    = models.IntegerField(null = True)
    intervals  = models.CharField(null = True, max_length = 64)

    class Meta:
        db_table = "cadences"

class Receiver_Group(models.Model):
    session        = models.ForeignKey(Sesshun)
    receivers      = models.ManyToManyField(Receiver
                                          , through = "Receiver_Group_Receiver")

    class Meta:
        db_table = "receiver_groups"

class Receiver_Group_Receiver(models.Model):
    group          = models.ForeignKey(Receiver_Group)
    receiver       = models.ForeignKey(Receiver)

    class Meta:
        db_table = "receiver_groups_receiver"

class Observing_Parameter(models.Model):
    session        = models.ForeignKey(Sesshun)
    parameter      = models.ForeignKey(Parameter)
    string_value   = models.CharField(null = True, max_length = 64)
    integer_value  = models.IntegerField(null = True)
    float_value    = models.FloatField(null = True)
    boolean_value  = models.BooleanField(null = True)
    datetime_value = models.DateTimeField(null = True)

    class Meta:
        db_table = "observing_parameters"
        unique_together = ("session", "parameter")

class Status(models.Model):
    session    = models.ForeignKey(Sesshun)
    enabled    = models.BooleanField()
    authorized = models.BooleanField()
    complete   = models.BooleanField()
    backup     = models.BooleanField()

    class Meta:
        db_table = "status"

class Window(models.Model):
    session  = models.ForeignKey(Sesshun)
    required = models.BooleanField()

    def init_from_post(self, fdata = QueryDict({})):
        self.required = fdata.get("required", False)
        self.save()
        start_time    = fdata.getlist("start_time")
        duration      = fdata.getlist("duration")
        for st, d in zip(start_time, duration):
            self.str2opportunity(st, d)

    def str2opportunity(self, start_time, duration):
        d, t      = start_time.split(' ')
        y, m, d   = map(int, d.split('-'))
        h, mm, ss = map(int, map(float, t.split(':')))
        st        = datetime(y, m, d, h, mm, ss)
        o = Opportunity(window = self
                      , start_time = st
                      , duration = float(duration))
        o.save()

    def update_from_post(self, fdata = QueryDict({})):
        for o in self.opportunity_set.all():
            o.delete()
        self.init_from_post(fdata)
        
    def jsondict(self, generate = False):
        windowed = first(Session_Type.objects.filter(type = 'windowed'))
        if self.session.session_type == windowed and generate:
            opportunities = self.gen_opportunities()
        else:
            opportunities = self.opportunity_set.all()
            
        return {"id"       : self.id
              , "required" : self.required
              , "opportunities" : [o.jsondict() for o in opportunities]
                }

    def gen_opportunities(self, now = None):
        w = first(self.opportunity_set.all())
        if w is None:
            return []

        now = datetime.utcnow() if now is None else now
        
        # Does the window already have one or more(!) sessions?
        # (Note if a session falls in the overlap of two
        # intersecting windows -- which should not be allowed
        # in any case -- then it satisfies both windows)
        # Note that the window start hour only applies to UTC windows,
        # the window itself starts at the beginning of the start date.
        #start = datetime(w.start_time.year, w.start_time.month, w.start_time.day)

        # TBF: Need to check to see if the window as already been satisfied.

        """
        limit = HourAngleLimit.query.filter(
            and_(
              HourAngleLimit.frequency ==
                               alloc.frequencyIndex(),
              HourAngleLimit.declination ==
                               alloc.declinationIndex()
                )).first()
        """
        limit = None
        ha_limit = int(limit.limit) if limit \
                   else int(round((
                            self.session.min_duration + 119) / 120))

        return OpportunityGenerator(now).generate(w, self.session, ha_limit)

    class Meta:
        db_table = "windows"

class Opportunity(models.Model):
    window     = models.ForeignKey(Window)
    start_time = models.DateTimeField()
    duration   = models.FloatField()

    def jsondict(self):
        return {"id"         : self.id
              , "start_time" : str(self.start_time)
              , "duration"   : self.duration
                }
    
    class Meta:
        db_table = "opportunities"

class System(models.Model):
    name   = models.CharField(max_length = 32)
    v_unit = models.CharField(max_length = 32)
    h_unit = models.CharField(max_length = 32)

    class Meta:
        db_table = "systems"

class Target(models.Model):
    session    = models.ForeignKey(Sesshun)
    system     = models.ForeignKey(System)
    source     = models.CharField(null = True, max_length = 32)
    vertical   = models.FloatField()
    horizontal = models.FloatField()

    class Meta:
        db_table = "targets"

