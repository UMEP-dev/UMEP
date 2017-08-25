# Funtion:
# Download WATCH/WFDEI data for specified date range and variable.
# Author:
# Lingbo Xue, L.Xue@student.reading.ac.uk
# Ting Sun, ting.sun@reading.ac.uk
# History:
# LX, 13 Jun 2016: initial version
# TS, 14 Jun 2016 : path parsing improved.
# TS, 15 Jun 2016: date/time bugs fixed and logic improved.

from ftplib import FTP
import os
import sys
import urllib
import numpy as np
from datetime import date,datetime
from dateutil.relativedelta import relativedelta

def single_file_download(path, key_word, ftp):
    path = os.path.join(path, key_word)  # safely join pathnames
    path = os.path.expanduser(path)  # expand Unix
    if os.path.lexists(path):
        print("File exist! Try again...")
    else:
        f = open(path, 'wb')
        print "%s downloading..." % key_word
        ftp.retrbinary('RETR %s' % key_word, f.write)
        print "%s download succeed!" % key_word


def time_period_files_download(key_word, path, ftp):
    ftp.cwd(key_word)
    list = ftp.nlst()

    path = os.path.expanduser(path)  # expand Unix
    os.chdir(path)
    path = os.path.join(path, key_word)  # safely join pathnames
    if not os.path.lexists(path):
        os.mkdir(key_word)

    time1, time2 = 190101, 200112
    time_range = time_period_test(time1, time2)

    if key_word == "Rainf_WFD" or key_word == "Rainf_daily_WFD" or key_word == "Snowf_WFD" or key_word == "Snowf_daily_WFD":
        name_base = key_word + '_CRU'
    else:
        name_base = key_word

    # bug here: such range cannot go over a year: 190113 will be generated.
    for i in time_range:
        file_name = name_base + '_' + str(i) + '.nc'
        # path_temp = path + file_name
        path_temp = os.path.join(path, file_name)
        if os.path.lexists(path_temp):
            print "%s exists!" % file_name
        else:
            f = open(path_temp, 'wb')
            print "%s downloading..." % file_name
            ftp.retrbinary('RETR %s' % file_name, f.write)
            print "%s download succeed!" % file_name


def time_period_test(firstAvailableTime, finalAvailableTime, start_time, end_time):
    # Take first and final available time (strings %Y%m) and user-supplied
    # requested start and end times (string %Y%m), check for validity and build a list of months
    firstAvailableTime = datetime.strptime(str(firstAvailableTime), "%Y%m")
    finalAvailableTime = datetime.strptime(str(finalAvailableTime), "%Y%m")
    print("The time period is from %s to %s" %
          (firstAvailableTime.strftime("%Y%m"), finalAvailableTime.strftime("%Y%m")))
    # convert to stirng then parse to date
    start_time = datetime.strptime(str(start_time), "%Y%m")
    end_time = datetime.strptime(str(end_time), "%Y%m")
    # check range availability
    if not(firstAvailableTime <= start_time <= end_time <= finalAvailableTime):
        raise ValueError("Sorry, please input a valid time range between %s and %s" % (
            firstAvailableTime.strftime("%Y%m"), finalAvailableTime.strftime("%Y%m")))

    # add valid months to a list
    print("the time range between %s and %s" %
         (start_time.strftime("%Y%m"), end_time.strftime("%Y%m")))
    range_time = [start_time.strftime("%Y%m")]
    while start_time < end_time:
        start_time = start_time + relativedelta(months=+1)
        range_time.append(start_time.strftime("%Y%m"))
    return range_time
