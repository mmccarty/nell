from django.http              import HttpResponse, HttpResponseRedirect
from django.db.models         import Q

from NellResource import NellResource
from sesshuns.models       import Sesshun, first, jsonMap

import simplejson as json

class SessionResource(NellResource):
    def __init__(self, *args, **kws):
        super(SessionResource, self).__init__(Sesshun, *args, **kws)
 
    def create(self, request, *args, **kws):
        return super(SessionResource, self).create(request, *args, **kws)

    def read(self, request, *args, **kws):
        if len(args) == 0:
            sortField = jsonMap.get(request.GET.get("sortField", "pcode"), "project__pcode")
            order     = "-" if request.GET.get("sortDir", "ASC") == "DESC" else ""
            query_set = Sesshun.objects

            filterEnb = request.GET.get("filterEnb", None)
            if filterEnb is not None:
                query_set = query_set.filter(
                    status__enabled = (filterEnb.lower() == "true"))

            filterClp= request.GET.get("filterClp", None)
            if filterClp is not None:
                query_set = query_set.filter(
                    status__complete = (filterClp.lower() == "true"))

            filterType = request.GET.get("filterType", None)
            if filterType is not None:
                query_set = query_set.filter(session_type__type = filterType.lower())

            filterSci = request.GET.get("filterSci", None)
            if filterSci is not None:
                query_set = query_set.filter(observing_type__type = filterSci.lower())

            filterSem = request.GET.get("filterSem", None)
            if filterSem is not None:
                query_set = query_set.filter(project__semester__semester__icontains = filterSem)

            filterRcvr = request.GET.get("filterRcvr", None)
            if filterRcvr is not None:
                query_set = query_set.filter(receiver_group__receivers__abbreviation = filterRcvr)

            filterFreq = request.GET.get("filterFreq", None)
            if filterFreq is not None:
                if ">" in filterFreq:
                    filterFreq = filterFreq.replace(">", "")
                    query_set = query_set.filter(frequency__gt = float(filterFreq))
                elif "<=" in filterFreq:
                    filterFreq = filterFreq.replace("<=", "")
                    query_set = query_set.filter(frequency__lte = float(filterFreq))

            filterText = request.GET.get("filterText", None)
            if filterText is not None:
                query_set = query_set.filter(
                    Q(name__icontains=filterText) |
                    Q(project__pcode__icontains=filterText) |
                    Q(project__semester__semester__icontains=filterText) |
                    Q(session_type__type__icontains=filterText) |
                    Q(observing_type__type__icontains=filterText))
            sessions = query_set.order_by(order + sortField)
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

