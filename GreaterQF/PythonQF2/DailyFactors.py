from __future__ import print_function
from __future__ import absolute_import
from builtins import object
# Stores and retrieves daily factors for buildings
from datetime import datetime as dt
from .DataManagement.temporalHelpers import holidaysForYear

class DailyFact(object):
    def __init__(self, use_uk_holidays, custom_holidays=[]):
        '''
        :param use_uk_holidays:  Boolean: Generate and use standard UK holidays
        :param custom_holidays:  List of non-standard or non-UK holidays to use (in addition to UK holidays if use_uk_holidays=True)
        '''
        self.use_uk_holidays = use_uk_holidays
        self.custom_holidays = custom_holidays

    def getFact(self, dateObj):
        ''' Return daily building factor for the requested date'''

        holidays = holidaysForYear(dateObj.year)
        if dateObj.date() in holidays:
            dayofweek = 6  # change this if using isoweekday
        else:
            dayofweek = dateObj.weekday()

        # TODO: Get these numbers into a configuration file
        if dayofweek <= 4:
            dailyfact = 0.792
        elif dayofweek == 5:
            dailyfact = 1.108
        elif dayofweek == 6:
            dailyfact = 1.78

        return dailyfact

def testIt():
    import pandas as pd
    a = DailyFact(True)
    date = pd.date_range(pd.datetime.strptime('2015-01-01 00:00', '%Y-%m-%d %H:%M'), tz='Europe/London', periods=5)[1]
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-01', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-02', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-03', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-04', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-05', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-06', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-07', '%Y-%m-%d')))
    # fix_print_with_import
    print(a.getFact(dt.strptime('2015-01-08', '%Y-%m-%d')))
