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

from CNF    import cnf
from Parse  import parse, scan

class ReceiverCompile:

    def __init__(self, names):
        """
        The argument names contains a list of receiver abbreviations,
        e.g., 1070 or L.
        """
        self.names = names

    def normalize(self, text):
        """
        Accepts a string containing a multi-receiver specification in logical
        form, e.g., "Ka | (L & S)" or "Q" (using receiver abbreviations)
        and returns a list of lists in CNF, e.g.,
        [['Ka', 'L'], ['Ka', 'S']] and [['Q']] respectively. Note that
        'and' may be represented by '&' or '^' and 'or' may be represented
        by '|' or 'v'.
        """
        if text is not None:
            text = text.strip()
        if text is None or text == "":
            return []
        if isinstance(text, unicode):
            text = text.encode("ascii")
        prop = parse(scan('(' + text + ')'))
        rcvr_grps = cnf(prop)
        self.checkAbbreviations(rcvr_grps)
        return rcvr_grps

    def checkAbbreviations(self, rcvr_grps):
        """
        Throws a ValueError if the receiver groups contain a
        non-abbreviation.
        """
        for rg in rcvr_grps:
            for r in rg:
                if r not in self.names:
                    raise ValueError, "%s not a receiver" % r

    def denormalize(self, normalized):
        """
        WTF does denormalize mean?  Don't ask me, this is just a function
        that makes the receiver specification symettrical: that is, 
        input rcvrs to normalize, and the output from that into this function
        will give you back the logical equivalent of your original input.

        Example:
        'L | (X | C)' ->
        [['L', 'X', 'C']] ->
        'L | (X | C)'
        """

        # make sure we have valid input
        self.checkAbbreviations(normalized)

        or_groups = []
        for group in normalized:
            or_groups.append(self.pairValues(group, "|"))
        and_groups = self.pairValues(or_groups, "&")

        return and_groups

    def pairValues(self, values, separator):
        """
        Given a list of values, creates a string representation w/ the 
        correct insertion of parens and separators.  For example:
        values = ['L', 'X', 'C']
        separator = '|'
        gives:
        'L | (X | C)'
        """
        numValues = len(values)
        if numValues == 0:
            return ''
        elif numValues == 1:
            return values[0]
        elif numValues == 2:
            return "(%s %s %s)" % (values[0], separator, values[1])
        else:
            seed = "(%s %s %s)" % (values[0], separator, values[1])
            for v in values[2:]:
                seed = "(%s %s %s)" % (seed, separator, v)
            return seed    
           
