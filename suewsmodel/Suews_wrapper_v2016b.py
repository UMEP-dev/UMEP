__author__ = 'xlinfr'

import numpy as np
import suewsdataprocessing
import suewsplotting
import subprocess
from ..Utilities import f90nml
import os
import sys
import stat
from PyQt4.QtGui import QMessageBox


def wrapper(pathtoplugin):


    sys.path.append(pathtoplugin)

    try:
        import matplotlib.pyplot as plt
        nomatplot = 0
    except ImportError:
        nomatplot = 1
        pass

    su = suewsdataprocessing.SuewsDataProcessing()
    pl = suewsplotting.SuewsPlotting()

    # read namelist, Runcontrol.nml
    nml = f90nml.read(pathtoplugin + '/RunControl.nml')
    fileinputpath = nml['runcontrol']['fileinputpath']
    fileoutputpath = nml['runcontrol']['fileoutputpath']
    filecode = nml['runcontrol']['filecode']
    multiplemetfiles = nml['runcontrol']['multiplemetfiles']
    snowuse = nml['runcontrol']['snowuse']
    qschoice = nml['runcontrol']['qschoice']
    multipleestmfiles = nml['runcontrol']['multipleestmfiles']
    # Working folder
    if not os.path.exists(fileoutputpath):
        os.mkdir(fileoutputpath)
    wf = pathtoplugin
    prog_name = 'SUEWS_V2016b'
    goodmetdata = 1

    # Open SiteSelect to get year and gridnames
    sitein = fileinputpath + 'SUEWS_SiteSelect.txt'
    f = open(sitein)
    lin = f.readlines()
    index = 2
    loop_out = ''
    while loop_out != '-9':
        lines = lin[index].split()
        YYYY = int(lines[1])

        # --- Create 5 min met-file and Ts-file --- #
        if multiplemetfiles == 0: # one file
            if index == 2:
                gridcodemet = ''
                data_in = fileinputpath + filecode + gridcodemet + '_data.txt' # No grid code in the name, nov 2015
                met_old = np.loadtxt(data_in, skiprows=1)
                goodmetdata = metdatacheck(met_old)
                if goodmetdata == 0:
                    return
                if met_old[1, 3] - met_old[0, 3] == 5:
                    met_new = met_old
                else:
                    met_new = su.tofivemin_v1(met_old)
        else:  # multiple files
            gridcodemet = lines[0]
            data_in = fileinputpath + filecode + gridcodemet + '_data.txt'
            met_old = np.loadtxt(data_in, skiprows=1)
            goodmetdata = metdatacheck(met_old)
            if goodmetdata == 0:
                return
            if met_old[1, 3] - met_old[0, 3] == 5:
                met_new = met_old
            else:
                met_new = su.tofivemin_v1(met_old)

        if index == 2:
            dectime0 = met_old[0, 1] + met_old[0, 2] / 24 + met_old[0, 3] / (60 * 24)
            dectime1 = met_old[1, 1] + met_old[1, 2] / 24 + met_old[1, 3] / (60 * 24)
            # timeres_old = int(np.round((dectime1 - dectime0) * (60. * 24.))) # moved to runcontrol

        if qschoice == 4 or qschoice == 14:
            if multipleestmfiles == 0: # one ts file
                if index == 2:
                    gridcodeestm = ''
                    ts_in = fileinputpath + filecode + gridcodeestm +'_Ts_data.txt' # No grid code in the name, nov 2015
                ts_old = np.loadtxt(ts_in, skiprows=1)
                if ts_old[1, 3] - ts_old[0, 3] == 5:
                    ts_new = ts_old
                else:
                    ts_new = su.ts_tofivemin_v1(ts_old)
            else:  # multiple ts files
                gridcodeestm = lines[0]
                ts_in = fileinputpath + filecode + gridcodeestm + '_Ts_data.txt'
                ts_old = np.loadtxt(ts_in, skiprows=1)
                if ts_old[1, 3] - ts_old[0, 3] == 5:
                    ts_new = ts_old
                else:
                    ts_new = su.ts_tofivemin_v1(ts_old)
        else:
            gridcodeestm = ''

        # find start end end of 5 min file for each year
        posstart = np.where((met_new[:, 0] == YYYY) & (met_new[:, 1] == 1) & (met_new[:, 2] == 0) & (met_new[:, 3] == 5))
        posend = np.where((met_new[:, 0] == YYYY + 1) & (met_new[:, 1] == 1) & (met_new[:, 2] == 0) & (met_new[:, 3] == 0))
        fixpos = 1

        if len(posstart[0]) == 0:
            starting = 0
        else:
            starting = posstart[0]
        if len(posend[0]) == 0:
            ending = met_new.shape[0]
            fixpos = 0
        else:
            ending = posend[0]

        met_save = met_new[starting:ending + fixpos, :]  # originally for one full year

        # --- save met-file --- #
        data_out = fileinputpath + filecode + gridcodemet + '_' + str(YYYY) + '_data_5.txt'
        header = 'iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow ldown fcld wuh xsmd lai kdiff kdir wdir'
        numformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.4f %6.2f %6.2f %6.2f %6.2f ' \
                    '%6.4f %6.2f %6.2f %6.2f %6.2f %6.2f'

        if multiplemetfiles == 0: # one file
            if index == 2:
                np.savetxt(data_out, met_save, fmt=numformat, delimiter=' ', header=header, comments='')
                f_handle = file(data_out, 'a')
                endoffile = [-9, -9]
                np.savetxt(f_handle, endoffile, fmt='%2d')
                f_handle.close()
        else:
            np.savetxt(data_out, met_save, fmt=numformat, delimiter=' ', header=header, comments='')
            f_handle = file(data_out, 'a')
            endoffile = [-9, -9]
            np.savetxt(f_handle, endoffile, fmt='%2d')
            f_handle.close()

        if qschoice == 4 or qschoice == 14:
            # find start end end of 5 min ts file for each year
            posstart = np.where((ts_new[:, 0] == YYYY) & (ts_new[:, 1] == 1) & (ts_new[:, 2] == 0) & (ts_new[:, 3] == 5))
            posend = np.where((ts_new[:, 0] == YYYY + 1) & (ts_new[:, 1] == 1) & (ts_new[:, 2] == 0) & (ts_new[:, 3] == 0))
            fixpos = 1

            if len(posstart[0]) == 0:
                starting = 0
            else:
                starting = posstart[0]
            if len(posend[0]) == 0:
                ending = ts_new.shape[0]
                fixpos = 0
            else:
                ending = posend[0]

            ts_save = ts_new[starting:ending + fixpos, :]  # originally for one full year

            # save ts-file
            ts_out = fileinputpath + filecode + gridcodeestm + '_' + str(YYYY) + '_ESTM_Ts_data_5.txt'
            tsheader = 'iy id it imin Tiair Tsurf Troof Troad Twall Twall_n Twall_e Twall_s Twall_w'
            tsnumformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f'
            np.savetxt(ts_out, ts_save, fmt=tsnumformat, delimiter=' ', header=tsheader, comments='')
            f_handle = file(ts_out, 'a')
            endoffile = [-9, -9]
            np.savetxt(f_handle, endoffile, fmt='%2d')
            f_handle.close()

        lines = lin[index + 1].split()
        loop_out = lines[0]
        index += 1

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

    # QMessageBox.critical(None, "test", str(goodmetdata))
    if goodmetdata == 1:
        subprocess.call(suewsbat)

    # --- This part makes temporal averages from SUEWS 5 min output --- #

    # Check if 5 min files should be deleted
    KeepTstepFilesIn = nml['runcontrol']['KeepTstepFilesIn']
    KeepTstepFilesOut = nml['runcontrol']['KeepTstepFilesOut']

    # Hard-coded python numformat
    pynumformat = '%4i ' + '%3i ' * 3 + '%8.5f ' +\
        '%9.4f ' * 5 + '%9.4f ' * 7 +\
        '%9.4f ' +\
        '%10.6f ' * 4 +\
        '%10.5f ' * 1 + '%10.6f ' * 3 +\
        '%10.6f ' * 6 +\
        '%9.3f ' * 2 + '%9.4f ' * 4 +\
        '%10.5f ' * 3 + '%14.7g ' * 1 + '%10.5f ' * 1 +\
        '%10.4f ' * 2 + '%10.5f ' * 6 + '%10.5f ' * 7 +\
        '%10.4f ' * 4 +\
        '%10.4f ' * 5 + '%10.6f ' * 6 +\
        '%8.4f' * 1

    header_snow = '%iy  id   it imin dectime SWE_Paved SWE_Bldgs SWE_EveTr SWE_DecTr SWE_Grass SWE_BSoil SWE_Water ' \
                  'Mw_Paved Mw_Bldgs Mw_EveTr Mw_DecTr Mw_Grass Mw_BSoil Mw_Water Qm_Paved Qm_Bldgs Qm_EveTr Qm_DecTr ' \
                  'Qm_Grass Qm_BSoil Qm_Water Qa_Paved Qa_Bldgs Qa_EveTr Qa_DecTr Qa_Grass Qa_BSoil Qa_Water QmFr_Paved ' \
                  'QmFr_Bldgs QmFr_EveTr QmFr_DecTr QmFr_Grass QmFr_BSoil QmFr_Water fr_Paved fr_Bldgs fr_EveTr fr_DecTr ' \
                  'fr_Grass fr_BSoil RainSn_Paved RainSn_Bldgs RainSn_EveTr RainSn_DecTr RainSn_Grass RainSn_BSoil ' \
                  'RainSn_Water Qn_PavedSnow Qn_BldgsSnow Qn_EveTrSnpw Qn_DecTrSnow Qn_GrassSnpw Qn_BSoilSnow ' \
                  'Qn_WaterSnow kup_PavedSnow kup_BldgsSnow kup_EveTrSnpw kup_DecTrSnow kup_GrassSnpw kup_BSoilSnow ' \
                  'kup_WaterSnow frMelt_Paved frMelt_Bldgs frMelt_EveTr frMelt_DecTr frMelt_Grass frMelt_BSoil ' \
                  'frMelt_Water MwStore_Paved MwStore_Bldgs MwStore_EveTr MwStore_DecTr MwStore_Grass MwStore_BSoil ' \
                  'MwStore_Water DensSnow_Paved DensSnow_Bldgs DensSnow_EveTr DensSnow_DecTr DensSnow_Grass ' \
                  'DensSnow_BSoil DensSnow_Water Sd_Paved Sd_Bldgs Sd_EveTr Sd_DecTr Sd_Grass Sd_BSoil Sd_Water ' \
                  'Tsnow_Paved Tsnow_Bldgs Tsnow_EveTr Tsnow_DecTr Tsnow_Grass Tsnow_BSoil Tsnow_Water'

    pynumformat_snow = '%4i ' + '%3i ' * 3 + '%8.5f ' + '%10.4f ' * 97

    header_estm = '%iy id it imin dectime QSNET QSAIR QSWALL QSROOF QSGROUND QSIBLD TWALL1 TWALL2 TWALL3 TWALL4 TWALL5' \
                 ' TROOF1 TROOF2 TROOF3 TROOF4 TROOF5 TGROUND1 TGROUND2 TGROUND3 TGROUND4 TGROUND5 TiBLD1 TiBLD2 ' \
                 'TiBLD3 TiBLD4 TiBLD5 TaBLD'

    pynumformat_estm = '%4i ' + '%3i ' * 3 + '%8.5f ' + '%10.4f ' * 27

    TimeCol = np.array([1, 2, 3, 4, 5]) -1
    SumCol = np.array([19,20,21,22,  25,26, 27,28,29,30,31,32,  33,34,35,36,37,38,  71,72,73]) -1
    LastCol = np.array( [23,24,  44,45,46,47,48,49,50,51,  52,53,54,55,56,57,58,  59,60,61,62,  68,69,70,  74]) -1

    header = '%iy id it imin dectime '\
             'kdown kup ldown lup Tsurf qn h_mod e_mod qs qf qh qe '\
             'qh_r '\
             'P/i Ie/i E/i Dr/i '\
             'St/i NWSt/i surfCh/i totCh/i '\
             'RO/i ROsoil/i ROpipe ROpav ROveg ROwater '\
             'AdditionalWater FlowChange WU_int WU_EveTr WU_DecTr WU_Grass '\
             'ra rs ustar L_Ob Fcld '\
             'SoilSt smd smd_Paved smd_Bldgs smd_EveTr smd_DecTr smd_Grass smd_BSoil '\
             'St_Paved St_Bldgs St_EveTr St_DecTr St_Grass St_BSoil St_Water '\
             'LAI z0m zdm bulkalbedo '\
             'qn1_SF qn1_S Qm QmFreez QmRain SWE Mw MwStore snowRem_Paved snowRem_Bldgs ChSnow/i '\
             'SnowAlb'

    TimeCol_snow = np.array([1, 2, 3, 4, 5]) - 1
    SumCol_snow = np.array([13, 14, 15, 16, 17, 18, 19, 47, 48, 49, 50, 51, 52, 53, 68, 69, 70, 71, 72, 73, 74]) - 1
    LastCol_snow = np.array([6, 7, 8, 9, 10, 11, 12, 62, 75, 76, 77, 78, 79, 80, 81]) - 1

    resolutionfilesout = nml['runcontrol']['resolutionfilesout']
    timeres_min = resolutionfilesout / 60

    for j in range(2, index):
        lines = lin[j].split()
        YYYY = int(lines[1])
        gridcode = lines[0]
        data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
        suews_5min = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
        suews_in = np.loadtxt(suews_5min, skiprows=1)
        suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_' + str(timeres_min) + '.txt'

        # suews_1hour = su.from5minto1hour_v1(suews_in, SumCol, LastCol, TimeCol)
        suews_result = su.from5mintoanytime(suews_in, SumCol, LastCol, TimeCol, timeres_min)
        np.savetxt(suews_out, suews_result, fmt=pynumformat, delimiter=' ', header=header, comments='')

        if qschoice == 4 or qschoice == 14:
            estm_5min = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_ESTM_5.txt'
            estm_in = np.loadtxt(estm_5min, skiprows=1)
            estm_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_ESTM_' + str(timeres_min) + '.txt'
            estm_result = su.from5mintoanytime(estm_in, [], [], TimeCol, timeres_min)
            np.savetxt(estm_out, estm_result, fmt=pynumformat_estm, delimiter=' ', header=header_estm, comments='')

        if snowuse == 1:
            suews_5min_snow = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_snow_5.txt'
            suews_out_snow = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_snow_' + str(timeres_min) + '.txt'
            suews_in_snow = np.loadtxt(suews_5min_snow, skiprows=1)
            suews_1hour_snow = su.from5mintoanytime(suews_in_snow, SumCol_snow, LastCol_snow, TimeCol_snow, timeres_min)
            np.savetxt(suews_out_snow, suews_1hour_snow, fmt=pynumformat_snow, delimiter=' ', header=header_snow, comments='')

        if KeepTstepFilesIn == 0 and multiplemetfiles == 1:
            os.remove(data_out)

        if KeepTstepFilesIn == 0 and multiplemetfiles == 0 and gridcode == gridcodemet:
            os.remove(fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt')

        if KeepTstepFilesOut == 0:
            os.remove(suews_5min)
            if snowuse == 1:
                os.remove(suews_5min_snow)

    # --- plot results --- #
    if nomatplot == 0:
        # read namelist, plot.nml
        plotnml = f90nml.read(pathtoplugin + '/plot.nml')
        plotbasic = plotnml['plot']['plotbasic']
        choosegridbasic = plotnml['plot']['choosegridbasic']
        chooseyearbasic = plotnml['plot']['chooseyearbasic']
        timeaggregation = plotnml['plot']['timeaggregation']
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

            suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
            suews_res = np.loadtxt(suews_out, skiprows=1)

            suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
            suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, timeaggregation)

            pl.plotbasic(suews_plottime, suews_plottimeold)
            # pl.plotbasic(suews_result, met_old)

        if plotmonthlystat == 1:
            if choosegridstat:
                gridcode = choosegridstat

            if chooseyearstat:
                YYYY = chooseyearstat

            suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
            suews_res = np.loadtxt(suews_out, skiprows=1)

            suews_plottime = su.from5mintoanytime(suews_res, SumCol, LastCol, TimeCol, timeaggregation)
            suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, timeaggregation)

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



def metdatacheck(met_new):
    goodmetdata = 1
    # Met variables
    testwhere = np.where((met_new[:, 14] < 0.0) | (met_new[:, 14] > 1200.0))
    if testwhere[0].__len__() > 0:
        QMessageBox.critical(None, "Value error", "Kdown - beyond what is expected at line:"
                                                  " \n" + str(testwhere[0] + 1))
        goodmetdata = 0

    testwhere = np.where((met_new[:, 9] <= 0) | (met_new[:, 9] > 60.0))
    if testwhere[0].__len__() > 0:
        QMessageBox.critical(None, "Value error", "Wind speed - beyond what is expected at line:"
                                                  " \n" + str(testwhere[0] + 1))
        goodmetdata = 0

    testwhere = np.where((met_new[:, 11] < -30.0) | (met_new[:, 11] > 55.0))
    if testwhere[0].__len__() > 0:
        QMessageBox.critical(None, "Value error", "Air temperature - beyond what is expected at line:"
                                                  " \n" + str(testwhere[0] + 1))
        goodmetdata = 0

    testwhere = np.where((met_new[:, 10] < 0.00) | (met_new[:, 10] > 100.0))
    if testwhere[0].__len__() > 0:
        QMessageBox.critical(None, "Value error", "Relative humidity - beyond what is expected at line:"
                                                  " \n" + str(testwhere[0] + 1))
        goodmetdata = 0

    testwhere = np.where((met_new[:, 12] < 70.0) | (met_new[:, 12] > 107.0))
    if testwhere[0].__len__() > 0:
        QMessageBox.critical(None, "Value error", "Pressure - beyond what is expected at line:"
                                                  " \n" + str(testwhere[0] + 1))
        goodmetdata = 0

    testwhere = np.where((met_new[:, 13] < 0.0) | (met_new[:, 13] > 30.0))
    if testwhere[0].__len__() > 0:
        QMessageBox.critical(None, "Value error", "Rain - beyond what is expected at line:"
                                                  " \n" + str(testwhere[0] + 1))
        goodmetdata = 0

    return goodmetdata

    # testwhere = np.where((met_new[:, 15] < 0.0) | (met_new[:, 15] > 300.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Snow - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     good = 0
    #     return good
    #
    # testwhere = np.where((met_new[:, 16] < 100.0) | (met_new[:, 16] > 600.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Ldown - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 17] < 0.0) | (met_new[:, 17] > 1.01))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Fraction of cloud - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 18] < 0.0) | (met_new[:, 18] > 10.01))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "External water use - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 19] < 0.01) | (met_new[:, 19] > 0.5))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Soil moisture - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 20] < 0.0) | (met_new[:, 20] > 15.01))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Leaf area index - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #
    # testwhere = np.where((met_new[:, 21] < 0.0) | (met_new[:, 21] > 600.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error",
    #                          "Diffuse shortwave radiation - beyond what is expected at line:"
    #                          " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 22] < 0.0) | (met_new[:, 22] > 1200.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error",
    #                          "Direct shortwave radiation - beyond what is expected at line:"
    #                          " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 23] < 0.0) | (met_new[:, 23] > 360.01))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Wind directions - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 4] < -200.0) | (met_new[:, 4] > 800.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Net radiation - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 5] < -200.0) | (met_new[:, 5] > 750.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Sensible heat flux - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 6] < -100.0) | (met_new[:, 6] > 650.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Latent heat flux - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 7] < -200.0) | (met_new[:, 7] > 650.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error", "Storage heat flux - beyond what is expected at line:"
    #                                               " \n" + str(testwhere[0] + 1))
    #     return
    #
    # testwhere = np.where((met_new[:, 8] < 0.0) | (met_new[:, 8] > 1500.0))
    # if testwhere[0].__len__() > 0:
    #     QMessageBox.critical(None, "Value error",
    #                          "Anthropogenic heat flux - beyond what is expected at line:"
    #                          " \n" + str(testwhere[0] + 1))
    #     return


    # Plot for water related variables
    # precip = (suews_1hour[:, 17])  #Precipitation (P/i)
    # wu = (suews_1hour[:, 18])  # exteranl wu (Ie/i)
    # st = (suews_1hour[:, 24])  #storage (totCh/i)
    # evap = (suews_1hour[:, 19])  #Evaporation (E/i)
    # drain= (suews_1hour[:, 25]) #runoff (RO/i)
    #
    # plt.figure(2, figsize=(15, 7), facecolor='white')
    # ax1 = plt.subplot(3, 1, 1)
    # ax1.plot(precip + wu)
    # ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    # ax2.plot(st, label='$\Delta S$')
    # ax2.plot(drain, label='$R$')
    # ax2.plot(evap, label='$E$')
    # plt.legend(bbox_to_anchor=(1.0, 1.0))
    # ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    # ax3.plot(precip + wu - st - drain - evap)
    # plt.show()

    # TODO: This part will read info from SUEWS_Output.f95 to e.g. convert f90 numformat to python. Not ready yet.
    # open SUEWS_output.f95 to get format and header of output file
    # SiteIn = wf + '/SUEWS_Output.f95'
    # f = open(SiteIn)
    # lin2 = f.readlines()
    #
    # for i in range(0,lin2.__len__()):
    #     timeline = lin2[i].find('TimeCol')
    #     sumline = lin2[i].find('SumCol')
    #     lastline = lin2[i].find('LastCol')
    #
    #     if timeline > -1:
    #         TimeCo = lin2[i][lin2[i].find('[') + 1:lin2[i].find(']')]
    #         TimeCol = [int(k) for k in TimeCo.split(',')]
    #     if sumline > -1:
    #         SumCo = lin2[i][lin2[i].find('[') + 1:lin2[i].find(']')]
    #         SumCol = [int(k) for k in SumCo.split(',')]
    #     if lastline > -1:
    #         LastCo = lin2[i][lin2[i].find('[') + 1:lin2[i].find(']')]
    #         LastCol = [int(k) for k in LastCo.split(',')]
    #
    # TimeCol = np.array(TimeCol) - 1
    # SumCol = np.array(SumCol) - 1
    # LastCol = np.array(LastCol) - 1
    #
    # headerline = lin2[i].find('110 format')
    # if headerline > -1:
    #     headstart = i
    #
    # formatline = lin2[i].find('301 format')
    # if formatline > -1:
    #     formatstart = i
    #
    # first = 1
    # formend = 0
    # pynumformat = ""
    # while formend == 0:
    #     if first == 1:
    #         sta = lin2[formatstart].find("((")
    #         first =
    #
    #     sta = lin2[formatstart].find("'")
    #     end = lin2[formatstart].rfind("+")
    #     block = lin2[formatstart][sta + 1:end]
    #     stop = lin2[formatstart].find(")")
    #     # skip = lin2[formatstart].find("!")
    #     # if skip > -1:
    #     #     if skip > sta:
    #     #         pynumformat = pynumformat + block
    #     # else:
    #     pynumformat = pynumformat + block
    #     if stop == -1:
    #         formatstart += 1
    #     else:
    #         formend = 1
    #
    # formend = 0
    # pynumformat = ""
    # while formend == 0:
    #     sta = lin2[formatstart].find("'")
    #     end = lin2[formatstart].rfind("+")
    #     block = lin2[formatstart][sta + 1:end]
    #     stop = lin2[formatstart].find(")")
    #     # skip = lin2[formatstart].find("!")
    #     # if skip > -1:
    #     #     if skip > sta:
    #     #         pynumformat = pynumformat + block
    #     # else:
    #     pynumformat = pynumformat + block
    #     if stop == -1:
    #         formatstart += 1
    #     else:
    #         formend = 1
    #
    # headend = 0
    # header = ""
    # while headend == 0:
    #     sta = lin2[headstart].find("'")
    #     end = lin2[headstart].rfind("'")
    #     block = lin2[headstart][sta + 1:end]
    #     stop = lin2[headstart].find(")")
    #     skip = lin2[headstart].find("!")
    #     if skip > -1:
    #         if skip > sta:
    #             header = header + block
    #     else:
    #         header = header + block
    #     if stop == -1:
    #         headstart += 1
    #     else:
    #         headend = 1




