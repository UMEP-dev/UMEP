#!/usr/bin/env python
# Adjusted to fit UMEP plugin 20181024 - Fredrik
from __future__ import print_function
import numpy as np
import os
from ..Utilities import f90nml
#import f90nml
try:
    import xarray as xr
    from matplotlib import colors
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except:
    pass


# read SUEWS output results as an xarray.DataArray
def readSO(fn, plugin_dir):
    # load conversion dict: 2016 --> 2017
    # dict_2016to2017 = dict(pd.read_excel('header-2016to2017.xlsx').values)
    dict_2016to2017 = dict(pd.read_excel(os.path.join(
        plugin_dir, 'header-2016to2017.xlsx')).values)
    # dict_2016to2017 = dict(pd.read_excel('header-2016to2017.xlsx').values)

    filename = os.path.abspath(os.path.expanduser(fn))
    rawdata = pd.read_csv(filename, sep='\s+', low_memory=False)
    # change column names to 2017 convention if needed
    varname = pd.Series(rawdata.columns).replace(dict_2016to2017)
    rawdata.columns = varname

    # get datetime
    rawDT = rawdata.iloc[:, 0:4]
    # convert to pythonic datetime
    dtbase = pd.to_datetime(rawDT.iloc[:, 0], format='%Y')
    # corrected DOY by deducting one day for timedelta
    dtday = pd.to_timedelta(rawDT['DOY'] - 1, unit='d')
    dthour = pd.to_timedelta(rawDT['Hour'], unit='h')
    dtmin = pd.to_timedelta(rawDT['Min'], unit='m')
    resDT = dtbase + dtday + dthour + dtmin

    # get variable values
    resValue = rawdata.iloc[:, 5:].values

    # construct datetime-indexed DataArray
    resDA = xr.DataArray(data=resValue,
                         coords=[resDT, varname[5:]],
                         dims=['time', 'var'])
    return resDA


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

    # get filenames of results
    fn_obs = prm_file['path_obs']
    fn_ref = prm_file['path_ref']
    fn_cfg = prm_file['path_cfg']
    name_cfg = prm_file['name_cfg']

    # load all data
    # get reference run
    rawdata_ref = readSO(fn_ref, plugin_dir)

    # get baseline
    rawdata_obs = readSO(fn_obs, plugin_dir)

    # get benchmark runs
    # the configuration names need to be refined
    rawdata_cfg = {cfg: readSO(fn, plugin_dir) for cfg, fn in list(zip(name_cfg, fn_cfg))}

    # pack the results into an xarray Dataset
    res_raw = rawdata_cfg.copy()
    res_raw.update({'ref': rawdata_ref, 'obs': rawdata_obs})

    # convert Dataset to DataFrame for easier processing
    res = xr.Dataset(res_raw).to_dataframe()
    # give configuration level a name
    res.columns.rename('cfg', inplace=True)

    # data cleaning:
    # drop variables without valid values
    res = res.dropna(axis=1, how='all')
    # drop times with invalid values
    res = res.dropna(axis=0, how='any')

    # re-order levels to facilliate further selection
    # top-down column levels: {'cfg','var'}
    res = res.unstack().swaplevel('cfg', 'var', axis=1).sort_index(axis=1)

    return res


# generic load_res
def load_res(fn_nml, plugin_dir):
    prm = f90nml.read(fn_nml)
    prm_benchmark = prm['benchmark']
    list_var = prm_benchmark['list_var']

    # load all variables
    res = load_res_all(fn_nml, plugin_dir)
    # select part of the variables
    if (isinstance(list_var, str) or isinstance(list_var, list)):
        res = res.loc[:, list_var]

    # drop invalid values
    res = res.dropna()
    return res


def plotMatMetric(res_metric, len_metric, title):
    # number of observations
    n_obs = len_metric

    # drop nan values
    resPlot = res_metric.dropna()

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
            plt.annotate("{:4.2f}".format(sub_val.iloc[y, x]),
                         xy=(x + 0.5, y + 0.5),
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
        'Performance Score \n(larger scores indicate better performance)',
        fontsize=12, weight='bold')
    ax.set_title('Performance Comparison', fontsize=16, weight='bold')
    return fig_score


# generate benchmark figures
def benchmark_SUEWS(fn_nml, plugin_dir):
    # load results in pandas Panel
    # data = load_res_all(dir_base)
    res_raw = load_res(fn_nml, plugin_dir)
    res_cfg = res_raw.swaplevel('cfg', 'var', axis=1).sort_index(axis=1)

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
    list_cfg = res_cfg.columns.get_level_values('cfg').unique()
    list_cfg = list_cfg.drop('obs', errors='ignore')
    res_metric = {f: pd.DataFrame(
        [list_func[f](res_cfg[cfg], res_cfg['obs'])
         for cfg in list_cfg],
        index=list_cfg).dropna(axis=1).apply(np.round, decimals=2)
        for f in list(list_func.keys())}
    ds_metric = xr.Dataset(res_metric)
    df_metric = ds_metric.to_dataframe()

    # name the index levels
    df_metric.index.rename(['cfg', 'var'], inplace=True)
    # name the column levels
    df_metric.columns.rename('stat', inplace=True)
    # improve the layout
    df_metric = df_metric.unstack()

    # add some meta-info: size of valid comparison data
    # NB: this is an EXPERIMENTAL test, not fully supported by pandas
    df_metric.len_metric = res_cfg['obs'].shape[0]

    return df_metric


def benchmark_score(df_metric):
    # calculate overall performance:
    # this method is very simple at the moment and needs to be refined with
    # more options
    res_score_sub = df_metric.apply(func_Norm).dropna(axis=1)
    res_score = (1 - res_score_sub.mean(axis=1)) * 100

    return res_score


def plot_score_metric(df_metric):

    # calculate overall performance score
    res_score = benchmark_score(df_metric)

    # plotting:
    # 1. overall performance score
    # print res_score
    fig_score = plotBarScore(res_score)
    res_fig = {'score': fig_score}

    # 2. sub-indicators
    # plot each metric in one page
    len_metric = df_metric.len_metric
    list_func = df_metric.columns.get_level_values('stat').unique()
    fig_metric = {name_func: plotMatMetric(
        df_metric[name_func],
        len_metric, name_func)
        for name_func in list_func}
    res_fig.update(fig_metric)

    return res_fig


# output report in PDF
def report_benchmark_PDF(fn_nml, plugin_dir):
    prm = f90nml.read(fn_nml)
    prm_file = prm['file']
    basename_output = prm_file['path_report_pdf']
    # basename_output = prm_file['output_pdf']

    # calculate benchmark results
    df_metric = benchmark_SUEWS(fn_nml, plugin_dir)

    # plotting metric results
    figs = plot_score_metric(df_metric)

    with PdfPages(basename_output) as pdf:
        pdf.savefig(figs['score'], bbox_inches='tight', papertype='a4')
        for k, x in figs.items():
            if k != 'score':
                pdf.savefig(x, bbox_inches='tight',
                            papertype='a4', orientation='portrait')


# output report in HTML
# normalise color values
def colour_norm(res):
    s = np.abs(res)
    m = s.min()
    M = s.max()
    range = M - m
    if range != 0:
        norm = colors.Normalize(m, M)
        normed = norm(s.values)
    else:
        normed = np.ones_like(res) * 0.5
    return normed


# set text colours
def text_color(res):
    normed = colour_norm(res)
    c_text = [('black' if 0.4 < x < 0.6 else 'white') for x in normed]
    return ['color: %s' % color for color in c_text]


# set background colour
def background_gradient(res, cmap='PuBu'):
    normed = colour_norm(res)
    # print normed
    c_rgba = [plt.cm.get_cmap(cmap)(x)
              if x != 0.5 else tuple(list(plt.cm.get_cmap(cmap)(x)[:3]) + [0])
              for x in normed]
    # print c_rgba
    c = [colors.rgb2hex(x) for x in c_rgba]
    # print c
    return ['background-color: %s' % color for color in c]


# generate matrix-like stat HTML
def mat_stat_HTML(df_metric, styles):
    # generate metric Styler
    style_metric = df_metric.T.style
    style_metric.apply(background_gradient, axis=1, cmap='PiYG_r')
    style_metric.apply(text_color, axis=1)

    style_metric = style_metric.set_table_styles(styles)
    style_metric = style_metric.set_caption('SUEWS benchmark statistics')

    res_html = style_metric.render()

    return res_html


# generate overall barplot of performance score HTML
def bar_score_HTML(df_metric, styles):

    df_score = benchmark_score(
        df_metric).to_frame().rename(columns={0: 'score'})

    # generate metric Styler
    style_score = df_score.style
    style_score.bar(align='left', color=['#d65f5f', '#5fba7d'])
    style_score = style_score.set_table_styles(styles)
    style_score = style_score.set_caption('SUEWS benchmark score')
    res_html = style_score.render()

    return res_html


def report_benchmark_HTML(fn_nml, plugin_dir):
    prm = f90nml.read(fn_nml)
    prm_file = prm['file']
    basename_output = prm_file['path_report_html']

    styles = [
        # table properties
        dict(selector=" ",
             props=[("margin", "0"),
                    ('max-width', '200px'),
                    ("font-family", '"Helvetica", "Arial", sans-serif'),
                    ("border-collapse", "collapse"),
                    ("border", "none"),
                    ("border", "2px solid #ccf")
                    ]),

        # header color - optional
        dict(selector="thead",
             props=[("background-color", "#ABB2B9")
                    ]),

        # background shading
        dict(selector="tbody tr:nth-child(even)",
             props=[("background-color", "#fff")]),
        dict(selector="tbody tr:nth-child(odd)",
             props=[("background-color", "#eee")]),

        # cell spacing
        dict(selector="td",
             props=[("padding", ".5em")]),

        # header cell properties
        dict(selector="th",
             props=[("font-size", "125%"),
                    ("padding", ".5em"),
                    ("text-align", "center")]),

        # caption placement
        dict(selector="caption",
             props=[("caption-side", "top")]),

        # render hover last to override background-color
        dict(selector="tbody tr:hover",
             props=[("background-color", "%s" % "#add8e6")])]

    # calculate benchmark results
    df_metric = benchmark_SUEWS(fn_nml, plugin_dir)

    # colour map
    # cm = sns.light_palette("green", as_cmap=True)

    # generate score Styler
    score_html = bar_score_HTML(df_metric, styles)
    # save html text
    path_html = basename_output + '_score.html'
    with open(path_html, 'w') as fn:
        fn.write(score_html)
        fn.close()

    # generate metric Styler
    stat_html = mat_stat_HTML(df_metric, styles)
    # save html text
    path_html = basename_output + '_stat.html'
    with open(path_html, 'w') as fn:
        fn.write(stat_html)
        fn.close()
