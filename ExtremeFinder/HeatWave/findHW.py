###########################################################################
#
#                               HWFinder
#
###########################################################################

# preloaded packages
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from datetime import datetime, timedelta, time
import os
import math
# import f90nml
import webbrowser
import datetime
import time
import gzip
import StringIO
import urllib2
import tempfile

# pandas, netCDF4 and numpy might not be shipped with QGIS
try:
    import pandas as pd
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

try:
    from netCDF4 import Dataset, date2num
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

try:
    import numpy as np
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it


# Find the nearest lat & lon in grid.
def lon_lat_grid(lat, lon):
    latGrid = 90 - (math.floor((90 - lat) / .5) * .5 + .25)
    lonGrid = math.floor((lon - (-180)) / .5) * .5 + .25 - 180
    return latGrid, lonGrid

# Find the land number of (lat, lon)


def WFD_get_city_index(city_latitude, city_longtitude):
    yGrid = math.floor((90 - city_latitude) / .5) + 1
    xGrid = math.floor((city_longtitude - (-180)) / .5) + 1
    return int((yGrid - 1) * 720 + xGrid)

# Get Tmax data from the specified time period.


def get_data(filepath, year_start, year_end):
    nc = Dataset(filepath,'r')
    xTair = nc.variables['Tair'][:]
    xdate = pd.date_range('1901-01-01', '2012-12-31')
    Tair = pd.Series(xTair, index=xdate)
    return Tair['%d' % year_start:'%d' % year_end]

# get the threshold from the specified percentage.


def get_threshold(data, threshold_year_start, threshold_year_end, percent1, percent2):
    data = data['%d' % threshold_year_start:'%d' % threshold_year_end]
    return np.percentile(data, percent1), np.percentile(data, percent2)

# Find HWs


def HWFinder(Tair, hw_start, hw_end, xT1, xT2):
    # the daily maximum temperature must be above T2 for every day of the
    # entire period

    hw_date = pd.date_range(hw_start, hw_end)
    Tair = pd.Series(Tair, index=hw_date)
    sub_filter1 = Tair[Tair > xT2]
    if len(sub_filter1) == 0:
        return sub_filter1

    #  subsequence for at least three consecutive days
    tind = [0]
    ind = []
    for i in range(1, len(sub_filter1)):
        if (sub_filter1.index[i] - sub_filter1.index[i - 1]) == timedelta(days=1):
            tind.append(i)
        else:
            if len(tind) >= 3:
                ind.append(tind)
            tind = [i]
    if len(tind) >= 3:
        ind.append(tind)
    if len(ind) == 0:
        return ind

    #  the daily maximum temperature must be above T1 for at least 3 days,
    # the average daily maximum temperature must be above T1 for the entire
    # period
    sub_filter2 = []

    def HWSearch(data, T1, T2):
        # shortest scenario:
        if np.sort(data)[-3] <= T1:
            return False
        # longer scenarios:
        else:
            if np.mean(data) > T1:
                sub_filter2.append(data)
            else:
                return HWSearch(data[:-1], T1, T2), HWSearch(data[1:], T1, T2)

    HWSearch = memoize(HWSearch)

    [HWSearch(sub_filter1[tind[0]:tind[-1] + 1], xT1, xT2) for tind in ind]
    if (sub_filter2) == 0:
        return sub_filter2

    #  combine the sublist with the same start date and choose the longest one
    keys = list(set(x.index[0] for x in sub_filter2))
    keys.sort()
    sub_filter3 = [[y for y in sub_filter2 if y.index[0] == x] for x in keys]
    [x.sort(key=len) for x in sub_filter3]
    sub_filter4 = [x[-1] for x in sub_filter3]
    if len(sub_filter4) == 0:
        return sub_filter4

    #  split sequential list into sublists if not overlapped
    sub = [sub_filter4[0]]
    sub_filter5 = []
    for i in range(1, len(sub_filter4)):
        # or sub_filter4[i-1][0] < sub_filter4[i][1] < sub_filter4[i-1][1]:
        if sub_filter4[i - 1].index[0] < sub_filter4[i].index[0] < sub_filter4[i - 1].index[-1]:
            sub.append(sub_filter4[i])
        else:
            sub_filter5.append(sub)
            sub = [sub_filter4[i]]
    sub_filter5.append(sub)
    if len(sub_filter5) == 0:
        return sub_filter5

    #  when overlapped, pick out the longest one
    #  if several longest ones exist, choose the first occurence
    [sub.sort(key=len) for sub in sub_filter5]
    submaxlen = [len(sub[-1]) for sub in sub_filter5]
    sub_filter6 = []
    for i in range(0, len(sub_filter5)):
        for j in range(0, len(sub_filter5[i])):
            if len(sub_filter5[i][j]) == submaxlen[i]:
                sub_filter6.append(sub_filter5[i][j])
                break

    return sub_filter6


def memoize(fn):
    """returns a memoized version of any function that can be called
    with the same list of arguments.
    Usage: foo = memoize(foo)
    http://stackoverflow.com/a/17268784/920789"""

    def handle_item(x):
        if isinstance(x, dict):
            return make_tuple(sorted(x.items()))
        elif hasattr(x, '__iter__'):
            return make_tuple(x)
        else:
            return x

    def make_tuple(L):
        return tuple(handle_item(x) for x in L)

    def foo(*args, **kwargs):
        items_cache = make_tuple(sorted(kwargs.items()))
        args_cache = make_tuple(args)
        if (args_cache, items_cache) not in foo.past_calls:
            foo.past_calls[(args_cache, items_cache)] = fn(*args, **kwargs)
        return foo.past_calls[(args_cache, items_cache)]
    foo.past_calls = {}
    foo.__name__ = 'memoized_' + fn.__name__
    return foo


def write_nc(xland, xHW):
    dataset = Dataset('HW/%s.nc' % xland, 'w')
    date = dataset.createDimension('date', None)

    dates = dataset.createVariable('dates', np.float64, ('date',))
    Tair = dataset.createVariable('Tair', np.float64, ('date',))
    dates.units = 'hours since 0001-01-01'
    dates.calendar = 'gregorian'
    Tair.units = 'K'

    Tair[:] = np.array(xHW)
    date = [datetime(i.year, i.month, i.day) for i in xHW.index]
    dates[:] = date2num(date, 'hours since 0001-01-01', 'gregorian')


def write_txt(xland, xHW):
    xHW.to_csv(str(outputpath) + '/%s.txt' %
               xland, sep=" ", index=True, float_format='%.4f')


def grid_district(lat, lon):
    grid_lat_lon = [(i, j) for i in lat for j in lon]
    return grid_lat_lon


def land_examine(grid_lat_lon, land_global):
    tland_district = [WFD_get_city_index(i[0], i[1]) for i in grid_lat_lon]

    land_district = []
    for land in tland_district:
        if land in land_global:
            land_district.append(land)
    return list(set(land_district))


def level(minvalue, maxvalue):
    lev_tan = np.arange(1, 5, 0.4)
    lev = [math.atan(i) for i in lev_tan]
    levels = [(i - lev[0]) / (lev[-1] - lev[0]) *
              (maxvalue - minvalue) + minvalue for i in lev]
    return levels

# get Tmax from urban-climate server


def get_Tmax(xland, year_start, year_end):
    # extract land grids of a certain district from global land grids
    # land_district = land_examine(tgrid_district, land_global)

    # check if the land grid is valid

    # download Tmax data
    url = "http://www.urban-climate.net/watch_data/Tmax_Land/Tmax_Land_" + \
          str(xland) + ".nc.gz"
    file_name = url.split('/')[-1]

    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib2.Request(url, None, headers)
    html = urllib2.urlopen(req).read()
    f_compressed = StringIO.StringIO(html)
    f_decompressed = gzip.GzipFile(fileobj=f_compressed)

    file_name_for_nc = os.path.join(tempfile.gettempdir(), file_name)

    # be specific here: write in 'wb' otherwise Windows will complain!
    with open(file_name_for_nc, 'wb') as f_dat:
        f_dat.write(f_decompressed.read())

    Tmax = get_data(file_name_for_nc, year_start, year_end)
    return Tmax


# identify HW periods


def findHW(Tmax,
           hw_start, hw_end,
           threshold_year_start, threshold_year_end,
           t1_quantile, t2_quantile):
    # thresholds used for HW identification
    xT1, xT2 = get_threshold(
        Tmax, threshold_year_start, threshold_year_end, t1_quantile, t2_quantile)
    # print xland, xT1, xT2
    # find heat waves
    xHW = HWFinder(Tmax, hw_start, hw_end, xT1, xT2)
    return xHW

# write out HW results


def outputHW(fileout, xHW):
    result = []
    if len(xHW) > 1:
        HW = xHW[0].append(xHW[1])
        for i in range(2, len(xHW)):
            HW = HW.append(xHW[i])
            result = HW
    elif len(xHW) == 1:
        result = xHW[0]
    return result


# ##########################################################################
# # district initial
# ##########################################################################
#
# lat1 = np.arange(27.25, 50.75, 0.5)
# lon1 = np.arange(73.25, 98.25, 0.5)
# lat2 = np.arange(17.75, 55.25, 0.5)
# lon2 = np.arange(97.75, 135.25, 0.5)
# lat3 = np.arange(45.75, 55.25, 0.5)
# lon3 = np.arange(97.75, 115.25, 0.5)
#
# tgrid_district1 = grid_district(lat1, lon1)
# tgrid_district2 = grid_district(lat2, lon2)
# tgrid_district3 = grid_district(lat3, lon3)
# tgrid_district = [i for i in (
#     tgrid_district1 + tgrid_district2) if i not in tgrid_district3]
