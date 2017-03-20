# Object that stores and retrieves diurnal profiles for different seasons and times of day for LUCY
# A profile is a week-long template of relative quantity e.g. traffic, energy use or metabolic rate used for scaling later.

import os
from string import lower
try:
    import pandas as pd
    import numpy as np
except:
    pass
import pytz
from DataManagement.TemporalProfileSampler import TemporalProfileSampler, is_holiday
from DataManagement.LookupLogger import LookupLogger
from datetime import timedelta, datetime
class LUCYDiurnalProfile:
    def __init__(self, areaTimezone, weekendDays, use_uk_holidays, other_holidays = [], logger= LookupLogger()):
        ''' Instantiate
        :param areaTimezone: Time zone string defining the study area's time zone
        :param weekendDays: list of int specifying which days of week are weekend days. 0 = Monday, 6 = Sunday.
        :param timezone : String specifying which timezone to use. Must be compatible with pytz.timezone standard
        :param use_uk_holidays : Boolean: use (True) or don't use (False) standard UK bank holidays (calculated internally)
        :param other_holidays : list() of public holidays (datetime objects). These always get used, regardless of use_uk_holidays.
        '''
        self.logger = logger

        self.diurnal = TemporalProfileSampler(self.logger)
        self.diurnal.setCountry(areaTimezone)
        self.diurnal.useUKHolidays(use_uk_holidays)
        self.diurnal.specialHolidays(other_holidays)
        self.diurnal.setWeekendDays(weekendDays)
        self.useUkHolidays = use_uk_holidays

    def addProfile(self, file):
        ''' Add in a file containing profile. Can be called multiple times to add multiple years.
        :param file: name of .csv file to load
        '''
        self.dealWithInputFile(file)

    def getValueAtTime(self, timeBinEnd, timeBinDuration):
        ''' Retrieve traffic value for the requested date and time.
        :param requestDateTime: datetime() object for which to get data'''
        return self.diurnal.getValueForDateTime(timeBinEnd, timeBinDuration)

    def dealWithInputFile(self, file):
        ''' Generic method to add a profile by loading a file.
        File must contain a single week-long time series of values starting on Monday morning and ending on Sunday night.
        '''

        if not os.path.exists(file):
            raise ValueError('The file ' + file + ' does not exist')
        # Check file is of correct format
        dl = pd.read_csv(file,skipinitialspace=True, header=None)

        # Expect certain keywords
        rowHeadings = map(lower, dl[0][0:4])
        if 'season' != rowHeadings[0]:
            raise ValueError('First column of row 1 must be \'Season\' in ' + file)

        if 'startdate' != rowHeadings[1]:
            raise ValueError('First column of row 2 must be \'StartDate\' in ' + file)

        if 'enddate' != rowHeadings[2]:
            raise ValueError('First column of row 3 must be \'EndDate\' in ' + file)

        if 'timezone' != rowHeadings[3]:
            raise ValueError('First column of row 4 must be \'Timezone\' in ' + file)

        firstDataLine = 4
        # Try to extract the timezone from the file header
        try:
            tz = pytz.timezone(dl[dl.keys()[1]][3])
        except Exception:
            raise ValueError('Invalid timezone "' + dl[dl.keys()[1]][3] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Go through in triplets gathering up data for a template week
        for seasonStart in np.arange(1, dl.shape[1]):
            try:
                sd = pd.datetime.strptime(dl[seasonStart][1], '%Y-%m-%d')
                ed = pd.datetime.strptime(dl[seasonStart][2], '%Y-%m-%d')
            except Exception, e:
                raise Exception('Rows 2 and 3 of ' + file + ' must be dates in the format YYYY-mm-dd')

            sd = tz.localize(sd)
            ed = tz.localize(ed)

            # TODO: Reinstate this when the input data is UTC and the code knows which country is represented
            # Check data doesn't cross DST changes
            #if len(np.unique(tzsecs)) > 1:
            #    raise ValueError('The period ' + sd.strftime('%Y-%m-%d') +
            #                     ' to ' + ed.strftime('%Y-%m-%d')
            #                     + ' crosses one or more daylight savings changes. Separate periods must be specified before and after each change.')

            # Amalgamate into a template week of data
            week = dl[seasonStart][firstDataLine:].astype('float')
            # Normalize each day's values by that day's sum so hourly relative variations are derived
            for day in range(0,7):
                hours = range(day*24, (day+1)*24)
                week.iloc[hours] = week.iloc[hours] / week.iloc[hours].sum()
            self.addWeeklyCycle(sd, ed, week)

    def addWeeklyCycle(self, sd, ed, week):
        '''
        Adds a weekly cycle to the object
        :param sd:  TZ Localized datetime: Start date of period represented by data
        :param ed:  TZ Localized datetime: End date of period represented by data
        :param week: Pd.Series: Continuous week (Monday-Sunday) of values upon which to base the diurnal cycle
        '''
        self.diurnal.addPeriod(startDate=sd, endDate=ed, dataSeries=week)

def testIt():
    # Add and retrieve test data
    a = LUCYDiurnalProfile('Europe/Athens',  weekendDays=[5,6], use_uk_holidays=False)
    a.addProfile('N:/QF_Heraklion/LUCYConfig/transportProfile.csv')

    timeBins = pd.date_range(pd.datetime.strptime('2015-01-16 09:00', '%Y-%m-%d %H:%M'), periods=7, tz='UTC',
                             freq='24H')

    for dp in timeBins:
        time = dp.to_datetime()
        print (a.getValueAtTime(time, 3600), time)


def test_building():
    # Add and retrieve test data with multi seasons
    from matplotlib import pyplot as plt
    a = LUCYDiurnalProfile('Europe/Athens',  weekendDays=[5,6], use_uk_holidays=True)
    a.addProfile('N:/QF_Heraklion/LUCYConfig/buildingProfiles_Heraklion.csv')

    timeBins = pd.date_range(pd.datetime.strptime('2015-12-31 00:00', '%Y-%m-%d %H:%M'), periods=24*365, tz='UTC',
                             freq='H')

    dataPoints = []
    timePoints = []
    for dp in timeBins:
        time = dp.to_datetime()
        print (a.getValueAtTime(time, 3600), time.strftime('%Y-%m-%d %H:%M'), time.weekday())
        dataPoints.append(a.getValueAtTime(time,3600)[0])
        timePoints.append(dp)
    plt.figure()
    plt.plot(timePoints, dataPoints)
    plt.show()

