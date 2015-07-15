# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ShadowGenerator
                                 A QGIS plugin
 Simulate casting shadows
                              -------------------
        begin                : 2015-04-10
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
#from PyQt4.QtGui import QAction, QIcon, QFileDialog
from PyQt4.QtGui import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from shadow_generator_dialog import ShadowGeneratorDialog
from ..Utilities.qgiscombomanager import *
from osgeo import gdal, osr
#import gdal from gdalconst import *
import os.path
import dailyshading as dsh
import numpy as np


class ShadowGenerator:
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
            'ShadowGenerator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ShadowGeneratorDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.shadowCheckBox.stateChanged.connect(self.checkbox_changed)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Shadow Generator')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'ShadowGenerator')
        # self.toolbar.setObjectName(u'ShadowGenerator')
        self.folderPath = 'None'
        self.timeInterval = 30

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
        return QCoreApplication.translate('ShadowGenerator', message)

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

        icon_path = ':/plugins/ShadowGenerator/ShadowIcon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Shadow Generator'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Shadow Generator'),
                action)
            self.iface.removeToolBarIcon(action)

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def checkbox_changed(self):
        if self.dlg.shadowCheckBox.isChecked():
            self.dlg.timeEdit.setEnabled(True)
        else:
            self.dlg.timeEdit.setEnabled(False)

    def start_progress(self):

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

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

        old_cs = osr.SpatialReference()
        dsm_ref = dsmlayer.crs().toWkt()
        old_cs.ImportFromWkt(dsm_ref)

        wgs84_wkt = """
        GEOGCS["WGS 84",
            DATUM["WGS_1984",
                SPHEROID["WGS 84",6378137,298.257223563,
                    AUTHORITY["EPSG","7030"]],
                AUTHORITY["EPSG","6326"]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.01745329251994328,
                AUTHORITY["EPSG","9122"]],
            AUTHORITY["EPSG","4326"]]"""

        new_cs = osr.SpatialReference()
        new_cs.ImportFromWkt(wgs84_wkt)

        transform = osr.CoordinateTransformation(old_cs, new_cs)

        width = gdal_dsm.RasterXSize
        height = gdal_dsm.RasterYSize
        gt = gdal_dsm.GetGeoTransform()
        minx = gt[0]
        miny = gt[3] + width*gt[4] + height*gt[5]
        lonlat = transform.TransformPoint(minx, miny)
        geotransform = gdal_dsm.GetGeoTransform()
        scale = 1 / geotransform[1]

        trans = self.dlg.spinBoxTrans.value() / 100.0

        if self.dlg.checkBoxUseVeg.isChecked():

            usevegdem = 1

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

            if not (vegsizex == sizex) & (vegsizey == sizey):
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
            date = self.dlg.calendarWidget.selectedDate()
            year = date.year()
            month = date.month()
            day = date.day()
            UTC = self.dlg.spinBoxUTC.value()
            if self.dlg.shadowCheckBox.isChecked():
                onetime = 1
                time = self.dlg.timeEdit.time()
                hour = time.hour()
                minu = time.minute()
                sec = time.second()
            else:
                onetime = 0
                hour = 0
                minu = 0
                sec = 0

            tv = [year, month, day, hour, minu, sec]

            intervalTime = self.dlg.intervalTimeEdit.time()
            self.timeInterval = intervalTime.minute() + (intervalTime.hour() * 60) + (intervalTime.second()/60)
            shadowresult = dsh.dailyshading(dsm, vegdsm, vegdsm2, scale, lonlat, sizex, sizey, tv, UTC, usevegdem,
                                       self.timeInterval, onetime, self.dlg, self.folderPath[0], gdal_dsm, trans)

            shfinal = shadowresult["shfinal"]
            time_vector = shadowresult["time_vector"]

            if onetime == 0:
                timestr = time_vector.strftime("%Y%m%d")
                savestr = '/shadow_fraction_on'
            else:
                timestr = time_vector.strftime("%Y%m%d_%H%M")
                savestr = '/shadow_at_'

        filename = self.folderPath[0] + savestr + timestr + '.tif'

        dsh.saveraster(gdal_dsm, filename, shfinal)

        QMessageBox.information(None, "ShadowGenerator", "Shadow grid(s) successfully generated")
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
        self.dlg.exec_()

