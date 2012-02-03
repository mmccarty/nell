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

import math

# TBF: use decoraters to gaurd for None?

def deg2rad(deg):
    "Translates degrees into radians."
    if deg is None:
        return None
    return math.pi * deg / 180

def rad2deg(rad):
    "Translates radians into degrees."
    if rad is None:
        return None
    return 180.0 * rad / math.pi

def hr2rad(hrs):
    "Translates hours into radians."
    if hrs is None:
        return None
    return math.pi * hrs / 12

def rad2hr(rad):
    "Translates radians into hours."
    if rad is None:
        return None
    return 12 * rad / math.pi

def sexigesimelFormTwo2float(value):
    return sexigesimel2float(value, deliminator = " ")

def sexigesimel2float(value, deliminator = ":"):
    "String (format [-]DD:MM[:SS)]) to float value"
    if value == '' or value is None:
        return value
    elif deliminator not in value:
        return float(value)
    values = value.split(deliminator)
    # find all values that aren't blank (could happen if deliminator is " ")
    values = [v for v in values if v != '']
    # TBF: assert minutes and seconds are between 0 and 59
    degrees= values[0].strip()
    
    if len(values) == 3:
        minute = (float(values[1].strip())/60.0) + (float(values[2].strip()) / 3600.) #/ 60.
    elif len(values) == 2:
        minute = float(values[1].strip()) / 60.
    else:
        return value
    return -1 * (float(degrees[1:]) + minute) if '-' in degrees else float(degrees) + minute

def sexigesimelFormThree2float(value):
    """
    Converts 06h 54m 46.514073s or 06d 54m 46.514073s to float.
    """
    if value == '' or value is None:
        return value
    # hours or degress?    
    hpos = value.find('h')    
    dpos = value.find('d')
    pos1 = dpos if dpos != -1 else hpos
    mpos = value.find('m')    
    spos = value.find('s')    
    if pos1 == -1 or mpos == -1 or spos == -1:
        return None
    # takes sign into account    
    degrees = float(value[0:pos1].strip())
    minutes = float(value[(pos1+1):mpos].strip())
    seconds = float(value[(mpos+1):spos].strip())
    return degrees + (minutes/60.0) + (seconds/3600.0) 


def float2sexigesimel(signed_decimaldegrees):
    "Float to string (format [-]DD:MM[:SS)]"
    if signed_decimaldegrees is None:
        return None
    decimaldegrees = abs(signed_decimaldegrees)
    degrees = int(decimaldegrees)
    minutes = int((abs(decimaldegrees) - abs(degrees)) * 60.0)
    seconds = ((abs(decimaldegrees) - abs(degrees)) * 60.0 - minutes) * 60.0
    sign = ""

    if abs(seconds - 60.0) < 0.1:
     	minutes += 1
       	seconds = abs(seconds - 60.0)
    if abs(minutes - 60.0) < 0.1:
       	degrees += 1
       	minutes = abs(minutes - 60)
    if signed_decimaldegrees < 0.0:
       	sign = "-";

    if degrees >= 100 or degrees <= -100:
        degStr = "%03d" % degrees
    else:
        degStr = "%02d" % degrees
    if seconds >= 10.0:
        secStr = "%2.1f" % seconds
    else:
        secStr = "0%1.1f" % seconds
    return "%s%s:%02d:%s" % (sign, degStr, minutes, secStr)
        
def sexHrs2rad(value):
    "String (format [-]H:MM[:SS)]) to float value (radians)"
    return hr2rad(sexigesimel2float(value))

def rad2sexHrs(value):
    return float2sexigesimel(rad2hr(value))

def sexDeg2rad(value):
    return deg2rad(sexigesimel2float(value))

def rad2sexDeg(value):
    return float2sexigesimel(rad2deg(value))

