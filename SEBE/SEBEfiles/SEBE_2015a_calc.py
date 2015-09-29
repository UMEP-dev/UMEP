from __future__ import division
import numpy as np
#from python_fns.shadowingfunction_wallheight_23 import shadowingfunction_wallheight_23
#from shadowingfunction_wallheight_13 import shadowingfunction_wallheight_13 as shadowingfunction_wallheight
#from shadowingfunction_wallheight import shadowingfunction_wallheight
# try:
#     from shadow_function import shadowingfunction_wallheight
# except ImportError:
from shadowingfunction_wallheight_13 import shadowingfunction_wallheight_13
from shadowingfunction_wallheight_23 import shadowingfunction_wallheight_23

from scipy.ndimage.filters import median_filter

# def SEBE_calc(demGrid,dem_scale,building_slope,building_aspect,voxelheight,vegGrid,wall_height,wall_dir,radmatI,radmatD,radmatR,albedo,psi, calc_month=False):
#     dem_max = np.max(demGrid)
#     wall_dir=np.radians(wall_dir).astype(np.float32)
#     if vegGrid is not None:
#         vegGrid_zero = vegGrid == 0
#         vegGrid2 = (vegGrid - demGrid) * 0.25
#         vegGrid2 = vegGrid2 + demGrid
#         vegGrid2[vegGrid_zero] = 0
#         veg_max = np.max(vegGrid - demGrid)
#         dem_max = max(dem_max, veg_max)
#         usevegdem = 1
#     else:
#         vegGrid2 = None
#         veg_max = 0
#         usevegdem = 0
#     return SEBE_2015a_calc(demGrid,dem_scale,building_slope,building_aspect,voxelheight,demGrid.shape[1],demGrid.shape[0],vegGrid,vegGrid2,wall_height,wall_dir,veg_max,dem_max,albedo,psi,radmatI,radmatD,radmatR,usevegdem,calc_month)

def SEBE_2015a_calc(a, scale, slope, aspect, voxelheight, sizey, sizex, vegdem, vegdem2, walls, dirwalls, albedo, psi, radmatI, radmatD, radmatR, usevegdem, calc_month):
    """
    :param a:
    :param scale:
    :param voxelheight:
    :param sizey:
    :param sizex:
    :param vegdem:
    :param vegdem2:
    :param walls:
    :param dirwalls:
    :param albedo:
    :param psi:
    :param radmatI:
    :param radmatD:
    :param radmatR:
    :param usevegdem:
    :param calc_month:
    :return:
    """

    #energymonth = output['energymonth']

    # Parameters
    deg2rad = np.pi/180
    Knight = np.zeros((sizex, sizey))
    Energyyearroof = np.copy(Knight)

    if calc_month:
        # Energymonthroof = np.zeros(sizey, sizex, 12)
        Energymonthroof = np.array([])
    else:
        Energymonthroof = np.array([])

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
    #wallcol, wallrow = np.where(np.transpose(walls) > 0)    #row and col for each wall pixel
    wallrow, wallcol = np.where(walls > 0)    #row and col for each wall pixel
    wallstot = np.floor(walls*(1/voxelheight)) * voxelheight
    wallsections = np.floor(np.max(walls) * (1/voxelheight))     # finding tallest wall
    wallmatrix = np.zeros((np.shape(wallrow)[0], wallsections))
    Energyyearwall = np.copy(wallmatrix)
    # Energymonthwall = np.zeros(np.shape(wallmatrix[0]), np.shape(wallmatrix[1]), 12)

    # Main loop - Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
    skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
    #skyvaultaziint = np.array([12, 12, 15, 15, 20, 30, 60, 360])
    aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])
    # annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])

    index = 0
    svf = 0

    if usevegdem == 1:
        wallshve = np.zeros(np.shape(a))
        vegrow, vegcol = np.where(vegdem > 0)    #row and col for each veg pixel
        vegdata = np.zeros((np.shape(vegrow)[0], 3))
        for i in range(0, vegrow.shape[0] - 1):
            # if vegdem[vegrow, vegcol] > 0:
            vegdata[i, 0] = vegrow[i] + 1
            vegdata[i, 1] = vegcol[i] + 1
            vegdata[i, 2] = vegdem[vegrow[i], vegcol[i]]
    else:
        vegdata = 0

    index = 0
    for i in range(skyvaultaltint.size):
        for j in range(aziinterval[i]):

            #################### SOLAR RADIATION POSITIONS ###################
            #Solar Incidence angle (Roofs)
            suniroof = np.sin(slope) * np.cos(radmatI[index, 0] * deg2rad) * \
                       np.cos((radmatI[index, 1]*deg2rad)-aspect) + \
                       np.cos(slope) * np.sin((radmatI[index, 0] * deg2rad))

            suniroof[suniroof < 0] = 0

            # Solar Incidence angle (Walls)
            suniwall = np.abs(np.sin(np.pi/2) * np.cos(radmatI[index, 0] * deg2rad) * np.cos((radmatI[index, 1] * deg2rad) - dirwalls*deg2rad)
                              + np.cos(np.pi/2) * np.sin((radmatI[index, 0] * deg2rad)))

            # Shadow image
            if usevegdem == 1:
                vegsh, sh, _, wallsh, wallsun, wallshve, _, facesun = shadowingfunction_wallheight_23(a,vegdem,vegdem2,
                                            radmatI[index, 1],radmatI[index, 0],scale,amaxvalue,bush, walls, dirwalls)
                shadow = np.copy(sh-(1-vegsh)*(1-psi))
            else:
                sh, wallsh, wallsun, facesh, facesun = shadowingfunction_wallheight_13(a, radmatI[index, 1],
                                                                                  radmatI[index, 0],
                                                                                  scale,
                                                                                  walls, dirwalls)
                shadow = np.copy(sh)

            #np.savetxt("sh/sh_%s.txt" % (index+1,) , sh, delimiter=',')
            # roof irradiance calculation
            # direct radiation
            if radmatI[index, 2] > 0:
                I = shadow * radmatI[index, 2] * suniroof
            else:
                I = np.copy(Knight)

            # roof diffuse and reflected radiation
            D = radmatD[index, 2] * shadow
            R = radmatR[index, 2] * (shadow*-1 + 1)

            Energyyearroof = np.copy(Energyyearroof+D+R+I)
            # radplot = np.copy(D+R+I)

            # WALL IRRADIANCE
            # direct radiation

            if radmatI[index, 2] > 0:
                Iw = radmatI[index, 2] * suniwall    # wall
            else:
                Iw = np.copy(Knight)

            # wall diffuse and reflected radiation
            Dw = radmatD[index, 2] * facesun
            Rw = radmatR[index, 2] * facesun

            # for each wall level (1 meter interval)
            wallsun = np.floor(wallsun*(1/voxelheight))*voxelheight
            wallsh = np.floor(wallsh*(1/voxelheight))*voxelheight
            if usevegdem == 1:
                wallshve = np.floor(wallshve*(1/voxelheight))*voxelheight

            wallmatrix = wallmatrix * 0

            for p in range(np.shape(wallmatrix)[0]):
                if wallsun[wallrow[p], wallcol[p]] > 0:    # Sections in sun
                    if wallsun[wallrow[p], wallcol[p]] == wallstot[wallrow[p], wallcol[p]]:    # Sections in sun
                        wallmatrix[p, 0:wallstot[wallrow[p], wallcol[p]]/voxelheight] = Iw[wallrow[p], wallcol[p]] + \
                                                                                        Dw[wallrow[p], wallcol[p]] + \
                                                                                        Rw[wallrow[p], wallcol[p]]
                    else:
                        wallmatrix[p, ((wallstot[wallrow[p], wallcol[p]] -
                                        wallsun[wallrow[p], wallcol[p]])/voxelheight) - 1:
                                        wallstot[wallrow[p], wallcol[p]]/voxelheight] = Iw[wallrow[p], wallcol[p]] + \
                                                                                        Dw[wallrow[p], wallcol[p]] + \
                                                                                        Rw[wallrow[p], wallcol[p]]

                if usevegdem == 1 and wallshve[wallrow[p], wallcol[p]] > 0:    # sections in vegetation shade
                    wallmatrix[p, 0:wallshve[wallrow[p], wallcol[p] + wallsh[wallrow[p], wallcol[p]]]/voxelheight] = \
                        (Iw[wallrow[p], wallcol[p]] + Dw[wallrow[p], wallcol[p]])*psi

                if wallsh[wallrow[p], wallcol[p]] > 0:    # sections in building shade
                    wallmatrix[p, 0:wallsh[wallrow[p], wallcol[p]] / voxelheight] = Rw[wallrow[p], wallcol[p]]

            Energyyearwall = Energyyearwall + np.copy(wallmatrix)

            if calc_month:
                for t in range(3, 15):
                    # ROFF IRRADIANCE
                    # direct radiation
                    if radmatI[index, t] > 0:
                        I = shadow*radmatI[index, t] * suniroof     # roof
                    else:
                        I = np.copy(Knight)

                    # roof diffuse and reflected radiation
                    D = radmatD[index, t] * shadow
                    R = radmatR[index, t] * (shadow*-1+1)
                    Energymonthroof[:, :, t-3] = Energymonthroof[:, :, t-3] + D + R + I

                    # WALL IRRADIANCE
                    # direct radiation
                    if radmatI[index, t] > 0:
                        Iw = radmatI[index, t] * suniwall    # wall
                    else:
                        Iw = np.copy(Knight)

                    # wall diffuse and reflected radiation
                    Dw = (radmatD[index, t] * facesun)
                    Rw = (radmatR[index, t] * facesun)

                    # for each wall level (1 meter interval)
                    wallsun = np.floor(wallsun)
                    wallsh = np.floor(wallsh)

                    wallshve = np.floor(wallshve)
                    wallmatrix = wallmatrix * 0

                    for p in range(np.shape(wallmatrix)[0]):
                        if wallsun[wallrow[p], wallcol[p]] > 0:    # Sections in sun
                            if wallsun[wallrow[p], wallcol[p]] == wallstot[wallrow[p], wallcol[p]]:    # Sections in sun
                                wallmatrix[p, 0:wallstot[wallrow[p], wallcol[p]]/voxelheight] = Iw[wallrow[p], wallcol[p]] + \
                                                                                                Dw[wallrow[p], wallcol[p]] + \
                                                                                                Rw[wallrow[p], wallcol[p]]
                            else:
                                wallmatrix[p, (wallstot[wallrow[p], wallcol[p]] -
                                           wallsun[wallrow[p], wallcol[p]] / voxelheight) - 1:
                                           wallstot[wallrow[p], wallcol[p]] / voxelheight] = Iw[wallrow[p], wallcol[p]] + \
                                                                                             Dw[wallrow[p], wallcol[p]] + \
                                                                                             Rw[wallrow[p], wallcol[p]]

                        if wallshve[wallrow[p], wallcol[p]] > 0:    # sections in vegetation shade
                            wallmatrix[p, 0:wallshve[wallrow[p],
                                                     (wallcol[p] + wallsh[wallrow[p], wallcol[p]])]/voxelheight] = \
                                (Iw[wallrow[p], wallcol[p]] + Dw[wallrow[p], wallcol[p]]) * psi

                        if wallsh[wallrow[p], wallcol[p]] > 0:    # sections in building shade
                            wallmatrix[p, 0:wallsh[wallrow[p], wallcol[p]]/voxelheight] = Rw[wallrow[p], wallcol[p]]

                    Energymonthwall[:, :, t-3] = Energymonthwall[:, :, t-3] + np.copy(wallmatrix)

            # TODO: Month is not working
            # if calc_month:
            #     for p in range(len(Dmonth)):
            #         Iradmonth = (shadow * radmat[index, 3+p] * suniroof)
            #         DGradmonth = (shadow * Dmonth[p] + (shadow*-1+1) * Gmonth[p] * albedo) * svf
            #         Energymonthroof[:, :, p] = Energymonthroof[:, :, p] + Iradmonth + DGradmonth

            index = index + 1

            ## HaR ska progressbaren emitta

    ## Including radiation from ground on walls as well as removing pixels high than walls
    print np.copy(Energyyearwall).shape
    wallmatrixbol = (Energyyearwall > 0).astype(float)
    Energyyearwall = (Energyyearwall + (np.sum(radmatR[:, 2]) * albedo)/2) * wallmatrixbol

    Energyyearroof /= 1000

    Energyyearwall /= 1000

    #Energyyearwall = np.hstack((np.transpose(np.atleast_2d(wallrow)),
    #                            np.transpose(np.atleast_2d(wallcol)), Energyyearwall))
    Energyyearwall = np.transpose(np.vstack((wallrow + 1, wallcol + 1, np.transpose(Energyyearwall))))    # adding 1 to wallrow and wallcol so that the tests pass

    if calc_month:
        for t in range(3, 15):
            Energymonthwall[:, :, t-3] = (Energymonthwall[:, :, t-3] + (np.sum(radmatR[:, t])*albedo)/2) * wallmatrixbol
    else:
        Energymonthwall = np.array([])

    if calc_month:
        return Energyyearroof, Energyyearwall, Energymonthroof, Energymonthwall
    else:
        return Energyyearroof, Energyyearwall, vegdata

