#!/bin/env python

from django.core.management import setup_environ
import settings
setup_environ(settings)

from sesshuns.models import *
from sets            import Set
from datetime        import date, datetime, timedelta
from tools           import TimeAccounting

def get_sessions(typ,sessions):
    return [s for s in sessions if s.session_type.type == typ]

def get_allotment_hours(sessions, typ):
    return sum([s.allotment.total_time for s in get_sessions(sessions, typ)])

def get_obs_hours(sessions, typ):
    ta = TimeAccounting()
    return sum([ta.getTime("observed", s) for s in get_sessions(session, typ)])

def missing_observer_parameter_pairs(sessions):
    pairs = [
        Set(["LST Exclude Hi", "LST Exclude Low"])
      , Set(["LST Include Hi", "LST Include Low"])
    ]

    return [s.name for s in sessions \
        if len(pairs[0].intersection(s.observing_parameter_set.all())) == 1 or \
           len(pairs[1].intersection(s.observing_parameter_set.all())) == 1]

def check_maintenance_and_rcvrs():
    "Are there rcvr changes happening w/ out maintenance days?"
    bad = []
    for dt, rcvrs in Receiver_Schedule.extract_schedule().items():
        # Well, what are the periods for this day?
        start = dt.replace(hour = 0)
        periods = Period.objects.filter(
                                   start__gt = start
                                 , start__lt = start + timedelta(days = 1)
                                 )
        # of these, is any one of them a maintenance?
        if len([p for p in periods if p.session.project.is_maintenance()]) == 0:
            bad.append(dt.date())
    return sorted(Set(bad))

def print_values(file, values):
    if values == []:
        file.write("\n\tNone")
    else:
        for v in values:
            file.write("\n\t%s" % v)


# Windowed Sessions w/ no windows (just give count)

def get_windowed_sessions_with_no_window():
    s = Sesshun.objects.all()
    sw = s.filter(session_type__type__exact = "windowed")
    windowless = [x for x in sw if len(x.window_set.all()) == 0]
    return windowless

# non-Windowed Sessions w/ windows (just give count)

def get_non_windowed_sessions_with_windows():
    s = Sesshun.objects.all()
    snw = s.exclude(session_type__type__exact = "windowed")
    windowed = [x for x in snw if len(x.window_set.all()) > 0]
    return windowed

# windows w/ out start, duration, or default_period

def get_incomplete_windows():
    ws = Window.objects.all()
    win_no_start = ws.filter(start_date = None)
    win_no_dur = ws.filter(duration = None)
    win_no_period = ws.filter(default_period = None)
    return (win_no_start, win_no_dur, win_no_period)

# windows w/ any period outside the window range

def get_win_period_outside():
    ws = Window.objects.all()
    wp = ws.exclude(default_period = None)
    badwin = []
    outside = False

    for i in wp:
        dps = i.default_period.start # start datetime for period
        dpe = i.default_period.end() # end datetime for period
        ws = i.start_datetime()     # start datetime for window
        we = i.end_datetime()       # end datetime for window

        if dps < ws or dpe > we:
            outside = True

        if i.period:
            if i.period.start() < ws or i.period.end() > we:
                outside = True

        if outside:
            badwin.append(i)

    return badwin

# overlapping windows belonging to the same session

def get_overlapping_windows():
    w = Window.objects.all()
    sid = Set()
    overlap = []

    for i in w:
        sid.add(i.session_id)

    for i in sid:
        wwsid = w.filter(session__id__exact = i)
        s = len(wwsid)

        # Would like to do this in terms of the model/SQL

        for j in range(0, s):
            for k in range(j + 1, s):
                w1s = wwsid[j].start_datetime()     # start datetime for window
                w1e = wwsid[j].end_datetime()       # end datetime for window
                w2s = wwsid[k].start_datetime()
                w2e = wwsid[k].end_datetime()

                # Here we check that the windows don't overlap.  To
                # meet this condition, a window's start *and* end time
                # must *both* be less than another's start, *or*
                # greater than another's end time. That would place
                # the entire window either before or after the other
                # window.
                if not ((w2s < w1s and w2e < w1s) or (w2s > w1e and w2e > w1e)):
                    overlap.append((wwsid[j], wwsid[k]))
    return overlap

# periods belonging to windowed sessions that are not assigned to a window.

def get_non_window_periods():
    ws = Sesshun.objects.filter(session_type__type__exact = "windowed")
    non_window_periods = []

    for s in ws:
        pds = s.period_set.all()
        win = s.window_set.all()
        winp = Set()

        for i in win:
            if i.default_period:
                winp.add(i.default_period)

            if i.period:
                winp.add(i.period)

        for i in pds:
            if i not in winp:
                non_window_periods.append(i)

    return non_window_periods

# windows with more than one period in the scheduled state

def get_windows_with_scheduled_periods():
    # need a set of windows with more than one period to start with
    w = Window.objects.exclude(default_period = None).exclude(period = None)
    w = w.filter(period__state__name = "scheduled").filter(default_period__state__name = "scheduled")
    return w


# windows of the same session with less than 48 hour inter-window interval

def get_window_within_48():
    w = Window.objects.all()
    sid = Set()
    within48 = []

    for i in w:
        sid.add(i.session_id)

    for i in sid:
        wwsid = w.filter(session__id__exact = i)
        s = len(wwsid)

        # Would like to do this in terms of the model/SQL

        for j in range(0, s):
            for k in range(j + 1, s):
                w1s = wwsid[j].start_datetime()     # start datetime for window
                w1e = wwsid[j].end_datetime()       # end datetime for window
                w2s = wwsid[k].start_datetime()
                w2e = wwsid[k].end_datetime()

                # Here we check that the windows don't come closer
                # than 48 hours to each other.  To meet this
                # condition, the earlier window's end time must be
                # less at least 2 days earlier than the later window's
                # start.

                if w1s < w2s:
                    delta = w2s - w1e
#                    print w2s, "-", w1e, "=", delta
                else:
                    delta = w1s - w2e
#                    print w1s, "-", w2e, "=", delta

                if delta.days < 2:
                    within48.append((wwsid[j], wwsid[k], delta))
    return within48

# windows whose period is pending

def get_pathological_windows():
    pathological = []
    w = Window.objects.all()

    for i in w:
        if i.state() == None or i.dual_pending_state():
            pathological.append(i)

    return pathological


# windows with periods not represented in its session's period list

def get_windows_with_rogue_periods():
    w = Window.objects.exclude(default_period = None)
    rogue = []

    for i in w:
        ps = i.session.period_set.filter(id__exact = i.default_period.id)

        if len(ps) == 0:
            rogue.append(i)

        if i.period:
            ps = i.session.period_set.filter(id__exact = i.period.id)

            if len(ps) == 0:
                rogue.append(i)
    return rogue

def output_windows(file, wins):
    for i in wins:
        file.write("\t%s\t%i\n" % (i.session.name, i.id))

def get_closed_projets_with_open_sessions():
    p = Project.objects.filter(complete = True)
    cp = []

    for i in p:
        if i.sesshun_set.filter(status__complete = False):
           cp.append(i)

    return cp

    

def output_windows_report(file):
    file.write("\n\nWindows:\n\n")

    w = []
    w.append(get_windowed_sessions_with_no_window())
    w.append(get_non_windowed_sessions_with_windows())
    w.append(get_incomplete_windows())
    w.append(get_win_period_outside())
    w.append(get_overlapping_windows())
    w.append(get_non_window_periods())
    w.append(get_windows_with_scheduled_periods())
    w.append(get_window_within_48())
    w.append(get_pathological_windows())
    w.append(get_windows_with_rogue_periods())

    file.write("Summary\n")
    file.write("\tNumber of windowed sessions with no windows: %i\n" % len(w[0]))
    file.write("\tNumber of non-windowed sessions with windows assigned: %i\n" % len(w[1]))
    file.write("\tNumber of incomplete windows (missing data: start, duration, period): (%i, %i, %i)\n" % (len(w[2][0]), len(w[2][1]), len(w[2][2])))
    file.write("\tNumber of windows with periods outside window: %i\n" % len(w[3]))
    file.write("\tNumber of overlapping window pairs: %i\n" % len(w[4]))
    file.write("\tNumber of periods belonging in windowed sessions not in windows: %i\n" % (len(w[5])))
    file.write("\tWindows with more than one period in the scheduled state: %i\n" % len(w[6]))
    file.write("\tWindows within same session that come within 48 hours of each other: %i\n" % len(w[7]))
    file.write("\tWindows in an illegal state: %i\n" % len(w[8]))
    file.write("\tWindows with periods not in their session period set: %i\n" % len(w[9]))


    file.write("\n\nWindow Details\n\n")

    if len(w[0]):
        file.write("Windowed sessions with no windows:\n")

        for i in w[0]:
            file.write("\t%s\n" % i.name)

    if len(w[1]):
        file.write("\nNon-windowed sessions with windows assigned:\n")

        for i in w[1]:
            file.write("\t%s\n" % i.name)

    if len(w[2]):
        file.write("\nIncomplete windows:\n")

        if len(w[2][0]):
            file.write("\n\tWith no start date:\n")
            output_windows(file, w[2][0])

        if len(w[2][1]):
            file.write("\n\tWith no duration:\n")
            output_windows(file, w[2][1])

        if len(w[2][2]):
            file.write("\n\tWith no period:\n")
#            print_values(file, w[2][2])
            output_windows(file, w[2][2])

    if len(w[3]):
        file.write("\nWindows with periods outside window:\n")
        output_windows(file, w[3])

    if len(w[4]):
        file.write("\nOverlapping window pairs:\n")

        for i in w[4]:
            file.write("\t%s\t%i\t&\t%s\t%i\n" % \
                       (i[0].session.name, i[0].id, i[1].session.name, i[1].id))

    if len(w[5]):
        file.write("\nPeriods belonging in windowed sessions not in windows:\n")

        for i in w[5]:
            file.write("\t%s\t%i\n" % (i.session.name, i.id))

    if len(w[6]):
        file.write("\nWindows with more than one period in the scheduled state:\n")
        output_windows(file, w[6])

    if len(w[7]):
        file.write("\nWindows within same session that come within 48 hours of each other:\n")
        file.write("\n\t(Window, Window, delta(days, seconds))\n")

        for i in w[7]:
            #exclude windows that overlap. Those are covered earlier.
            if not (i[2].days < 0 or i[2].seconds < 0):
                file.write("\t%s\t%i\t&\t%s\t%i\t(%i, %i)\n" % \
                           (i[0].session.name, i[0].id, i[1].session.name,
                            i[1].id, i[2].days, i[2].seconds))

    if len(w[8]):
        file.write("\nWindows in an illegal state:\n")
        output_windows(file, w[8])

    if len(w[9]):
        file.write("\nWindows with periods not in their session period set:\n")
        output_windows(file, w[9])


def GenerateReport():

    ta = TimeAccounting()

    outfile = open("./DssDbHealthReport.txt",'w')

    projects = sorted(Project.objects.all(), lambda x, y: cmp(x.pcode, y.pcode))
    sessions = sorted(Sesshun.objects.all(), lambda x, y: cmp(x.name, y.name))
    periods  = Period.objects.order_by("start")
    rcvrs    = Receiver.objects.order_by("freq_low")

    outfile.write("Projects without sessions:")
    values = [p.pcode for p in projects if p.sesshun_set.all() == []]
    print_values(outfile, values)

    outfile.write("\n\nSessions without a project:")
    values = [s.name for s in sessions if not s.project]
    print_values(outfile, values)

    outfile.write("\n\nOpen sessions with alloted time < min duration:")
    values = [s.name for s in sessions \
              if s.session_type.type == "open" and \
                 s.allotment.total_time < s.min_duration]
    print_values(outfile, values)

    outfile.write("\n\nOpen sessions (not completed) with time left < min duration:")
    values = [s.name for s in sessions \
              if s.session_type.type == "open" and \
                 not s.status.complete and \
                 ta.getTimeLeft(s) < s.min_duration]
    print_values(outfile, values)

    outfile.write("\n\nOpen sessions with max duration < min duration:")
    values = [s.name for s in sessions \
              if s.session_type.type == "open" and \
                 s.min_duration > s.max_duration]
    print_values(outfile, values)

    outfile.write("\n\nSessions with negative observed time:")
    values = ["%s; obs: %s, total: %s" % \
        (s.name, str(s.getObservedTime()), str(s.allotment.total_time)) \
        for s in sessions if ta.getTime("observed", s) < 0.0]
    print_values(outfile, values)

    outfile.write("\n\nSessions without recievers:")
    values = [s.name for s in sessions if len(s.receiver_list()) == 0]
    print_values(outfile, values)

    outfile.write("\n\nOpen sessions with default frequency 0:")
    values = [s.name for s in sessions \
              if s.session_type.type == "open" and s.frequency == 0.0]
    print_values(outfile, values)

    outfile.write("\n\nSessions with unmatched observer parameter pairs:")
    values = [s.name for s in missing_observer_parameter_pairs(sessions)]
    print_values(outfile, values)

    outfile.write("\n\nSessions with RA and Dec equal to zero:")
    values = [s.name for s in sessions \
                     for t in s.target_set.all() \
                     if t.vertical == 0.0 and t.horizontal == 0.0]
    print_values(outfile, values)

    outfile.write("\n\nSessions with frequency (GHz) out of all Rcvr bands")
    values = []
    for s in sessions:
        out_of_band = False
        # freq. must be out of band for ALL rcvrs to be reported
        rcvrs = [first(Receiver.objects.filter(abbreviation = rname)) \
            for rname in s.rcvrs_specified()]
        in_bands = [r for r in rcvrs if r.in_band(s.frequency)]
        # don't report sessions w/ out rcvrs: we do that above
        if len(in_bands) == 0 and len(rcvrs) != 0:
            values.append("%s %s %5.4f" % (s.name
                                         , s.receiver_list_simple()
                                         , s.frequency))
    print_values(outfile, values)

    outfile.write("\n\nProjects without a friend:")
    values = [p.pcode for p in projects if not p.complete and not p.friend]
    print_values(outfile, values)

    outfile.write("\n\nProjects without any Schedulable sessions:")
    values = [p.pcode for p in projects \
              if not p.complete and \
              not any([s.schedulable() for s in p.sesshun_set.all()])]
    print_values(outfile, values)

    outfile.write("\n\nProjects without any observers:")
    values = [p.pcode for p in projects \
              if not p.complete and len(p.get_observers()) == 0]
    print_values(outfile, values)

    outfile.write("\n\nReceiver changes happening on days other than maintenance days:")
    values = [str(s) for s in check_maintenance_and_rcvrs()]
    print_values(outfile, values)

    outfile.write("\n\nSessions for which periods are scheduled when none of their receivers are up:")
    values = [p.__str__() for p in periods if not p.has_required_receivers()]
    print_values(outfile, values)

    outfile.write("\n\nProjects that contain non-unique session names:")
    names  = [(p.pcode, [s.name for s in p.sesshun_set.all()]) for p in projects]
    values = [p for p, n in names if len(Set(n)) != len(n)]
    print_values(outfile, values)

    outfile.write("\n\nUsers with duplicate accounts:")
    users  = list(User.objects.order_by("last_name"))
    values = []
    for u in users:
        users.remove(u)
        for i in users:
            if i.last_name == u.last_name and i.first_name == u.first_name:
                values.append(u)
    print_values(outfile, values)

    outfile.write("\n\nUsers with no username:")
    users  = list(User.objects.order_by("last_name"))
    values = [u for u in users if u.username is None]
    print_values(outfile, values)

    outfile.write("\n\nPeriods Scheduled on blackout dates:")
    values = []
    for s in sessions:
        for p in [p for p in s.period_set.all() if p.start >= datetime.today() \
                                                   and not p.isDeleted()]:
            blackouts = s.project.get_blackout_times(p.start, p.end())
            if blackouts:
                values.append("%s on %s" % (s.name, p.start.strftime("%m/%d/%Y %H:%M")))
    print_values(outfile, values)

    outfile.write("\n\nOverlapping periods:")
    values  = []
    overlap = []
    not_deleted_periods = [p for p in periods if p.state.abbreviation != "D"]
    for p1 in not_deleted_periods:
        start1, end1 = p1.start, p1.end()
        for p2 in not_deleted_periods:
            start2, end2 = p2.start, p2.end()
            if p1 != p2 and p1 not in overlap and p2 not in overlap:
                if overlaps((start1, end1), (start2, end2)):
                    values.append("%s and %s" % (str(p1), str(p2)))
                    overlap.extend([p1, p2])
    print_values(outfile, values)

    outfile.write("\n\nGaps in historical schedule:")
    now = datetime.utcnow()
    ps_all = Period.objects.filter(start__lt = now).order_by("start")
    ps = [p for p in ps_all if not p.isDeleted()] # TBF: use filter?
    values = []
    previous = ps[0]
    for p in ps[1:]:
        # periods should be head to tail - TBF: this catches overlaps too!
        if p.start != previous.end():
            values.append("Gap between: %s and %s" % (previous, p))
        previous = p
    print_values(outfile, values)

    outfile.write("\n\nPeriods with non-positive durations:")
    values  = [p for p in periods if p.duration <= 0.]
    print_values(outfile, values)

    outfile.write("\n\nPeriods with negative observed times:")
    values  = [str(p) for p in periods if p.accounting.observed() < 0.]
    print_values(outfile, values)

    outfile.write("\n\nDeleted Periods with positive observed times:")
    ps = [p for p in periods if p.state.abbreviation == 'D']
    values  = [str(p) for p in ps if p.accounting.observed() > 0.]
    print_values(outfile, values)

    outfile.write("\n\nPending Periods (non-windowed):")
    values  = [str(p) for p in periods if p.isPending() and not p.is_windowed()]
    print_values(outfile, values)

    outfile.write("\n\nCompleted projects with non-complete sessions:")
    print_values(outfile, get_closed_projets_with_open_sessions())

    output_windows_report(outfile)



if __name__ == '__main__':
    GenerateReport()
