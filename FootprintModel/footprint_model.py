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
from footprint_model_dialog import FootprintModelDialog
import os.path
import numpy as np
import KingsFootprint_UMEP as fp
from osgeo import gdal
import subprocess
import sys
import webbrowser


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
        self.dlg.comboBoxFPM.currentIndexChanged.connect(self.bl_enable)

        self.fileDialogOpen = QFileDialog()
        self.filePath = None
        self.data = None
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        # self.layerComboManagerPoint = VectorLayerCombo(self.dlg.comboBox_Point)
        # fieldgen = VectorLayerCombo(self.dlg.comboBox_Point, initLayer="", options={"geomType": QGis.Point})
        self.layerComboManagerPoint = QgsMapLayerComboBox(self.dlg.widgetPointLayer)
        self.layerComboManagerPoint.setCurrentIndex(-1)
        self.layerComboManagerPoint.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.layerComboManagerPoint.setFixedWidth(175)
        # self.layerComboManagerPointField = FieldCombo(self.dlg.comboBox_Field, fieldgen, initField="")
        # self.layerComboManagerDSMbuildground = RasterLayerCombo(self.dlg.comboBox_DSMbuildground)
        # RasterLayerCombo(self.dlg.comboBox_DSMbuildground, initLayer="")
        # self.layerComboManagerDEM = RasterLayerCombo(self.dlg.comboBox_DEM)
        # RasterLayerCombo(self.dlg.comboBox_DEM, initLayer="")
        # self.layerComboManagerDSMbuild = RasterLayerCombo(self.dlg.comboBox_DSMbuild)
        # RasterLayerCombo(self.dlg.comboBox_DSMbuild, initLayer="")
        # self.layerComboManagerVEGDSM = RasterLayerCombo(self.dlg.comboBox_vegdsm)
        # RasterLayerCombo(self.dlg.comboBox_vegdsm, initLayer="")

        self.layerComboManagerDSMbuildground  = QgsMapLayerComboBox(self.dlg.widgetDSMbuildground )
        self.layerComboManagerDSMbuildground .setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSMbuildground .setFixedWidth(175)
        self.layerComboManagerDSMbuildground .setCurrentIndex(-1)
        self.layerComboManagerDEM = QgsMapLayerComboBox(self.dlg.widgetDEM)
        self.layerComboManagerDEM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDEM.setFixedWidth(175)
        self.layerComboManagerDEM.setCurrentIndex(-1)
        self.layerComboManagerDSMbuild = QgsMapLayerComboBox(self.dlg.widgetDSMbuild)
        self.layerComboManagerDSMbuild.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSMbuild.setFixedWidth(175)
        self.layerComboManagerDSMbuild.setCurrentIndex(-1)
        self.layerComboManagerVEGDSM = QgsMapLayerComboBox(self.dlg.widgetVegDSM)
        self.layerComboManagerVEGDSM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerVEGDSM.setFixedWidth(175)
        self.layerComboManagerVEGDSM.setCurrentIndex(-1)

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

            if not self.data.shape[1] == 13:
                QMessageBox.critical(None, "Import Error", "Check number of columns in textfile."
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

    def bl_enable(self):
        if self.dlg.comboBoxFPM.currentIndex() == 1:
            self.dlg.doubleSpinBox_bl.setEnabled(True)
            self.dlg.label_19.setEnabled(True)
        else:
            self.dlg.doubleSpinBox_bl.setEnabled(False)
            self.dlg.label_19.setEnabled(False)

    def start_process(self):

        # # Check OS and dep
        # if sys.platform == 'darwin':
        #     gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        # else:
        #     gdalwarp_os_dep = 'gdalwarp'

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
            sigv = self.data[:, 7]
            Obukhov = self.data[:, 8]
            ustar = self.data[:, 9]
            wdir = self.data[:, 10]
            pbl = self.data[:,11]
            por = self.data[:,12]
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
            sigv = np.ones((1, 1)) * self.dlg.doubleSpinBox_wssd.value()
            Obukhov = np.ones((1, 1)) * self.dlg.doubleSpinBox_L.value()
            ustar = np.ones((1, 1)) * self.dlg.doubleSpinBox_ustar.value()
            wdir = np.ones((1, 1)) * self.dlg.doubleSpinBox_wd.value()
            pbl = np.ones((1, 1)) * self.dlg.doubleSpinBox_bl.value()
            #por = np.ones((1, 1)) * 100.
            por = np.ones((1, 1)) * self.dlg.spinBoxPorosity.value()

        #QMessageBox.critical(None, "Error", str(por))

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

        # if sys.platform == 'win32':
        #     si = subprocess.STARTUPINFO()
        #     si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # else:
        #     si = None

        if self.dlg.checkBoxVectorLayer.isChecked():
            point = self.layerComboManagerPoint.currentLayer()
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
            dsm_build = self.layerComboManagerDSMbuild.currentLayer()
            if dsm_build is None:
                QMessageBox.critical(None, "Error", "No valid building DSM raster layer is selected")
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

            # Remove gdalwarp with gdal.Translate
            bigraster_dsm = gdal.Open(filePath_dsm)
            bigraster_dem = gdal.Open(filePath_dem)
            bbox = (x - r, y + r, x + r, y - r)
            gdal.Translate(self.plugin_dir + '/data/clipdsm.tif', bigraster_dsm, projWin=bbox)
            gdal.Translate(self.plugin_dir + '/data/clipdem.tif', bigraster_dem, projWin=bbox)

            # gdalruntextdsm = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
            #                                    ' ' + str(x + r ) + ' ' + str(y + r) + ' -of GTiff "' + \
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

            dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
            dsm = dataset.ReadAsArray().astype(np.float)
            dataset2 = gdal.Open(self.plugin_dir + '/data/clipdem.tif')
            dem = dataset2.ReadAsArray().astype(np.float)

            sizex = dsm.shape[0]
            sizey = dsm.shape[1]

            dsm = dsm - dem     #remove ground height

            if not (dsm.shape[0] == dem.shape[0]) & (dsm.shape[1] == dem.shape[1]):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

        vegdsm = np.zeros((sizex, sizey))           #initiate zeroed vegdsm the same size of building

        if self.dlg.checkBoxUseVeg.isChecked():

            usevegdem = 1
            if self.dlg.checkBoxUseFile.isChecked():
                vegdsm = self.layerComboManagerVEGDSM.currentLayer()
            else:
                vegdsm = self.layerComboManagerVEGDSM.currentLayer()
                por = np.ones((1, 1)) * self.dlg.spinBoxPorosity.value()

            if vegdsm is None:
                QMessageBox.critical(None, "Error", "No valid vegetation DSM selected")
                return

            # # load raster
            provider = vegdsm.dataProvider()
            filePath_vegdsm = str(provider.dataSourceUri())
            # gdalruntextvegdsm = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -te ' + str(x - r) + ' ' + str(y - r) + \
            #                        ' ' + str(x + r) + ' ' + str(y + r) + ' -of GTiff "' + \
            #                        filePath_vegdsm + '" "' + self.plugin_dir + '/data/clipvegdsm.tif"'
            #
            # if sys.platform == 'win32':
            #     subprocess.call(gdalruntextvegdsm, startupinfo=si)
            # else:
            #     os.system(gdalruntextvegdsm)

            # Remove gdalwarp with gdal.Translate
            bigraster_vegdsm = gdal.Open(filePath_vegdsm)
            bbox = (x - r, y + r, x + r, y - r)
            gdal.Translate(self.plugin_dir + '/data/clipvegdsm.tif', bigraster_vegdsm, projWin=bbox)

            dataset = gdal.Open(self.plugin_dir + '/data/clipvegdsm.tif')
            vegdsm = dataset.ReadAsArray().astype(np.float)
            vegsizex = vegdsm.shape[0]
            vegsizey = vegdsm.shape[1]

            if not (vegsizex == sizex) & (vegsizey == sizey):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return
        else:
            vegdsm = np.zeros((sizex, sizey))           #initiate zeroed vegdsm the same size of building
            if por == 'None':
                por = np.ones((1, 1)) * 100.

            vegsizex = vegdsm.shape[0]
            vegsizey = vegdsm.shape[1]

        por = por/100.          # convert to 0 - 1 scale

        geotransform = dataset.GetGeoTransform()
        # scale = 1 / geotransform[1]
        res = geotransform[1]

        nodata_test = (dsm == -9999)
        if nodata_test.any():
            QMessageBox.critical(None,"Error", "Grids includes nodata pixels. Is your point closer than " +
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

            ro2 = self.dlg.comboBoxFPM.currentIndex()
            if ro2 == 0:
                fpm = 'KAM'
            elif ro2 == 1:
                fpm = 'KLJ'

            #Run FPR model
            if fpm == "KAM":
                totRotatedphi,Wz_d_output,Wz_0_output,Wz_m_output,phi_maxdist,phi_totdist,Wfai,Wpai,WzH,WzMax,WzSdev,Wfaiveg,\
                        Wpaiveg,WzHveg,WzMaxveg,WzSdevveg,Wfaibuild,Wpaibuild,WzHbuild,WzMaxbuild,WzSdevbuild = \
                        fp.footprintiterKAM(iterations=it,z_0_input=z_0_input,z_d_input=z_d_input,z_ag=z_m_input,sigv=sigv,
                        Obukhov=Obukhov,ustar=ustar,dir=wdir,porosity=por,bld=dsm,veg=vegdsm,rows=sizey,cols=sizex,res=res,dlg=self.dlg,
                        maxfetch=r,rm=Rm)
            elif fpm == "KLJ":
                totRotatedphi,Wz_d_output,Wz_0_output,Wz_m_output,phi_maxdist,phi_totdist,Wfai,Wpai,WzH,WzMax,WzSdev,Wfaiveg,\
                        Wpaiveg,WzHveg,WzMaxveg,WzSdevveg,Wfaibuild,Wpaibuild,WzHbuild,WzMaxbuild,WzSdevbuild = \
                        fp.footprintiterKLJ(iterations=it,z_0_input=z_0_input,z_d_input=z_d_input,z_ag=z_m_input,sigv=sigv,
                        Obukhov=Obukhov,ustar=ustar,dir=wdir,porosity=por,h=pbl,bld=dsm,veg=vegdsm,rows=sizey,cols=sizex,res=res,
                        dlg=self.dlg,maxfetch=r,rm=Rm)

            #If zd and z0 are lower than open country, set to open country
            for i in np.arange(0,it,1):
                if Wz_d_output[i]< 0.03:
                    Wz_d_output[i] = 0.03
                if Wz_0_output[i]< 0.03:
                    Wz_0_output[i] = 0.03

            # save to file
            header = 'iy id it imin z_0_input z_d_input z_m_input sigv Obukhov ustar dir h por fai pai zH zMax zSdev zd z0'
            numfmt = '%3d %2d %3d %2d %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f'
            mat = np.column_stack((yyyy[0:it], doy[0:it], ih[0:it], imin[0:it], z_0_input[0:it], z_d_input[0:it],
                                   z_m_input[0:it], sigv[0:it], Obukhov[0:it], ustar[0:it], wdir[0:it],pbl[0:it],por[0:it],
                                   Wfai, Wpai, WzH, WzMax, WzSdev,Wz_d_output,Wz_0_output))
            pre = self.dlg.textOutput_prefix.text()
            np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'SourceMorphParameters.txt', mat, fmt=('%5.5f'), comments='', header=header)

            # QMessageBox.critical(None, "Test", str(mat))
            #Presentation of Source area
            #rotatedphiPerc = totRotatedphi/np.nansum(totRotatedphi)
            rotatedphiPerc = (totRotatedphi/np.nanmax(totRotatedphi))*100
            rotatedphiPerc = (rotatedphiPerc - 100)*-1
            #rotatedphiPerc[rotatedphiPerc == 0] = -9999
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
        url = "http://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Land%20Cover%20Land%20Cover%20" \
              "Fraction%20(Point).html"
        webbrowser.open_new_tab(url)