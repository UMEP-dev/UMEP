#!/usr/bin/env python
import numpy as np
#import pandas as pd
try:
    import pandas as pd
except:
    pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it
import os
import glob
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ..Utilities import f90nml


# read in SUEWS output
def readSO(fn, plugin_dir):
    # load conversion dict: 2016 --> 2017
    dict_2016to2017 = dict(pd.read_excel(os.path.join(
        plugin_dir, 'header-2016to2017.xlsx')).values)
    # dict_2016to2017 = dict(pd.read_excel('header-2016to2017.xlsx').values)

    filename = os.path.abspath(os.path.expanduser(fn))
    rawdata = pd.read_csv(filename, sep='\s+')
    # change column names to 2017 convention if needed
    varname = pd.Series(rawdata.columns).replace(dict_2016to2017)
    rawdata.columns = varname

    # get datetime
    rawDT = rawdata.iloc[:, 0:4]
    # convert to pythonic datetime
    dtbase = pd.to_datetime(rawDT.iloc[:, 0], format='%Y')
    dtday = pd.to_timedelta(rawDT['DOY'], unit='d')
    dthour = pd.to_timedelta(rawDT['Hour'], unit='h')
    dtmin = pd.to_timedelta(rawDT['Min'], unit='m')
    resDT = dtbase + dtday + dthour + dtmin

    # get variable values
    resValue = rawdata.iloc[:, 5:].values

    # construct datetime-indexed DataFrame
    resData = pd.DataFrame(data=resValue, index=resDT, columns=varname[5:])
    return resData


# RMSE:
def func_RMSE(sim, ref):
    return np.sqrt(((sim - ref) ** 2).mean())


# mean bias error:
def func_MBE(sim, ref):
    return np.mean(sim - ref)


# mean absolute error:
def func_MAE(sim, ref):
    return np.mean(np.abs(sim - ref))


# mean absolute error:
def func_StdBias(sim, ref):
    return np.std(sim - ref)


# normalise to [0,1]
def func_Norm(data):
    xmax = data.max()
    xmin = data.min()
    res = (data - xmin) / (xmax - xmin)
    return res


# get results of configurations
def load_res_all(fn_nml, plugin_dir):
    # get all names
    prm = f90nml.read(fn_nml)
    prm_file = prm['file']
    # listAll = [os.path.basename(x)
    #            for x in glob.glob(os.path.join(dir_base, '*'))]
    # listRef = ['ref', 'base']
    # # names of configurations
    # listCfg = [x for x in listAll if not x in listRef]

    # get filenames of results
    fn_base = prm_file['input_basefile']
    fn_ref = prm_file['input_reffile']
    fn_cfg = prm_file['input_cfgfiles']
    # fn_ref = glob.glob(os.path.join(dir_base, 'ref', '*txt'))[0]
    # fn_obs = glob.glob(os.path.join(dir_base, 'base', '*txt'))[0]
    # fn_cfg = [glob.glob(os.path.join(dir_base, cfg, '*txt'))[0]
    #           for cfg in listCfg]

    # load all data
    # get reference run
    rawdata_ref = readSO(fn_ref, plugin_dir)

    # get baseline
    rawdata_base = readSO(fn_base, plugin_dir)

    # get benchmark runs
    # the configuration names need to be refined
    listCfg = np.arange(len(fn_cfg)) + 1
    rawdata_cfg = {cfg: readSO(fn, plugin_dir)
                   for cfg, fn in zip(listCfg, fn_cfg)}

    # pack the results into a pandas Panel
    res = rawdata_cfg.copy()
    res.update({'ref': rawdata_ref, 'base': rawdata_base})
    res = pd.Panel(res)

    # data cleaning:
    # 1. variables consisting of only NAN
    # 2. timestamp with any NAN
    res = pd.Panel({k: df.dropna(axis=1, how='all').dropna(axis=0, how='any')
                    for k, df in res.to_frame().to_panel().iteritems()})

    # calculate benchmark metrics
    return res


# get results of selected variables
def load_res_var(fn_nml, list_var_user, plugin_dir):
    # get all variables
    res_all = load_res_all(fn_nml, plugin_dir)
    # available variables after data cleaning:
    list_var_valid = res_all['base'].columns
    # get valid variables by intersecting:
    list_var = list_var_valid.intersection(list_var_user)

    # select variables of interest
    res = {k: v.loc[:, list_var] for k, v in res_all.iteritems()}

    return res


# generic load_res
def load_res(fn_nml, plugin_dir):
    prm = f90nml.read(fn_nml)
    prm_benchmark = prm['benchmark']
    list_var = prm_benchmark['list_var']
    if not (isinstance(list_var, basestring) or isinstance(list_var, list)):
        res = load_res_all(fn_nml, plugin_dir)
    else:
        # res=kwargs.keys()
        res = load_res_var(fn_nml, list_var, plugin_dir)
    return res


def plotMatMetric(res, base, func, title):
    # number of observations
    n_obs = base.index.size

    # calculate metrics
    resPlot = pd.DataFrame([func(x, base)
                            for k, x in res.iteritems()], index=res.keys())

    # rescale metrics values for plotting: [0,1]
    # resPlot_res = func_Norm(resPlot).dropna(axis=1)  # nan will be dropped
    # fill nan with 0.5 so as to display white
    if title == 'MBE':
        resPlot_res = func_Norm(np.abs(resPlot)).fillna(0.5)
    else:
        resPlot_res = func_Norm(resPlot).fillna(0.5)

    sub = resPlot_res.transpose()
    # select those non-nans based on rescaled values
    sub_val = resPlot.loc[:, resPlot_res.columns].transpose()

    # determine the shape of output
    nrow, ncol = sub.shape

    # reset plot to default settings
    plt.rcdefaults()

    # determine the figure size
    # figsize set to A4
    # size_fig=(8.27, 11.69)
    size_fig = (2 * ncol, nrow)
    fig = plt.figure(figsize=size_fig, dpi=100)
    plt.axes(frameon=False)
    plt.tick_params(axis='both', length=0)

    plt.pcolormesh(np.array(sub),
                   cmap='PiYG_r',
                   edgecolors='w', linewidths=6)

    # annotate the color swatches with metric values
    for x in np.arange(ncol):
        for y in np.arange(nrow):
            # print x,y
            if 0.4 < sub.iloc[y, x] < .6:
                xcolor = 'black'
            else:
                xcolor = 'white'
            plt.annotate("{:4.2f}".format(sub_val.iloc[y, x]), xy=(x + 0.5, y + 0.5),
                         verticalalignment='center',
                         horizontalalignment='center',
                         fontsize=11,
                         color=xcolor)

    # label ticks with variable names
    plt.yticks(np.arange(.5, nrow + 1, 1),
               sub.index, fontsize=12, weight='bold')

    # label ticks with configuration names
    plt.xticks(np.arange(.5, ncol + 1, 1),
               sub.columns, fontsize=14, weight='bold')
    plt.title(title + ' (N=%d)' % n_obs, fontsize=16, weight='bold')
    # plt.savefig(filename, bbox_inches='tight')
    # plt.show()
    return fig


def plotMatMetricX(res_panel, func, title):
    res_comp = pd.Panel({x: res_panel[x]
                         for x in res_panel.keys() if not x == 'base'})
    fig = plotMatMetric(res_comp, res_panel['base'], func, title)
    return fig


def plotBarScore(res_score):
    plt.rcdefaults()
    plt.figure(figsize=(8.27, 11.69), dpi=100)
    fig_score, ax = plt.subplots()

    res_score.sort_values(inplace=True)

    y_lbl = res_score.index
    y_pos = np.arange(len(y_lbl))

    mask_better = res_score > res_score['ref']
    mask_ref = res_score.index == 'ref'
    mask_worse = res_score <= res_score['ref']

    # make zero values visible in the plot
    res_score.replace({0.0: 0.5}, inplace=True)

    res_score = np.array(res_score)
    ax.barh(y_pos[mask_better], res_score[mask_better],
            align='center', color='green')
    ax.barh(y_pos[mask_worse], res_score[mask_worse],
            align='center', color='gray')

    # res_score=pd.DataFrame(res_score)
    ax.barh(y_pos[mask_ref], res_score[mask_ref], align='center', color='blue')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_lbl, fontsize=12, weight='bold')
    # ax.invert_yaxis()
    ax.set_xlabel(
        'Performance Score (larger scores indicate better performance)', fontsize=12, weight='bold')
    ax.set_title('Performance Comparison', fontsize=16, weight='bold')
    return fig_score


# generate benchmark figures
def benchmarkSUEWS(fn_nml, plugin_dir):
    # load results in pandas Panel
    # data = load_res_all(dir_base)
    data = load_res(fn_nml, plugin_dir)

    # all available metrics
    list_func_all = {'RMSE': func_RMSE,
                     'Bias_std': func_StdBias,
                     'MAE': func_MAE,
                     'MBE': func_MBE}

    # select functions to be used
    prm = f90nml.read(fn_nml)
    prm_bmk = prm['benchmark']
    list_metric = prm_bmk['list_metric']
    list_func = {k: list_func_all[k] for k in list_metric}

    # calculate metrics based on different functions:
    res_metric = {f: pd.DataFrame([list_func[f](data[x], data['base'])
                                   for x in data.keys() if not x == 'base'],
                                  index=[x for x in data.keys() if not x == 'base']).dropna(axis=1)
                  for f in list_func.keys()}
    res_metric = pd.Panel(res_metric)

    # calculate overall performance:
    # this method is very simple at the moment and needs to be refined with
    # more options
    res_score_sub = pd.DataFrame(
        [1 - func_Norm(v.transpose().mean()) for key, v in res_metric.iteritems()])
    res_score = res_score_sub.mean(axis=0) * 100

    # plotting:
    # 1. overall performance score
    # print res_score
    fig_score = plotBarScore(res_score)
    res_fig = {'score': fig_score}

    # 2. sub-indicators
    # plot each metric in one page
    fig_metric = {name_func: plotMatMetricX(data, list_func[name_func], name_func)
                  for name_func in list_func.keys()}
    res_fig.update(fig_metric)

    return res_fig


# output report in PDF
def report_benchmark(fn_nml, plugin_dir):
    prm = f90nml.read(fn_nml)
    prm_file = prm['file']
    basename_output = prm_file['output_pdf']
    prm_bmk = prm['benchmark']
    list_metric = prm_bmk['list_metric']
    figs = benchmarkSUEWS(fn_nml, plugin_dir)
    with PdfPages(basename_output + '.pdf') as pdf:
        pdf.savefig(figs['score'], bbox_inches='tight', papertype='a4')
        for k, x in figs.iteritems():
            if k != 'score':
                pdf.savefig(x, bbox_inches='tight',
                            papertype='a4', orientation='portrait')
