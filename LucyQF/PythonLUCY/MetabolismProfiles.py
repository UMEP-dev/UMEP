from __future__ import print_function
from builtins import str
from builtins import object
# Object that creates diurnal metabolism profiles

try:
    import numpy as np
    import pandas as pd
except:
    pass

import pytz
from datetime import timedelta

class MetabolismProfiles(object):
    def __init__(self, timezoneCountry, sleepLevel, workLevel):
        '''
        Instantiate
        :param timezone: str: time zone string (e.g. Europe/London) for region being modelled
        :param sleepLevel: float: Metabolic rate (Watts) of sleeping human (used as night-time value)
        :param workLevel: float: Metabolic rate (Watts) of working human (used as peak value)
        '''
        self.timezone = pytz.timezone(timezoneCountry)
        self.sleepLevel = float(sleepLevel)
        self.workLevel = float(workLevel)
        self.cached = None              # Cache the previous response because repetitive requests are likely
        self.sampleInterval = 60        # Resolution over which to calculate the mean metabolic rate when in between night and day

    def instantaneous(self, x, transitionRate, transitionSeconds, wakeStart, sleepStart):
        '''
        Return instantaneous metabolic rate at time x (seconds in local time)
        :param x: Seconds since start of day (local time)
        :param transitionRate: Rate of change in metabolic rate when someone is waking up/going to sleep (W/sec)
        :param transitionSeconds: Length of transition period for population (sec)
        :param wakeStart: Time of day when 50% of people have woken (sec singe midnight, local time)
        :param sleepStart: Time of day when 50% of people have gone to sleep (sec singe midnight, local time)
        :return: float: instantaneous metabolic rate of one person
        '''
        return self.sleepLevel + min(transitionSeconds, max(0, x-wakeStart))*transitionRate - min(transitionSeconds, max(0, x-sleepStart))*transitionRate

    def getWattPerson(self, timeBinEnd, timeBinDuration, medianAwake, medianAsleep, transitionDuration):
        '''
        Retrieve metabolic activity per person
        :param timeBinEnd: datetime: End of model time step (must be time zone aware)
        :param timeBinDuration: int: Duration of model time step (seconds) for averaging purposes
        :param medianAwake: float: Hour of day at which half of population has woken up
        :param medianAsleep: float: Hour of day at which half of population has gone to sleep
        :param transitionDuration: float: Time taken (hours) for population to go from awake<->asleep
        :return: float: Mean metabolic rate (Watts) given off by a human under these conditions
        '''
        # Get request date in local time, half way through the time step being requested (linear interpolation is used here)

        # Is this request identical to a previous one? If so, use that to save a little time.
        if self.cached is not None:
            if (timeBinEnd == self.cached['timeBinEnd']) \
                    and (medianAwake == self.cached['medianAwake']) \
                    and (medianAsleep == self.cached['medianAsleep']) \
                    and (transitionDuration == self.cached['transitionDuration']):
                return self.cached['result']

        if medianAwake > medianAsleep:
            raise ValueError('medianAwake must be earlier than medianAsleep. Got %f and %f (respectively)'%(medianAwake, medianAsleep))
        localTimeEnd = pd.Timestamp(timeBinEnd - timedelta(seconds = 1)).tz_convert(self.timezone) # 1 second from end of time bin
        localTimeStart = pd.Timestamp(timeBinEnd - timedelta(seconds = timeBinDuration)).tz_convert(self.timezone)
        timeStart_secs =  (3600*localTimeStart.hour + 60*localTimeStart.minute + localTimeStart.second)
        timeEnd_secs =  (3600*localTimeEnd.hour + 60*localTimeEnd.minute + localTimeEnd.second)
        transitionSeconds = transitionDuration*3600

        if timeEnd_secs < timeStart_secs:
            raise ValueError('Requested time step is not allowed to cross through midnight')
        # Everybody awake
        if (timeStart_secs >= (medianAwake*3600 + 0.5*transitionSeconds)) & (timeEnd_secs <= (medianAsleep*3600 - 0.5*transitionSeconds)):
            result = self.workLevel
        elif (timeStart_secs >= (medianAsleep*3600 + 0.5*transitionSeconds)) | (timeEnd_secs <= (medianAwake*3600 - 0.5*transitionSeconds)):
            # Everybody asleep
            result = self.sleepLevel
        else:
            # Somewhere in between. Integrate instantaneous rates over the chosen time bin
            wakeStart = 3600*medianAwake-0.5*transitionSeconds
            sleepStart = 3600*medianAsleep-0.5*transitionSeconds

            transitionRate = (self.workLevel - self.sleepLevel)/transitionSeconds
            times = np.arange(start=timeStart_secs, stop=timeEnd_secs, step=self.sampleInterval)
            metabs = [self.instantaneous(t, transitionRate, transitionSeconds, wakeStart, sleepStart) for t in times]
            result = np.mean(metabs)

        self.cached = {'timeBinEnd':timeBinEnd, 'medianAwake':medianAwake, 'medianAsleep':medianAsleep, 'transitionDuration':transitionDuration, 'result':result}
        return result

def testIt():
    a = MetabolismProfiles('Europe/Athens', 75, 175)
    times = pd.date_range(start='2015-01-01 01:00', freq='3600s', periods=96, tz='UTC')
    # fix_print_with_import
    print(a.getWattPerson(pd.Timestamp('2015-01-02 12:00:00+0000', offset='H'), 3600, 6.0, 22.0, 2.0))

    for t in times:
        # fix_print_with_import
        print(str(t) + ' ' +str(a.getWattPerson(t, 1800, 8, 20, 2)))

    # fix_print_with_import
    print(times[0])
    # fix_print_with_import
    print(times[0].to_datetime())
