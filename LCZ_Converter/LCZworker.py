from PyQt4 import QtCore
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QMessageBox
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
from LCZ_fractions import *
import traceback
import numpy as np
from osgeo import gdal
import subprocess
import sys
import linecache
import os
import fileinput

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, lc_grid, poly, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                 folderPath, dlg):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.lc_grid = lc_grid
        self.poly = poly
        self.vlayer = vlayer
        self.prov = prov  # provider
        self.fields = fields
        self.idx = idx
        self.dir_poly = dir_poly
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.folderPath = folderPath
        self.dlg = dlg

    def run(self):

        #Check OS and dep
        if sys.platform == 'darwin':
            gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        else:
            gdalwarp_os_dep = 'gdalwarp'

        ret = 0
        arrmat1 = np.empty((1, 8))
        arrmat2 = np.empty((1, 8))
        arrmat3 = np.empty((1, 8))
        pre = str(self.dlg.lineEdit.text())

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

                writer = QgsVectorFileWriter(self.dir_poly, "CP1250", self.fields, self.prov.geometryType(),
                                                 self.prov.crs(), "ESRI shapefile")

                if writer.hasError() != QgsVectorFileWriter.NoError:
                    self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))
                
                writer.addFeature(feature)
                del writer

                provider = self.lc_grid.dataProvider()
                filePath_lc_grid = str(provider.dataSourceUri())
                
                gdalruntextlc_grid = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + ' -crop_to_cutline -of GTiff "' + filePath_lc_grid + '" "' +        self.plugin_dir + '/data/clipdsm.tif"'

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
                if np.sum(lc_grid_array) == (lc_grid_array.shape[0] * lc_grid_array.shape[1] * nd):
                    QgsMessageLog.logMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated. Includes Only NoData Pixels", level=QgsMessageLog.CRITICAL)
                    cal = 0
                else:
                    lc_grid_array[lc_grid_array == nd] = 0
                    cal = 1

                if cal == 1:
                    lczfractions = LCZ_fractions(lc_grid_array,self.dlg)
                    lczfractions["lc_frac_all"] = np.where(np.isnan(lczfractions["lc_frac_all"] ),-9999,lczfractions["lc_frac_all"] )
                    lczfractions["bui_aero"] = np.where(np.isnan(lczfractions["bui_aero"]),-9999,lczfractions["bui_aero"])
                    lczfractions["veg_aero"] = np.where(np.isnan(lczfractions["veg_aero"]),-9999,lczfractions["veg_aero"])
                    lczfractions = self.resultcheck(lczfractions)
                    
                    arr1 = np.array([f.attributes()[self.idx], lczfractions["lc_frac_all"][0,0], lczfractions["lc_frac_all"][0,1],
                                      lczfractions["lc_frac_all"][0,2], lczfractions["lc_frac_all"][0,3], lczfractions["lc_frac_all"][0,4],
                                     lczfractions["lc_frac_all"][0,5], lczfractions["lc_frac_all"][0,6]])
                    arr2 = np.array([f.attributes()[self.idx], lczfractions["bui_aero"][0,0], lczfractions["bui_aero"][0,1],
                                      lczfractions["bui_aero"][0,2], lczfractions["bui_aero"][0,3], lczfractions["bui_aero"][0,4],
                                     lczfractions["bui_aero"][0,5], lczfractions["bui_aero"][0,6]])
                    arr3 = np.array([f.attributes()[self.idx], lczfractions["veg_aero"][0,0], lczfractions["veg_aero"][0,1],
                                      lczfractions["veg_aero"][0,2], lczfractions["veg_aero"][0,3], lczfractions["veg_aero"][0,4],
                                     lczfractions["veg_aero"][0,5], lczfractions["veg_aero"][0,6]])

                    arrmat1 = np.vstack([arrmat1, arr1])
                    arrmat2 = np.vstack([arrmat2, arr2])
                    arrmat3 = np.vstack([arrmat3, arr3])

                dataset = None
                dataset2 = None
                dataset3 = None
                self.progress.emit()

            header1 = 'ID Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
            numformat = '%3d %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
            arrmatsave1 = arrmat1[1: arrmat1.shape[0], :]
            np.savetxt(self.folderPath[0] + '/' +pre +'_'+'LCFGrid_isotropic.txt', arrmatsave1, fmt=numformat, delimiter=' ', header=header1, comments='')
            header2 = ' ID  pai   fai   zH  zHmax   zHstd  zd  z0'
            numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
            arrmatsave2 = arrmat2[1: arrmat2.shape[0], :]
            np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'build_MPGrid_isotropic.txt', arrmatsave2,fmt=numformat, delimiter=' ', header=header2, comments='')
            header3 = ' ID  pai   fai   zH  zHmax   zHstd  zd  z0'
            numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
            arrmatsave3 = arrmat3[1: arrmat3.shape[0], :]
            np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'veg_MPGrid_isotropic.txt', arrmatsave3,fmt=numformat, delimiter=' ', header=header3, comments='')
            
            #when files are saved through the np.savetext method the values are rounded according to the information in
            #the numformat variable. This can cause the total sum of the values in a line in the text file to not be 1
            #this method reads through the text file after it has been generated to make sure every line has a sum of 1.
            self.textFileCheck(pre)

            if self.dlg.checkBox_2.isChecked():
                self.addattributes(self.vlayer, arrmatsave1, header1, pre)
                self.addattributes(self.vlayer, arrmatsave2, header2, pre)
                self.addattributes(self.vlayer, arrmatsave3, header3, pre)

            if self.killed is False:
                self.progress.emit()
                ret = 1

        except Exception, e:
            ret = 0
            #self.error.emit(e, traceback.format_exc())
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)
        # self.finished.emit(self.killed)

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

    def addattributes(self, vlayer, matdata, header, pre):
        # vlayer = self.vlayer
        current_index_length = len(vlayer.dataProvider().attributeIndexes())
        caps = vlayer.dataProvider().capabilities()

        if caps & QgsVectorDataProvider.AddAttributes:
            #vlayer.startEditing()
            line_split = header.split()
            for x in range(1, len(line_split)):

                vlayer.dataProvider().addAttributes([QgsField(pre + '_' + line_split[x], QVariant.Double)])
                vlayer.commitChanges()
                vlayer.updateFields()

            attr_dict = {}

            for y in range(0, matdata.shape[0]):
                attr_dict.clear()
                idx = int(matdata[y, 0])
                for x in range(1, matdata.shape[1]):
                    attr_dict[current_index_length + x - 1] = float(matdata[y, x])
                #QMessageBox.information(None, "Error", str(line_split[x]))
                vlayer.dataProvider().changeAttributeValues({idx: attr_dict})

            vlayer.commitChanges()
            vlayer.updateFields()
        else:
            QMessageBox.critical(None, "Error", "Vector Layer does not support adding attributes")

    def resultcheck(self, landcoverresult):
        total = 0.
        arr = landcoverresult["lc_frac_all"]

        for x in range(0, len(arr[0])):
            total += arr[0, x]

        if total != 1.0:
            diff = total - 1.0

            maxnumber = max(arr[0])

            for x in range(0, len(arr[0])):
                if maxnumber == arr[0, x]:
                    arr[0, x] -= diff
                    break

        landcoverresult["lc_frac_all"] = arr

        return landcoverresult
    
    def textFileCheck(self, pre):
        try:
            file_path = self.folderPath[0] + '/' + pre + '_' + 'LCFG_isotropic.txt'
            if os.path.isfile(file_path):
                wrote_header = False
                for line in fileinput.input(file_path, inplace=1):
                    if not wrote_header:
                        print line,
                        wrote_header = True
                    else:
                        line_split = line.split()
                        total = 0.
                        # QgsMessageLog.logMessage(str(line), level=QgsMessageLog.CRITICAL)
                        for x in range(1, len(line_split)):
                            total += float(line_split[x])

                        if total == 1.0:
                            print line,
                        else:
                            diff = total - 1.0
                            # QgsMessageLog.logMessage("Diff: " + str(diff), level=QgsMessageLog.CRITICAL)
                            max_number = max(line_split[1:])
                            # QgsMessageLog.logMessage("Max number: " + str(max_number), level=QgsMessageLog.CRITICAL)

                            for x in range(1, len(line_split)):
                                if float(max_number) == float(line_split[x]):
                                    line_split[x] = float(line_split[x]) - diff
                                    break
                            if int(line_split[0]) < 10:
                                string_to_print = '  '
                            elif int(line_split[0]) < 100:
                                string_to_print = ' '
                            else:
                                string_to_print = ''

                            for element in line_split[:-1]:
                                string_to_print += str(element) + ' '
                            string_to_print += str(line_split[-1])
                            string_to_print += '\n'

                            print string_to_print,
                fileinput.close()
        except Exception, e:
            errorstring = self.print_exception()
            QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)
            fileinput.close()

    def kill(self):
        self.killed = True
