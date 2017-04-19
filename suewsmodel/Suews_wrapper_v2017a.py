__author__ = 'xlinfr'
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QColor


def wrapper(pathtoplugin):

    import numpy as np
    import suewsdataprocessing
    import suewsplotting
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
    pl = suewsplotting.SuewsPlotting()

    # # read namelist, Runcontrol.nml
    nml = f90nml.read(pathtoplugin + '/RunControl.nml')
    fileinputpath = nml['runcontrol']['fileinputpath']
    fileoutputpath = nml['runcontrol']['fileoutputpath']
    filecode = nml['runcontrol']['filecode']
    multiplemetfiles = nml['runcontrol']['multiplemetfiles']
    # snowuse = nml['runcontrol']['snowuse']
    # qschoice = nml['runcontrol']['storageheatmethod']
    # multipleestmfiles = nml['runcontrol']['multipleestmfiles']
    tstep = nml['runcontrol']['tstep']
    timeaggregation = nml['runcontrol']['resolutionfilesout']
    resolutionfilesin = nml['runcontrol']['resolutionfilesin']
    KeepTstepFilesIn = nml['runcontrol']['KeepTstepFilesIn']
    #
    #
    # Working folder
    if not os.path.exists(fileoutputpath):
        os.mkdir(fileoutputpath)
    wf = pathtoplugin
    prog_name = 'SUEWS_V2017a'

    # Open SiteSelect to get year and gridnames
    sitein = fileinputpath + 'SUEWS_SiteSelect.txt'
    fs = open(sitein)
    lin = fs.readlines()
    index = 2
    loop_out = ''
    gridcodeestm = ''
    ts_in = ''
    gridcodemet = ''
    # while loop_out != '-9':
    lines = lin[index].split()
    YYYY = int(lines[1])
    gridcode = lines[0] # for plotting
    # resin = int(float(resolutionfilesin) / 60.)
    # QMessageBox.critical(None, "Test", resolutionfilesin)
    # return
    # --- Create 5 min met-file and Ts-file --- #
    if multiplemetfiles == 0:  # one file
        if index == 2:
            # gridcodemet = ''
            data_in = fileinputpath + filecode + '_' + str(YYYY) + gridcodemet + '_data_' + str(int(int(resolutionfilesin) / 60.)) + '.txt'  # No grid code in the name, nov 2015
            met_old = np.genfromtxt(data_in, skip_header=1, missing_values='**********', filling_values=-9999) #  skip_footer=2,
            # met_old = np.loadtxt(data_in, skiprows=1)
            if met_old[1, 3] - met_old[0, 3] == 5:
                met_new = met_old
            else:
                met_new = su.tofivemin_v1(met_old)
    #     else:  # multiple files
    #         gridcodemet = lines[0]
    #         data_in = fileinputpath + filecode + gridcodemet + '_data.txt'
    #         met_old = np.loadtxt(data_in, skiprows=1)
    #         if met_old[1, 3] - met_old[0, 3] == 5:
    #             met_new = met_old
    #         else:
    #             met_new = su.tofivemin_v1(met_old)
    #
    #     # if index == 2:
    #     #     dectime0 = met_old[0, 1] + met_old[0, 2] / 24 + met_old[0, 3] / (60 * 24)
    #     #     dectime1 = met_old[1, 1] + met_old[1, 2] / 24 + met_old[1, 3] / (60 * 24)
    #         # timeres_old = int(np.round((dectime1 - dectime0) * (60. * 24.))) # moved to runcontrol
    #
    #     if qschoice == 4 or qschoice == 14:
    #         if multipleestmfiles == 0: # one ts file
    #             if index == 2:
    #                 # gridcodeestm = ''
    #                 ts_in = fileinputpath + filecode + gridcodeestm +'_Ts_data.txt' # No grid code in the name, nov 2015
    #             ts_old = np.loadtxt(ts_in, skiprows=1)
    #             if ts_old[1, 3] - ts_old[0, 3] == 5:
    #                 ts_new = ts_old
    #             else:
    #                 ts_new = su.ts_tofivemin_v1(ts_old)
    #         else:  # multiple ts files
    #             gridcodeestm = lines[0]
    #             ts_in = fileinputpath + filecode + gridcodeestm + '_Ts_data.txt'
    #             ts_old = np.loadtxt(ts_in, skiprows=1)
    #             if ts_old[1, 3] - ts_old[0, 3] == 5:
    #                 ts_new = ts_old
    #             else:
    #                 ts_new = su.ts_tofivemin_v1(ts_old)
    #     # else:
    #     #     gridcodeestm = ''
    #
    #     # find start end end of 5 min file for each year
    #     posstart = np.where((met_new[:, 0] == YYYY) & (met_new[:, 1] == 1) & (met_new[:, 2] == 0) & (met_new[:, 3] == 5))
    #     posend = np.where((met_new[:, 0] == YYYY + 1) & (met_new[:, 1] == 1) & (met_new[:, 2] == 0) & (met_new[:, 3] == 0))
    #     fixpos = 1
    #
    #     if len(posstart[0]) == 0:
    #         starting = 0
    #     else:
    #         starting = posstart[0]
    #     if len(posend[0]) == 0:
    #         ending = met_new.shape[0]
    #         fixpos = 0
    #     else:
    #         ending = posend[0]
    #
    #     met_save = met_new[int(starting):int(ending) + fixpos, :]  # originally for one full year
    #
    #     # --- save met-file --- #
    #     data_out = fileinputpath + filecode + gridcodemet + '_' + str(YYYY) + '_data_5.txt'
    #     header = 'iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow ldown fcld wuh xsmd lai kdiff kdir wdir'
    #     numformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.4f %6.2f %6.2f %6.2f %6.2f ' \
    #                 '%6.4f %6.2f %6.2f %6.2f %6.2f %6.2f'
    #
    #     if multiplemetfiles == 0: # one file
    #         if index == 2:
    #             np.savetxt(data_out, met_save, fmt=numformat, delimiter=' ', header=header, comments='')
    #             f_handle = file(data_out, 'a')
    #             endoffile = [-9, -9]
    #             np.savetxt(f_handle, endoffile, fmt='%2d')
    #             f_handle.close()
    #     else:
    #         np.savetxt(data_out, met_save, fmt=numformat, delimiter=' ', header=header, comments='')
    #         f_handle = file(data_out, 'a')
    #         endoffile = [-9, -9]
    #         np.savetxt(f_handle, endoffile, fmt='%2d')
    #         f_handle.close()
    #
    #     if qschoice == 4 or qschoice == 14:
    #         # find start end end of 5 min ts file for each year
    #         posstart = np.where((ts_new[:, 0] == YYYY) & (ts_new[:, 1] == 1) & (ts_new[:, 2] == 0) & (ts_new[:, 3] == 5))
    #         posend = np.where((ts_new[:, 0] == YYYY + 1) & (ts_new[:, 1] == 1) & (ts_new[:, 2] == 0) & (ts_new[:, 3] == 0))
    #         fixpos = 1
    #
    #         if len(posstart[0]) == 0:
    #             starting = 0
    #         else:
    #             starting = posstart[0]
    #         if len(posend[0]) == 0:
    #             ending = ts_new.shape[0]
    #             fixpos = 0
    #         else:
    #             ending = posend[0]
    #
    #         ts_save = ts_new[starting:ending + fixpos, :]  # originally for one full year
    #
    #         # save ts-file
    #         ts_out = fileinputpath + filecode + gridcodeestm + '_' + str(YYYY) + '_ESTM_Ts_data_5.txt'
    #         tsheader = 'iy id it imin Tiair Tsurf Troof Troad Twall Twall_n Twall_e Twall_s Twall_w'
    #         tsnumformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f'
    #         np.savetxt(ts_out, ts_save, fmt=tsnumformat, delimiter=' ', header=tsheader, comments='')
    #         f_handle = file(ts_out, 'a')
    #         endoffile = [-9, -9]
    #         np.savetxt(f_handle, endoffile, fmt='%2d')
    #         f_handle.close()
    #
    #     lines = lin[index + 1].split()
    #     loop_out = lines[0]
    #     index += 1
    #
    fs.close()

    # --- This section runs the model --- #
    pf = sys.platform
    if pf == 'win32':
        suewsstring0 = 'REM' + '\n'
        suewsstring1 = 'cd ' + os.path.dirname(os.path.abspath(__file__)) + '\n'
        suewsstring2 = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + prog_name
        suewsbat = wf + '/runsuews.bat'
        f = open(suewsbat, 'w')

    if pf == 'darwin' or pf == 'linux2':
        suewsstring0 = '#!/bin/bash' + '\n'
        suewsstring1 = 'cd ' + os.path.dirname(os.path.abspath(__file__)) + '\n'
        suewsstring2 = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + prog_name
        suewsbat = wf + '/runsuews.sh'
        f = open(suewsbat, 'w')
        st = os.stat(wf + '/runsuews.sh')
        os.chmod(wf + '/runsuews.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        st2 = os.stat(wf + '/' + prog_name)
        os.chmod(wf + '/' + prog_name, st2.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    f.write(suewsstring0)
    f.write(suewsstring1)
    f.write(suewsstring2)
    f.close()

    if pf == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    subprocess.call(suewsbat)

    # # # --- This part makes temporal averages from SUEWS 5 min output --- #
    # # # Check if 5 min files should be deleted
    # KeepTstepFilesIn = nml['runcontrol']['KeepTstepFilesIn']
    # # KeepTstepFilesOut = nml['runcontrol']['KeepTstepFilesOut']
    # #
    # # # Open ...OutputFormat.txt
    # # # sitein = fileoutputpath + filecode + '_' + str(YYYY) + '_' + str(int(tstep / 60)) + '_OutputFormat.txt'
    # sitein = fileoutputpath + filecode + '_YYYY_' + str(int(timeaggregation / 60)) + '_OutputFormat.txt'
    # f = open(sitein)
    # lin2 = f.readlines()
    # head = lin2[1].split(";")
    # pynumformat = ''
    # formatparts = lin2[4].split(";")
    # aggrparts = lin2[5].split(";")
    # TimeCol = np.array([],dtype=int)
    # SumCol = np.array([],dtype=int)
    # LastCol = np.array([],dtype=int)
    # header = ''
    #
    # for i in range(0, formatparts.__len__()):
    #     formatpartsi = formatparts[i][1:-4]
    #     if i == formatparts.__len__() - 1:
    #         formatpartsi = formatparts[i][1:-6]
    #         header += head[i][0:-1]
    #     else:
    #         header += head[i] + ' '
    #     if formatpartsi[0] == 'i':
    #         numform = str(int(formatpartsi[1:]))
    #     else:
    #         numform = str(float(formatpartsi[1:]))
    #     pynumformat += '%' + numform + formatpartsi[0] + ' '
    #     if aggrparts[i] == '0':
    #         TimeCol = np.hstack([TimeCol, int(i)])
    #     if aggrparts[i] == '2':
    #         SumCol = np.hstack([SumCol, int(i)])
    #     if aggrparts[i] == '3':
    #         LastCol = np.hstack([LastCol, int(i)])
    # #     # header += head[i] + ' '
    #
    ### THIS HAS BEEN MOVED TO FORTRAN ###
    # # pynumformat = '%4i ' + '%3i ' * 3 + '%8.5f ' +\
    # #     '%9.4f ' * 5 + '%9.4f ' * 7 +\
    # #     '%9.4f ' +\
    # #     '%10.6f ' * 4 +\
    # #     '%10.5f ' * 1 + '%10.6f ' * 3 +\
    # #     '%10.6f ' * 6 +\
    # #     '%9.3f ' * 2 + '%9.4f ' * 4 +\
    # #     '%10.5f ' * 3 + '%14.7g ' * 1 + '%10.5f ' * 1 +\
    # #     '%10.4f ' * 2 + '%10.5f ' * 6 + '%10.5f ' * 7 +\
    # #     '%10.4f ' * 4 +\
    # #     '%10.4f ' * 5 + '%10.6f ' * 6 +\
    # #     '%8.4f' * 1
    #
    # # TimeCol = np.array([1, 2, 3, 4, 5]) -1
    # # SumCol = np.array([19,20,21,22,  25,26, 27,28,29,30,31,32,  33,34,35,36,37,38,  71,72,73]) -1
    # # LastCol = np.array( [23,24,  44,45,46,47,48,49,50,51,  52,53,54,55,56,57,58,  59,60,61,62,  68,69,70,  74]) -1
    #
    # # header = '%iy id it imin dectime '\
    # #          'kdown kup ldown lup Tsurf qn h_mod e_mod qs qf qh qe '\
    # #          'qh_r '\
    # #          'P/i Ie/i E/i Dr/i '\
    # #          'St/i NWSt/i surfCh/i totCh/i '\
    # #          'RO/i ROsoil/i ROpipe ROpav ROveg ROwater '\
    # #          'AdditionalWater FlowChange WU_int WU_EveTr WU_DecTr WU_Grass '\
    # #          'ra rs ustar L_Ob Fcld '\
    # #          'SoilSt smd smd_Paved smd_Bldgs smd_EveTr smd_DecTr smd_Grass smd_BSoil '\
    # #          'St_Paved St_Bldgs St_EveTr St_DecTr St_Grass St_BSoil St_Water '\
    # #          'LAI z0m zdm bulkalbedo '\
    # #          'qn1_SF qn1_S Qm QmFreez QmRain SWE Mw MwStore snowRem_Paved snowRem_Bldgs ChSnow/i '\
    # #          'SnowAlb'
    #
    # # Still hard-coded python numformat
    # header_snow = '%iy  id   it imin dectime SWE_Paved SWE_Bldgs SWE_EveTr SWE_DecTr SWE_Grass SWE_BSoil SWE_Water ' \
    #               'Mw_Paved Mw_Bldgs Mw_EveTr Mw_DecTr Mw_Grass Mw_BSoil Mw_Water Qm_Paved Qm_Bldgs Qm_EveTr Qm_DecTr ' \
    #               'Qm_Grass Qm_BSoil Qm_Water Qa_Paved Qa_Bldgs Qa_EveTr Qa_DecTr Qa_Grass Qa_BSoil Qa_Water QmFr_Paved ' \
    #               'QmFr_Bldgs QmFr_EveTr QmFr_DecTr QmFr_Grass QmFr_BSoil QmFr_Water fr_Paved fr_Bldgs fr_EveTr fr_DecTr ' \
    #               'fr_Grass fr_BSoil RainSn_Paved RainSn_Bldgs RainSn_EveTr RainSn_DecTr RainSn_Grass RainSn_BSoil ' \
    #               'RainSn_Water Qn_PavedSnow Qn_BldgsSnow Qn_EveTrSnpw Qn_DecTrSnow Qn_GrassSnpw Qn_BSoilSnow ' \
    #               'Qn_WaterSnow kup_PavedSnow kup_BldgsSnow kup_EveTrSnpw kup_DecTrSnow kup_GrassSnpw kup_BSoilSnow ' \
    #               'kup_WaterSnow frMelt_Paved frMelt_Bldgs frMelt_EveTr frMelt_DecTr frMelt_Grass frMelt_BSoil ' \
    #               'frMelt_Water MwStore_Paved MwStore_Bldgs MwStore_EveTr MwStore_DecTr MwStore_Grass MwStore_BSoil ' \
    #               'MwStore_Water DensSnow_Paved DensSnow_Bldgs DensSnow_EveTr DensSnow_DecTr DensSnow_Grass ' \
    #               'DensSnow_BSoil DensSnow_Water Sd_Paved Sd_Bldgs Sd_EveTr Sd_DecTr Sd_Grass Sd_BSoil Sd_Water ' \
    #               'Tsnow_Paved Tsnow_Bldgs Tsnow_EveTr Tsnow_DecTr Tsnow_Grass Tsnow_BSoil Tsnow_Water'
    # pynumformat_snow = '%4i ' + '%3i ' * 3 + '%8.5f ' + '%10.4f ' * 97
    # TimeCol_snow = np.array([1, 2, 3, 4, 5]) - 1
    # SumCol_snow = np.array([13, 14, 15, 16, 17, 18, 19, 47, 48, 49, 50, 51, 52, 53, 68, 69, 70, 71, 72, 73, 74]) - 1
    # LastCol_snow = np.array([6, 7, 8, 9, 10, 11, 12, 62, 75, 76, 77, 78, 79, 80, 81]) - 1
    #
    # header_estm = '%iy id it imin dectime QSNET QSAIR QSWALL QSROOF QSGROUND QSIBLD TWALL1 TWALL2 TWALL3 TWALL4 TWALL5' \
    #               ' TROOF1 TROOF2 TROOF3 TROOF4 TROOF5 TGROUND1 TGROUND2 TGROUND3 TGROUND4 TGROUND5 TiBLD1 TiBLD2 ' \
    #               'TiBLD3 TiBLD4 TiBLD5 TaBLD'
    # pynumformat_estm = '%4i ' + '%3i ' * 3 + '%8.5f ' + '%10.4f ' * 27
    #
    # resolutionfilesout = nml['runcontrol']['resolutionfilesout']
    # timeres_min = resolutionfilesout / 60
    #
    # for j in range(2, index):
    #     lines = lin[j].split()
    #     YYYY = int(lines[1])
    #     gridcode = lines[0]
    #     data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
    #     suews_5min = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
    #     suews_in = np.genfromtxt(suews_5min, skip_header=1, missing_values='**********', filling_values=-9999)
    #     # suews_in = np.loadtxt(suews_5min, skiprows=1)
    #     suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_' + str(timeres_min) + '.txt'
    #
    #     # suews_1hour = su.from5minto1hour_v1(suews_in, SumCol, LastCol, TimeCol)
    #     suews_result = su.from5mintoanytime(suews_in, SumCol, LastCol, TimeCol, timeres_min)
    #     np.savetxt(suews_out, suews_result, fmt=pynumformat, delimiter=' ', header=header, comments='')
    #
    #     if qschoice == 4 or qschoice == 14:
    #         estm_5min = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_ESTM_5.txt'
    #         estm_in = np.loadtxt(estm_5min, skiprows=1)
    #         estm_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_ESTM_' + str(timeres_min) + '.txt'
    #         estm_result = su.from5mintoanytime(estm_in, [], [], TimeCol, timeres_min)
    #         np.savetxt(estm_out, estm_result, fmt=pynumformat_estm, delimiter=' ', header=header_estm, comments='')
    #
    #     if snowuse == 1:
    #         suews_5min_snow = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_snow_5.txt'
    #         suews_out_snow = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_snow_' + str(timeres_min) + '.txt'
    #         suews_in_snow = np.loadtxt(suews_5min_snow, skiprows=1)
    #         suews_1hour_snow = su.from5mintoanytime(suews_in_snow, SumCol_snow, LastCol_snow, TimeCol_snow, timeres_min)
    #         np.savetxt(suews_out_snow, suews_1hour_snow, fmt=pynumformat_snow, delimiter=' ', header=header_snow, comments='')

    # --- plot results --- #
    if nomatplot == 0:
        # read namelist, plot.nml
        plotnml = f90nml.read(pathtoplugin + '/plot.nml')
        plotbasic = plotnml['plot']['plotbasic']
        choosegridbasic = plotnml['plot']['choosegridbasic']
        chooseyearbasic = plotnml['plot']['chooseyearbasic']
        # timeaggregation = plotnml['plot']['timeaggregation']
        plotmonthlystat = plotnml['plot']['plotmonthlystat']
        choosegridstat = plotnml['plot']['choosegridstat']
        chooseyearstat = plotnml['plot']['chooseyearstat']
        TimeCol_plot = np.array([1, 2, 3, 4]) - 1
        SumCol_plot = np.array([14]) - 1
        LastCol_plot = np.array([16]) - 1

        if plotbasic == 1:
            if choosegridbasic:
                gridcode = choosegridbasic

            if chooseyearbasic:
                YYYY = chooseyearbasic

            # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
            suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_' + str(int(timeaggregation/60.)) + '.txt'
            suews_plottime = np.loadtxt(suews_out, skiprows=1)
            # suews_res = np.loadtxt(suews_out, skiprows=1)
            #
            # suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
            suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, int(timeaggregation/60.))

            pl.plotbasic(suews_plottime, suews_plottimeold)
            # pl.plotbasic(suews_result, met_old)

        if plotmonthlystat == 1:
            if choosegridstat:
                gridcode = choosegridstat

            if chooseyearstat:
                YYYY = chooseyearstat

            # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
            suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_' + str(
                int(timeaggregation / 60.)) + '.txt'
            suews_plottime = np.loadtxt(suews_out, skiprows=1)
            # suews_res = np.loadtxt(suews_out, skiprows=1)
            #
            # suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
            suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot,
                                                     int(timeaggregation / 60.))

            # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
            # suews_res = np.loadtxt(suews_out, skiprows=1)
            #
            # suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
            # suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, timeaggregation)

            # suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_' + str(timeres_min) + '.txt'
            #
            # suews_resu = np.loadtxt(suews_out, skiprows=1)

            # pl.plotmonthlystatistics(suews_result, met_old)
            pl.plotmonthlystatistics(suews_plottime, suews_plottimeold)

        if plotmonthlystat == 1:
            plt.show()

        if plotbasic == 1:
            plt.show()
    else:
        print("No plots generated - No matplotlib installed")

    # removing input files
    ind = 0
    for j in range(2, index):
        lines = lin[j].split()
        YYYY = int(lines[1])
        gridcode = lines[0]

        # if KeepTstepFilesIn == 0 and multipleestmfiles == 1:
        #     gridcodeestm = lines[0]
        #     ts_out = fileinputpath + filecode + gridcodeestm + '_' + str(YYYY) + '_ESTM_Ts_data_5.txt'
        #     if os.path.isfile(ts_out):
        #         os.remove(ts_out)
        # if KeepTstepFilesIn == 0 and multipleestmfiles == 0:
        #     if ind == 2:
        #         gridcodeestm = ''
        #         ts_out = fileinputpath + filecode + gridcodeestm + '_' + str(YYYY) + '_ESTM_Ts_data_5.txt'
        #         if os.path.isfile(ts_out):
        #             os.remove(ts_out)

        if KeepTstepFilesIn == 0 and multiplemetfiles == 1:
            gridcode = lines[0]
            data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
            if os.path.isfile(data_out):
                os.remove(data_out)

        if KeepTstepFilesIn == 0 and multiplemetfiles == 0:
            gridcode = ''
            data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
            if os.path.isfile(data_out):
                os.remove(data_out)
        ind += 1

    #
    # if KeepTstepFilesOut == 0:
    #     os.remove(suews_5min)
    #     if snowuse == 1:
    #         os.remove(suews_5min_snow)





