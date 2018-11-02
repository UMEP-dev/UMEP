# -*- coding: utf-8 -*-
#%calculates morphometric parameters for an image based on prevailing wind
#%direction. Specify a dem on a square grid to load and averaging dimension
#%
#%Date: 26 February 2004
#%Author:
#%   Offerle, B.
#%   Geovetarcentrum
#%   Goteborg University, Sweden
#%   Modified by Fredrik Lindberg 2010-01-09, fredrik.lindberg@kcl.ac.uk
#%   Translated to Python 20150108
#%--------------------------------------------------------------------------
# a = dsm
# b = dem
# scale = 1/pixel resolution (m)
# dtheta = 5.  # degree interval
# import Image
# from scipy import *
import numpy as np
import scipy.ndimage.interpolation as sc
# import scipy.misc as sc
# import matplotlib as plt
# import PIL
from qgis.core import QgsMessageLog
import linecache
import sys


def imagemorphparam_v2(dsm, dem, scale, mid, dtheta, dlg, imp_point):

    try:
        build = dsm - dem
        build[(build < 2.)] = 0.  # building should be higher than 2 meter

        # new part
        buildvec = build[np.where(build > 0)]
        if buildvec.size > 0:
            zH_all = buildvec.mean()
            zHmax_all = buildvec.max()
            zH_sd_all = buildvec.std()
            pai_all = (buildvec.size * 1.0) / (build.size * 1.0)
        else:
            zH_all = 0
            zHmax_all = 0
            zH_sd_all = 0
            pai_all = 0

        fai = np.zeros((int(360./dtheta), 1))
        zH = np.zeros((int(360./dtheta), 1))
        zHmax = np.zeros((int(360./dtheta), 1))
        zH_sd = np.zeros((int(360./dtheta), 1))
        pai = np.zeros((int(360./dtheta), 1))
        deg = np.zeros((int(360./dtheta), 1))

        #%subset and center
        n = dsm.shape[0]
        imid = np.floor((n/2.))
        if mid == 1:
            dY = np.int16(np.arange(np.dot(1, imid)))  # half the length of the grid (y)
        else:
            dY = np.int16(np.arange(np.dot(1, n)))  # the whole length of the grid (y)
        if imp_point == 1:
                dlg.progressBar.setRange(0., 360. / dtheta)
        dX = np.int16(np.arange(imid, imid+1))
        lx = dX.shape[0]
        ly = dY.shape[0]
        filt1 = np.ones((n, 1)) * -1.
        filt2 = np.ones((n, 1))
        filt = np.array(np.hstack((filt1, filt2))).conj().T
        j = int(0)
        for angle in np.arange(0, (360.-dtheta+0) + dtheta, dtheta):
            if imp_point == 1:
                dlg.progressBar.setValue(angle)

            c = np.zeros((n, n))

            # Rotating building
            # d = sc.imrotate(build, angle, 'nearest')
            d = sc.rotate(build, angle, order=0, reshape=False, mode='nearest')
            b = ((build.max()-build.min())/d.max())*d+build.min()
            a = b
            if dem.sum() != 0:  # ground heights
                # d = sc.imrotate(dsm, angle, 'nearest')
                d = sc.rotate(build, angle, order=0, reshape=False, mode='nearest')
                a = ((dsm.max()-dsm.min())/d.max())*d+dsm.min()

            #% convolve leading edge filter with domain
            for i in np.arange(1, (n-1)+1):
                c[int(i)-1, :] = np.sum((filt*a[int(i)-1:i+1, :]), 0)

            wall = c[dY, dX]  # wall array
            wall = wall[np.where(wall > 2)]  # wall vector
            fai[j] = np.sum(wall)/((lx*ly)/scale)
            bld = b[dY, dX]  # building array
            bld = bld[np.where(bld > 2)]  # building vector: change from 0 to 2  : 20150906
            pai[j] = np.float32(bld.shape[0]) / (lx*ly)
            deg[j] = angle
            if np.float32(bld.shape[0]) == 0:
                zH[j] = 0
                zHmax[j] = 0
                zH_sd[j] = 0
            else:
                zH[j] = bld.sum() / np.float32(bld.shape[0])
                zHmax[j] = bld.max()
                zH_sd[j] = bld.std()

            if angle == 0:
                test = wall

            j += 1

        fai_all = np.mean(fai)

        immorphresult = {'fai': fai, 'pai': pai, 'zH': zH, 'deg': deg, 'zHmax': zHmax,'zH_sd': zH_sd, 'pai_all': pai_all,
                         'zH_all': zH_all, 'zHmax_all': zHmax_all, 'zH_sd_all': zH_sd_all, 'fai_all': fai_all,'test': test}

        return immorphresult

    except Exception:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        errorstring = 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(),
                                                                                   exc_obj)
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)


def imagemorphparam_v1(dsm, dem, scale, mid, dtheta, dlg, imp_point):

    build = dsm - dem
    test = build.max()
    build[(build < 2.)] = 0.  # building should be higher than 2 meter
    test = build.max()
    # new part
    buildvec = build[np.where(build > 0)]
    if buildvec.size > 0:
        zH_all = buildvec.mean()
        zHmax_all = buildvec.max()
        zH_sd_all = buildvec.std()
        pai_all = (buildvec.size * 1.0) / (build.size * 1.0)
    else:
        zH_all = 0
        zHmax_all = 0
        zH_sd_all = 0
        pai_all = 0 

    fai = np.zeros((int(360./dtheta), 1))
    zH = np.zeros((int(360./dtheta), 1))
    zHmax = np.zeros((int(360./dtheta), 1))
    zH_sd = np.zeros((int(360./dtheta), 1))
    pai = np.zeros((int(360./dtheta), 1))
    deg = np.zeros((int(360./dtheta), 1))

    #%subset and center
    n = dsm.shape[0]
    imid = np.floor((n/2.))
    if mid == 1:
        dY = np.int16(np.arange(np.dot(1, imid)))  # half the length of the grid (y)
    else:
        dY = np.int16(np.arange(np.dot(1, n)))  # the whole length of the grid (y)
    if imp_point == 1:
            dlg.progressBar.setRange(0., 360. / dtheta)
    dX = np.int16(np.arange(imid, imid+1))
    lx = dX.shape[0]
    ly = dY.shape[0]
    filt1 = np.ones((n, 1)) * -1.
    filt2 = np.ones((n, 1))
    filt = np.array(np.hstack((filt1, filt2))).conj().T
    j = int(0)
    for angle in np.arange(0, (360.-dtheta+0) + dtheta, dtheta):
        if imp_point == 1:
            dlg.progressBar.setValue(angle)

        c = np.zeros((n, n))

        # Rotating building
        # d = sc.imrotate(build, angle, 'nearest')
        d = sc.rotate(build, angle, reshape=False, mode='nearest')
        b = ((build.max()-build.min())/d.max())*d+build.min()
        a = b
        if b.sum() != 0:  # ground heights
            # d = sc.imrotate(dsm, angle, 'nearest')
            d = sc.rotate(dsm, angle, reshape=False, mode='nearest')
            a = ((dsm.max()-dsm.min())/d.max())*d+dsm.min()

        #% convolve leading edge filter with domain
        for i in np.arange(1, (n-1)+1):
            c[int(i)-1, :] = np.sum((filt*a[int(i)-1:i+1, :]), 0)

        wall = c[dY, dX]  # wall array
        wall = wall[np.where(wall > 2)]  # wall vector
        fai[j] = np.sum(wall)/((lx*ly)/scale)
        bld = b[dY, dX]  # building array
        bld = bld[np.where(bld > 0)]  # building vector
        pai[j] = np.float32(bld.shape[0]) / (lx*ly)
        deg[j] = angle
        if np.float32(bld.shape[0]) == 0:
            zH[j] = 0
            zHmax[j] = 0
            zH_sd[j] = 0
        else:
            zH[j] = bld.sum() / np.float32(bld.shape[0])
            zHmax[j] = bld.max()
            zH_sd[j] = bld.std()

        if angle == 0:
            test = wall

        j += 1

    fai_all = np.mean(fai)

    immorphresult = {'fai': fai, 'pai': pai, 'zH': zH, 'deg': deg, 'zHmax': zHmax,'zH_sd': zH_sd, 'pai_all': pai_all,
                     'zH_all': zH_all, 'zHmax_all': zHmax_all, 'zH_sd_all': zH_sd_all, 'fai_all': fai_all,'test': test}

    return immorphresult
