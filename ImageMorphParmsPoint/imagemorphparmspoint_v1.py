# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageMorphParmsPoint
                                 A QGIS plugin
 This plugin calculates Morphometric parameters fro a high resolution DSM around a point of interest
                              -------------------
        begin                : 2015-01-12
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg GU
        email                : fredrikl@gvc.gu.se
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
from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog
from qgis.gui import *
from qgis.core import QgsMapLayerProxyModel, QgsFeature, QgsGeometry, QgsVectorLayer, QgsPointXY, QgsVectorFileWriter, QgsProject
import os
from ..Utilities import RoughnessCalcFunctionV2 as rg
from osgeo import gdal
import subprocess
import webbrowser
from ..Utilities.imageMorphometricParms_v1 import *
from ..WallHeight import wallalgorithms as wa
# Initialize Qt resources from file resources.py
# from . import resources_rc
import sys

# Import the code for the dialog
from .imagemorphparmspoint_v1_dialog import ImageMorphParmsPointDialog


class ImageMorphParmsPoint(object):
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
            'ImageMorphParmsPoint_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ImageMorphParmsPointDialog()
        self.dlg.runButton.clicked.connect(self.start_process)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.selectpoint.clicked.connect(self.select_point)
        self.dlg.generateArea.clicked.connect(self.generate_area)
        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.progressBar.setValue(0)
        self.dlg.checkBoxOnlyBuilding.toggled.connect(self.text_enable)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(QFileDialog.Directory)
        self.fileDialog.setOption(QFileDialog.ShowDirsOnly, True)

        for i in range(1, 25):
            if 360 % i == 0:
                self.dlg.degreeBox.addItem(str(i))
        self.dlg.degreeBox.setCurrentIndex(4)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Image Morphometric Parameters Point')

        # get reference to the canvas
        self.canvas = self.iface.mapCanvas()
        self.poiLayer = None
        self.polyLayer = None
        self.folderPath = 'None'
        self.degree = 5.0
        self.point = None
        self.pointx = None
        self.pointy = None

        # #g pin tool
        self.pointTool = QgsMapToolEmitPoint(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)

        self.layerComboManagerPoint = QgsMapLayerComboBox(self.dlg.widgetPointLayer)
        self.layerComboManagerPoint.setCurrentIndex(-1)
        self.layerComboManagerPoint.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.layerComboManagerPoint.setFixedWidth(175)
        self.layerComboManagerDSMbuildground = QgsMapLayerComboBox(self.dlg.widgetDSMbuildground)
        self.layerComboManagerDSMbuildground.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSMbuildground.setFixedWidth(175)
        self.layerComboManagerDSMbuildground.setCurrentIndex(-1)
        self.layerComboManagerDEM = QgsMapLayerComboBox(self.dlg.widgetDEM)
        self.layerComboManagerDEM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDEM.setFixedWidth(175)
        self.layerComboManagerDEM.setCurrentIndex(-1)
        self.layerComboManagerDSMbuild = QgsMapLayerComboBox(self.dlg.widgetDSMbuild)
        self.layerComboManagerDSMbuild.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSMbuild.setFixedWidth(175)
        self.layerComboManagerDSMbuild.setCurrentIndex(-1)


        if not (os.path.isdir(self.plugin_dir + '/data')):
            os.mkdir(self.plugin_dir + '/data')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ImageMorphParmsPoint', message)

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
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # icon = QIcon(icon_path)
        # action = QAction(icon, text, parent)
        # action.triggered.connect(callback)
        # action.setEnabled(enabled_flag)
        #
        # if status_tip is not None:
        #     action.setStatusTip(status_tip)
        #
        # if whats_this is not None:
        #     action.setWhatsThis(whats_this)
        #
        # if add_to_toolbar:
        #     self.toolbar.addAction(action)
        #
        # if add_to_menu:
        #     self.iface.addPluginToMenu(
        #         self.menu,
        #         action)
        #
        # self.actions.append(action)
        #
        # return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/ImageMorphParmsPoint/ImageMorphIconPoint.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Image Morphometric Parameters Point'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Image Morphometric Parameters Point'),
                action)
            self.iface.removeToolBarIcon(action)

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def create_point(self, point):  # Var kommer point ifran???
        # report map coordinates from a canvas click
        # coords = "{}, {}".format(point.x(), point.y())
        # self.iface.messageBar().pushMessage("Coordinate selected", str(coords))
        self.dlg.closeButton.setEnabled(1)
        QgsProject.instance().addMapLayer(self.poiLayer)

        # create the feature
        fc = int(self.provider.featureCount())
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttributes([fc, point.x(), point.y()])
        self.poiLayer.startEditing()
        self.poiLayer.addFeature(feature)  # ,True
        self.poiLayer.commitChanges()
        self.poiLayer.triggerRepaint()
        self.dlg.setEnabled(True)
        self.dlg.activateWindow()
        self.pointx = point.x()
        self.pointy = point.y()
        self.point = point

    def generate_area(self):

        if self.dlg.checkBoxVectorLayer.isChecked():
            point = self.layerComboManagerPoint.currentLayer()
            if point is None:
                QMessageBox.critical(None, "Error", "No valid point layer is selected")
                return
            if not point.geometryType() == 0:
                QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
                return

            for poi in point.getFeatures():
                loc = poi.geometry().asPoint()
                self.pointx = loc[0]
                self.pointy = loc[1]
        else:
            if not self.pointx:
                QMessageBox.critical(None, "Error", "No click registred on map canvas")
                return

        self.dlg.runButton.setEnabled(1)
        self.create_poly_layer()

    def select_point(self):  # Connected to "Secelct Point on Canves"
        if self.poiLayer is not None:
            QgsProject.instance().removeMapLayer(self.poiLayer.id())
        if self.polyLayer is not None:
            self.polyLayer.startEditing()
            self.polyLayer.selectAll()
            self.polyLayer.deleteSelectedFeatures()
            self.polyLayer.commitChanges()
            QgsProject.instance().removeMapLayer(self.polyLayer.id())

        self.canvas.setMapTool(self.pointTool)  # Calls a canvas click and create_point

        self.dlg.setEnabled(False)
        self.create_point_layer()

    def create_point_layer(self):
        canvas = self.iface.mapCanvas()
        srs = canvas.mapSettings().destinationCrs()
        crs = str(srs.authid())
        uri = "Point?field=id:integer&field=x:double&field=y:double&index=yes&crs=" + crs
        self.poiLayer = QgsVectorLayer(uri, "Point of Interest", "memory")
        self.provider = self.poiLayer.dataProvider()

    def create_poly_layer(self):
        canvas = self.iface.mapCanvas()
        srs = canvas.mapSettings().destinationCrs()
        crs = str(srs.authid())
        uri = "Polygon?field=id:integer&index=yes&crs=" + crs
        # dir_poly = self.plugin_dir + '/data/poly_temp.shp'
        #self.polyLayer = QgsVectorLayer(dir_poly, "Study area", "ogr")
        self.polyLayer = QgsVectorLayer(uri, "Study area", "memory")
        self.provider = self.polyLayer.dataProvider()
        #QgsMapLayerRegistry.instance().addMapLayer(self.polyLayer)

        # create buffer feature
        fc = int(self.provider.featureCount())
        featurepoly = QgsFeature()

        # Assign feature the buffered geometry
        radius = self.dlg.spinBox.value()
        # featurepoly.setGeometry(
        #     QgsGeometry.fromPointXY(QgsPointXY(self.pointx, self.pointy)).buffer(radius, 1000, 1, 1, 1.0))
        featurepoly.setGeometry(
            QgsGeometry.fromPointXY(QgsPointXY(self.pointx, self.pointy)).buffer(radius, 1000)) #fix issue #400
        featurepoly.setAttributes([fc])
        self.polyLayer.startEditing()
        self.polyLayer.addFeature(featurepoly)
        self.polyLayer.commitChanges()

        QgsProject.instance().addMapLayer(self.polyLayer)
        self.polyLayer.setOpacity(0.42)
        self.polyLayer.triggerRepaint()

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

        # #Check OS and dep
        # if sys.platform == 'darwin':
        #     gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        # else:
        #     gdalwarp_os_dep = 'gdalwarp'

        # pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)
        self.dlg.progressBar.setValue(0)

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

        poly = self.iface.activeLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return

        prov = poly.dataProvider()
        fields = prov.fields()

        dir_poly = self.plugin_dir + '/data/poly_temp.shp'

        writer = QgsVectorFileWriter(dir_poly, "CP1250", fields, prov.wkbType(),
                                     prov.crs(), "ESRI shapefile")

        if writer.hasError() != QgsVectorFileWriter.NoError:
            self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))

        poly.selectAll()
        selection = poly.selectedFeatures()

        for feature in selection:
            writer.addFeature(feature)
        del writer

        if sys.platform == 'win32':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            si = None

        x = self.pointx
        y = self.pointy
        r = self.dlg.spinBox.value()

        if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
            dsm_build = self.layerComboManagerDSMbuild.currentLayer()
            if dsm_build is None:
                QMessageBox.critical(None, "Error", "No valid building DSM raster layer is selected")
                return

            provider = dsm_build.dataProvider()
            filePath_dsm_build = str(provider.dataSourceUri())
            # gdalruntextdsm_build = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
            #                        ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
            #                        filePath_dsm_build + '" "' + self.plugin_dir + '/data/clipdsm.tif"'
            # # gdalruntextdsm_build = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + dir_poly + \
            # #                        ' -crop_to_cutline -of GTiff ' + filePath_dsm_build + \
            # #                        ' ' + self.plugin_dir + '/data/clipdsm.tif'
            # if sys.platform == 'win32':
            #     subprocess.call(gdalruntextdsm_build, startupinfo=si)
            # else:
            #     os.system(gdalruntextdsm_build)

            # Remove gdalwarp with gdal.Translate
            bigraster = gdal.Open(filePath_dsm_build)
            bbox = (x - r, y + r, x + r, y - r)
            gdal.Translate(self.plugin_dir + '/data/clipdsm.tif', bigraster, projWin=bbox)
            bigraster = None

            dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
            dsm = dataset.ReadAsArray().astype(np.float)
            sizex = dsm.shape[0]
            sizey = dsm.shape[1]
            dem = np.zeros((sizex, sizey))

        else:  # Both building ground heights
            dsm = self.layerComboManagerDSMbuildground.currentLayer()
            dem = self.layerComboManagerDEM.currentLayer()

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

            # gdalruntextdsm = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
            #                                    ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
            #                                    filePath_dsm + '" "' + self.plugin_dir + '/data/clipdsm.tif"'
            # gdalruntextdem = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
            #                        ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
            #                        filePath_dem + '" "' + self.plugin_dir + '/data/clipdem.tif"'
            #
            # if sys.platform == 'win32':
            #     si = subprocess.STARTUPINFO()
            #     si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            #     subprocess.call(gdalruntextdsm, startupinfo=si)
            #     subprocess.call(gdalruntextdem, startupinfo=si)
            # else:
            #     os.system(gdalruntextdsm)
            #     os.system(gdalruntextdem)

            # Testing with gdal.Translate
            bigraster = gdal.Open(filePath_dsm)
            bbox = (x - r, y + r, x + r, y - r)
            gdal.Translate(self.plugin_dir + '/data/clipdsm.tif', bigraster, projWin=bbox)
            bigraster = gdal.Open(filePath_dem)
            bbox = (x - r, y + r, x + r, y - r)
            gdal.Translate(self.plugin_dir + '/data/clipdem.tif', bigraster, projWin=bbox)

            dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
            dsm = dataset.ReadAsArray().astype(np.float)
            dataset2 = gdal.Open(self.plugin_dir + '/data/clipdem.tif')
            dem = dataset2.ReadAsArray().astype(np.float)

            if not (dsm.shape[0] == dem.shape[0]) & (dsm.shape[1] == dem.shape[1]):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

        geotransform = dataset.GetGeoTransform()
        scale = 1 / geotransform[1]
        self.degree = float(self.dlg.degreeBox.currentText())
        nd = dataset.GetRasterBand(1).GetNoDataValue()
        nodata_test = (dsm == nd)
        if nodata_test.any():
            QMessageBox.critical(None, "Error", "Clipped grid includes nodata pixels")
            return
        else:
            immorphresult = imagemorphparam_v2(dsm, dem, scale, 1, self.degree, self.dlg, 1)

        # #Calculate Z0m and Zdm depending on the Z0 method
        ro = self.dlg.comboBox_Roughness.currentIndex()
        if ro == 0:
            Roughnessmethod = 'RT'
        elif ro == 1:
            Roughnessmethod = 'Rau'
        elif ro == 2:
            Roughnessmethod = 'Bot'
        elif ro == 3:
            Roughnessmethod = 'Mac'
        elif ro == 4:
            Roughnessmethod = 'Mho'
        else:
            Roughnessmethod = 'Kan'

        zH = immorphresult["zH"]
        fai = immorphresult["fai"]
        pai = immorphresult["pai"]
        zMax = immorphresult["zHmax"]
        zSdev = immorphresult["zH_sd"]

        zd,z0 = rg.RoughnessCalcMany(Roughnessmethod, zH, fai, pai, zMax, zSdev)

        # save to file
        pre = self.dlg.textOutput_prefix.text()
        header = 'Wd pai fai zH zHmax zHstd zd z0'
        numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
        arr = np.concatenate((immorphresult["deg"], immorphresult["pai"], immorphresult["fai"],
                            immorphresult["zH"], immorphresult["zHmax"], immorphresult["zH_sd"],zd,z0), axis=1)
        np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'IMPPoint_anisotropic.txt', arr,
                   fmt=numformat, delimiter=' ', header=header, comments='')

        zHall = immorphresult["zH_all"]
        faiall = immorphresult["fai_all"]
        paiall = immorphresult["pai_all"]
        zMaxall = immorphresult["zHmax_all"]
        zSdevall = immorphresult["zH_sd_all"]
        zdall,z0all = rg.RoughnessCalc(Roughnessmethod, zHall, faiall, paiall, zMaxall, zSdevall)
        
        # If zd and z0 are lower than open country, set to open country
        if zdall < 0.2:
            zdall = 0.2
        if z0all < 0.03:
            z0all = 0.03

        # If pai is larger than 0 and fai is zero, set fai to 0.001. Issue # 164
        if paiall > 0.:
            if faiall == 0.:
                faiall = 0.001

        # adding wai area to isotrophic (wall area index)
        wallarea = np.sum(wa.findwalls(dsm, 2.))
        gridArea = (abs(bbox[2]-bbox[0]))*(abs(bbox[1]-bbox[3]))
        wai = wallarea / gridArea

        header = 'pai fai zH zHmax zHstd zd z0 wai'
        numformat = '%4.3f %4.3f %5.3f %5.3f %5.3f %5.3f %5.3f %4.3f'
        arr2 = np.array([[paiall, faiall, zHall, zMaxall, zSdevall, zdall, z0all, wai]])
        np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'IMPPoint_isotropic.txt', arr2,
                   fmt=numformat, delimiter=' ', header=header, comments='')

        dataset = None
        dataset2 = None
        dataset3 = None

        #self.iface.messageBar().clearWidgets()
        QMessageBox.information(None, "Image Morphometric Parameters", "Process successful!")

    def run(self):
        try:
            import scipy
        except Exception as e:
            QMessageBox.critical(None, 'Error', 'This plugin requires the scipy package '
                                                'to be installed. Please consult the FAQ in the manual for further '
                                                'information on how to install missing python packages.')
            return

        self.dlg.show()
        self.dlg.exec_()
        gdal.UseExceptions()
        gdal.AllRegister()

    def help(self):
        url = "https://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Morphology%20Morphometric%20Calculator%20(Point).html"
        webbrowser.open_new_tab(url)