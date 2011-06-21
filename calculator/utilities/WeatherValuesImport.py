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

from django.core.management import setup_environ
import settings
setup_environ(settings)

from calculator.models import *

class WeatherValuesImport(object):

    def __init__(self, filename):
        f = open(filename)

        def processData(data):
            return [int(float(data[0]))] + map(float, data[1:])

        raw_data = [processData([i.replace('\n', '') for i in l.split(',') 
                                     if i != ' ' and i != ' \n']) for l in f.readlines()[1:]]
        self.data = [rd for rd in raw_data if len(rd) > 1]
        f.close()
        self.insertData()

    def insertData(self):
        for i, d in enumerate(self.data):
            wv = WeatherValues(*([i + 1] + d))
            wv.save()
            

if __name__ == "__main__":
    wvi = WeatherValuesImport('calculator/data/SensCalcWeatherValues.csv')
