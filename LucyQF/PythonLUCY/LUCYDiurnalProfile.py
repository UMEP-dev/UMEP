from __future__ import absolute_import
from builtins import map
from builtins import range
from builtins import object
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
from .DataManagement.TemporalProfileSampler import TemporalProfileSampler, is_holiday
from .DataManagement.LookupLogger import LookupLogger
from datetime import timedelta, datetime
class LUCYDiurnalProfile(object):
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
        rowHeadings = list(map(lower, dl[0][0:4]))
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
            tz = pytz.timezone(dl[list(dl.keys())[1]][3])
        except Exception:
            raise ValueError('Invalid timezone "' + dl[list(dl.keys())[1]][3] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Go through in triplets gathering up data for a template week
        earliestStart = None
        latestEnd = None
        dateRanges = []
        for seasonStart in np.arange(1, dl.shape[1]):
            try:
                sd = pd.datetime.strptime(dl[seasonStart][1], '%Y-%m-%d')
                ed = pd.datetime.strptime(dl[seasonStart][2], '%Y-%m-%d')
            except Exception as e:
                raise Exception('Rows 2 and 3 of ' + file + ' must be dates in the format YYYY-mm-dd')

            sd = tz.localize(sd)
            ed = tz.localize(ed)

            # Collect start and end dates to check for complete years later on
            if earliestStart == None:
                earliestStart = sd
            if latestEnd == None:
                latestEnd = ed

            earliestStart = sd if sd < earliestStart else earliestStart
            latestEnd = ed if ed > latestEnd else latestEnd
            dateRanges.extend(pd.date_range(sd, ed, freq='D'))

            # Amalgamate into a template week of data
            week = dl[seasonStart][firstDataLine:].astype('float')
            # Normalize each day's values by that day's sum so hourly relative variations are derived
            for day in range(0,7):
                hours = list(range(day*24, (day+1)*24))
                week.iloc[hours] = week.iloc[hours] / week.iloc[hours].sum()
            self.addWeeklyCycle(sd, ed, week)

        # Check for complete years. Raise exception if not complete.
        fullRange = pd.date_range('%d-01-01'%(earliestStart.year,), '%d-12-31'%(latestEnd.year,), freq='D')
        if len(fullRange) != len(dateRanges):
            raise Exception('Diurnal profile file %s must contain complete years of data (Jan 1 to Dec 31), but starts on %s and ends on %s'%(file, earliestStart.strftime('%Y-%m-%d'), latestEnd.strftime('%Y-%m-%d')))

    def addWeeklyCycle(self, sd, ed, week):
        '''
        Adds a weekly cycle to the object
        :param sd:  TZ Localized datetime: Start date of period represented by data
        :param ed:  TZ Localized datetime: End date of period represented by data
        :param week: Pd.Series: Continuous week (Monday-Sunday) of values upon which to base the diurnal cycle
        '''
        self.diurnal.addPeriod(startDate=sd, endDate=ed, dataSeries=week)

