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

from pht.tools.LstPressures import LstPressures

from matplotlib.backends.backend_agg import FigureCanvasAgg 
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy

class PlotLstPressures(object):

    def __init__(self):


        self.grades = ['A', 'B', 'C']

        # colors for grades A, B, C ...
        self.reds   = ('#FF0000', '#FF8080', '#FFCCCC')
        self.blues  = ('#0000FF', '#8080FF', '#CCCCFF')
        self.greens = ('#00FF00', '#99FF99', '#e5FFe5')

        self.colors = {'excellent' : self.blues
                     , 'good' : self.greens
                     , 'poor' : self.reds
                      }

        self.lst = LstPressures()

        self.initPlots()

    def initPlots(self):

        self.figure = Figure(figsize=(6,6))
        self.axes = self.figure.add_axes([0.1, 0.1, 0.8, 0.8])
        self.canvas = None

    def plot(self, type):

        self.lst.getPressures()

        # what type of plot?
        if type == 'total':
            self.plotTotals()
        elif type == 'poor':    
            self.plotPoor()
        elif type == 'good':    
            self.plotGood()
        elif type == 'excellent':    
            self.plotExcellent()
        else:
            raise "unknown plot type", type

    def plotTotals(self):
    
        stacks = [
            {'data': self.lst.carryoverTotalPs
           , 'color': 'orange'}
           # grade A
          , {'data': self.lst.gradePs['A'].excellent
           , 'color': self.getColor('A', 'excellent')}
          , {'data': self.lst.gradePs['A'].good
           , 'color': self.getColor('A', 'good')}
          , {'data': self.lst.gradePs['A'].poor
           , 'color': self.getColor('A', 'poor')}
           # grade B
          , {'data': self.lst.gradePs['B'].excellent
           , 'color': self.getColor('B', 'excellent')}
          , {'data': self.lst.gradePs['B'].good
           , 'color': self.getColor('B', 'good')}
          , {'data': self.lst.gradePs['B'].poor
           , 'color': self.getColor('B', 'poor')}
           # grade C
          , {'data': self.lst.gradePs['C'].excellent
           , 'color': self.getColor('C', 'excellent')}
          , {'data': self.lst.gradePs['C'].good
           , 'color': self.getColor('C', 'good')}
          , {'data': self.lst.gradePs['C'].poor
           , 'color': self.getColor('C', 'poor')}
          , {'data': self.lst.requestedTotalPs
           , 'color': 'yellow'}
                ]
       
        self.plotPressureData(stacks, "Total Pressure")
    
    def plotPoor(self):

        # TBF: There's a patter here we could use to shrink this
        stacks = [
            {'data': self.lst.carryoverPs.poor
           , 'color': 'orange'}
          , {'data': self.lst.gradePs['A'].poor
           , 'color': self.getColor('A', 'poor')}
          , {'data': self.lst.gradePs['B'].poor
           , 'color': self.getColor('B', 'poor')}
          , {'data': self.lst.gradePs['C'].poor
           , 'color': self.getColor('C', 'poor')}
          , {'data': self.lst.requestedPs.poor
           , 'color': 'yellow'}
                ]
       
        self.plotPressureData(stacks, "Poor")

    def plotGood(self):

        stacks = [
            {'data': self.lst.carryoverPs.good
           , 'color': 'orange'}
          , {'data': self.lst.gradePs['A'].good
           , 'color': self.getColor('A', 'good')}
          , {'data': self.lst.gradePs['B'].good
           , 'color': self.getColor('B', 'good')}
          , {'data': self.lst.gradePs['C'].good
           , 'color': self.getColor('C', 'good')}
          , {'data': self.lst.requestedPs.good
           , 'color': 'yellow'}
                ]
       
        self.plotPressureData(stacks, "Good")

    def plotExcellent(self):

        stacks = [
            {'data': self.lst.carryoverPs.excellent
           , 'color': 'orange'}
          , {'data': self.lst.gradePs['A'].excellent
           , 'color': self.getColor('A', 'excellent')}
          , {'data': self.lst.gradePs['B'].excellent
           , 'color': self.getColor('B', 'excellent')}
          , {'data': self.lst.gradePs['C'].excellent
           , 'color': self.getColor('C', 'excellent')}
          , {'data': self.lst.requestedPs.excellent
           , 'color': 'yellow'}
                ]
       
        self.plotPressureData(stacks, "Excellent")

    def plotPressureData(self, stacks, title):

        ind = numpy.arange(self.lst.hrs)
        total = numpy.zeros(self.lst.hrs)
        for stack in stacks:
            data = stack['data']
            print data
            self.axes.bar(ind, data, color=stack['color'], bottom=total)
            total += data

        self.axes.set_xlabel('LST')
        self.axes.set_ylabel('Pressure (Hrs)')
        self.figure.suptitle(title, fontsize=14)
        self.canvas = FigureCanvasAgg(self.figure)

    def getColor(self, grade, weatherType):
        return self.colors[weatherType][self.grades.index(grade)]

    def printPlot(self, filename):
        self.canvas.print_png(filename)

if __name__ == '__main__':
    plot = PlotLstPressures()

