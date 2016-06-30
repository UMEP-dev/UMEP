# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FootprintModel
                                 A QGIS plugin
 Generates source area contributing to turbulent fluxes at central point
                              -------------------
        begin                : 2015-10-22
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Christoph Kent
        email                : C.W.Kent@pgr.reading.ac.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QColor
from qgis.gui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
#import resources
# Import the code for the dialog
from footprint_model_dialog import FootprintModelDialog
import os.path
from ..Utilities.qgiscombomanager import *
import numpy as np
import KingsFootprint_UMEP as fp
from osgeo import gdal
import subprocess
import sys
import webbrowser

# import sys
# sys.path.append('C:/OSGeo4W64/apps/Python27/Lib/site-packages/pydev')
# import pydevd


class FootprintModel:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'FootprintModel_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = FootprintModelDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Footprint model')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'FootprintModel')
        # self.toolbar.setObjectName(u'FootprintModel')

        # get reference to the canvas
        self.canvas = self.iface.mapCanvas()
        self.poiLayer = None
        self.polyLayer = None
        self.folderPath = 'None'
        self.degree = 5.0
        self.point = None
        self.pointx = None
        self.pointy = None
        self.provider = None

        # #g pin tool
        self.pointTool = QgsMapToolEmitPoint(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)
        self.dlg.pushButtonImport.clicked.connect(self.import_file)
        self.dlg.runButton.clicked.connect(self.start_process)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.selectpoint.clicked.connect(self.select_point)
        # self.dlg.generateArea.clicked.connect(self.generate_area)
        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.progressBar.setValue(0)
        self.dlg.checkBoxOnlyBuilding.toggled.connect(self.text_enable)

        self.fileDialogOpen = QFileDialog()
        self.filePath = None
        self.data = None
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        self.layerComboManagerPoint = VectorLayerCombo(self.dlg.comboBox_Point)
        fieldgen = VectorLayerCombo(self.dlg.comboBox_Point, initLayer="", options={"geomType": QGis.Point})
        # self.layerComboManagerPointField = FieldCombo(self.dlg.comboBox_Field, fieldgen, initField="")
        self.layerComboManagerDSMbuildground = RasterLayerCombo(self.dlg.comboBox_DSMbuildground)
        RasterLayerCombo(self.dlg.comboBox_DSMbuildground, initLayer="")
        self.layerComboManagerDEM = RasterLayerCombo(self.dlg.comboBox_DEM)
        RasterLayerCombo(self.dlg.comboBox_DEM, initLayer="")
        self.layerComboManagerDSMbuild = RasterLayerCombo(self.dlg.comboBox_DSMbuild)
        RasterLayerCombo(self.dlg.comboBox_DSMbuild, initLayer="")

        if not (os.path.isdir(self.plugin_dir + '/data')):
            os.mkdir(self.plugin_dir + '/data')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('FootprintModel', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/FootprintModel/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Footprint model'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Footprint model'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def import_file(self):
        self.fileDialogOpen.open()
        result = self.fileDialogOpen.exec_()
        if result == 1:
            self.filePath = self.fileDialogOpen.selectedFiles()
            self.dlg.textInputMetdata.setText(self.filePath[0])
            delim = None  # space

            try:
                self.data = np.loadtxt(self.filePath[0], skiprows=1, delimiter=delim)
            except:
                QMessageBox.critical(None, "Import Error", "Check format of textfile format."
                                            " See help section to get correct format.")
                return

            if not self.data.shape[1] == 12:
                QMessageBox.critical(None, "Import Error", "Check format of textfile format."
                                            " See help section to get correct format.")
                return

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])
            self.dlg.runButton.setEnabled(True)

    def create_point(self, point):
        self.dlg.closeButton.setEnabled(1)
        QgsMapLayerRegistry.instance().addMapLayer(self.poiLayer)

        # create the feature
        fc = int(self.provider.featureCount())
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPoint(point))
        feature.setAttributes([fc, point.x(), point.y()])
        self.poiLayer.startEditing()
        self.poiLayer.addFeature(feature, True)
        self.poiLayer.commitChanges()
        self.poiLayer.triggerRepaint()
        self.dlg.setEnabled(True)
        self.dlg.activateWindow()
        self.pointx = point.x()
        self.pointy = point.y()
        self.point = point

    def select_point(self):  # Connected to "Select Point on Canves"
        if self.poiLayer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(self.poiLayer.id())
        self.canvas.setMapTool(self.pointTool)  # Calls a canvas click and create_point
        self.dlg.setEnabled(False)
        self.create_point_layer()

    def create_point_layer(self):
        canvas = self.iface.mapCanvas()
        srs = canvas.mapSettings().destinationCrs()
        self.srs = srs
        crs = str(srs.authid())
        uri = "Point?field=id:integer&field=x:double&field=y:double&index=yes&crs=" + crs
        self.poiLayer = QgsVectorLayer(uri, "Flux tower", "memory")
        self.provider = self.poiLayer.dataProvider()

    def text_enable(self):
        if self.dlg.checkBoxOnlyBuilding.isChecked():
            self.dlg.label_2.setEnabled(False)
            self.dlg.label_3.setEnabled(False)
            self.dlg.label_4.setEnabled(True)
        else:
            self.dlg.label_2.setEnabled(True)
            self.dlg.label_3.setEnabled(True)
            self.dlg.label_4.setEnabled(False)

    def start_process(self):

        #Check OS and dep
        if sys.platform == 'darwin':
            gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        else:
            gdalwarp_os_dep = 'gdalwarp'

        if self.dlg.checkBoxUseFile.isChecked():
            if self.data == 'None':
                QMessageBox.critical(None, "No inputfile selected", "Choose an input file."
                                            " See help section to get correct format.")
                return
            # QMessageBox.critical(None, "test1", str(self.data.shape))
            it = self.data.shape[0]
            yyyy = self.data[:, 0]
            doy = self.data[:, 1]
            ih = self.data[:, 2]
            imin = self.data[:, 3]
            z_0_input = self.data[:, 4]
            z_d_input = self.data[:, 5]
            z_m_input = self.data[:, 6]
            wind = self.data[:, 7]
            sigv = self.data[:, 8]
            Obukhov = self.data[:, 9]
            ustar = self.data[:, 10]
            wdir = self.data[:, 11]
            # QMessageBox.critical(None, "Test", str(it))
            # return
        else:
            manylines = 0
            it = 1
            yyyy = np.ones((1, 1)) * -999
            doy = np.ones((1, 1)) * -999
            ih = np.ones((1, 1)) * -999
            imin = np.ones((1, 1)) * -999
            z_0_input = np.ones((1, 1)) * self.dlg.doubleSpinBox_z0.value()
            z_d_input = np.ones((1, 1)) * self.dlg.doubleSpinBox_zd.value()
            z_m_input = np.ones((1, 1)) * self.dlg.doubleSpinBox_zm.value()
            wind = np.ones((1, 1)) * self.dlg.doubleSpinBox_ws.value()
            sigv = np.ones((1, 1)) * self.dlg.doubleSpinBox_wssd.value()
            Obukhov = np.ones((1, 1)) * self.dlg.doubleSpinBox_L.value()
            ustar = np.ones((1, 1)) * self.dlg.doubleSpinBox_ustar.value()
            wdir = np.ones((1, 1)) * self.dlg.doubleSpinBox_wd.value()

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

        if sys.platform == 'win32':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            si = None

        if self.dlg.checkBoxVectorLayer.isChecked():
            point = self.layerComboManagerPoint.getLayer()
            if point is None:
                QMessageBox.critical(None, "Error", "No valid point layer is selected")
                return

            for poi in point.getFeatures():
                loc = poi.geometry().asPoint()
                self.pointx = loc[0]
                self.pointy = loc[1]
        else:
            if not self.pointx:
                QMessageBox.critical(None, "Error", "No click registred on map canvas")
                return

        x = self.pointx
        y = self.pointy
        r = self.dlg.spinBoxFetch.value()
        # r = 1000

        # coords = "{}, {}".format(x, y)
        # QMessageBox.critical(None, "Test", str(coords))

        if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
            dsm_build = self.layerComboManagerDSMbuild.getLayer()
            if dsm_build is None:
                QMessageBox.critical(None, "Error", "No valid building DSM raster layer is selected")
                return

            provider = dsm_build.dataProvider()
            filePath_dsm_build = str(provider.dataSourceUri())
            # Kolla om memorylayer går att användas istället för dir_poly tempfilen.
            gdalruntextdsm_build = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                   ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
                                   filePath_dsm_build + '" "' + self.plugin_dir + '/data/clipdsm.tif"'
            # gdalruntextdsm_build = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + dir_poly + \
            #                        ' -crop_to_cutline -of GTiff ' + filePath_dsm_build + \
            #                        ' ' + self.plugin_dir + '/data/clipdsm.tif'
            if sys.platform == 'win32':
                subprocess.call(gdalruntextdsm_build, startupinfo=si)
            else:
                os.system(gdalruntextdsm_build)

            dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
            dsm = dataset.ReadAsArray().astype(np.float)
            sizex = dsm.shape[0]
            sizey = dsm.shape[1]
            dem = np.zeros((sizex, sizey))

        else:  # Both building ground heights
            dsm = self.layerComboManagerDSMbuildground.getLayer()
            dem = self.layerComboManagerDEM.getLayer()

            if dsm is None:
                QMessageBox.critical(None, "Error", "No valid ground and building DSM raster layer is selected")
                return
            if dem is None:
                QMessageBox.critical(None, "Error", "No valid ground DEM raster layer is selected")
                return

            # # get raster source - gdalwarp
            provider = dsm.dataProvider()
            filePath_dsm = str(provider.dataSourceUri())
            provider = dem.dataProvider()
            filePath_dem = str(provider.dataSourceUri())

            gdalruntextdsm = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                               ' ' + str(x + r ) + ' ' + str(y + r) + ' -of GTiff "' + \
                                               filePath_dsm + '" "' + self.plugin_dir + '/data/clipdsm.tif"'
            gdalruntextdem = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
                                   ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
                                   filePath_dem + '" "' + self.plugin_dir + '/data/clipdem.tif"'

            if sys.platform == 'win32':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.call(gdalruntextdsm, startupinfo=si)
                subprocess.call(gdalruntextdem, startupinfo=si)
            else:
                os.system(gdalruntextdsm)
                os.system(gdalruntextdem)
            # QMessageBox.critical(None, "test", gdalruntextdem)
            dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
            dsm = dataset.ReadAsArray().astype(np.float)
            dataset2 = gdal.Open(self.plugin_dir + '/data/clipdem.tif')
            dem = dataset2.ReadAsArray().astype(np.float)

            sizex = dsm.shape[0]
            sizey = dsm.shape[1]

            if not (dsm.shape[0] == dem.shape[0]) & (dsm.shape[1] == dem.shape[1]):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

        geotransform = dataset.GetGeoTransform()
        # scale = 1 / geotransform[1]
        res = geotransform[1]
        # QMessageBox.critical(None, "test", str(res) + ' ' + str(sizey) + ' ' + str(sizex))



        nodata_test = (dsm == -9999)
        if nodata_test.any():
            QMessageBox.critical(None, "Error", "Grids includes nodata pixels. Is your point closer than " +
                                 str(r) + " meters (maximum fetch) from the extent of the DSM?")
            return
        else:

            # #Calculate Z0m and Zdm depending on the Z0 method
            ro = self.dlg.comboBox_Roughness.currentIndex()
            if ro == 0:
                Rm = 'RT'
            elif ro == 1:
                Rm = 'Rau'
            elif ro == 2:
                Rm = 'Bot'
            elif ro == 3:
                Rm = 'Mac'
            elif ro == 4:
                Rm = 'Mho'
            else:
                Rm = 'Kan'

            Wfai, Wpai, WzH, WzMax, WzSdev,Wz_d_output,Wz_0_output, rotatedphi, rotatedphiPerc = fp.footprintiter(it, z_0_input, z_d_input,
                        z_m_input, wind, sigv, Obukhov, ustar, wdir, dsm, dem, sizey, sizex, res, self.dlg, r,Rm)

            # save to file
            header = 'iy id it imin z_0_input z_d_input z_m_input wind sigv Obukhov ustar dir fai pai zH zMax zSdev zd z0'
            numfmt = '%3d %2d %3d %2d %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f'
            mat = np.column_stack((yyyy[0:it], doy[0:it], ih[0:it], imin[0:it], z_0_input[0:it], z_d_input[0:it],
                                   z_m_input[0:it], wind[0:it], sigv[0:it], Obukhov[0:it], ustar[0:it], wdir[0:it],
                                   Wfai, Wpai, WzH, WzMax, WzSdev,Wz_d_output,Wz_0_output))
            pre = self.dlg.textOutput_prefix.text()
            np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'SourceMorphParameters.txt', mat, fmt=('%5.5f'), comments='', header=header)

            # QMessageBox.critical(None, "Test", str(mat))
            # rotatedphiPerc[rotatedphiPerc == 0] = -999
            rotatedphiPerc = (rotatedphiPerc - 100) * - 1
            rotatedphiPerc[rotatedphiPerc >= 100] = -9999
            fp.saveraster(dataset, self.folderPath[0] + '/' + pre + '_' + 'SourceAreaCumulativePercentage.tif', rotatedphiPerc)

            # load roof irradiance result into map canvas
            if self.dlg.checkBoxIntoCanvas.isChecked():
                rlayer = self.iface.addRasterLayer(self.folderPath[0] + '/' + pre + '_' + 'SourceAreaCumulativePercentage.tif')

                # Trigger a repaint
                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)

                rlayer.loadNamedStyle(self.plugin_dir + '/footprint_style.qml')

                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)

                rlayer.triggerRepaint()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = "http://www.urban-climate.net/umep/UMEP_Manual#Pre-Processor:" \
              "_Urban_Morphology:_Source_Area_Model_.28Point.29_-_Footprint_Model"
        webbrowser.open_new_tab(url)