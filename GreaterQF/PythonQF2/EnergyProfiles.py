from __future__ import absolute_import
from builtins import map
from builtins import range
from builtins import object
# Object that stores and retrieves energy use profiles for different seasons and times of day for GreaterQF
# An energy profile is a week-long template of relative energy use that changes only with season

import os
# from string import lower
try:
    import numpy as np
    import pandas as pd
except:
    pass

import pytz
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.TemporalProfileSampler import TemporalProfileSampler

class EnergyProfiles(object):
    def __init__(self, city, use_uk_holidays, customHolidays = [], logger=LookupLogger()):
        ''' Instantiate
        :param city : String specifying which city is being modelled (e.g. Europe/London). Must be compatible with pytz.timezone standard
        :param use_uk_holidays : Boolean: use (True) or don't use (False) standard UK bank holidays (calculated internally)
        :param other_holidays : list() of public holidays (datetime objects). These always get used, regardless of use_uk_holidays.
        :param logger: LookupLogger: Logger object
        '''
        self.logger = logger

        self.domesticElectricity = TemporalProfileSampler(logger=self.logger)
        self.domesticElectricity.useUKHolidays(use_uk_holidays)
        self.domesticElectricity.setCountry(city)
        self.domesticElectricity.specialHolidays(customHolidays)
        self.domesticElectricity.setWeekendDays([5,6]) # Future version: Support other weekdays

        self.economy7 = TemporalProfileSampler(logger=self.logger)
        self.economy7.useUKHolidays(use_uk_holidays)
        self.economy7.setCountry(city)
        self.economy7.specialHolidays(customHolidays)
        self.economy7.setWeekendDays([5,6])

        self.domesticGas = TemporalProfileSampler(logger=self.logger)
        self.domesticGas.useUKHolidays(use_uk_holidays)
        self.domesticGas.setCountry(city)
        self.domesticGas.specialHolidays(customHolidays)
        self.domesticGas.setWeekendDays([5,6])

        self.industrialElectricity = TemporalProfileSampler(logger=self.logger)
        self.industrialElectricity.useUKHolidays(use_uk_holidays)
        self.industrialElectricity.setCountry(city)
        self.industrialElectricity.specialHolidays(customHolidays)
        self.industrialElectricity.setWeekendDays([5,6])

        self.industrialGas = TemporalProfileSampler(logger=self.logger)
        self.industrialGas.useUKHolidays(use_uk_holidays)
        self.industrialGas.setCountry(city)
        self.industrialGas.specialHolidays(customHolidays)
        self.industrialGas.setWeekendDays([5,6])

    def addDomElec(self, file):
        ''' Add in a file containing domestic electricity profiles. Can be called multiple times to add multiple years.
        :param file: name of .csv file to load
        '''
        self.dealWithInputFile(self.domesticElectricity, file)

    # methods that follow the same pattern as addDomElec()
    def addIndElec(self, file):
        self.dealWithInputFile(self.industrialElectricity, file)

    def addEconomy7(self, file):
        self.dealWithInputFile(self.economy7, file)

    def addIndGas(self, file):
        self.dealWithInputFile(self.industrialGas, file)

    def addDomGas(self, file):
        self.dealWithInputFile(self.domesticGas, file)

    def getDomElec(self, timeBinEnd, timeBinDuration):
        ''' Retrieve domestic electricity value for the requested date and time.
        :param requestDateTime: datetime() object for which to get data'''
        return self.domesticElectricity.getValueForDateTime(timeBinEnd, timeBinDuration)

    # Methods that follow the same pattern as getDomElec()
    def getIndElec(self, timeBinEnd, timeBinDuration):
        return self.industrialElectricity.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getEconomy7(self, timeBinEnd, timeBinDuration):
        return self.economy7.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getDomGas(self, timeBinEnd, timeBinDuration):
        return self.domesticGas.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getIndGas(self,  timeBinEnd, timeBinDuration):
        return self.industrialGas.getValueForDateTime(timeBinEnd, timeBinDuration)

    def dealWithInputFile(self, energyComponent, file):
        ''' Generic method to add a profile for a particular energy type by loading a file
        File must contain triplets of diurnal cycles for each season, "Weekday", "Saturday", "Sunday"
        '''

        if not os.path.exists(file):
            raise ValueError('The file ' + file + ' does not exist')

        # Check file is of correct format

        dl = pd.read_csv(file,skipinitialspace=True, header=None)

        # Should be 3x each season in header
        if (len(list(dl.keys()))-1)%3 != 0:
            raise ValueError('There must be 3 columns for each named season in ' + file)

        # Expect certain keywords
        rowHeadings = list(map(str.lower, dl[0][0:6]))
        if 'season' != rowHeadings[0]:
            raise ValueError('First column of row 1 must be \'Season\' in ' + file)

        if 'day' != rowHeadings[1]:
            raise ValueError('First column of row 2 must be \'Day\' in ' + file)

        if 'tariff' != rowHeadings[2]:
            raise ValueError('First column of row 3 must be \'Tariff\' in ' + file)

        if 'startdate' != rowHeadings[3]:
            raise ValueError('First column of row 4 must be \'StartDate\' in ' + file)

        if 'enddate' != rowHeadings[4]:
            raise ValueError('First column of row 5 must be \'EndDate\' in ' + file)

        if 'timezone' != rowHeadings[5]:
            raise ValueError('First column of row 6 must be \'Timezone\' in ' + file)

        firstDataLine = 6
        # Try to extract the timezone from the file header
        try:
            tz = pytz.timezone(dl[list(dl.keys())[1]][5])
        except Exception:
            raise ValueError('Invalid timezone "' + dl[list(dl.keys())[1]][5] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        earliestStart = None
        latestEnd = None
        dateRanges = []

        # Go through in triplets gathering up data for a template week
        for seasonStart in np.arange(1, dl.shape[1], 3):
            try:
                sd = pd.datetime.strptime(dl[seasonStart][3], '%Y-%m-%d')
                ed = pd.datetime.strptime(dl[seasonStart][4], '%Y-%m-%d')
            except Exception as e:
                raise Exception('Rows 4 and 5 of ' + file + ' must be dates in the format YYYY-mm-dd')

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

            # Normalize each day's series so it's a weighting factor
            for i in range(0,3,1):
                dl[seasonStart+i][firstDataLine:] = dl[seasonStart+i][firstDataLine:].astype('float')/dl[seasonStart+i][firstDataLine:].astype('float').mean()

            # Amalgamate into a template week of data
            week = pd.concat([dl[seasonStart][firstDataLine:],
                              dl[seasonStart][firstDataLine:],
                              dl[seasonStart][firstDataLine:],
                              dl[seasonStart][firstDataLine:],
                              dl[seasonStart][firstDataLine:],
                              dl[seasonStart+1][firstDataLine:],
                              dl[seasonStart+2][firstDataLine:]])
            energyComponent.addPeriod(startDate=sd, endDate=ed, dataSeries=week)

        # Check for complete years. Raise exception if not complete.
        fullRange = pd.date_range('%d-01-01'%(earliestStart.year,), '%d-12-31'%(latestEnd.year,), freq='D')
        if len(fullRange) != len(dateRanges):
            raise Exception('Diurnal profile file %s must contain complete years of data (Jan 1 to Dec 31), but starts on %s and ends on %s'%(file, earliestStart.strftime('%Y-%m-%d'), latestEnd.strftime('%Y-%m-%d')))

