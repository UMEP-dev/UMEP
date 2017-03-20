# Class to handle temporal profiles for different year, season, day of week and time of day
# to make it easy to pull the relevant number out
try:
    import numpy as np
except:
    pass
from temporalHelpers import *
from GenericAnnualSampler import GenericAnnualSampler

class TemporalProfileSampler(GenericAnnualSampler):

    def dealWithSeries(self, series):
        # Converts the time series into a more structured data frame to allow general day of week lookups
        # The time zone inside this array is the same as the input data: no shifts occur.
        # Returns data frame that bins according to START OF EACH PERIOD

        # This has already been validated for length, so divide it into 7 days of data. Final point is midnight on Sunday evening
        binsPerDay = len(series)/7 # Integers
        if type(series) is not type(pd.Series()):
            raise ValueError('Input series must be a pandas.Series()')

        dayCol = np.repeat(np.arange(0,7,1), binsPerDay)  # Label each row with the day of the week (same convention as datetime)
        # Each bin of profile data is demarcated by the end of the period.
        # But it's easier from a programming poV to use the start of each period.
        secCol = np.tile(np.linspace(0, 24., binsPerDay, endpoint=False)*3600, 7)
        # Ensure data is float before going in
        df = pd.concat([pd.Series(np.array(dayCol).astype('int')), pd.TimeSeries(np.array(secCol).astype('int')), pd.Series(np.array(series.tolist()).astype('float'))], axis=1)
        df.columns = ['dayofweek', 'seconds', 'data']
        return df

    # File into the relevant year, splitting across years if necessary
    def validateInputs(self, startDate, endDate, weekSeries):
        ''' Validate the inputs, in conjunction with core date validation from superclass'''

        if len(weekSeries) % 7 > 0:
            raise ValueError('Length of data series must be divisible by 7 (data for each day of week)')

        startAndEndYear = super(TemporalProfileSampler, self).validateInputs(startDate, endDate)
        return startAndEndYear

    def extractCorrectEntry(self, df, endOfTimestep, timestepDuration, dowNeeded):
        '''
        Get the data point for the relevant time of day from the data frame <<df>> provided
        :param df: pandas dataframe containing the relevant day of data
        :param endOfTimestep: datetime() object with the date and end time of the time step
        :param timestepDuration: the duration of the time step ins econds
        :param dowNeeded: int: day of week requested, including any corrections based on bank holidays
        :return: A float() of the value representing that period (averaged or sub-sampled depending on timestepDuration)
        '''

        # Set the request datetime into the same time zone as the data in the object
        endOfTimestep = pd.Timestamp(endOfTimestep).tz_convert(self.dataTimezone).to_datetime()
        startOfTimestep = endOfTimestep - timedelta(seconds=timestepDuration)
        almostEndOfTimestep = endOfTimestep - timedelta(microseconds=1)  # Subtract 1 microsecond to remove right-binning issues on date boundaries

        # Key the whole dataframe to the relevant time of day on January 1 2000. Hacky and would ideally be a
        # timeDeltaIndex but earlier pandas don't allow it
        relevant = df['dayofweek'] == dowNeeded

        ts = df[:][relevant]
        ts.index = [dt(2000,1,1) + timedelta(seconds=int(sec)) for sec in ts['seconds']]
        ts = pd.Series(data=ts.data, index=ts.index)
        # We want to get data from the start of the time period of interest and include all but the final microsecond
        startTime = dt(2000,1,1) + timedelta(seconds = int(startOfTimestep.second + startOfTimestep.hour*3600 + startOfTimestep.minute * 60))
        endTime = dt(2000,1,1) + timedelta(seconds = int(almostEndOfTimestep.second + almostEndOfTimestep.hour*3600 + almostEndOfTimestep.minute * 60))

        iStart = ts.index.asof(startTime)
        iEnd = ts.index.asof(endTime)

        if iStart == iEnd:
            # Requested period falls within a time bin
            return (ts.asof(iStart), iEnd, dowNeeded)
        else:
            # Requested period straddles two or more time bins
            # Resample the day's data to freq=timeBinDuration/100 and take a mean
            # to introduce first approximation of weightings
            resampleFreq = str(int(float(timestepDuration)/100.0))+'S'
            rs = ts.resample(resampleFreq, fill_method='pad')
            return (rs[rs.index.asof(startTime):rs.index.asof(endTime)].mean(), iEnd, dowNeeded)

    def addPeriod(self, startDate, endDate, dataSeries):

        # Add weekly profile for a particular period defined by startDate and endDate (both datetime() inclusive)
        # weekSeries: Profile data. Continuous series data for a week, starting Monday and ending Sunday
        # timezone: pytz.timezone object defining the time zone represented by the data

        # Do simple validations and add
        self.validateInputs(startDate, endDate, dataSeries)
        super(TemporalProfileSampler, self).addPeriod(startDate, endDate, dataSeries)

    def hasDOW(self, dow, year):
        '''
        Returns the pandas series of start dates and whether they contain the requested day of week from self.yearContents[year]
        :param: dow: int: day of week (0-6)
        :param: year: int: year to look at
        '''

        result = {}
        for startDate in self.entriesForYear(year):
            if self.yearContents[startDate] is not None:
                # Get days of week present in each startDate's entry.
                # Each startdate's entry must be a pd.DataFrame with dayofweek column (just extract this)
                if 'dayofweek' in self.yearContents[startDate]['data'].columns:
                    result[startDate] = dow in self.yearContents[startDate]['data']['dayofweek']
                else:
                    raise Exception('Data frame must contain dayofweek column')

        return pd.Series(result)