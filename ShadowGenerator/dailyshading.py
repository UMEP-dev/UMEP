import datetime as dt
from builtins import range

from ..Utilities import shadowingfunctions as shadow
from ..Utilities.SEBESOLWEIGCommonFiles.shadowingfunction_wallheight_13 import shadowingfunction_wallheight_13
from ..Utilities.SEBESOLWEIGCommonFiles.shadowingfunction_wallheight_23 import shadowingfunction_wallheight_23
from ..Utilities.misc import *
from ..Utilities.SEBESOLWEIGCommonFiles import sun_position as sp


def dailyshading(dsm, vegdsm, vegdsm2, scale, lon, lat, sizex, sizey, tv, UTC, usevegdem, timeInterval, onetime, dlg, folder, gdal_data, trans, dst, wallshadow, wheight, waspect):

    # lon = lonlat[0]
    # lat = lonlat[1]
    year = tv[0]
    month = tv[1]
    day = tv[2]

    alt = np.median(dsm)
    location = {'longitude': lon, 'latitude': lat, 'altitude': alt}
    if usevegdem == 1:
        psi = trans
        # amaxvalue
        vegmax = vegdsm.max()
        amaxvalue = dsm.max() - dsm.min()
        amaxvalue = np.maximum(amaxvalue, vegmax)

        # Elevation vegdsms if buildingDSM includes ground heights
        vegdem = vegdsm + dsm
        vegdem[vegdem == dsm] = 0
        vegdem2 = vegdsm2 + dsm
        vegdem2[vegdem2 == dsm] = 0

        # Bush separation
        bush = np.logical_not((vegdem2*vegdem))*vegdem

    #     vegshtot = np.zeros((sizex, sizey))
    # else:
        
    shtot = np.zeros((sizex, sizey))

    if onetime == 1:
        itera = 1
    else:
        itera = int(np.round(1440 / timeInterval))

    alt = np.zeros(itera)
    azi = np.zeros(itera)
    hour = int(0)
    index = 0
    time = dict()
    time['UTC'] = UTC

    if wallshadow == 1:
        walls = wheight
        dirwalls = waspect
    else: 
        walls = np.zeros((sizex, sizey))
        dirwalls = np.zeros((sizex, sizey))

    for i in range(0, itera):
        if onetime == 0:
            minu = int(timeInterval * i)
            if minu >= 60:
                hour = int(np.floor(minu / 60))
                minu = int(minu - hour * 60)
        else:
            minu = tv[4]
            hour = tv[3]
        
        doy = day_of_year(year, month, day)

        ut_time = doy - 1. + ((hour - dst) / 24.0) + (minu / (60. * 24.0)) + (0. / (60. * 60. * 24.0))
        
        if ut_time < 0:
            year = year - 1
            month = 12
            day = 31
            doy = day_of_year(year, month, day)
            ut_time = ut_time + doy - 1

        HHMMSS = dectime_to_timevec(ut_time)
        
        time['year'] = year
        time['month'] = month
        time['day'] = day
        time['hour'] = HHMMSS[0]
        time['min'] = HHMMSS[1]
        time['sec'] = HHMMSS[2]

        sun = sp.sun_position(time, location)
        alt[i] = 90. - sun['zenith']
        azi[i] = sun['azimuth']

        if time['sec'] == 59: #issue 228 and 256
            time['sec'] = 0
            time['min'] = time['min'] + 1
            if time['min'] == 60:
                time['min'] = 0
                time['hour'] = time['hour'] + 1
                if time['hour'] == 24:
                    time['hour'] = 0

        time_vector = dt.datetime(year, month, day, time['hour'], time['min'], time['sec'])
        timestr = time_vector.strftime("%Y%m%d_%H%M")

        if alt[i] > 0:
            if wallshadow == 1: # Include wall shadows (Issue #121)
                if usevegdem == 1:
                    vegsh, sh, _, wallsh, _, wallshve, _, _ = shadowingfunction_wallheight_23(dsm, vegdem, vegdem2,
                                                azi[i], alt[i], scale, amaxvalue, bush, walls, dirwalls * np.pi / 180.)
                    sh = sh - (1 - vegsh) * (1 - psi)
                    if onetime == 0:
                        filenamewallshve = folder + '/Facadeshadow_fromvegetation_' + timestr + '_LST.tif'
                        saveraster(gdal_data, filenamewallshve, wallshve)
                else:
                    sh, wallsh, _, _, _ = shadowingfunction_wallheight_13(dsm, azi[i], alt[i], scale,
                                                                                        walls, dirwalls * np.pi / 180.)
                    # shtot = shtot + sh
                
                if onetime == 0:
                    filename = folder + '/Shadow_ground_' + timestr + '_LST.tif'
                    saveraster(gdal_data, filename, sh)
                    filenamewallsh = folder + '/Facadeshadow_frombuilding_' + timestr + '_LST.tif'
                    saveraster(gdal_data, filenamewallsh, wallsh)
                    

            else:
                if usevegdem == 0:
                    sh = shadow.shadowingfunctionglobalradiation(dsm, azi[i], alt[i], scale, dlg, 0)
                    # shtot = shtot + sh
                else:
                    shadowresult = shadow.shadowingfunction_20(dsm, vegdem, vegdem2, azi[i], alt[i], scale, amaxvalue,
                                                            bush, dlg, 0)
                    vegsh = shadowresult["vegsh"]
                    sh = shadowresult["sh"]
                    sh=sh-(1-vegsh)*(1-psi)
                    # vegshtot = vegshtot + sh

                if onetime == 0:
                    filename = folder + '/Shadow_' + timestr + '_LST.tif'
                    saveraster(gdal_data, filename, sh)

            shtot = shtot + sh
            index += 1

    shfinal = shtot / index

    if wallshadow == 1:
        if onetime == 1:
            filenamewallsh = folder + '/Facadeshadow_frombuilding_' + timestr + '_LST.tif'
            saveraster(gdal_data, filenamewallsh, wallsh)
            if usevegdem == 1:
                filenamewallshve = folder + '/Facadeshadow_fromvegetation_' + timestr + '_LST.tif'
                saveraster(gdal_data, filenamewallshve, wallshve)

    shadowresult = {'shfinal': shfinal, 'time_vector': time_vector}

    dlg.progressBar.setValue(0)

    return shadowresult

def day_of_year(yy, month, day):
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

    if leapyear == 1:
        dayspermonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    else:
        dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    doy = np.sum(dayspermonth[0:month-1]) + day

    return doy


def dectime_to_timevec(dectime):
    # This subroutine converts dectime to individual hours, minutes and seconds

    doy = np.floor(dectime)

    DH = dectime-doy
    HOURS = int(24 * DH)

    DM=24*DH - HOURS
    MINS=int(60 * DM)

    DS = 60 * DM - MINS
    SECS = int(60 * DS)

    return (HOURS, MINS, SECS)
