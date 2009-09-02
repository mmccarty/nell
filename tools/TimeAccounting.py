from datetime import datetime, timedelta

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

    def getObservedProjTime(self, proj):
        ss = proj.sesshun_set.all()
        return sum([self.getObservedTime(s) for s in ss])

    def getObservedTime(self, sess):
        now = datetime.utcnow()
        ps = sess.period_set.all()
        return sum([p.duration for p in ps if (p.start + timedelta(hours=p.duration)) < now])
        
    def getTimeLeft(self, sess):
        obs = self.getObservedTime(sess)
        return sess.allotment.total_time - obs
