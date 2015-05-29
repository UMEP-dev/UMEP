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
import Image
from scipy import *
import numpy as np
import scipy.ndimage.interpolation as sc
import PIL


def imagemorphparam_v1(dsm, dem, scale, mid, dtheta, dlg):

    build = dsm - dem
    build[(build < 2.)] = 0.  # building should be higher than 2 meter

    # new part
    buildvec = build[np.where(build > 0)]
    zH_all = buildvec.mean()
    zHmax_all = buildvec.max()
    zH_sd_all = buildvec.std()
    pai_all = (buildvec.size * 1.0) / (build.size * 1.0)

    fai = np.zeros((72, 1))
    zH = np.zeros((72, 1))
    zHmax = np.zeros((72, 1))
    zH_sd = np.zeros((72, 1))
    pai = np.zeros((72, 1))
    deg = np.zeros((72, 1))

    #%subset and center
    n = dsm.shape[0]
    imid = np.floor((n/2.))
    if mid == 1:
        dY = np.int16(np.arange(np.dot(1, imid)))  # the whole length of the grid (y)
        dlg.progressBar.setRange(0., 360. / dtheta)
    else:
        dY = np.int16(np.arange(np.dot(1, n)))  # the whole length of the grid (y)

    dX = np.int16(np.arange(imid, imid+1))
    lx = dX.shape[0]
    ly = dY.shape[0]
    filt1 = np.ones((n, 1.)) * -1.
    filt2 = np.ones((n, 1.))
    filt = np.array(np.hstack((filt1, filt2))).conj().T
    j = int(0)
    for angle in np.arange(0, (360.-dtheta+0) + dtheta, dtheta):
        if mid == 1:
            dlg.progressBar.setValue(angle)

        c = np.zeros((n, n))
        #d = sc.imrotate(build, angle, 'nearest')
        d = sc.rotate(build, angle, reshape=False, mode='nearest')
        b = ((build.max()-build.min())/d.max())*d+build.min()
        a = b
        if b.sum() != 0:  # ground heights
            #d = sc.imrotate(dsm, angle, 'nearest')
            d = sc.rotate(build, angle, reshape=False, mode='nearest')
            a = ((dsm.max()-dsm.min())/d.max())*d+dsm.min()

        #% convolve leading edge filter with domain
        for i in np.arange(1., (n-1.)+1):
            c[int(i)-1, :] = np.sum((filt*a[int(i)-1:i+1., :]), 0)

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

        j += 1

    immorphresult = {'fai': fai, 'pai': pai, 'zH': zH, 'deg': deg, 'zHmax': zHmax,'zH_sd': zH_sd, 'pai_all': pai_all,
                     'zH_all': zH_all, 'zHmax_all': zHmax_all, 'zH_sd_all': zH_sd_all}

    return immorphresult
