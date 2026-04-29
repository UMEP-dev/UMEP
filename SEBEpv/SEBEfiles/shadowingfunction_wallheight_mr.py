# -*- coding: utf-8 -*-
# from __future__ import division
import numpy as np
from math import radians


def shadowingfunction_wallheight_13(a, azimuth, altitude, scale, walls, aspect):
    """
    This m.file calculates shadows on a DSM and shadow height on building
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
    
    Fredrik Lindberg 2012-03-19  (original author)
    fredrikl@gvc.gu.se
    
     Utdate 2013-03-13 - bugfix for walls alinged with sun azimuths
     
    Changes by Michael Revesz 
    revesz.michael@gmail.com (michael.revesz@ait.ac.at)
    
    2017 - new ground-reflection algorithm

    :param a:
    :param azimuth:
    :param altitude:
    :param scale:
    :param walls:
    :param aspect:
    :return:
    """

    if not walls.size:
        """
        walls = ordfilt2(a,4,[0 1 0; 1 0 1; 0 1 0])
        walls = walls-a
        walls[walls < 3]=0
        sizex = np.shape(a)[0]    #might be wrong
        sizey = np.shape(a)[1]
        dirwalls = filter1Goodwin_as_aspect_v3(walls,sizex,sizey,scale,a);
        aspect = dirwalls*np.pi/180
        """

    # conversion
    azimuth = radians(azimuth)
    altitude = radians(altitude)

    # measure the size of the image
    sizex = np.shape(a)[0]   # NOTE: x and y coordinates are interchanged in comparison to sebeworker!!
    sizey = np.shape(a)[1]

    # initialise parameters
    f = np.copy(a)
    a_inv = np.copy(a) * (-1)              # for gnd-reflect; i.e. z-inverse dsm (former a2)
    a_inv_w = np.copy(a) * (-1) - walls    # for gnd-reflect; envelope around walls & a_inv
    f_inv = np.copy(a_inv)                 # ground shadow volume (in direction of negative z)
    dx = 0
    dy = 0
    dz = 0
    temp = np.zeros((sizex, sizey))
    temp2 = np.zeros((sizex, sizey))      # for gnd-reflect
    index = 0   # better, if walls are outside the building
    wallbol = (walls > 0).astype(float)

    # status of surface coordinates regarding hit walls: 0=never hit, 1=hit a wall, 2=hit walls and then non-wall
    status_hit_wall = np.zeros((sizex, sizey))

    # other loop parameters
    amaxvalue = np.max(a) - np.min(a)   # this is enough! max(a) might be much larger, if e.g. min(a) = 200
    pibyfour = np.pi/4
    threetimespibyfour = 3 * pibyfour
    sinazimuth = np.sin(azimuth)
    cosazimuth = np.cos(azimuth)
    tanazimuth = np.tan(azimuth)
    signsinazimuth = np.sign(sinazimuth)
    signcosazimuth = np.sign(cosazimuth)
    dssin = np.abs(1/sinazimuth)
    dscos = np.abs(1/cosazimuth)
    tanaltitudebyscale = np.tan(altitude)/scale

    # Removing walls in shadow due to selfshadowing
    azilow = azimuth-np.pi/2
    azihigh = azimuth+np.pi/2

    # new method for calc facesh, facesun (M. Revesz, 09.04.2018):
    if azilow < 0:              # azimuth (0;90)
        azilow += 2*np.pi
        facesun = np.logical_or(aspect > azilow, aspect < azihigh).astype(float)
    elif azihigh > (2*np.pi):   # azimuth (270;360]
        azihigh -= 2*np.pi
        facesun = np.logical_or(aspect > azilow, aspect < azihigh).astype(float)
    else:                       # azimuth [90;270]
        facesun = np.logical_and(aspect > azilow, aspect < azihigh).astype(float)
    facesh = (facesun * -1) + 1
    facesun *= wallbol   # can only be 1 where walls!
    facesh *= wallbol    # can only be 1 where walls!

    # main loop
    while (amaxvalue >= dz) and (np.abs(dx) < sizex) and (np.abs(dy) < sizey):
        if azimuth > np.pi:
            azimuth -= np.pi
        else:
            pass
        if (pibyfour <= azimuth) and (azimuth < threetimespibyfour):
            dy = signsinazimuth*index
            dx = -1*signcosazimuth*np.abs(np.round(index/tanazimuth))
            ds = dssin
        else:
            dy = signsinazimuth*abs(round(index*tanazimuth))
            dx = -1*signcosazimuth*index
            ds = dscos

        # note: dx, dy, dz represent absolute values while ds is an incremental value
        dz = ds*index*tanaltitudebyscale
        temp[0:sizex, 0:sizey] = 0
        temp2 = temp2 * 0      # for gnd-reflect, temporary

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

        f = np.max([f, temp], axis=0)

        # Ground reflectance on wall:
        temp2[xp1:xp2, yp1:yp2] = a_inv[xc1:xc2, yc1:yc2] - dz    # temporary for moving ground view volume
        if index == 0:
            dz_buffer = 0
        else:
            dz_buffer = dz/index
        # Check if gnd-refl volume lies within a wall (& facing to irrad source):
        bool_hit_wall = np.logical_and(
                            np.logical_and(temp2 > (a_inv_w - dz_buffer), temp2 <= f_inv), facesun)
        bool_hit_wall[xp1:xp2, yp1:yp2] = np.logical_and(bool_hit_wall[xp1:xp2, yp1:yp2],
                                                         status_hit_wall[xc1:xc2, yc1:yc2] < 2)
        # de-activate gnd-pixel for future:
        #   1st cond: previously a point did not or at last time hit a wall
        status_hit_wall[xc1:xc2, yc1:yc2] = np.where(np.logical_and(bool_hit_wall[xp1:xp2, yp1:yp2],
                                                                    (status_hit_wall[xc1:xc2, yc1:yc2] < 2)),
                                                     1, status_hit_wall[xc1:xc2, yc1:yc2])
        #   2nd cond: last time a point hit a wall, now not anymore
        status_hit_wall[xc1:xc2, yc1:yc2] = np.where(np.logical_and(np.logical_not(bool_hit_wall[xp1:xp2, yp1:yp2]),
                                                     (status_hit_wall[xc1:xc2, yc1:yc2] == 1)),
                                                     2, status_hit_wall[xc1:xc2, yc1:yc2])
        # Update gnd-refl. volume:
        f_inv = np.where(bool_hit_wall, temp2, f_inv)

        index = index+1
    wshinv = (np. copy(f_inv) * (-1) - a)       # profile of ground reflectance on wall

    sh = np.copy(f-a)    # shadow volume
    wallsun = facesun * np.copy(walls-sh)   # Calc wallheight in shadow + remove walls in "self"-shadow
    wallsun[wallsun < 0] = 0
    wallsh = np.copy(walls-wallsun)

    sh = np.logical_not(sh).astype(float)

    # subplot(2,2,1),imagesc(facesh),axis image ,colorbar,title('facesh')#
    # subplot(2,2,2),imagesc(wallsh,[0 20]),axis image, colorbar,title('Wallsh')#
    # subplot(2,2,3),imagesc(sh), colorbar,axis image,title('Groundsh')#
    # subplot(2,2,4),imagesc(wallsun,[0 20]),axis image, colorbar,title('Wallsun')#

    return sh, wallsh, wallsun, facesh, facesun, wshinv
