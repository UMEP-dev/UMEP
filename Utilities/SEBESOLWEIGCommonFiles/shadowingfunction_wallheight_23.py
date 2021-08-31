from __future__ import division
import numpy as np
# import matplotlib.pylab as plt
def shadowingfunction_wallheight_23(a, vegdem, vegdem2, azimuth, altitude, scale, amaxvalue, bush, walls, aspect):
    """
    This function calculates shadows on a DSM and shadow height on building
    walls including both buildings and vegetion units.
    New functionallity to deal with pergolas, August 2021
    
    INPUTS:
    a = DSM
    vegdem = Vegetation canopy DSM (magl)
    vegdem2 = Trunkzone DSM (magl)
    azimuth and altitude = sun position
    scale= scale of DSM (1 meter pixels=1, 2 meter pixels=0.5)
    walls= pixel row 'outside' buildings. will be calculated if empty
    aspect=normal aspect of walls
    
    OUTPUT:
    sh=ground and roof shadow

    wallsh = height of wall that is in shadow
    wallsun = hieght of wall that is in sun

    original Matlab code:
    Fredrik Lindberg 2013-08-14
    fredrikl@gvc.gu.se

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
    degrees = np.pi/180.
    azimuth *= degrees
    altitude *= degrees
    
    # measure the size of the image
    sizex = np.shape(a)[0]
    sizey = np.shape(a)[1]
    
    # initialise parameters
    dx = 0
    dy = 0
    dz = 0
    temp = np.zeros((sizex, sizey))
    tempvegdem = np.zeros((sizex, sizey))
    tempvegdem2 = np.zeros((sizex, sizey))
    templastfabovea = np.zeros((sizex, sizey))
    templastgabovea = np.zeros((sizex, sizey))
    bushplant = bush > 1
    sh = np.zeros((sizex, sizey)) #shadows from buildings
    vbshvegsh = np.copy(sh) #vegetation blocking buildings
    vegsh = np.add(np.zeros((sizex, sizey)), bushplant, dtype=float) #vegetation shadow
    f = np.copy(a)
    shvoveg = np.copy(vegdem) # for vegetation shadowvolume
    # g = np.copy(sh)
    wallbol = (walls > 0).astype(float)

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

    index = 0

    # new case with pergola (thin vertical layer of vegetation), August 2021
    dzprev = 0

    # main loop
    while (amaxvalue >= dz) and (np.abs(dx) < sizex) and (np.abs(dy) < sizey):
        if ((pibyfour <= azimuth) and (azimuth < threetimespibyfour)) or ((fivetimespibyfour <= azimuth) and (azimuth < seventimespibyfour)):
            dy = signsinazimuth * index
            dx = -1 * signcosazimuth * np.abs(np.round(index / tanazimuth))
            ds = dssin
        else:
            dy = signsinazimuth * np.abs(np.round(index * tanazimuth))
            dx = -1 * signcosazimuth * index
            ds = dscos

        # note: dx and dy represent absolute values while ds is an incremental value
        dz = (ds * index) * tanaltitudebyscale
        tempvegdem[0:sizex, 0:sizey] = 0
        tempvegdem2[0:sizex, 0:sizey] = 0
        temp[0:sizex, 0:sizey] = 0
        templastfabovea[0:sizex, 0:sizey] = 0.
        templastgabovea[0:sizex, 0:sizey] = 0.
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

        tempvegdem[xp1:xp2, yp1:yp2] = vegdem[xc1:xc2, yc1:yc2] - dz
        tempvegdem2[xp1:xp2, yp1:yp2] = vegdem2[xc1:xc2, yc1:yc2] - dz
        temp[xp1:xp2, yp1:yp2] = a[xc1:xc2, yc1:yc2]-dz

        f = np.fmax(f, temp) #Moving building shadow
        shvoveg = np.fmax(shvoveg, tempvegdem) # moving vegetation shadow volume
        sh[f > a] = 1
        sh[f <= a] = 0   
        fabovea = (tempvegdem > a).astype(int)   #vegdem above DEM
        gabovea = (tempvegdem2 > a).astype(int)   #vegdem2 above DEM
        
        #new pergola condition
        templastfabovea[xp1:xp2, yp1:yp2] = vegdem[xc1:xc2, yc1:yc2]-dzprev
        templastgabovea[xp1:xp2, yp1:yp2] = vegdem2[xc1:xc2, yc1:yc2]-dzprev
        lastfabovea = templastfabovea > a
        lastgabovea = templastgabovea > a
        dzprev = dz
        vegsh2 = np.add(np.add(np.add(fabovea, gabovea, dtype=float),lastfabovea, dtype=float),lastgabovea, dtype=float)
        vegsh2[vegsh2 == 4] = 0.
        # vegsh2[vegsh2 == 1] = 0. # This one is the ultimate question...
        vegsh2[vegsh2 > 0] = 1.

        # vegsh2 = fabovea - gabovea #old without pergolas
        # vegsh = np.max([vegsh, vegsh2], axis=0) #old without pergolas

        vegsh = np.fmax(vegsh, vegsh2)
        vegsh[vegsh*sh > 0] = 0    
        vbshvegsh = np.copy(vegsh) + vbshvegsh # removing shadows 'behind' buildings

        # # vegsh at high sun altitudes # Not needed when pergolas are included
        # if index == 0:
        #     firstvegdem = np.copy(tempvegdem) - np.copy(temp)
        #     firstvegdem[firstvegdem <= 0] = 1000
        #     vegsh[firstvegdem < dz] = 1
        #     vegsh *= (vegdem2 > a)
        #     vbshvegsh = np.zeros((sizex, sizey))

        # # Bush shadow on bush plant # Not needed when pergolas are included
        # if np.max(bush) > 0 and np.max(fabovea*bush) > 0:
        #     tempbush = np.zeros((sizex, sizey))
        #     tempbush[int(xp1):int(xp2), int(yp1):int(yp2)] = bush[int(xc1):int(xc2), int(yc1):int(yc2)] - dz
        #     g = np.max([g, tempbush], axis=0)
        #     g = bushplant * g
    
        index += 1

    # Removing walls in shadow due to selfshadowing
    azilow = azimuth - np.pi/2
    azihigh = azimuth + np.pi/2
    if azilow >= 0 and azihigh < 2*np.pi:    # 90 to 270  (SHADOW)
        facesh = np.logical_or(aspect < azilow, aspect >= azihigh).astype(float) - wallbol + 1    # TODO check
    elif azilow < 0 and azihigh <= 2*np.pi:    # 0 to 90
        azilow = azilow + 2*np.pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh) * -1 + 1    # (SHADOW)
    elif azilow > 0 and azihigh >= 2*np.pi:    # 270 to 360
        azihigh -= 2 * np.pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh)*-1 + 1    # (SHADOW)

    sh = 1-sh
    vbshvegsh[vbshvegsh > 0] = 1
    vbshvegsh = vbshvegsh-vegsh
    
    # if np.max(bush) > 0: # Not needed when pergolas are included
    #     g = g-bush
    #     g[g > 0] = 1
    #     g[g < 0] = 0
    #     vegsh = vegsh-bushplant+g
    #     vegsh[vegsh < 0] = 0

    vegsh[vegsh > 0] = 1
    shvoveg = (shvoveg-a) * vegsh    #Vegetation shadow volume
    vegsh = 1-vegsh
    vbshvegsh = 1-vbshvegsh
    
    # wall shadows
    shvo = f - a   # building shadow volume
    facesun = np.logical_and(facesh + (walls > 0).astype(float) == 1, walls > 0).astype(float)
    wallsun = np.copy(walls-shvo)
    wallsun[wallsun < 0] = 0
    wallsun[facesh == 1] = 0    # Removing walls in "self"-shadow
    wallsh = np.copy(walls-wallsun)

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
