from django.core.management import setup_environ
import settings
setup_environ(settings)

from datetime        import date, datetime, timedelta
from sesshuns.models import *
from sets            import Set

import calendar

ALL_PERIODS = [p for p in Period.objects.all() if p.state.abbreviation in ("S", "C")]

def getPeriods():
    return ALL_PERIODS

def filterPeriods(periods, condition):
    "Filters periods according to some critia, e.g. is science?"
    return [p for p in periods if eval(condition)]

def filterPeriodsByDate(periods, start):
    "Returns the periods within a given month and year."
    _, day = calendar.monthrange(start.year, start.month)
    stop  = datetime(start.year, start.month, day, 23, 59, 59)
    ustart = TimeAgent.est2utc(start)
    ustop  = TimeAgent.est2utc(stop)
    return [p for p in periods if (p.start >= ustart or p.end() > ustart) and p.start < ustop]

def normalizePeriodStartStop(period, dt):
    """
    Returns the start/stop time for a period ensuring it stays within the 
    given month.
    """
    start = TimeAgent.utc2est(period.start)
    if start.month != dt.month:
        start = datetime(dt.year, dt.month, 1, 0, 0, 0)

    stop = TimeAgent.utc2est(period.end())
    if stop.month != dt.month:
        _, day = calendar.monthrange(dt.year, dt.month)
        stop = datetime(dt.year, dt.month, day, 23, 59, 59)

    return start, stop

def getTime(periods, month):
    periods.sort(key = lambda x: x.start)
    ss = [(stop - start).seconds / 3600. for start, stop in [normalizePeriodStartStop(p, month) for p in periods]]
    #f = open("stuff%d.txt" % month.month, "w")
    #for p, s in zip(periods, ss):
    #    f.write("%s, %s, %s\n" % (p.session.project.pcode, p.start, s))
    #f.close()
    return sum([(stop - start).seconds / 3600. \
                 for start, stop in [normalizePeriodStartStop(p, month) \
                                     for p in periods]])

def getScheduledTime(month):
    "Returns scheduled astronomy time for this month."
    periods = filterPeriodsByDate(filterPeriods(getPeriods(), 'p.session.project.is_science()'), month)
    return getTime(periods, month)
    
def getDowntime(month):
    periods = filterPeriodsByDate(filterPeriods(getPeriods(), 'p.session.project.is_science()'), month)
    return sum([p.accounting.lost_time() for p in periods])

def getMaintenance(month):
    periods = filterPeriodsByDate(filterPeriods(getPeriods(), 'p.session.project.is_maintenance()'), month)
    return getTime(periods, month)

def getTesting(month):
    periods = filterPeriodsByDate(filterPeriods(getPeriods(), 'p.session.project.is_test() or p.session.project.is_commissioning() or p.session.project.is_calibration()'), month)
    return getTime(periods, month)

def getShutdown(month):
    periods = filterPeriodsByDate(filterPeriods(getPeriods(), 'p.session.project.pcode == "Shutdown"'), month)
    return getTime(periods, month)

def printSummary(outfile, label, items):
    outfile.write("%s %s %s %s %s\n" % \
                  (label
                 , ("%.1f" % sum(items)).center(8)
                 , ("%.1f" % items[0]).center(8)
                 , ("%.1f" % items[1]).center(8)
                 , ("%.1f" % items[2]).center(8)))

def GenerateReport(label, months):
    assert len(months) == 3, "Are we still doing quarters?"

    outfile = open("./NSFReport.txt", 'w')

    outfile.write("GBT %s   %s %s %s %s\n" % \
                  (label
                 , 'Total'
                 , months[0].strftime("%B").center(8)
                 , months[1].strftime("%B").center(8)
                 , months[2].strftime("%B").center(8)))

    scheduled = [getScheduledTime(m) for m in months]
    downtime  = [getDowntime(m) for m in months]
    astronomy = [s - d for s, d in zip(scheduled, downtime)]

    printSummary(outfile, "Scheduled   ",   scheduled)
    printSummary(outfile, "   Astronomy",   astronomy)
    printSummary(outfile, "   Downtime",    downtime)

    maintenance = [getMaintenance(m) for m in months]
    printSummary(outfile, "Maintenance ", maintenance)

    testing = [getTesting(m) for m in months]
    printSummary(outfile, "Test        ", testing)

    shutdown = [getShutdown(m) for m in months]
    printSummary(outfile, "Shutdown    ", shutdown)

    total = zip(scheduled, maintenance, testing, shutdown)
    outfile.write("%s %s %s %s %s\n" % \
                  ('Total Hours '
                 , ("%.1f" % sum([sum(t) for t in total])).center(8)
                 , ("%.1f" % sum(total[0])).center(8)
                 , ("%.1f" % sum(total[1])).center(8)
                 , ("%.1f" % sum(total[2])).center(8)))

def show_help():
    print "\nThe arguments to NSFReport are:"
    print "\t<integer quarter> <integer fiscal year>\n\n"

if __name__=='__main__':
    import sys

    if len(sys.argv) != 3:
        show_help()
        sys.exit()

    quarters = {
        1: [10, 11, 12]
      , 2: [1, 2, 3]
      , 3: [4, 5, 6]
      , 4: [7, 8, 9]
    }

    quarter     = int(sys.argv[1])
    fiscal_year = int(sys.argv[2])

    months = quarters[quarter]
    year   = fiscal_year if quarter != 1 else fiscal_year - 1

    GenerateReport('Q%dFY%d' % (quarter, fiscal_year)
                 , [datetime(year, m, 1) for m in months])
