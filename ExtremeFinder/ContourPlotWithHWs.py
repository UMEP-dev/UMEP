import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from netCDF4 import Dataset, date2num
import datetime
from datetime import timedelta
import time
import os
import math
from ..Utilities import f90nml
import urllib2

###########################################################################
#INPUT
###########################################################################

#read the namelist file
with open('/Users/hyacinth/Desktop/hwstat/input.nml') as nml_file:
    nml = f90nml.read(nml_file)

threshold_year_start = nml['time_control']['reference_start_year']
threshold_year_end = nml['time_control']['reference_end_year']
hw_year_start = nml['time_control']['start_year']
hw_month_start = nml['time_control']['start_month']
hw_day_start = nml['time_control']['start_day']
hw_year_end = nml['time_control']['end_year']
hw_month_end = nml['time_control']['end_month']
hw_day_end = nml['time_control']['end_day']
lat = nml['domain_control']['lat']
lon = nml['domain_control']['lon']
t1_quantile = nml['method']['t1_quantile']
t2_quantile = nml['method']['t2_quantile']

hw_start = [hw_year_start, hw_month_start, hw_day_start]
hw_start = '-'.join(str(d) for d in hw_start)
hw_end = [hw_year_end, hw_month_end, hw_day_end]
hw_end = '-'.join(str(d) for d in hw_end)

#read Tmax & static data
folderpath = nml['method']['Tmax_data_path']
nc = Dataset(nml['domain_control']['land_data_path'])
outputpath = nml['method']['output_path']
#folderpath = '/Volumes/15201514269/Tmax_Grid'
#nc = Dataset('/Volumes/15201514269/20150405HWDefinition/WFD-land-lat-long-z.nc')
land_global = nc.variables['land'][:]

#Find the nearest lat & lon in grid.
def lon_lat_grid(lat, lon):
    latGrid = 90 - (math.floor((90 - lat) / .5) * .5 + .25)
    lonGrid = math.floor((lon - (-180)) / .5) * .5 + .25 - 180
    return latGrid, lonGrid

#Find the land number of (lat, lon)
def WFD_get_city_index(city_latitude, city_longtitude):
    yGrid = math.floor((90 - city_latitude) / .5) + 1
    xGrid = math.floor((city_longtitude - (-180)) / .5) + 1
    return int((yGrid - 1) * 720 + xGrid)

def get_data(filepath, year_start, year_end):
    nc = Dataset(filepath)
    xTair = nc.variables['Tair'][:]
    xdate = pd.date_range('1901-01-01', '2012-12-31')
    Tair = pd.Series(xTair, index=xdate)
    return Tair['%d' % year_start:'%d' % year_end]

##########################################################################
# district initial
##########################################################################

latGrid, lonGrid=lon_lat_grid(lat, lon)
xland = WFD_get_city_index(latGrid, lonGrid)

import gzip
import StringIO

url = "http://www.urban-climate.net/watch_data/Tmax_Land_"+str (xland)+".nc.gz"
file_name = url.split('/')[-1]
res = urllib2.urlopen(url)
f_compressed = StringIO.StringIO(res.read())
f_decompressed = gzip.GzipFile(fileobj=f_compressed)
with open(file_name, 'w') as f_dat:
    f_dat.write(f_decompressed.read())

Tmax = get_data(file_name, hw_year_start, hw_year_end)
yearnumber = hw_year_end - hw_year_start + 1
DataForPlot = np.zeros((yearnumber,365))
hw_date = pd.date_range(hw_start, hw_end)

for i in range(0,yearnumber):
    ydate = pd.date_range(str(hw_year_start+i)+'-01-01', str(hw_year_start+i)+'-12-31')
    DataForPlot[i]=pd.Series(Tmax, index=ydate)[0:365]

from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator

x = range(1,366)
y = range(hw_year_start,hw_year_end+1)
z = DataForPlot

def level(minvalue,maxvalue):
    lev_tan = np.arange(1,5,0.4)
    lev = [math.atan(i) for i in lev_tan]
    levels = [(i-lev[0])/(lev[-1]-lev[0])*(maxvalue - minvalue)+ minvalue for i in lev]
    return levels

minvalue = z.min()
maxvalue = z.max()
levels = level(minvalue,maxvalue)


# pick the desired colormap, sensible levels, and define a normalization
# instance which takes data values and translates those into levels.
cmap = plt.get_cmap('RdBu_r')
norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

print z.min()
fig, (ax0) = plt.subplots(figsize=(20, 4))
im = ax0.pcolormesh(x, y, z, cmap=cmap, norm=norm)
fig.colorbar(im, ax=ax0)
plt.axis([1,365,hw_year_start,hw_year_end])
# plt.xticks(np.arange(1,12,1))
# Yticks = [str(i) for i in y]
#
# plt.yticks(Yticks)
#
# Yticks = [str(i) for i in y]
# print Yticks
ticks = ("Jan","Feb","Mar")
labels = range(0,12)
plt.xticks(ticks, labels)
plt.ylabel('Years')
plt.xlabel('Days of Year')


# fig.set_size_inches(15, 2.5)


ax0.set_title('Tmax During HWs')

path = '/Users/hyacinth/Desktop/Heatwave/111.txt'
data = pd.read_table(path,header=None,encoding='gb2312',delim_whitespace=True)

hwT = np.zeros((yearnumber,365))
pointX = []
pointY = []
for i in range(0,len(data)):
    yearX = str(data[0][i]).split("-",1)[0]
    locationY = int(yearX)-hw_year_start
    timestart = (time.mktime(datetime.datetime.strptime(str(yearX)+"-01-01", "%Y-%m-%d").timetuple()))/86400
    timestamp = int((time.mktime(datetime.datetime.strptime(data[0][i], "%Y-%m-%d").timetuple()))/86400)
    locationX = timestamp - timestart
    hwT[int(locationY)][int(locationX)] = data[1][i]
    pointX.append(locationX)
    pointY.append(locationY)

lineX = [pointX[0]]
lineY = [pointY[0]]
for i in range(0,len(pointX)-1):
    if pointX[i+1]-pointX[i]!=1:
        lineX.append(pointX[i])
        lineX.append(pointX[i+1])
        lineY.append(pointY[i+1])

lineX.append(pointX[-1])
mask = hwT[hwT>0]

# plot the box
for i in range(0,len(lineY)):
    tx0 = lineX[i*2]
    tx1 = lineX[i*2+1]
    ty0 = hw_year_start+lineY[i]
    ty1 = ty0+1
    sx = [tx0,tx1,tx1,tx0,tx0]
    sy = [ty0,ty0,ty1,ty1,ty0]
    plt.plot(sx,sy,"yellow",linewidth=2.0)


plt.show()
