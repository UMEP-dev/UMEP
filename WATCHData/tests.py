import unittest
#from WFDEIDownloader.WFDEI_Interpolator import height_solver_WFDEI
import os
def height_solver_WFDEI(lat, lon):
    '''determine the original height of WFDEI grid'''
    glat, glon = lon_lat_grid(lat, lon)


    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'WFDEIDownloader/WFDEI-land-long-lat-height.txt')) as f:
        ls = [line.split() for line in f]
    print (glat, glon)
    for i in range(7, len(ls)):
        if float(ls[i][0]) == glon and float(ls[i][1]) == glat:
            print ls[i]
            return float(ls[i][2])
            break
    # oceanic grids determined as 0.0
    return 0.0


# determing grid index according to coordinates
def lon_lat_grid(lat, lon):
    lon_deci = lon - int(lon)
    lat_deci = lat - int(lat)

    if lon >= 0:
        if 0 <= lon_deci < 0.5:
            lon = int(lon) + 0.25
        else:
            lon = int(lon) + 0.75
    else:
        if -0.5 < lon_deci <= 0:
            lon = -(-int(lon) + 0.25)
        else:
            lon = -(-int(lon) + 0.75)

    if lat >= 0:
        if 0 <= lat_deci < 0.5:
            lat = int(lat) + 0.25
        else:
            lat = int(lat) + 0.75
    else:
        if -0.5 < lat_deci <= 0:
            lat = -(-int(lat) + 0.25)
        else:
            lat = -(-int(lat) + 0.75)
    print (lat, lon)
    return lat, lon


class TestBasicCalcs(unittest.TestCase):
    ''' Tests for custom temperature response calculation'''

    def testZeroInLondon(self):
        print height_solver_WFDEI(51.539, -0.142)
        ''' Extreme low should be a particular value'''
