# Copyright (C) 2009 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 675 Mass Ave Cambridge, MA 02139, USA.
#
# Correspondence concerning GBT software should be addressed as follows:
#     GBT Operations
#     National Radio Astronomy Observatory
#     P. O. Box 2
#     Green Bank, WV 24944-0002 USA

from   Notifier  import Notifier
from   datetime  import datetime, timedelta
from   sets      import Set
import TimeAgent

class SchedulingNotifier(Notifier):
 
    def __init__(self
               , periods
               , skipEmails = []
               , test       = False
               , log        = False):
        Notifier.__init__(self, skipEmails, test, log)

        self.examinePeriods(periods)
        #self.periods = periods

        self.periods.sort(lambda x, y: cmp(x.start, y.start))

        if self.periods != []:
            self.startdate = periods[0].start
            self.enddate   = periods[-1].end()
        else:
            self.startdate = datetime.utcnow()
            self.enddate   = self.startdate + timedelta(hours = 48)

        # by default, set the class up for notifying obsevers of what
        # will be obseved in the next time period
        self.createObservingAddresses()
        self.createObservingSubject()
        self.createBody()

    def examinePeriods(self, periods):
        """
        This class must notify observers of eminent observations, *and*
        remind observers of things that have changed.  Here we filter out
        the two purposes from our generic list of periods.
        """

        self.periods = periods

        # the list of periods for scheduling (upcoming observations) includes
        # everything *but* the deleted periods.
        self.observingPeriods = \
            sorted([p for p in periods if not p.isDeleted()])

        # the list of periods that we must list to remind obs. of changes:
        self.changedPeriods = sorted([p for p in periods if p.isDeleted() or \
                                   p.accounting.of_interest()])
                              
        # deleted periods must also be tracked separately, because those
        # observers will get an email with a different subject
        self.deletedPeriods = sorted([p for p in periods if p.isDeleted()])

    def notify(self):
        "send out all the different emails"
        # notify the obs; subject = "Your GBT Project has been scheduled..."
        Notifier.notify(self)

        # now let the people who aren't observing know, but who
        # might have been in scheduled in the past
        self.createDeletedAddresses()
        self.createDeletedSubject()
        if len(self.getAddresses()) != 0:
            Nofitier.notify(self)

        # now let the staff know - "GBT schedule for ..."
        self.createStaffAddresses()
        self.createStaffSubject()
        Notifier.notify(self)

    def createStaffAddresses(self):
        self.setAddresses(["gbtops@gb.nrao.edu", "gbtlocal@gb.nrao.edu", "gbtime@gb.nrao.edu"])
        self.logMessage("Staff To: %s\n" % self.getAddresses())

    def createObservingAddresses(self):
        "get addresses of only those who are observing"
        self.createAddresses(self.observingPeriods)

    def createDeletedAddresses(self):
        "get addresses of only those who had periods originally scheduled"
        self.createAddresses(self.deletedPeriods)

    def createAddresses(self, periods):
        # Make sure we get succinct list of observers because we need to
        # query the user db and we should minimize the number of calls.
        observers = [o.user for p in periods \
                            for o in p.session.project.get_observers()]
        observers.extend([p.session.project.principal_contact() \
                          for p in periods \
                          if p.session.project.principal_contact() is not None])
                          
        observers = Set(observers)

        if not self.test:
            # get email addresses from the PST
            addresses = Set([e for o in observers \
                           for e in o.getStaticContactInfo()['emails']])
        else:
            # for testing, we don't want to use the PST server
            # so just make up some emails
            addresses = Set(["%s@test.edu" % o.first_name for o in observers])

        self.setAddresses(list(addresses))

        self.logMessage("To: %s\n" % self.getAddresses())

    def createStaffSubject(self):
        self.setSubject("GBT schedule for %s-%s" % \
                        (TimeAgent.utc2est(self.startdate).strftime('%b %d')
                       , TimeAgent.utc2est(self.enddate).strftime('%b %d')))
        self.logMessage("Staff Subject: %s\n" % self.getSubject())

    def createDeletedSubject(self):
        self.setSubject("Reminder: GBT Schedule has changed.")
        self.logMessage("Subject: %s\n" % self.getSubject())

    def createObservingSubject(self):
        self.setSubject("Your GBT project has been scheduled (%s-%s)" % \
                        (TimeAgent.utc2est(self.startdate).strftime('%b %d')
                       , TimeAgent.utc2est(self.enddate).strftime('%b %d')))
        self.logMessage("Subject: %s\n" % self.getSubject())

    def createBody(self):
        self.setBody("""
Dear Colleagues,

The schedule for the period %s ET through %s ET is fixed and available.

%s
%s
Please log into https://dss.gb.nrao.edu to view your observation
related information.

Any requests or problems with the schedule should be directed
to helpdesk-dss@gb.nrao.edu.

Happy Observing!
""" % (TimeAgent.utc2est(self.startdate).strftime('%b %d %H:%M')
     , TimeAgent.utc2est(self.enddate).strftime('%b %d %H:%M')
     , self.getSessionTable(self.observingPeriods)
     , self.getChanges()))

        self.logMessage("Body: %s\n" % self.getBody())

    def createDeletedBody(self):
        self.setBody("""
Dear Colleagues,

This is a reminder that the following projects had been scheduled 
between %s ET through %s ET, but have been removed from the schedule.

%s

Please log into https://dss.gb.nrao.edu to view your observation
related information.

Any requests or problems with the schedule should be directed
to helpdesk-dss@gb.nrao.edu.

Thank You.
""" % (TimeAgent.utc2est(self.startdate).strftime('%b %d %H:%M')
     , TimeAgent.utc2est(self.enddate).strftime('%b %d %H:%M')
     , self.getSessionTable(self.deletedPeriods)
     ))
  
        self.logMessage("Body: %s\n" % self.getBody())

    def getSessionTable(self, periods):
        table  = "Start (ET)   |      UT      |  LST  |  (hr) | Observer  | Rx        | Session\n"
        table += "------------------------------------------------------------------------------\n"
        for p in periods:
            if p.session.project.pcode == "Maintenance":
                observer = ""
            else:
                observer = p.session.project.get_observers()[0].user.last_name[:9] if p.session.project.get_observers() else "Unknown"

            table += "%s | %s | %s | %5s | %-9s | %-9s | %s\n" % (
                TimeAgent.utc2est(p.start).strftime('%b %d %H:%M')
              , p.start.strftime('%b %d %H:%M')
              , TimeAgent.dt2tlst(p.start).strftime('%H:%M')
              , "%2.2f" % p.duration
              , observer
              , p.session.receiver_list_simple()[:9]
              , p.session.name
            )
        return table

    def getChanges(self):
        if len(self.changedPeriods) == 0:
            changes = ""
        else:
            changes = "Changes made to the schedule:\n %s" % \
                self.getChangeTable()
        return changes        

    def getChangeTable(self):
        table  = "Start (ET)   |      UT      |  LST  |  (hr) | Observer  | Rx        | Session | Change\n"
        table += "------------------------------------------------------------------------------\n"
        for p in self.changedPeriods:
            if p.session.project.pcode == "Maintenance":
                observer = ""
            else:
                observer = p.session.project.get_observers()[0].user.last_name[:9] if p.session.project.get_observers() else "Unknown"

            table += "%s | %s | %s | %5s | %-9s | %-9s | %s | %s\n" % (
                TimeAgent.utc2est(p.start).strftime('%b %d %H:%M')
              , p.start.strftime('%b %d %H:%M')
              , TimeAgent.dt2tlst(p.start).strftime('%H:%M')
              , "%2.2f" % p.duration
              , observer
              , p.session.receiver_list_simple()[:9]
              , p.session.name
              , "rescheduled" if not p.isDeleted() else "removed"
            )
        return table

