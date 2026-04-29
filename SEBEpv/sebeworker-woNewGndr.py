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

    # def __init__(self, dsm, scale, building_slope,building_aspect, voxelheight, sizey, sizex, vegdsm, vegdsm2, wheight,waspect, albedo, psi, radmatI, radmatD, radmatR, usevegdem, calc_month, dlg):
    def __init__(self, dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex, vegdsm, vegdsm2,
                        wheight, waspect, albedo, psi, metdata, altitude, azimuth, onlyglobal, output, jday, location,
                        zen, usevegdem, calc_month, dlg, pvm, tcel):
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

    def run(self):
        ret = None
        try:
            # Energyyearroof, Energyyearwall, vegdata = SEBE_2015a_calc.SEBE_2015a_calc(self.dsm, self.scale, self.building_slope,
            #         self.building_aspect, self.voxelheight, self.sizey, self.sizex, self.vegdsm, self.vegdsm2, self.wheight,
            #         self.waspect, self.albedo, self.psi, self.radmatI, self.radmatD, self.radmatR, self.usevegdem, self.calc_month)

            #def SEBE_2015a_calc(a, scale, slope, aspect, voxelheight, sizey, sizex, vegdem, vegdem2, walls, dirwalls, albedo, psi, radmatI, radmatD, radmatR, usevegdem, calc_month):

            a = self.dsm
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
            Energyyearroof = np.copy(Knight)

            dectime = met[:, 1] + met[:, 2] / 24 + met[:, 3] / (60 * 24.)

            # TODO: Month calculation is not prepared
            # if calc_month:
            #     # Energymonthroof = np.zeros(sizey, sizex, 12)
            #     Energymonthroof = np.array([])
            # else:
            #     Energymonthroof = np.array([])

            if usevegdem == 1:
                # amaxvalue
                vegmax = vegdem.max()
                amaxvalue = a.max() - a.min()
                amaxvalue = np.maximum(amaxvalue, vegmax)

                # Elevation vegdsms if buildingDEM includes ground heights
                vegdem = vegdem+a
                vegdem[vegdem == a] = 0
                vegdem2 = vegdem2+a
                vegdem2[vegdem2 == a] = 0

                #% Bush separation
                bush = np.logical_not((vegdem2*vegdem))*vegdem
            else:
                psi = 1

            # Creating wallmatrix (1 meter interval)
            wallcol, wallrow = np.where(np.transpose(walls) > 0)    #row and col for each wall pixel
            # wallrow, wallcol = np.where(walls > 0.2)    #row and col for each wall pixel
            wallstot = np.floor(walls*(1/voxelheight)) * voxelheight
            wallsections = np.floor(np.max(walls) * (1/voxelheight))     # finding tallest wall
            wallmatrix = np.zeros((np.shape(wallrow)[0], np.int(wallsections)))
            Energyyearwall = np.copy(wallmatrix)
            # Energymonthwall = np.zeros(np.shape(wallmatrix[0]), np.shape(wallmatrix[1]), 12)

            # commented out MRevesz
            #  Main loop - Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
            #skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
            #aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])

            if usevegdem == 1:
                wallshve = np.zeros(np.shape(a))
                vegrow, vegcol = np.where(vegdem > 0)    #row and col for each veg pixel
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
            # index = 1
            skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
            skyvaultaziint = np.array([12, 12, 15, 15, 20, 30, 60, 360])
            aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])
            azistart = np.array([0, 4, 2, 5, 8, 0, 10, 0])
            # annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])
            skyvaultazi = np.array([])
            for j in range(8):
                for k in range(1, int(360 / skyvaultaziint[j]) + 1):
                    # skyvaultalt(index)=skyvaultaltint(j);
                    skyvaultazi = np.append(skyvaultazi, k * skyvaultaziint[j] + azistart[j])
                    if skyvaultazi[-1] > 360:
                        skyvaultazi[-1] = skyvaultazi[-1] - 360
                        # index = index + 1

            iangle2 = np.array([])
            Gyear = 0
            Dyear = 0
            Gmonth = np.zeros([1, 12])
            Dmonth = Gmonth
            for j in range(len(aziinterval)):
                iangle2 = np.append(iangle2, skyvaultaltint[j] * np.ones([1, aziinterval[j]]))


            iazimuth = skyvaultazi
            # Ta = met[:, 11]
            # RH = met[:, 10]



            #radmatI, radmatD, radmatR = sunmapcreator_2015a(self.metdata, altitude, azimuth,
            #                                                onlyglobal, output, jday, albedo, location, zen)

            # Main loop
            for k in range(len(met[:, 0])):
                # moved initialisation into for-loop (MRevesz):
                radinit = np.transpose(np.vstack((iangle2, skyvaultazi, np.zeros((13, len(iangle2))))))
                radmatI = np.copy(radinit)
                radmatD = np.copy(radinit)
                radmatR = np.copy(radinit)
                # print(radmatI)

                Energyroof = np.copy(Knight) * 0
                Energywall = np.copy(wallmatrix) * 0
                # Energywallgndr = np.copy(wallmatrix) * 0

                # time delta between 2 time stamps in units of hour:
                if k == 0:
                    timedelta = (dectime[1] - dectime[0]) * 24
                else:
                    timedelta = (dectime[k] - dectime[k-1]) * 24
                alt = altitude[0, k]
                azi = azimuth[0, k]
                # disp(alt)
                if alt > 2:
                    # Estimation of radD and radI if not measured after Reindl et al. (1990)
                    if onlyglobal:
                        I0, CI, Kt, I0et, CIuncorr = clearnessindex_2013b(zen[0, k], jday[0, k], met[k, 11], met[k, 10],
                                                                          met[k, 14], location, -999.0)
                        I, D = diffusefraction(met[k, 14], altitude[0, k], Kt, met[k, 11], met[k, 10])
                    else:
                        I = met[k, 22]
                        D = met[k, 21]

                    G = met[k, 14]

                    # anisotrophic diffuse distribution (Perez)
                    lv, _, _ = Perez_v3(90 - altitude[0, k], azimuth[0, k], D, I, jday[0, k], 1)

                    distalt = np.abs(iangle2 - alt)
                    altlevel = distalt == (np.min(np.abs(distalt)))
                    distazi = np.abs(iazimuth - azi)
                    azipos = distazi[altlevel] == (np.min(distazi[altlevel]))
                    azipos2 = np.where(altlevel)[0][0] + np.where(azipos)[0][0]
                    # azipos2 = np.where(altlevel)[0] + np.where(azipos)[0]
                    # azipos2 = find(altlevel, 1)-1 + find(azipos, 1)

                    radmatI[azipos2, 2] = radmatI[azipos2, 2] + I
                    radmatD[:, 2] = radmatD[:, 2] + D * lv[:, 2]
                    radmatR[:, 2] = radmatR[:, 2] + G * (1 / 145) * albedo

                    #         Gyear=Gyear+(G*sin(altitude(k)*(pi/180)));
                    #         Dyear=Dyear+D;

                    if output['energymonth'] == 1:
                        radmatI[azipos2, met[k, 1] + 2] = radmatI[azipos2, met[k, 1] + 2] + I
                        radmatD[:, met[k, 1] + 2] = radmatD[:, met[k, 1] + 2] + D * lv[:, 2]
                        radmatR[:, met[k, 1] + 2] = radmatR[:, met[k, 1] + 2] + G * (1 / 145) * albedo
                        #             Gmonth(met(k,2))=Gmonth(met(k,2))+(G*sin(altitude(k)*(pi/180)));
                        #             Dmonth(met(k,2))=Dmonth(met(k,2))+D;

                    print("%d:%d, %.5f, %.5f, %.3f, %.3f, %.3f" % (met[k, 2], met[k, 3], alt, azi, G, I, D))
                # Adjusting the numbers if multiple years is used
                # MRevesz: commented
                # if np.shape(met)[0] > 8760:
                #     multiyear = np.shape(met)[0] / 8760
                #     radmatI[:, 2:15] = radmatI[:, 2:15] / multiyear
                #     radmatD[:, 2:15] = radmatD[:, 2:15] / multiyear
                #     radmatR[:, 2:15] = radmatR[:, 2:15] / multiyear
                #

                # timer for testing:
                import time
                time1 = time.time()
                index = 0
                for i in range(skyvaultaltint.size):
                    for j in range(aziinterval[i]):

                        if self.killed is True:
                            break

                        #################### SOLAR RADIATION POSITIONS ###################
                        #Solar Incidence angle (Roofs)
                        suniroof = np.sin(slope) * np.cos(radmatI[index, 0] * deg2rad) * \
                                   np.cos((radmatI[index, 1]*deg2rad)-aspect) + \
                                   np.cos(slope) * np.sin((radmatI[index, 0] * deg2rad))

                        suniroof[suniroof < 0] = 0

                        # Solar Incidence angle (Walls)
                        suniwall = (np.sin(np.pi/2) * np.cos(radmatI[index, 0] * deg2rad) * np.cos((radmatI[index, 1] * deg2rad) - dirwalls*deg2rad)
                                    + np.cos(np.pi/2) * np.sin((radmatI[index, 0] * deg2rad)))
                        suniwall = np.where(suniwall<0,0,suniwall)

                        # Shadow image
                        if usevegdem == 1:
                            vegsh, sh, _, wallsh, wallsun, wallshve, _, facesun = shadowingfunction_wallheight_23(a,
                                                vegdem, vegdem2, radmatI[index, 1], radmatI[index, 0], scale, amaxvalue,
                                                                                                bush, walls, dirwalls*deg2rad)
                            shadow = np.copy(sh-(1.-vegsh)*(1.-psi))
                        else:
                            sh, wallsh, wallsun, facesh, facesun, wallgndr = shadowingfunction_wallheight_13(a, radmatI[index, 1],
                                                                            radmatI[index, 0], scale, walls, dirwalls*deg2rad)
                            shadow = np.copy(sh)

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

                        Energyroof = np.copy(Energyroof+D+R+I)

                        # WALL IRRADIANCE
                        # direct radiation
                        if radmatI[index, 2] > 0:
                            Iw = radmatI[index, 2] * suniwall    # wall
                        else:
                            Iw = np.copy(Knight)

                        # wall diffuse and reflected radiation
                        Dw = radmatD[index, 2] * facesun
                        Rw = radmatR[index, 2] * facesun

                        # for each wall level (voxelheight interval)
                        wallsun = np.floor(wallsun*(1/voxelheight))*voxelheight
                        wallsh = np.floor(wallsh*(1/voxelheight))*voxelheight
                        wallgndr = np.floor(wallgndr*(1/voxelheight))*voxelheight
                        if usevegdem == 1:
                            wallshve = np.floor(wallshve*(1/voxelheight))*voxelheight

                        wallmatrix = wallmatrix * 0
                        # wallmatrixgndr = np.copy(wallmatrix)  # for testing the ground reflected component

                        for p in range(np.shape(wallmatrix)[0]):
                            if wallsun[wallrow[p], wallcol[p]] > 0:    # Sections in sun
                                if wallsun[wallrow[p], wallcol[p]] == wallstot[wallrow[p], wallcol[p]]:    # Sections in sun
                                    wallmatrix[p, 0:int(wallstot[wallrow[p], wallcol[p]]/voxelheight)] = Iw[wallrow[p],
                                                                                                        wallcol[p]] + \
                                                                                                    Dw[wallrow[p],
                                                                                                       wallcol[p]]
                                else:
                                    wallmatrix[p, int((wallstot[wallrow[p], wallcol[p]] -
                                                    wallsun[wallrow[p], wallcol[p]])/voxelheight) - 1:
                                                    int(wallstot[wallrow[p], wallcol[p]]/voxelheight)] = Iw[wallrow[p],
                                                                                                        wallcol[p]] + \
                                                                                                    Dw[wallrow[p],
                                                                                                       wallcol[p]]

                            if usevegdem == 1 and wallshve[wallrow[p], wallcol[p]] > 0:    # sections in vegetation shade
                                wallmatrix[p, 0:int(wallshve[wallrow[p], wallcol[p] + wallsh[wallrow[p],
                                                                                          wallcol[p]]]/voxelheight)] = \
                                    (Iw[wallrow[p], wallcol[p]] + Dw[wallrow[p], wallcol[p]])*psi

                            # if wallsh[wallrow[p], wallcol[p]] > 0:    # sections in building shade
                            #     wallmatrix[p, 0:int(wallsh[wallrow[p], wallcol[p]] / voxelheight)] = Rw[wallrow[p],
                            #                                                                           wallcol[p]]
                            if wallgndr[wallrow[p], wallcol[p]] > 0:
                                if wallgndr[wallrow[p], wallcol[p]] <= wallstot[wallrow[p], wallcol[p]]:    # Walls
                                    #  see ground reflections
                                    wallmatrix[p, 0:int(wallgndr[wallrow[p],wallcol[p]] / voxelheight)] = wallmatrix[p, 0:int(wallgndr[wallrow[p],
                                                                                                                            wallcol[p]] / voxelheight)
                                                                                                          ] + Rw[wallrow[p], wallcol[p]]
                                else:
                                    wallmatrix[p, 0:int(wallstot[wallrow[p], wallcol[p]]/voxelheight)] = wallmatrix[p, 0:int(wallstot[wallrow[p],
                                                                                                                            wallcol[p]] / voxelheight)
                                                                                                          ] + Rw[wallrow[p], wallcol[p]]
                                # wallmatrixgndr[p, 0:int(wallgndr[wallrow[p], wallcol[p]] / voxelheight)] = wallmatrixgndr[p,
                                #                                                                        0:int(
                                #                                                                            wallgndr[
                                #                                                                                wallrow[p], wallcol[p]] / voxelheight)] + Rw[wallrow[p], wallcol[p]]

                        Energywall = Energywall + np.copy(wallmatrix)
                        # Energywallgndr = Energywallgndr + np.copy(wallmatrixgndr)    # for testing ground reflection

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

                time2 = time.time()
                print("t1=%.2f, t2=%.2f, dt=%.2f" % (time1, time2, (time2-time1)))

                # Including radiation from ground on walls as well as removing pixels high than walls
                wallmatrixbol = (Energywall > 0).astype(float)
                Energywall = Energywall * wallmatrixbol

                # calculate PV power for walls and roofs: (MRevesz)
                celltemp = self.tcel.celltemp(Energywall, met[k, 11], met[k, 9])    # 11: Tamb, 9: Vwind
                Energywall = self.pvm.calcpower(Energywall, celltemp)
                Energyyearwall = Energyyearwall + np.copy(Energywall)*timedelta
                # Energyyearwall = Energyyearwall + np.copy(Energywallgndr)         # for testing only!
                celltemp = self.tcel.celltemp(Energyroof, met[k, 11], met[k, 9])    # 11: Tamb, 9: Vwind
                Energyroof = self.pvm.calcpower(Energyroof, celltemp)
                Energyyearroof = Energyyearroof + np.copy(Energyroof)*timedelta

            # convert from Wh/Wp to kWh/Wp (for PV output; for solar irradiation in kWh/m2):
            Energyyearroof /= 1000
            Energyyearwall /= 1000

            #Energyyearwall = np.hstack((np.transpose(np.atleast_2d(wallrow)),
            #                            np.transpose(np.atleast_2d(wallcol)), Energyyearwall))
            Energyyearwall = np.transpose(np.vstack((wallrow + 1, wallcol + 1, np.transpose(Energyyearwall))))    # adding 1 to wallrow and wallcol so that the tests pass

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

            seberesult = {'PVEnergyyearroof': Energyyearroof, 'PVEnergyyearwall': Energyyearwall, 'vegdata': vegdata}

            if self.killed is False:
                self.progress.emit()
                ret = seberesult
        except Exception:
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)


    def kill(self):
        self.killed = True


