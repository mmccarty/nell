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

from django.db                 import models

from Allotment    import Allotment
from Backend      import Backend
from Proposal     import Proposal
from Receiver     import Receiver
from SessionType  import SessionType
from Semester     import Semester
from SessionFlags import SessionFlags
from Source       import Source
from Target       import Target
from WeatherType  import WeatherType

from pht.utilities import *

class Session(models.Model):

    proposal                = models.ForeignKey(Proposal)
    sources                 = models.ManyToManyField(Source)
    receivers               = models.ManyToManyField(Receiver, related_name = 'sessions')
    backends                = models.ManyToManyField(Backend)
    allotment               = models.ForeignKey(Allotment, null = True)
    target                  = models.ForeignKey(Target, null = True)
    session_type            = models.ForeignKey(SessionType, null = True)
    weather_type            = models.ForeignKey(WeatherType, null = True)
    semester                = models.ForeignKey(Semester, null = True)
    grade                   = models.CharField(max_length = 20, null = True)
    flags                   = models.ForeignKey(SessionFlags, null = True)
    receivers_granted       = models.ManyToManyField(Receiver) 
    pst_session_id          = models.IntegerField()
    name                    = models.CharField(max_length = 2000)
    
    separation              = models.CharField(null = True, max_length = 255) # day or week
    interval_time           = models.IntegerField(null = True, ) # TBF: units?
    constraint_field        = models.CharField(null = True, max_length = 2000)
    comments                = models.CharField(null = True, max_length = 2000)
    scheduler_notes         = models.TextField(null = True, blank = True)
    session_time_calculated = models.BooleanField(default = False)

    class Meta:
        db_table  = "pht_sessions"
        app_label = "pht"

    def __str__(self):
        return "%s (%d)" % (self.name, self.id)

    def get_lst_parameters(self):
        """
        Returns a dictionary of LST Exclusion and Inclusion
        params, each entry in the dict is a list of (low, high) LST float pairs.
        """
        params = {'LST Exclude' : [], 'LST Include' : []}
        for lst_type in params.keys():
            lows = [sp.float_value for sp in self.sessionparameter_set.filter(
              parameter__name = '%s Low' % lst_type).order_by('id')]
            highs = [sp.float_value for sp in self.sessionparameter_set.filter(
              parameter__name = '%s Hi' % lst_type).order_by('id')]
            params[lst_type] = zip(lows, highs)
        return params

    def get_lst_string(self):
        "Converts pair of LST Exclude/Include observing parameters into low-high string"
        lst   = self.get_lst_parameters()
        types = ['LST Include', 'LST Exclude']
        return [', '.join(
          ["%.2f-%.2f" % (low, hi) for low, hi in lst[t]]) for t in types]

    # Calling get_lst_parameters twice (for each lst_type) causes a performance drop
    # when load all the sessions.
    # I was able to shave off 4 seconds to the load time for sessions by using the 
    # method above.
    """
    def get_lst_string(self, lst_type):
        "Converts pair of LST Exclude/Include observing parameters into low-high string"
        return ', '.join(
          ["%.2f-%.2f" % (low, hi) for low, hi in self.get_lst_parameters()[lst_type]])
    """

    def get_receivers_granted(self):
        "Returns comma-separated string of rcvrs granted."
        return ','.join([r.abbreviation \
            for r in self.receivers_granted.all().order_by('freq_low')])

    def get_receivers(self):
        "Returns comma-separated string of rcvrs."
        return ','.join([r.abbreviation \
            for r in self.receivers.all().order_by('freq_low')])

    def get_backends(self):
        "Returns comma-separated string of backends."
        return ','.join([r.abbreviation \
            for r in self.backends.all().order_by('name')])

    @staticmethod
    def createFromSqlResult(proposal_id, result):
        """
        Creates a new Session instance initialized using the request from
        an SQL query.
        """

        session = Session(pst_session_id = result['session_id']
                          # Don't use result's because that's for the
                          # PST, not our GB PHT DB!
                        , proposal_id = proposal_id #result['PROPOSAL_ID']
                        , name = result['SESSION_NAME']
                        , separation = result['SEPARATION']
                        , interval_time = result['INTERVAL_TIME']
                        , constraint_field = result['CONSTRAINT_FIELD']
                        , comments = result['COMMENTS']
                        , session_time_calculated = result['SESSION_TIME_CALCULATED']
                        )

        session.save()
        return session
        
