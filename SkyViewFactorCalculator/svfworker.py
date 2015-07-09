from PyQt4 import QtCore, QtGui
import traceback
import numpy as np
from ..Utilities import shadowingfunctions as shadow
import Skyviewfactor4d as svf
#import shadowingfunctions as shadow
#from osgeo import gdal
#from osgeo.gdalconst import *

#import sys

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, a, scale, dlg):
        QtCore.QObject.__init__(self)
        self.killed = False
        self.a = a
        self.scale = scale
        self.dlg = dlg

    def run(self):
        ret = None
        # %This m.file calculates Skyview factors on a DEM for the four cardinal points
        # %This new version is NOT using 1000 randow shadow casting, but implies
        # %the theory of annulus weights (e.g. Steyn, 1980). The number of shadow
        # %castings is reduced to 653.
        # %20130208 - changed to use cell input
        try:
            #  self.dlg.progressBar.setRange(0, 655)
            sizex = self.a.shape[0]
            sizey = self.a.shape[1]
            svf = np.zeros((sizex, sizey))
            svfE = svf
            svfS = svf
            svfW = svf
            svfN = svf
            noa = 19.
            # % No. of angle steps minus 1
            step = 89./noa
            iangle = np.array(np.hstack((np.arange(step/2., 89., step), 90.)))
            annulino = np.array(np.hstack((np.round(np.arange(0., 89., step)), 90.)))
            angleresult = self.svf_angles_100121()
            aziinterval = angleresult["aziinterval"]
            iazimuth = angleresult["iazimuth"]
            aziintervalaniso = np.ceil((aziinterval/2.))
            index = 1.

            for i in np.arange(0, iangle.shape[0]-1):
                if self.killed is True:
                    break
                for j in np.arange(0, (aziinterval[int(i)])):
                    if self.killed is True:
                        break
                    altitude = iangle[int(i)]
                    azimuth = iazimuth[int(index)-1]

                    # self.dlg.progressBar.setValue(index)
                    sh = shadow.shadowingfunctionglobalradiation(self.a, azimuth, altitude, self.scale, self.dlg, 1)
                    for k in np.arange(annulino[int(i)]+1, (annulino[int(i+1.)])+1):

                        weight = self.annulus_weight(k, aziinterval[i])*sh
                        svf = svf + weight
                        if azimuth >= 0 and azimuth < 180:
                            weight = self.annulus_weight(k, aziintervalaniso[i])*sh
                            svfE = svfE + weight
                        if azimuth >= 90 and azimuth < 270:
                            weight = self.annulus_weight(k, aziintervalaniso[i])*sh
                            svfS = svfS + weight
                        if azimuth >= 180 and azimuth < 360:
                            weight = self.annulus_weight(k, aziintervalaniso[i])*sh
                            svfW = svfW + weight
                        if azimuth >= 270 or azimuth < 90:
                            weight = self.annulus_weight(k, aziintervalaniso[i])*sh
                            svfN = svfN + weight
                    index += 1
                    self.progress.emit()

            svfS = svfS + 3.0459e-004
            svfW = svfW + 3.0459e-004
            # % Last azimuth is 90. Hence, manual add of last annuli for svfS and SVFW
            # %Forcing svf not be greater than 1 (some MATLAB crazyness)
            svf[(svf > 1.)] = 1.
            svfE[(svfE > 1.)] = 1.
            svfS[(svfS > 1.)] = 1.
            svfW[(svfW > 1.)] = 1.
            svfN[(svfN > 1.)] = 1.

            svfresult = {'svf': svf, 'svfE': svfE, 'svfS': svfS, 'svfW': svfW, 'svfN': svfN}

            if self.killed is False:
                self.progress.emit()
                ret = svfresult
        except Exception, e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def svf_angles_100121(self):

        azi1 = np.arange(1., 360., 360./16.)  # %22.5
        azi2 = np.arange(12., 360., 360./16.)  # %22.5
        azi3 = np.arange(5., 360., 360./32.)  # %11.25
        azi4 = np.arange(2., 360., 360./32.)  # %11.25
        azi5 = np.arange(4., 360., 360./40.)  # %9
        azi6 = np.arange(7., 360., 360./48.)  # %7.50
        azi7 = np.arange(6., 360., 360./48.)  # %7.50
        azi8 = np.arange(1., 360., 360./48.)  # %7.50
        azi9 = np.arange(4., 359., 360./52.)  # %6.9231
        azi10 = np.arange(5., 360., 360./52.)  # %6.9231
        azi11 = np.arange(1., 360., 360./48.)  # %7.50
        azi12 = np.arange(0., 359., 360./44.)  # %8.1818
        azi13 = np.arange(3., 360., 360./44.)  # %8.1818
        azi14 = np.arange(2., 360., 360./40.)  # %9
        azi15 = np.arange(7., 360., 360./32.)  # %10
        azi16 = np.arange(3., 360., 360./24.)  # %11.25
        azi17 = np.arange(10., 360., 360./16.)  # %15
        azi18 = np.arange(19., 360., 360./12.)  # %22.5
        azi19 = np.arange(17., 360., 360./8.)  # %45
        azi20 = 0.  # %360
        iazimuth = np.array(np.hstack((azi1, azi2, azi3, azi4, azi5, azi6, azi7, azi8, azi9, azi10, azi11, azi12, azi13,
                                       azi14, azi15, azi16, azi17, azi18, azi19, azi20)))
        aziinterval = np.array(np.hstack((16., 16., 32., 32., 40., 48., 48., 48., 52., 52., 48., 44., 44., 40., 32., 24.,
                                          16., 12., 8., 1.)))
        angleresult = {'iazimuth': iazimuth, 'aziinterval': aziinterval}

        return angleresult

    def annulus_weight(self, altitude, aziinterval):

        n = 90.
        steprad = (360./aziinterval) * (np.pi/180.)
        annulus = 91.-altitude
        w = (1./(2.*np.pi)) * np.sin(np.pi / (2.*n)) * np.sin((np.pi * (2. * annulus - 1.)) / (2. * n))
        weight = steprad * w

        return weight
