from PyQt4 import QtCore
# from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
import traceback
from ..Utilities.imageMorphometricParms_v1 import *
# import Image
from scipy import *
import numpy as np
# from ..Utilities.qgiscombomanager import *
from osgeo import gdal
import subprocess
# import os
# import PIL
# from paramWorker import ParamWorker
# from pydev import pydevd
# import sys

class Worker(QtCore.QObject):

    # Implementation av de signaler som traden skickar
    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, dsm, dem, dsm_build, poly, poly_field, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                 folderPath, dlg, imid, radius):
        QtCore.QObject.__init__(self)
        # Boolean som berattar for traden ifall den har avbrutits
        self.killed = False
        # skapar referenser till all data som skickas in till traden, maste goras for att variablerna ska kunna nas
        # i run()-metoden och alla andra metoder klassen kan tankas ha.
        self.dsm = dsm
        self.dem = dem
        self.dsm_build = dsm_build
        self.poly = poly
        self.poly_field = poly_field
        self.vlayer = vlayer
        self.prov = prov
        self.fields = fields
        self.idx = idx
        self.dir_poly = dir_poly
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.folderPath = folderPath
        self.dlg = dlg
        self.imid = imid
        self.radius = radius

        # Forsok till att skapa ytterligare tradar, anvands inte for tillfallet.
        self.paramthread = None
        self.paramworker = None

    def run(self):
        # ska nagot returneras fran traden sker detta genom denna ret-variabel och retuneras till image_morph_param.py
        # genom finished signalen ovan. bool skickas for tillfallet, kan bytas ut mot tex Object for att skicka diverse
        # data. Behovs inte for just detta verktyg.
        ret = 0
        imp_point = 0

        # Allt arbete en trad ska utforas maste goras i en try-sats
        try:
            # j = 0
            # Loop som utfor det arbete som annars hade "hangt" anvandargranssnittet i Qgis
            for f in self.vlayer.getFeatures():  # looping through each grid polygon
                # Kollar sa att traden inte har avbrutits, ifall den har det sa slutar loopning.
                if self.killed is True:
                    break
                # pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True) #used for debugging

                attributes = f.attributes()
                geometry = f.geometry()
                feature = QgsFeature()
                feature.setAttributes(attributes)
                feature.setGeometry(geometry)

                if self.imid == 1:  # use center point
                    r = self.radius
                    y = f.geometry().centroid().asPoint().y()
                    x = f.geometry().centroid().asPoint().x()
                    # self.iface.messageBar().pushMessage("Test", str(loc))
                else:
                    r = 0  # Uses as info to separate from IMP point to grid
                    writer = QgsVectorFileWriter(self.dir_poly, "CP1250", self.fields, self.prov.geometryType(),
                                                 self.prov.crs(), "ESRI shapefile")

                    if writer.hasError() != QgsVectorFileWriter.NoError:
                        self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))
                    writer.addFeature(feature)
                    del writer

                if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
                    provider = self.dsm_build.dataProvider()
                    filePath_dsm_build = str(provider.dataSourceUri())

                    if self.imid == 1:
                        gdalruntextdsm_build = 'gdalwarp -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                               ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff ' + \
                                               filePath_dsm_build + ' ' + self.plugin_dir + '/data/clipdsm.tif'
                    else:
                        gdalruntextdsm_build = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + \
                                               ' -crop_to_cutline -of GTiff ' + filePath_dsm_build + ' ' + \
                                               self.plugin_dir + '/data/clipdsm.tif'

                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.call(gdalruntextdsm_build, startupinfo=si)

                    # os.system(gdalruntextdsm_build)
                    dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
                    dsm_array = dataset.ReadAsArray().astype(np.float)
                    sizex = dsm_array.shape[0]
                    sizey = dsm_array.shape[1]
                    dem_array = np.zeros((sizex, sizey))

                else:  # Both building ground heights
                    provider = self.dsm.dataProvider()
                    filePath_dsm = str(provider.dataSourceUri())
                    provider = self.dem.dataProvider()
                    filePath_dem = str(provider.dataSourceUri())

                    # # get raster source - gdalwarp
                    if self.imid == 1:
                        gdalruntextdsm = 'gdalwarp -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                               ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff ' + \
                                               filePath_dsm + ' ' + self.plugin_dir + '/data/clipdsm.tif'
                        gdalruntextdem = 'gdalwarp -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                               ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff ' + \
                                               filePath_dem + ' ' + self.plugin_dir + '/data/clipdem.tif'
                    else:
                        gdalruntextdsm = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + \
                                         ' -crop_to_cutline -of GTiff ' + filePath_dsm + \
                                         ' ' + self.plugin_dir + '/data/clipdsm.tif'
                        gdalruntextdem = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + \
                                         ' -crop_to_cutline -of GTiff ' + filePath_dem + \
                                         ' ' + self.plugin_dir + '/data/clipdem.tif'

                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.call(gdalruntextdsm, startupinfo=si)
                    subprocess.call(gdalruntextdem, startupinfo=si)

                    dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
                    dsm_array = dataset.ReadAsArray().astype(np.float)
                    dataset2 = gdal.Open(self.plugin_dir + '/data/clipdem.tif')
                    dem_array = dataset2.ReadAsArray().astype(np.float)

                    if not (dsm_array.shape[0] == dem_array.shape[0]) & (dsm_array.shape[1] == dem_array.shape[1]):
                        QMessageBox.critical(None, "Error", "All grids must be of same pixel resolution")
                        return

                geotransform = dataset.GetGeoTransform()
                scale = 1 / geotransform[1]

                nodata_test = (dsm_array == -9999)
                if nodata_test.any():  # == True
                    # QgsMessageBar.pushInfo(self.iface,"Grid " + str(f.attributes()[self.idx]) + " not calculated", "Includes NoData Pixels") #  Funkar inte
                    # QgsMessageBar(self.iface).pushMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated", "Includes NoData Pixels") # funkar inte
                    QgsMessageLog.logMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated. Includes NoData Pixels", level=QgsMessageLog.CRITICAL)
                else:
                    degree = float(self.dlg.degreeBox.currentText())
                    # Hade varit bra om ytterligare en trad hade kunnit anvandas istallet for imagemorphparam_v1
                    # self.startParamWorker(dsm_array, dem_array, scale, 0, degree, f, self.idx, self.dlg)
                    immorphresult = imagemorphparam_v1(dsm_array, dem_array, scale, self.imid, degree, self.dlg, imp_point)

                    # save to file
                    header = ' Wd pai   fai   zH  zHmax   zHstd'
                    numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f'
                    arr = np.concatenate((immorphresult["deg"], immorphresult["pai"], immorphresult["fai"],
                                        immorphresult["zH"], immorphresult["zHmax"], immorphresult["zH_sd"]), axis=1)
                    np.savetxt(self.folderPath[0] + '/anisotropic_result_' + str(f.attributes()[self.idx]) + '.txt', arr,
                               fmt=numformat, delimiter=' ', header=header, comments='')

                    header = ' pai  fai   zH    zHmax    zHstd '
                    numformat = '%4.3f %4.3f %5.3f %5.3f %5.3f'
                    arr2 = np.array([[immorphresult["pai_all"], immorphresult["fai_all"], immorphresult["zH_all"],
                                      immorphresult["zHmax_all"], immorphresult["zH_sd_all"]]])
                    np.savetxt(self.folderPath[0] + '/isotropic_result_' + str(f.attributes()[self.idx]) + '.txt', arr2,
                                fmt=numformat, delimiter=' ', header=header, comments='')

                dataset = None
                dataset2 = None
                dataset3 = None
                self.progress.emit()
                # j += 1
            # Nas om hela loopen utforts, kan anvandas for att tilldela ret-variabeln resultatet av arbetet som ska
            # ska skickas tillbaka till image_morph_param.py
            if self.killed is False:
                self.progress.emit()
                ret = 1

        # Om try-statsen stoter pa error nas denna except-sats som skickar en signal med felmeddelandet till
        # image_morph_param.py
        except Exception, e:
            # forward the exception upstream
            ret = 0
            # QgsMessageLog.logMessage("Here", level=QgsMessageLog.CRITICAL)
            self.error.emit(e, traceback.format_exc())

        # Traden ar fardig, skicka finished signalen. Skickar enbart en boolean ifall traden avbrots eller inte eftersom
        # information skrivs till textfiler pa disken istallet for att returneras till tex QGIS. self.killed kan bytas
        # ut mot ret-variabeln istallet for att returnera nagot annat
        self.finished.emit(ret)
        # self.finished.emit(self.killed)

    # Metod som tar emot signalen som sager att traden ska avbrytas, andrar self.killed till True.
    def kill(self):
        self.killed = True

    #ALLT UNDER DENNA KOMMENTAR FUNGERAR INTE aN OCH ANVaNDS INTE

    # def startParamWorker(self, dsm, dem, scale, mid, degree, f, idx, dlg):
    #     # create a new worker instance
    #     paramworker = ParamWorker(dsm, dem, scale, mid, degree, f, idx, dlg)
    #
    #     #self.dlg.runButton.setText('Cancel')
    #     #self.dlg.runButton.clicked.disconnect()
    #     self.dlg.runButton.clicked.connect(paramworker.kill)
    #     #self.dlg.closeButton.setEnabled(False)
    #
    #     # start the worker in a new thread
    #     paramthread = QThread(self)
    #     paramworker.moveToThread(paramthread)
    #     paramworker.finished.connect(self.paramworkerFinished)
    #     paramworker.error.connect(self.paramworkerError)
    #     #worker.progress.connect(self.progress_update)
    #     paramthread.started.connect(paramworker.run)
    #     paramthread.start()
    #     self.paramthread = paramthread
    #     self.paramworker = paramworker
    #
    # def paramworkerFinished(self, ret, f, idx):
    #     # clean up the worker and thread
    #     try:
    #         self.paramworker.deleteLater()
    #     except RuntimeError:
    #         pass
    #     self.paramthread.quit()
    #     self.paramthread.wait()
    #     self.paramthread.deleteLater()
    #
    #     if ret is not None:
    #          save to file
    #         header = ' Wd pai   fai   zH  zHmax   zHstd'
    #         numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f'
    #         arr = np.concatenate((ret["deg"], ret["pai"], ret["fai"],
    #                               ret["zH"], ret["zHmax"], ret["zH_sd"]), axis=1)
    #         np.savetxt(self.folderPath[0] + '/anisotropic_result_' + str(f.attributes()[idx]) + '.txt', arr,
    #                    fmt=numformat, delimiter=' ', header=header, comments='')
    #
    #         header = ' pai   zH    zHmax    zHstd'
    #         numformat = '%4.3f %5.3f %5.3f %5.3f'
    #         arr2 = np.array([[ret["pai_all"], ret["zH_all"], ret["zHmax_all"],
    #                           ret["zH_sd_all"]]])
    #         np.savetxt(self.folderPath[0] + '/isotropic_result_' + str(f.attributes()[idx]) + '.txt', arr2,
    #                    fmt=numformat, delimiter=' ', header=header, comments='')
    #
    #     else:
    #         notify the user that something went wrong
    #         self.dlg.runButton.setText('Run')
    #         self.dlg.runButton.clicked.disconnect()
    #         self.dlg.runButton.clicked.connect(self.start_progress)
    #         self.dlg.closeButton.setEnabled(True)
    #         self.dlg.progressBar.setValue(0)

    # def paramworkerError(self, e, exception_string):
    #     strerror = "ParamWorker thread raised an exception: " + str(e)
    #     QgsMessageLog.logMessage(strerror.format(exception_string), level=QgsMessageLog.CRITICAL)
