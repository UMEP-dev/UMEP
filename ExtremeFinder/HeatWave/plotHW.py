from builtins import str
from builtins import range
# -*- coding: utf-8 -*-

###########################################
# plot
###########################################
from datetime import datetime, timedelta, time
import math

import datetime
# pandas, netCDF4 and numpy might not be shipped with QGIS
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm
    import numpy as np
    from netCDF4 import Dataset, date2num
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
    if lat == None or lon == None:
        return 'Unknown location'
    if lon>=0:
        if lat>=0:
            strloc = str(abs(lon))+u"°E, "+str(abs(lat))+u"°N"
        else:
            strloc = str(abs(lon))+u"°E, "+str(abs(lat))+u"°S"
    else:
        if lat>=0:
            strloc = str(abs(lon))+u"°W, "+str(abs(lat))+u"°N"
        else:
            strloc = str(abs(lon))+u"°W, "+str(abs(lat))+u"°S"
    return strloc

#plot

def plotHW(lat,lon,Tmax, xHW, hw_year_start, hw_year_end, labelsForPlot):
    # hw_year_start = int(str(hw_start).split("-",1)[0])
    # hw_year_end = int(str(hw_end).split("-",1)[0])

    ####################################################
    #                      contour                     #
    ####################################################
    yearnumber = hw_year_end - hw_year_start + 1

    # Check that first and final year are complete. If not, don't include in plot
    range_start = 0
    range_end = yearnumber

    ydate_first = pd.date_range(str(hw_year_start) + '-01-01',  str(hw_year_start) + '-12-31')
    ydate_final = pd.date_range(str(hw_year_start + yearnumber-1) + '-01-01',  str(hw_year_start + yearnumber-1) + '-12-31')
    data_first = pd.Series(Tmax, index= ydate_first)[0:365]
    data_final = pd.Series(Tmax, index= ydate_final)[0:365]
    if sum(np.isnan(data_first)) > 0:
        range_start = 1
    if sum(np.isnan(data_final)) > 0:
        range_end-=1

    range_size = range_end - range_start
    DataForPlot = np.zeros((range_size, 365))
    for i in range(range_start, range_end):
        ydate = pd.date_range(str(hw_year_start + i) + '-01-01',
                              str(hw_year_start + i) + '-12-31')
        DataForPlot[i-range_start] = pd.Series(Tmax, index=ydate)[0:365]

    xmin = 1
    xmax = 366
    dx = 1
    ymin = hw_year_start + range_start
    ymax = hw_year_start + range_end
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
    fig.colorbar(im, ax=ax0, label='%s %s'%(labelsForPlot[0], labelsForPlot[3]))
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
    ax0.set_title(labelsForPlot[0]+' at ('+strlocation(lat,lon)+')')

    ####################################################
    #                   HWs highlight                  #
    ####################################################

    data = xHW

    hwT = np.zeros((yearnumber, 365))
    pointX = []
    pointY = []
    for iHW in xHW:
        ts_datetime = iHW.index
        ts_year = ts_datetime[0].year
        ts_len = len(ts_datetime)
        tx0 = ts_datetime[0]

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
        plt.plot(sx, sy, "yellow", linewidth=2.0)

    plt.show()

    ####################################################
    #                   barcharplot                    #
    ####################################################

    for iHW in xHW:
        ts_datetime = iHW.index
        ts_year = ts_datetime.year
        iHW.index = ts_year

    TmaxForBoxplot = xHW[0].tolist()
    YearsForBoxplot = [xHW[0].index[0]]
    dataForBoxplot = []
    lenTmaxForBarchart = [len(xHW[0])]
    lendataForBarchart = []

    if not len(xHW)==1:
        for i in range(1,len(xHW)):
            if xHW[i].index[0] == xHW[i-1].index[0]:
                TmaxForBoxplot.extend(xHW[i].tolist())
                lenTmaxForBarchart.extend([len(xHW[i])])
            else:
                dataForBoxplot.append(TmaxForBoxplot)
                YearsForBoxplot.append(xHW[i].index[0])
                lendataForBarchart.append(lenTmaxForBarchart)
                lenTmaxForBarchart = [len(xHW[i])]
                TmaxForBoxplot = xHW[i].tolist()
    dataForBoxplot.append(TmaxForBoxplot)
    lendataForBarchart.append(lenTmaxForBarchart)

    YearList = list(range(hw_year_start,hw_year_end+1))
    # TdataList = [ [] for _ in range(len(YearList))]
    for i in range(0,len(YearList)):
        if not YearList[i]==YearsForBoxplot[-1]:
            if not YearList[i]==YearsForBoxplot[i]:
                YearsForBoxplot.insert(i,YearList[i])
                dataForBoxplot.insert(i,[])
                lendataForBarchart.insert(i,[0])
        else:
            if not i == len(YearList)-1:
                YearsForBoxplot.insert(i+1,YearList[i+1])
                dataForBoxplot.insert(i+1,[])
                lendataForBarchart.insert(i+1,[0])

    maxLen = np.max([len(a) for a in lendataForBarchart])
    dataForBarchart = np.zeros((len(YearList),maxLen),dtype=np.int)
    for i in range(0,len(YearList)):
        for j in range(0,len(lendataForBarchart[i])):
            dataForBarchart[i,j]=lendataForBarchart[i][j]
    dataForBarchart = dataForBarchart.T

    plt.figure()
    # Get some pastel shades for the colors
    colors = plt.cm.Paired(np.linspace(0, 1, len(dataForBarchart)))
    bar_width = 0.4
    index = np.arange(1,len(YearList)+1)-0.2
    y_offset = np.array([0.0] * len(YearList))

    # Plot bars and create text labels for the table
    for row in range(len(dataForBarchart)):
        plt.bar(index, dataForBarchart[row], bar_width, bottom=y_offset, color=colors[row])
        y_offset = y_offset + dataForBarchart[row]

    # Reverse colors and text labels to display the last value at the top.
    colors = colors[::-1]

    xticks=list(range(1,len(YearsForBoxplot)+1,dyForTicks))
    plt.xlabel("Time (Years)")
    plt.ylabel("Days")
    plt.xticks(xticks,yearticks_lbl)
    plt.title(labelsForPlot[1]+' Days in ('+strlocation(lat,lon)+')')
    plt.show()

    ####################################################
    #                      boxplot                     #
    ####################################################
    # plt.figure()
    plt.figure()
    plt.boxplot(dataForBoxplot)
    plt.xticks(xticks,yearticks_lbl)
    plt.ylabel('%s %s'%(labelsForPlot[0], labelsForPlot[3]))
    plt.xlabel('Time (Years)')
    plt.title('BoxPlot for '+labelsForPlot[0]+' during '+labelsForPlot[2]+' in ('+strlocation(lat,lon)+')')

    plt.show()