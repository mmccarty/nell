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

from django.db      import models
from math           import modf
from nell.utilities import TimeAgent
from System         import System

class Target(models.Model):
    session    = models.OneToOneField("Sesshun", null = True, related_name = "target")
    system     = models.ForeignKey(System)
    source     = models.CharField(null = True, max_length = 256, blank = True)
    vertical   = models.FloatField(null = True, blank = True)
    horizontal = models.FloatField(null = True, blank = True)

    def __str__(self):
        return "%s at %s : %s" % (self.source
                                , self.horizontal
                                , self.vertical
                                  )

    def __unicode__(self):
        if self.source and self.horizontal and self.vertical:
            return "%s @ (%5.2f, %5.2f), Sys: %s" % \
                (self.source
               , float(self.horizontal)
               , float(self.vertical)
               , self.system)
        else:
            return "Incomplete target for session %s - missing fields" % self.session.name

    def get_horizontal(self):
        "Returns the horizontal component in sexigesimal form."
        if self.horizontal is None:
            return ""

        if self.system.name == 'Galactic':
            return self.get_deg(self.horizontal)

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

        return self.get_deg(self.vertical)

    def get_deg(self, value):
        degs = TimeAgent.rad2deg(value)

        if degs < 0:
            degs = abs(degs)
            sign = "-"
        else:
            sign = " "

        fpart, ddegs = modf(degs)
        fpart, dmins = modf(fpart * 60)
        dsecs = round(fpart * 60, 1)

        if dsecs > 59.9:
            dmins = dmins + 1
            dsecs = 0.0
        if dmins > 59.9:
            ddegs = ddegs + 1
            dmins = 0.0

        return "%s%02i:%02i:%04.1f" % (sign, int(ddegs), int(dmins), dsecs)

    def isEphemeris(self):
        return self.system.name == "Ephemeris"

    class Meta:
        db_table  = "targets"
        app_label = "scheduler"

