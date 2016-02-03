__author__ = 'xlinfr'


def wrapper(pathtoplugin):

    import numpy as np
    import suewsdataprocessing_v3
    import suewsplotting_v1
    import subprocess
    import f90nml
    import os
    import sys
    import stat
    sys.path.append(pathtoplugin)

    try:
        import matplotlib.pyplot as plt
        nomatplot = 0
    except ImportError:
        #raise ImportError('<any message you want here>')
        nomatplot = 1
        pass

    su = suewsdataprocessing_v3.SuewsDataProcessing()
    pl = suewsplotting_v1.SuewsPlotting()

    # read namelist, Runcontrol.nml
    nml = f90nml.read(pathtoplugin + '/RunControl.nml')
    fileinputpath = nml['runcontrol']['fileinputpath']
    fileoutputpath = nml['runcontrol']['fileoutputpath']
    filecode = nml['runcontrol']['filecode']
    multiplemetfiles = nml['runcontrol']['multiplemetfiles']
    snowuse = nml['runcontrol']['snowuse']

    # Working folder
    #wf = os.getcwd()
    if not os.path.exists(fileoutputpath):
        os.mkdir(fileoutputpath)
    wf = pathtoplugin
    prog_name = 'SUEWS_V2015a'
    # fileinputpath = wf + fileoutputpath[1:] # comment out in UMEP version
    ### open SiteSelect to get year and gridnames
    SiteIn = fileinputpath + 'SUEWS_SiteSelect.txt'
    f = open(SiteIn)
    lin = f.readlines()
    index = 2
    loop_out = ''
    YYYY_old = -9876
    while loop_out != '-9':
        lines = lin[index].split()
        YYYY = int(lines[1])

        ### Create 5 min file
        if multiplemetfiles == 0: # one metfile
            if index == 2:
                gridcode1 = lines[0]
                data_in = fileinputpath + filecode + '_data.txt' # No grid code in the name, nov 2015
                met_old = np.loadtxt(data_in, skiprows=1)
                if met_old[1, 3] - met_old[0, 3] == 5:
                    met_new = met_old
                else:
                    met_new = su.tofivemin_v1(met_old)
        else:  # multiple metfiles
            if index == 2:
                gridcode1 = lines[0]
                data_in = fileinputpath + filecode + gridcode1 + '_data.txt'
                met_old = np.loadtxt(data_in, skiprows=1)
                if met_old[1, 3] - met_old[0, 3] == 5:
                    met_new = met_old
                else:
                    met_new = su.tofivemin_v1(met_old)
            else:
                gridcode2 = lines[0]
                if gridcode2 != gridcode1:
                    gridcode1 = gridcode2
                    data_in = fileinputpath + filecode + gridcode1 + '_data.txt'
                    met_old = np.loadtxt(data_in, skiprows=1)
                    if met_old[1, 3] - met_old[0, 3] == 5:
                        met_new = met_old
                    else:
                        met_new = su.tofivemin_v1(met_old)

        ### find start end end of 5 min file for each year
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

        met_save = met_new[starting:ending + fixpos, :]  ## originally for one full year

        ### save file
        data_out = fileinputpath + filecode + gridcode1 + '_' + str(YYYY) + '_data_5.txt'
        header = 'iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow ldown fcld wuh xsmd lai kdiff kdir wdir'
        numformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.4f %6.2f %6.2f %6.2f %6.2f ' \
                    '%6.4f %6.2f %6.2f %6.2f %6.2f %6.2f'
        np.savetxt(data_out, met_save, fmt=numformat, delimiter=' ', header=header, comments='')
        f_handle = file(data_out, 'a')
        endoffile = [-9, -9]
        np.savetxt(f_handle, endoffile, fmt='%2d')
        f_handle.close()

        lines = lin[index + 1].split()
        loop_out = lines[0]
        index += 1

    ### This part runs the model ###
    pf = sys.platform
    suewsstring1 = 'cd ' + os.path.dirname(os.path.abspath(__file__)) + '\n'

        ### This part runs the model ###
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
        st2 = os.stat(wf + '/SUEWS_V2015a')
        os.chmod(wf + '/SUEWS_V2015a', st2.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    f.write(suewsstring0)
    f.write(suewsstring1)
    f.write(suewsstring2)
    f.close()

    if pf == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    subprocess.call(suewsbat)

    ### This part makes hourly averages from SUEWS 5 min output ###

    ### Delete 5 min files
    KeepTstepFilesIn = nml['runcontrol']['KeepTstepFilesIn']
    KeepTstepFilesOut = nml['runcontrol']['KeepTstepFilesOut']

    ## open SUEWS_output.f95 to get format and header of output file NOT READY
    SiteIn = wf + '/SUEWS_Output.f95'
    f = open(SiteIn)
    lin2 = f.readlines()

    for i in range(0,lin2.__len__()):
        timeline = lin2[i].find('TimeCol')
        sumline = lin2[i].find('SumCol')
        lastline = lin2[i].find('LastCol')

        if timeline > -1:
            TimeCo = lin2[i][lin2[i].find('[') + 1:lin2[i].find(']')]
            TimeCol = [int(k) for k in TimeCo.split(',')]
        if sumline > -1:
            SumCo = lin2[i][lin2[i].find('[') + 1:lin2[i].find(']')]
            SumCol = [int(k) for k in SumCo.split(',')]
        if lastline > -1:
            LastCo = lin2[i][lin2[i].find('[') + 1:lin2[i].find(']')]
            LastCol = [int(k) for k in LastCo.split(',')]

        headerline = lin2[i].find('110 format')
        if headerline > -1:
            headstart = i

        formatline = lin2[i].find('301 format')
        if formatline > -1:
            formatstart = i

    # first = 1
    # formend = 0
    # pynumformat = ""
    # while formend == 0:
    #     if first == 1:
    #         sta = lin2[formatstart].find("((")
    #         first =
    #
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

    pynumformat = '%4i ' + '%3i ' * 3 + '%8.5f ' +\
    '%9.4f ' * 5  + '%9.4f ' * 7 +\
    '%10.6f ' * 4 +\
    '%10.5f ' * 1 + '%10.6f ' * 3 +\
    '%10.6f ' * 6 +\
    '%9.3f ' * 2  + '%9.4f ' * 4 +\
    '%10.5f ' * 3 + '%14.7g ' * 1 + '%10.5f ' * 1 +\
    '%10.4f ' * 2 + '%10.5f ' * 6 + '%10.5f ' * 7 +\
    '%10.4f ' * 3 +\
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

    TimeCol = np.array(TimeCol) - 1
    SumCol = np.array(SumCol) - 1
    LastCol = np.array(LastCol) - 1
    # TimeCol = np.array([1, 2, 3, 4, 5]) - 1
    # SumCol = np.array([18, 19, 20, 21, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 67, 68, 69]) - 1
    # LastCol = np.array([22, 23, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 64, 65, 66, 70]) - 1

    headend = 0
    header = ""
    while headend == 0:
        sta = lin2[headstart].find("'")
        end = lin2[headstart].rfind("'")
        block = lin2[headstart][sta + 1:end]
        stop = lin2[headstart].find(")")
        skip = lin2[headstart].find("!")
        if skip > -1:
            if skip > sta:
                header = header + block
        else:
            header = header + block
        if stop == -1:
            headstart += 1
        else:
            headend = 1

    header = '%iy id it imin dectime ' \
             'kdown kup ldown lup Tsurf qn h_mod e_mod qs QF QH QE ' \
             'P/i Ie/i E/i Dr/i ' \
             'St/i NWSt/i surfCh/i totCh/i ' \
             'RO/i ROsoil/i ROpipe ROpav ROveg ROwater ' \
             'AdditionalWater FlowChange WU_int WU_EveTr WU_DecTr WU_Grass ' \
             'RA RS ustar L_mod Fcld ' \
             'SoilSt smd smd_Paved smd_Bldgs smd_EveTr smd_DecTr smd_Grass smd_BSoil ' \
             'St_Paved St_Bldgs St_EveTr St_DecTr St_Grass St_BSoil St_Water ' \
             'LAI z0m zdm ' \
             'qn1_SF qn1_S Qm QmFreez Qmrain SWE Mw MwStore snowRem_Paved snowRem_Bldgs ChSnow/i ' \
             'SnowAlb '

    TimeCol_snow = np.array([1, 2, 3, 4, 5]) - 1
    SumCol_snow = np.array([13, 14, 15, 16, 17, 18, 19, 47, 48, 49, 50, 51, 52, 53, 68, 69, 70, 71, 72, 73, 74]) - 1
    LastCol_snow = np.array([6, 7, 8, 9, 10, 11, 12, 75, 76, 77, 78, 79, 80, 81]) - 1

    for j in range(2, index):
        lines = lin[j].split()
        YYYY = int(lines[1])
        gridcode = lines[0]
        data_out = fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt'
        suews_5min = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_5.txt'
        suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_60.txt'
        suews_in = np.loadtxt(suews_5min, skiprows=1)
        suews_1hour = su.from5minto1hour_v1(suews_in, SumCol, LastCol, TimeCol)
        np.savetxt(suews_out, suews_1hour, fmt=pynumformat, delimiter=' ', header=header, comments='')  #, fmt=numformat

        if snowuse == 1:
            suews_5min_snow = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_snow_5.txt'
            suews_out_snow = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_snow_60.txt'
            suews_in_snow = np.loadtxt(suews_5min_snow, skiprows=1)
            suews_1hour_snow = su.from5minto1hour_v1(suews_in_snow, SumCol_snow, LastCol_snow, TimeCol_snow)
            np.savetxt(suews_out_snow, suews_1hour_snow, fmt=pynumformat_snow, delimiter=' ', header=header_snow, comments='')  #, fmt=numformat

        if KeepTstepFilesIn == 0 and multiplemetfiles==1:
            os.remove(data_out)

        if KeepTstepFilesIn == 0 and multiplemetfiles == 0 and gridcode==gridcode1:
            os.remove(fileinputpath + filecode + gridcode + '_' + str(YYYY) + '_data_5.txt')

        if KeepTstepFilesOut == 0:
            os.remove(suews_5min)
            if snowuse == 1:
                os.remove(suews_5min_snow)

    if nomatplot == 0:
        ### plot results ###
        # read namelist, plot.nml
        plotnml = f90nml.read(pathtoplugin + '/plot.nml')
        plotbasic = plotnml['plot']['plotbasic']
        choosegridbasic = plotnml['plot']['choosegridbasic']
        chooseyearbasic = plotnml['plot']['chooseyearbasic']
        plotmonthlystat = plotnml['plot']['plotmonthlystat']
        choosegridstat = plotnml['plot']['choosegridstat']
        chooseyearstat = plotnml['plot']['chooseyearstat']

        if plotbasic == 1:
            if choosegridbasic:
                gridcode = choosegridbasic

            if chooseyearbasic:
                YYYY = chooseyearbasic

            suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_60.txt'

            if chooseyearbasic or choosegridbasic:
                suews_1hour = np.loadtxt(suews_out, skiprows=1)

            pl.plotbasic(suews_1hour, met_old)

        if plotmonthlystat == 1:
            if choosegridstat:
                gridcode = choosegridstat

            if chooseyearstat:
                YYYY = chooseyearstat

            suews_out = fileoutputpath + filecode + gridcode + '_' + str(YYYY) + '_60.txt'

            if chooseyearbasic or choosegridbasic:
                suews_1hour = np.loadtxt(suews_out, skiprows=1)

            pl.plotmonthlystatistics(suews_1hour, met_old)


        if plotmonthlystat == 1:
            plt.show()

        if plotbasic == 1:   # or plotmonthlystat == 1
            plt.show()
    else:
        print("No plots generated - No matplotlib installed")

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



