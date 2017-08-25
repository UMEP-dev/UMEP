try:
    import numpy as np
except:
    pass
from GenericAnnualSampler import GenericAnnualSampler
from temporalHelpers import *

class DailyLoading(GenericAnnualSampler):
    # Object to store and retrieve annualised pandas time series
    # Retrieves data for the next best year if the requested date isn't available
    # Data must be daily resolution

    def addPeriod(self, startDate, endDate, dataSeries):

        # Add daily values profile for a particular period defined by startDate and endDate (both datetime() inclusive)
        # dataSeries: Profile data. Continuous series data for a week, starting Monday and ending Sunday

        if startDate.tzinfo is None:
            raise ValueError('Start date must have timezone attached')

        if endDate.tzinfo is None:
            raise ValueError('End date must have timezone attached')
        expectedLength = ((endDate.date()-startDate.date()).days+1) # +1 because the start and end date in the file are inclusive

        if expectedLength != len(dataSeries):
            raise ValueError('Daily dataset must have exactly ' + str(expectedLength) + ' entries')

        # Add temporal index to series if it passed the validation tests.
        dataSeries.index = pd.date_range(startDate, periods=len(dataSeries))

        # Each day gets its own regime
        # DST regimes from range available
        regimeStarts = dataSeries.index

        #regimeEnds = list(regimeStarts[1:].copy(deep=True))
        #regimeStarts = list(regimeStarts)
        #finalEntry = regimeEnds[-1]+timedelta(hours=24)
        #regimeEnds.append(finalEntry)

        for st in np.arange(0, len(regimeStarts), 1):
            # Do simple validations
            self.validateInputs(regimeStarts[st], regimeStarts[st], dataSeries[regimeStarts[st]:regimeStarts[st]])
            super(DailyLoading, self).addPeriod(regimeStarts[st], regimeStarts[st], dataSeries[regimeStarts[st]:regimeStarts[st]])

    def dealWithSeries(self, series):
        # Converts the time series into a more structured data frame to allow general day of week lookups
        # Assumes each day of data is covering that day. Assigns a datestamp for the whole day
        # Nothing to actually do here since validateInputs does the heavy lifting
        return series

    # File into the relevant year, splitting across years if necessary
    def validateInputs(self, startDate, endDate, series):
        ''' Validate the inputs, in conjunction with core date validation from superclass'''

        if type(series) is not type(pd.Series()):
            raise ValueError('Input series must be a pandas.Series()')

        # Series length must match the specified period, even if some of it's NAs
        numDays = (endDate - startDate).days + 1 # Start and end dates are inclusive
        if len(series) != numDays:
            raise ValueError('Length of daily time series should be integer multiple of days in period. Need ' + str(numDays) + ', got ' + str(len(series)))
        newSeries = pd.Series(data=np.array(series.tolist()).astype('float'), index=[pd.date_range(start=startDate, end=endDate)])

        startAndEndYear = super(DailyLoading, self).validateInputs(startDate, endDate)
        return startAndEndYear

    def extractCorrectEntry(self, df, endOfTimestep, timestepDuration, wd):
        '''
        Get the data point for the relevant day from the data frame <<df>> provided
        :param df: pandas dataframe containing the relevant day of data
        :param endOfTimestep: datetime() object with the date and end time of the time step
        :param timestepDuration: the duration of the time step ins econds
        :param wd: int: Weekday needed (0-6), 6 if sunday or holiday
        :return: A float() of the value representing that period (averaged or sub-sampled depending on timestepDuration)
        '''

        # Within the series, find the most recent occurrence of this day of week

        # Is the section of data provided to us correct? It should be, given earlier stages, but still...
        dows_available = map(self.getDOW, [d.to_pydatetime() for d in df.index])
        # Return the value and the corresponding date from which it came
        dateNeeded = (endOfTimestep - timedelta(seconds=timestepDuration-1))
        use = np.array(dows_available) == wd
        mostRecent = df[use].index.asof(dateNeeded)
        # If this pushes us off the left hand edge, take the first chronological matching weekday
        if mostRecent is np.nan:
            mostRecent =  df[use].index[0]
        return (df[mostRecent], mostRecent, wd)

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
                # Each entry must be a pandas timeseries, in which case the day of week is converted from the timestamp
                dates = [d.to_pydatetime() for d in self.yearContents[startDate]['data'].index]
                result[startDate] = (dow in list(np.unique(map(self.getDOW, dates))))

        return pd.Series(result)