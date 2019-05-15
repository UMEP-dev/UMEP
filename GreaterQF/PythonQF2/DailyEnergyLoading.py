# Object that stores and retrieves coefficients that describe the total energy used (gas or electricity) each day
# This allows GreaterQF to disaggregate the annual total to a particular day
import os
from .string_func import   lower
try:
    import pandas as pd
except:
    pass

import pytz
from .DataManagement.DailyLoading import DailyLoading
from .DataManagement.LookupLogger import LookupLogger


class DailyEnergyLoading:
    '''
    Manage daily energy loadings for different energy types
    '''
    def __init__(self, city, useUKholidays, customHolidays=[], logger=LookupLogger()):
        self.logger = logger
        self.gas = DailyLoading(logger=self.logger)
        self.gas.useUKHolidays(useUKholidays)
        self.gas.setCountry(city)
        self.gas.specialHolidays(customHolidays)
        self.electricity = DailyLoading(logger=self.logger)
        self.electricity.useUKHolidays(useUKholidays)
        self.electricity.setCountry(city)
        self.electricity.specialHolidays(customHolidays)

    def addLoadings(self, file):
        ''' Process data from a file containing the electricity and gas daily loadings. Can be called multiple times for multiple years
        :param file: name of .csv file to load
        :param timezone: str() timezone name (same style as used by dateutils.relativedelta'''
        return self.dealWithInputFile(file)

    # Methods that follow the same pattern as getDomElec()
    def getElec(self, requestDateTime, timeBinDuration):
        ''' Retrieve industrial electricity value for the requested date and time.
        :param requestDateTime: End of time bin datetime() object for which to get data
        :param timeBinDuration: Duration of time bin (sec)'''
        return self.electricity.getValueForDateTime(requestDateTime, timeBinDuration)

    def getGas(self, requestDateTime, timeBinDuration):
        ''' Retrieve domestic gas value for the requested date and time.
        :param requestDateTime: End of time bin datetime() object for which to get data
        :param timeBinDuration: Duration of time bin (sec)'''
        return self.gas.getValueForDateTime(requestDateTime, timeBinDuration)

    def dealWithInputFile(self, file):
        ''' Generic method to add a profile for a particular energy type'''

        if not os.path.exists(file):
            raise ValueError('The file ' + file + ' does not exist')

        # Check file is of correct format
        dl = pd.read_csv(file,skipinitialspace=True)
        dl.columns = list(map(lower, dl.columns))
        # Expect certain keywords
        if 'fuel' not in list(dl.keys()):
            raise ValueError('First column of first row must be \'Fuel\' in ' + file)

        if 'gas' not in list(dl.keys()):
            raise ValueError('One of the column headers in ' + file + ' must be \'Gas\'')

        if 'elec' not in list(dl.keys()):
            raise ValueError('One of the column headers in ' + file + ' must be \'Elec\'')

        rowHeaders = list(map(lower, dl.fuel[0:3]))
        if 'startdate' != rowHeaders[0]:
            raise ValueError('First column of second row must be \'StartDate\' in ' + file)

        if 'enddate' != rowHeaders[1]:
            raise ValueError('First column of third row must be \'EndDate\' in ' + file)

        if 'timezone' != rowHeaders[2]:
            raise ValueError('First column of fourth row must be \'Timezone\' in ' + file)

        firstDataLine = 3
        # Try to extract the timezone from the file header
        try:
            tz = pytz.timezone(dl[list(dl.keys())[1]][2])

        except Exception:
            raise ValueError('Invalid timezone "' + dl[list(dl.keys())[1]][2] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Rest of rows 1 and 2 should be dates
        try:
            sd = pd.datetime.strptime(dl[list(dl.keys())[1]][0], '%Y-%m-%d')
            ed = pd.datetime.strptime(dl[list(dl.keys())[1]][1], '%Y-%m-%d')
        except Exception as e:
            raise Exception('The second and third rows of ' + file + ' must be dates in the format YYYY-mm-dd')

        sd = tz.localize(sd)
        ed = tz.localize(ed)
        # Normalize by annual mean

        # for col in dl.columns:
        #     dl[col][firstDataLine:] = dl[col][firstDataLine:].astype('float') / dl[col][firstDataLine:].astype('float').mean()
        dl_data = dl.loc[firstDataLine:, :].astype('float').copy()
        dl_data /= dl_data.mean()
        dl.loc[firstDataLine:, :] = dl_data.values
        self.gas.addPeriod(startDate=sd, endDate=ed, dataSeries=dl.gas[firstDataLine:])
        self.electricity.addPeriod(startDate=sd, endDate=ed, dataSeries=dl.elec[firstDataLine:])

