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

from datetime import time
from django   import forms
from scheduler.models    import Repeat
from users.utilities import *

times = [time(h, m).strftime("%H:%M") for h in range(0, 24) for m in range(0, 60, 15)]

class BlackoutForm(forms.Form):
    start        = forms.CharField(max_length = 10)
    start_time   = forms.ChoiceField(choices = [(t, t) for t in times])
    end          = forms.CharField(max_length = 10)
    end_time     = forms.ChoiceField(choices = [(t, t) for t in times])
    repeats      = forms.ChoiceField(choices = [(r.repeat, r.repeat) for r in Repeat.objects.all()])
    until        = forms.CharField(max_length = 10, required = False)
    until_time   = forms.ChoiceField(choices = [(t, t) for t in times], required = False)
    description  = forms.CharField(max_length = 512, required = False)

    @staticmethod
    def initialize(b, tz):

        start_date = adjustDate(tz, b.getStartDate())
        end_date   = adjustDate(tz, b.getEndDate())
        until      = adjustDate(tz, b.getUntil())
        return BlackoutForm({'start'      : start_date.strftime("%m/%d/%Y %H:%M").split(' ')[0] \
                                          if start_date is not None else ''
                       , 'start_time' : start_date.strftime("%m/%d/%Y %H:%M").split(' ')[1] \
                                          if start_date is not None else ''
                       , 'end'        : end_date.strftime("%m/%d/%Y %H:%M").split(' ')[0] \
                                          if end_date is not None else ''
                       , 'end_time'   : end_date.strftime("%m/%d/%Y %H:%M").split(' ')[1] \
                                          if end_date is not None else ''
                       , 'repeats'    : b.getRepeat()
                       , 'until'      : until.strftime("%m/%d/%Y %H:%M").split(' ')[0] \
                                          if until is not None else ''
                       , 'until_time' : until.strftime("%m/%d/%Y %H:%M").split(' ')[1] \
                                          if until is not None else ''
                       , 'description' : b.getDescription()
                        })

    def format_dates(self, tz, data):
        # Now see if the data to be saved is valid
        # watch for malformed dates
        # NOTE: parse_datetime takes 'tz' and returns UT!!! This
        # is notable because it influences the functioning of
        # Blackout.initialize(), which expects this. (RC)
        self.cleaned_start, stError = parse_datetime(data, 'start', 'start_time', tz)
        self.cleaned_end,   edError = parse_datetime(data,   'end',   'end_time', tz)
        self.cleaned_until, utError = parse_datetime(data, 'until', 'until_time', tz)
        self.date_errors = [e for e in [stError, edError, utError] if e is not None]

    def clean(self):
        try:
            for e in self.date_errors:
                raise forms.ValidationError(e)
        except AttributeError:
            return self.cleaned_data

        cleaned_data                     = self.cleaned_data
        self.cleaned_data['repeat']      = Repeat.objects.get(repeat = cleaned_data['repeats'])
        self.cleaned_data['description'] = cleaned_data['description']

        start, end, until = self.cleaned_start, self.cleaned_end, self.cleaned_until
        # more error checking!
        # start, end can't be null
        if start is None or end is None:
            raise forms.ValidationError("ERROR: must specify Start Date and End Date")
        # start has to be a start, end has to be an end 
        if end is not None and start is not None and end < start:
            raise forms.ValidationError("ERROR: End Date must be after Start Date")
        if end is not None and until is not None and until < end:
            raise forms.ValidationError("ERROR: Until must be after End Date")
        # if it's repeating, we must have an until date
        if self.cleaned_data['repeat'].repeat != "Once" and until is None:
            raise forms.ValidationError("ERROR: if repeating is not 'Once', you must specify Until")

        return cleaned_data
