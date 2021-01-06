from builtins import str
# Helper methods for temporal calculations and calendar events

from datetime import datetime as dt
from datetime import timedelta
from datetime import date as dtd
import pytz
try:
    import pandas as pd
except:
    pass

def calc_easter(year):
    '''Returns Easter Sunday as a date object. Confirmed working by Andy"
    Credit: http: // code.activestate.com / recipes / 576517 - calculate - easter - western - given - a - year '''
    a = year % 19
    b = year // 100
    c = year % 100
    d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
    e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
    f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
    month = f // 31
    day = f % 31 + 1
    return dt(year, month, day)

def is_holiday(timeStepEnd, use_UK, extraHolidays):
    ''' Determines if the given date falls on a bank holiday
     Considers UK holidays if use_UK = True
     extraHolidays: List of datetime objects containing any extra holidays.
     UK holidays generated automatically unless unexpected'''

    # if type(timeStepEnd) in [type(dt(2015, 1, 1)), pd.datetime(2015, 1, 1), pd.tslib.Timestamp]:
    if type(timeStepEnd) in [type(dt(2015, 1, 1)), pd.datetime(2015, 1, 1), pd.Timestamp]:
        reqDate = timeStepEnd.date()
        reqDate = timeStepEnd.date()
    elif type(timeStepEnd) is type(dtd(2015, 1, 1)):
        reqDate = timeStepEnd
    else:
        raise ValueError('Input date is invalid type: ' + str(type(timeStepEnd)) + '. Must be datetime() or datetime.date()')

    if use_UK:
        if reqDate in holidaysForYear(timeStepEnd.year):
            return True

    if reqDate in extraHolidays:
        return True

    return False

def makeUTC(x): return pytz.timezone('UTC').localize(x)

def holidaysForYear(year):
    # Generate public holidays (UK) for a given year
    # Christmas day/boxing day falling on weekend isn't included (assumed standard weekend)
    holidays = []
    # New year:
    holidays.append(dt(year, 0o1, 0o1))
    # If 2 or 3 january is a monday, this is the bank holiday
    jan2 = dt(year, 0o1, 0o2)
    jan3 = dt(year, 0o1, 0o3)
    if jan2.weekday() == 0:
        holidays.append(jan2)
    if jan3.weekday() == 0:
        holidays.append(jan3)

    # Get easter monday and friday bank holidays from lookup function
    easter_sun = calc_easter(year)
    easter_mon = easter_sun + timedelta(1)
    good_fri = easter_sun - timedelta(2)
    holidays.extend([good_fri, easter_mon])

    # Early and late may
    may1 = dt(year, 0o5, 0o1)
    may1 = may1 if may1.weekday() is 0 else may1 + timedelta(7 - may1.weekday())
    holidays.append(may1)
    holidays.append(dt(year, 5, 31) - timedelta(dt(year, 5, 31).weekday()))
    # Final monday in August
    holidays.append(dt(year, 8, 31) - timedelta(dt(year, 8, 31).weekday()))
    # Christmas bank holidays. Only add if on a week, because weekends are weekends anyway
    dec25 = dt(year, 12, 25)
    dec26 = dt(year, 12, 26)
    if dec25.weekday() < 6:  # only include if not Sunday
        holidays.append(dec25)
    if dec26.weekday() < 6:
        holidays.append(dec26)

    # If december 28 is a monday or tuesday, it must be displaced bank holiday because xmas day and/or boxing day fell on weekend
    dec27 = dt(year, 12, 27)
    dec28 = dt(year, 12, 28)
    if dec28.weekday() < 2:
        holidays.append(dec28)
    if dec27.weekday() < 2:
        holidays.append(dec27)
    # Ensure datetime.date:
    holList = [h.date() for h in holidays]
    return holList