# Copyright (C) 2011 Associated Universities, Inc. Washington DC, USA.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# 
# Correspondence concerning GBT software should be addressed as follows:
#       GBT Operations
#       National Radio Astronomy Observatory
#       P. O. Box 2
#       Green Bank, WV 24944-0002 USA

#! /usr/bin/env python
from django.core.management import setup_environ
import settings
setup_environ(settings)

from scheduler.models import *
from reversion.models import Version
from RevisionReport import RevisionReport

class ProjectRevReport(RevisionReport):

    def __init__(self, filename = None):
        super(ProjectRevReport, self).__init__(filename)
        #RevisionReport.__init__(self)
       
        self.relatedClasses = ['Investigator'
                             , 'Allotment'
                              ]

    def reportProject(self, pcode, time = None, field = None):
        self.add("Revision Report for Project: %s\n\n" % pcode)
        p = Project.objects.get(pcode = pcode)
        self.reportObject(p, time, field)
        self.add("\nDiffs:\n")
        self.reportProjectDiffs(pcode)
        self.write()

    def reportProjectForTime(self, pcode, timeStr):
        self.add("Project: %s at %s\n\n" % (pcode, timeStr))
        p = Project.objects.get(pcode = pcode)
        self.reportObjectForTime(p, timeStr)
        self.write()    

    #def reportAllotments(self, pcode, time = None, field = None):
    #    p = Project.objects.get(pcode = pcode)
    #    for a in p.allotments.all():
    #        self.reportObject(a, time, field)
    #        #reportObjectDiffs(a)
    
    def reportProjectDiffs(self, pcode):

        self.add("Differences for Project: %s \n\n" % pcode)
        diffs = []
        p = Project.objects.get(pcode = pcode)
        diffs.extend(self.getObjectDiffs(p))
        for a in p.allotments.all():
            diffs.extend(self.getObjectDiffs(a))
        for i in p.investigator_set.all():
            diffs.extend(self.getObjectDiffs(i))
        diffs.sort(key=lambda d: d.dt)
        for d in diffs:
            self.add("%s\n" % d)
        self.write()    
    
    def reportDeletedProject(self, pcode):
        # we could get the obj we want if we had the PK ID! but we don't ...
        deleted_list = Version.objects.get_deleted(Project)
        for d in deleted_list:
            if d.object_version.object.pcode == pcode:
                self.reportVersion(d)
        self.write()


    def runFromCommandLine(self, args):

        msg = None
        keys = ['pcode', 'type']
        types = ['history', 'diffs', 'time']

        # first check of arguments
        opts, msg = self.parseOptions(args[1:], keys)
        if msg is not None:
            return msg
        type  = opts['type']    
        pcode = opts['pcode']    
        if type not in types:
            return "type arg must be in type: %s" % (", ".join(types))

        # what type of report to run?
        if type == 'history':
            self.reportProject(pcode)
        elif type == 'diffs':
            self.reportProjectDiffs(pcode)
        elif type == 'time':
            timeStr = opts.get('time', None)
            if timeStr is None:
                return "type=time must include time option"
            self.reportProjectForTime(pcode, timeStr)
        else:
            return "Type %s not supported" % type
        return msg


def show_help(program):
    print "\nThe arguments to", program, "are:"
    print "\t-pcode=pcode -name=name -type=type [-time=time]"
    print "\nwhere:"
    print "\tpcode = project code, in double quotes"
    print "\ttype  = one of [history, diffs, time]"
    print "\ttime  = if 'time' type chosen, the time in YY-mm-dd HH:MM:SS"
    print "\nAll required arguments are required.  Anything else is optional :)"

if __name__ == '__main__':

    import sys

    if len(sys.argv) < 2:
        show_help(sys.argv[0])
        sys.exit()
    else:    
        filename = "ProjectRevReport.txt"
        pr = ProjectRevReport(filename = filename)                 
        msg = pr.runFromCommandLine(sys.argv)
            
        if msg is not None:
            print msg
            print ""
            show_help(sys.argv[0])
            sys.exit()
                    
