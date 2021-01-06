# -*- coding: utf-8 -*-
from __future__ import division
import numpy as np
from math import radians,pi
from scipy.ndimage.filters import median_filter,gaussian_filter
def shadowingfunction_wallheight(a, azimuth, altitude, scale, walls, aspect,
                                 vegdem=None, vegdem2=None, amaxvalue=0, bush=0,call_index=0):
    """
    This function calculates shadows on a DSM and shadow height on building
    walls.

    INPUTS:
    a = DSM
    azimuth and altitude = sun position
    scale= scale of DSM (1 meter pixels=1, 2 meter pixels=0.5)
    walls= pixel row 'outside' buildings. will be calculated if empty
    aspect = normal aspect of buildings walls
    
    OUTPUT:
    sh=ground and roof shadow
    wallsh = height of wall that is in shadow
    wallsun = hieght of wall that is in sun

    original Matlab code by:
    Fredrik Lindberg 2012-03-19
    fredrikl@gvc.gu.se
    
    Update 2013-03-13 - bugfix for walls alinged with sun azimuths

    :param a:
    :param vegdem:
    :param vegdem2:
    :param azimuth:
    :param altitude:
    :param scale:
    :param amaxvalue:
    :param bush:
    :param walls:
    :param aspect:
    :return:
    """

    # conversion
    #degrees = np.pi/180

    azimuth = radians(azimuth)
    altitude = radians(altitude)

    # measure the size of the image

    sizex = np.shape(a)[0]
    sizey = np.shape(a)[1]

    # initialise parameters
    f = np.copy(a)
    dx = 0
    dy = 0
    dz = 0

    temp = np.zeros((sizex, sizey))
    index = 1
    wallbol = (walls > 0).astype(float)
    wallbol[wallbol == 0] = np.nan

    # other loop parameters
    pibyfour = np.pi/4
    threetimespibyfour = 3*pibyfour
    fivetimespibyfour = 5*pibyfour
    seventimespibyfour = 7*pibyfour
    sinazimuth = np.sin(azimuth)
    cosazimuth = np.cos(azimuth)
    tanazimuth = np.tan(azimuth)
    signsinazimuth = np.sign(sinazimuth)
    signcosazimuth = np.sign(cosazimuth)
    dssin = np.abs(1/sinazimuth)
    dscos = np.abs(1/cosazimuth)
    tanaltitudebyscale = np.tan(altitude)/scale

    if not amaxvalue:
        amaxvalue = np.max(a)

    if vegdem is not None and vegdem2 is not None:
        tempvegdem = np.zeros((sizex, sizey))
        tempvegdem2 = np.zeros((sizex, sizey))
        sh = np.zeros((sizex, sizey))
        vbshvegsh = np.copy(sh)
        vegsh = np.copy(sh)
        shvoveg = np.copy(vegdem)    # for vegetation shadowvolume
        g = np.copy(sh)
        bushplant = bush > 1
    elif (vegdem is not None and vegdem2 is None) or (vegdem is None and vegdem2 is not None):
        raise ValueError("Error with inputs, pass both vegdem and vegdem2 or neither, as args")

    usevegdem = vegdem is not None and vegdem2 is not None

    while True:
        if (pibyfour <= azimuth and azimuth < threetimespibyfour) or \
           (fivetimespibyfour <= azimuth and azimuth<seventimespibyfour):
            dy = signsinazimuth*index
            dx = -1*signcosazimuth*np.abs(np.round(index/tanazimuth))
            ds = dssin
        else:
            dy = signsinazimuth*abs(round(index*tanazimuth))
            dx = -1*signcosazimuth*index
            ds = dscos

        # note: dx and dy represent absolute values while ds is an incremental value
        dz = ds*index*tanaltitudebyscale
        if not((amaxvalue >= dz) and (np.abs(dx) < sizex) and (np.abs(dy) < sizey)):
            break
        temp[0:sizex, 0:sizey] = 0
        if usevegdem:
            tempvegdem[0:sizex, 0:sizey] = 0
            tempvegdem2[0:sizex, 0:sizey] = 0

        absdx = np.abs(dx)
        absdy = np.abs(dy)

        xc1 = int((dx+absdx)/2)
        xc2 = int(sizex+(dx-absdx)/2)
        yc1 = int((dy+absdy)/2)
        yc2 = int(sizey+(dy-absdy)/2)

        xp1 = -int((dx-absdx)/2)
        xp2 = int(sizex-(dx+absdx)/2)
        yp1 = -int((dy-absdy)/2)
        yp2 = int(sizey-(dy+absdy)/2)


        temp[xp1:xp2, yp1:yp2] = a[xc1:xc2, yc1:yc2] - dz

        #f = np.maximum([f, temp], axis=0)
        f=np.maximum(f,temp)

        if usevegdem:
            tempvegdem[xp1:xp2, yp1:yp2] = vegdem[xc1:xc2, yc1:yc2] - dz
            tempvegdem2[xp1:xp2, yp1:yp2] = vegdem2[xc1:xc2, yc1:yc2] - dz

            shvoveg = np.max([shvoveg, tempvegdem], axis=0)
            sh[f > a] = 1
            sh[f <= a] = 0   # Moving building shadow
            fabovea = (tempvegdem > a).astype(int)   # vegdem above DEM
            gabovea = (tempvegdem2 > a).astype(int)   # vegdem2 above DEM
            vegsh2 = fabovea - gabovea
            vegsh = np.max([vegsh, vegsh2], axis=0)
            vegsh[vegsh*sh > 0] = 0    # removing shadows 'behind' buildings
            vbshvegsh = np.copy(vegsh) + vbshvegsh

            # vegsh at high sun altitudes
            if index == 1:
                firstvegdem = np.copy(tempvegdem) - np.copy(temp)
                firstvegdem[firstvegdem <= 0] = 1000
                vegsh[firstvegdem < dz] = 1
                vegsh *= (vegdem2 > a)
                vbshvegsh = np.zeros((sizex, sizey))

            # Bush shadow on bush plant
            if np.max(bush) > 0 and np.max(fabovea*bush) > 0:
                tempbush = np.zeros((sizex, sizey))
                tempbush[xp1:xp2, yp1:yp2] = bush[xc1:xc2, yc1:yc2] - dz
                g = np.max([g, tempbush], axis=0)
                g = bushplant * g

        index += 1

    # Removing walls in shadow due to selfshadowing
    azilow = azimuth-pi/2
    azihigh = azimuth+pi/2

    if azilow >= 0 and azihigh < 2*pi:    # 90 to 270  (SHADOW)
        facesh = np.logical_or(aspect < azilow, aspect >= azihigh).astype(float) - wallbol + 1
    elif azilow < 0 and azihigh <= 2*pi:    # 0 to 90
        azilow += 2*pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh) * -1 + 1    # (SHADOW)    # check for the -1
    elif azilow > 0 and azihigh >= 2*pi:    # 270 to 360
        azihigh -= 2 * pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh)*-1 + 1    # (SHADOW)
    #facesh=facesh.astype(int)

    sh = np.copy(f-a)    #shadow volume

    if not usevegdem:    # shadowing_13 case
        facesun = np.logical_and( (facesh + (walls > 0).astype(int)) == 1, walls > 0).astype(float)
        wallsun = np.copy(walls-sh)
        wallsun[wallsun < 1/scale] = 0
        wallsun[facesh == 1] = 0    # Removing walls in "self"-shadow
        wallsh = np.copy(walls-wallsun)

        sh = np.logical_not(np.logical_not(sh)).astype(float)
        sh = sh*-1 + 1

        return sh, wallsh, wallsun, facesh, facesun
    else:               # shadowing_23 case
        sh = 1-sh
        vbshvegsh[vbshvegsh > 0] = 1
        vbshvegsh = vbshvegsh-vegsh

        if np.max(bush) > 0:
            g = g-bush
            g[g > 0] = 1
            g[g < 0] = 0
            vegsh = vegsh-bushplant+g
            vegsh[vegsh < 0] = 0

        vegsh[vegsh > 0] = 1
        shvoveg = (shvoveg-a) * vegsh    # Vegetation shadow volume
        vegsh = 1-vegsh
        vbshvegsh = 1-vbshvegsh

        #removing walls in shadow
        # tempfirst=tempfirst-a;
        # tempfirst(tempfirst<2)=1;
        # tempfirst(tempfirst>=2)=0;

        shvo = f - a   # building shadow volume

        facesun = np.logical_and(facesh + (walls > 0).astype(float) == 1, walls > 0).astype(float)

        wallsun = np.copy(walls-shvo)
        wallsun[wallsun < 0] = 0
        wallsun[facesh == 1] = 0    # Removing walls in "self"-shadow
        wallsh = np.copy(walls-wallsun)
        wallbol = (walls > 0).astype(float)

        wallshve = shvoveg * wallbol
        wallshve = wallshve - wallsh
        wallshve[wallshve < 0] = 0
        id = np.where(wallshve > walls)
        wallshve[id] = walls[id]
        wallsun = wallsun-wallshve    # problem with wallshve only
        id = np.where(wallsun < 0)
        wallshve[id] = 0
        wallsun[id] = 0

        return vegsh, sh, vbshvegsh, wallsh, wallsun, wallshve, facesh, facesun