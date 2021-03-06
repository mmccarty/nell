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

from datetime                            import datetime
from nell.utilities.database.DSSDatabase import DSSDatabase
from scheduler.models                     import *

class DSSDatabase09C(DSSDatabase):

    """
    This class is responsible for adding any additional items to the database
    that is needed to run the DSS for this semester.
    """

    def create(self):
        # do what always needs to get done
        DSSDatabase.create(self, "09C")
        # now the 09C specific stuff
        self.create_09C_rcvr_schedule()
        print "09C DB created."
    
    def create_09C_rcvr_schedule(self):
        "For each given date, what rcvrs are up?"

        rcvrChanges = []

        # First week - start a little early.
        #dt = datetime(2009, 10, 1, 16)
        dt = datetime(2009, 10, 1, 0)
        rcvrs = ['L', 'C', 'X', 'Ku', 'S', 'Hol', 'Q', '1070'] 
        rcvrChanges.append((dt, rcvrs))

        # "versoin 4.0[sick] receiver schedule for Oct - Jan"

        # Oct 8: Hol comes down
        dt = datetime(2009, 10, 8, 16)
        rcvrs = ['L', 'C', 'X', 'Ku', 'S', 'Q', '1070'] 
        rcvrChanges.append((dt, rcvrs))

        # Oct 13: 1070 -> 800, Hol goes up
        dt = datetime(2009, 10, 13, 16)
        rcvrs = ['L', 'C', 'X', 'Ku', 'S', 'Hol', 'Q', '800'] 
        rcvrChanges.append((dt, rcvrs))

        # Oct 19 800 -> 300
        dt = datetime(2009, 10, 19, 16)
        rcvrs = ['L', 'C', 'X', 'Ku', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Oct 22: K goes up
        dt = datetime(2009, 10, 22, 16)
        rcvrs = ['L', 'C', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Oct 27: 342 -> 450
        dt = datetime(2009, 10, 27, 16)
        rcvrs = ['L', 'C', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '450'] 
        rcvrChanges.append((dt, rcvrs))

        # Oct 30: 450 -> 600
        dt = datetime(2009, 10, 30, 16)
        rcvrs = ['L', 'C', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '600'] 
        rcvrChanges.append((dt, rcvrs))

        # Nov 3: 600 -> 342, Remove C
        dt = datetime(2009, 11, 3, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Nov 6: Add MBA
        dt = datetime(2009, 11, 6, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'MBA', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Nov 12: Remove MBA
        dt = datetime(2009, 11, 12, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Nov 18: 342 -> 800, MBA goes up 
        dt = datetime(2009, 11, 18, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'MBA', 'S', 'Hol', 'Q', '800'] 
        rcvrChanges.append((dt, rcvrs))

        # Nov 23: 800 -> 342
        dt = datetime(2009, 11, 23, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'MBA', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Dec 9: Mustang down
        dt = datetime(2009, 12, 9, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Dec 15: 342 -> 800
        dt = datetime(2009, 12, 15, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '800'] 
        rcvrChanges.append((dt, rcvrs))

        # Dec 22: 800 -> 342
        dt = datetime(2009, 12, 22, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '342'] 
        rcvrChanges.append((dt, rcvrs))

        # Jan 6: 342 -> 800
        dt = datetime(2010, 1, 6, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '800'] 
        rcvrChanges.append((dt, rcvrs))

        # Jan 12: MBA goes up
        dt = datetime(2010, 1, 12, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '800', 'MBA'] 
        rcvrChanges.append((dt, rcvrs))

        # Jan 21 800 down, 342 up
        dt = datetime(2010, 1, 21, 16)
        rcvrs = ['L', 'K', 'X', 'Ku', 'S', 'Hol', 'Q', '342', 'MBA'] 
        rcvrChanges.append((dt, rcvrs))

        # Jan 26 KFPA up, Z up, Ku -> Ka, Q-band down
        dt = datetime(2010, 1, 26, 16)
        rcvrs = ['L', 'K', 'X', 'S', 'Hol', 'KFPA',  'Ka', 'Z', '342', 'MBA'] 
        rcvrChanges.append((dt, rcvrs))

        # Feb 2: 342 -> 1070
        dt = datetime(2010, 2, 2, 16)
        rcvrs = ['L', 'K', 'X', 'S', 'Hol', 'KFPA',  'Ka', 'Z', '1070', 'MBA'] 
        rcvrChanges.append((dt, rcvrs))

        for dt, rcvrs in rcvrChanges:
            print dt, rcvrs
            for rcvr in rcvrs:
                r = Receiver.objects.get(abbreviation = rcvr)
                print "    ", r
                rs = Receiver_Schedule(receiver = r, start_date = dt)
                rs.save()
                #print rs

