# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageMorphParam
                                 A QGIS plugin
 This plugin calculates morphometric parameters based on high resolution urban DSMs
                              -------------------
        begin                : 2015-01-06
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg, GU
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
from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QProgressBar, QFileDialog
from qgis.core import QgsVectorLayer, QgsVectorFileWriter, QgsFeature
#import os.path
import os
from qgiscombomanager import *
from osgeo import gdal  #, ogr
#import numpy as np
import subprocess
from imageMorphometricParms_v1 import *
#import matplotlib.pylab as plt
import time
#import scipy as sc
import sys
#sys.path.append('C:/Program Files (x86)/JetBrains/PyCharm 3.4.1/helpers/pydev')
#from pydev import pydevd

# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from image_morph_param_dialog import ImageMorphParamDialog


class ImageMorphParam:
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
            'ImageMorphParam_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ImageMorphParamDialog()

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.progressBar.setValue(0)

        for i in range(1, 25):
            if 360 % i == 0:
                self.dlg.degreeBox.addItem(str(i))
        self.dlg.degreeBox.setCurrentIndex(4)

        self.folderPath = 'None'
        self.degree = 5.0

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Image Morphometric Parameters')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ImageMorphParam')
        self.toolbar.setObjectName(u'ImageMorphParam')

        #self.layerComboManagerPolygrid = VectorLayerCombo(self.dlg.comboBox_Polygrid, options={"geomType":Polygon})
        self.layerComboManagerPolygrid = VectorLayerCombo(self.dlg.comboBox_Polygrid)
        fieldgen = VectorLayerCombo(self.dlg.comboBox_Polygrid, initLayer="")
        self.layerComboManagerPolyField = FieldCombo(self.dlg.comboBox_Field, fieldgen, initField="")
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
        return QCoreApplication.translate('ImageMorphParam', message)

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

        icon_path = ':/plugins/ImageMorphParam/ImageMorphIcon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Image Morphometric Parameters'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Image Morphometric Parameters'),
                action)
            self.iface.removeToolBarIcon(action)

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def start_progress(self):

        poly = self.layerComboManagerPolygrid.getLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return

        poly_field = self.layerComboManagerPolyField.getFieldName()
        if poly_field is None:
            QMessageBox.critical(None, "Error", "An attribute filed with unique fields must be selected")
            return

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        idx = vlayer.fieldNameIndex(poly_field)

        self.dlg.progressBar.setMaximum(vlayer.featureCount())

        dir_poly = self.plugin_dir + '/data/poly_temp.shp'
        j = 0
        for f in vlayer.getFeatures():  # looping through each grip polygon
            self.dlg.progressBar.setValue(j + 1)

            #savename = self.plugin_dir + '/data/' + str(j) + ".shp"
            writer = QgsVectorFileWriter(dir_poly, "CP1250", fields, prov.geometryType(),
                                         prov.crs(), "ESRI shapefile")

            if writer.hasError() != QgsVectorFileWriter.NoError:
                self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))

            attributes = f.attributes()
            # self.iface.messageBar().pushMessage("Test", str(f.attributes()[idx]))
            geometry = f.geometry()
            feature = QgsFeature()
            feature.setAttributes(attributes)
            feature.setGeometry(geometry)
            writer.addFeature(feature)
            del writer

            if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
                dsm_build = self.layerComboManagerDSMbuild.getLayer()
                if dsm_build is None:
                    QMessageBox.critical(None, "Error", "No valid building DSM raster layer is selected")
                    return

                provider = dsm_build.dataProvider()
                filePath_dsm_build = str(provider.dataSourceUri())
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

            geotransform = dataset.GetGeoTransform()
            scale = 1 / geotransform[1]

            nodata_test = (dem == -9999)
            if nodata_test.any() == True:
                self.iface.messageBar().pushMessage("Image Morphometric Parameters", str(j))
            else:
                self.degree = float(self.dlg.degreeBox.currentText())
                immorphresult = imagemorphparam_v1(dsm, dem, scale, 0, self.degree)

                # save to file
                header = ' Wd pai   fai   zH  zHmax   zHstd'
                numformat = '%3d %4.3f %4.3f %5.3f %5.3f %5.3f'
                arr = np.concatenate((immorphresult["deg"], immorphresult["pai"], immorphresult["fai"],
                                      immorphresult["zH"], immorphresult["zHmax"], immorphresult["zH_sd"]), axis=1)
                np.savetxt(self.folderPath[0] + '/anisotropic_result_' + str(f.attributes()[idx]) + '.txt', arr,
                           fmt=numformat, delimiter=' ', header=header, comments='')

                header = ' pai   zH zHmax zHstd'
                numformat = '%4.3f %4.3f %5.3f'
                arr = np.concatenate((immorphresult["pai_all"], immorphresult["zH_all"], immorphresult["zHmax_all"],
                                      immorphresult["zH_sd_all"]), axis=1)
                np.savetxt(self.folderPath[0] + '/isotropic_result_' + str(f.attributes()[idx]) + '.txt', arr,
                           fmt=numformat, delimiter=' ', header=header, comments='')
                # np.savetxt(self.plugin_dir + '/data/result_' + str(f.attributes()[idx]) + '.txt', arr,
                #            fmt=numformat, delimiter=' ', header=header, comments='')

            dataset = None
            dataset2 = None
            dataset3 = None

            j += 1
            time.sleep(0.25)

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage("Image Morphometric Parameters", "Process successful!")

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        gdal.UseExceptions()
        gdal.AllRegister()
        #
        # if result:  # See if OK was pressed
        #
        #     # initiate progressbar
        #     progressMessageBar = self.iface.messageBar().createMessage("Processing...")
        #     progress = QProgressBar()
        #
        #     poly = self.layerComboManagerPolygrid.getLayer()
        #     if poly is None:
        #         QMessageBox.critical(None, "Error", "No valid Polygon layer is selected1")
        #         return
        #     if not poly.geometryType() == 2:
        #         QMessageBox.critical(None, "Error", "No valid Polygon layer is selected2")
        #         return
        #
        #     poly_field = self.layerComboManagerPolyField.getFieldName()
        #     if poly_field is None:
        #         QMessageBox.critical(None, "Error", "An attribute filed with unique fields must be selected")
        #         return
        #
        #     vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        #     prov = vlayer.dataProvider()
        #     fields = prov.fields()
        #     idx = vlayer.fieldNameIndex(poly_field)
        #
        #     progress.setMaximum(vlayer.featureCount())
        #     progressMessageBar.layout().addWidget(progress)
        #     self.iface.messageBar().pushWidget(progressMessageBar, self.iface.messageBar().INFO)
        #
        #     dir_poly = self.plugin_dir + '/data/poly_temp.shp'
        #     j = 0
        #     for f in vlayer.getFeatures():  # looping through each grip polygon
        #         progress.setValue(j + 1)
        #
        #         #savename = self.plugin_dir + '/data/' + str(j) + ".shp"
        #         writer = QgsVectorFileWriter(dir_poly, "CP1250", fields, prov.geometryType(),
        #                                      prov.crs(), "ESRI shapefile")
        #
        #         if writer.hasError() != QgsVectorFileWriter.NoError:
        #             self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))
        #
        #         attributes = f.attributes()
        #         self.iface.messageBar().pushMessage("Test", str(f.attributes()[idx]))
        #         geometry = f.geometry()
        #         feature = QgsFeature()
        #         feature.setAttributes(attributes)
        #         feature.setGeometry(geometry)
        #         writer.addFeature(feature)
        #         del writer
        #
        #         if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
        #             dsm_build = self.layerComboManagerDSMbuild.getLayer()
        #             if dsm_build is None:
        #                 QMessageBox.critical(None, "Error", "No valid building DSM raster layer is selected")
        #                 return
        #
        #             provider = dsm_build.dataProvider()
        #             filePath_dsm_build = str(provider.dataSourceUri())
        #             gdalruntextdsm_build = 'gdalwarp -dstnodata -9999 -q -cutline ' + dir_poly + \
        #                                    ' -crop_to_cutline -of GTiff ' + filePath_dsm_build + \
        #                                    ' ' + self.plugin_dir + '/data/clipdsm.tif'
        #             os.system(gdalruntextdsm_build)
        #             dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
        #             dsm = dataset.ReadAsArray().astype(np.float)
        #             sizex = dsm.shape[0]
        #             sizey = dsm.shape[1]
        #             dem = np.zeros((sizex, sizey))
        #
        #         else:  # Both building ground heights
        #             dsm = self.layerComboManagerDSMbuildground.getLayer()
        #             dem = self.layerComboManagerDEM.getLayer()
        #
        #             if dsm is None:
        #                 QMessageBox.critical(None, "Error", "No valid ground and building DSM raster layer is selected")
        #                 return
        #             if dem is None:
        #                 QMessageBox.critical(None, "Error", "No valid ground DEM raster layer is selected")
        #                 return
        #
        #             # # get raster source - gdalwarp
        #             provider = dsm.dataProvider()
        #             filePath_dsm = str(provider.dataSourceUri())
        #             provider = dem.dataProvider()
        #             filePath_dem = str(provider.dataSourceUri())
        #             gdalruntextdsm = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + dir_poly + \
        #                              ' -crop_to_cutline -of GTiff ' + filePath_dsm + \
        #                              ' ' + self.plugin_dir + '/data/clipdsm.tif'
        #             gdalruntextdem = 'gdalwarp -dstnodata -9999 -q -overwrite -cutline ' + dir_poly + \
        #                              ' -crop_to_cutline -of GTiff ' + filePath_dem + \
        #                              ' ' + self.plugin_dir + '/data/clipdem.tif'
        #             si = subprocess.STARTUPINFO()
        #             si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        #             subprocess.call(gdalruntextdsm, startupinfo=si)
        #             subprocess.call(gdalruntextdem, startupinfo=si)
        #
        #             dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
        #             dsm = dataset.ReadAsArray().astype(np.float)
        #             dataset2 = gdal.Open(self.plugin_dir + '/data/clipdem.tif')
        #             dem = dataset2.ReadAsArray().astype(np.float)
        #
        #         geotransform = dataset.GetGeoTransform()
        #         scale = 1 / geotransform[1]
        #
        #         nodata_test = (dem == -9999)
        #         if nodata_test.any() == True:
        #             self.iface.messageBar().pushMessage("Image Morphometric Parameters", str(j))
        #         else:
        #             immorphresult = imagemorphparam_v1(dsm, dem, scale, 0, 5.)
        #
        #             # save to file
        #             header = ' Wd pai   fai   zH'
        #             numformat = '%3d %4.3f %4.3f %5.3f'
        #             arr = np.concatenate((immorphresult["deg"], immorphresult["pai"], immorphresult["fai"],
        #                                   immorphresult["zH"]), axis=1)
        #             np.savetxt(self.plugin_dir + '/data/result_' + str(f.attributes()[idx]) + '.txt', arr,
        #                        fmt=numformat, delimiter=' ', header=header, comments='')
        #
        #         dataset = None
        #         dataset2 = None
        #         dataset3 = None
        #
        #         j += 1
        #         time.sleep(0.25)
        #
        #     self.iface.messageBar().clearWidgets()
        #     self.iface.messageBar().pushMessage("Image Morphometric Parameters", "Process successful!")
