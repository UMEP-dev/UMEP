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

import numpy as np
#import scipy.misc as sc
import scipy.ndimage.interpolation as sc


def imagemorphparam_v1(dsm, dem, scale, mid, dtheta):

    build = dsm - dem
    build[(build < 2.)] = 0.  # building should be higher than 2 meter
    fai = np.zeros((72, 1))
    zH = np.zeros((72, 1))
    pai = np.zeros((72, 1))
    deg = np.zeros((72, 1))

    #%subset and center
    n = dsm.shape[0]
    imid = np.floor((n/2.))
    if mid == 1:
        dY = np.int16(np.arange(np.dot(1, imid)))  # the whole length of the grid (y)
    else:
        dY = np.int16(np.arange(np.dot(1, n)))  # the whole length of the grid (y)

    dX = np.int16(np.arange(imid, imid+1))
    lx = dX.shape[0]
    ly = dY.shape[0]
    filt1 = np.ones((n, 1.)) * -1.
    filt2 = np.ones((n, 1.))
    filt = np.array(np.hstack((filt1, filt2))).conj().T
    j = int(0)
    #progess 72 index
    for angle in np.arange(0, (360.-dtheta+0) + dtheta, dtheta):
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
        else:
            zH[j] = bld.sum() / np.float32(bld.shape[0])

        j += 1

    immorphresult = {'fai': fai, 'pai': pai, 'zH': zH, 'deg': deg}

    return immorphresult
