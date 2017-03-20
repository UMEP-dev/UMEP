# Object that stores and retrieves energy use profiles for different seasons and times of day for GreaterQF
# An energy profile is a week-long template of relative energy use that changes only with season

import os
from string import lower
try:
    import numpy as np
    import pandas as pd
except:
    pass

import pytz
from DataManagement.LookupLogger import LookupLogger
from DataManagement.TemporalProfileSampler import TemporalProfileSampler

class EnergyProfiles:
    def __init__(self, city, use_uk_holidays, customHoldays = [], logger=LookupLogger()):
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
        self.domesticElectricity.specialHolidays(customHoldays)
        self.domesticElectricity.setWeekendDays([5,6]) # Future version: Support other weekdays

        self.economy7 = TemporalProfileSampler(logger=self.logger)
        self.economy7.useUKHolidays(use_uk_holidays)
        self.economy7.setCountry(city)
        self.economy7.specialHolidays(customHoldays)
        self.economy7.setWeekendDays([5,6])

        self.domesticGas = TemporalProfileSampler(logger=self.logger)
        self.domesticGas.useUKHolidays(use_uk_holidays)
        self.domesticGas.setCountry(city)
        self.domesticGas.specialHolidays(customHoldays)
        self.domesticGas.setWeekendDays([5,6])

        self.industrialElectricity = TemporalProfileSampler(logger=self.logger)
        self.industrialElectricity.useUKHolidays(use_uk_holidays)
        self.industrialElectricity.setCountry(city)
        self.industrialElectricity.specialHolidays(customHoldays)
        self.industrialElectricity.setWeekendDays([5,6])

        self.industrialGas = TemporalProfileSampler(logger=self.logger)
        self.industrialGas.useUKHolidays(use_uk_holidays)
        self.industrialGas.setCountry(city)
        self.industrialGas.specialHolidays(customHoldays)
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
        if (len(dl.keys())-1)%3 != 0:
            raise ValueError('There must be 3 columns for each named season in ' + file)

        # Expect certain keywords
        rowHeadings = map(lower, dl[0][0:6])
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
            tz = pytz.timezone(dl[dl.keys()[1]][5])
        except Exception:
            raise ValueError('Invalid timezone "' + dl[dl.keys()[1]][5] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Go through in triplets gathering up data for a template week
        for seasonStart in np.arange(1, dl.shape[1], 3):
            try:
                sd = pd.datetime.strptime(dl[seasonStart][3], '%Y-%m-%d')
                ed = pd.datetime.strptime(dl[seasonStart][4], '%Y-%m-%d')
            except Exception, e:
                raise Exception('Rows 4 and 5 of ' + file + ' must be dates in the format YYYY-mm-dd')

            sd = tz.localize(sd)
            ed = tz.localize(ed)
            # Check data doesn't cross DST changes
            temp = [thisDate for thisDate in pd.date_range(sd.replace(hour=12), ed.replace(hour=12))]
            a = temp[0]

            tzsecs = np.array([thisDate.dst().total_seconds() for thisDate in pd.date_range(sd.replace(hour=12), ed.replace(hour=12))])

            # TODO: Reinstate this when the input data is UTC and the code knows which country is represented
            #if len(np.unique(tzsecs)) > 1:
            #    raise ValueError('The period ' + sd.strftime('%Y-%m-%d') +
            #                     ' to ' + ed.strftime('%Y-%m-%d')
            #                     + ' crosses one or more daylight savings changes. Separate periods must be specified before and after each change.')

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



if __name__ == '__main__':
    # Add and retrieve test data
    a = EnergyProfiles('Europe/London', use_uk_holidays=True)
    a.addDomElec(  'N:\\QF_London\\GreaterQF_input\\London\\profiles\\BuildingLoadings_DomUnre.csv')
    a.addDomGas(   'N:\\QF_London\\GreaterQF_input\\London\\profiles\\BuildingLoadings_DomUnre.csv')
    a.addEconomy7( 'N:\\QF_London\\GreaterQF_input\\London\\profiles\\BuildingLoadings_EC7.csv')
    a.addIndElec(  'N:\\QF_London\\GreaterQF_input\\London\\profiles\\BuildingLoadings_Industrial.csv')
    a.addIndGas(   'N:\\QF_London\\GreaterQF_input\\London\\profiles\\BuildingLoadings_Industrial.csv')
    timeBins_mar_apr = pd.date_range(pd.datetime.strptime('2015-03-15 00:30', '%Y-%m-%d %H:%M'),  end=pd.datetime.strptime('2015-04-15 00:30', '%Y-%m-%d %H:%M'), tz='UTC',
                             freq='30min')
    for dp in timeBins_mar_apr:
        #print dp
        time = dp.to_datetime()
        indGas = a.getDomElec(time, 1800)
        print dp.strftime('%Y-%m-%d %H:%M,') + str(indGas[0])

    print a.logger.getEvents()

