from builtins import str
from builtins import range
# -*- coding: utf-8 -*-
###########################################################################
#
#                               HWFinder
#
###########################################################################

# preloaded packages
from datetime import datetime, timedelta, time
import math
import datetime

try:
    import pandas as pd
    from netCDF4 import Dataset, date2num, num2date
    import numpy as np
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

# Get Tdata from the new data set.
def get_ncdata(filepath, year_start, year_end, data_variable_name):
    nc = Dataset(filepath)
    xTair = nc.variables[data_variable_name][:,0,0].squeeze() # IF there is more than one grid point included, just take the south-west corner
    times = nc.variables['time']
    xdate = num2date(times[:], times.units)
    Tair = pd.Series(xTair, index=xdate)
    unit = nc.variables[data_variable_name].units
    try:  # If lat and lon are available, use them. The user will be prompted to enter them later if they're not present.
        lat = nc.variables['latitude'][0] # If more than one latitude and longitude included, just take the first corner
        lon = nc.variables['longitude'][0]
    except:
        lat = None
        lon = None
    start_time = xdate[0]
    end_time = xdate[len(xdate)-2]
    nc.close()
    return (Tair['%d' % year_start:'%d' % year_end], unit, lat, lon, start_time, end_time)

def get_ncmetadata(filepath):
    # Get start and end time and lat and lon for netcdf file (if avialable)
    try:
        nc = Dataset(filepath)
        times = nc.variables['time']
    except:
        nc.close()
        raise Exception('Invalid .nc file. Must contain \'time\' dimension and be a NetCDF file')

    xdate = num2date(times[:], times.units)
    try:  # If lat and lon are available, use them. The user will be prompted to enter them later if they're not present.
        lat = nc.variables['latitude'][0] # If more than one latitude and longitude included, just take the first corner
        lon = nc.variables['longitude'][0]
    except:
        lat = None
        lon = None
    start_time = xdate[0]
    end_time = xdate[len(xdate)-2] # Final date is the midnight the day after; we want day before
    nc.close()
    return (lat, lon, start_time, end_time)

def get_txtdata(filepath, year_start, year_end, data_start_time, data_end_time):
    xTair = pd.read_csv(filepath,header=None)[0]
    xdate = pd.date_range(data_start_time, data_end_time)
    if len(xTair) != len(xdate):
        raise ValueError('Please set the start and end dates to match the text file. Dates cover %d days but file contains %d days'%(len(xdate), len(xTair)))
    data = xTair.values.tolist()
    Tair = pd.Series(data, index=xdate)
    return Tair['%d' % year_start:'%d' % year_end]
    
# get the threshold from the specified percentage.
# one is for all period, and the other is for MJJASO in every year

def get_threshold(data, threshold_year_start, threshold_year_end, percent):
    data = data['%d' % threshold_year_start:'%d' % threshold_year_end]
    return np.percentile(data, percent)

def get_MJJASOthreshold(data, threshold_year_start, threshold_year_end, percent1, lat):
    dataMJJASO = []
    if lat >= 0:
        for i in range(threshold_year_start,threshold_year_end+1):
            dataMJJASO.extend(data[str(i)+'-05':str(i)+'-10'])
    else:
        for i in range(threshold_year_start,threshold_year_end+1):
            dataMJJASO.extend(data[str(i)+'-01':str(i)+'-04'])
            dataMJJASO.extend(data[str(i)+'-11':str(i)+'-11'])
    return np.percentile(dataMJJASO, percent1)

def get_Tdata_Tdif_365(data):
    '''
    Get difference between daily temperature and its annual average
    '''
    year_start = data.index[0].year
    year_end = data.index[len(data.index)-2].year
    T365 = np.zeros((0,365))
    Tdif365 = []
    date = []
    for year in range(year_start, year_end+1):
        if len( data['%d' % year:'%d' % year]) < 365:
            continue # Only allow full years of data
        new_data =  np.zeros((1,365))
        new_data[0] = data['%d' % year:'%d' % year][0:365]
        T365 = np.append(T365, new_data, axis=0)

    Tavg365 = np.average(T365, axis=0)

    for year in range(year_start, year_end+1):
        if len( data['%d' % year:'%d' % year]) < 365:
            continue # Only allow full years of data
        xdate = pd.date_range('%d-01-01' % year, '%d-12-31' % year)[0:365]
        date.extend(xdate)
        Tdif365.extend(T365[year - year_start]-Tavg365)

    Tdif= pd.Series(Tdif365, index=date)
    Tdata = pd.Series(T365.flatten().tolist(), index=date)
    return Tdata,Tdif

# Find HWs
def MeehlHWFinder(Tair, hw_start, hw_end, xT1, xT2):
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

    def MeehlHWSearch(data, T1, T2):
        # shortest scenario:
        if np.sort(data)[-3] <= T1:
            return False
        # longer scenarios:
        else:
            if np.mean(data) > T1:
                sub_filter2.append(data)
            else:
                return MeehlHWSearch(data[:-1], T1, T2), MeehlHWSearch(data[1:], T1, T2)

    MeehlHWSearch = memoize(MeehlHWSearch)

    [MeehlHWSearch(sub_filter1[tind[0]:tind[-1] + 1], xT1, xT2) for tind in ind]
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

def VautardHWFinder(Tair, hw_start, hw_end, xT1):
    hw_date = pd.date_range(hw_start, hw_end)
    Tair = pd.Series(Tair, index=hw_date)
    sub_filter1 = Tair[Tair > xT1]
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

    def VautardHWSearch(data):
        # shortest scenario:
        if len(data)<= 2:
            return False
        # longer scenarios:
        else:
            sub_filter2.append(data)


    [VautardHWSearch(sub_filter1[tind[0]:tind[-1] + 1]) for tind in ind]
    if (sub_filter2) == 0:
        return sub_filter2
    return sub_filter2

def FischerHWFinder(Tair, hw_start, hw_end, xT1):
    hw_date = pd.date_range(hw_start, hw_end)
    Tair = pd.Series(Tair, index=hw_date)
    sub_filter1 = Tair[Tair > xT1]
    if len(sub_filter1) == 0:
        return sub_filter1

    #  subsequence for at least three consecutive days
    tind = [0]
    ind = []
    for i in range(1, len(sub_filter1)):
        if (sub_filter1.index[i] - sub_filter1.index[i - 1]) == timedelta(days=1):
            tind.append(i)
        else:
            if len(tind) >= 6:
                ind.append(tind)
            tind = [i]
    if len(tind) >= 6:
        ind.append(tind)
    if len(ind) == 0:
        return ind

    #  the daily maximum temperature must be above T1 for at least 3 days,
    # the average daily maximum temperature must be above T1 for the entire
    # period
    sub_filter2 = []

    def FischerHWSearch(data):
        # shortest scenario:
        if len(data)<= 5:
            return False
        # longer scenarios:
        else:
            sub_filter2.append(data)


    [FischerHWSearch(sub_filter1[tind[0]:tind[-1] + 1]) for tind in ind]
    if (sub_filter2) == 0:
        return sub_filter2
    return sub_filter2

def KeevallikCWFinder(Tair, hw_start, hw_end, xT1):
    cw_date = pd.date_range(hw_start, hw_end)
    Tair = pd.Series(Tair, index=cw_date)
    sub_filter1 = Tair[Tair < xT1]
    if len(sub_filter1) == 0:
        return sub_filter1

    #  subsequence for at least 6 consecutive days
    tind = [0]
    ind = []
    for i in range(1, len(sub_filter1)):
        if (sub_filter1.index[i] - sub_filter1.index[i - 1]) == timedelta(days=1):
            tind.append(i)
        else:
            if len(tind) >= 6:
                ind.append(tind)
            tind = [i]
    if len(tind) >= 6:
        ind.append(tind)
    if len(ind) == 0:
        return ind

    sub_filter2 = []

    def KeevallikCWSearch(data):
        # shortest scenario:
        if len(data)<= 5:
            return False
        # longer scenarios:
        else:
            sub_filter2.append(data)


    [KeevallikCWSearch(sub_filter1[tind[0]:tind[-1] + 1]) for tind in ind]
    if (sub_filter2) == 0:
        return sub_filter2
    return sub_filter2


def SrivastavaCWFinder(Tair, Tdif, TempDif):
    sub_filter1 = Tair[Tdif <= TempDif]
    if len(sub_filter1) == 0:
        return sub_filter1

    #  subsequence for at least 6 consecutive days
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

    sub_filter2 = []

    def SrivastavaCWSearch(data):
        # shortest scenario:
        if len(data)<= 2:
            return False
        # longer scenarios:
        else:
            sub_filter2.append(data)
    [SrivastavaCWSearch(sub_filter1[tind[0]:tind[-1] + 1]) for tind in ind]
    if (sub_filter2) == 0:
        return sub_filter2
    return sub_filter2

def BusuiocCWFinder(Tair, Tdif, TempDif):
    sub_filter1 = Tair[Tdif <= TempDif]
    if len(sub_filter1) == 0:
        return sub_filter1

    #  subsequence for at least 6 consecutive days
    tind = [0]
    ind = []
    for i in range(1, len(sub_filter1)):
        if (sub_filter1.index[i] - sub_filter1.index[i - 1]) == timedelta(days=1):
            tind.append(i)
        else:
            if len(tind) >= 6:
                ind.append(tind)
            tind = [i]
    if len(tind) >= 6:
        ind.append(tind)
    if len(ind) == 0:
        return ind

    sub_filter2 = []

    def BusuiocCWSearch(data):
        # shortest scenario:
        if len(data)<= 5:
            return False
        # longer scenarios:
        else:
            sub_filter2.append(data)
    [BusuiocCWSearch(sub_filter1[tind[0]:tind[-1] + 1]) for tind in ind]
    if (sub_filter2) == 0:
        return sub_filter2
    return sub_filter2


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



def level(minvalue, maxvalue):
    lev_tan = np.arange(1, 5, 0.4)
    lev = [math.atan(i) for i in lev_tan]
    levels = [(i - lev[0]) / (lev[-1] - lev[0]) *
              (maxvalue - minvalue) + minvalue for i in lev]
    return levels


# identify HW periods

# Meehl and Tebaldi (2004)
def findHW_Meehl(Tmax,
           hw_start, hw_end,
           threshold_year_start, threshold_year_end,
           t1_quantile, t2_quantile):
    # thresholds used for HW identification
    xT1 = get_threshold(Tmax, threshold_year_start, threshold_year_end, t1_quantile)
    xT2 = get_threshold(Tmax, threshold_year_start, threshold_year_end, t2_quantile)
    # find heat waves
    xHW = MeehlHWFinder(Tmax, hw_start, hw_end, xT1, xT2)
    return xHW

# Vautard et al. (2013)
# 3 consecutive days above the 90th percentile of daily mean temperature
# need to change Tmax to Tmean
def findHW_Vautard(Tmax,
           hw_start, hw_end,
           threshold_year_start, threshold_year_end,
           t1_quantile):
    # thresholds used for HW identification
    xT1 = get_threshold(Tmax, threshold_year_start, threshold_year_end, t1_quantile)
    # find heat waves
    xHW = VautardHWFinder(Tmax, hw_start, hw_end, xT1)
    return xHW

# Schoetter et al. (2014)
# 3 consecutive days above the 98th percentile (MJJASO) of maximum temperature
def findHW_Schoetter(Tmax,
           hw_start, hw_end,
           threshold_year_start, threshold_year_end,
           t1_quantile, lat):
    # thresholds used for HW identification
    xT1= get_MJJASOthreshold(
        Tmax, threshold_year_start, threshold_year_end, t1_quantile, lat)
    # find heat waves
    xHW = VautardHWFinder(Tmax, hw_start, hw_end, xT1)
    return xHW

# Fischer and Schar (2010)
# Multi-measurement index—periods of at least 6days where maximum
# temperature exceeds the calendar day 90th percentile (15day calendar window).
def findHW_Fischer(Tmax,
           hw_start, hw_end,
           threshold_year_start, threshold_year_end,
           t1_quantile):
    # thresholds used for HW identification
    xT1 = get_threshold(Tmax, threshold_year_start, threshold_year_end, t1_quantile)
    # find heat waves
    xHW = FischerHWFinder(Tmax, hw_start, hw_end, xT1)
    return xHW

# Sirje Keevallik （2015）
# cold night: temperature lower than 10th percentile of daily minimal temperatures
# calculated for a 5-day window centred on each calendar day in 1961–1990;
# cold wave: six consecutive cold nights;
def findCW_Keevallik(Tmin,
           hw_start, hw_end,
           threshold_year_start, threshold_year_end,
           t1_quantile):
    # thresholds used for HW identification
    xT1 = get_threshold(Tmin, threshold_year_start, threshold_year_end, t1_quantile)
    xHW = KeevallikCWFinder(Tmin, hw_start, hw_end, xT1)
    return xHW

# Srivastava (2009)
# a cold wave is defined if the minimum temperature at a grid point is below the
# normal temperature by 3 °C or more, consecutively for 3 days or more.
def findCW_Srivastava(Tmin, hw_start, hw_end,  TempDif):
    Tdata,Tdif = get_Tdata_Tdif_365(Tmin)
    cw_date = pd.date_range(hw_start, hw_end)
    Tdata = Tdata[cw_date]
    Tdif = Tdif[cw_date]
    xHW = SrivastavaCWFinder(Tdata, Tdif, TempDif)
    return xHW

# Busuioc et al., (2010)
# at least 6 consecutive days with negative deviations of at least 5°C from the normal value of each calendar day
def findCW_Busuioc(Tmin, hw_start, hw_end, TempDif):
    Tdata,Tdif = get_Tdata_Tdif_365(Tmin)
    cw_date = pd.date_range(hw_start, hw_end)
    Tdata = Tdata[cw_date]
    Tdif = Tdif[cw_date]
    xHW = BusuiocCWFinder(Tdata, Tdif, TempDif)
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
