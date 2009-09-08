from datetime                       import datetime, date, time
from django.contrib.auth.decorators import login_required
from django.db.models         import Q
from django.http              import HttpResponse, HttpResponseRedirect
from django.shortcuts         import render_to_response
from models                   import *
from sets                     import Set
from utilities.UserInfo       import UserInfo
from utilities                import NRAOBosDB

# persist this object to avoid having to authenticate every time
# we want PST services
ui = UserInfo()

def schedule(request, *args, **kws):
    # serve up the GBT schedule
    # TBF: make this date and range dependent
    ps = Period.objects.all()
    return render_to_response("sesshuns/schedule.html"
                            , {'periods'            : ps })

@login_required
def dates_not_schedulable(request, *args, **kws):
    pcode     = args[0]
    start     = datetime.fromtimestamp(float(request.GET.get('start', '')))
    end       = datetime.fromtimestamp(float(request.GET.get('end', '')))
    project   = first(Project.objects.filter(pcode = pcode).all())
    period    = (end - start).days

    dates = Set([])
    if not project.has_schedulable_sessions():
        dates = dates.union([start + timedelta(days = i) for i in range(period)])
    else:
        dates = dates.union(project.get_blackout_dates(start, end))
        dates = dates.union(project.get_receiver_blackout_dates(start, end))
        dates = dates.union(project.get_prescheduled_days(start, end))

    return HttpResponse(json.dumps([{"start": d.isoformat()} for d in dates]))

@login_required
def events(request, *args, **kws):
    pcode     = args[0]
    start     = request.GET.get('start', '')
    end       = request.GET.get('end', '')
    project   = first(Project.objects.filter(pcode = pcode).all())

    # Each event needs a unique id.  Let's start with 1.
    id          = 1
    jsonobjlist = []

    # Investigator blackout events
    blackouts = Set([b for i in project.investigator_set.all() \
                       for b in i.user.blackout_set.all()])
    for b in blackouts:
        jsonobjlist.extend(b.eventjson(start, end, id))
        id = id + 1

    # Investigator reservations
    reservations, id = NRAOBosDB().eventjson(project, id)
    jsonobjlist.extend(reservations)

    # Scheduled telescope periods
    for p in project.getPeriods():
        jsonobjlist.append(p.eventjson(id))
        id = id + 1

    # Semester start dates
    date = datetime.fromtimestamp(float(start))
    for s in Semester.getFutureSemesters(date):
        jsonobjlist.append(s.eventjson(id))
        id = id + 1

    return HttpResponse(json.dumps(jsonobjlist))

def get_day(n, today):
    'Find the n_th day on the calendar.'
    start = today - timedelta(today.isoweekday())
    return start + timedelta(n)

def get_current_month(n, today):
    day   = get_day(7*(n/7), today)
    pivot = day if day.day == 1 else day + timedelta(7)
    return pivot.month

def get_label(w, d, today):
    'Certain day labels should include month names.'
    n      = 7 * w + d
    day    = get_day(n, today)
    format = '%b %d' if day.day == 1 or n == 0 else '%d'
    return day.strftime(format)

def get_color(w, d, today):
    n   = 7 * w + d
    day = get_day(n, today)
    return 'black' if day.month == get_current_month(n, today) else '#888888'

def get_bgcolor(w, d, today):
    day = get_day(7 * w + d, today)
    return '#EEEEEE' if day == date.today() else '#FFFFFF'

@login_required
def profile(request, *args, **kws):
    loginUser = request.user.username
    if len(args) > 0:
        u_id,     = args
        user      = first(User.objects.filter(id = u_id))
        projects  = [i.project.pcode for i in user.investigator_set.all()]
        requestor = first(User.objects.filter(username = loginUser))
        assert requestor is not None
        union     = [i.project.pcode for i in requestor.investigator_set.all()
                        if i.project.pcode in projects]
        #  If the requestor is not the user profile requested and they are
        #  not on the same project redirect to the requestor's profile.
        if union == [] and user != requestor and not requestor.isAdmin():
            return HttpResponseRedirect("/profile")
    else:
        requestor = first(User.objects.filter(username = loginUser))
        assert requestor is not None
        user      = requestor
        
    # get the users' info from the PST
    try:
        # TBF: use user's credentials to get past CAS, not Mr. Nubbles!
        info = ui.getProfileByID(user, 'dss', 'MrNubbles!')
    except:
        #  we really should only see this during unit tests.
        #print "encountered exception w/ UserInfo and user: ", user
        info = dict(emails = [e.email for e in user.email_set.all()]
                  , phones = ['Not Available']
                  , postals = ['Not Available']
                  , affiliations = ['Not Available']
                  , username = user.username)
        
    # get the reservations information from BOS
    bos = NRAOBosDB()
    reservations = bos.getReservationsByUsername(user.username)

    # Remember [] is False,  TBF is this needed?
    isFriend = ["yep" for p in user.investigator_set.all() if p.friend]
    return render_to_response("sesshuns/profile.html"
                            , {'u'            : user
                             , 'requestor'    : requestor
                             , 'authorized'   : user == requestor # allowed to edit
                             , 'isFriend'     : isFriend
                             , 'emails'       : info['emails']
                             , 'phones'       : info['phones']
                             , 'postals'      : info['postals']
                             , 'affiliations' : info['affiliations']
                             , 'username'     : info['username']
                             , 'reserves'     : reservations
                               })

@login_required
def project(request, *args, **kws):
    bos = NRAOBosDB()
    loginUser = request.user.username
    user   = first(User.objects.filter(username = loginUser))
    assert user is not None
    pcode, = args
    #  If the requestor is not on this project redirect to their profile.
    if pcode not in [i.project.pcode for i in user.investigator_set.all()] \
            and not user.isAdmin():
        return HttpResponseRedirect("/profile")
        
    project = first(Project.objects.filter(pcode = pcode))

    now          = datetime.utcnow().replace(hour = 0, minute = 0, second = 0)
    later        = now + timedelta(days = 90)
    rcvr_blkouts = []
    for s, e in project.get_receiver_blackout_ranges(now, later):
        if e is None:
            rcvr_blkouts.append((s.date(), None))
        else:
            rcvr_blkouts.append((s.date(), e.date()))

    return render_to_response(
        "sesshuns/project.html"
      , {'p' : project
       , 'u' : user
       , 'v' : project.investigator_set.order_by('priority').all()
       , 'r' : bos.reservations(project)
       , 'rcvr_blkouts': rcvr_blkouts
       }
    )

@login_required
def search(request, *args, **kws):
    loginUser = request.user.username
    user   = first(User.objects.filter(username = loginUser))
    assert user is not None
    search   = request.POST.get('search', '')

    projects = Project.objects.filter(
        Q(pcode__icontains = search) | \
            Q(name__icontains = search) | \
            Q(semester__semester__icontains = search.upper()))
    projects = [p for p in projects]

    # Search for project by short code.
    for p in Project.objects.all():
        code = p.pcode.replace("GBT", "")
        code = code.replace("-0", "")
        code = code[1:] if code[0] == "0" else code
        if code == search.upper():
            projects.append(p)
        
    users = User.objects.filter(
        Q(first_name__icontains = search) | Q(last_name__icontains = search))

    return render_to_response("sesshuns/search.html"
                            , {'ps' : projects
                             , 'us' : users
                             , 'u'  : user
                               })

@login_required
def toggle_session(request, *args, **kws):
    pcode, sname = args
    s = first(Sesshun.objects.filter(project__pcode = pcode, name = sname))
    s.status.enabled = not s.status.enabled
    s.status.save()
    
    return HttpResponseRedirect("/project/%s" % pcode)

@login_required
def toggle_observer(request, *args, **kws):
    pcode, i_id = args
    i = first(Investigator.objects.filter(project__pcode = pcode, id = i_id))
    i.observer = not i.observer
    i.save()

    project = Project.objects.filter(pcode=pcode)[0]
    project.normalize_investigators()
    
    return HttpResponseRedirect("/project/%s" % pcode)

@login_required
def modify_priority(request, *args, **kws):
    pcode, i_id, dir = args
    project = Project.objects.filter(pcode=pcode)[0]
    project.normalize_investigators()
    I = first(project.investigator_set.filter(id = i_id))
    key = 'priority' if dir == "down" else '-priority'
    t = None
    for i in project.investigator_set.order_by(key):
        if i.observer:
            if t:
                t.priority, i.priority = i.priority, t.priority
                t.save()
                i.save()
                break
            if i == I:
                t = i
    
    return HttpResponseRedirect("/project/%s" % pcode)

@login_required
def dynamic_contact_form(request, *args, **kws):
    u_id,     = args
    user      = first(User.objects.filter(id = u_id))

    # TBF Use a decorator
    loginUser = request.user.username
    requestor = first(User.objects.filter(username = loginUser))
    assert requestor is not None
    if user != requestor and not requestor.isAdmin():
        return HttpResponseRedirect("/profile")

    return render_to_response("sesshuns/dynamic_contact_form.html"
                            , {'u': user})

@login_required
def dynamic_contact_save(request, *args, **kws):
    u_id, = args
    user  = first(User.objects.filter(id = u_id))

    # TBF Use a decorator
    loginUser = request.user.username
    requestor = first(User.objects.filter(username = loginUser))
    assert requestor is not None
    if user != requestor and not requestor.isAdmin():
        return HttpResponseRedirect("/profile")

    user = first(User.objects.filter(id = u_id))
    user.contact_instructions = request.POST.get("contact_instructions", "")
    user.save()

    return HttpResponseRedirect("/profile/%s" % u_id)

@login_required
def blackout_form(request, *args, **kws):
    loginUser = request.user.username
    method = request.GET.get('_method', '')
    u_id, = args
    user  = first(User.objects.filter(id = u_id))

    # TBF Use a decorator
    requestor = first(User.objects.filter(username = loginUser))
    assert requestor is not None
    if user != requestor and not requestor.isAdmin():
        return HttpResponseRedirect("/profile")

    b     = first(Blackout.objects.filter(id = int(request.GET.get('id', 0))))
    times = [time(h, m).strftime("%H:%M")
             for h in range(0, 24) for m in range(0, 60, 15)]

    return render_to_response("sesshuns/blackout_form.html"
                            , {'method' : method
                             , 'b'      : b
                             , 'u'      : user
                             , 'tzs'    : TimeZone.objects.all()
                             , 'repeats': Repeat.objects.all()
                             , 'times'  : times
                               })

@login_required
def blackout(request, *args, **kws):
    u_id, = args
    user = first(User.objects.filter(id = u_id))

    # TBF Use a decorator
    loginUser = request.user.username
    requestor = first(User.objects.filter(username = loginUser))
    assert requestor is not None
    if user != requestor and not requestor.isAdmin():
        return HttpResponseRedirect("/profile")

    if request.GET.get('_method', '') == "DELETE":
        b = first(Blackout.objects.filter(
                id = int(request.GET.get('id', '0'))))
        b.delete()
        return HttpResponseRedirect("/profile/%s" % u_id)
        
    if request.POST.get('_method', '') == 'PUT':
        b = first(Blackout.objects.filter(id = request.POST.get('id', '0')))
    else:
        b = Blackout(user = user)

    # Convert blackout to UTC.
    utcOffset = first(TimeZone.objects.filter(timeZone = request.POST['tz'])).utcOffset()
    if request.POST['start'] != '':
        b.start = datetime.strptime(
            "%s %s" % (request.POST['start'], request.POST['starttime'])
          , "%m/%d/%Y %H:%M") + utcOffset
    if request.POST['end'] != '':
        b.end = datetime.strptime(
            "%s %s" % (request.POST['end'], request.POST['endtime'])
          , "%m/%d/%Y %H:%M") + utcOffset
    if request.POST['until'] != '':
        until = datetime.strptime(
            "%s %s" % (request.POST['until'], request.POST['untiltime'])
          , "%m/%d/%Y %H:%M") + utcOffset

    b.repeat      = first(Repeat.objects.filter(repeat = request.POST['repeat']))
    b.description = request.POST['description']
    b.save()
        
    return HttpResponseRedirect("/profile/%s" % u_id)
