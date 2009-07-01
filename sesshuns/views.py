from django.template          import Context, loader
from django.http              import HttpResponse
from django_restapi.resource  import Resource
from django.db.models         import Q
from django.shortcuts         import render_to_response
from models                   import *
from utilities                import TimeAgent
from settings                 import PROXY_PORT

from datetime import date, datetime, timedelta
import simplejson as json

class NellResource(Resource):
    def __init__(self, dbobject, *args, **kws):
        self.dbobject = dbobject
        super(NellResource, self).__init__(*args, **kws)

    def create(self, request, *args, **kws):
        method = request.POST.get("_method", None)
        if method == "put":
            return self.update(request, *args, **kws)
        elif method == "delete":
            return self.delete(request, *args, **kws)
        else:
            return self.create_worker(request, *args, **kws)

    def create_worker(self, request, *args, **kws):
        o = self.dbobject()
        o.init_from_post(request.POST)
        # Query the database to insure data is in the correct data type
        o = first(self.dbobject.objects.filter(id = o.id))
        
        return HttpResponse(json.dumps(o.jsondict())
                          , mimetype = "text/plain")

    def update(self, request, *args, **kws):
        id    = int(args[0])
        o     = self.dbobject.objects.get(id = id)
        o.update_from_post(request.POST)

        return HttpResponse("")

    def delete(self, request, *args):
        id = int(args[0])
        o  = self.dbobject.objects.get(id = id)
        o.delete()
        
        return HttpResponse(json.dumps({"success": "ok"}))

class ProjectResource(NellResource):
    def __init__(self, *args, **kws):
        super(ProjectResource, self).__init__(Project, *args, **kws)

    def create(self, request, *args, **kws):
        return super(ProjectResource, self).create(request, *args, **kws)
    
    def read(self, request, *args, **kws):
        sortField = request.GET.get("sortField", "id")
        sortField = "id" if sortField == "null" else sortField
        order     = "-" if request.GET.get("sortDir", "ASC") == "DESC" else ""

        projects = Project.objects.order_by(order + sortField)
        total    = len(projects)
        offset   = int(request.GET.get("offset", 0))
        limit    = int(request.GET.get("limit", 50))
        projects = projects[offset:offset+limit]
        return HttpResponse(json.dumps(dict(total = total
                                          , projects = [p.jsondict() for p in projects]))
                          , content_type = "application/json")

class SessionResource(NellResource):
    def __init__(self, *args, **kws):
        super(SessionResource, self).__init__(Sesshun, *args, **kws)
 
    def create(self, request, *args, **kws):
        return super(SessionResource, self).create(request, *args, **kws)

    def read(self, request, *args, **kws):
        if len(args) == 0:
            sortField = jsonMap.get(request.GET.get("sortField", "id"), "id")
            order     = "-" if request.GET.get("sortDir", "ASC") == "DESC" else ""

            filterText = request.GET.get("filterText", None)
            if filterText is None:
                sessions = Sesshun.objects.order_by(order + sortField)
            else:
                sessions = Sesshun.objects.filter(Q(name__contains=filterText) |\
                    Q(project__pcode__contains=filterText) |\
                    Q(project__semester__semester__contains=filterText) |
                    Q(session_type__type__contains=filterText) |
                    Q(observing_type__type__contains=filterText)).\
                    order_by(order + sortField)
            total  = len(sessions)
            offset = int(request.GET.get("offset", 0))
            limit  = int(request.GET.get("limit", 50))
            sessions = sessions[offset:offset+limit]
            return HttpResponse(json.dumps(dict(total = total
                                              , sessions = [s.jsondict() for s in sessions]))
                              , content_type = "application/json")
        else:
            s_id  = args[0]
            s     = first(Sesshun.objects.filter(id = s_id))
            return HttpResponse(json.dumps(dict(session = s.jsondict())))

def receivers_schedule(request, *args, **kws):
    startdate = request.GET.get("startdate", None)
    if startdate is not None:
        d, t      = startdate.split(' ')
        y, m, d   = map(int, d.split('-'))
        h, mm, ss = map(int, map(float, t.split(':')))
        startdate = datetime(y, m, d, h, mm, ss)
    duration = request.GET.get("duration", None)
    if duration is not None:
        duration = int(duration)
    schedule = Receiver_Schedule.extract_schedule(startdate, duration)
    return HttpResponse(
            json.dumps({"schedule" : Receiver_Schedule.jsondict(schedule)})
          , mimetype = "text/plain")

def get_options(request, *args, **kws):
    projects = Project.objects.order_by('pcode')
    return HttpResponse(json.dumps({'project codes' : [ p.pcode for p in projects]})
                      , mimetype = "text/plain")

def get_schedule(request, *args, **kws):
    #  This:
    # static two-day display
    now = TimeAgent.quarter(datetime.utcnow())
    periods = Period.objects.filter(start__gte=now).filter(start__lte=(now+timedelta(days=2))).order_by('start')
    end = now
    #   Or:
    # for now, show all periods so we can see affect of calling antioch
    #periods = Period.objects.all()
    #end = datetime(2009, 6, 1, 0, 0, 0)

    pfs = []
    for p in periods:
        # Is there a hole between periods?
        if end < p.start:
            # that is within a day?
            if p.start.day == end.day:
                dur = p.start - end
                pfs.append(
                    createPeriodDict(end, 24*dur.days + dur.seconds/3600.))
            # or is spanning over midnight?
            else:
                p_start_end = TimeAgent.truncateDt(p.start)
                pfs.append(
                    createPeriodDict(end,
                                     TimeAgent.timedelta2minutes(p_start_end - end)/60.))
                pfs.append(
                    createPeriodDict(p_end_start,
                                     TimeAgent.timedelta2minutes(p.start - p_start_end)/60.))
        # or an overlap?
        elif p.start < end:
            pass
        # that is within a day?
        p_end = p.start + timedelta(hours=p.duration)
        if p.start.day == p_end.day:
            pfs.append(createPeriodDict(p.start, p.duration, p))
        # or is spanning over midnight?
        else:
            p_end_start = TimeAgent.truncateDt(p_end)
            pfs.append(createPeriodDict(p.start,
                                        TimeAgent.timedelta2minutes(
                                                p_end_start - p.start)/60.,
                                        p))
            pfs.append(createPeriodDict(p_end_start,
                                        TimeAgent.timedelta2minutes(
                                                p_end - p_end_start)/60.,
                                        p,
                                        " (cont)"))
        end = p.start + timedelta(hours=p.duration)
    proxyPort = PROXY_PORT 
    action = "http://trent.gb.nrao.edu:%d/schedule_algo" % proxyPort
    return render_to_response('sessions/schedule/index.html'
                            , {'periods': periods
                            ,  'pfs': pfs
                            ,  'action' : action})

def createPeriodDict(start, dur, per = None, suffix = ""):
    strt = start - datetime(year = start.year, month=start.month, day=start.day)
    day  = date(year = start.year, month=start.month, day=start.day)
    nqtr = int(round(60*dur)/15)
    return dict(
        sname = "" if per is None else per.session.name + suffix
      , stype = "" if per is None else per.session.observing_type.type
      , date  = str(day)
      , start = str(strt)[:-3]
      , dur   = str(nqtr)
      , durs  = [str(strt + timedelta(minutes=q))[:-3] for q in range(15, 15*nqtr, 15)]
      , freq  = "" if per is None else str(per.session.frequency) if per.session.observing_type.type != 'maintenance' else "&nbsp;"
      , notes = "" if per is None else 'backup' if per.backup else "&nbsp;"
                   )
