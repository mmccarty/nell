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

# This dictionary was parsed from the contents of this website:
# old: http://www.cfa.harvard.edu/iau/Ephemerides/Bright/2010/Soft03Bright.txt
# new: http://www.minorplanetcenter.net/iau/Ephemerides/Bright/2011/Soft03Bright.txt
# it can be used with pyephem to create objects which can give the
# position of these objects for any date 
# For specific use with UpdateEphemeris
# This is for 2010, so we'll need a way to autoupdate this?
# See Story: https://www.pivotaltracker.com/story/show/8254649

ephemerisAsteroids = {'Alexandra': 'Alexandra,e,11.8070,313.4363,345.8050,2.710965,0.2208097,0.19693015,346.3726,01/04.0/2010,2000,H 7.66,0.15\n',
 'Amphitrite': 'Amphitrite,e,6.0967,356.4867,63.0125,2.553755,0.2415101,0.07326953,183.9269,01/04.0/2010,2000,H 5.85,0.20\n',
 'Angelina': 'Angelina,e,1.3099,309.2168,179.4868,2.681989,0.2243977,0.12588199,354.8065,01/04.0/2010,2000,H 7.67,0.48\n',
 'Antigone': 'Antigone,e,12.2187,136.4148,108.3572,2.868167,0.2029072,0.21215845,333.5598,01/04.0/2010,2000,H 7.07,0.33\n',
 'Astraea': 'Astraea,e,5.3714,141.6582,358.0207,2.577742,0.2381468,0.19081553,191.8727,01/04.0/2010,2000,H 6.85,0.15\n',
 'Atalante': 'Atalante,e,18.4346,358.4574,46.9273,2.747428,0.2164286,0.30334494,285.5228,01/04.0/2010,2000,H 8.46,0.15\n',
 'Athamantis': 'Athamantis,e,9.4381,239.9411,140.1096,2.382202,0.2680625,0.06143776,191.8246,01/04.0/2010,2000,H 7.35,0.27\n',
 'Ausonia': 'Ausonia,e,5.7858,337.8953,295.9389,2.395405,0.2658494,0.12556909,315.4710,01/04.0/2010,2000,H 7.55,0.25\n',
 'Ceres': 'Ceres,e,10.5863,80.3939,72.6927,2.765723,0.2142846,0.07922194,70.4340,01/04.0/2010,2000,H 3.34,0.12\n',
 'Chloris': 'Chloris,e,10.9213,97.1937,172.2141,2.728646,0.2186670,0.23622641,321.1459,01/04.0/2010,2000,H 8.30,0.15\n',
 'Dembowska': 'Dembowska,e,8.2573,32.4750,347.5229,2.924498,0.1970730,0.08879829,192.4192,01/04.0/2010,2000,H 5.93,0.37\n',
 'Diana': 'Diana,e,8.7049,333.4591,152.6084,2.621552,0.2322022,0.20644060,247.8727,01/04.0/2010,2000,H 8.09,0.08\n',
 'Echo': 'Echo,e,3.6011,191.6420,271.1550,2.393271,0.2662051,0.18329887,23.1715,01/04.0/2010,2000,H 8.21,0.27\n',
 'Egeria': 'Egeria,e,16.5441,43.2759,80.5710,2.575576,0.2384474,0.08581607,97.3317,01/04.0/2010,2000,H 6.74,0.15\n',
 'Eleonora': 'Eleonora,e,18.3938,140.4072,6.5840,2.798915,0.2104842,0.11445962,337.3523,01/04.0/2010,2000,H 6.44,0.37\n',
 'Eugenia': 'Eugenia,e,6.6102,147.9209,85.7033,2.719904,0.2197221,0.08131381,14.1126,01/04.0/2010,2000,H 7.46,0.07\n',
 'Eukrate': 'Eukrate,e,24.9952,0.2086,54.7780,2.741231,0.2171629,0.24396546,275.2718,01/04.0/2010,2000,H 8.04,0.15\n',
 'Eunomia': 'Eunomia,e,11.7387,293.2568,97.8237,2.642430,0.2294557,0.18809363,224.3120,01/04.0/2010,2000,H 5.28,0.23\n',
 'Euterpe': 'Euterpe,e,1.5838,94.8039,356.7148,2.346165,0.2742625,0.17297500,122.8826,01/04.0/2010,2000,H 7.0,0.15\n',
 'Fides': 'Fides,e,3.0738,7.3331,62.4036,2.644718,0.2291579,0.17447937,282.1342,01/04.0/2010,2000,H 7.29,0.24\n',
 'Flora': 'Flora,e,5.8891,110.9579,285.3765,2.200870,0.3018648,0.15683333,248.7976,01/04.0/2010,2000,H 6.49,0.28\n',
 'Harmonia': 'Harmonia,e,4.2563,94.2796,269.9133,2.267202,0.2887146,0.04656883,205.7277,01/04.0/2010,2000,H 7.0,0.15\n',
 'Hebe': 'Hebe,e,14.7541,138.7397,239.4705,2.424609,0.2610608,0.20249066,279.4693,01/04.0/2010,2000,H 5.71,0.24\n',
 'Hera': 'Hera,e,5.4223,136.2710,190.4115,2.701518,0.2219690,0.08039842,318.6619,01/04.0/2010,2000,H 7.66,0.15\n',
 'Herculina': 'Herculina,e,16.3121,107.5986,76.5316,2.771956,0.2135623,0.17807010,338.0632,01/04.0/2010,2000,H 5.81,0.26\n',
 'Hesperia': 'Hesperia,e,8.5831,185.0601,289.8457,2.978358,0.1917515,0.16876869,7.8792,01/04.0/2010,2000,H 7.05,0.19\n',
 'Hestia': 'Hestia,e,2.3433,181.1490,176.7719,2.525037,0.2456419,0.17304732,315.7669,01/04.0/2010,2000,H 8.36,0.06\n',
 'Hygiea': 'Hygiea,e,3.8411,283.4499,313.1132,3.139718,0.1771610,0.11694343,268.9053,01/04.0/2010,2000,H 5.43,0.15\n',
 'Irene': 'Irene,e,9.1066,86.4520,96.3462,2.585174,0.2371207,0.16730550,80.8430,01/04.0/2010,2000,H 6.30,0.15\n',
 'Kalliope': 'Kalliope,e,13.7071,66.2184,355.4365,2.908910,0.1986591,0.10242299,242.4011,01/04.0/2010,2000,H 6.45,0.21\n',
 'Klotho': 'Klotho,e,11.7861,159.7510,268.4370,2.670011,0.2259095,0.25590195,263.4063,01/04.0/2010,2000,H 7.63,0.15\n',
 'Laetitia': 'Laetitia,e,10.3865,157.1621,209.3093,2.767649,0.2140610,0.11505655,293.9910,01/04.0/2010,2000,H 6.1,0.15\n',
 'Leto': 'Leto,e,7.9731,44.1517,305.5290,2.781463,0.2124683,0.18631778,258.0109,01/04.0/2010,2000,H 6.78,0.05\n',
 'Ludmilla': 'Ludmilla,e,9.7820,263.3432,151.6149,2.771938,0.2135644,0.20191932,306.8782,01/04.0/2010,2000,H 7.91,0.15\n',
 'Metis': 'Metis,e,5.5743,68.9536,6.3073,2.386609,0.2673204,0.12222132,87.9228,01/04.0/2010,2000,H 6.28,0.17\n',
 'Pallas': 'Pallas,e,34.8404,173.1284,310.2064,2.772749,0.2134707,0.23097025,53.3955,01/04.0/2010,2000,H 4.13,0.11\n',
 'Papagena': 'Papagena,e,14.9804,84.0877,314.1539,2.886579,0.2009690,0.23354292,284.6413,01/04.0/2010,2000,H 6.73,0.37\n',
 'Peraga': 'Peraga,e,2.9366,295.5323,127.0499,2.375803,0.2691463,0.15326623,289.6470,01/04.0/2010,2000,H 8.97,0.15\n',
 'Philomela': 'Philomela,e,7.2593,72.5535,200.3964,3.113987,0.1793614,0.02103519,201.3007,01/04.0/2010,2000,H 6.54,0.15\n',
 'Phocaea': 'Phocaea,e,21.5858,214.2394,90.3149,2.399574,0.2651568,0.25588856,351.3887,01/04.0/2010,2000,H 7.83,0.15\n',
 'Pomona': 'Pomona,e,5.5285,220.5479,338.9166,2.587428,0.2368109,0.08280398,307.4625,01/04.0/2010,2000,H 7.56,0.15\n',
 'Psyche': 'Psyche,e,3.0991,150.2952,226.9416,2.923139,0.1972104,0.13841013,339.6540,01/04.0/2010,2000,H 5.90,0.20\n',
 'Siegena': 'Siegena,e,20.2624,166.9197,219.6086,2.896421,0.1999454,0.17307428,306.6640,01/04.0/2010,2000,H 7.43,0.16\n',
 'Suleika': 'Suleika,e,10.2315,85.4085,336.3192,2.715659,0.2202375,0.23405052,296.1757,01/04.0/2010,2000,H 8.50,0.15\n',
 'Thusnelda': 'Thusnelda,e,10.8452,200.9321,142.3785,2.353439,0.2729918,0.22372518,303.5804,01/04.0/2010,2000,H 9.32,0.15\n',
 'Tyche': 'Tyche,e,14.2961,207.6734,154.8051,2.614758,0.2331078,0.20595187,318.8028,01/04.0/2010,2000,H 8.50,0.23\n',
 'Undina': 'Undina,e,9.9222,101.8268,242.1262,3.188085,0.1731447,0.10171674,307.8500,01/04.0/2010,2000,H 6.61,0.15\n',
 'Urania': 'Urania,e,2.0985,307.7340,86.9989,2.365229,0.2709532,0.12713747,188.2670,01/04.0/2010,2000,H 7.57,0.15\n',
 'Vesta': 'Vesta,e,7.1344,103.9148,149.8368,2.361937,0.2715198,0.08872916,253.5043,01/04.0/2010,2000,H 3.20,0.32\n',
 'Vibilia': 'Vibilia,e,4.8078,76.4723,293.4762,2.654068,0.2279481,0.23632217,313.9956,01/04.0/2010,2000,H 7.91,0.17\n',
 'Victoria': 'Victoria,e,8.3627,235.5094,69.7647,2.334373,0.2763431,0.22024988,273.3013,01/04.0/2010,2000,H 7.24,0.22\n'}

def parseAsteroidsFile():
    "This code snippet produced the above dictionary"

    dict = {}

    filename = "ephemerisAsteroids.txt"
    path = "/home/sandboxes/pmargani/dss/trunk/nell/utilities/"
    fullpath = path + filename
    f = open(fullpath, 'r')
    lines = f.readlines()

    for l in lines:
        # skip the comments
        if l[0] != "#":
            # skip the number line
            l2 = " ".join(l.split(" ")[1:])
            # get the name
            parts = l2.split(",")
            name = parts[0]
            dict[name] = l2

    return dict        
        

