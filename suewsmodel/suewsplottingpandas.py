from builtins import range
from builtins import object
__author__ = 'Fredrik Lindberg'

# This module will be used to plot output result from Suews
import numpy as np
try:
    import matplotlib.pylab as plt
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


def make_dectime(dataout):
    datenum_yy = np.zeros(dataout.shape[0])
    for i in range(0, dataout.shape[0]): # making date number
        datenum_yy[i] = dt.date2num(dt.datetime.datetime(int(dataout[i, 0]), 1, 1))

    dectime = datenum_yy + dataout[:, 4]

    return dectime

class SuewsPlottingPandas(object):
    def __init__(self):
        pass

    def plotforcing(self, df_forcing):
        list_var_forcing = [
            'kdown',
            'Tair',
            'RH',
            'pres',
            'U',
            'rain',
        ]
        dict_var_label = {
            'kdown': 'Incoming Solar\n Radiation ($ \mathrm{W \ m^{-2}}$)',
            'Tair': 'T_{Air} ($^{\circ}}$C)',
            'RH': r'Relative Humidity (%)',
            'pres': 'Pressure (hPa)',
            'rain': 'Rainfall (mm)',
            'U': 'Wind Speed (m $\mathrm{s^{-1}}$)'
        }
        df_plot_forcing_x = df_forcing.loc[:, list_var_forcing].copy().shift(
            -1).dropna(how='any')
        df_plot_forcing = df_plot_forcing_x.resample('1h').mean()
        df_plot_forcing['rain'] = df_plot_forcing_x['rain'].resample('1h').sum()

        axes = df_plot_forcing.plot(subplots=True, figsize=(14, 9), legend=False, )
        fig = axes[0].figure
        fig.tight_layout()
        for ax, var in zip(axes, list_var_forcing):
            ax.set_ylabel(dict_var_label[var])

    def plotbasic(self, df_output_suews, grid):

        # a dict for better display variable names
        dict_var_disp = {
            'QN': '$Q^*$',
            'QS': r'$\Delta Q_S$',
            'QE': '$Q_E$',
            'QH': '$Q_H$',
            'QF': '$Q_F$',
            'Kdown': r'$K_{\downarrow}$',
            'Kup': r'$K_{\uparrow}$',
            'Ldown': r'$L_{\downarrow}$',
            'Lup': r'$L_{\uparrow}$',
            'Rain': '$P$',
            'Irr': '$I$',
            'Evap': '$E$',
            'RO': '$R$',
            'TotCh': '$\Delta S$',
        }
        # dataout.loc[:, ['QN', 'QS', 'QE', 'QH', 'QF']].plot()

        # energy balance
        ax_output = df_output_suews.loc[:, ['QN', 'QS', 'QE', 'QH', 'QF']] \
            .rename(columns=dict_var_disp) \
            .plot(figsize=(12, 8), title='Surface Energy Balance')
        ax_output.set_xlabel('Date')
        ax_output.set_ylabel('Flux ($ \mathrm{W \ m^{-2}}$)')
        ax_output.legend()

    def plotmonthly(self, df_output_suews, grid):

        dict_var_disp = {
            'QN': '$Q^*$',
            'QS': r'$\Delta Q_S$',
            'QE': '$Q_E$',
            'QH': '$Q_H$',
            'QF': '$Q_F$',
            'Kdown': r'$K_{\downarrow}$',
            'Kup': r'$K_{\uparrow}$',
            'Ldown': r'$L_{\downarrow}$',
            'Lup': r'$L_{\uparrow}$',
            'Rain': '$P$',
            'Irr': '$I$',
            'Evap': '$E$',
            'RO': '$R$',
            'TotCh': '$\Delta S$',
        }

        # get a monthly Resampler
        df_plot = df_output_suews.copy()
        df_plot.index = df_plot.index.set_names('Month')
        rsmp_1M = df_plot.shift(-1).dropna(how='all').resample('1M', kind='period')
        # mean values
        df_1M_mean = rsmp_1M.mean()
        # sum values
        df_1M_sum = rsmp_1M.sum()

        # month names
        name_mon = [x.strftime('%b') for x in rsmp_1M.groups]
        # create subplots showing two panels together
        fig, axes = plt.subplots(2, 1, sharex=True)
        # surface energy balance
        df_1M_mean.loc[:, ['QN', 'QS', 'QE', 'QH', 'QF']].rename(columns=dict_var_disp).plot(
            ax=axes[0],  # specify the axis for plotting
            figsize=(10, 6),  # specify figure size
            title='Surface Energy Balance',
            kind='bar',
        )
        # surface water balance
        df_1M_sum.loc[:, ['Rain', 'Irr', 'Evap', 'RO', 'TotCh']].rename(columns=dict_var_disp).plot(
            ax=axes[1],  # specify the axis for plotting
            title='Surface Water Balance',
            kind='bar'
        )

        # annotations
        axes[0].set_ylabel('Mean Flux ($ \mathrm{W \ m^{-2}}$)')
        axes[0].legend()
        axes[1].set_xlabel('Month')
        axes[1].set_ylabel('Total Water Amount (mm)')
        axes[1].xaxis.set_ticklabels(name_mon, rotation=0)
        axes[1].legend()