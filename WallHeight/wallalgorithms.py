# -*- coding: utf-8 -*-
__author__ = 'xlinfr'

import numpy as np
import scipy.misc as sc
import math


def findwalls(a, walllimit):
    # This function identifies walls based on a DSM and a wall-height limit
    # Walls are represented by outer pixels within building footprints
    #
    #Fredrik Lindberg, Goteborg Urban Climate Group
    # fredrikl@gvc.gu.se
    #20150625

    col = a.shape[0]
    row = a.shape[1]
    walls = np.zeros((col, row))
    domain = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
    for i in np.arange(1, row-1):
        for j in np.arange(1, col-1):
            dom = a[j-1:j+2, i-1:i+2]
            walls[j, i] = np.min(dom[np.where(domain == 1)])

    walls = a-walls
    walls[(walls < walllimit)] = 0
    # wallsbol = np.copy(walls)
    # wallsbol[(wallsbol > 0)] = 1

    # wallsbol[0:wallsbol .shape[0], 0] = 0
    # wallsbol[0:wallsbol .shape[0], wallsbol .shape[1] - 1] = 0
    # wallsbol[0, 0:wallsbol .shape[0]] = 0
    # wallsbol[wallsbol .shape[0] - 1, 0:wallsbol .shape[1]] = 0

    walls[0:walls .shape[0], 0] = 0
    walls[0:walls .shape[0], walls .shape[1] - 1] = 0
    walls[0, 0:walls .shape[0]] = 0
    walls[walls .shape[0] - 1, 0:walls .shape[1]] = 0

    return walls  #, wallsbol


def filter1Goodwin_as_aspect_v3(walls, scale, a):
    """
    tThis function applies the filter processing presented in Goodwin et al (2010) but instead for removing
    linear fetures it calculates wall aspect based on a wall pixels grid, a dsm (a) and a scale factor

    Fredrik Lindberg, 2012-02-14
    fredrikl@gvc.gu.se

    Translated: 2015-09-15

    :param walls:
    :param scale:
    :param a:
    :return: dirwalls
    """

    # function dirwalls = filter1Goodwin_as_aspect_v3(walls,sizex,sizey,scale,a)
    # %
    # %
    # %

    # if isempty(walls)==1
    #     walls=ordfilt2(a,4,[0 1 0; 1 0 1; 0 1 0]);
    #     walls=walls-a;
    #     walls(walls<3)=0;
    # end
    #plt.show()

    row = a.shape[0]
    col = a.shape[1]

    filtersize = np.floor((scale + 0.0000000001) * 9)
    if filtersize <= 2:
        filtersize = 3
    else:
        if filtersize != 9:
            if filtersize % 2 == 0:
                filtersize = filtersize + 1

    filthalveceil = int(np.ceil(filtersize / 2.))
    filthalvefloor = int(np.floor(filtersize / 2.))

    filtmatrix = np.zeros((int(filtersize), int(filtersize)))
    buildfilt = np.zeros((int(filtersize), int(filtersize)))

    filtmatrix[:, filthalveceil - 1] = 1
    buildfilt[filthalveceil - 1, 0:filthalvefloor] = 1
    buildfilt[filthalveceil - 1, filthalveceil: int(filtersize)] = 2

    y = np.zeros((row, col))  # final direction
    z = np.zeros((row, col))  # temporary direction
    x = np.zeros((row, col))  # building side
    walls[walls > 0] = 1

    for h in range(0, 180):  # =0:1:180 #%increased resolution to 1 deg 20140911
        # print h
        filtmatrix1temp = sc.imrotate(filtmatrix, h, 'bilinear')
        filtmatrix1 = np.round(filtmatrix1temp / 255.)
        filtmatrixbuildtemp = sc.imrotate(buildfilt, h, 'nearest')
        filtmatrixbuild = np.round(filtmatrixbuildtemp / 127.)
        index = 270 - h
        if h == 150:
            filtmatrixbuild[:, filtmatrix.shape[0] - 1] = 0
        if h == 30:
            filtmatrixbuild[:, filtmatrix.shape[0] - 1] = 0
        if index == 225:
            n = filtmatrix.shape[0] - 1  # length(filtmatrix);
            filtmatrix1[0, 0] = 1
            filtmatrix1[n, n] = 1
        if index == 135:
            n = filtmatrix.shape[0] - 1  # length(filtmatrix);
            filtmatrix1[0, n] = 1
            filtmatrix1[n, 0] = 1

        for i in range(int(filthalveceil) - 1, row - int(filthalveceil) - 1):  # i=filthalveceil:sizey-filthalveceil
            for j in range(int(filthalveceil) - 1,
                           col - int(filthalveceil) - 1):  # (j=filthalveceil:sizex-filthalveceil
                if walls[i, j] == 1:
                    wallscut = walls[i - filthalvefloor:i + filthalvefloor + 1,
                               j - filthalvefloor:j + filthalvefloor + 1] * filtmatrix1
                    dsmcut = a[i - filthalvefloor:i + filthalvefloor + 1, j - filthalvefloor:j + filthalvefloor + 1]
                    if z[i, j] < wallscut.sum():  # sum(sum(wallscut))
                        z[i, j] = wallscut.sum()  # sum(sum(wallscut));
                        if np.sum(dsmcut[filtmatrixbuild == 1]) > np.sum(dsmcut[filtmatrixbuild == 2]):
                            x[i, j] = 1
                        else:
                            x[i, j] = 2

                        y[i, j] = index

    y[(x == 1)] = y[(x == 1)] - 180
    y[(y < 0)] = y[(y < 0)] + 360

    grad, asp = get_ders(a, scale)

    y = y + ((walls == 1) * 1) * ((y == 0) * 1) * (asp / (math.pi / 180.))

    dirwalls = y


    
    #
    #
    #
    # row = a.shape[0]
    # col = a.shape[1]
    #
    # filtersize = np.floor((scale + 0.0000000001) * 9)  # numpy crazyness rounding
    # if filtersize != 9:
    #     if np.mod(filtersize, scale) == 0:
    #         filtersize = filtersize - 1
    #
    # filthalveceil = np.ceil(filtersize / 2)
    # filthalvefloor = np.floor(filtersize / 2)
    #
    # filtmatrix = np.zeros((filtersize, filtersize))
    # buildfilt = np.zeros((filtersize, filtersize))
    #
    # filtmatrix[:, filthalveceil - 1] = 1
    # buildfilt[filthalveceil - 1, 0:filthalvefloor] = 1
    # buildfilt[filthalveceil - 1, filthalveceil: filtersize] = 2
    #
    # y = np.zeros((row, col)) #%final direction
    # z = np.zeros((row, col))#%temporary direction
    # x = np.zeros((row, col)) #%building side
    # walls[walls > 0] = 1
    #
    # for h in range(0, 180):  #=0:1:180 #%increased resolution to 1 deg 20140911
    #     # print h
    #     filtmatrix1temp = sc.imrotate(filtmatrix, h, 'bilinear')
    #     filtmatrix1 = np.round(filtmatrix1temp / 255.)
    #     filtmatrixbuildtemp = sc.imrotate(buildfilt, h, 'nearest')
    #     filtmatrixbuild = np.round(filtmatrixbuildtemp / 127.)
    #     index = 270-h
    #     if h == 150:
    #         filtmatrixbuild[:, 8] = 0
    #     if h == 30:
    #         filtmatrixbuild[:, 8] = 0
    #     if index == 225:
    #         n = filtmatrix.shape[0] - 1  #length(filtmatrix);
    #         filtmatrix1[0, 0] = 1
    #         filtmatrix1[n, n] = 1
    #     if index == 135:
    #         n = filtmatrix.shape[0] - 1  #length(filtmatrix);
    #         filtmatrix1[0, n] = 1
    #         filtmatrix1[n, 0] = 1
    #
    #     for i in range(int(filthalveceil)-1, row - int(filthalveceil) - 1):  #i=filthalveceil:sizey-filthalveceil
    #         for j in range(int(filthalveceil)-1, col - int(filthalveceil) - 1):  #(j=filthalveceil:sizex-filthalveceil
    #             if walls[i, j] == 1:
    #                 wallscut = walls[i-filthalvefloor:i+filthalvefloor+1, j-filthalvefloor:j+filthalvefloor+1] * filtmatrix1
    #                 dsmcut = a[i-filthalvefloor:i+filthalvefloor+1, j-filthalvefloor:j+filthalvefloor+1]
    #                 if z[i, j] < wallscut.sum():  #sum(sum(wallscut))
    #                     z[i, j] = wallscut.sum()  #sum(sum(wallscut));
    #                     if np.sum(dsmcut[filtmatrixbuild == 1]) > np.sum(dsmcut[filtmatrixbuild == 2]):
    #                         x[i, j] = 1
    #                     else:
    #                         x[i, j] = 2
    #
    #                     y[i, j] = index
    #
    # y[(x == 1)] = y[(x == 1)] - 180
    # y[(y < 0)] = y[(y < 0)] + 360
    #
    # grad, asp = get_ders(a, scale)
    #
    # # fx, fy = np.gradient(a)
    # # asp, _ = cart2pol(fy, fx)
    # # # grad = math.atan(grad)
    # # asp = asp * -1.
    # # temp = asp > 0
    # # temp = temp * (math.pi * 2)
    # # asp = asp + temp
    # #[~,aspect] = get_ders(a,1/scale); #% filling edges of model domain
    # y = y + ((walls == 1) * 1) * ((y == 0) * 1) * (asp / (math.pi / 180.))
    # # y = y + ((walls == 1 & y == 0) * (asp / (math.pi / 180.)))
    #
    # dirwalls = y

    return dirwalls


def cart2pol(x, y, units='deg'):
    radius = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    if units in ['deg', 'degs']:
        theta = theta * 180 / np.pi
    return theta, radius


def get_ders(dsm, scale):
    # dem,_,_=read_dem_grid(dem_file)
    dx = 1/scale
    # dx=0.5
    fy, fx = np.gradient(dsm, dx, dx)
    asp, grad = cart2pol(fy, fx, 'rad')
    grad = np.arctan(grad)
    asp = asp * -1
    asp = asp + (asp < 0) * (np.pi * 2)
    return grad, asp