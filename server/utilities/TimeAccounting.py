from sesshuns.models import *

class TimeAccounting:

    """
    This class is responsible for calculating the equations specified in
    Memo 10.2.
    """

    def getProjectTotalTime(self, proj):
        return sum([a.total_time for a in proj.allotments.all()])

    def getProjSessionsTotalTime(self, proj):
        ss = proj.sesshun_set.all()
        return sum([s.allotment.total_time for s in ss])
