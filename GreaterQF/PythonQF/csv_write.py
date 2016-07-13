import Calcs3
import numpy as np
import read_data_files
import Config
import csv 
import datetime as dt
from ...Utilities import f90nml

areaname=Config.SpatialDomain
if areaname=='SubOA200Data':
    y=read_data_files.SubOAAreaDataReader(areaname)
else:
    y=read_data_files.AreaDataReader(areaname)
y.AData()
y.Code()
Area=y.Area
Code=y.IDCode

def WattDayWrite():
    WattDayWrite=Calcs.WattDay
    date = dt.date(2006,5,26)

    with open('WattDayMJ.csv', 'w') as csvfile:
        cwriter = csv.writer(csvfile, delimiter=';',
                            quoting=csv.QUOTE_NONE)
        cwriter.writerow( ('Area', 'Date', 'Total Qf') )
        for i in range(len(Code)):
            cwriter.writerow( (Code[i], date+dt.timedelta(days=1),WattDayWrite[i,18]))
    
    return None

LAnml = f90nml.read('borough_names_codes.nml') #stored in borough_names_codes.nml
borough_codes=LAnml['borough_nml']['borough_codes']  #ONS LA code new

header=borough_codes 

def HHJan2005array():
    HHJan2005=Calcs3.mostcalcs()
    
    
def HHJan2005():
    HHJan2005=Calcs3.mostcalcs()
    date_time = dt.datetime(2005,1,1)
    
    with open('Jan2005HHtest2.csv','w') as csvfile:
        cwriter=csv.writer(csvfile, delimiter=';',
                            quoting=csv.QUOTE_NONE,escapechar=' ')
        cwriter.writerow(header)
        for day in range(len(HHJan2005.keys())):
            for hh in range(48):
                row = HHJan2005[date_time.strftime('%Y-%m-%d')][:,18,hh]
                cwriter.writerow(row)
                date_time+=dt.timedelta(minutes=30)

            
                
          

    
    
    
    