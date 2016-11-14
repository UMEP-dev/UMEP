# -*- coding: utf-8 -*-

###########################################
# plot
###########################################
import os.path
from datetime import datetime, timedelta, time
import os
import math
# import f90nml
import webbrowser
import datetime
import time
import gzip
import StringIO
import urllib2
import tempfile
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator

# pandas, netCDF4 and numpy might not be shipped with QGIS
try:
    import pandas as pd
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

try:
    from netCDF4 import Dataset, date2num
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

try:
    import numpy as np
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it




# rescale color levels


def level(minvalue, maxvalue):
    lev_tan = np.arange(2, 6, 0.3)
    lev = [math.atan(i) for i in lev_tan]
    levels = [int((i - lev[0]) / (lev[-1] - lev[0]) *
              (maxvalue - minvalue) + minvalue) for i in lev]
    return levels

def strlocation(lat,lon):
    if lon>=0:
        if lat>=0:
            strloc = str(lon)+u"°E, "+str(lat)+u"°N"
        else:
            strloc = str(lon)+u"°E, "+str(lat)+u"°S"
    else:
        if lat>=0:
            strloc = str(lon)+u"°W, "+str(lat)+u"°N"
        else:
            strloc = str(lon)+u"°W, "+str(lat)+u"°S"
    return strloc

#plot

def plotHW(lat,lon,Tmax, xHW, hw_year_start, hw_year_end):
    # hw_year_start = int(str(hw_start).split("-",1)[0])
    # hw_year_end = int(str(hw_end).split("-",1)[0])

    ####################################################
    #                      contour                     #
    ####################################################
    yearnumber = hw_year_end - hw_year_start + 1
    DataForPlot = np.zeros((yearnumber, 365))
    # hw_date = pd.date_range(hw_start, hw_end)

    for i in range(0, yearnumber):
        ydate = pd.date_range(str(hw_year_start + i) +
                              '-01-01', str(hw_year_start + i) + '-12-31')
        DataForPlot[i] = pd.Series(Tmax, index=ydate)[0:365]

    x = range(1, 366)
    y = range(hw_year_start, hw_year_end + 1)
    xmin = 1
    xmax = 366
    dx = 1
    ymin = hw_year_start
    ymax = hw_year_end + 1
    dy = 1
    x2, y2 = np.meshgrid(np.arange(xmin, xmax + dx, dx) -
                         dx / 2., np.arange(ymin, ymax + dy, dy) - dy / 2.)
    z = DataForPlot

    minvalue = z.min()
    maxvalue = z.max()
    levels = level(minvalue, maxvalue)

    # pick the desired colormap, sensible levels, and define a normalization
    # instance which takes data values and translates those into levels.
    cmap = plt.get_cmap('RdBu_r')
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

    fig, (ax0) = plt.subplots(figsize=(20, 4.5))
    im = ax0.pcolormesh(x2, y2, z, cmap=cmap, norm=norm)
    fig.colorbar(im, ax=ax0, label='Temp (K)')
    plt.axis([x2.min(), x2.max(), y2.min(), y2.max()])
    xticks = pd.Series([1, 31, 59, 90, 120, 151, 181,
                        212, 243, 273, 304, 334, 365])
    plt.xticks(xticks.rolling(window=2).mean()[1:], ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                                     "Nov", "Dec"])
    if (ymax-ymin+1)<=7:
        dyForTicks=1
    else:
        dyForTicks=int((ymax-ymin+1)/7)
    yearticks = np.arange(ymin, ymax, dyForTicks)
    yearticks_lbl=[str(x) for x in yearticks]
    plt.yticks(yearticks, yearticks_lbl)
    plt.ylabel('Time (years)')
    plt.xlabel('Time (DoY)')
    ax0.set_title('Tmax at ('+strlocation(lat,lon)+')')

    ####################################################
    #                   HWs highlight                  #
    ####################################################

    data = xHW

    hwT = np.zeros((yearnumber, 365))
    pointX = []
    pointY = []
    for iHW in xHW:
        ts_datetime = iHW.index
        # print ts_datetime
        # print ts_datetime[0]
        # print ts_datetime[0].year
        ts_year = ts_datetime[0].year
        # print ts_year
        ts_len = len(ts_datetime)
        tx0 = ts_datetime[0]
        # print datetime.date(ts_datetime[0].year, 1, 1)

        day_of_year_f = ts_datetime[0].to_pydatetime(
        ) - datetime.datetime(ts_datetime[0].year, 1, 1)
        day_of_year = day_of_year_f.days
        # print day_of_year
        tx0 = day_of_year + 0.5
        tx1 = ts_len + tx0
        ty0 = ts_year - 0.5
        ty1 = ts_year + 0.5
        sx = [tx0, tx1, tx1, tx0, tx0]
        sy = [ty0, ty0, ty1, ty1, ty0]
        # print sx, sy
        plt.plot(sx, sy, "yellow", linewidth=2.0)

    plt.show()

    ####################################################
    #                   barcharplot                    #
    ####################################################

    for iHW in xHW:
        ts_datetime = iHW.index
        ts_year = ts_datetime.year
        iHW.index = ts_year

    TmaxForBoxplot = xHW[0]
    YearsForBoxplot = [xHW[0].index[0]]
    dataForBoxplot = []
    lenTmaxForBarchart = [len(xHW[0])]
    lendataForBarchart = []
    # print TmaxForBoxplot,YearsForBoxplot

    if not len(xHW)==1:
        for i in range(1,len(xHW)):
            if xHW[i].index[0] == xHW[i-1].index[0]:
                TmaxForBoxplot.append(xHW[i])
                lenTmaxForBarchart.extend([len(xHW[i])])
            else:
                dataForBoxplot.append(TmaxForBoxplot.tolist())
                YearsForBoxplot.append(xHW[i].index[0])
                lendataForBarchart.append(lenTmaxForBarchart)
                lenTmaxForBarchart = [len(xHW[i])]
                TmaxForBoxplot = xHW[i]
    dataForBoxplot.append(TmaxForBoxplot.tolist())
    lendataForBarchart.append(lenTmaxForBarchart)

    YearList = range(hw_year_start,hw_year_end+1)
    # TdataList = [ [] for _ in range(len(YearList))]
    for i in range(0,len(YearList)):
        if not YearList[i]==YearsForBoxplot[-1]:
            if not YearList[i]==YearsForBoxplot[i]:
                YearsForBoxplot.insert(i,YearList[i])
                dataForBoxplot.insert(i,[])
                lendataForBarchart.insert(i,[0])
        else:
            YearsForBoxplot.insert(i,YearList[i])
            dataForBoxplot.insert(i,[])
            lendataForBarchart.insert(i,[0])
    dataForBarchart = np.zeros((len(YearList),10),dtype=np.int)
    dataForBarchart[0,0]=lendataForBarchart[0][0]
    for i in range(0,len(YearList)):
        for j in range(0,len(lendataForBarchart[i])):
            dataForBarchart[i,j]=lendataForBarchart[i][j]
    dataForBarchart = dataForBarchart.T

    plt.figure()
    # Get some pastel shades for the colors
    colors = plt.cm.BuPu(np.linspace(0, 1, len(dataForBarchart)))
    bar_width = 0.4
    index = np.arange(1,len(YearList)+1)-0.2
    y_offset = np.array([0.0] * len(YearList))

    # Plot bars and create text labels for the table
    for row in range(len(dataForBarchart)):
        plt.bar(index, dataForBarchart[row], bar_width, bottom=y_offset, color=colors[row])
        y_offset = y_offset + dataForBarchart[row]

    # Reverse colors and text labels to display the last value at the top.
    colors = colors[::-1]

    xticks=range(1,len(YearsForBoxplot)+1,dyForTicks)
    plt.xlabel("Time (Years)")
    plt.ylabel("Days")
    plt.xticks(xticks,yearticks_lbl)
    plt.title('Heat Wave Days in ('+strlocation(lat,lon)+')')
    plt.show()

    ####################################################
    #                      boxplot                     #
    ####################################################
    # plt.figure()
    plt.figure()
    plt.boxplot(dataForBoxplot)
    plt.xticks(xticks,yearticks_lbl)
    plt.ylabel('Temp (K)')
    plt.xlabel('Time (Years)')
    plt.title('BoxPlot for Tmax during HWs in ('+strlocation(lat,lon)+')')

    plt.show()

    # # plot the box
    # for i in range(0, len(lineY)):
    #     tx0 = lineX[i * 2] + 0.5
    #     tx1 = lineX[i * 2 + 1] + 0.5
    #     ty0 = hw_year_start + lineY[i] - 0.5
    #     ty1 = ty0 + 1
    #     sx = [tx0, tx1, tx1, tx0, tx0]
    #     sy = [ty0, ty0, ty1, ty1, ty0]
    #     plt.plot(sx, sy, "yellow", linewidth=2.0)

    # for i in range(0,len(data)):
    #     yearX = str(data[0][i]).split("-",1)[0]
    #     locationY = int(yearX)-hw_year_start
    #     timestart = (time.mktime(datetime.datetime.strptime(str(yearX)+"-01-01", "%Y-%m-%d").timetuple()))/86400
    #     timestamp = int((time.mktime(datetime.datetime.strptime(data[0][i], "%Y-%m-%d").timetuple()))/86400)
    #     locationX = timestamp - timestart
    #     hwT[int(locationY)][int(locationX)] = data[1][i]
    #     pointX.append(locationX)
    #     pointY.append(locationY)
    #
    # lineX = [pointX[0]]
    # lineY = [pointY[0]]
    # for i in range(0,len(pointX)-1):
    #     if pointX[i+1]-pointX[i]!=1:
    #         lineX.append(pointX[i])
    #         lineX.append(pointX[i+1])
    #         lineY.append(pointY[i+1])
    #
    # lineX.append(pointX[-1])
    # mask = hwT[hwT>0]
