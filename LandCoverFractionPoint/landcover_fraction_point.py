# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandCoverFractionPoint
                                 A QGIS plugin
 Calculates land cover fraction from a buffered point
                              -------------------
        begin                : 2015-07-13
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.gui import *
from qgis.core import *
import os
from ..Utilities.landCoverFractions_v1 import *
from osgeo import gdal
import subprocess
import sys
import webbrowser
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from landcover_fraction_point_dialog import LandCoverFractionPointDialog


class LandCoverFractionPoint:
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
            'LandCoverFractionPoint_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LandCoverFractionPointDialog()
        self.dlg.runButton.clicked.connect(self.start_process)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.selectpoint.clicked.connect(self.select_point)
        self.dlg.generateArea.clicked.connect(self.generate_area)
        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.progressBar.setValue(0)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        for i in range(1, 25):
            if 360 % i == 0:
                self.dlg.degreeBox.addItem(str(i))
        self.dlg.degreeBox.setCurrentIndex(4)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Land Cover Fraction Point')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'LandCoverFractionPoint')
        # self.toolbar.setObjectName(u'LandCoverFractionPoint')

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
        #self.toolPan = QgsMapToolPan(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)

        # self.layerComboManagerPoint = VectorLayerCombo(self.dlg.comboBox_Point)
        # fieldgen = VectorLayerCombo(self.dlg.comboBox_Point, initLayer="", options={"geomType": QGis.Point})
        self.layerComboManagerPoint = QgsMapLayerComboBox(self.dlg.widgetPointLayer)
        self.layerComboManagerPoint.setCurrentIndex(-1)
        self.layerComboManagerPoint.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.layerComboManagerPoint.setFixedWidth(175)

        # self.layerComboManagerLCgrid = RasterLayerCombo(self.dlg.comboBox_lcgrid)
        # RasterLayerCombo(self.dlg.comboBox_lcgrid, initLayer="")
        self.layerComboManagerLCgrid = QgsMapLayerComboBox(self.dlg.widget_lcgrid)
        self.layerComboManagerLCgrid.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerLCgrid.setFixedWidth(175)
        self.layerComboManagerLCgrid.setCurrentIndex(-1)

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
        return QCoreApplication.translate('LandCoverFractionPoint', message)


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

        icon_path = ':/plugins/LandCoverFractionPoint/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Calculates land cover fraction from a buffered point'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Land Cover Fraction Point'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

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
        # self.create_poly_layer(point) # Flyttad till generate_area
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
            QgsMapLayerRegistry.instance().removeMapLayer(self.poiLayer.id())
        if self.polyLayer is not None:
            self.polyLayer.startEditing()
            self.polyLayer.selectAll()
            self.polyLayer.deleteSelectedFeatures()
            self.polyLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.polyLayer.id())

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
        featurepoly.setGeometry(QgsGeometry.fromPoint(
            QgsPoint(self.pointx, self.pointy)).buffer(radius, 1000, 1, 1, 1.0))
        featurepoly.setAttributes([fc])
        self.polyLayer.startEditing()
        self.polyLayer.addFeature(featurepoly, True)
        self.polyLayer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(self.polyLayer)

        # props = {'color_border': '255,165,0,125', 'style': 'no', 'style_border': 'solid'}
        # s = QgsFillSymbolV2.createSimple(props)
        # self.polyLayer.setRendererV2(QgsSingleSymbolRendererV2(s))

        self.polyLayer.setLayerTransparency(42)
        # self.polyLayer.repaintRequested(None)
        # self.polyLayer.setCacheImage(None)
        self.polyLayer.triggerRepaint()
        #QObject.connect(self.dlg.selectpoint, SIGNAL("clicked()"), self.select_point)

    # def help(self):
    #     url = "file://" + self.plugin_dir + "/README.html"
    #     webbrowser.open_new_tab(url)

    def start_process(self):
        # pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)

        # #Check OS and dep
        # if sys.platform == 'darwin':
        #     gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        # else:
        #     gdalwarp_os_dep = 'gdalwarp'

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

        writer = QgsVectorFileWriter(dir_poly, "CP1250", fields, prov.geometryType(),
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

        dsm_build = self.layerComboManagerLCgrid.currentLayer()
        if dsm_build is None:
            QMessageBox.critical(None, "Error", "No valid land cover raster layer is selected")
            return

        provider = dsm_build.dataProvider()
        filePath_dsm_build = str(provider.dataSourceUri())
        # gdalruntextdsm_build = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
        #                        ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
        #                        filePath_dsm_build + '" "' + self.plugin_dir + '/data/clipdsm.tif"'
        #
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

        self.degree = float(self.dlg.degreeBox.currentText())
        nd = dataset.GetRasterBand(1).GetNoDataValue()
        nodata_test = (dsm == nd)
        if nodata_test.any():
            QMessageBox.critical(None, "Error", "Clipped grid includes nodata pixels")
            return
        else:
            landcoverresult = landcover_v1(dsm, 1, self.degree, self.dlg, 1)

        landcoverresult = self.resultcheck(landcoverresult)

        # save to file
        pre = self.dlg.textOutput_prefix.text()
        header = 'Wd Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
        numformat = '%3d %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
        arr = np.concatenate((landcoverresult["deg"], landcoverresult["lc_frac"]), axis=1)
        np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'LCFPoint_anisotropic.txt', arr,
                   fmt=numformat, delimiter=' ', header=header, comments='')

        header = 'Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
        numformat = '%5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
        arr2 = np.array(landcoverresult["lc_frac_all"])
        np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'LCFPoint_isotropic.txt', arr2,
                    fmt=numformat, delimiter=' ', header=header, comments='')

        dataset = None
        dataset2 = None
        dataset3 = None

        QMessageBox.information(None, "Land Cover Fraction Point: ", "Process successful!")

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

    def run(self):
        """Run method that performs all the real work"""
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = 'http://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Land%20Cover%20Land%20Cover%20' \
              'Fraction%20(Point).html'
        webbrowser.open_new_tab(url)

