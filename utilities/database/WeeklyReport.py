from django.core.management import setup_environ
import settings
setup_environ(settings)

from sesshuns.models import *
from sets            import Set
from datetime        import date,datetime,timedelta

def print_values(file, values):
    if values == []:
        file.write("\tNone\n")
    else:
        for v in values:
            file.write("\t%s\n" % v)

def GenerateReport(start):
    outfile    = open("./DssWeeklyReport.txt", 'w')
    end        = start + timedelta(days = 7)
    next_start = end + timedelta(days = 1)
    next_end   = end + timedelta(days = 7)
    periods    = [p for p in Period.objects.all() if p.state.abbreviation in ("S", "C")]

    outfile.write("Last 7 days (%s to %s)\n" % (start.strftime("%m/%d/%Y")
                                              , end.strftime("%m/%d/%Y")))
    outfile.write("======================================\n")

    observed_periods = \
        sorted(Set([p for p in periods \
                      if overlaps((p.start, p.end()), (start, end))]))
    upcoming_periods = \
        sorted(Set([p for p in periods \
                      if overlaps((p.start, p.end())
                                , (next_start, next_end))]))

    outfile.write("Observations for proposals\n")
    print_values(outfile
               , Set([p.session.project.pcode for p in observed_periods]))

    outfile.write("\nCompleted proposals\n")
    print_values(outfile, Set([p.session.project.pcode \
                               for p in observed_periods \
                               if p.session.project.complete]))

    outfile.write("\nNext Week\n")
    outfile.write("=========\n")
    outfile.write("Observations scheduled for %s - %s (note this only includes pre-scheduled projects):\n" % (next_start.strftime("%m/%d/%Y"), next_end.strftime("%m/%d/%Y")))
    values = ["%s, [%s], PI: %s\n\t\t%s\n\t\t%s" % \
              (p.session.project.pcode
             , p.session.observing_type.type
             , p.session.project.principal_investigator()
             , p.session.project.name
             , p.__str__())
              for p in upcoming_periods]
    print_values(outfile, Set(values))

    projects = Set([p.session.project for p in upcoming_periods])
    outfile.write("\nContact Information for pre-scheduled projects for %s - %s\n" % (next_start.strftime("%m/%d/%Y"), next_end.strftime("%m/%d/%Y")))
    outfile.write("==========================================================================\n")
    outfile.write("\tProject     PI                 Bands Email [NRAO contact]\n")
    outfile.write("\t----------- ------------------ ----- --------------------\n")
    values = ["%s %s %s %s [%s]" % \
                  (p.pcode.ljust(11)
                 , str(p.principal_investigator())[:17].ljust(18)
                 , ",".join(p.rcvrs_specified())[:4].center(5)
                 , first(p.principal_investigator().getStaticContactInfo()['emails'])
                 , p.friend
                 )
              for p in projects]
    print_values(outfile, Set(values))

    last_month   = start - timedelta(days = 31)
    last_periods = [p for p in periods \
                      if p.start.month == last_month.month and \
                         p.start.year  == last_month.year]
    this_periods = [p for p in periods \
                      if p.start.month == start.month and \
                         p.start.year  == start.year]


    outfile.write("\nScheduled Hours [backup]\n")
    outfile.write("========================\n")
    outfile.write("Category/Month -> %s %s\n" % \
                  (last_month.strftime("%B").center(8)
                 , start.strftime("%B").center(8)))
    outfile.write("     Astronomy ~  %s %s\n" % \
                  (("%.1f" % \
                   sum([p.accounting.scheduled for p in last_periods \
                   if p.session.project.project_type.type == "science"])).center(8)
                 , ("%.1f" % \
                   sum([p.accounting.scheduled for p in this_periods \
                   if p.session.project.project_type.type == "science"])).center(8)))
    outfile.write("   Maintenance ~  %s %s\n" % \
                  (("%.1f" % \
                   sum([p.accounting.scheduled for p in last_periods \
                   if p.session.project.pcode == "Maintenance"])).center(8)
                ,  ("%.1f" % \
                   sum([p.accounting.scheduled for p in this_periods \
                   if p.session.project.pcode == "Maintenance"])).center(8)))
    outfile.write("   Test & Comm ~  %s %s\n" % \
                  (("%.1f" % \
                   sum([p.accounting.scheduled for p in last_periods \
                        if p.session.project.pcode[0] == "T"])).center(8)
                 , ("%.1f" % \
                   sum([p.accounting.scheduled for p in this_periods \
                        if p.session.project.pcode[0] == "T"])).center(8)))
    outfile.write("      Shutdown ~  %s %s\n" % \
                  (("%.1f" % \
                   sum([p.accounting.scheduled for p in last_periods \
                        if p.session.project.pcode == "Shutdown"])).center(8)
                 , ("%.1f" % \
                   sum([p.accounting.scheduled for p in this_periods \
                        if p.session.project.pcode == "Shutdown"])).center(8)))

    ta         = TimeAccounting()
    pSemesters = Semester.getPreviousSemesters(start)
    backlog    = [p for p in Project.objects.all() if p.semester in pSemesters]
    outfile.write(
        "\nCurrent backlog of Reg & RSS proposals [hours prior to %s*] = %.1f\n" % \
            (Semester.getCurrentSemester(start)
           , sum([ta.getTimeLeft(p) for p in backlog])))
    outfile.write("\t[")
    outfile.write(", ".join(["%s: %.1f (%d)" % \
       (y 
      , sum([ta.getTimeLeft(p) for p in backlog if p.semester.start().year == y])
      , len([p for p in backlog if p.semester.start().year == y]))
        for y in sorted(list(Set([s.start().year for s in Semester.getPreviousSemesters(start)])))]))
    outfile.write("]\n")
    outfile.write("\tBacklog includes %.1f hours of monitoring projects\n" % \
                  sum([ta.getTimeLeft(p) for p in backlog \
                       if any([s.session_type.type == "windowed" \
                               for s in p.sesshun_set.all()])]))
    outfile.write("\t                 %.1f hours of vlbi projects\n" % \
                  sum([ta.getTimeLeft(p) for p in backlog \
                       if any([s.observing_type.type == "vlbi" \
                               for s in p.sesshun_set.all()])]))

    cSemester  = Semester.getCurrentSemester(start)
    fSemesters = Semester.getFutureSemesters(start)
    total_time = sum([ta.getTimeLeft(p) for p in Project.objects.all()])
    monitoring = sum([ta.getTimeLeft(p) for p in backlog \
                       if any([s.session_type.type == "windowed" \
                               for s in p.sesshun_set.all()]) and \
                          ta.getProjectTotalTime(p) <= 200.])
    vlbi       = sum([ta.getTimeLeft(p) for p in backlog \
                       if any([s.observing_type.type == "vlbi" \
                               for s in p.sesshun_set.all()])])
    large      = sum([ta.getTimeLeft(p) for p in backlog \
                      if ta.getProjectTotalTime(p) > 200.])
    rest       = total_time - monitoring - vlbi - large

    outfile.write("\nTotal time to discharge [hours] = %.1f\n" % total_time)
    outfile.write("\tIncludes %.1f hours of monitoring projects (not Large) after trimester %s\n" % (monitoring, cSemester))
    outfile.write("\t         %.1f hours of Regular & RRS projects\n" % rest)
    outfile.write("\t         %.1f hours of Large projects\n" % large)
    outfile.write("\t         %.1f hours of VLBI projects\n" % vlbi)
    outfile.write("\n* Includes projects that are on hold for trimester %s\n" % cSemester)

    visitors = ["%s - %s - %s" % (r.start_date.strftime("%m/%d/%Y")
                              , r.end_date.strftime("%m/%d/%Y")
                              , r.user.name()) \
                for r in Reservation.objects.filter(
                                      end_date__gte = next_start
                                                   ).filter(
                                      start_date__lte = next_end)]

    outfile.write("\nVisitors coming for %s - %s:\n" % (next_start.strftime("%m/%d/%Y"), next_end.strftime("%m/%d/%Y")))
    print_values(outfile, visitors)

def show_help(program):
    print "\nThe arguments to", program, "are:"
    print "\t<integer day> <integer month> <integer year>"
    print "and represent the date on which you wish the report to start."
    print "\nAll arguments are optional.  You can choose to specify all, any, or none."
    print "Appropriate defaults are chosen (if necessary) based upon today's date."
    print "\nNote: Although all arguments are optional, order matters."
    print "I.e. You cannot specify the month without the day.\n\n"


if __name__=='__main__':
    import sys

    today = datetime.today()

    if len(sys.argv) <= 1:
        start = today

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        show_help(sys.argv[0])
        sys.exit()

    if len(sys.argv) == 2:
        start = datetime(today.year, today.month, int(sys.argv[1]))

    if len(sys.argv) == 3:
        start = datetime(today.year, int(sys.argv[2]), int(sys.argv[1]))

    if len(sys.argv) >= 4:
        start = datetime(int(sys.argv[3]), int(sys.argv[2]), int(sys.argv[1]))

    GenerateReport(start)
