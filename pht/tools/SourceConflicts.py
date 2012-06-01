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

from pht.models import *
from pht.utilities import *

class SourceConflicts(object):

    def __init__(self, semester = None):

        if semester is None:
            self.semester = '12B'
        else:
            self.semester = semester

        self.initHPBWs()

    def initHPBWs(self):
        "Map receivers to their Half Power Beam Widths (arc-mins)"

        self.hpbw = {
          'RRI' : 123.5
        , '342' : 36.5
        , '450' : 27.5
        , '600' : 20.7
        , '800' : 15.5
        , '1070' : 12.4
        , 'L' : 8.7
        , 'S' : 4.1
        , 'C' : 2.5
        , 'X' : 1.3
        , 'Ku' : 0.830
        , 'KFPA' : 0.560
        , 'Ka' : 0.376
        , 'Q' : 0.249
        , 'W' : 0.160
        , 'MBA' : 0.160 
        }

    def findConflicts(self, proposals = None, allProposals = None):
        "Main entry point: find all source conflicts"

        # which proposals to check?
        if proposals is None:
            if self.semester is not None:
                proposals = Proposal.objects.filter(semester__semester = self.semester)
            else: 
                proposals = Proposal.objects.all()

        # which proposals to check against?
        if allProposals is None:
            allProposals = Proposal.objects.all()

        # start checking
        for p in proposals:
            self.findConflictsForProposal(p, allProposals)

    def findConflicstsForProposal(self, proposal, allProposals):

        for p in allProposals:
            self.findConflictsBetweenProposals(proposal, p)

    def findConflictsBetweenProposals(targetProp, searchedProp):
        """
        targetProp - the proposal that we use to determine the search rad
        searchedProp - checking srcs in targetProp against one's in here
        """

        rad = self.getSearchRadius(targetProp)        
        trgSrcs = targetProp.sources.all()
        srchSrcs = searchedProp.sources.all()
        for trgSrc in trgSrcs:
            for srchSrc in srchSrcs:
                d = self.sourceAngularDistance(trgSrc, srchSrc)
                if d <= rad:
                    print "Too close!"


    def getLowestRcvr(self, proposal):
        # TBF: use all rx's of the proposal, or do this by session?
        lowest = None
        for s in proposal.session_set.all():
            rxs = s.receivers.all().order_by('freq_low')
            if len(rxs) > 0:
                if lowest is None or lowestRx.freq_low > rxs[0].freq_low:
                    lowest = rxs[0]

    def getSearchRadius(self, proposal):
        """
        Search Radius (arc-mins) = 2*HPBW of lowest receiver.
        """
        lowestRcvr = self.getLowestRcvr(proposal)
        if lowestRcvr is None:
            return None
        # get HPWB, *2, convert to degress, then to radians
        return deg2rad(self.hpbw[lowestRcvr.abbreviation] * 2.0 * (1/60.))            
                    
    def sourceAngularDistance(self, src1, src2):
        "Ang. Dist. between two source objs: all in radians"
        return angularDistance(src1.ra
                             , src1.dec
                             , src2.ra
                             , src2.dec)
        

            

