# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SEBEpv
                                 A QGIS plugin
 Derived from SEBE:
 Calculated solar energy on roofs, walls and ground
                             -------------------
        begin                : 2015-09-17
        copyright            : (C) 2015 by Fredrik Lindberg - Dag Wästberg
        email                : fredrikl@gvc.gu.se
        git sha              : $Format:%H$

 New SEBEpv:
 Calculate Photovoltaic power on walls and roofs
                              -------------------
        begin                : 2016-11-17
        copyright            : (C) 2016 by Michael Revesz
        email                : michael.revesz@ait.ac.at
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.gui import QgsMessageBar
from qgis.core import QgsMessageLog
# Initialize Qt resources from file resources.py
# import resources
# Import the code for the dialog
from sebepv_dialog import SEBEDialog
import os.path
from ..Utilities.qgiscombomanager import *
from ..Utilities.misc import *
from osgeo import gdal, osr
import numpy as np
from sebeworker import Worker
from SEBEfiles.Solweig_v2015_metdata_noload import Solweig_2015a_metdata_noload
from SEBEfiles import pvmodel as pv
from SEBEfiles import ParameterCombo as pc       # for PV model combobox
from SEBEfiles.sunmapcreator_2016pv import sunmapcreator_2015a
import webbrowser


def valid_float(value):
    """ Returns True if value can be converted to float,
        otherwise returns False.
    """
    try:
        float(value)
    except ValueError:
        return False
    else:
        return True


class SEBEpv:
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
            'SEBE_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # PV module parameters:
        self.celltdata = self.plugin_dir + "/ModelParameters/temperature_model.txt"
        self.pvdata = self.plugin_dir + "/ModelParameters/photovoltaic_model.txt"

        # Create the dialog (after translation) and keep reference
        self.dlg = SEBEDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.runButton.setEnabled(0)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        # self.dlg.shadowCheckBox.stateChanged.connect(self.checkbox_changed)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.pushButtonImport.clicked.connect(self.read_metdata)
        self.dlg.pushButtonSaveIrradiance.clicked.connect(self.save_radmat)
        self.dlg.ButtonDefault.clicked.connect(self.set_default_pvmodel)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)
        self.fileDialogFile = QFileDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SEBEpv - Photovoltaic Yield on Building Envelopes')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SEBEpv')
        # self.toolbar.setObjectName(u'SEBEpv')

        self.layerComboManagerDSM = RasterLayerCombo(self.dlg.comboBox_dsm)
        RasterLayerCombo(self.dlg.comboBox_dsm, initLayer="")
        self.layerComboManagerVEGDSM = RasterLayerCombo(self.dlg.comboBox_vegdsm)
        RasterLayerCombo(self.dlg.comboBox_vegdsm, initLayer="")
        self.layerComboManagerVEGDSM2 = RasterLayerCombo(self.dlg.comboBox_vegdsm2)
        RasterLayerCombo(self.dlg.comboBox_vegdsm2, initLayer="")
        self.layerComboManagerWH = RasterLayerCombo(self.dlg.comboBox_wallheight)
        RasterLayerCombo(self.dlg.comboBox_wallheight, initLayer="")
        self.layerComboManagerWA = RasterLayerCombo(self.dlg.comboBox_wallaspect)
        RasterLayerCombo(self.dlg.comboBox_wallaspect, initLayer="")

        # PV model combobox:
        keys, params = pc.load_data(self.celltdata)
        self.ComboPVmount = pc.ParametersCombo(self.dlg.comboPVmount, keys, params)
        keys, params = pc.load_data(self.pvdata)
        self.ComboPVtech = pc.ParametersCombo(self.dlg.comboPVtech, keys, params)
        self.dlg.linePnom.setText('1.')

        self.dlg.comboPVmount.currentIndexChanged.connect(self.update_tempmodel_params)
        self.dlg.comboPVtech.currentIndexChanged.connect(self.update_pvmodel_params)

        self.dlg.lineK1.editingFinished.connect(self.manual_pv_params)
        self.dlg.lineK2.editingFinished.connect(self.manual_pv_params)
        self.dlg.lineK3.editingFinished.connect(self.manual_pv_params)
        self.dlg.lineK4.editingFinished.connect(self.manual_pv_params)
        self.dlg.lineK5.editingFinished.connect(self.manual_pv_params)
        self.dlg.lineK6.editingFinished.connect(self.manual_pv_params)
        self.dlg.lineTempA.editingFinished.connect(self.manual_tmp_params)
        self.dlg.lineTempB.editingFinished.connect(self.manual_tmp_params)
        self.dlg.lineTempD.editingFinished.connect(self.manual_tmp_params)
        self.dlg.linePnom.editingFinished.connect(self.manual_pnom)

        self.folderPath = None
        self.usevegdem = 0
        self.scale = None
        self.gdal_dsm = None
        self.dsm = None
        self.vegdsm = None
        self.vegdsm2 = None
        self.usevegdem = None
        self.folderPathMetdata = None
        self.metdata = None
        self.radmatfile = None

        self.thread = None
        self.worker = None
        self.steps = 0

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
        return QCoreApplication.translate('SEBEpv', message)


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
        icon_path = ':/plugins/SEBEpv/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Photovoltaic Yield on Building Envelopes'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SEBEpv - Photovoltaic Yield on Building Envelopes'),
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

    def read_metdata(self):
        self.fileDialogFile.open()
        result = self.fileDialogFile.exec_()
        if result == 1:
            # self.dlg.pushButtonExport.setEnabled(True)
            self.folderPathMetdata = self.fileDialogFile.selectedFiles()
            self.dlg.textInputMetdata.setText(self.folderPathMetdata[0])
            headernum = 1
            delim = ' '

            try:
                self.metdata = np.loadtxt(self.folderPathMetdata[0],skiprows=headernum, delimiter=delim)
            except:
                QMessageBox.critical(None, "Import Error", "Make sure format of meteorological file is correct. You can"
                                                           "prepare your data by using 'Prepare Existing Data' in "
                                                           "the Pre-processor")
                return

            # Test if short wave irradiation is within bounds:
            testwhere = np.where((self.metdata[:, 14] < 0.0) | (self.metdata[:, 14] > 1300.0))
            if testwhere[0].__len__() > 0:
                QMessageBox.critical(None, "Value error", "Kdown - beyond what is expected at line: \n" +
                                     str(testwhere[0] + 1))
                return

            # Test if ambient temperature is within bounds:
            testwhere = np.where((self.metdata[:, 11] < -30.0) | (self.metdata[:, 11] > 55.0))
            if testwhere[0].__len__() > 0:
                QMessageBox.critical(None, "Value error", "Air temperature - beyond what is expected at line:"
                                                          " \n" + str(testwhere[0] + 1))
                return

            # Test if wind speed is within bounds:
            testwhere = np.where((self.metdata[:, 9] <= 0) | (self.metdata[:, 9] > 60.0))
            if testwhere[0].__len__() > 0:
                QMessageBox.critical(None, "Value error", "Wind speed - beyond what is expected at line:"
                                                          " \n" + str(testwhere[0] + 1))
                return

            if self.metdata.shape[1] == 24:
                self.iface.messageBar().pushMessage("SEBEpv", "Meteorological data succefully loaded",
                                                    level=QgsMessageBar.INFO, duration=3)
            else:
                QMessageBox.critical(None, "Import Error", "Wrong number of columns in meteorological data. You can "
                                                           "prepare your data by using 'Prepare Existing Data' in "
                                                           "the Pre-processor")
                return

    def save_radmat(self):
        self.radmatfile = self.fileDialogFile.getSaveFileName(None, "Save File As:", None, "Text Files (*.txt)")
        self.dlg.textOutputIrradience.setText(self.radmatfile)

    def set_default_pvmodel(self):
        self.ComboPVmount.set_selection_index('Open rack cell polymerback')
        self.ComboPVtech.set_selection_index('c-Si Huld')
        self.dlg.linePnom.setText("1.")
        self.check_allparams_valid()

    def manual_pv_params(self):
        sender = self.dlg.sender()
        value = sender.text()
        if valid_float(value):
            pass
        else:
            sender.setText("invalid number")
        self.ComboPVtech.set_selection_index('')
        self.check_allparams_valid()

    def manual_tmp_params(self):
        sender = self.dlg.sender()
        value = sender.text()
        if valid_float(value):
            pass
        else:
            sender.setText("invalid number")
        self.ComboPVmount.set_selection_index('')
        self.check_allparams_valid()

    def manual_pnom(self):
        sender = self.dlg.sender()
        value = sender.text()
        if valid_float(value):
            pass
        else:
            sender.setText("invalid number")
        self.check_allparams_valid()

    def check_allparams_valid(self):
        allvalues = [self.dlg.lineK1.text(),
                     self.dlg.lineK2.text(),
                     self.dlg.lineK3.text(),
                     self.dlg.lineK4.text(),
                     self.dlg.lineK5.text(),
                     self.dlg.lineK6.text(),
                     self.dlg.lineTempA.text(),
                     self.dlg.lineTempB.text(),
                     self.dlg.lineTempD.text(),
                     self.dlg.linePnom.text()
                     ]
        if ("invalid number" in allvalues) or ("" in allvalues):
            self.dlg.runButton.setEnabled(0)
        else:
            self.dlg.runButton.setEnabled(1)

    def update_pvmodel_params(self):
        self.ComboPVtech.changed_selection()
        try:
            params = self.ComboPVtech.paramdict[self.ComboPVtech.get_current_item()]
        except KeyError:
            pass   # ignore, as with manual edit key becomes ''.
        else:
            self.dlg.lineK1.setText(str(params[0]))
            self.dlg.lineK2.setText(str(params[1]))
            self.dlg.lineK3.setText(str(params[2]))
            self.dlg.lineK4.setText(str(params[3]))
            self.dlg.lineK5.setText(str(params[4]))
            self.dlg.lineK6.setText(str(params[5]))
            self.check_allparams_valid()

    def update_tempmodel_params(self):
        self.ComboPVmount.changed_selection()
        try:
            params = self.ComboPVmount.paramdict[self.ComboPVmount.get_current_item()]
        except KeyError:
            pass   # ignore, as with manual edit key becomes ''.
        else:
            self.dlg.lineTempA.setText(str(params[0]))
            self.dlg.lineTempB.setText(str(params[1]))
            self.dlg.lineTempD.setText(str(params[2]))
            self.check_allparams_valid()


    def start_progress(self):
        self.dlg.progressBar.setRange(0, 145*len(self.metdata[:, 0]))
        if self.folderPath is None:
            QMessageBox.critical(None, "Error", "No output folder selected")
            return
        else:
            dsmlayer = self.layerComboManagerDSM.getLayer()

            if dsmlayer is None:
                    QMessageBox.critical(None, "Error", "No valid DSM raster layer is selected")
                    return

            provider = dsmlayer.dataProvider()
            filepath_dsm = str(provider.dataSourceUri())
            # self.dsmpath = filepath_dsm
            self.gdal_dsm = gdal.Open(filepath_dsm)
            self.dsm = self.gdal_dsm.ReadAsArray().astype(float)
            sizex = self.dsm.shape[0]
            sizey = self.dsm.shape[1]

            # Get latlon from grid coordinate system
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
            width = self.gdal_dsm.RasterXSize
            height = self.gdal_dsm.RasterYSize
            geotransform = self.gdal_dsm.GetGeoTransform()
            minx = geotransform[0]
            miny = geotransform[3] + width*geotransform[4] + height*geotransform[5]
            lonlat = transform.TransformPoint(minx, miny)
            lon = lonlat[0]
            lat = lonlat[1]
            self.scale = 1 / geotransform[1]
            # self.iface.messageBar().pushMessage("SEBE", str(lonlat),level=QgsMessageBar.INFO)

            if (sizex * sizey) > 250000 and (sizex * sizey) <= 1000000:
                QMessageBox.warning(None, "Semi lage grid", "This process will take a couple of minutes. "
                                                            "Go and make yourself a cup of tea...")

            if (sizex * sizey) > 1000000 and (sizex * sizey) <= 4000000:
                QMessageBox.warning(None, "Large grid", "This process will take some time. "
                                                        "Go for lunch...")

            if (sizex * sizey) > 4000000 and (sizex * sizey) <= 16000000:
                QMessageBox.warning(None, "Very large grid", "This process will take a long time. "
                                                             "Go for lunch and for a walk...")

            if (sizex * sizey) > 16000000:
                QMessageBox.warning(None, "Huge grid", "This process will take a very long time. "
                                                       "Go home for the weekend or consider to tile your grid")

            if self.dlg.checkBoxUseVeg.isChecked():
                self.usevegdem = 1
                self.vegdsm = self.layerComboManagerVEGDSM.getLayer()

                if self.vegdsm is None:
                    QMessageBox.critical(None, "Error", "No valid vegetation DSM selected")
                    return

                # load raster
                gdal.AllRegister()
                provider = self.vegdsm.dataProvider()
                filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(filePathOld)
                self.vegdsm = dataSet.ReadAsArray().astype(float)

                vegsizex = self.vegdsm.shape[0]
                vegsizey = self.vegdsm.shape[1]

                if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                    QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                    return

                if self.dlg.checkBoxTrunkExist.isChecked():
                    self.vegdsm2 = self.layerComboManagerVEGDSM2.getLayer()

                    if self.vegdsm2 is None:
                        QMessageBox.critical(None, "Error", "No valid trunk zone DSM selected")
                        return

                    # load raster
                    gdal.AllRegister()
                    provider = self.vegdsm.dataProvider()
                    filePathOld = str(provider.dataSourceUri())
                    dataSet = gdal.Open(filePathOld)
                    self.vegdsm2 = dataSet.ReadAsArray().astype(float)
                else:
                    trunkratio = self.dlg.spinBoxTrunkHeight.value() / 100.0
                    self.vegdsm2 = self.vegdsm * trunkratio

                vegsizex = self.vegdsm2.shape[0]
                vegsizey = self.vegdsm2.shape[1]

                if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                    QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                    return
            else:
                self.vegdsm = 0
                self.vegdsm2 = 0
                self.usevegdem = 0

            UTC = self.dlg.spinBoxUTC.value()
            psi = self.dlg.spinBoxTrans.value() / 100.0
            voxelheight = geotransform[1]
            albedo = self.dlg.doubleSpinBoxAlbedo.value()
            if self.dlg.checkBoxUseOnlyGlobal.isChecked():
                onlyglobal = 1
            else:
                onlyglobal = 0

            output = {'energymonth': 0, 'energyyear': 1, 'suitmap': 0}

             # wall height layer
            whlayer = self.layerComboManagerWH.getLayer()
            if whlayer is None:
                    QMessageBox.critical(None, "Error", "No valid wall height raster layer is selected")
                    return
            provider = whlayer.dataProvider()
            filepath_wh= str(provider.dataSourceUri())
            self.gdal_wh = gdal.Open(filepath_wh)
            self.wheight = self.gdal_wh.ReadAsArray().astype(float)
            vhsizex = self.wheight.shape[0]
            vhsizey = self.wheight.shape[1]
            if not (vhsizex == sizex) & (vhsizey == sizey):  # &
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

            # wall aspectlayer
            walayer = self.layerComboManagerWA.getLayer()
            if walayer is None:
                    QMessageBox.critical(None, "Error", "No valid wall aspect raster layer is selected")
                    return
            provider = walayer.dataProvider()
            filepath_wa= str(provider.dataSourceUri())
            self.gdal_wa = gdal.Open(filepath_wa)
            self.waspect = self.gdal_wa.ReadAsArray().astype(float)
            vasizex = self.waspect.shape[0]
            vasizey = self.waspect.shape[1]
            if not (vasizex == sizex) & (vasizey == sizey):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

            # Prepare metdata
            alt = self.dsm.mean()
            location = {'longitude': lon, 'latitude': lat, 'altitude': alt}
            YYYY, altitude, azimuth, zen, jday, leafon, dectime, altmax = \
                Solweig_2015a_metdata_noload(self.metdata,location, UTC)

            building_slope, building_aspect = get_ders(self.dsm, self.scale)
            calc_month = False  # TODO: Month not implemented

            # setup photovoltaic and cell-temperature model:
            pvmodel = pv.PhotovoltaicModel(self.pvdata)
            celltemp = pv.TemperatureModel(self.celltdata)

            if self.ComboPVtech.get_current_item() != '':
                pvmodel.set_model(self.ComboPVtech.get_current_item())
                pvmodel.set_peakpower(self.dlg.linePnom.text())
            else:
                pvmodel.set_modelparams(self.dlg.linePnom.text(),
                                        self.dlg.lineK1.text(),
                                        self.dlg.lineK2.text(),
                                        self.dlg.lineK3.text(),
                                        self.dlg.lineK4.text(),
                                        self.dlg.lineK5.text(),
                                        self.dlg.lineK6.text())
            if self.ComboPVmount.get_current_item() != '':
                celltemp.set_model(self.ComboPVmount.get_current_item())
            else:
                celltemp.set_modelparams(self.dlg.lineTempA,
                                         self.dlg.lineTempB,
                                         self.dlg.lineTempD
                                         )

            self.startWorker(self.dsm, self.scale, building_slope, building_aspect, voxelheight, sizey, sizex,
                             self.vegdsm, self.vegdsm2, self.wheight, self.waspect, albedo, psi,
                             self.metdata, altitude, azimuth, onlyglobal, output, jday, location, zen,
                             self.usevegdem, calc_month, self.dlg, pvmodel, celltemp)

    # here changes by MRevesz:
    def startWorker(self, dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex,
                    vegdsm, vegdsm2, wheight, waspect, albedo, psi,
                    metdata, altitude, azimuth, onlyglobal, output, jday, location, zen,
                    usevegdem, calc_month, dlg, pvm, tcel):
        # create a new worker instance
        worker = Worker(dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex,
                        vegdsm, vegdsm2, wheight, waspect, albedo, psi,
                        metdata, altitude, azimuth, onlyglobal, output, jday, location, zen,
                        usevegdem, calc_month, dlg, pvm, tcel)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.pushButtonClose.setEnabled(False)

        # start the worker in a new thread
        thread = QThread(self.dlg)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, ret):
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # remove widget from message bar
        if ret is not None:
            # report the result
            Energyyearroof = ret["PVEnergyyearroof"]
            Energyyearwall = ret["PVEnergyyearwall"]
            vegdata = ret["vegdata"]
            # layer, total_area = ret
            saveraster(self.gdal_dsm, self.folderPath[0] + '/dsm.tif', self.dsm)
            filenameroof = self.folderPath[0] + '/PVEnergyyearroof.tif'
            saveraster(self.gdal_dsm, filenameroof, Energyyearroof)
            filenamewall = self.folderPath[0] + '/PVEnergyyearwall.txt'
            header = '%row col irradiance'
            # numformat = '%4d %4d ' + '%6.2f ' * (Energyyearwall.shape[1] - 2)
            numformat = '%4d %4d ' + '%.4E ' * (Energyyearwall.shape[1] - 2)
            np.savetxt(filenamewall, Energyyearwall, fmt=numformat, header=header, comments='')
            if self.usevegdem == 1:
                filenamewall = self.folderPath[0] + '/Vegetationdata.txt'
                header = '%row col height'
                numformat = '%4d %4d %.4E'    #%6.2f'
                np.savetxt(filenamewall, vegdata, fmt=numformat, header=header, comments='')
            QMessageBox.information(None, "SEBEpv", "Calculation successfully completed")

            # load roof irradiance result into map canvas
            if self.dlg.checkBoxIntoCanvas.isChecked():
                rlayer = self.iface.addRasterLayer(filenameroof)

                # Trigger a repaint
                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

                rlayer.loadNamedStyle(self.plugin_dir + '/SEBE_kwh.qml')
                # self.QgsMapLayerRegistry.instance().addMapLayer(rlayer)

                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

            QMessageBox.information(None, "SEBEpv", "Calculation successfully completed")
        else:
            # notify the user that something went wrong
            self.iface.messageBar().pushMessage('Operations cancelled either by user or error. ' +
                                                'See the General tab in Log Messages Panel ' +
                                                '(speech bubble, lower right) for more information.',
                                                level=QgsMessageBar.CRITICAL, duration=3)
            QMessageBox.information(None, "SEBEpv",
                                    'Operations cancelled either by user or error. See the General tab ' +
                                    'in Log Messages Panel (speech bubble, lower right) for more information.')
        self.dlg.runButton.setText('Run')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.steps = 0
        self.dlg.progressBar.setValue(self.steps)
        self.dlg.pushButtonClose.setEnabled(True)

    def workerError(self, errorstring):
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = "http://www.urban-climate.net/umep/UMEP_Manual#Solar_Radiation:_Solar_Energy_on_Building_Envelopes_.28SEBE.29"
        webbrowser.open_new_tab(url)
