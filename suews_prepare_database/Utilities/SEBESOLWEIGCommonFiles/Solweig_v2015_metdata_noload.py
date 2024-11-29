from __future__ import absolute_import
# from importdata import importdata
from . import sun_position as sp
#import sun_position as sp
import numpy as np
import datetime
import calendar

def Solweig_2015a_metdata_noload(inputdata, location, UTC):
    """
    This function is used to process the input meteorological file.
    It also calculates Sun position based on the time specified in the met-file

    :param inputdata:
    :param location:
    :param UTC:
    :return:
    """

    met = inputdata
    data_len = len(met[:, 0])
    dectime = met[:, 1]+met[:, 2] / 24 + met[:, 3] / (60*24.)
    dectimemin = met[:, 3] / (60*24.)
    if data_len == 1:
        halftimestepdec = 0
    else:
        halftimestepdec = (dectime[1] - dectime[0]) / 2.
    time = dict()
    time['sec'] = 0
    time['UTC'] = UTC
    sunmaximum = 0.
    leafon1 = 97  #TODO this should change
    leafoff1 = 300  #TODO this should change

    # initialize matrices
    altitude = np.empty(shape=(1, data_len))
    azimuth = np.empty(shape=(1, data_len))
    zen = np.empty(shape=(1, data_len))
    jday = np.empty(shape=(1, data_len))
    YYYY = np.empty(shape=(1, data_len))
    leafon = np.empty(shape=(1, data_len))
    altmax = np.empty(shape=(1, data_len))

    sunmax = dict()

    for i, row in enumerate(met[:, 0]):
        if met[i, 1] == 221:
            test = 4
        YMD = datetime.datetime(int(met[i, 0]), 1, 1) + datetime.timedelta(int(met[i, 1]) - 1)
        # Finding maximum altitude in 15 min intervals (20141027)
        if (i == 0) or (np.mod(dectime[i], np.floor(dectime[i])) == 0):
            fifteen = 0.
            sunmaximum = -90.
            sunmax['zenith'] = 90.
            while sunmaximum <= 90. - sunmax['zenith']:
                sunmaximum = 90. - sunmax['zenith']
                fifteen = fifteen + 15. / 1440.
                HM = datetime.timedelta(days=(60*10)/1440.0 + fifteen)
                YMDHM = YMD + HM
                time['year'] = YMDHM.year
                time['month'] = YMDHM.month
                time['day'] = YMDHM.day
                time['hour'] = YMDHM.hour
                time['min'] = YMDHM.minute
                sunmax = sp.sun_position(time,location)
        altmax[0, i] = sunmaximum

        half = datetime.timedelta(days=halftimestepdec)
        H = datetime.timedelta(hours=met[i, 2])
        M = datetime.timedelta(minutes=met[i, 3])
        YMDHM = YMD + H + M - half
        time['year'] = YMDHM.year
        time['month'] = YMDHM.month
        time['day'] = YMDHM.day
        time['hour'] = YMDHM.hour
        time['min'] = YMDHM.minute
        sun = sp.sun_position(time, location)
        altitude[0, i] = 90. - sun['zenith']
        azimuth[0, i] = sun['azimuth']
        zen[0, i] = sun['zenith'] * (np.pi/180.)

        # day of year and check for leap year
        if calendar.isleap(time['year']):
            dayspermonth = np.atleast_2d([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        else:
            dayspermonth = np.atleast_2d([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        # jday[0, i] = np.sum(dayspermonth[0, 0:time['month']-1]) + time['day'] # bug when a new day 20191015
        YYYY[0, i] = met[i, 0]
        doy = YMD.timetuple().tm_yday
        jday[0, i] = doy
        if (doy > leafon1) | (doy < leafoff1):
            leafon[0, i] = 1
        else:
            leafon[0, i] = 0

    return YYYY, altitude, azimuth, zen, jday, leafon, dectime, altmax




