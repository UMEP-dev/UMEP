# Object that stores and retrieves temperature each day

import os
from string import lower
import pytz
from DataManagement.DailyLoading import DailyLoading
try:
    import pandas as pd
except:
    pass
from DataManagement.LookupLogger import LookupLogger

class DailyTemperature:
    '''
    Manage daily  temperature time series
    '''
    def __init__(self, studyAreaTimezone, weekendDays, use_uk_holidays, other_holidays=[], logger=LookupLogger()):
        '''
        Create dailyTemperature object
        :param studyAreaTimezone: timezone string for city being represented (e.g. Europe/London)
        :param weekendDays: List of integers specifying which day(s) of week are weekend (0=Mon, 6=Sun)
                            Empty list means weekends (inc. public holidays) and weekdays are equivalent
        :param use_uk_holidays: Boolean: Whether or not to use standard UK holidays
        :param other_holidays: List of specific dates to use as public holidays (in addition to UK if enabled)
        :param logger: Logger object
        '''
        self.logger = logger
        self.temperature = DailyLoading(logger=self.logger)
        self.temperature.setCountry(studyAreaTimezone)
        # If weekend days not specified, then weekends, weekdays and holidays have no distinction
        # In this case, un-set the holidays because they do not matter
        if len(weekendDays)==0:
            self.temperature.useUKHolidays(False)
            self.temperature.specialHolidays([])
            self.logger.addEvent('TemporalSampler', None, None, None, 'No weekend days set, so any public holidays will be ignored')
        else:
            self.temperature.useUKHolidays(use_uk_holidays)
            self.temperature.specialHolidays(other_holidays)
        self.weekendDays = weekendDays


    def addTemperatureData(self, file):
        ''' Process data from a file containing the electricity and gas daily loadings. Can be called multiple times for multiple years
        :param file: name of .csv file to load
        :param timezone: str() timezone name (same style as used by dateutils.relativedelta'''
        return self.dealWithInputFile(file)

    # Methods that follow the same pattern as getDomElec()
    def getTemp(self, requestDateTime, timeBinDuration):
        ''' Retrieve temperature value for the requested date and time.
        :param requestDateTime: End of time bin datetime() object for which to get data
        :param timeBinDuration: Duration of time bin (sec)
        :return tuple of (temperature, datetime retrieved)'''
        return self.temperature.getValueForDateTime(requestDateTime, timeBinDuration)

    def dealWithInputFile(self, file):
        ''' Generic method to add a profile for a particular energy type'''

        if not os.path.exists(file):
            raise ValueError('The file ' + file + ' does not exist')

        # Check file is of correct format
        dl = pd.read_csv(file,skipinitialspace=True)
        dl.columns = map(lower, dl.columns)
        # Expect certain keywords
        if 't_celsius' not in map(lower, dl.keys()):
            raise ValueError('One of the column headers in ' + file + ' must be \'T_celsius\'')

        rowHeaders = map(lower, dl.data[0:3])
        if 'startdate' != rowHeaders[0]:
            raise ValueError('First column of second row must be \'StartDate\' in ' + file)

        if 'enddate' != rowHeaders[1]:
            raise ValueError('First column of third row must be \'EndDate\' in ' + file)

        if 'timezone' != rowHeaders[2]:
            raise ValueError('First column of fourth row must be \'Timezone\' in ' + file)

        firstDataLine = 3
        # Try to extract the timezone from the file header
        try:
            tz = pytz.timezone(dl.t_celsius[2])

        except Exception:
            raise ValueError('Invalid timezone "' + dl.t_celsius[2] + '" specified in ' + file +
                             '. This should be of the form "UTC" or "Europe/London" as per python timezone documentation')

        # Rest of rows 1 and 2 should be dates
        try:
            sd = pd.datetime.strptime(dl.t_celsius[0], '%Y-%m-%d')
            ed = pd.datetime.strptime(dl.t_celsius[1], '%Y-%m-%d')
        except Exception, e:
            raise Exception('The second and third rows of ' + file +
                            ' must be dates in the format YYYY-mm-dd. Got:' + dl.t_celsius[0] + ' and ' + dl.t_celsius[1])

        sd = tz.localize(sd)
        ed = tz.localize(ed)

        for col in dl.columns:
            dl[col][firstDataLine:] = dl[col][firstDataLine:].astype('float')

        self.temperature.addPeriod(startDate=sd, endDate=ed, dataSeries=dl.t_celsius[firstDataLine:])

def test():
    # Add and retrieve test data
    dr = pd.date_range(pd.datetime.strptime('2015-01-01 00:00', '%Y-%m-%d %H:%M'), pd.datetime.strptime('2015-01-05 12:00', '%Y-%m-%d %H:%M'), tz="UTC", freq="H")

    a = DailyTemperature("Asia/Shanghai", use_uk_holidays=False, weekendDays= [], other_holidays=[])
    a.addTemperatureData('N:\QF_China\Beijing\dailyTemperature_2013_Beijing.csv')
    #a.addTemperatureData('N:\QF_Heraklion\LUCYConfig\dailyTemperature_2016_Heraklion.csv')
    for dt in dr:
        print str(dt) + str(a.getTemp(dt.to_datetime(), 3600))
