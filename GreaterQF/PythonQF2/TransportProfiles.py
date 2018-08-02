from __future__ import absolute_import
from builtins import map
from builtins import str
from builtins import object
# Object that stores and retrieves diurnal cycles of road traffic for different seasons and times of day for GreaterQF
# An energy profile is a week-long template of relative energy use that changes only with season

import os
import string
try:
    import numpy as np
    import pandas as pd
except:
    pass
import pytz
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.TemporalProfileSampler import TemporalProfileSampler

class TransportProfiles(object):
    def __init__(self, city, use_uk_holidays, customHolidays = [], logger=LookupLogger()):
        ''' Instantiate
        :param city: String specifying the city being modelled (must be in timezone format e.g. Europe/London)
        :param timezone : String specifying which timezone to use. Must be compatible with pytz.timezone standard
        :param use_uk_holidays : Boolean: use (True) or don't use (False) standard UK bank holidays (calculated internally)
        :param customHolidays : list() of public holidays (datetime objects). These always get used, regardless of use_uk_holidays.
        '''

        self.logger = logger

        self.motorcycles = TemporalProfileSampler(logger=self.logger)
        self.motorcycles.useUKHolidays(use_uk_holidays)
        self.motorcycles.setCountry(city)
        self.motorcycles.specialHolidays(customHolidays)
        self.motorcycles.setWeekendDays([5,6])

        self.taxis = TemporalProfileSampler(logger=self.logger)
        self.taxis.useUKHolidays(use_uk_holidays)
        self.taxis.setCountry(city)
        self.taxis.specialHolidays(customHolidays)
        self.taxis.setWeekendDays([5,6])

        self.cars = TemporalProfileSampler(logger=self.logger)
        self.cars.useUKHolidays(use_uk_holidays)
        self.cars.setCountry(city)
        self.cars.specialHolidays(customHolidays)
        self.cars.setWeekendDays([5,6])

        self.buses = TemporalProfileSampler(logger=self.logger)
        self.buses.useUKHolidays(use_uk_holidays)
        self.buses.setCountry(city)
        self.buses.specialHolidays(customHolidays)
        self.buses.setWeekendDays([5,6])

        self.lgvs = TemporalProfileSampler(logger=self.logger)
        self.lgvs.useUKHolidays(use_uk_holidays)
        self.lgvs.setCountry(city)
        self.lgvs.specialHolidays(customHolidays)
        self.lgvs.setWeekendDays([5,6])

        self.rigids = TemporalProfileSampler(logger=self.logger)
        self.rigids.useUKHolidays(use_uk_holidays)
        self.rigids.setCountry(city)
        self.rigids.specialHolidays(customHolidays)
        self.rigids.setWeekendDays([5,6])

        self.artics = TemporalProfileSampler(logger=self.logger)
        self.artics.useUKHolidays(use_uk_holidays)
        self.artics.setCountry(city)
        self.artics.specialHolidays(customHolidays)
        self.artics.setWeekendDays([5,6])

    def addProfiles(self, file):
        ''' Add in a data file containing all of the transport types for a given period'''
        self.dealWithInputFile(file)

    def getMotorcycle(self, timeBinEnd, timeBinDuration):
        ''' Retrieve domestic electricity value for the requested date and time.
        :param requestDateTime: datetime() object for which to get data'''
        return self.motorcycles.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getTaxi(self, timeBinEnd, timeBinDuration):
        return self.taxis.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getCar(self, timeBinEnd, timeBinDuration):
        return self.cars.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getBus(self, timeBinEnd, timeBinDuration):
        return self.buses.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getLGV(self, timeBinEnd, timeBinDuration):
        return self.lgvs.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getRigid(self, timeBinEnd, timeBinDuration):
        return self.rigids.getValueForDateTime(timeBinEnd, timeBinDuration)

    def getArtic(self, timeBinEnd, timeBinDuration):
        return self.artics.getValueForDateTime(timeBinEnd, timeBinDuration)

    def dealWithInputFile(self, file):
        ''' Generic method to add a profile for transport data. Only allows one period to be added, as
        many vehicle types are involved
        '''

        if not os.path.exists(file):
            raise ValueError('The file ' + file + ' does not exist')

        # Check file is of correct format

        dl = pd.read_csv(file,skipinitialspace=True)

        # Should be 3x each season in header
        if len(list(dl.keys())) != 8:
            raise ValueError('There must be 8 columns in ' + file)

        dl.columns = list(map(string.lower,  dl.columns.tolist()))
        expectedHeadings = ['motorcycles', 'taxis', 'cars', 'buses', 'lgvs', 'rigids', 'artics']
        matches = list(set(list(dl.keys())[1:]).intersection(expectedHeadings))
        if len(matches) != len(list(dl.keys()))-1:
            raise ValueError('Top row of transport diurnal profiles must contain each of: ' + str(expectedHeadings))

        firstDataRow = 3
        # Expect certain keywords
        if 'transporttype' not in dl.columns.tolist():
            raise ValueError('First column of row 1 must be \'TransportType\' in ' + file)

        if dl['transporttype'][0].lower() != 'startdate':
            raise ValueError('First column of row 2 must be \'StartDate\' (of season) in ' + file)

        if dl['transporttype'][1].lower() != 'enddate':
            raise ValueError('First column of row 3 must be \'EndDate\' (of season) in ' + file)

        if 'timezone' != dl['transporttype'][2].lower():
            raise ValueError('First column of row 4 must be \'Timezone\' (of data for that season) in ' + file)

        # Try to extract the timezone from the file header
        try:
            tz = pytz.timezone(dl[list(dl.keys())[1]][2])
        except Exception:
            raise ValueError('Invalid timezone "' + dl[list(dl.keys())[1]][2] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Step through the list of transport types, adding the profiles
        # Asssumes first time point is the start of monday
        try:
            sd = pd.datetime.strptime(dl[dl.columns[1]][0], '%Y-%m-%d')
            ed = pd.datetime.strptime(dl[dl.columns[1]][1], '%Y-%m-%d')
        except Exception as e:
            raise Exception('Second column of Rows 2 and 3 of ' + file + ' must be dates in the format YYYY-mm-dd')

        sd = tz.localize(sd)
        ed = tz.localize(ed)

        for transportType in expectedHeadings:
            # Normalize each week series (over the whole week) so it's a weighting factor
            dl[transportType][firstDataRow:] = dl[transportType][firstDataRow:].astype('float')/dl[transportType][firstDataRow:].astype('float').mean()
            # Assign to the relevant element of this object
            subObj = getattr(self, transportType.lower())
            if subObj is None:
                raise Exception('Programming error: The wrong transport type has been referenced')
            subObj.addPeriod(startDate=sd, endDate=ed, dataSeries=dl[transportType][firstDataRow:])
