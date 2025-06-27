from builtins import range
from builtins import object
__author__ = 'Fredrik Lindberg'

# This module will be used to plot output result from Suews
import numpy as np
import pandas as pd
import datetime
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as dt
    nomatplot = 0
except ImportError:
    nomatplot = 1
    pass


def leap_year(yy):
    if (yy % 4) == 0:
        if (yy % 100) == 0:
            if (yy % 400) == 0:
                leapyear = 1
            else:
                leapyear = 0
        else:
            leapyear = 1
    else:
        leapyear = 0

    return leapyear


def make_dectime(df_output_suews):
    datenum_yy = np.zeros(df_output_suews.shape[0])
    for i in range(0, df_output_suews.shape[0]): # making date number
        datenum_yy[i] = dt.date2num(dt.datetime.datetime(int(df_output_suews[i, 0]), 1, 1))

    dectime = datenum_yy + df_output_suews[:, 4]

    return dectime

def make_datetime(df_output_suews):
    datenum_yy = []
    for i in range(0, df_output_suews.shape[0]): # making date number
        datenum_yy.append(dt.datetime.datetime(int(df_output_suews[i, 0]), 1, 1) + datetime.timedelta(days=df_output_suews[i, 1] - 1, hours=df_output_suews[i, 2],minutes=df_output_suews[i, 3]))

    return datenum_yy


class SuewsPlotting(object):
    def __init__(self):
        pass

    def plotbasic(self, df_output_suews, df_met_forcing):

        plt.figure(1, figsize=(15, 7), facecolor='white')
        ax1 = plt.subplot(3, 1, 1)
        df_output_suews['Kdown'].plot(color =  'r', label='$K_{down}$', ax = ax1)
        df_output_suews['Kup'].plot(color = 'g', label='$K_{up}$', ax = ax1)
        df_output_suews['Ldown'].plot(color = 'b', label='$L_{down}$', ax = ax1)
        df_output_suews['Lup'].plot(color =  'c', label='$L_{up}$', ax = ax1)
        df_output_suews['QN'].plot( color = 'k', label='$Q*$', ax = ax1)
        ax1.set_ylim([-100, 1000])
        ax1.set_ylabel('$W$'' ''$m ^{-2}$', fontsize=14)
        plt.title('Model output of radiation balance, energy budget and water balance')
        pos1 = ax1.get_position()
        pos2 = [pos1.x0 - 0.07, pos1.y0 + 0.04, pos1.width * 1.05, pos1.height * 1.1]
        ax1.set_position(pos2)
        plt.legend(bbox_to_anchor=(1.02, 1.0), loc='upper left', borderaxespad=0.)

        ax2 = plt.subplot(3, 1, 2, sharex=ax1)
        df_output_suews['QS'].plot(color = 'k', label='$Q_S$', ax = ax2)
        df_output_suews['QH'].plot(color = 'r', label='$Q_H$', ax = ax2)
        df_output_suews['QF'].plot( color = 'c', label='$Q_F$', ax = ax2)
        df_output_suews['QE'].plot(color = 'b', label='$Q_E$', ax = ax2)
        ax2.set_ylabel('$W$'' ''$m ^{-2}$', fontsize=14)

        ax2.set_ylim([-200, df_output_suews.loc[:, ['QE', 'QS', 'QH', 'QF']].max().max()])
        pos1 = ax2.get_position()
        pos2 = [pos1.x0 - 0.07, pos1.y0 + 0.01, pos1.width * 1.05, pos1.height * 1.1]
        ax2.set_position(pos2)
        plt.legend(bbox_to_anchor=(1.02, 1.0), loc='upper left', borderaxespad=0.)

        ax3 = plt.subplot(3, 1, 3, sharex=ax1)
        df_output_suews['LAI'].plot(color = 'g', label='$LAI$', ax = ax3)
        ax3.legend(bbox_to_anchor=(1.05, 0.5), loc='upper left', borderaxespad=0.)
        ax3.set_xlabel('Time', fontsize=14)
        ax3.set_ylabel('$LAI$', color='g', fontsize=14)
        ax3.set_xlim([df_output_suews.index.min(), df_output_suews.index.max()])
        pos1 = ax3.get_position()
        pos2 = [pos1.x0 - 0.07, pos1.y0 - 0.02, pos1.width * 1.05, pos1.height * 1.1]
        ax3.set_position(pos2)
        ax4 = ax3.twinx()
        df_output_suews['SMD'].plot(color = 'k', label='$SMD$', ax =ax4)

        ax4.bar(df_met_forcing.index, df_met_forcing['rain'], width=0.01, edgecolor='b', label='$Precip$')
        ax4.set_ylim([0, max(df_met_forcing['rain'].max(), df_output_suews['SMD'].max())])
        ax4.set_ylabel('$mm$', color='b', fontsize=14)
        ax4.set_position(pos2)
        ax4.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left', borderaxespad=0.)
    def plotmonthlystatistics(self, df_output_suews, datain):
        
        # Create Month column
        df_output_suews['month'] = df_output_suews.index.month

        # Calculate monthly averages and sum
        df_monthly_mean = df_output_suews[['QH', 'QE', 'QS', 'QF', 'QN']].groupby(df_output_suews['month']).mean()

        df_monthly_sum = df_output_suews[['Rain', 'WUInt', 'Evap','RO', 'TotCh']].groupby(df_output_suews['month']).sum()

        plt.figure(2, figsize=(15, 7), facecolor='white')
        # Plot energy Balance
        ax1 = plt.subplot(1, 2, 1)
        ax1.axhline(0, color = 'grey', alpha = 0.5)
        df_monthly_mean['QN'].plot(style='o-', color = 'g', label='$Q*$', ax = ax1)
        df_monthly_mean['QF'].plot(style='o-', color = 'c', label='$Q_F$', ax = ax1)
        (-df_monthly_mean['QH']).plot(style='o-', color = 'r', label='$Q_H$', ax = ax1)
        (-df_monthly_mean['QE']).plot(style='o-', color = 'b', label='$Q_E$', ax = ax1)
        (-df_monthly_mean['QS']).plot(style='o-', color = 'k', label=r'$\Delta Q_S$', ax = ax1)
        ax1.set_xlim(1,12)
        ax1.set_xticks(range(1,13))

        ax1.set_xlabel('$Month$', fontsize=14)
        ax1.set_ylabel('$W$'' ''$m ^{-2}$', fontsize=14)
        plt.title('Monthly  partition of the surface energy balance')
        pos1 = ax1.get_position()
        pos2 = [pos1.x0 - 0.035, pos1.y0 + 0.00, pos1.width * 1.00, pos1.height * 1.0]
        ax1.set_position(pos2)
        plt.legend(bbox_to_anchor=(1.02, 1.0), loc='upper left', borderaxespad=0.)

        # Plot Water Balance
        ax3 = plt.subplot(1, 2, 2)
        ax3.axhline(0, color = 'grey', alpha = 0.5)
        (-df_monthly_sum['WUInt']).plot(style='o-', color = 'g', label='$W-use$', ax = ax3)
        (-df_monthly_sum['TotCh']).plot(style='o-', color = 'r', label='$Storage$', ax = ax3)
        (-df_monthly_sum['Evap']).plot(style='o-', color = 'b', label='$Evap$', ax = ax3)
        (-df_monthly_sum['RO']).plot(style='o-', color = 'k', label='$Runoff$', ax = ax3)
        ax3.bar(df_monthly_sum.index, df_monthly_sum['Rain'], width=0.5, edgecolor='b', align='center', label='$Precip$')
        ax3.set_xlabel('$Month$', fontsize=14)
        ax3.set_ylabel('$mm$', fontsize=14)
        plt.title('Monthly water balance')
        pos1 = ax3.get_position()
        pos2 = [pos1.x0 - 0.00, pos1.y0 - 0.00, pos1.width * 1.00, pos1.height * 1.0]
        ax3.set_position(pos2)
        ax3.set_position(pos2)
        ax3.axhline(0, color = 'grey')
        plt.legend(bbox_to_anchor=(1.02, 1.0), loc='upper left', borderaxespad=0.)
        ax3.set_xlim(1,12)
        ax3.set_xticks(range(1,13));





