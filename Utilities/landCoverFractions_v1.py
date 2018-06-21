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
# import scipy.ndimage.interpolation as sc
from scipy import misc as sc
import numpy as np
# import scipy.ndimage.interpolation as sc
# import PIL
# import matplotlib.pylab as plt


def landcover_v1(lc_grid, mid, dtheta, dlg, imp_point):

    # Isotropic
    lc_frac_all = np.zeros((1, 7))
    for i in range(0, 7):
        lc_gridvec = lc_grid[np.where(lc_grid == i + 1)]
        if lc_gridvec.size > 0:
            lc_frac_all[0, i] = (lc_gridvec.size * 1.0) / (lc_grid.size * 1.0)

    # Anisotropic
    lc_frac = np.zeros((int(360./dtheta), 7))
    deg = np.zeros((int(360./dtheta), 1))

    n = lc_grid.shape[0]
    imid = np.floor((n/2.))
    if mid == 1:
        dY = np.int16(np.arange(np.dot(1, imid)))  # the half length of the grid (y)
    else:
        dY = np.int16(np.arange(np.dot(1, n)))  # the whole length of the grid (y)

    if imp_point == 1:
            dlg.progressBar.setRange(0., 360. / dtheta)

    dX = np.int16(np.arange(imid, imid+1))
    lx = dX.shape[0]
    ly = dY.shape[0]

    j = int(0)
    for angle in np.arange(0, (360.-dtheta+0) + dtheta, dtheta):
        if imp_point == 1:
            dlg.progressBar.setValue(angle)

        # d = sc.rotate(lc_grid, angle, reshape=False, mode='nearest')
        # b = ((build.max()-build.min())/d.max())*d+build.min()
        d = sc.imrotate(lc_grid, angle, 'nearest')

        # d = sc.rotate(lc_grid, angle, reshape=False, mode='nearest')
        b = np.round(((lc_grid.max()-lc_grid.min())/d.max())*d+lc_grid.min(), 0)

        # plt.matshow(b)
        # plt.colorbar()
        # plt.show()

        bld = b[dY, dX]  # lc array

        for i in range(0, 7):
            bldtemp = bld[np.where(bld == i + 1)]  # lc vector
            lc_frac[j, i] = np.float32(bldtemp.shape[0]) / (lx*ly)

        deg[j] = angle
        j += 1

    landcoverresult = {'lc_frac_all': lc_frac_all, 'lc_frac': lc_frac, 'deg': deg}

    return landcoverresult

