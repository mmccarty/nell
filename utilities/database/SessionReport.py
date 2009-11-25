from django.core.management import setup_environ
import settings
setup_environ(settings)

from sesshuns.models      import *
from tools.TimeAccounting import TimeAccounting
from sets                 import Set
from datetime             import *
from sesshuns.templatetags.custom import *

# TBF: isn't this the same as TimeAccounting.getProjSessionsTotalTime
def get_total_time(project):
    return sum([s.allotment.total_time for s in project.sesshun_set.all()])

def get_remaining_time(project,ta):
    #ta = TimeAccounting()
    return sum([ta.getTimeLeft(s) for s in project.sesshun_set.all()])

def ljust(value, width):
    # watch out for floats
    if type(value) == type(3.14):
        return str("%5.2f" % value)[:width].ljust(width)
    else:    
        return str(value)[:width].ljust(width)

def bl(value):
    return "T" if value else "F"

def GenerateReport(start):
    outfile = open("./DssSessionReport.txt", 'w')
    sorted_semesters=sorted(Semester.objects.all(),lambda x,y:cmp(x.semester,y.semester))
    ta = TimeAccounting()
    pcs = [11, 50, 12, 10, 10]
    scs = [3, 3, 15, 5, 9, 4, 5, 9, 8, 5, 5, 5, 5, 5, 15]
    for s in sorted_semesters:
        outfile.write("\n\n Trimester : %s" %s.semester)
        outfile.write("\n-----------------")
        the_projects=[p for p in s.project_set.all() if not p.complete]
        projects = sorted(the_projects, lambda x,y:cmp(x.pcode, y.pcode))
        if projects:
            outfile.write("\n\n %s \t %s \t %s \t %s \t %s" % \
                (str("pcode").ljust(pcs[0])
               , str("name").ljust(pcs[1])
               , str("PI").ljust(pcs[2])
               , str("total hrs").ljust(pcs[3])
               , str("remaining").ljust(pcs[4])))
            outfile.write("\n" + ("-"*115))   
            for p in projects:
                outfile.write("\n\n %s \t %s \t %s \t %s \t %s" % \
                            (p.pcode.ljust(pcs[0])
                           , p.name[:50].ljust(pcs[1])
                           , p.principal_investigator().last_name.ljust(pcs[2])
                           , str(get_total_time(p)).ljust(pcs[3])
                           , str(get_remaining_time(p,ta)).ljust(pcs[4])
                            ))
                outfile.write("\n\n\t %s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" %\
                       (ljust("sch",            scs[0])
                      , ljust("cmp",            scs[1])
                      , ljust("name",           scs[2])
                      , ljust("orgID",          scs[3])
                      , ljust("obs type",       scs[4])
                      , ljust("type",           scs[5])
                      , ljust("freq",           scs[6])
                      , ljust("RA",             scs[7])
                      , ljust("Dec",            scs[8])
                      , ljust("tot",            scs[9])
                      , ljust("rem",            scs[10])
                      , ljust("min",            scs[11])
                      , ljust("max",            scs[12])
                      , ljust("btn",            scs[13])
                      , ljust("rcvrs",          scs[14])
                      ))
                outfile.write("\n\t" + ("-"*120))                 
                sess = sorted(p.sesshun_set.all(), \
                           lambda x,y:cmp(x.name, y.name))
                for s in sess: #p.sesshun_set.all():

                    outfile.write("\n\t %s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" %\
                        (ljust(bl(s.schedulable()),    scs[0])
                       , ljust(bl(s.status.complete),  scs[1])
                       , ljust(s.name,                 scs[2])
                       , ljust(s.original_id,          scs[3])
                       , ljust(s.observing_type.type,  scs[4])
                       , ljust(s.session_type.type[0], scs[5])
                       , ljust(s.frequency,            scs[6])
                       , ljust(target_horz(s),         scs[7])
                       , ljust(target_vert(s),         scs[8])
                       , ljust(s.allotment.total_time, scs[9])
                       , ljust(ta.getTimeLeft(s),      scs[10])
                       , ljust(s.min_duration,         scs[11])
                       , ljust(s.max_duration,         scs[12])
                       , ljust(s.time_between,         scs[13])
                       , ljust("".join(s.rcvrs_specified()), scs[14])
                       )
                     )
                    
        else:
            outfile.write("\n\t None")

if __name__=='__main__':
    start = datetime.today()
    GenerateReport(start)

