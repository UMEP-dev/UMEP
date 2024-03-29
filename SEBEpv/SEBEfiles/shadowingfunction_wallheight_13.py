# -*- coding: utf-8 -*-
from __future__ import division
import numpy as np
from math import radians

try:
    from scipy.ndimage.filters import median_filter
except Exception as e:
    QMessageBox.warning(None, 'Error', 'Many tools in UMEP requires the scipy package '
                                        'to be installed. Please consult the FAQ in the manual for further '
                                        'information on how to install missing python packages.')



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
    
    Fredrik Lindberg 2012-03-19
    fredrikl@gvc.gu.se
    
     Utdate 2013-03-13 - bugfix for walls alinged with sun azimuths

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
    degrees = np.pi/180
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
    #wallbol[wallbol == 0] = np.nan
    # np.savetxt("wallbol.txt",wallbol)
    # other loop parameters
    amaxvalue = np.max(a)
    pibyfour = np.pi/4
    threetimespibyfour = 3 * pibyfour
    fivetimespibyfour = 5 * pibyfour
    seventimespibyfour = 7 * pibyfour
    sinazimuth = np.sin(azimuth)
    cosazimuth = np.cos(azimuth)
    tanazimuth = np.tan(azimuth)
    signsinazimuth = np.sign(sinazimuth)
    signcosazimuth = np.sign(cosazimuth)
    dssin = np.abs(1/sinazimuth)
    dscos = np.abs(1/cosazimuth)
    tanaltitudebyscale = np.tan(altitude)/scale

    # main loop
    while (amaxvalue >= dz) and (np.abs(dx) < sizex) and (np.abs(dy) < sizey):

        if (pibyfour <= azimuth and azimuth < threetimespibyfour) or \
                (fivetimespibyfour <= azimuth and azimuth < seventimespibyfour):
            dy = signsinazimuth*index
            dx = -1*signcosazimuth*np.abs(np.round(index/tanazimuth))
            ds = dssin
        else:
            dy = signsinazimuth*abs(round(index*tanazimuth))
            dx = -1*signcosazimuth*index
            ds = dscos

        # note: dx and dy represent absolute values while ds is an incremental value
        dz = ds*index*tanaltitudebyscale
        temp[0:sizex, 0:sizey] = 0

        absdx = np.abs(dx)
        absdy = np.abs(dy)

        xc1 = ((dx+absdx)/2)
        xc2 = (sizex+(dx-absdx)/2)
        yc1 = ((dy+absdy)/2)
        yc2 = (sizey+(dy-absdy)/2)

        xp1 = -((dx-absdx)/2)
        xp2 = (sizex-(dx+absdx)/2)
        yp1 = -((dy-absdy)/2)
        yp2 = (sizey-(dy+absdy)/2)

        temp[xp1:xp2, yp1:yp2] = a[xc1:xc2, yc1:yc2] - dz

        f = np.max([f, temp], axis=0)

        index = index+1

    # Removing walls in shadow due to selfshadowing
    azilow = azimuth-np.pi/2
    azihigh = azimuth+np.pi/2

    if azilow >= 0 and azihigh < 2*np.pi:    # 90 to 270  (SHADOW)
        facesh = (np.logical_or(aspect < azilow, aspect >= azihigh).astype(float)-wallbol+1)
    elif azilow < 0 and azihigh <= 2*np.pi:    # 0 to 90
        azilow = azilow + 2*np.pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh) * -1 + 1    # (SHADOW)    # check for the -1
    elif azilow > 0 and azihigh >= 2*np.pi:    # 270 to 360
        azihigh = azihigh-2*np.pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh)*-1 + 1    # (SHADOW)

    sh = np.copy(f-a)    # shadow volume
    facesun = np.logical_and(facesh + (walls > 0).astype(float) == 1, walls > 0).astype(float)
    wallsun = np.copy(walls-sh)
    wallsun[wallsun < 0] = 0
    wallsun[facesh == 1] = 0    # Removing walls in "self"-shadow
    wallsh = np.copy(walls-wallsun)

    sh = np.logical_not(np.logical_not(sh)).astype(float)
    sh = sh*-1 + 1

    # subplot(2,2,1),imagesc(facesh),axis image ,colorbar,title('facesh')#
    # subplot(2,2,2),imagesc(wallsh,[0 20]),axis image, colorbar,title('Wallsh')#
    # subplot(2,2,3),imagesc(sh), colorbar,axis image,title('Groundsh')#
    # subplot(2,2,4),imagesc(wallsun,[0 20]),axis image, colorbar,title('Wallsun')#

    ## old stuff
    #     if index==0 #removing shadowed walls at first iteration
    #         tempfirst(1:sizex,1:sizey)=0;
    #         tempfirst(xp1:xp2,yp1:yp2)= a(xc1:xc2,yc1:yc2);
    #         tempfirst=tempfirst-a;
    #         tempfirst(tempfirst<2)=1;# 2 is smallest wall height. Should be variable
    #         tempfirst(tempfirst>=2)=0;# walls in shadow at first movment (iteration)
    #         tempwalls(1:sizex,1:sizey)=0;
    #         tempwalls(xp1:xp2,yp1:yp2)= wallbol(xc1:xc2,yc1:yc2);
    #         wallfirst=tempwalls.*wallbol;#wallpixels potentially shaded by adjacent wall pixels
    #         wallfirstaspect=aspect.*wallfirst;
    #         azinormal=azimuth-pi/2;
    #         if azinormal<=0,azinormal=azinormal+2*pi;end
    #         facesh=double(wallfirstaspect<azinormal|tempfirst<=0);
    #         facesun=double((facesh+double(walls>0))==1);
    #     end


    # Removing walls in shadow due to selfshadowing (This only works on
    # regular arrays)
    #     if dy~=0 && firsty==0
    #         if yp1>1
    #             yp1f=2;yp2f=sizey;
    #             yc1f=1;yc2f=sizey-1;
    #         else
    #             yp1f=1;yp2f=sizey-1;
    #             yc1f=2;yc2f=sizey;
    #         end
    #         firsty=1;
    #     end
    #     if dx~=0 && firstx==0
    #         if xp1>1
    #             xp1f=2;xp2f=sizex;
    #             xc1f=1;xc2f=sizex-1;
    #         else
    #             xp1f=1;xp2f=sizex-1;
    #             xc1f=2;xc2f=sizex;
    #         end
    #         firstx=1;
    #     end
    #     if firsty==1 && firstx==1
    #         facesh(xp1f:xp2f,yp1f:yp2f)= a(xc1f:xc2f,yc1f:yc2f);
    #         facesh=facesh-a;
    #         facesh(facesh<=0)=0;
    #         facesh(facesh>0)=1;
    #     end


    #     if index<3 #removing shadowed walls 1
    #         tempfirst(1:sizex,1:sizey)=0;
    #         tempfirst(xp1:xp2,yp1:yp2)= a(xc1:xc2,yc1:yc2);
    #         #removing walls in shadow
    #         tempfirst=tempfirst-a;
    #         tempfirst(tempfirst<2)=1;# 2 is smallest wall height. Should be variable
    #         tempfirst(tempfirst>=2)=0;
    #         if index==1 # removing shadowed walls 2
    #             tempwalls(1:sizex,1:sizey)=0;
    #             tempwalls(xp1:xp2,yp1:yp2)= wallbol(xc1:xc2,yc1:yc2);
    #             #             wallfirst=((tempwalls+wallbol).*wallbol)==2;
    #             wallfirst=tempwalls.*wallbol;
    #             wallfirstaspect=aspect.*wallfirst;#.*wallbol
    #             #             wallfirstaspect(wallfirstaspect==0)=NaN;
    #             wallfirstsun=wallfirstaspect>(azimuth-pi/2);
    #             #             wallfirstsun=(wallfirstaspect>=azimuth-pi/2 & wallfirstaspect<=azimuth+pi/2);###H�R�RJAG
    #             wallfirstshade=wallfirst-wallfirstsun;
    #         end
    #     end
    return sh, wallsh, wallsun, facesh, facesun
