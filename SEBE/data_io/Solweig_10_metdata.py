from importdata import importdata
from sun_position import sun_position
import numpy as np

def Solweig_10_metdata(inputdata, location, UTC):
    """
    This function is used to process the input meteorological file.
    It also calculates Sun position based on the time specified in the met-file

    :param inputdata:
    :param location:
    :param UTC:
    :return:
    """

    Newdata1, _, _ = importdata(inputdata, '\t', 1)
    met = Newdata1['data']
    met_header = Newdata1['textdata']
    time = dict()
    time['min'] = 30
    time['sec'] = 0
    # (sunposition one halfhour before metdata)
    time['UTC'] = UTC

    # initialize matrices
    data_len = len(Newdata1['data'][:, 0])
    altitude = np.empty(shape=(1, data_len))
    azimuth = np.empty(shape=(1, data_len))
    zen = np.empty(shape=(1, data_len))
    jday = np.empty(shape=(1, data_len))

    for i, row in enumerate(Newdata1['data'][:, 0]):
        time['year'] = float(met[i, 0])
        time['month'] = float(met[i, 1])
        time['day'] = float(met[i, 2])
        time['hour'] = float(met[i, 3])

        #print(time)
        #print(location)
        sun = sun_position(time, location)
        #print sun
        altitude[0, i] = 90 - sun['zenith']
        azimuth[0, i] = sun['azimuth']
        zen[0, i] = sun['zenith'] * (np.pi/180)

        # day of year and check for leap year
        if isleapyear(time['year']):
            dayspermonth = np.atleast_2d([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        else:
            dayspermonth = np.atleast_2d([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        jday[0, i] = np.sum(dayspermonth[0, 0:time['month']-1]) + time['day']

    # if time.year<2000, year=time.year-1900 ; else year=time.year-2000; end
    # if year<10, XY='0'; else XY=''; end
    if time['month'] < 10:
        XM = '0'
    else:
        XM = ''
    if time['day'] < 10:
        XD = '0'
    else:
        XD = np.str('')
    return met, met_header, time, altitude, azimuth, zen, jday, XM, XD

def isleapyear(year):
    if (year % 4) == 0:
        if (year % 100) == 0:
            if (year % 400) == 0:
                return True
    return False
