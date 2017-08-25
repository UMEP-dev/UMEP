# Common functions for storing/retrieving data for a specific time used by both TemporalProfileSampler (does template weeks for diurnal cycles)
# and PeriodicProfileSampler (does continuous data)

import pytz
from datetime import datetime as dt
from datetime import timedelta
try:
    import pandas as pd
    import numpy as np
except:
    pass

from dateutil.relativedelta import *

def addPeriod(obj, startDate, endDate, weekSeries, timezone=pytz.timezone('Europe/London')):
    '''
    # For use by TemporalProfileSampler and PeriodicProfileSampler
    :param obj: the TemporalProfileSampler or PeriodicProfileSampler object involved
    :param startDate: datetime() of start of period (inclusive)
    :param endDate:  datetime() of end of period (inclusive)
    :param weekSeries: pandas.Series of data corresponding to period. Standard week in TemporalProfileResampler and a continuous period in PeriodicProfileResampler
    :param timezone: pytz representing time zone of data
    :return: None (updates the object fields)
    '''

    # Add weekly profile for a particular period defined by startDate and endDate (both datetime() inclusive)
    # weekSeries: Profile data. Continuous series data for a week, starting Monday and ending Sunday
    # timezone: pytz.timezone object defining the time zone represented by the data

    # Set object timezone to that of input data, provided it's consistent
    if obj.timeZone is not None:
        if obj.timeZone != timezone:
            raise ValueError('Timezone specified is not consistent with the one used earlier')

    obj.timeZone = timezone

    # Do simple validations
    (startYear, endYear) = obj.validateInputs(startDate, endDate, timezone, weekSeries)

    # Generally deal with the inputs straddling the year end
    years = np.arange(startYear, endYear + 1)
    startEndDates = {}
    for y in years:
        startEndDates[y] = [max(dt(y, 1, 1), startDate), min(dt(y, 12, 31), endDate)]

    # Go round each year (if necessary), adding entries
    for y in startEndDates.keys():
        # Within the year, set start date of period as DOY
        sd = startEndDates[y][0]  # start date
        ed = startEndDates[y][1]  # End date
        # Is daylight savings in effect?
        isDST = obj.timeZone.localize(sd).utcoffset().seconds != 0
        formattedSeries = obj.dealWithSeries(weekSeries)

        # Add straight to the dict if it's the first entry for the year
        if y not in obj.yearContents.keys():
            obj.yearContents[y] = pd.Series(index=[sd],
                                                 data=[{'isDST': isDST, 'data': formattedSeries.copy(deep=True)}])

        else:
            # Check if this period falls within a gap w.r.t. existing periods
            # Existing periods should end with a None, or a pd.Series.
            start_asof = obj.yearContents[y].index <= sd
            end_asof = obj.yearContents[y].index <= ed
            start_entry = None
            end_entry = None

            if np.sum(start_asof) > 0:
                start_entry = obj.yearContents[y].index[start_asof][-1]
            if np.sum(end_asof) > 0:
                end_entry = obj.yearContents[y].index[end_asof][-1]

            # If entries are different, we must be straddling an existing entry
            if start_entry != end_entry:
                raise ValueError('There is already data present between ' + sd.strftime('%Y-%m-%d')
                                 + ' and ' + ed.strftime('%Y-%m-%d'))
            series_entries = obj.yearContents[y].index[obj.yearContents[y].notnull()]
            if start_entry in series_entries:
                raise ValueError('There is a data series starting between between ' + sd.strftime('%Y-%m-%d')
                                 + ' and ' + ed.strftime('%Y-%m-%d'))

            # No matching entry, or a None, means we can use this gap in light of the previous checks
            if start_entry not in series_entries:
                obj.yearContents[y][start_entry] = {'isDST': isDST, 'data': formattedSeries.copy(deep=True)}

        # Ensure the dates are sorted
        obj.yearContents[y] = obj.yearContents[y].sort_index()

        # Cap off the period with a None, unless there is already a series starting there or it's december 31
        if not ((ed.month == 12) and (ed.day == 31)):
            if (ed + timedelta(1)) not in obj.yearContents[y].index:
                obj.yearContents[y][endDate + timedelta(1)] = None



