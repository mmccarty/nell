from datetime                 import datetime, timedelta
from django.http              import HttpResponse, HttpResponseRedirect

from NellResource    import NellResource
from sesshuns.models import Period, first, jsonMap, str2dt
from sesshuns.httpadapters import PeriodHttpAdapter
from utilities       import TimeAgent
from utilities       import Score
#from utilities       import formatExceptionInfo

import simplejson as json
import reversion
from reversion import revision

import sys
import traceback

def formatExceptionInfo(maxTBlevel=5):
    cla, exc, trbk = sys.exc_info()
    excName = cla.__name__
    try:
        excArgs = exc.__dict__["args"]
    except KeyError:
        excArgs = "<no args>"
        excTb = traceback.format_tb(trbk, maxTBlevel)
    return (excName, excArgs, excTb)


class PeriodResource(NellResource):
    def __init__(self, *args, **kws):
        super(PeriodResource, self).__init__(Period, PeriodHttpAdapter, *args, **kws)
        self.score_period = Score()

    def read(self, request, *args, **kws):

        tz = args[0]
        # one or many?
        if len(args) == 1:
            # we are getting periods from within a range of dates
            sortField    = jsonMap.get(request.GET.get("sortField", "start"), "start")
            order        = "-" if request.GET.get("sortDir", "ASC") == "DESC" else ""
            startPeriods = request.GET.get("startPeriods"
                                         , datetime.now().strftime("%Y-%m-%d"))
            daysPeriods  = request.GET.get("daysPeriods", "1")
            dt           = str2dt(startPeriods)
            start        = dt if tz == 'UTC' else TimeAgent.est2utc(dt)
            duration     = int(daysPeriods) * 24 * 60
            periods      = Period.get_periods(start, duration)
            pids         = [p.id for p in periods]
            sd           = self.score_period.periods(pids)
            scores       = [sd.get(pid, 0.0) for pid in pids]
            return HttpResponse(
                json.dumps(dict(total   = len(periods)
                              , periods = [PeriodHttpAdapter(p).jsondict(tz, s)
                                           for (p, s) in zip(periods, scores)]
                              , success = 'ok'))
              , content_type = "application/json")
        else:
            # we're getting a single period as specified by ID
            p_id    = int(args[1])
            p       = first(Period.objects.filter(id = p_id))
            score   = self.score_period.periods([p_id]).get(p_id, 0.0)
            adapter = PeriodHttpAdapter(p)
            return HttpResponse(
                json.dumps(dict(period  = adapter.jsondict(tz, score)
                              , success = 'ok'))
              , content_type = "application/json")

    @revision.create_on_success
    def create_worker(self, request, *args, **kws):
        o = self.dbobject()
        tz = args[0]
        adapter = PeriodHttpAdapter(o)
        adapter.init_from_post(request.POST, tz)
        # Query the database to insure data is in the correct data type
        o = first(self.dbobject.objects.filter(id = o.id))
        score = self.score_period.periods([o.id]).get(o.id, 0.0)
        
        revision.comment = self.get_rev_comment(request, o, "create_worker")

        return HttpResponse(json.dumps(adapter.jsondict(tz, score))
                          , mimetype = "text/plain")

    @revision.create_on_success
    def update(self, request, *args, **kws):
        tz    = args[0]
        id    = int(args[1])
        o     = self.dbobject.objects.get(id = id)
        adapter = PeriodHttpAdapter(o)
        adapter.update_from_post(request.POST, tz)

        revision.comment = self.get_rev_comment(request, o, "update")

        return HttpResponse(json.dumps({"success": "ok"})
                          , mimetype = "text/plain")

    @revision.create_on_success
    def delete(self, request, *args):
        id = int(args[1])
        o  = self.dbobject.objects.get(id = id)
        revision.comment = self.get_rev_comment(request, o, "delete")        
        o.delete()

        return HttpResponse(json.dumps({"success": "ok"})
                          , mimetype = "text/plain")

