from __future__ import absolute_import
from builtins import map
from builtins import range
from builtins import object
# Object that stores and retrieves diurnal cycles of metabolic activity profiles for different seasons and times of day for GreaterQF

import os
from string import lower
try:
    import numpy as np
    import pandas as pd
except:
    pass
import pytz
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.TemporalProfileSampler import TemporalProfileSampler


class HumanActivityProfiles(object):
    def __init__(self, city, use_uk_holidays, customHolidays = [], logger=LookupLogger()):
        ''' Instantiate
        :param city: string: City being modelled (in time zone format e.g. Europe/London)
        :param use_uk_holidays : Boolean: use (True) or don't use (False) standard UK bank holidays (calculated internally)
        :param customHolidays : list() of public holidays (datetime objects). These always get used, regardless of use_uk_holidays.
        '''
        self.logger = logger
        self.energy = TemporalProfileSampler(logger=self.logger)
        self.energy.useUKHolidays(use_uk_holidays)
        self.energy.setCountry(city)
        self.energy.specialHolidays(customHolidays)
        self.energy.setWeekendDays([5,6])

        self.fraction = TemporalProfileSampler(logger=self.logger)
        self.fraction.useUKHolidays(use_uk_holidays)
        self.fraction.setCountry(city)
        self.fraction.specialHolidays(customHolidays)
        self.fraction.setWeekendDays([5,6])

    def addProfiles(self, file):
        ''' Add in a data file containing all of the transport types for a given period'''
        self.dealWithInputFile(file)

    def getWattPerson(self, timeBinEnd, timeBinDuration):
        ''' Retrieve metabolic activity per person value for the requested date and time.
        :param requestDateTime: datetime() object for which to get data'''
        return self.energy.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getFraction(self, timeBinEnd, timeBinDuration):
        ''' Return fraction of population undergoing metabolic activity
        '''
        return self.fraction.getValueForDateTime(timeBinEnd, timeBinDuration)

    def dealWithInputFile(self, file):
        ''' Generic method to add a profile for metabolic activity for multiple seasons of the year (if desired) by loading a file
        File must contain 6 diurnal cycles for each season, 3 metabolic activity "Weekday", "Saturday", "Sunday" and (correspondingly) 3 fractions active
        '''

        if not os.path.exists(file):
            raise ValueError('The file ' + file + ' does not exist')

        # Check file is of correct format
        dl = pd.read_csv(file,skipinitialspace=True, header=None)

        # Should be 3x each season in header
        if (len(list(dl.keys()))-1)%3 != 0:
            raise ValueError('There must be 6 columns for each named season in ' + file)
        rowHeaders = list(map(lower, dl[0][0:6]))

        firstDataRow = 6
        # Expect certain keywords
        if 'season' != rowHeaders[0]:
            raise ValueError('First column of row 1 must be \'Season\' in ' + file)

        if 'day' != rowHeaders[1]:
            raise ValueError('First column of row 2 must be \'Day\' in ' + file)

        if 'type' != rowHeaders[2]:
            raise ValueError('First column of row 3 must be \'Type\' (of cycle for that column) in ' + file)

        if 'startdate' != rowHeaders[3]:
            raise ValueError('First column of row 4 must be \'StartDate\' (of season) in ' + file)

        if 'enddate' != rowHeaders[4]:
            raise ValueError('First column of row 5 must be \'EndDate\' (of season) in ' + file)

        if 'timezone' != rowHeaders[5]:
            raise ValueError('First column of row 6 must be \'Timezone\' (of data for that season) in ' + file)

        # Check that the right "Type" entries are present
        if 'energy' != lower(dl[1][2]):
            raise ValueError('Second column of row 3 must be \'Energy\' (metabolic energy) in ' + file)

        if 'fraction' != lower(dl[2][2]):
            raise ValueError('Second column of row 3 must be \'Fraction\' (fraction of population doing work) in ' + file)

        if len(pd.unique(dl.iloc[2][1:])) != 2:
            raise ValueError('Headers in row 5 must be alternating list of \'Energy\' and \'Fraction\' in ' + file)

        # Try and get timezone set up
        try:
            tz = pytz.timezone(dl[list(dl.keys())[1]][5])

        except Exception:
            raise ValueError('Invalid timezone "' + dl[list(dl.keys())[1]][5] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Go through in sextouplets gathering up data for a template week
        for seasonStart in np.arange(1, dl.shape[1], 6):
            try:
                sd = pd.datetime.strptime(dl[seasonStart][3], '%Y-%m-%d')
                ed = pd.datetime.strptime(dl[seasonStart][4], '%Y-%m-%d')
            except Exception as e:
                raise Exception('Rows 4 and 5 ' + file + ' must be dates in the format YYYY-mm-dd')

            sd = tz.localize(sd)
            ed = tz.localize(ed)

            for i in range(0,6,1):
                dl[seasonStart+i][firstDataRow:] = dl[seasonStart+i][firstDataRow:].astype('float')

            # Amalgamate into a template weeks of data
            energyWeek = pd.concat([dl[seasonStart][firstDataRow:],
                                    dl[seasonStart][firstDataRow:],
                                    dl[seasonStart][firstDataRow:],
                                    dl[seasonStart][firstDataRow:],
                                    dl[seasonStart][firstDataRow:],
                                    dl[seasonStart+2][firstDataRow:],
                                    dl[seasonStart+4][firstDataRow:]])

            fractionWeek = pd.concat([dl[seasonStart+1][firstDataRow:],
                                      dl[seasonStart+1][firstDataRow:],
                                      dl[seasonStart+1][firstDataRow:],
                                      dl[seasonStart+1][firstDataRow:],
                                      dl[seasonStart+1][firstDataRow:],
                                      dl[seasonStart+3][firstDataRow:],
                                      dl[seasonStart+5][firstDataRow:]])

            self.fraction.addPeriod(startDate=sd, endDate=ed, dataSeries=fractionWeek)
            self.energy.addPeriod(startDate=sd, endDate=ed, dataSeries=energyWeek)
