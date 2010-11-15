from datetime               import datetime
from PeriodHttpAdapter      import PeriodHttpAdapter
from SessionHttpAdapter     import SessionHttpAdapter
from sesshuns.models        import Period, Sesshun
from sesshuns.models.common import *

class ElectiveHttpAdapter (object):

    def __init__(self, elective):
        self.elective = elective

    def load(self, elective):
        self.elective = elective

    def jsondict(self):
        minMax = self.elective.periodDateRange()
        js = {  "id"             : self.elective.id
              , "handle"         : self.elective.toHandle()
              , "session"        : SessionHttpAdapter(self.elective.session).jsondict()
              , "complete"       : self.elective.complete
              , "firstPeriod"    : dt2str(minMax[0])
              , "lastPeriod"     : dt2str(minMax[1])
              , "periods"        : [PeriodHttpAdapter(p).jsondict('UTC', 0.0) for p in self.elective.periods.all()]
              }
        return js    

    def init_from_post(self, fdata):
        self.from_post(fdata)

    def update_from_post(self, fdata):
        self.from_post(fdata)

    def from_post(self, fdata):

        # most likely, we'll be specifying sessions for windows in the same
        # manner as we do for periods
        handle = fdata.get("handle", "")
        if handle:
            self.elective.session = self.elective.handle2session(handle)
        else:
            try:
                maintenance = first(Project.objects.filter(pcode='Maintenance'))
                self.elective.session = first(Sesshun.objects.filter(project=maintenance))
            except:
                self.elective.session  = Sesshun.objects.get(id=fdata.get("session", 1))


        self.elective.setComplete(fdata.get("complete", "false") == "true")

        self.elective.save()                
