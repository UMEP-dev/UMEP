from __future__ import division

from PyQt4 import QtCore, QtGui
import traceback
# from SEBEfiles import SEBE_2015a_calc
import numpy as np
# from SEBEfiles.shadowingfunction_wallheight_13 import shadowingfunction_wallheight_13
from SEBEfiles.shadowingfunction_wallheight_mr import shadowingfunction_wallheight_13
from SEBEfiles.shadowingfunction_wallheight_23 import shadowingfunction_wallheight_23

from SEBEfiles.diffusefraction import diffusefraction
from SEBEfiles.Perez_v3 import Perez_v3
from SEBEfiles.clearnessindex_2013b import clearnessindex_2013b

# from ..Utilities import shadowingfunctions as shadow
import linecache
import sys

#from osgeo import gdal
#from osgeo.gdalconst import *


class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex, vegdsm, vegdsm2,
                        wheight, waspect, albedo_raster, albedo, psi, metdata, altitude, azimuth, onlyglobal, output, jday, location,
                        zen, usevegdem, calc_month, dlg, pvm, tcel, output_folder):
        QtCore.QObject.__init__(self)
        self.killed = False

        self.dsm = dsm
        self.scale = scale
        self.building_slope = building_slope
        self.building_aspect = building_aspect
        self.voxelheight = voxelheight
        self.sizey = sizey
        self.sizex = sizex
        self.vegdsm = vegdsm
        self.vegdsm2 = vegdsm2
        self.wheight = wheight
        self.waspect = waspect
        self.albedo_array = albedo_raster
        self.albedo = albedo
        self.psi = psi
        # self.radmatI = radmatI
        # self.radmatD = radmatD
        # self.radmatR = radmatR
        self.metdata = metdata
        self.altitude = altitude
        self.azimuth = azimuth
        self.onlyglobal = onlyglobal
        self.output = output
        self.jday = jday
        self.location = location
        self.zen = zen
        self.usevegdem = usevegdem
        self.calc_month = calc_month
        self.dlg = dlg
        self.pvm = pvm
        self.tcel = tcel
        self.outputfolder = output_folder

    def run(self):
        ret = None
        try:
            dsm = self.dsm
            scale = self.scale
            slope = self.building_slope
            aspect = self.building_aspect
            voxelheight = self.voxelheight
            sizey = self.sizey
            sizex = self.sizex
            vegdem = self.vegdsm
            vegdem2 = self.vegdsm2
            walls = self.wheight
            dirwalls = self.waspect
            albedo_array = self.albedo_array
            albedo = self.albedo
            psi = self.psi
            # radmatI = self.radmatI
            # radmatD = self.radmatD
            # radmatR = self.radmatR
            met = self.metdata
            altitude = self.altitude
            azimuth = self.azimuth
            onlyglobal = self.onlyglobal
            output = self.output
            jday = self.jday
            location = self.location
            zen = self.zen
            usevegdem = self.usevegdem
            calc_month = self.calc_month
            #energymonth = output['energymonth']

            # Parameters
            deg2rad = np.pi/180
            Knight = np.zeros((sizex, sizey))
            Energyyearroof = np.copy(Knight)    # total irradiance on ground/roof
            EnergyyearroofI = np.copy(Knight)   # direct sun irradiance on ground/roof
            EnergyyearroofD = np.copy(Knight)   # diffuse sky irradiance on ground/roof
            EnergyyearroofR = np.copy(Knight)   # ground reflected irradiance on ground/roof

            dectime = met[:, 1] * 24 + met[:, 2] + met[:, 3] / 60.   # time stamp in units of hour (excluding year)
            # print(dectime)

            # TODO: Month calculation is not prepared
            # if calc_month:
            #     # Energymonthroof = np.zeros(sizey, sizex, 12)
            #     Energymonthroof = np.array([])
            # else:
            #     Energymonthroof = np.array([])

            if usevegdem == 1:
                # amaxvalue
                vegmax = vegdem.max()
                amaxvalue = dsm.max() - dsm.min()
                amaxvalue = np.maximum(amaxvalue, vegmax)

                # Elevation vegdsms if buildingDEM includes ground heights
                vegdem = vegdem+dsm
                vegdem[vegdem == dsm] = 0
                vegdem2 = vegdem2+dsm
                vegdem2[vegdem2 == dsm] = 0

                # Bush separation
                bush = np.logical_not((vegdem2*vegdem))*vegdem
            else:
                psi = 1

            # Creating wallmatrix
            wallcol, wallrow = np.where(np.transpose(walls) > 0)    # row (y) and col (x) for each wall pixel
            wallstot = np.floor(walls*(1/voxelheight)) * voxelheight
            wallsections = np.floor(np.max(walls) * (1/voxelheight))     # finding tallest wall
            wallmatrix = np.zeros((np.shape(wallrow)[0], np.int(wallsections)))
            Energyyearwall = np.copy(wallmatrix)    # total irradiance on walls
            EnergyyearwallI = np.copy(wallmatrix)   # direct sun irradiance on walls
            EnergyyearwallD = np.copy(wallmatrix)   # diffuse sky irradiance on walls
            EnergyyearwallR = np.copy(wallmatrix)   # ground reflected irradiance on walls
            # Energymonthwall = np.zeros(np.shape(wallmatrix[0]), np.shape(wallmatrix[1]), 12)

            # commented out MRevesz
            #  Main loop - Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
            # skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
            # aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])

            if usevegdem == 1:
                wallshve = np.zeros(np.shape(dsm))
                vegrow, vegcol = np.where(vegdem > 0)    # row and col for each veg pixel
                vegdata = np.zeros((np.shape(vegrow)[0], 3))
                for i in range(0, vegrow.shape[0] - 1):
                    vegdata[i, 0] = vegrow[i] + 1
                    vegdata[i, 1] = vegcol[i] + 1
                    vegdata[i, 2] = vegdem[vegrow[i], vegcol[i]]
            else:
                vegdata = 0

            # copied from sunmapcreator (MRevesz):
            np.seterr(over='raise')
            np.seterr(invalid='raise')
            # Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
            skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
            skyvaultaziint = np.array([12, 12, 15, 15, 20, 30, 60, 360])
            aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])
            azistart = np.array([0, 4, 2, 5, 8, 0, 10, 0])
            # annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])
            skyvaultazi = np.array([])
            for j in range(8):
                for k in range(1, int(360 / skyvaultaziint[j]) + 1):
                    skyvaultazi = np.append(skyvaultazi, k * skyvaultaziint[j] + azistart[j])
                    if skyvaultazi[-1] > 360:
                        skyvaultazi[-1] = skyvaultazi[-1] - 360

            iangle2 = np.array([])
            Gyear = 0
            Dyear = 0
            Gmonth = np.zeros([1, 12])
            Dmonth = Gmonth
            for j in range(len(aziinterval)):
                iangle2 = np.append(iangle2, skyvaultaltint[j] * np.ones([1, aziinterval[j]]))

            # Ta = met[:, 11]
            # RH = met[:, 10]

            # run shadow algorithm (once for all):
            hemiangles = np.transpose(np.vstack((iangle2, skyvaultazi)))
            import time
            finaltime1 = time.time()  # timer for testing

            # initiate arrays for later:
            shadow_all = None
            wallsun_all = None
            facesun_all = None
            wallgndr_all = None
            wallshve_all = None
            wallshve = np.array([])

            index = 0
            for i in range(skyvaultaltint.size):
                for j in range(aziinterval[i]):
                    if self.killed is True:
                        break
                    # azimuth: hemiangles[index, 1]
                    # altitude: hemiangles[index, 0]

                    # Shadow image
                    if usevegdem == 1:
                        vegsh, sh, _, _, wallsun, wallshve, _, facesun = shadowingfunction_wallheight_23(dsm,
                                                                                                              vegdem,
                                                                                                              vegdem2,
                                                                                                              hemiangles[index, 1],
                                                                                                              hemiangles[index, 0],
                                                                                                              scale,
                                                                                                              amaxvalue,
                                                                                                              bush,
                                                                                                              walls,
                                                                                                              dirwalls * deg2rad)
                        shadow = np.copy(sh - (1. - vegsh) * (1. - psi))
                    else:
                        sh, _, wallsun, _, facesun, wallgndr = shadowingfunction_wallheight_13(dsm,
                                                                                                    hemiangles[index, 1],
                                                                                                    hemiangles[index, 0],
                                                                                                    scale, walls,
                                                                                                    dirwalls * deg2rad)
                        shadow = np.copy(sh)

                    wallgndr[walls == 0] = 0
                    # append wallgndr and suniwall for later use:
                    if index != 0:
                        shadow_all = np.append(shadow_all, np.copy(shadow), axis=0)
                        wallsun_all = np.append(wallsun_all, np.copy(wallsun), axis=0)
                        facesun_all = np.append(facesun_all, np.copy(facesun), axis=0)
                        wallgndr_all = np.append(wallgndr_all, np.copy(wallgndr), axis=0)
                        wallshve_all = np.append(wallshve_all, np.copy(wallshve), axis=0)
                    else:
                        shadow_all = np.copy(shadow)
                        wallsun_all = np.copy(wallsun)
                        facesun_all = np.copy(facesun)
                        wallgndr_all = np.copy(wallgndr)
                        wallshve_all = np.copy(wallshve)

                    index = index + 1
                    self.progress.emit()  # move progressbar forward
            print("Finished preparing shadow and ground reflection. Start simulations!")
            # Main loop
            for k in range(len(met[:, 0])):
                # moved initialisation into for-loop (MRevesz):
                radinit = np.transpose(np.vstack((iangle2, skyvaultazi, np.zeros((13, len(iangle2))))))
                radmatI = np.copy(radinit)
                radmatD = np.copy(radinit)
                radmatR = np.copy(radinit)

                # Energy per time step (i.e. data point in met)
                Energyroof = np.copy(Knight) * 0
                EnergyroofI = np.copy(Knight) * 0
                EnergyroofD = np.copy(Knight) * 0
                EnergyroofR = np.copy(Knight) * 0
                Energywall = np.copy(wallmatrix) * 0
                EnergywallI = np.copy(wallmatrix) * 0
                EnergywallD = np.copy(wallmatrix) * 0
                EnergywallR = np.copy(wallmatrix) * 0

                # time delta between 2 time stamps in units of hour:
                if k == 0:
                    timedelta = (dectime[1] - dectime[0])
                else:
                    timedelta = (dectime[k] - dectime[k-1])
                if timedelta > 1:    # if delta > 1 hour, then assume 1 hour
                    timedelta = 1
                print("dt for W -> Wh conversion: %.4f" % timedelta)
                alt = altitude[0, k]
                azi = azimuth[0, k]
                # disp(alt)
                if alt > 2 and met[k, 14] > 0:   # sun-altitude > 2 deg and G > 0 W/m2
                    # Estimation of radD and radI if not measured after Reindl et al. (1990)
                    if onlyglobal:
                        I0, CI, Kt, I0et, CIuncorr = clearnessindex_2013b(zen[0, k], jday[0, k], met[k, 11], met[k, 10],
                                                                          met[k, 14], location, -999.0)
                        I, D = diffusefraction(met[k, 14], altitude[0, k], Kt, met[k, 11], met[k, 10])
                    else:
                        I = met[k, 22]
                        D = met[k, 21]

                    # azimuth: hemiangles[index, 1]
                    # altitude: hemiangles[index, 0]

                    # Solar Incidence angle (Roofs)
                    suniroof = np.sin(slope) * np.cos(alt * deg2rad) * \
                               np.cos((azi * deg2rad) - aspect) + \
                               np.cos(slope) * np.sin((alt * deg2rad))

                    suniroof[suniroof < 0] = 0

                    # Solar Incidence angle (Walls)
                    suniwall = (np.sin(np.pi / 2) * np.cos(alt * deg2rad) *
                                np.cos((azi * deg2rad) - dirwalls * deg2rad) +
                                np.cos(np.pi / 2) * np.sin((alt * deg2rad))
                                )
                    suniwall = np.where(suniwall < 0, 0, suniwall)

                    G = met[k, 14]

                    # anisotrophic diffuse distribution (Perez)
                    lv, _, _ = Perez_v3(90 - altitude[0, k], azimuth[0, k], D, I, jday[0, k], 1)

                    distalt = np.abs(iangle2 - alt)
                    altlevel = distalt == (np.min(np.abs(distalt)))
                    distazi = np.abs(skyvaultazi - azi)
                    azipos = distazi[altlevel] == (np.min(distazi[altlevel]))
                    azipos2 = np.where(altlevel)[0][0] + np.where(azipos)[0][0]

                    radmatI[azipos2, 2] = radmatI[azipos2, 2] + I
                    radmatD[:, 2] = radmatD[:, 2] + D * lv[:, 2]
                    radmatR[:, 2] = radmatR[:, 2] + G * ((1 / 145) / 2) * albedo

                    #         Gyear=Gyear+(G*sin(altitude(k)*(pi/180)));
                    #         Dyear=Dyear+D;

                    if output['energymonth'] == 1:
                        radmatI[azipos2, met[k, 1] + 2] = radmatI[azipos2, met[k, 1] + 2] + I
                        radmatD[:, met[k, 1] + 2] = radmatD[:, met[k, 1] + 2] + D * lv[:, 2]
                        radmatR[:, met[k, 1] + 2] = radmatR[:, met[k, 1] + 2] + G * ((1 / 145) / 2) * albedo
                        #             Gmonth(met(k,2))=Gmonth(met(k,2))+(G*sin(altitude(k)*(pi/180)));
                        #             Dmonth(met(k,2))=Dmonth(met(k,2))+D;

                    print("%d, %d:%d, %.2f, %.2f, %.1f, %.1f, %.1f" % (k, met[k, 2], met[k, 3], alt, azi, G, I, D))
                    # Adjusting the numbers if multiple years is used
                    # MRevesz: commented
                    # if np.shape(met)[0] > 8760:
                    #     multiyear = np.shape(met)[0] / 8760
                    #     radmatI[:, 2:15] = radmatI[:, 2:15] / multiyear
                    #     radmatD[:, 2:15] = radmatD[:, 2:15] / multiyear
                    #     radmatR[:, 2:15] = radmatR[:, 2:15] / multiyear
                    #

                    # timer for testing:
                    time1 = time.time()
                    index = 0
                    for i in range(skyvaultaltint.size):
                        for j in range(aziinterval[i]):
                            if self.killed is True:
                                break

                            # get pre-calculated arrays:
                            shadow = shadow_all[index*sizex:(index+1)*sizex]
                            wallsun = wallsun_all[index*sizex:(index+1)*sizex]
                            facesun = facesun_all[index*sizex:(index+1)*sizex]
                            wallshve = wallshve_all[index*sizex:(index+1)*sizex]
                            # print("index: %d\n shape suniroof: %s\n shape shadow: %s" % (index, np.shape(suniroof),
                            #                                                          np.shape(shadow)))

                            # azimuth: radmatI[index, 1]
                            # altitude: radmatI[index, 0]

                            # if radmatI[index,2] != 0:
                                # MRevesz: Write arrays to png:

                                # import Image
                                # im = Image.fromarray(wallsh)
                                # im.save('wallsh-%s-%s.tif' % (radmatI[index, 1], radmatI[index, 0]))
                                # im = Image.fromarray(wallsun)
                                # im.save('wallsun-%s-%s.tif' % (radmatI[index, 1], radmatI[index, 0]))
                                # im = Image.fromarray(shadow)
                                # im.save('shadow-%s-%s.tif' % (radmatI[index, 1], radmatI[index, 0]))

                            # roof irradiance calculation
                            # direct radiation
                            if radmatI[index, 2] > 0:
                                I = shadow * radmatI[index, 2] * suniroof
                            else:
                                I = np.copy(Knight)

                            # roof diffuse and reflected radiation
                            D = radmatD[index, 2] * shadow
                            R = radmatR[index, 2] * (shadow*-1 + 1)

                            Energyroof = np.copy(Energyroof + I + D + R)
                            EnergyroofI = np.copy(EnergyroofI + I)
                            EnergyroofD = np.copy(EnergyroofD + D)
                            EnergyroofR = np.copy(EnergyroofR + R)

                            # WALL IRRADIANCE
                            # direct radiation
                            if radmatI[index, 2] > 0:
                                Iw = radmatI[index, 2] * suniwall    # wall
                            else:
                                Iw = np.copy(Knight)

                            # wall diffuse and reflected radiation
                            Dw = radmatD[index, 2] * facesun
                            # Rw = radmatR[index, 2] * facesun

                            # for each wall level (voxelheight interval)
                            wallsun = np.floor(wallsun*(1/voxelheight))*voxelheight
                            if usevegdem == 1:
                                wallshve = np.floor(wallshve*(1/voxelheight))*voxelheight

                            wallmatrix = wallmatrix * 0
                            wallmatrixI = np.copy(wallmatrix)
                            wallmatrixD = np.copy(wallmatrix)

                            for p in range(np.shape(wallmatrix)[0]):
                                wrowp = wallrow[p]   # y-coordinate index
                                wcolp = wallcol[p]   # x-coordinate index
                                if wallsun[wrowp, wcolp] > 0:    # Sections in sun
                                    if wallsun[wrowp, wcolp] == wallstot[wrowp, wcolp]:    # Sections in sun
                                        wallmatrix[p, 0:int(wallstot[wrowp, wcolp]/voxelheight)] = Iw[wrowp, wcolp] + \
                                                                                                      Dw[wrowp, wcolp]
                                        wallmatrixI[p, 0:int(wallstot[wrowp, wcolp]/voxelheight)] = Iw[wrowp, wcolp]
                                        wallmatrixD[p, 0:int(wallstot[wrowp, wcolp]/voxelheight)] = Dw[wrowp, wcolp]
                                    else:
                                        wallmatrix[p, int((wallstot[wrowp, wcolp] -
                                                        wallsun[wrowp, wcolp])/voxelheight) - 1:
                                                        int(wallstot[wrowp, wcolp]/voxelheight)] = Iw[wrowp, wcolp] + \
                                                                                                      Dw[wrowp, wcolp]
                                        wallmatrixI[p, int((wallstot[wrowp, wcolp] -
                                                           wallsun[wrowp, wcolp]) / voxelheight) - 1:
                                                      int(wallstot[wrowp, wcolp] / voxelheight)] = Iw[wrowp, wcolp]
                                        wallmatrixD[p, int((wallstot[wrowp, wcolp] -
                                                           wallsun[wrowp, wcolp]) / voxelheight) - 1:
                                                      int(wallstot[wrowp, wcolp] / voxelheight)] = Dw[wrowp, wcolp]

                            Energywall = Energywall + np.copy(wallmatrix)
                            EnergywallI = EnergywallI + np.copy(wallmatrixI)
                            EnergywallD = EnergywallD + np.copy(wallmatrixD)

                            # if calc_month:
                            #     for t in range(3, 15):
                            #         # ROFF IRRADIANCE
                            #         # direct radiation
                            #         if radmatI[index, t] > 0:
                            #             I = shadow*radmatI[index, t] * suniroof     # roof
                            #         else:
                            #             I = np.copy(Knight)
                            #
                            #         # roof diffuse and reflected radiation
                            #         D = radmatD[index, t] * shadow
                            #         R = radmatR[index, t] * (shadow*-1+1)
                            #         Energymonthroof[:, :, t-3] = Energymonthroof[:, :, t-3] + D + R + I
                            #
                            #         # WALL IRRADIANCE
                            #         # direct radiation
                            #         if radmatI[index, t] > 0:
                            #             Iw = radmatI[index, t] * suniwall    # wall
                            #         else:
                            #             Iw = np.copy(Knight)
                            #
                            #         # wall diffuse and reflected radiation
                            #         Dw = (radmatD[index, t] * facesun)
                            #         Rw = (radmatR[index, t] * facesun)
                            #
                            #         # for each wall level (1 meter interval)
                            #         wallsun = np.floor(wallsun)
                            #         wallsh = np.floor(wallsh)
                            #
                            #         wallshve = np.floor(wallshve)
                            #         wallmatrix = wallmatrix * 0
                            #
                            #         for p in range(np.shape(wallmatrix)[0]):
                            #             if wallsun[wallrow[p], wallcol[p]] > 0:    # Sections in sun
                            #                 if wallsun[wallrow[p], wallcol[p]] == wallstot[wallrow[p], wallcol[p]]:    # Sections in sun
                            #                     wallmatrix[p, 0:wallstot[wallrow[p], wallcol[p]]/voxelheight] = Iw[wallrow[p], wallcol[p]] + \
                            #                                                                                     Dw[wallrow[p], wallcol[p]] + \
                            #                                                                                     Rw[wallrow[p], wallcol[p]]
                            #                 else:
                            #                     wallmatrix[p, (wallstot[wallrow[p], wallcol[p]] -
                            #                                wallsun[wallrow[p], wallcol[p]] / voxelheight) - 1:
                            #                                wallstot[wallrow[p], wallcol[p]] / voxelheight] = Iw[wallrow[p], wallcol[p]] + \
                            #                                                                                  Dw[wallrow[p], wallcol[p]] + \
                            #                                                                                  Rw[wallrow[p], wallcol[p]]
                            #
                            #             if wallshve[wallrow[p], wallcol[p]] > 0:    # sections in vegetation shade
                            #                 wallmatrix[p, 0:wallshve[wallrow[p],
                            #                                          (wallcol[p] + wallsh[wallrow[p], wallcol[p]])]/voxelheight] = \
                            #                     (Iw[wallrow[p], wallcol[p]] + Dw[wallrow[p], wallcol[p]]) * psi
                            #
                            #             if wallsh[wallrow[p], wallcol[p]] > 0:    # sections in building shade
                            #                 wallmatrix[p, 0:wallsh[wallrow[p], wallcol[p]]/voxelheight] = Rw[wallrow[p], wallcol[p]]
                            #
                            #         Energymonthwall[:, :, t-3] = Energymonthwall[:, :, t-3] + np.copy(wallmatrix)
                            #
                            # if calc_month:
                            #     for p in range(len(Dmonth)):
                            #         Iradmonth = (shadow * radmat[index, 3+p] * suniroof)
                            #         DGradmonth = (shadow * Dmonth[p] + (shadow*-1+1) * Gmonth[p] * albedo) * svf
                            #         Energymonthroof[:, :, p] = Energymonthroof[:, :, p] + Iradmonth + DGradmonth

                            index = index + 1

                            self.progress.emit()  # move progressbar forward

                    # now loop for ground reflected irradiance on walls:
                    index = 0
                    ddt = 0     # initiate for timing measurement
                    shape_wallmatrix = np.shape(wallmatrix)
                    # count invalid coordinates: (for testing)
                    count_invalid = 0
                    for i in range(skyvaultaltint.size):
                        for j in range(aziinterval[i]):
                            if self.killed is True:
                                break
                            # get pre-calculated arrays:
                            wallgndr = wallgndr_all[index*sizex:(index+1)*sizex]

                            # Prepare for viewfactor:
                            if radmatD[index, 0] < 90:
                                alt_index = np.where(skyvaultaltint == radmatD[index, 0])[0][0]
                                delta_azi = skyvaultaziint[alt_index]

                                cot_alt_outer = (1/np.tan(skyvaultaltint[alt_index] * deg2rad))
                                cot_alt_inner = (1/np.tan(skyvaultaltint[alt_index+1] * deg2rad))
                                cotsq_alt_outer = cot_alt_outer**2
                                cotsq_alt_inner = cot_alt_inner**2

                                # following radii are r/z_wall:
                                radi_xy_half = np.sqrt((cotsq_alt_outer + cotsq_alt_inner) / 2)   # at circ segment/2
                                radi_outer = np.sqrt(3 * cotsq_alt_outer + cotsq_alt_inner)   # at center of outer area
                                radi_inner = np.sqrt(cotsq_alt_outer + 3 * cotsq_alt_inner)   # at center of inner area
                                radi_outer = radi_outer / 2
                                radi_inner = radi_inner / 2

                                # is dArea/(z_wall**2):
                                d_area = delta_azi / 360. * (cotsq_alt_outer - cotsq_alt_inner) * np.pi

                                wallmatrix *= 0

                                # temporary for testing:
                                # roundvoxel = round(self.voxelheight, 1)
                                # print("roundvoxel = %.1f" % roundvoxel)
                                # printnowflag = 0   # 1
                                # if printnowflag:
                                #     print(wallrow[0], wallcol[0])
                                #     print((wallrow[0] == 24), (wallcol[0] == 23))
                                #     printnowflag = 0

                                time3 = time.time()

                                for p in range(shape_wallmatrix[0]):
                                    wrowp = wallrow[p]   # y-coordinate index
                                    wcolp = wallcol[p]   # x-coordinate index
                                    # create array for wall-height-indices:
                                    if wallgndr[wrowp, wcolp] > 0:
                                        if wallgndr[wrowp, wcolp] < wallstot[wrowp, wcolp]:
                                            # only part of wall sees ground:
                                            max_wallidx = int(wallgndr[wrowp, wcolp] / voxelheight)
                                        else:
                                            # top wall-pixel or higher can see ground:
                                            max_wallidx = int(wallstot[wrowp, wcolp] / voxelheight)
                                        wall_gndr_idx = np.arange(max_wallidx) + 1

                                        # normal vector on walls, assuming all walls have 90 degree tilt:
                                        normal_w_x = np.sin(dirwalls[wrowp, wcolp])
                                        normal_w_y = -np.cos(dirwalls[wrowp, wcolp])
                                        normal_w_z = 0.

                                        r_xy_half = np.copy(wall_gndr_idx) * radi_xy_half
                                        r_xy_inner = np.copy(wall_gndr_idx) * radi_inner
                                        r_xy_outer = np.copy(wall_gndr_idx) * radi_outer

                                        # Get x, y coordinates in the center for view factor calculation:
                                        x = wcolp + np.sin(radmatD[index, 1] * deg2rad) * r_xy_half
                                        y = wrowp - np.cos(radmatD[index, 1] * deg2rad) * r_xy_half
                                        x = x.astype(int)
                                        y = y.astype(int)

                                        # wallmatrix[p, 0:max_wallidx] += x                  # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += y                  # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += slope[y, x]    # used for testing only!!!

                                        # Get distance vector of reflection (in real scale, from wall to ground):
                                        r_wg_x = r_xy_half * voxelheight * np.sin(radmatD[index, 1] * deg2rad)
                                        r_wg_y = (-1) * r_xy_half * voxelheight * np.cos(radmatD[index, 1] * deg2rad)
                                        r_wg_z = (-1) * np.copy(wall_gndr_idx) * voxelheight

                                        # normal vector on ground:
                                        try:
                                            slope_at_xy = np.where(walls[y, x] > 0, 0, slope[y, x])
                                        except IndexError:
                                            # print("Index of reflection source coordinate is out of array. \n" +
                                            #       "Assuming flat ground for ground normal vector. ")
                                            normal_g_x = 0
                                            normal_g_y = 0
                                            normal_g_z = 1
                                        else:
                                            normal_g_x = np.sin(aspect[y, x]) * np.sin(slope_at_xy)
                                            normal_g_y = -np.cos(aspect[y, x]) * np.sin(slope_at_xy)
                                            normal_g_z = np.cos(slope_at_xy)

                                        d_area_true = d_area * ((np.copy(wall_gndr_idx) * voxelheight)**2)

                                        gndIrrad = np.copy(wall_gndr_idx) * 0.

                                        # Get x, y coordinates in the center of the 4 area patches to be averaged:
                                        for patches in range(4):
                                            if patches < 2:
                                                # inner patches:
                                                x = wcolp + np.sin((radmatD[index, 1] -
                                                                    (-1)**patches * delta_azi/4)*deg2rad) * r_xy_inner
                                                y = wrowp - np.cos((radmatD[index, 1] -
                                                                    (-1)**patches * delta_azi/4)*deg2rad) * r_xy_inner
                                            else:
                                                # outer patches:
                                                x = wcolp + np.sin((radmatD[index, 1] -
                                                                    (-1)**patches * delta_azi/4)*deg2rad) * r_xy_outer
                                                y = wrowp - np.cos((radmatD[index, 1] -
                                                                    (-1)**patches * delta_azi/4)*deg2rad) * r_xy_outer
                                            x = x.astype(int)
                                            y = y.astype(int)

                                            # add up irradiation/PV yield on ground at coord. x,y:
                                            invalidcoords = (x < 0) + (x >= sizex) + (y < 0) + (y >= sizey)
                                            x = np.where(invalidcoords, 0, x)
                                            y = np.where(invalidcoords, 0, y)
                                            tmpgndIrrad = 0   # reinitiate for testing
                                            try:
                                                tmpgndIrrad = np.where(invalidcoords, 0, Energyroof[y, x])
                                            except IndexError:
                                                count_invalid += 1
                                                errmsg = str(count_invalid) + "\n" + \
                                                    "Energyroof size = " + str(np.shape(Energyroof)) + \
                                                    ", sizex=" + str(sizex) + ", sizey=" + str(sizey) + \
                                                    "\n maximum x,y = " + str(max(x)) + ', ' + str(max(y)) + \
                                                    "\n condition yields: " + str(invalidcoords) + \
                                                    "\n tmpgndIrrad = " + str(tmpgndIrrad)
                                                # print(errmsg)
                                            else:
                                                if albedo_array is None:
                                                    gndIrrad += tmpgndIrrad
                                                else:
                                                    gndIrrad += (tmpgndIrrad * albedo_array[y, x])
                                        # average ground irradiance/PV yield of 4 patches:
                                        gndIrrad *= 0.25
                                        wallmatrix[p, 0:max_wallidx] += gndIrrad    # commented for testing!! UNcomment for usage!

                                        # Now calculate the ground reflected irradiance:
                                        rn_w = r_wg_x * normal_w_x + r_wg_y * normal_w_y
                                        rn_g = r_wg_x * normal_g_x + r_wg_y * normal_g_y + r_wg_z * normal_g_z
                                        r_wg_sq = r_wg_x**2 + r_wg_y**2 + r_wg_z**2

                                        rn_wg = np.where(rn_w < 0, 0, rn_w) * np.where(rn_g > 0, 0, rn_g)

                                        wallmatrix[p, 0:max_wallidx] *= (d_area_true * rn_wg / (r_wg_sq**2))   # commented for testing!! UNcomment for usage! New, corrected version!!
                                        # wallmatrix[p, 0:max_wallidx] += (d_area_true * rn_wg * albedo * (-1) / (np.pi * (r_wg_sq**2)))   # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += d_area_true    # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += r_wg_sq    # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += rn_wg    # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += rn_w    # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] -= rn_g    # used for testing only!!!
                                        # wallmatrix[p, 0:max_wallidx] += normal_g_z    # used for testing only!!!
                                    else:
                                        pass

                                time4 = time.time()
                                ddt += (time4 - time3)

                                if albedo_array is None:
                                    Energywall += (np.copy(wallmatrix) * albedo * (-1) / np.pi)
                                    EnergywallR += (np.copy(wallmatrix) * albedo * (-1) / np.pi)   # commented for testing!! UNcomment for usage!
                                else:
                                    Energywall += (np.copy(wallmatrix) * (-1) / np.pi)
                                    EnergywallR += (np.copy(wallmatrix) * (-1) / np.pi)   # commented for testing!! UNcomment for usage!

                                # START of TEST ###########################################
                                # EnergywallR += np.copy(wallmatrix)    # for summation over hemisphere
                                # test_walls = np.transpose(np.vstack((wallrow + 1, wallcol + 1,
                                #                                      np.transpose(np.copy(wallmatrix))
                                #                                      )
                                #                                     )
                                #                           )   # for output at single skypatch
                                # angles_string = "az" + str(hemiangles[index, 1]) + "-al" + str(hemiangles[index, 0])
                                # filenamewall = str('slop-wallR-' + angles_string + '.txt')
                                # header = '%row col irradiance'
                                # numformat = '%4d %4d ' + '%.4E ' * (
                                #         test_walls.shape[1] - 2)  # format origina: %6.2f instead of %.4E
                                # np.savetxt(filenamewall, test_walls, fmt=numformat, header=header, comments='')
                                # END of TEST #############################################
                            index += 1

                            self.progress.emit()  # move progressbar forward

                    time2 = time.time()
                    print("t1=%.2f, t2=%.2f, dt=%.2f, dt-alb=%.2f" % (time1, time2, (time2-time1), ddt))

                    # Including radiation from ground on walls as well as removing pixels high than walls
                    wallmatrixbol = (Energywall > 0).astype(float)
                    Energywall = Energywall * wallmatrixbol
                    EnergywallI = EnergywallI * wallmatrixbol
                    EnergywallD = EnergywallD
                    EnergywallR = EnergywallR

                    # calculate PV power for walls and roofs: (MRevesz)
                    celltemp = self.tcel.celltemp(Energywall, met[k, 11], met[k, 9])    # 11: Tamb, 9: Vwind
                    Energywall = self.pvm.calcpower(Energywall, celltemp)
                    Energyyearwall = Energyyearwall + np.copy(Energywall)*timedelta
                    EnergyyearwallI = EnergyyearwallI + np.copy(EnergywallI)*timedelta
                    EnergyyearwallD = EnergyyearwallD + np.copy(EnergywallD)*timedelta
                    EnergyyearwallR = EnergyyearwallR + np.copy(EnergywallR)*timedelta
                    # Energyyearwall = Energyyearwall + np.copy(Energywallgndr)         # for testing only!
                    celltemp = self.tcel.celltemp(Energyroof, met[k, 11], met[k, 9])    # 11: Tamb, 9: Vwind
                    Energyroof = self.pvm.calcpower(Energyroof, celltemp)
                    Energyyearroof = Energyyearroof + np.copy(Energyroof)*timedelta
                    EnergyyearroofI = EnergyyearroofI + np.copy(EnergyroofI)*timedelta
                    EnergyyearroofD = EnergyyearroofD + np.copy(EnergyroofD)*timedelta
                    EnergyyearroofR = EnergyyearroofR + np.copy(EnergyroofR)*timedelta

                else:
                    self.progress.emit()

                if self.dlg.checkBoxSaveIntermedi.isChecked():
                    # save data for each timestamp:
                    time_str = '{0:.0f}{1:03.0f}-{2:02.0f}{3:02.0f}-{4}'.format(met[k, 0], met[k, 1],
                                                                                met[k, 2], met[k, 3], k)
                    filenamewall = 'Energywall-' + time_str + '.txt'
                    self.save_intermediate_res(Energywall, filenamewall, wallcol, wallrow, timedelta)

                    filenamewall = 'EnergywallI-' + time_str + '.txt'
                    self.save_intermediate_res(EnergywallI, filenamewall, wallcol, wallrow, timedelta)

                    filenamewall = 'EnergywallD-' + time_str + '.txt'
                    self.save_intermediate_res(EnergywallD, filenamewall, wallcol, wallrow, timedelta)

                    filenamewall = 'EnergywallR-' + time_str + '.txt'
                    self.save_intermediate_res(EnergywallR, filenamewall, wallcol, wallrow, timedelta)
                else:
                    pass

            # convert from Wh/Wp to kWh/Wp (for PV output; for solar irradiation in kWh/m2):
            Energyyearroof /= 1000
            EnergyyearroofI /= 1000
            EnergyyearroofD /= 1000
            EnergyyearroofR /= 1000
            Energyyearwall /= 1000
            EnergyyearwallI /= 1000
            EnergyyearwallD /= 1000
            EnergyyearwallR /= 1000

            Energyyearwall = np.transpose(np.vstack((wallrow + 1, wallcol + 1, np.transpose(Energyyearwall))))    # adding 1 to wallrow and wallcol so that the tests pass
            EnergyyearwallI = np.transpose(np.vstack((wallrow + 1, wallcol + 1, np.transpose(EnergyyearwallI))))    # adding 1 to wallrow and wallcol so that the tests pass
            EnergyyearwallD = np.transpose(np.vstack((wallrow + 1, wallcol + 1, np.transpose(EnergyyearwallD))))    # adding 1 to wallrow and wallcol so that the tests pass
            EnergyyearwallR = np.transpose(np.vstack((wallrow + 1, wallcol + 1, np.transpose(EnergyyearwallR))))    # adding 1 to wallrow and wallcol so that the tests pass

            # if calc_month:
            #     for t in range(3, 15):
            #         Energymonthwall[:, :, t-3] = (Energymonthwall[:, :, t-3] + (np.sum(radmatR[:, t])*albedo)/2) * wallmatrixbol
            # else:
            #     Energymonthwall = np.array([])
            #
            # if calc_month:
            #     return Energyyearroof, Energyyearwall, Energymonthroof, Energymonthwall
            # else:
            #     return Energyyearroof, Energyyearwall, vegdata

            # if self.killed is True:
            #     break

            finaltime2 = time.time()  # timer for testing
            print("Total simulation time:\nt1=%.2f, t2=%.2f, dt=%.2f" % (finaltime1, finaltime2,
                                                                         (finaltime2 - finaltime1)))

            seberesult = {'PVEnergyyearroof': Energyyearroof, 'PVEnergyyearwall': Energyyearwall, 'vegdata': vegdata,
                          'EnergyyearroofI': EnergyyearroofI, 'EnergyyearroofD': EnergyyearroofD, 'EnergyyearroofR': EnergyyearroofR,
                          'EnergyyearwallI': EnergyyearwallI, 'EnergyyearwallD': EnergyyearwallD, 'EnergyyearwallR': EnergyyearwallR}

            if self.killed is False:
                self.progress.emit()
                ret = seberesult
        except Exception:
            raise
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        print(sys.exc_info())
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

    def kill(self):
        self.killed = True

    def save_intermediate_res(self, array, filename, wallcol, wallrow, timedelta):
        """
        Save intermediate results of wall-energy,
        which can not be sent to the main result-handler after finishing the simulation.

        :param array:
        :param filename: <str>
        :param wallcol:
        :param wallrow:
        :param timedelta: <int>
        :return:
        """
        header = '%row col irradiance'
        numformat = '%4d %4d ' + '%.4E ' * (array.shape[1])
        np.savetxt(filename,
                   np.transpose(
                       np.vstack((wallrow + 1,
                                  wallcol + 1,
                                  np.transpose(np.copy(array) * timedelta / 1000))
                                 )
                   ),
                   fmt=numformat, header=header, comments='')
        return 0
