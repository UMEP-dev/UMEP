from PyQt4 import QtCore
# from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
import traceback
from ..Utilities.landCoverFractions_v1 import *
# import Image
# from scipy import *
import numpy as np
from osgeo import gdal
import subprocess
# import os
# import PIL
# from paramWorker import ParamWorker
# from pydev import pydevd
# import sys

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, lc_grid, poly, poly_field, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                 folderPath, dlg, imid, radius, degree):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.lc_grid = lc_grid
        self.poly = poly
        self.poly_field = poly_field
        self.vlayer = vlayer
        self.prov = prov  # provider
        self.fields = fields
        self.idx = idx
        self.dir_poly = dir_poly
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.folderPath = folderPath
        self.dlg = dlg
        self.imid = imid
        self.radius = radius
        self.degree = degree

    def run(self):
        # ska nagot returneras fran traden sker detta genom denna ret-variabel och retuneras till image_morph_param.py
        # genom finished signalen ovan. bool skickas for tillfallet, kan bytas ut mot tex Object for att skicka diverse
        # data. Behovs inte for just detta verktyg.
        ret = 0
        imp_point = 0

        # Allt arbete en trad ska utforas maste goras i en try-sats
        try:
            # j = 0
            for f in self.vlayer.getFeatures():  # looping through each grid polygon
                # Kollar sa att traden inte har avbrutits, ifall den har det sa slutar loopning.
                if self.killed is True:
                    break

                attributes = f.attributes()
                geometry = f.geometry()
                feature = QgsFeature()
                feature.setAttributes(attributes)
                feature.setGeometry(geometry)

                if self.imid == 1:  # use center point
                    r = self.radius
                    y = f.geometry().centroid().asPoint().y()
                    x = f.geometry().centroid().asPoint().x()
                else:
                    r = 0
                    writer = QgsVectorFileWriter(self.dir_poly, "CP1250", self.fields, self.prov.geometryType(),
                                                 self.prov.crs(), "ESRI shapefile")

                    if writer.hasError() != QgsVectorFileWriter.NoError:
                        self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))
                    writer.addFeature(feature)
                    del writer

                # if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
                provider = self.lc_grid.dataProvider()
                filePath_lc_grid = str(provider.dataSourceUri())

                if self.imid == 1:
                    gdalruntextlc_grid = 'gdalwarp -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                           ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff ' + \
                                           filePath_lc_grid + ' ' + self.plugin_dir + '/data/clipdsm.tif'
                else:
                    gdalruntextlc_grid = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + \
                                           ' -crop_to_cutline -of GTiff ' + filePath_lc_grid + ' ' + \
                                           self.plugin_dir + '/data/clipdsm.tif'

                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.call(gdalruntextlc_grid, startupinfo=si)

                dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
                lc_grid_array = dataset.ReadAsArray().astype(np.float)

                nodata_test = (lc_grid_array == -9999)
                if nodata_test.any():  # == True
                    # QgsMessageBar.pushInfo(self.iface,"Grid " + str(f.attributes()[self.idx]) + " not calculated", "Includes NoData Pixels") #  Funkar inte
                    # QgsMessageBar(self.iface).pushMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated", "Includes NoData Pixels") # funkar inte
                    QgsMessageLog.logMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated. Includes NoData Pixels", level=QgsMessageLog.CRITICAL)
                else:
                    # degree = float(self.dlg.degreeBox.currentText())
                    landcoverresult = landcover_v1(lc_grid_array, self.imid, self.degree, self.dlg, imp_point)

                    # save to file
                    pre = self.dlg.textOutput_prefix.text()
                    header = 'Wd Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
                    numformat = '%3d %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
                    arr = np.concatenate((landcoverresult["deg"], landcoverresult["lc_frac"]), axis=1)
                    np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'LCFG_anisotropic_result_' + str(f.attributes()[self.idx]) + '.txt', arr,
                               fmt=numformat, delimiter=' ', header=header, comments='')

                    header = ' Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
                    numformat = '%5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
                    arr2 = np.array(landcoverresult["lc_frac_all"])
                    np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'LCFG_isotropic_result_' + str(f.attributes()[self.idx]) + '.txt', arr2,
                                fmt=numformat, delimiter=' ', header=header, comments='')

                dataset = None
                dataset2 = None
                dataset3 = None
                self.progress.emit()

            if self.killed is False:
                self.progress.emit()
                ret = 1

        except Exception, e:
            ret = 0
            # QgsMessageLog.logMessage("Here", level=QgsMessageLog.CRITICAL)
            self.error.emit(e, traceback.format_exc())

        self.finished.emit(ret)
        # self.finished.emit(self.killed)

    def kill(self):
        self.killed = True
