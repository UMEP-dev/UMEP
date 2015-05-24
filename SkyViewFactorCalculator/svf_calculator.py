# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SkyViewFactorCalculator
                                 A QGIS plugin
 Calculates SVF on high resolution DSM (building and vegetation)
                              -------------------
        begin                : 2015-02-04
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from svf_calculator_dialog import SkyViewFactorCalculatorDialog
import os.path
import numpy as np
from qgiscombomanager import *
from osgeo import gdal
import Skyviewfactor4d as svf
from osgeo.gdalconst import *

class SkyViewFactorCalculator:
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
            'SkyViewFactorCalculator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SkyViewFactorCalculatorDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Sky View Factor Calculator')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'SkyViewFactorCalculator')
        self.toolbar.setObjectName(u'SkyViewFactorCalculator')

        self.layerComboManagerDSM = RasterLayerCombo(self.dlg.comboBox_dsm)
        RasterLayerCombo(self.dlg.comboBox_dsm, initLayer="")
        self.layerComboManagerVEGDSM = RasterLayerCombo(self.dlg.comboBox_vegdsm)
        RasterLayerCombo(self.dlg.comboBox_vegdsm, initLayer="")
        self.layerComboManagerVEGDSM2 = RasterLayerCombo(self.dlg.comboBox_vegdsm2)
        RasterLayerCombo(self.dlg.comboBox_vegdsm2, initLayer="")

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
        return QCoreApplication.translate('SkyViewFactorCalculator', message)


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

        icon_path = ':/plugins/SkyViewFactorCalculator/icon_svf.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Calculates SVF on high resolution DSM (building and vegetation)'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Sky View Factor Calculator'),
                action)
            self.iface.removeToolBarIcon(action)

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def start_progress(self):
        self.dlg.textOutput.setText(self.folderPath[0])
        dsmlayer = self.layerComboManagerDSM.getLayer()

        if dsmlayer is None:
                QMessageBox.critical(None, "Error", "No valid raster layer is selected")
                return

        provider = dsmlayer.dataProvider()
        filepath_dsm = str(provider.dataSourceUri())
        gdal_dsm = gdal.Open(filepath_dsm)
        dsm = gdal_dsm.ReadAsArray().astype(np.float)
        sizex = dsm.shape[0]
        sizey = dsm.shape[1]
        geotransform = gdal_dsm.GetGeoTransform()
        scale = 1 / geotransform[1]

        if self.dlg.checkBoxUseVeg.isChecked():

            usevegdem = 1

            trans = self.dlg.spinBoxTrans.value() / 100.0

            vegdsm = self.layerComboManagerVEGDSM.getLayer()

            if vegdsm is None:
                QMessageBox.critical(None, "Error", "No valid vegetation DSM selected")
                return

            # load raster
            gdal.AllRegister()
            provider = vegdsm.dataProvider()
            filePathOld = str(provider.dataSourceUri())
            dataSet = gdal.Open(filePathOld)
            vegdsm = dataSet.ReadAsArray().astype(np.float)

            vegsizex = vegdsm.shape[0]
            vegsizey = vegdsm.shape[1]

            if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

            if self.dlg.checkBoxTrunkExist.isChecked():
                vegdsm2 = self.layerComboManagerVEGDSM2.getLayer()

                if vegdsm2 is None:
                    QMessageBox.critical(None, "Error", "No valid trunk zone DSM selected")
                    return

                # load raster
                gdal.AllRegister()
                provider = vegdsm.dataProvider()
                filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(filePathOld)
                vegdsm2 = dataSet.ReadAsArray().astype(np.float)
            else:
                trunkratio = self.dlg.spinBoxTrunkHeight.value() / 100.0
                vegdsm2 = vegdsm * trunkratio

            vegsizex = vegdsm2.shape[0]
            vegsizey = vegdsm2.shape[1]

            if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

        else:
            vegdsm = 0
            vegdsm2 = 0
            usevegdem = 0

        if self.folderPath is 'None':
            QMessageBox.critical(None, "Error", "No selected folder")
            return
        else:

            svfresult = svf.Skyviewfactor4d(dsm, scale, self.dlg)
            svfbu = svfresult["svf"]
            svfbuE = svfresult["svfE"]
            svfbuS = svfresult["svfS"]
            svfbuW = svfresult["svfW"]
            svfbuN = svfresult["svfN"]

            svfbuname = svfresult.keys()

            svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[0] + '.tif', svfbu)
            svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[1] + '.tif', svfbuE)
            svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[2] + '.tif', svfbuS)
            svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[3] + '.tif', svfbuW)
            svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[4] + '.tif', svfbuN)

            if usevegdem == 1:
                svfvegresult = svf.Skyviewfactor4d_veg(dsm, scale, vegdsm, vegdsm2, self.dlg)
                svfveg = svfvegresult["svfveg"]
                svfEveg = svfvegresult["svfEveg"]
                svfSveg = svfvegresult["svfSveg"]
                svfWveg = svfvegresult["svfWveg"]
                svfNveg = svfvegresult["svfNveg"]
                svfaveg = svfvegresult["svfaveg"]
                svfEaveg = svfvegresult["svfEaveg"]
                svfSaveg = svfvegresult["svfSaveg"]
                svfWaveg = svfvegresult["svfWaveg"]
                svfNaveg = svfvegresult["svfNaveg"]

                svfvegname = svfvegresult.keys()

                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[0] + '.tif', svfveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[1] + '.tif', svfEveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[2] + '.tif', svfSveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[3] + '.tif', svfWveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[4] + '.tif', svfNveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[5] + '.tif', svfaveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[6] + '.tif', svfEaveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[7] + '.tif', svfSaveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[8] + '.tif', svfWaveg)
                svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[9] + '.tif', svfNaveg)

                svftotal = (svfbu-(1-svfveg)*(1-trans))
            else:
                svftotal = svfbu

            filename = self.folderPath[0] + '/' + 'SkyViewFactor' + '.tif'

            svf.saveraster(gdal_dsm, filename, svftotal)

        QMessageBox.information(None, "Sky View Factor Calculator", "SVF grid(s) successfully generated")
        # self.iface.messageBar().pushMessage("ShadowGenerator", "Shadow grid(s) successfully generated")

        # load result into canvas
        if self.dlg.checkBoxIntoCanvas.isChecked():
            rlayer = self.iface.addRasterLayer(filename)

            # Set opacity
            rlayer.renderer().setOpacity(0.5)

            # Trigger a repaint
            if hasattr(rlayer, "setCacheImage"):
                rlayer.setCacheImage(None)
            rlayer.triggerRepaint()

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        # result = self.dlg.exec_()
        self.dlg.exec_()
        # See if OK was pressed
       # if result:

            #progressMessageBar = self.dlg.messageBar().createMessage("Processing...")
            #progress = QProgressBar()

            # dsm = self.layerComboManagerDSM.getLayer()
            # if dsm is None:
            #     QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            #     return
            #
            # # load raster
            # gdal.AllRegister()
            # provider = dsm.dataProvider()
            # filePathOld = str(provider.dataSourceUri())
            # dataSet = gdal.Open(filePathOld)
            # dsm = dataSet.ReadAsArray().astype(np.float)
            # geotransform = dataSet.GetGeoTransform()
            # scale = 1 / geotransform[1]
            #
            # if self.dlg.checkBoxUseVeg.isChecked():
            #
            #     vegdsm = self.layerComboManagerVEGDSM.getLayer()
            #
            #     #if dsm is None:
            #     #    QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            #         #stop
            #
            #     # load raster
            #     gdal.AllRegister()
            #     provider = vegdsm.dataProvider()
            #     filePathOld = str(provider.dataSourceUri())
            #     dataSet = gdal.Open(filePathOld)
            #     vegdsm = dataSet.ReadAsArray().astype(np.float)
            #
            #     if self.dlg.checkBoxTrunkExist.isChecked():
            #         vegdsm2 = self.layerComboManagerVEGDSM2.getLayer()
            #
            #         #if dsm is None:
            #         #    QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            #             #stop
            #
            #         # load raster
            #         gdal.AllRegister()
            #         provider = vegdsm.dataProvider()
            #         filePathOld = str(provider.dataSourceUri())
            #         dataSet = gdal.Open(filePathOld)
            #         vegdsm2 = dataSet.ReadAsArray().astype(np.float)
            #     else:
            #         trunkratio = self.dlg.spinBoxTrunkHeight.value() /100
            #         vegdsm2 = vegdsm * trunkratio
            #
            #     # calculate vegsvfs
            #     # svfresult = svf.Skyviewfactor4d(dsm, scale, self.dlg)
            #     svfvegresult = svf.Skyviewfactor4d_veg(dsm, scale, vegdsm, vegdsm2, self.dlg)
            #
            # # else:
                # calculate svfs
            # svfresult = svf.Skyviewfactor4d(dsm, scale, self.dlg)
            # svfbu = svfresult["svf"]

            # if not self.outputFormat: # do memory layer
            #     QMessageBox.critical(None, "Error", "No selected folder")
            #     return
            # else:
            #     rows = dataSet.RasterYSize
            #     cols = dataSet.RasterXSize
            #
            #     outDs = gdal.GetDriverByName(self.outputFormat).Create(self.outputFile, cols, rows, int(1), GDT_Float32)
            #     outBand = outDs.GetRasterBand(1)
            #
            #     # write the data
            #     outBand.WriteArray(svfbu, 0, 0)
            #     #self.iface.messageBar().pushMessage("Altitude and Azimuth", str(self.outputFormat))
            #     # flush data to disk, set the NoData value and calculate stats
            #     outBand.FlushCache()
            #     outBand.SetNoDataValue(-9999)
            #
            #     # georeference the image and set the projection
            #     outDs.SetGeoTransform(dataSet.GetGeoTransform())
            #     outDs.SetProjection(dataSet.GetProjection())
            #
            #     del outDs, outBand
            #
            # if self.dlg.checkBoxIntoCanvas.isChecked():
            #     rlayer = self.iface.addRasterLayer(self.outputFile)
            #
            #     # Set opacity
            #     rlayer.renderer().setOpacity(0.5)
            #
            #     # Trigger a repaint
            #     if hasattr(rlayer, "setCacheImage"):
            #         rlayer.setCacheImage(None)
            #     rlayer.triggerRepaint()

