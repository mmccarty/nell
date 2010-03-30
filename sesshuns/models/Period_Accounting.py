from django.db  import models

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
        db_table  = "periods_accounting"
        app_label = "sesshuns"

    def __unicode__(self):
        return "Id (%d); SC:%5.2f OT:%5.2f NB:%5.2f OS:%5.2f LT:%5.2f SN:%5.2f" % \
            (self.id
           , self.scheduled
           , self.observed()
           , self.not_billable
           , self.other_session()
           , self.lost_time()
           , self.short_notice)

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

