from PyQt4 import QtCore
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
import traceback
from ..Utilities.landCoverFractions_v1 import *
import numpy as np
from osgeo import gdal
import subprocess
import sys
import os

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

        #Check OS and dep
        if sys.platform == 'darwin':
            gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        else:
            gdalwarp_os_dep = 'gdalwarp'

        ret = 0
        imp_point = 0

        try:
            # j = 0
            for f in self.vlayer.getFeatures():  # looping through each grid polygon
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

                provider = self.lc_grid.dataProvider()
                filePath_lc_grid = str(provider.dataSourceUri())

                if self.imid == 1:
                    gdalruntextlc_grid = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                           ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff ' + \
                                           filePath_lc_grid + ' ' + self.plugin_dir + '/data/clipdsm.tif'
                else:
                    gdalruntextlc_grid = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + \
                                           ' -crop_to_cutline -of GTiff ' + filePath_lc_grid + ' ' + \
                                           self.plugin_dir + '/data/clipdsm.tif'

                if sys.platform == 'win32':
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.call(gdalruntextlc_grid, startupinfo=si)
                else:
                    os.system(gdalruntextlc_grid)

                dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
                lc_grid_array = dataset.ReadAsArray().astype(np.float)
                nd = dataset.GetRasterBand(1).GetNoDataValue()
                nodata_test = (lc_grid_array == nd)
                if nodata_test.any():  # == True
                    # QgsMessageBar.pushInfo(self.iface,"Grid " + str(f.attributes()[self.idx]) + " not calculated", "Includes NoData Pixels") #  Funkar inte
                    # QgsMessageBar(self.iface).pushMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated", "Includes NoData Pixels") # funkar inte
                    QgsMessageLog.logMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated. Includes NoData Pixels", level=QgsMessageLog.CRITICAL)
                else:
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
                                fmt=numformat, delimiter=' ', header=header, comments='') #TODO FREDRIK. Spara som en fil

                    self.vlayer.changeAttributeValue(4, 6, f.attributes()[self.idx] + 6)  # TODO NIKLAS
                    self.vlayer.updateFields()

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
