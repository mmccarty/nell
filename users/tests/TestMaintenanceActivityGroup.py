######################################################################
#
#  TestMaintenanceActivityGroup.py
#
#  Copyright (C) 2011 Associated Universities, Inc. Washington DC, USA.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#  Correspondence concerning GBT software should be addressed as follows:
#  GBT Operations
#  National Radio Astronomy Observatory
#  P. O. Box 2
#  Green Bank, WV 24944-0002 USA
#
######################################################################

from test_utils            import NellTestCase
from users.models       import *
from scheduler.models      import *
from scheduler.tests.utils import create_maintenance_period, create_maintenance_elective
from datetime              import datetime

class TestMaintenanceActivityGroup(NellTestCase):
    def setUp(self):
        super(TestMaintenanceActivityGroup, self).setUp()
        self.week = datetime(2011, 04, 11)
        per_data = ((datetime(2011, 04, 12, 8), 8),
                    (datetime(2011, 04, 13, 8), 8),
                    (datetime(2011, 04, 14, 8), 8),
                    (datetime(2011, 04, 15, 8), 8))
        self.me1 = create_maintenance_elective(per_data)
        self.me2 = create_maintenance_elective(per_data)
        self.mp1 = create_maintenance_period(datetime(2011, 04, 11, 8), 8,
                                             'Pending')
        self.deleted = Period_State.objects.get(name = 'Deleted')
        self.pending = Period_State.objects.get(name = 'Pending')
        self.scheduled = Period_State.objects.get(name = 'Scheduled')


    def tearDown(self):
        super(TestMaintenanceActivityGroup, self).tearDown()


    def test_maintenance_groups(self):
        # get the maintenance groups for the week of April 11, 2011
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        # there should be 3 maintenance groups: 2 electives, one pending period
        self.assertEqual(len(mags), 3)
        # mag should have period set to None.  Elective not scheduled yet.
        for i in range(0, len(mags)):
            mag = mags[i]
            self.assertEqual(mag.period, None)
            self.assertEqual(mag.rank, chr(65 + i))
            self.assertEqual(mag.get_week(), self.week)
            # not scheduled electives, so mag get_start() should be
            # the same as mag.get_week()
            self.assertEqual(mag.get_start(), mag.get_week())

        self.mp1.state = self.deleted
        self.mp1.save()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week,
                                                                          include_deleted = True)
        # there should still be 3 maintenance groups, but the last one
        # should be marked deleted because of the deleted period.
        self.assertEqual(len(mags), 3)
        self.assertEqual(mags[2].deleted, True)

        # now only return non-deleted ones.
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual(len(mags), 2)
        
        # restore the period.
        self.mp1.state = self.pending
        self.mp1.save()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual(len(mags), 3)
        self.assertEqual(mags[2].deleted, False)

    ######################################################################
    # This tests the assignemnt of groups to scheduled periods.  The
    # results should be:
    #
    # 1st scheduled period, no matter when, should get 'A'
    #
    # 2nd scheduled should get 'B' if later than 'A', but 'A' if
    # earlier and other period should then get 'B'
    #
    # 3d scheduled period should get 'C' if it comes after the first
    # two; otherwise should get the appropriate group in accordance
    # with its scheduled date.
    #
    # Subsequent changes to the scheduled periods (new dates,
    # deletions, etc.) should continue to be accounted for.
    ######################################################################
        
    def test_maintenance_assignment(self):
        # publish the first elective, publishing its Friday period.
        pds = self.me1.periods.all().order_by('start')
        p1 = pds[pds.count() - 1] # get last one, Friday.
        p1.publish()
        self.me1.setComplete(True)
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual(len(mags), 3)
        
        # 0 is 'A', and period should be the recently scheduled
        # period.  'B' and 'C' should be uunassigned.
        
        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, p1.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period, None)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].period, None)
       
        # publish the second elective, for Tuesday
        
        pds = self.me2.periods.all().order_by('start')
        p2 = pds[0]
        p2.publish()
        self.me2.setComplete(True)
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual(len(mags), 3)

        # 'A' now should point to 'p2', since it comes earlier in the
        # week. 'B' now should point to 'p1' (which used to have 'A'),
        # since it comes later in the week.  'C' should remain
        # unassigned.

        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, p2.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period.id, p1.id)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].period, None)

        # now schedule the pending non-elective period Monday.  This
        # period will now have 'A', p2 will have 'B', and p1 will have
        # 'C'
        
        self.mp1.publish()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual(len(mags), 3)
        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, self.mp1.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period.id, p2.id)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].period.id, p1.id)

        # Now move the already scheduled self.mp1 to Wednesday.  It
        # should now get 'B', and the previous 'B' holder should get
        # 'A'.  'C' should remain the same.
        
        self.mp1.start = datetime(2011, 04, 13, 8)
        self.mp1.save()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, p2.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period.id, self.mp1.id)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].period.id, p1.id)

        # Now delete the middle period 'self.mp1'.  'A' should remain
        # with 'p2', 'B' should now go to 'p1', and 'C' should be
        # marked deleted.

        self.mp1.state = self.deleted
        self.mp1.save()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week,
                                                                          include_deleted = True)
        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, p2.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period.id, p1.id)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].deleted, True)
        
        # now revive 'self.mp1'.  C should reappear.
        self.mp1.state = self.pending
        self.mp1.save()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, p2.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period.id, p1.id)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].deleted, False)
        self.assertEqual(mags[2].period, None)

        # and finally re-schedule 'self.mp1'.  'B' should be assigned to
        # it, since it is still Wednesday.
        self.mp1.state = self.scheduled
        self.mp1.save()
        mags = Maintenance_Activity_Group.get_maintenance_activity_groups(self.week)
        self.assertEqual('A', mags[0].rank)
        self.assertEqual(mags[0].period.id, p2.id)
        self.assertEqual('B', mags[1].rank)
        self.assertEqual(mags[1].period.id, self.mp1.id)
        self.assertEqual('C', mags[2].rank)
        self.assertEqual(mags[2].deleted, False)
        self.assertEqual(mags[2].period.id, p1.id)
