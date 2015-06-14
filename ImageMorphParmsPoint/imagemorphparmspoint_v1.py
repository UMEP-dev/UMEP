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
from PyQt4.QtCore import *  # QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QProgressBar, QFileDialog
from qgis.gui import *
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint, QgsVectorFileWriter
import os
from ..Utilities.qgiscombomanager import *
from osgeo import gdal
import subprocess
import webbrowser
from ..Utilities.imageMorphometricParms_v1 import *
# from ..pydev import pydevd
# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from imagemorphparmspoint_v1_dialog import ImageMorphParmsPointDialog


class ImageMorphParmsPoint:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
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
        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.progressBar.setValue(0)
        self.dlg.checkBoxOnlyBuilding.toggled.connect(self.text_enable)
        #self.dlg.selectpoint.QWhatsThisClickedEvent.connect(self.whatsthisclicked)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        for i in range(1, 25):
            if 360 % i == 0:
                self.dlg.degreeBox.addItem(str(i))
        self.dlg.degreeBox.setCurrentIndex(4)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Image Morphometric Parameters Point')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ImageMorphParmsPoint')
        self.toolbar.setObjectName(u'ImageMorphParmsPoint')

        # g reference to the canvas
        self.canvas = self.iface.mapCanvas()
        self.poiLayer = None
        self.polyLayer = None
        self.folderPath = 'None'
        self.degree = 5.0

        #g pin tool
        self.pointTool = QgsMapToolEmitPoint(self.canvas)
        self.toolPan = QgsMapToolPan(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)

        self.layerComboManagerDSMbuildground = RasterLayerCombo(self.dlg.comboBox_DSMbuildground)
        RasterLayerCombo(self.dlg.comboBox_DSMbuildground, initLayer="")
        self.layerComboManagerDEM = RasterLayerCombo(self.dlg.comboBox_DEM)
        RasterLayerCombo(self.dlg.comboBox_DEM, initLayer="")
        self.layerComboManagerDSMbuild = RasterLayerCombo(self.dlg.comboBox_DSMbuild)
        RasterLayerCombo(self.dlg.comboBox_DSMbuild, initLayer="")

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

        icon_path = ':/plugins/ImageMorphParmsPoint/ImageMorphIconPoint.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Image Morphometric Parameters Point'),
            callback=self.run,
            parent=self.iface.mainWindow())
        #QObject.connect(self.dlg.selectpoint, SIGNAL("clicked()"), self.select_point)
        #QObject.connect(self.dlg.button_box, SIGNAL("accepted()"), self.calc_image)

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

    def create_point_layer(self):
        canvas = self.iface.mapCanvas()
        mapRenderer = canvas.mapRenderer()
        srs = mapRenderer.destinationCrs()
        crs = str(srs.authid())
        # self.iface.messageBar().pushMessage("Coordinate selected", test)
        uri = "Point?field=id:integer&field=x:double&field=y:double&index=yes&crs=" + crs
        self.poiLayer = QgsVectorLayer(uri, "Point of Interest", "memory")
        self.provider = self.poiLayer.dataProvider()


    def select_point(self):
        #pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)
        if self.poiLayer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(self.poiLayer.id())
        if self.polyLayer is not None:
            self.polyLayer.startEditing()
            self.polyLayer.selectAll()
            self.polyLayer.deleteSelectedFeatures()
            self.polyLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.polyLayer.id())

        #self.canvas = self.iface.mapCanvas()
        self.canvas.setMapTool(self.pointTool)
        #self.dlg.hide()
        #self.dlg.setVisible(False)
        self.dlg.setEnabled(False)
        self.create_point_layer()
        #self.pointTool.canvasClicked.connect(self.create_point)
        #self.dlg.show()

    def create_point(self, point):
        # report map coordinates from a canvas click
        # self.dlg.hide()
        coords = "{}, {}".format(point.x(), point.y())
        self.iface.messageBar().pushMessage("Coordinate selected", str(coords))
        #self.point = point
        #self.dlg.button_box.setEnabled(1)
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
        self.poiLayer.setCacheImage(None)
        self.poiLayer.triggerRepaint()
        self.create_poly_layer(point)
        self.canvas.setMapTool(self.toolPan)
        self.dlg.setEnabled(True)
        #self.dlg.show()
        #self.dlg.setVisible(True)
        #self.dlg.showNormal()


    def create_poly_layer(self, point):

        canvas = self.iface.mapCanvas()
        mapRenderer = canvas.mapRenderer()
        srs = mapRenderer.destinationCrs()
        crs = str(srs.authid())
        uri = "Polygon?field=id:integer&index=yes&crs=" + crs
        dir_poly = self.plugin_dir + '/data/poly_temp.shp'
        #self.polyLayer = QgsVectorLayer(dir_poly, "Study area", "ogr")
        self.polyLayer = QgsVectorLayer(uri, "Study area", "memory")
        self.provider = self.polyLayer.dataProvider()
        #QgsMapLayerRegistry.instance().addMapLayer(self.polyLayer)

        # create buffer feature
        fc = int(self.provider.featureCount())
        featurepoly = QgsFeature()

        # Assign feature the buffered geometry
        radius = self.dlg.spinBox.value()
        #radius = 200
        featurepoly.setGeometry(QgsGeometry.fromPoint(
            #QgsPoint(self.point.x(), self.point.y())).buffer(radius, 1000, 1, 1, 1.0))
            QgsPoint(point.x(), point.y())).buffer(radius, 1000, 1, 1, 1.0))
        featurepoly.setAttributes([fc])
        self.polyLayer.startEditing()
        self.polyLayer.addFeature(featurepoly, True)
        self.polyLayer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(self.polyLayer)

        # props = {'color_border': '255,165,0,125', 'style': 'no', 'style_border': 'solid'}
        # s = QgsFillSymbolV2.createSimple(props)
        # self.polyLayer.setRendererV2(QgsSingleSymbolRendererV2(s))

        self.polyLayer.setLayerTransparency(42)
        self.polyLayer.setCacheImage(None)
        self.polyLayer.triggerRepaint()
        #QObject.connect(self.dlg.selectpoint, SIGNAL("clicked()"), self.select_point)

    def help(self):
        url = "file://" + self.plugin_dir + "/README.html"
        #url = "http://www.google.com"
        webbrowser.open_new_tab(url)

    #def whatsthisclicked(self, href):
        #webbrowser.open_new_tab(href)

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
        # pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)
        self.dlg.progressBar.setValue(0)

        poly = self.iface.activeLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return

        # poly_field = self.layerComboManagerPolyField.getFieldName()
        # if poly_field is None:
        #     QMessageBox.critical(None, "Error", "An attribute filed with unique fields must be selected")
        #     return

        #vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        #vlayer = self.polyLayer
        prov = poly.dataProvider()
        fields = prov.fields()
        #idx = poly.fieldNameIndex(poly_field)
        #QMessageBox.warning(None, "Error", str(fields))

        #progress.setMaximum(vlayer.featureCount())
        #progressMessageBar.layout().addWidget(progress)
        #self.iface.messageBar().pushWidget(progressMessageBar, self.iface.messageBar().INFO)

        dir_poly = self.plugin_dir + '/data/poly_temp.shp'

        #savename = self.plugin_dir + '/data/' + str(j) + ".shp"
        writer = QgsVectorFileWriter(dir_poly, "CP1250", fields, prov.geometryType(),
                                     prov.crs(), "ESRI shapefile")

        if writer.hasError() != QgsVectorFileWriter.NoError:
            self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))

        poly.selectAll()
        selection = poly.selectedFeatures()

        for feature in selection:
            writer.addFeature(feature)
        del writer

        if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
            dsm_build = self.layerComboManagerDSMbuild.getLayer()
            if dsm_build is None:
                QMessageBox.critical(None, "Error", "No valid building DSM raster layer is selected")
                return

            provider = dsm_build.dataProvider()
            filePath_dsm_build = str(provider.dataSourceUri())
            #Kolla om memorylayer går att användas istället för dir_poly tempfilen.
            gdalruntextdsm_build = 'gdalwarp -dstnodata -9999 -q -cutline ' + dir_poly + \
                                   ' -crop_to_cutline -of GTiff ' + filePath_dsm_build + \
                                   ' ' + self.plugin_dir + '/data/clipdsm.tif'
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
            gdalruntextdsm = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + dir_poly + \
                             ' -crop_to_cutline -of GTiff ' + filePath_dsm + \
                             ' ' + self.plugin_dir + '/data/clipdsm.tif'
            gdalruntextdem = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + dir_poly + \
                             ' -crop_to_cutline -of GTiff ' + filePath_dem + \
                             ' ' + self.plugin_dir + '/data/clipdem.tif'
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.call(gdalruntextdsm, startupinfo=si)
            subprocess.call(gdalruntextdem, startupinfo=si)

            dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
            dsm = dataset.ReadAsArray().astype(np.float)
            dataset2 = gdal.Open(self.plugin_dir + '/data/clipdem.tif')
            dem = dataset2.ReadAsArray().astype(np.float)

            if not (dsm.shape[0] == dem.shape[0]) & (dsm.shape[1] == dem.shape[1]):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

        geotransform = dataset.GetGeoTransform()
        scale = 1 / geotransform[1]
        # self.iface.messageBar().pushMessage("innan loop")

        self.degree = float(self.dlg.degreeBox.currentText())
        immorphresult = imagemorphparam_v1(dsm, dem, scale, 1, self.degree, self.dlg, 1)

        # save to file
        header = ' Wd pai   fai   zH  zHmax   zHstd'
        numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f'
        arr = np.concatenate((immorphresult["deg"], immorphresult["pai"], immorphresult["fai"],
                              immorphresult["zH"], immorphresult["zHmax"], immorphresult["zH_sd"]), axis=1)
        np.savetxt(self.folderPath[0] + '/anisotropic_result.txt', arr,
                   fmt=numformat, delimiter=' ', header=header, comments='')

        header = ' pai   zH    zHmax    zHstd'
        numformat = '%4.3f %5.3f %5.3f %5.3f'
        arr2 = np.array([[immorphresult["pai_all"], immorphresult["zH_all"], immorphresult["zHmax_all"],
                          immorphresult["zH_sd_all"]]])
        np.savetxt(self.folderPath[0] + '/isotropic_result.txt', arr2,
                   fmt=numformat, delimiter=' ', header=header, comments='')

        dataset = None
        dataset2 = None
        dataset3 = None

        #self.iface.messageBar().clearWidgets()
        QMessageBox.information(None, "Image Morphometric Parameters", "Process successful!")

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        self.dlg.exec_()

        gdal.UseExceptions()
        gdal.AllRegister()