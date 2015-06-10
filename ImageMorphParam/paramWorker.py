from PyQt4 import QtCore, QtGui
import traceback
import numpy as np
from ..Utilities import shadowingfunctions as shadow
import Image
from scipy import *
import numpy as np
import scipy.ndimage.interpolation as sc
import PIL

import sys

#ARBETARMETOD FOR TRADKLASS SOM INTE ANNU AR IMPLEMENTERAD. FUNGERAR INTE FORRAN PROBLEM MED MANGA TRADAR HAR LOSTS

class ParamWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object, object, object)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, dsm, dem, scale, mid, dtheta, f, idx, dlg):
        QtCore.QObject.__init__(self)
        self.killed = False
        self.dsm = dsm
        self.dem = dem
        self.scale = scale
        self.mid = mid
        self.dtheta = dtheta
        self.f = f
        self.idx = idx
        self.dlg = dlg

    def run(self):
        ret = None

        try:
            build = self.dsm - self.dem
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

            fai = np.zeros((72, 1))
            zH = np.zeros((72, 1))
            zHmax = np.zeros((72, 1))
            zH_sd = np.zeros((72, 1))
            pai = np.zeros((72, 1))
            deg = np.zeros((72, 1))

            #%subset and center
            n = self.dsm.shape[0]
            imid = np.floor((n/2.))
            if self.mid == 1:
                dY = np.int16(np.arange(np.dot(1, imid)))  # the whole length of the grid (y)
                #self.dlg.progressBar.setRange(0., 360. / self.dtheta)
            else:
                dY = np.int16(np.arange(np.dot(1, n)))  # the whole length of the grid (y)

            dX = np.int16(np.arange(imid, imid+1))
            lx = dX.shape[0]
            ly = dY.shape[0]
            filt1 = np.ones((n, 1)) * -1
            filt2 = np.ones((n, 1))
            filt = np.array(np.hstack((filt1, filt2))).conj().T
            j = int(0)
            for angle in np.arange(0, (360.-self.dtheta+0) + self.dtheta, self.dtheta):
                if self.killed is True:
                    break

                if self.mid == 1:
                    #self.dlg.progressBar.setValue(angle)
                    self.progress.emit()

                c = np.zeros((n, n))
                #d = sc.imrotate(build, angle, 'nearest')
                d = sc.rotate(build, angle, reshape=False, mode='nearest')
                b = ((build.max()-build.min())/d.max())*d+build.min()
                a = b
                if b.sum() != 0:  # ground heights
                    #d = sc.imrotate(dsm, angle, 'nearest')
                    d = sc.rotate(build, angle, reshape=False, mode='nearest')
                    a = ((self.dsm.max()-self.dsm.min())/d.max())*d+self.dsm.min()

                #% convolve leading edge filter with domain
                for i in np.arange(1, (n-1)+1):
                    if self.killed is True:
                        break
                    c[int(i)-1, :] = np.sum((filt*a[int(i)-1:i+1, :]), 0)

                wall = c[dY, dX]  # wall array
                wall = wall[np.where(wall > 2)]  # wall vector
                fai[j] = np.sum(wall)/((lx*ly)/self.scale)
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

            if self.killed is False:
                #self.progress.emit()
                ret = immorphresult

        except Exception, e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())
        self.finished.emit(ret, self.f, self.idx)

    def kill(self):
        self.killed = True
