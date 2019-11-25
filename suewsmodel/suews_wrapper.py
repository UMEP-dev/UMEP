from __future__ import print_function
from __future__ import absolute_import
from builtins import str
__author__ = 'xlinfr'
# from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
# from qgis.PyQt.QtGui import QIcon, QColor


def wrapper(pathtoplugin):

    import supy as sp
    from pathlib import Path
    import numpy as np
    from . import suewsdataprocessing
    from . import suewsplottingpandas
    import subprocess
    from ..Utilities import f90nml
    import os
    import sys
    import stat
    sys.path.append(pathtoplugin)

    try:
        import matplotlib.pyplot as plt
        nomatplot = 0
    except ImportError:
        nomatplot = 1
        pass

    su = suewsdataprocessing.SuewsDataProcessing()
    plp = suewsplottingpandas.SuewsPlottingPandas()

    # supy
    path_runcontrol = Path(pathtoplugin + '/RunControl.nml')
    df_state_init = sp.init_supy(path_runcontrol)
    grid = df_state_init.index[0]
    df_forcing = sp.load_forcing_grid(path_runcontrol, grid)
    df_output, df_state_final = sp.run_supy(df_forcing, df_state_init, check_input=True)
    df_output_suews = df_output['SUEWS']
    df_output_suews_rsmp = df_output_suews.loc[grid].resample('1h').mean()
    # import matplotlib.pyplot as plt
    # df_output_suews_rsmp.loc[:, ['QN', 'QS', 'QE', 'QH', 'QF']].plot()
    # plt.show()

    # # read namelist, Runcontrol.nml
    nml = f90nml.read(pathtoplugin + '/RunControl.nml')
    # fileinputpath = nml['runcontrol']['fileinputpath']
    fileoutputpath = nml['runcontrol']['fileoutputpath']
    filecode = nml['runcontrol']['filecode']
    # multiplemetfiles = nml['runcontrol']['multiplemetfiles']
    # snowuse = nml['runcontrol']['snowuse']
    # qschoice = nml['runcontrol']['storageheatmethod']
    # multipleestmfiles = nml['runcontrol']['multipleestmfiles']
    # tstep = nml['runcontrol']['tstep']
    timeaggregation = nml['runcontrol']['resolutionfilesout']
    # resolutionfilesin = nml['runcontrol']['resolutionfilesin']
    # KeepTstepFilesIn = nml['runcontrol']['KeepTstepFilesIn']

    suews_out = fileoutputpath + filecode + str(grid) + '_SUEWSout_' + str(int(timeaggregation / 60.)) + '.txt'
    str_out = df_output_suews_rsmp.to_string(float_format='%8.2f', na_rep='-999', justify='right', )
    with open(suews_out, 'w') as file_out:
        print(str_out, file=file_out)


    # pandasplotting
    # read namelist, plot.nml
        plotnml = f90nml.read(pathtoplugin + '/plot.nml')
        plotbasic = plotnml['plot']['plotbasic']
    #     choosegridbasic = plotnml['plot']['choosegridbasic']
    #     chooseyearbasic = plotnml['plot']['chooseyearbasic']
    #     # timeaggregation = plotnml['plot']['timeaggregation']
        plotmonthlystat = plotnml['plot']['plotmonthlystat']
    #     choosegridstat = plotnml['plot']['choosegridstat']
    #     chooseyearstat = plotnml['plot']['chooseyearstat']
    #     TimeCol_plot = np.array([1, 2, 3, 4]) - 1
    #     SumCol_plot = np.array([14]) - 1
    #     LastCol_plot = np.array([16]) - 1

    if nomatplot == 0:
        if plotbasic == 1:
            plp.plotbasic(df_output_suews_rsmp, df_forcing)

    # return df_output_suews_rsmp

    # # Working folder
    # if not os.path.exists(fileoutputpath):
    #     os.mkdir(fileoutputpath)
    # wf = pathtoplugin
    # prog_name = 'SUEWS_V2018a'

    # # Open SiteSelect to get year and gridnames
    # sitein = fileinputpath + 'SUEWS_SiteSelect.txt'
    # fs = open(sitein)
    # lin = fs.readlines()
    # index = 2
    # loop_out = ''
    # gridcodeestm = ''
    # ts_in = ''
    # gridcodemet = ''
    # # while loop_out != '-9':
    # lines = lin[index].split()
    # YYYY = int(lines[1])
    # gridcode = lines[0]  # for plotting
    # # resin = int(float(resolutionfilesin) / 60.)
    # # QMessageBox.critical(None, "Test", resolutionfilesin)
    # # return
    # # --- Create 5 min met-file and Ts-file --- #
    # if multiplemetfiles == 0:  # one file
    #     if index == 2:
    #         # gridcodemet = ''
    #         data_in = fileinputpath + filecode + '_' + str(YYYY) + gridcodemet + '_data_' + str(int(int(resolutionfilesin) / 60.)) + '.txt'  # No grid code in the name, nov 2015
    #         # data_in = fileinputpath + filecode + '_' + str(YYYY) + gridcodemet + '_data.txt'  # No grid code in the name, nov 2015
    #         met_old = np.genfromtxt(data_in, skip_header=1, missing_values='**********', filling_values=-9999) #  skip_footer=2,
    #         # met_old = np.loadtxt(data_in, skiprows=1)
    #         if met_old[1, 3] - met_old[0, 3] == 5:
    #             met_new = met_old
    #         else:
    #             met_new = su.tofivemin_v1(met_old)
    #
    # fs.close()

    # # --- This section runs the model --- #
    # pf = sys.platform
    # if pf == 'win32':
    #     suewsstring0 = 'REM' + '\n'
    #     suewsstring1 = 'cd ' + os.path.dirname(os.path.abspath(__file__)) + '\n'
    #     suewsstring2 = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + prog_name
    #     suewsbat = wf + '/runsuews.bat'
    #     f = open(suewsbat, 'w')
    #
    # if pf == 'darwin' or pf == 'linux2':
    #     suewsstring0 = '#!/bin/bash' + '\n'
    #     suewsstring1 = 'cd ' + os.path.dirname(os.path.abspath(__file__)) + '\n'
    #     suewsstring2 = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + prog_name
    #     suewsbat = wf + '/runsuews.sh'
    #     f = open(suewsbat, 'w')
    #     st = os.stat(wf + '/runsuews.sh')
    #     os.chmod(wf + '/runsuews.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    #     st2 = os.stat(wf + '/' + prog_name)
    #     os.chmod(wf + '/' + prog_name, st2.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    #
    # f.write(suewsstring0)
    # f.write(suewsstring1)
    # f.write(suewsstring2)
    # f.close()
    #
    # if pf == 'win32':
    #     si = subprocess.STARTUPINFO()
    #     si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    #
    # subprocess.call(suewsbat)

        # --- plot results --- #
    # if nomatplot == 0:
    #     # read namelist, plot.nml
    #     plotnml = f90nml.read(pathtoplugin + '/plot.nml')
    #     plotbasic = plotnml['plot']['plotbasic']
    #     choosegridbasic = plotnml['plot']['choosegridbasic']
    #     chooseyearbasic = plotnml['plot']['chooseyearbasic']
    #     # timeaggregation = plotnml['plot']['timeaggregation']
    #     plotmonthlystat = plotnml['plot']['plotmonthlystat']
    #     choosegridstat = plotnml['plot']['choosegridstat']
    #     chooseyearstat = plotnml['plot']['chooseyearstat']
    #     TimeCol_plot = np.array([1, 2, 3, 4]) - 1
    #     SumCol_plot = np.array([14]) - 1
    #     LastCol_plot = np.array([16]) - 1
    #
    #     suews_out = fileoutputpath + filecode + grid + '_' + str(YYYY) + '_SUEWS_' + str(
    #         int(timeaggregation / 60.)) + '.txt'
    #
    #     if plotbasic == 1:
    #         if choosegridbasic:
    #             gridcode = choosegridbasic
    #
    #         if chooseyearbasic:
    #             YYYY = chooseyearbasic
    #
    #         # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
    #         # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_SUEWS_' + str(int(timeaggregation/60.)) + '.txt'
    #         suews_plottime = np.loadtxt(suews_out, skiprows=1)
    #         # suews_res = np.loadtxt(suews_out, skiprows=1)
    #         #
    #         # suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
    #         suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, int(timeaggregation/60.))
    #
    #         pl.plotbasic(suews_plottime, suews_plottimeold)
    #         # pl.plotbasic(suews_result, met_old)
    #
    #     if plotmonthlystat == 1:
    #         if choosegridstat:
    #             gridcode = choosegridstat
    #
    #         if chooseyearstat:
    #             YYYY = chooseyearstat
    #
    #         # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
    #         # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_SUEWS_' + str(int(timeaggregation / 60.)) + '.txt'
    #         suews_plottime = np.loadtxt(suews_out, skiprows=1)
    #         # suews_res = np.loadtxt(suews_out, skiprows=1)
    #         #
    #         # suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
    #         suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot,
    #                                                  int(timeaggregation / 60.))
    #
    #         # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
    #         # suews_res = np.loadtxt(suews_out, skiprows=1)
    #         #
    #         # suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
    #         # suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, timeaggregation)
    #
    #         # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_' + str(timeres_min) + '.txt'
    #         #
    #         # suews_resu = np.loadtxt(suews_out, skiprows=1)
    #
    #         # pl.plotmonthlystatistics(suews_result, met_old)
    #         pl.plotmonthlystatistics(suews_plottime, suews_plottimeold)
    #
        if plotmonthlystat == 1:
            plt.show()

        if plotbasic == 1:
            plt.show()
    # else:
    #     print("No plots generated - No matplotlib installed")

    # removing input files
    # ind = 0
    # for j in range(2, index):
    #     lines = lin[j].split()
    #     YYYY = int(lines[1])
    #     gridcode = lines[0]
    #
    #     if KeepTstepFilesIn == 0 and multiplemetfiles == 1:
    #         gridcode = lines[0]
    #         data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
    #         if os.path.isfile(data_out):
    #             os.remove(data_out)
    #
    #     if KeepTstepFilesIn == 0 and multiplemetfiles == 0:
    #         gridcode = ''
    #         data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
    #         if os.path.isfile(data_out):
    #             os.remove(data_out)
    #     ind += 1





