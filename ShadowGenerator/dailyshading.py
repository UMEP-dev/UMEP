__author__ = 'xlinfr'
from ..Utilities import shadowingfunctions as shadow
# import Pysolarn.solar as pys
from ..Utilities import Pysolarn as pys
import datetime as dt
from PyQt4.QtGui import *
from ..Utilities.misc import *
# import numpy as np


def dailyshading(dsm, vegdsm, vegdsm2, scale, lonlat, sizex, sizey, tv, UTC, usevegdem, timeInterval, onetime, dlg, folder, gdal_data, trans):

    lon = lonlat[0]
    lat = lonlat[1]
    year = tv[0]
    month = tv[1]
    day = tv[2]

    if usevegdem == 1:
        psi = trans
        # amaxvalue
        vegmax = vegdsm.max()
        amaxvalue = dsm.max()
        amaxvalue = np.maximum(amaxvalue,vegmax)

        # Elevation vegdsms if buildingDEM includes ground heights
        vegdem = vegdsm+dsm
        vegdem[vegdem == dsm] = 0
        vegdem2 = vegdsm2+dsm
        vegdem2[vegdem2 == dsm] = 0

        #% Bush separation
        bush = np.logical_not((vegdem2*vegdem))*vegdem

        vegshtot = np.zeros((sizex, sizey))
    else:
        shtot = np.zeros((sizex, sizey))

    if onetime == 1:
        itera = 1
    else:
        itera = int(1440 / timeInterval)

    alt = np.zeros(itera)
    azi = np.zeros(itera)
    hour = int(0)
    index = 0
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

        ut_time = doy - 1 + ((hour - UTC) / 24.0) + (minu / (60 * 24.0)) + (0 / (60 * 60 * 24.0))

        if ut_time < 0:
            year = year - 1
            month = 12
            day = 31
            doy = day_of_year(year, month, day)
            ut_time = ut_time + doy - 1

        HHMMSS = dectime_to_timevec(ut_time)

        time_vector = dt.datetime(year, month, day, HHMMSS[0], HHMMSS[1], HHMMSS[2])
        alt[i] = pys.GetAltitude(lat, lon, time_vector, 0)
        if onetime == 1:
            if alt[i] < 0:
                QMessageBox.critical(None, "Sun altitude below zero", "No shadow grid generated. Try again...")
                return # THIS NEEDS FIXING. THE CODE DOESNT STOP

        azi[i] = abs(pys.GetAzimuth(lat, lon, time_vector, 0)) - 180
        if azi[i] < 0:
            azi[i] = azi[i] + 360

        if alt[i] > 0:
            if usevegdem == 0:
                sh = shadow.shadowingfunctionglobalradiation(dsm, azi[i], alt[i], scale, dlg, 0)
                shtot = shtot + sh

            else:
                shadowresult = shadow.shadowingfunction_20(dsm, vegdem, vegdem2, azi[i], alt[i], scale, amaxvalue, bush, dlg,0)
                vegsh = shadowresult["vegsh"]
                sh = shadowresult["sh"]
                sh=sh-(1-vegsh)*(1-psi)
                vegshtot = vegshtot + sh

            if onetime == 0:
                timestr = time_vector.strftime("%Y%m%d_%H%M")
                filename = folder + '/shadow_' + timestr + '.tif'
                saveraster(gdal_data, filename, sh)

            index += 1

    if usevegdem == 1:
        shfinal = vegshtot / index
    else:
        shfinal = shtot / index

    shadowresult = {'shfinal': shfinal, 'time_vector': time_vector}

    return shadowresult


# def saveraster(gdal_data, filename, raster):
#     rows = gdal_data.RasterYSize
#     cols = gdal_data.RasterXSize
#
#     # outDs = gdal.GetDriverByName("GTiff").Create(folder + 'shadow' + tv + '.tif', cols, rows, int(1), GDT_Float32)
#     outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
#     # outDs = gdal.GetDriverByName(gdal_data.GetDriver().LongName).Create(filename, cols, rows, int(1), GDT_Float32)
#     outBand = outDs.GetRasterBand(1)
#
#     # write the data
#     outBand.WriteArray(raster, 0, 0)
#     # flush data to disk, set the NoData value and calculate stats
#     outBand.FlushCache()
#     outBand.SetNoDataValue(-9999)
#
#     # georeference the image and set the projection
#     outDs.SetGeoTransform(gdal_data.GetGeoTransform())
#     outDs.SetProjection(gdal_data.GetProjection())
#
#     del outDs, outBand


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
    #This subroutine converts dectime to individual
    #hours, minutes and seconds

    doy = np.floor(dectime)

    DH = dectime-doy
    HOURS = int(24 * DH)

    DM=24*DH - HOURS
    MINS=int(60 * DM)

    DS = 60 * DM - MINS
    SECS = int(60 * DS)

    return (HOURS, MINS, SECS)