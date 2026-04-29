
from qgis.PyQt import QtCore
import numpy as np
from ..Utilities import shadowingfunctions as shadow

import sys
import linecache

class VegWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, a, scale, vegdem, vegdem2, dlg):
        QtCore.QObject.__init__(self)
        self.killed = False
        self.a = a
        self.scale = scale
        self.vegdem = vegdem
        self.vegdem2 = vegdem2
        self.dlg = dlg

    def run(self):
        """
        #%This m.file calculates Skyview factors on a VegetationDEM for the four cardinal points.
        #%It also calculates separate SVFs for vegetation units shadowed by buildings
        #%Created by Fredrik Lindberg 20080-30
        # 20181004 - New version using 145 shadow castings
        """
        ret = None
        #%% Set up
        try:
            #self.dlg.progressBar.setRange(0, 655)
            sizex = self.a.shape[0]
            sizey = self.a.shape[1]
            svfveg = np.zeros((sizex, sizey))
            svfEveg = np.zeros((sizex, sizey))
            svfSveg = np.zeros((sizex, sizey))
            svfWveg = np.zeros((sizex, sizey))
            svfNveg = np.zeros((sizex, sizey))
            svfaveg = np.zeros((sizex, sizey))
            svfEaveg = np.zeros((sizex, sizey))
            svfSaveg = np.zeros((sizex, sizey))
            svfWaveg = np.zeros((sizex, sizey))
            svfNaveg = np.zeros((sizex, sizey))

            #% amaxvalue
            vegmax = self.vegdem.max()
            amaxvalue = self.a.max()
            amaxvalue = np.maximum(amaxvalue, vegmax)

            #% Elevation vegdems if buildingDEM inclused ground heights
            self.vegdem = self.vegdem+self.a
            self.vegdem[self.vegdem == self.a] = 0
            self.vegdem2 = self.vegdem2+self.a
            self.vegdem2[self.vegdem2 == self.a] = 0
            #% Bush separation
            bush = np.logical_not((self.vegdem2*self.vegdem))*self.vegdem

            noa = 19.
            #% No. of anglesteps minus 1
            step = 89./noa
            iangle = np.array(np.hstack((np.arange(step/2., 89., step), 90.)))
            annulino = np.array(np.hstack((np.round(np.arange(0., 89., step)), 90.)))
            angleresult = self.svf_angles_100121()
            aziinterval = angleresult["aziinterval"]
            iazimuth = angleresult["iazimuth"]
            aziintervalaniso = np.ceil((aziinterval/2.))
            index = 1.
            #%% Main core
            for i in np.arange(0, iangle.shape[0]-1):
                if self.killed is True:
                    break
                for j in np.arange(0, (aziinterval[int(i)])):
                    if self.killed is True:
                        break
                    # print index
                    altitude = iangle[int(i)]
                    azimuth = iazimuth[int(index)-1]
                    shadowresult = shadow.shadowingfunction_20(self.a, self.vegdem, self.vegdem2, azimuth, altitude,
                                                               self.scale, amaxvalue, bush, self.dlg, 1)
                    vegsh = shadowresult["vegsh"]
                    vbshvegsh = shadowresult["vbshvegsh"]
                    for k in np.arange(annulino[int(i)]+1, (annulino[int(i+1.)])+1):
                        #% changed to include 90
                        weight = self.annulus_weight(k, aziinterval[i])
                        svfveg = svfveg + weight * vegsh
                        svfaveg = svfaveg + weight * vbshvegsh
                        weight = self.annulus_weight(k, aziintervalaniso[i])
                        if (azimuth >= 0) and (azimuth < 180):
                            svfEveg = svfEveg + weight * vegsh
                            svfEaveg = svfEaveg + weight * vbshvegsh
                        if (azimuth >= 90) and (azimuth < 270):
                            svfSveg = svfSveg + weight * vegsh
                            svfSaveg = svfSaveg + weight * vbshvegsh
                        if (azimuth >= 180) and (azimuth < 360):
                            svfWveg = svfWveg + weight * vegsh
                            svfWaveg = svfWaveg + weight * vbshvegsh
                        if (azimuth >= 270) or (azimuth < 90):
                            svfNveg = svfNveg + weight * vegsh
                            svfNaveg = svfNaveg + weight * vbshvegsh
                    index += 1
                    self.progress.emit()

            #% Last azimuth is 90. Hence, manual add of last annuli for svfS and SVFW
            last = np.zeros((sizex, sizey))
            last[(self.vegdem2 == 0.)] = 3.0459e-004
            svfSveg = svfSveg+last
            svfWveg = svfWveg+last
            svfSaveg = svfSaveg+last
            svfWaveg = svfWaveg+last
            #%Forcing svf not be greater than 1 (some MATLAB crazyness)
            svfveg[(svfveg > 1.)] = 1.
            svfEveg[(svfEveg > 1.)] = 1.
            svfSveg[(svfSveg > 1.)] = 1.
            svfWveg[(svfWveg > 1.)] = 1.
            svfNveg[(svfNveg > 1.)] = 1.
            svfaveg[(svfaveg > 1.)] = 1.
            svfEaveg[(svfEaveg > 1.)] = 1.
            svfSaveg[(svfSaveg > 1.)] = 1.
            svfWaveg[(svfWaveg > 1.)] = 1.
            svfNaveg[(svfNaveg > 1.)] = 1.

            svfvegresult = {'svfveg': svfveg, 'svfEveg': svfEveg, 'svfSveg': svfSveg, 'svfWveg': svfWveg, 'svfNveg': svfNveg,
                            'svfaveg': svfaveg, 'svfEaveg': svfEaveg, 'svfSaveg': svfSaveg, 'svfWaveg': svfWaveg, 'svfNaveg': svfNaveg}

            #return svfvegresult

            if self.killed is False:
                self.progress.emit()
                ret = svfvegresult
        except Exception:
            # forward the exception upstream
            errorstring = self.print_exception()
            self.error.emit(errorstring)
        self.finished.emit(ret)

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)



    # def run(self):
    #     ret = None
    #     #%This m.file calculates Skyview factors on a DEM for the four cardinal points
    #     #%This new version is NOT using 1000 randow shadow casting, but implies
    #     #%the theory of annulus weights (e.g. Steyn, 1980). The number of shadow
    #     #%castings is reduced to 653.
    #     #%20130208 - changed to use cell input
    #     try:
    #         self.dlg.progressBar.setRange(0, 655)
    #         sizex = self.a.shape[0]
    #         sizey = self.a.shape[1]
    #         svf = np.zeros((sizex, sizey))
    #         svfE = svf
    #         svfS = svf
    #         svfW = svf
    #         svfN = svf
    #         noa = 19.
    #         #% No. of angle steps minus 1
    #         step = 89./noa
    #         iangle = np.array(np.hstack((np.arange(step/2., 89., step), 90.)))
    #         annulino = np.array(np.hstack((np.round(np.arange(0., 89., step)), 90.)))
    #         angleresult = self.svf_angles_100121()
    #         aziinterval = angleresult["aziinterval"]
    #         iazimuth = angleresult["iazimuth"]
    #         aziintervalaniso = np.ceil((aziinterval/2.))
    #         index = 1.
    #
    #         for i in np.arange(0, iangle.shape[0]-1):
    #             if self.killed is True:
    #                 break
    #             for j in np.arange(0, (aziinterval[int(i)])):
    #                 if self.killed is True:
    #                     break
    #                 altitude = iangle[int(i)]
    #                 azimuth = iazimuth[int(index)-1]
    #
    #                 self.dlg.progressBar.setValue(index)
    #                 sh = shadow.shadowingfunctionglobalradiation(self.a, azimuth, altitude, self.scale, self.dlg, 1)
    #                 for k in np.arange(annulino[int(i)]+1, (annulino[int(i+1.)])+1):
    #                     #% changed to include 90
    #
    #                     weight = self.annulus_weight(k, aziinterval[i])*sh
    #                     svf = svf + weight
    #                     if azimuth >= 0 and azimuth < 180:
    #                         weight = self.annulus_weight(k, aziintervalaniso[i])*sh
    #                         svfE = svfE + weight
    #                     if azimuth >= 90 and azimuth < 270:
    #                         weight = self.annulus_weight(k, aziintervalaniso[i])*sh
    #                         svfS = svfS + weight
    #                     if azimuth >= 180 and azimuth < 360:
    #                         weight = self.annulus_weight(k, aziintervalaniso[i])*sh
    #                         svfW = svfW + weight
    #                     if azimuth >= 270 or azimuth < 90:
    #                         weight = self.annulus_weight(k, aziintervalaniso[i])*sh
    #                         svfN = svfN + weight
    #                 index += 1
    #
    #         svfS = svfS+3.0459e-004
    #         svfW = svfW+3.0459e-004
    #         #% Last azimuth is 90. Hence, manual add of last annuli for svfS and SVFW
    #         #%Forcing svf not be greater than 1 (some MATLAB crazyness)
    #         svf[(svf > 1.)] = 1.
    #         svfE[(svfE > 1.)] = 1.
    #         svfS[(svfS > 1.)] = 1.
    #         svfW[(svfW > 1.)] = 1.
    #         svfN[(svfN > 1.)] = 1.
    #
    #         svfresult = {'svf': svf, 'svfE': svfE, 'svfS': svfS, 'svfW': svfW, 'svfN': svfN}
    #
    #         #return svfresult
    #
    #
    #         if self.killed is False:
    #             #self.progress.emit(100)
    #             ret = svfresult
    #     except Exception, e:
    #         # forward the exception upstream
    #         self.error.emit(e, traceback.format_exc())
    #     self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def svf_angles_100121(self):

        azi1 = np.arange(1., 360., 360./16.)  #%22.5
        azi2 = np.arange(12., 360., 360./16.)  #%22.5
        azi3 = np.arange(5., 360., 360./32.)  #%11.25
        azi4 = np.arange(2., 360., 360./32.)  #%11.25
        azi5 = np.arange(4., 360., 360./40.)  #%9
        azi6 = np.arange(7., 360., 360./48.)  #%7.50
        azi7 = np.arange(6., 360., 360./48.)  #%7.50
        azi8 = np.arange(1., 360., 360./48.)  #%7.50
        azi9 = np.arange(4., 359., 360./52.)  #%6.9231
        azi10 = np.arange(5., 360., 360./52.)  #%6.9231
        azi11 = np.arange(1., 360., 360./48.)  #%7.50
        azi12 = np.arange(0., 359., 360./44.)  #%8.1818
        azi13 = np.arange(3., 360., 360./44.)  #%8.1818
        azi14 = np.arange(2., 360., 360./40.)  #%9
        azi15 = np.arange(7., 360., 360./32.)  #%10
        azi16 = np.arange(3., 360., 360./24.)  #%11.25
        azi17 = np.arange(10., 360., 360./16.)  #%15
        azi18 = np.arange(19., 360., 360./12.)  #%22.5
        azi19 = np.arange(17., 360., 360./8.)  #%45
        azi20 = 0.  #%360
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
        #% 91 before
        w = (1./(2.*np.pi)) * np.sin(np.pi / (2.*n)) * np.sin((np.pi * (2. * annulus - 1.)) / (2. * n))
        weight = steprad * w

        return weight
