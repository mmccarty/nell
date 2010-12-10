######################################################################
#
#  resource_cal.py - form and views for the resource calendar specific
#  views.
#
#  Copyright (C) 2010 Associated Universities, Inc. Washington DC, USA.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#  Correspondence concerning GBT software should be addressed as follows:
#  GBT Operations
#  National Radio Astronomy Observatory
#  P. O. Box 2
#  Green Bank, WV 24944-0002 USA
#
######################################################################

from django.contrib.auth.decorators import login_required
from django.http                    import HttpResponse, HttpResponseRedirect
from django.template                import Context, loader
from django.shortcuts               import render_to_response
from django                         import forms
from django.forms                   import ModelForm
from models                         import *
from django.utils.safestring        import mark_safe
from django.utils.encoding          import StrAndUnicode, force_unicode
from itertools import chain
from django.utils.html              import escape, conditional_escape
from django                         import template
from nell.utilities                 import TimeAgent
from datetime                       import date, datetime, time
from utilities                      import get_requestor

supervisors = ["rcreager", "ashelton", "banderso", "mchestnu", "koneil"]
interval_names = {0:"None", 1:"Daily", 7:"Weekly", 30:"Monthly"}

######################################################################
# This class is a rendering clas for the RadioSelect widget, which is
# nice enough to let us do this.  It renders the radio buttons without
# using the ugly <ul><li>rb</li></ul> construction, which puts an
# extra bullet next to the radio button, which seems a bit redundant.
# Instead, it puts a <br> after each button so that they are rendered
# neatly in a vertical orientation.
######################################################################

class BRRadioRender(forms.RadioSelect.renderer):
    """
    A class to override the standard radio button rendering.  Instead
    of using <ul><li>rb</li>...<li>rb</li></ul>, it uses
    rb<br>...rb<br>
    """

    def render(self):
        """Outputs a <br> for this set of radio fields."""
        return mark_safe(u'%s\n' % u'\n'.join([u'%s<br>'
                % force_unicode(w) for w in self]))

######################################################################
# This rendering class allows the RadioSelect widget to render the
# radio buttons horizontally.
######################################################################

class HorizRadioRender(forms.RadioSelect.renderer):
    """
    This renderer renders the radio buttons horizontally.
    """
    def render(self):
            """Outputs radios"""
            return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))

######################################################################
# This class is here because the CheckboxSelectMultiple widget is not
# as nice as the RadioSelect and does not allow us to do the same
# thing with the renderers.  It doesn't have one, so we have to
# subclass the entire class to get rid of the <ul><li> bullets.
######################################################################

class MyCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])

        for i, (option_value, option_label) in enumerate(chain(self.choices,
                                                               choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))

            cb = forms.CheckboxInput(final_attrs,
                                     check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'%s %s<br>' % (rendered_cb, option_label))
        return mark_safe(u'\n'.join(output))

######################################################################
# The form.  All the fields for the 'Add/Edit Record' form are defined
# here.  Set the 'xxx_req' booleans appropriately to set which fields
# must be filled in by the user to be valid.
######################################################################

class RCAddActivityForm(forms.Form):

#    error_css_class = 'error'
    required_css_class = 'required'

    subject_req          = True
    date_req             = True
    time_req             = True
    end_time_req         = True
    responsible_req      = True
    location_req         = False
    receivers_req        = False
    backends_req         = False
    description_req      = False
    recurrency_until_req = False


    hours = [(i, "%02i" % i) for i in range(0, 24)]
    minutes = [(i, "%02i" % i) for i in range(0, 60, 5)]

    subject = forms.CharField(required = subject_req,
                              max_length = 100,
                              widget = forms.TextInput(attrs = {'size': '80'}))
    date = forms.DateField(required = date_req)
    time_hr  = forms.ChoiceField(required = time_req, choices = hours)
    time_min = forms.ChoiceField(required = time_req, choices = minutes)
    end_choice = forms.ChoiceField(choices=[("end_time", "End Time"),
                                            ("duration", "Duration")],
                                   widget=forms.RadioSelect(
            renderer = HorizRadioRender))
    end_time_hr = forms.ChoiceField(required = end_time_req, choices = hours)
    end_time_min = forms.ChoiceField(required = end_time_req, choices = minutes)
    responsible = forms.CharField(required = responsible_req,
                                  max_length = 256,
                                  widget = forms.TextInput(
            attrs = {'size': '70'}))

    location = forms.CharField(required = location_req, max_length = 200,
                               widget = forms.TextInput(attrs = {'size': '80'}))
    tel_resc = [(p.id, p.resource) 
                for p in Maintenance_Telescope_Resources.objects.all()]
    telescope = forms.ChoiceField(choices = tel_resc,
                                  widget = forms.RadioSelect(
            renderer = BRRadioRender))
    soft_resc = [(p.id, p.resource)
                 for p in Maintenance_Software_Resources.objects.all()]
    software = forms.ChoiceField(choices = soft_resc,
                                 widget = forms.RadioSelect(
            renderer = BRRadioRender))
    rcvr = [(p.id, p.full_description()) for p in Receiver.objects.all()]
    receivers = forms.MultipleChoiceField(required = receivers_req,
                                          choices = rcvr,
                                          widget = MyCheckboxSelectMultiple)

    other_resc = [(p.id, p.resource)
                  for p in Maintenance_Other_Resources.objects.all()]
    other_resource = forms.ChoiceField(choices = other_resc,
                                       widget = forms.RadioSelect(
            renderer = BRRadioRender))

    rcvr.insert(0, (-1, ''))

    # This is the change receivers UI.  It consists of a checkbox and
    # two selection lists.  The selection lists are disabled if the
    # checkbox is cleared.  To do this requires some JavaScript in the
    # template.  This is provided by the function 'EnableWidget()', as
    # set below.  The function name in the attribute must match the
    # function name in the template.  This only should work for
    # supervisors, so we check the initial data to see if data for the
    # hidden field 'supervisor_mode' is set.
    change_receiver = forms.BooleanField(
        required = False,
        widget = forms.CheckboxInput(attrs = {'onClick': 'EnableWidget()'}))
    old_receiver = forms.ChoiceField(
        label = 'down:', required = False, choices = rcvr,
        widget = forms.Select(attrs = {'disabled': 'true'}))
    new_receiver = forms.ChoiceField(
        label = 'up:', required = False, choices = rcvr,
        widget = forms.Select(attrs = {'disabled': 'true'}))
    
    be = [(p.id, p.full_description()) for p in Backend.objects.all()]
    backends = forms.MultipleChoiceField(required = backends_req,
                                         choices = be,
                                         widget = MyCheckboxSelectMultiple)
    description = forms.CharField(required = description_req,
                                  widget = forms.Textarea)
    intervals = [(0, "None"), (1, "Daily"), (7, "Weekly"), (30, "Monthly")]
    recurrency_interval = forms.ChoiceField(choices = intervals)
    recurrency_until = forms.DateField(required = recurrency_until_req)

    entity_id = forms.IntegerField(required = False, widget = forms.HiddenInput)

######################################################################
# display_maintenance_activity(request, activity_id)
#
# Displays a summary table of the maintenance activity, with options
# to modify or delete the activity.
#
# @param request: the HttpRequest object.
# @param activity_id: the id number of the maintenance activity.
#
# @return HttpResponse.
#
######################################################################

def display_maintenance_activity(request, activity_id = None):
    if activity_id:
        ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
        start = ma.get_start('EST')
        duration = timedelta(hours = ma.duration)
        end = start + duration
        u = get_requestor(request)

        if ma.is_repeat_activity():
            repeat_interval = interval_names[ma.repeat_template.repeat_interval]
            repeat_end = ma.repeat_template.repeat_end
            repeat_template = ma.repeat_template.id
        else:
            repeat_interval = "None"
            repeat_end = "None"
            repeat_template = "None"

        last_modified = str(ma.modifications.all()
                            [len(ma.modifications.all()) - 1]
                            if ma.modifications.all() else "")
        created = str(ma.modifications.all()[0]
                      if ma.modifications.all() else ""),
        supervisor_mode = True if (u and u.username() in supervisors) else False

        params = {'subject'            : ma.subject,
                  'date'               : start.date(),
                  'time'               : start.time(),
                  'end_choice'         : "end_time",
                  'end_time'           : end.time(),
                  'responsible'        : ma.contacts,
                  'location'           : ma.location,
                  'telescope'          : ma.telescope_resource.resource,
                  'software'           : ma.software_resource.resource,
                  'other_resource'     : ma.other_resource.resource,
                  'receivers'          : ", ".join([r.full_description()
                                                    for r in ma.receivers.all()]),
                  'backends'           : ", ".join([b.full_description()
                                                    for b in ma.backends.all()]),
                  'description'        : ma.description,
                  'activity_id'        : activity_id,
                  'approval'           : 'Yes' if ma.approved else 'No',
                  'last_modified'      : last_modified,
                  'created'            : created,
                  'receiver_swap'      : ma.receiver_changes.all(),
                  'supervisor_mode'    : supervisor_mode,
                  'maintenance_period' : ma.period_id,
                  'repeat_activity'    : ma.is_repeat_activity(),
                  'repeat_interval'    : repeat_interval,
                  'repeat_end'         : repeat_end,
                  'repeat_template'    : repeat_template
                 }
    else:
        params = {}

    return render_to_response('sesshuns/rc_display_activity.html', params)

######################################################################
# The view.  This is called twice, by the 'GET' and 'POST' paths.  The
# period ID is needed by both the 'GET' and 'POST' paths.  It is
# provided to the 'GET' via the URL.  The 'GET' portion then stashes it
# into a hidden field, from which it can then be retrieved by the
# 'POST' portion.
######################################################################

@login_required
def add_activity(request, period_id = None, year = None,
                 month = None, day = None):
    if request.method == 'POST':

        form = RCAddActivityForm(request.POST)

        if form.is_valid():
            # process the returned stuff here...
            ma = Maintenance_Activity()
            ma.save() # needs to have a primary key for many-to-many
                      # relationships to be set.

            process_activity(request, ma, form)

            if request.POST['ActionEvent'] =="Submit And Continue":
                if form.cleaned_data['entity_id']:
                    redirect_url = '/resourcecal_add_activity/%s/' % \
                        (form.cleaned_data['entity_id'])
                elif year and month and day:
                    redirect_url = '/resourcecal_add_activity/%s/%s/%s/' % \
                        (year, month, day)
                else:
                    redirect_url = '/resourcecal_add_activity/'


                return HttpResponseRedirect(redirect_url)
            else:
                return HttpResponseRedirect('/schedule/')
    else:
        default_telescope = Maintenance_Telescope_Resources.objects \
            .filter(rc_code = 'N')[0]
        default_software  = Maintenance_Software_Resources.objects \
            .filter(rc_code = 'N')[0]
        default_other     = Maintenance_Other_Resources.objects \
            .filter(rc_code = 'N')[0]
        u = get_requestor(request)
        user = get_user_name(u)
        supervisor_mode = True if (u and u.username() in supervisors) else False
        
        if period_id:
            p = Period.objects.filter(id = int(period_id))[0]
            start = TimeAgent.utc2est(p.start)
        elif year and month and day:
            start = datetime(int(year), int(month), int(day))

        initial_data = {'date'              : start.date(),
                        'time_hr'           : start.hour,
                        'time_min'          : start.minute,
                        'end_choice'        : "end_time",
                        'end_time_hr'       : start.hour + 1,
                        'end_time_min'      : 0,
                        'responsible'       : user,
                        'telescope'         : default_telescope.id,
                        'software'          : default_software.id,
                        'other_resource'    : default_other.id,
                        'entity_id'         : period_id,
                        'recurrency_until'  : start + timedelta(days = 30),
                        }

        form = RCAddActivityForm(initial = initial_data)

    return render_to_response('sesshuns/rc_add_activity_form.html',
                              {'form': form,
                               'supervisor_mode': supervisor_mode,
                               'add_activity': True })

######################################################################
# This helper function loads up a maintenance activity's data into a
# form for modification.
######################################################################

def _modify_activity_form(ma):
    start = ma.get_start('EST')
    end = ma.get_end('EST')
    change_receiver = True if len(ma.receiver_changes.all()) else False
    old_receiver = None if not change_receiver else \
                   ma.receiver_changes.all()[0].down_receiver_id
    new_receiver = None if not change_receiver else \
                   ma.receiver_changes.all()[0].up_receiver_id

    initial_data = {'subject'             : ma.subject,
                    'date'                : start.date(),
                    'time_hr'             : start.hour,
                    'time_min'            : start.minute,
                    'end_choice'          : "end_time",
                    'end_time_hr'         : end.hour,
                    'end_time_min'        : end.minute,
                    'responsible'         : ma.contacts,
                    'location'            : ma.location,
                    'telescope'           : ma.telescope_resource.id,
                    'software'            : ma.software_resource.id,
                    'other_resource'      : ma.other_resource.id,
                    'receivers'           : [r.id for r in ma.receivers.all()],
                    'change_receiver'     : change_receiver,
                    'old_receiver'        : old_receiver,
                    'new_receiver'        : new_receiver,
                    'backends'            : [b.id for b in ma.backends.all()],
                    'description'         : ma.description,
                    'entity_id'           : ma.id,
                    'recurrency_interval' : ma.repeat_interval,
                    'recurrency_until'    : ma.repeat_end,
                   }
        
    form = RCAddActivityForm(initial = initial_data)
    return form

######################################################################
# The edit view.  Like the add_activity() view, this is called twice,
# by the 'GET' and 'POST' paths.  Also similar to add_activity with
# the period ID, the activity ID is needed by both the 'GET' and
# 'POST' paths.  It is provided to the 'GET' via the URL.  The 'GET'
# portion then stashes it into a hidden field, from which it can then
# be retrieved by the 'POST' portion.
######################################################################

@login_required
def edit_activity(request, activity_id = None):

    if request.method == 'POST':
        form = RCAddActivityForm(request.POST)

        if form.is_valid():
            # process the returned stuff here...
            ma = Maintenance_Activity.objects \
                .filter(id = form.cleaned_data["entity_id"])[0]
            process_activity(request, ma, form)
            return HttpResponseRedirect('/schedule/')
    else:
        u = get_requestor(request)
        supervisor_mode = True if (u and u.username() in supervisors) else False
        
        if request.GET['ActionEvent'] == 'Modify':
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            form = _modify_activity_form(ma)

        elif request.GET['ActionEvent'] == 'ModifyFuture':
            # In this case we want to go back to the template, and set
            # its 'future_template' to this one.
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            ma.set_as_new_template()
            form = _modify_activity_form(ma)

        elif request.GET['ActionEvent'] == 'ModifyAll':
            today = TimeAgent.truncateDt(datetime.now())
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            start_ma = Maintenance_Activity.objects\
                       .filter(repeat_template = ma.repeat_template)\
                       .filter(_start__gte = today)\
                       .order_by('_start')[0]
            start_ma.set_as_new_template()
            form = _modify_activity_form(start_ma)

        elif request.GET['ActionEvent'] == 'Delete':
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            ma.deleted = True
            ma.save()
            return HttpResponseRedirect('/schedule/')

        elif request.GET['ActionEvent'] == 'DeleteFuture':
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            ma.repeat_template.repeat_end = ma.get_start('EST').date()
            ma.repeat_template.save()
            mas = Maintenance_Activity.objects\
                  .filter(_start__gte = TimeAgent.truncateDt(ma.get_start()))\
                  .filter(repeat_template = ma.repeat_template)

            for i in mas:
                i.deleted = True
                i.save()

            return HttpResponseRedirect('/schedule/')

        elif request.GET['ActionEvent'] == 'DeleteAll':
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            ma.repeat_template.delete = True
            ma.repeat_template.save()
            mas = Maintenance_Activity.objects \
                .filter(repeat_template = ma.repeat_template)

            for i in mas:
                i.deleted = True
                i.save()

            return HttpResponseRedirect('/schedule/')

        elif request.GET['ActionEvent'] == 'Approve':
            ma = Maintenance_Activity.objects.filter(id = activity_id)[0]
            u = get_requestor(request)
            user = get_user_name(u)
            ma.add_approval(user)
            ma.save()

            # Record any receiver changes in the receiver schedule table.
            for i in ma.get_receiver_changes():
                start = ma.get_start()
                rsched = datetime(start.year, start.month, start.day, 16)
                Receiver_Schedule.change_schedule(rsched, [i.up_receiver],
                                                  [i.down_receiver])

            return HttpResponseRedirect('/schedule/')

    return render_to_response('sesshuns/rc_add_activity_form.html',
                              {'form': form,
                               'supervisor_mode': supervisor_mode,
                               'add_activity' : False })

######################################################################
# def process_activity(request, ma, form)
#
# This is a helper function to handle the transfer of data from the
# form to the database. The only difference between the 'add_activity'
# and 'edit_activity' POST sections is in how a maintenance activity
# object is acquired.  In the first, it is created.  In the second, it
# is retrieved from the database by id.  The rest is done by this
# function.
#
# request: The request object
# ma: The Maintenance_Activity object
# form: The RCAddActivityForm object
#
######################################################################

def process_activity(request, ma, form):
    """
    Does some processing in common between the add and the edit views.
    """
    # process the returned stuff here...
    ma.subject = form.cleaned_data['subject']

    # The date and time entered into the form will be ET.  It
    # must be converted to UTC.  The end-time need not be
    # converted since a duration is computed and stored in the
    # database instead of the end time.
    date = form.cleaned_data['date']
    start = datetime(date.year, date.month, date.day,
                     hour = int(form.cleaned_data['time_hr']),
                     minute = int(form.cleaned_data['time_min']))
    ma.set_start(start, 'EST')

    if form.cleaned_data["end_choice"] == "end_time":
        end_date = form.cleaned_data['date']
        end = datetime(year = end_date.year, month = end_date.month,
                       day = end_date.day,
                       hour = int(form.cleaned_data['end_time_hr']),
                       minute = int(form.cleaned_data['end_time_min']))
        delta = end - start
        ma.duration = delta.seconds / 3600.0 # in decimal hours
    else:
        ma.duration = float(form.cleaned_data['end_time_hr']) \
            + float(form.cleaned_data["end_time_min"]) / 60.0

    ma.contacts = form.cleaned_data["responsible"]
    ma.location = form.cleaned_data["location"]
    trid = form.cleaned_data["telescope"]
    ma.telescope_resource = Maintenance_Telescope_Resources.objects \
        .filter(id = trid)[0]
    srid = form.cleaned_data["software"]
    ma.software_resource = Maintenance_Software_Resources.objects \
        .filter(id = srid)[0]
    orid = form.cleaned_data["other_resource"]
    ma.other_resource = Maintenance_Other_Resources.objects.filter(id = orid)[0]

    ma.receivers.clear()

    for rid in form.cleaned_data["receivers"]:
        rcvr = Receiver.objects.filter(id = rid)[0]
        ma.receivers.add(rcvr)

    if form.cleaned_data["change_receiver"] == True:
        down_rcvr_id = form.cleaned_data["old_receiver"]
        up_rcvr_id = form.cleaned_data["new_receiver"]

        # What is needed is a receiver swap entry that contains our
        # receivers in the correct order (i.e. a for b, not b for a).
        # To avoid creating duplicate entries (for instance, repeated
        # swaps of a for b and b for a), search for an existing one
        # first.  If there is none, then create a new swap pair.
        mrsg = Maintenance_Receivers_Swap.objects.filter(
            down_receiver = down_rcvr_id).filter(up_receiver = up_rcvr_id)

        if len(mrsg) == 0:
            down_rcvr = Receiver.objects \
                .filter(id = form.cleaned_data["old_receiver"])[0]
            up_rcvr = Receiver.objects \
                .filter(id = form.cleaned_data["new_receiver"])[0]
            mrs = Maintenance_Receivers_Swap(down_receiver = down_rcvr,
                                             up_receiver = up_rcvr)
            mrs.save()
        else:
            mrs = mrsg[0]

        ma.receiver_changes.clear()
        ma.receiver_changes.add(mrs)
    else:
        ma.receiver_changes.clear()

    ma.backends.clear()

    for bid in form.cleaned_data["backends"]:
        be = Backend.objects.filter(id = bid)[0]
        ma.backends.add(be)

    ma.description = form.cleaned_data["description"]
    ma.repeat_interval = int(form.cleaned_data["recurrency_interval"])

    if ma.repeat_interval > 0:
        ma.repeat_end = form.cleaned_data["recurrency_until"]
    
    # assign right period for maintenance activity.  If no
    # periods, this will remain 'None'
    start = TimeAgent.truncateDt(ma._start)
    end = start + timedelta(days = 1)
    periods = Period.get_periods_by_observing_type(start, end, "maintenance")

    for p in periods:
        if ma._start >= p.start and ma._start < p.end():
            ma.period = p

    # Now add user and timestamp for modification.  Earliest mod is
    # considered creation.
    u = get_requestor(request)
    modifying_user = get_user_name(u)
    ma.add_modification(modifying_user)
    ma.save()

    # If this is a template, modify all subsequent activities based on
    # it.

    if ma.is_repeat_template():
        template = ma
    elif ma.is_future_template():
        template = ma.repeat_template
    else:
        template = None

    if template:

        mas = [m for m in Maintenance_Activity.objects\
               .filter(repeat_template = template)\
               .filter(_start__gte = ma._start)]

        # times neet to be carried over as ET so that the underlying
        # UT will compensate for DST.
        for i in mas:
            ma_time = ma.get_start('EST')
            i_time = i.get_start('EST')
            start = datetime(i_time.year, i_time.month, i_time.day,
                             ma_time.hour, ma_time.minute)

            i.copy_data(ma)
            i.set_start(start, 'EST')
            i.save()

def get_user_name(u):
    if u:
        if u.first_name and u.last_name:
            user = u.last_name + ", " + u.first_name
        else:
            user = u.username()
    else:
        user = "anonymous"

    return user