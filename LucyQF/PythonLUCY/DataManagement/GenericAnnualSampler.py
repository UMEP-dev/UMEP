# Class to handle temporal profiles for different year, season, day of week and time of day
# to make it easy to pull the relevant number out

try:
    import pandas as pd
    import numpy as np
except:
    pass
from dateutil.relativedelta import *
from temporalHelpers import *
from LookupLogger import LookupLogger
from datetime import datetime as dt
from datetime import date as dateType

class GenericAnnualSampler(object):
    def __init__(self, logger = LookupLogger()):
        self.logger = logger # Keep track of the requests and the resulting periods provided
        self.yearContents = None# Dictionary {year:pd.Series()} of years for which there is data
        self.ukBankHolidays = None # Use UK bank holidays? Set to False for non-UK countries and use special bank holidays
        self.extraHolidays = [] # List of datetime objects for special (non standard UK bank holidays).
        self.dataTimezone = None    # pytz.timezone : Time zone described by the data file
        self.countryTimezone = None # Time zone object representing country being modelled (so we know when every DST switch is)
        self.dstOccurs = None       # Boolean: Does this country have daylight savings? Used to validate input data
        self.weekendDays = []       # List of integers that state which days of the week are weekends (0=Mon, 6=Sun)

    def setWeekendDays(self, weekendDays):
        '''
        Defines which days of the week are the weekend.
        :param weekendDays: List of int. 0=Mon, 6=sun
        :return: Nothing
        '''
        self.weekendDays = weekendDays

    def setCountry(self, timezoneString):
        '''
        Defines the country being modelled so the model knows when Daylight saving can occur for any given year
        :param timezoneString: A string of timezone style (e.g. Europe/London)
        :return: None
        '''
        try:
            self.countryTimezone = pytz.timezone(timezoneString)
            # Does this country have DST? Model an arbitrary year
            dates = pd.date_range('2015-01-01', '2016-01-01', tz=timezoneString)
            self.dstOccurs = len(pd.unique([d.dst().seconds != 0 for d in dates])) > 1
        except Exception:
            raise ValueError('Invalid time zone string: %s'%(timezoneString,))

    def specialHolidays(self, holidayDates):
        '''Adds in public holidays
        :param holidayDates: List of datetime.date objects each of which represents a holiday'''
        self.extraHolidays = holidayDates
        def niceDate(dateobj): return dateobj.strftime('%Y-%m-%d')
        if holidayDates not in [None, []]:
            self.logger.addEvent('TemporalSampler', None, None, None, 'Special bank holidays added: ' + str(map(niceDate, holidayDates)))

    def useUKHolidays(self, state):
        '''Use UK bank holidays: Christmas, Boxing day, New Year's day, Easter Friday and Monday, May day, early and late summer
        Any other bank holidays should be added using self.specialHolidays()
        :param state: Boolean. True = Use UK holidays; False = Just use special holidays'''
        self.logger.addEvent('TemporalSampler', None, None, None, 'Use UK bank holidays = TRUE')
        self.ukBankHolidays = state

    def dealWithSeries(self, series):
        # This should be overridden to format and add a time series
        raise NotImplementedError('This method should be implemented in the child class')

    def validateInputs(self, startDate, endDate):
        ''' Validate inputs: These are standard validations of dates, so override to add other methods then call this superclass method
        :param startDate: datetime() of start of period
        :param endDate: datetime() end of period
        :return (startYear, endYear) tuple'''

        try:
            startYear = int(startDate.strftime('%Y'))
        except:
            raise ValueError('Start date must be a datetime() object')

        try:
            endYear = int(endDate.strftime('%Y'))
        except:
            raise ValueError('End date must be a datetime() object')

        if (endDate - startDate).days < 0:
            raise ValueError('Start date cannot be earlier than end date')

        if startDate.tzinfo is None:
            raise ValueError('Start date must have time zone attached')

        if endDate.tzinfo is None:
            raise ValueError('End date must have time zone attached')

        return (startYear, endYear)

    def availableYears(self):
        ''' Returns list of available years'''
        years = np.array([date.year for date in self.yearContents.index])
        years.sort()
        return list(np.unique(years))

    def entriesForYear(self, reqYear):
        ''' Return profile start dates for the specified year(s) regardless of whether they are Series or None'''

        try:
            reqYear = int(reqYear)
        except Exception:
            raise ValueError('Non-numeric year specified')

        reqYear = [int(reqYear)]
        years = np.array([date.year for date in self.yearContents.index])

        relevant = [y in reqYear for y in years]
        # If the earliest matching date is after January 1, see if there is a date starting in the previous year
        # carrying over into this one
        if not ((self.yearContents[relevant].index[0].day == 1) and (self.yearContents[relevant].index[0].month == 1)):
            firstThisYear = np.min(np.where(relevant))
            if (firstThisYear - 1) >= 0:
                relevant[firstThisYear-1] = True

        if np.sum(relevant) == 0:
            return None

        return self.yearContents[relevant].index

    # What options are there for the current DST status?
    def getDSTStates(self, year):
        # Return pandas series of start dates and DST states from self.yearContents[year]
        if year not in self.availableYears():
            raise ValueError('DST states requested for a year (' + str(year) + ') for which there is no data')

        result = {}
        for startDate in self.entriesForYear(year):
            if self.yearContents[startDate] is not None:
                result[startDate] = self.yearContents[startDate]['isDST']

        return pd.Series(result)

    def getDOW(self, date):
        ''' Return day of week of a particular date, after taking into account things like holidays'''
        if is_holiday(date, self.ukBankHolidays, self.extraHolidays):
            # If weekend days exist, then return the latest weekend day in the week for a holiday
            if len(self.weekendDays) > 0:
                return self.weekendDays[-1]
            else:
                return date.weekday()
        else:
            return date.weekday()

    def hasDOW(self, dow, year):
        '''
        Returns the pandas series of start dates and whether they contain the requested day of week from self.yearContents[year]
        :param: dow: int: day of week (0-6)
        :param: year: int: year to look at
        '''
        raise NotImplementedError('This must be implemented by the child class')


    def addPeriod(self, startDate, endDate, dataSeries):
        ''' Given a time series representing a period, perform validation and work the data into the object
           :param startDate: datetime() of start of period (inclusive)
           :param endDate:  datetime() of end of period (inclusive)
           :param dataSeries: pandas.Series of data corresponding to period. Standard week in TemporalProfileResampler and a continuous period in PeriodicProfileResampler
           :return: None (updates the object fields)
           '''

        # Check the time zone of these periods are the same as those added earlier (if any were added earlier).
        # Data is allowed to be in a different time zone to the country being represented, but must be divided based on
        # DST switch dates for the country represented.
        if self.dataTimezone is not None:
            if str(self.dataTimezone) != str(startDate.tzinfo):
                raise ValueError('Start date of ' + startDate.strftime('%Y-%m-%d') + ' has time zone of ' + str(startDate.tzinfo) +
                                 ' is inconsistent with ' + str(self.dataTimezone) + ', which was used earlier. All datasets must have the same time zone.')

        if self.dataTimezone is None:
            self.dataTimezone = pytz.timezone(str(startDate.tzinfo))

        # Is daylight savings in effect in the country represented?
        # Base this decision on what's happening at noon local time
        localizedStartTime = self.countryTimezone.localize(startDate.replace(tzinfo=None) + timedelta(seconds=12*3600))
        localizedEndTime = self.countryTimezone.localize(endDate.replace(tzinfo=None) + timedelta(seconds=12*3600))
        isDST = localizedStartTime.dst().total_seconds() != 0
        formattedSeries = self.dealWithSeries(dataSeries)

        # If the data is not the same time zone as the country being represented, ensure this data doesn't
        # sit across a DST switch

        if self.dstOccurs & (self.dataTimezone != self.countryTimezone):
            dates = pd.date_range(startDate, endDate, tz=self.dataTimezone)
            dstChange = len(pd.unique([d.dst().seconds != 0 for d in dates]))
            if dstChange:
                raise ValueError('Input data file for ' +
                                 startDate.strftime('%Y-%m-%d') + ' to ' + endDate.strftime('%Y-%m-%d') +
                                 ' is not in local time and crosses at least one daylight savings change. This is not allowed.')

        # Add straight to the dict if it's the first entry ever
        if self.yearContents is None:
            self.yearContents = pd.Series(index=[startDate.date()], data=[{'isDST': isDST, 'data': formattedSeries.copy(deep=True)}])
        else:
            # Check if this period falls within a gap w.r.t. existing periods
            # Existing periods should end with a None (the day after the end), or a pd.Series.
            idx = np.array(self.yearContents.index.tolist())
            # This should be doable using pd.asof but there was a strange compatibility issue with the QGIs pandas and time zones
            beforeStart = idx <= startDate.date()
            beforeEnd =  idx <= endDate.date()
            start_entry = None
            end_entry = None

            if np.sum(beforeStart)>0:
                start_entry = self.yearContents.index.tolist()[np.max(np.where(beforeStart))]
            if np.sum(beforeEnd)>0:
                end_entry = self.yearContents.index.tolist()[np.max(np.where(beforeEnd))]

            # If entries are different, we must be straddling an existing entry

            if start_entry != end_entry:
                raise ValueError('There is already data present between ' + startDate.strftime('%Y-%m-%d')
                                 + ' and ' + endDate.strftime('%Y-%m-%d'))

            series_entries = self.yearContents.index[self.yearContents.notnull()]

            if np.sum((series_entries <= endDate.date()) & (series_entries >= startDate.date())) > 0:
                raise ValueError('There is already data series starting between between ' + startDate.strftime('%Y-%m-%d')
                                 + ' and ' + endDate.strftime('%Y-%m-%d'))

            self.yearContents[startDate.date()] = {'isDST': isDST, 'data': formattedSeries.copy(deep=True)}

            # Ensure the dates are sorted
            self.yearContents = self.yearContents.sort_index()

        # Cap off the period with a None, unless there is already a series starting there, or it's the end of the year
        if (endDate.date() + timedelta(days=1)) not in self.yearContents.index:

            self.yearContents[endDate.date() + timedelta(days=1)] = None

    def extractCorrectEntry(self, df, endOfTimestep, timestepDuration):
        # Should be overridden to extract the relevant bits of a series once the entry has been identified
        raise NotImplementedError('This method must be implemented by the child class')

    def findSuitableYear(self, requestDate):
        ''' Given a dict of {year: pd.Series( pd.series, None, Pd.Series),
            Picks a suitable year and pd.Series within that year to use relative the requested date and time.
            Used with TemporalProfileSampler and PeriodicProfileSampler
            :param requestDateTime: datetime object containing the day to look up
            :return the suitable year (int) or False if nothing is suited'''

        ## Line of interrogation...
        # Is the requested year present in the data? If so, great.
        # If not, then go to a year that does contain the requested data
        # Does the selected year have a period containing the requested date? If not, go back further
        # Assumes NO GAPS between years of data

        # Convert from request timezone to data's timezone
        requestDate = pd.Timestamp(requestDate).tz_convert(self.dataTimezone)
        sortedYears = np.array(self.availableYears())
        reqYear = requestDate.year
        thisYear = reqYear in sortedYears

        if not thisYear:
            # No data at all this year: Go to the first/last year for which there is data.
            if reqYear < sortedYears[0]:
                firstSuitableYear = sortedYears[0]
            else:
                firstSuitableYear = sortedYears[-1]

            # Revise the request by looking for the same day of week and time of month in a different year.
            chosenYear = firstSuitableYear
        else:
            chosenYear = reqYear

        # Now there is a year requested for which there is data, check is there data during the requested time of year
        periodStartStops = self.entriesForYear(int(chosenYear))
        modifiedDate = requestDate + relativedelta(weekday=requestDate.weekday(), year=chosenYear)
        mostRecent = periodStartStops <= modifiedDate.date()
        if np.sum(mostRecent) > 0:
            # Was the most recent relevant entry a None (after end of available data) or something else (good)?
            goodEntry = self.yearContents[periodStartStops[mostRecent][-1]] is not None
            if goodEntry:
                return periodStartStops[mostRecent][0].year # Return year containing suitable start date

        # If we get this far, it was not a good entry OR we don't have data for the required year.
        # Search strategy:
        # Go to year before if at end of available data
        # Go to year after if at start of available data.
        # No other cases supported: Only the first and final years are allowed to be partial. years in between must be complete.

        # If this is the only year for which we have data, then there's a problem
        if len(sortedYears) < 2:
            return None

        if chosenYear == sortedYears[0]:
            chosenYear = sortedYears[1]
        elif chosenYear == sortedYears[-1]:
            chosenYear = sortedYears[-2]
        else:
            # We have no suitable data and are not at the edge of the available years. This shouldn't occur.
            return None

        revisedRequest = requestDate + relativedelta(weekday=requestDate.weekday(), year=chosenYear)
        thisYear = self.findSuitableYear(revisedRequest)

        return thisYear

    def getValueForDateTime(self, timeBinEnd, timeBinDuration):
        '''
        Retrieve the most appropriate value for the requested datetime object
        :param timeBinEnd: End of the time period in question (datetime())
        :param timeBinDuration: Duration of time bin (seconds)
        :param weekendDays: list of int specifying which day(s) of week are the weekend. 0=Mon, 6=Sun.
                If empty list, no distinction is made between weekdays and weekends (and public holidays)
        :return: tuple: (relevantValue Float()  , startOfOriginalPeriod)
        '''
        if self.countryTimezone is None:
            raise Exception('Country has not been set so cannot look up a value for date/time')

        # If there are any gaps in the time series, then refuse to look anything up
        gaps = self.gaps_present()

        if gaps != False:
            raise Exception('There are currently gaps present in years ' + str(gaps))

        if self.ukBankHolidays is None:
            raise Exception('User must set whether to use UK bank holidays (True or False)')

        if timeBinEnd.tzinfo is None:
            raise ValueError('Requested time bin must have time zone attached')

        # if timeBinEnd minus timeBinDuration goes over a date boundary, reject the request, unless timeBinEnd is bang on midnight
        lookupTimeBin = timeBinEnd - timedelta(seconds=timeBinDuration-1) # This is the start of the requested time bin

        if (timeBinEnd - timedelta(seconds=1)).day != lookupTimeBin.day:
            raise ValueError('Requested time bin crosses a date boundary. This is not allowed')

        # Get the lookup time bin into the same time zone as the data in the object
        localLookupTimeBin = pd.Timestamp(lookupTimeBin).tz_convert(self.dataTimezone)

        # Get the right year and season from the empirical data
        yearToUse = self.findSuitableYear(lookupTimeBin) # findSuitableYear is timezone aware

        if yearToUse is None:
            raise ValueError('No data available at this time of year for time bin ending ' + str(timeBinEnd))

        # Establish if the date needed is a bank holiday and adjust day of week accordingly
        # Get day of week needed in local time (start of lookup time bin)
        if is_holiday(localLookupTimeBin, self.ukBankHolidays, self.extraHolidays):
            # Is requested date a holiday? Revise day of week to latest weekend day in week (if weekend days are provided.)
            if len(self.weekendDays) > 0:
                dowNeeded = int(self.weekendDays[-1]) # Take the latest weekend day in the list as the day (e.g. sunday in UK)
            else:
                dowNeeded = localLookupTimeBin.weekday() # If no weekend days provided, use existing day of week
        else:
            dowNeeded = localLookupTimeBin.weekday()

        localLookupTimeBin = localLookupTimeBin + relativedelta(weekday=dowNeeded, year=yearToUse)
        # Edge case: Sometimes December 31 XXXX + relativedelta(year=YYYY) can take it back to January 1 YYYY+1
        # Subtract 51 weeks if this happens (keeps it at the same time of year)
        if localLookupTimeBin.year != yearToUse:
            localLookupTimeBin = localLookupTimeBin + relativedelta(weekday=dowNeeded, weeks=-51)

        # Determine if DST is in effect for the chosen modelled date (at noon)
        isDst = self.countryTimezone.localize(lookupTimeBin.replace(tzinfo=None, hour=12, minute=0)).dst().total_seconds() != 0
        # Get keys that have same DST status as request date. Assume no offset means DST while offset means not DST
        # Decision about DST for the request time is based on the requested date at noon
        dsts = self.getDSTStates(localLookupTimeBin.year)

        # Get those entries that contain the required day of week (just in case incomplete weeks present)
        hasRelevantDOW = self.hasDOW(year=yearToUse, dow=dowNeeded)
        dstDates = set(dsts.index[dsts == isDst]).intersection(hasRelevantDOW.index[hasRelevantDOW])

        if (len(dstDates) == 0) & self.dstOccurs & (self.countryTimezone != self.dataTimezone):
            raise Exception('No data for daylight savings = ' + str(isDst) +
                            ' during year ' + str(timeBinEnd.year) +
                            ' (input data was not specified in local time so DST is important)')

        # Get a suitable day's values based on comparable DSTs
        if (not self.dstOccurs) or (self.countryTimezone == self.dataTimezone):
            # Case 1: If all data is in local time, or DST does not occur in the country represented,
            # then the profile dates don't need to line up with local DST dates. Use the most recent (for the time of year)
            minDiff = self.yearContents[hasRelevantDOW.index[hasRelevantDOW]].index.asof(localLookupTimeBin.date())
        else:
            # Case 2: Data is not in local time, so find a compatible DST state
            # Use the most recent period of the same DST type
            minDiff = dsts[dstDates].index.asof(localLookupTimeBin.date())

        if type(minDiff) is not dateType:
            minDiff = minDiff.date()

        df = self.yearContents[minDiff]['data']

        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        (extracted, timestamp, dayofweek) = self.extractCorrectEntry(df, timeBinEnd, timeBinDuration, dowNeeded)

        timeLookedUp = dt(year=minDiff.year, month=minDiff.month, day=minDiff.day, hour=timestamp.hour, minute=timestamp.minute, tzinfo=timestamp.tzinfo)
        self.logger.addEvent('LookupTemporal', timeBinEnd, minDiff, None,
                              'Got ' + str(timeBinDuration) + ' s period starting ' +
                              timeLookedUp.strftime('%H:%M %Z') +
                              '(' + days[dayofweek] + ')'
                              ' for step ending ' +
                              timeBinEnd.strftime('%Y-%m-%d %H:%M:%S %Z') +
                              ' (' + days[timeBinEnd.weekday()] + ')')
        return (extracted, minDiff,)

    def gaps_present(self):
        ''' Looks for gaps between the available periods. Incomplete years at the start and end do not count
        Returns False if no gaps'''

        # First year should not contain any Nones. A None represents a terminated period with a gap after it
        # Only one None is allowed and it must be at the end

        endings = self.yearContents.index[self.yearContents.isnull()]
        if (len(endings) > 1) or (endings[0] != self.yearContents.index[-1]):
            return list(endings) # There are gaps and here they are
        else:
            return False # no gaps

