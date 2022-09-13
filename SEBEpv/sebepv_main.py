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
from qgis.gui import QgsMessageBar                       # commented for testing
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from PyQt4.QtGui import QApplication                       # added for testing
# from qgis.core import QgsMessageLog                      # commented for testing
# Initialize Qt resources from file resources.py
# import resources
# Import the code for the dialog:
from sebepv_dialog import SEBEDialog
import sys                                                          # for this main application needed!
import os.path
import Utilities.qgiscombomanager.testinglayercombo as tslc         # added for testing
from Utilities.misc import *                                        # added for testing
# from ..Utilities.qgiscombomanager import *                        # commented for testing
# from ..Utilities.misc import *                                    # commented for testing
from osgeo import gdal, osr
import numpy as np
from sebeworker import Worker
from SEBEfiles.Solweig_v2015_metdata_noload import Solweig_2015a_metdata_noload
import SEBEfiles.pvmodel as pv
import SEBEfiles.ParameterCombo as pc       # for PV model combobox
# from SEBEfiles.sunmapcreator_2016pv import sunmapcreator_2015a
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
    """Main implementation for testing. Usage without QGIS."""

    def __init__(self, iface):
        """Constructor.

        """
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        # locale = QSettings().value('locale/userLocale')[0:2]    # not needed for testing

        self.data_path = None
        # self.data_path ='<hardcoded directory for input>'
        # self.data_path = 'D:/.../03_Doktorat/02_Simulationen/19a_SEBEpv-BOKUvalidation_longterm/input-dsm/'

        if self.data_path == None:
            self.inputDialog = QFileDialog(caption="Select folder with raster layers", directory="./")
            self.inputDialog.setFileMode(4)
            self.inputDialog.setAcceptMode(0)
            result = 0
            while result != 1:
                self.inputDialog.open()
                result = self.inputDialog.exec_()
            self.inputPath = self.inputDialog.selectedFiles()
            self.data_path = self.inputPath[0] + "/"        # this fixes a bug: missing "/"
        else:
            pass

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
        self.fileDialog = QFileDialog(directory=self.data_path+'out')
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)
        self.fileDialogFile = QFileDialog(directory=self.data_path)


        # Declare instance attributes
        self.actions = []
        ##self.menu = self.tr(u'&SEBE - Solar Energy on Building Envelopes')    # not needed for testing
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SEBE')
        # self.toolbar.setObjectName(u'SEBE')

        self.layerComboManagerDSM = tslc.RasterLayerCombo(self.dlg.comboBox_dsm, self.data_path)
        # tslc.RasterLayerCombo(self.dlg.comboBox_dsm, self.data_path, initLayer="")
        self.layerComboManagerVEGDSM = tslc.RasterLayerCombo(self.dlg.comboBox_vegdsm, self.data_path)
        # tslc.RasterLayerCombo(self.dlg.comboBox_vegdsm, self.data_path, initLayer="")
        self.layerComboManagerVEGDSM2 = tslc.RasterLayerCombo(self.dlg.comboBox_vegdsm2, self.data_path)
        # tslc.RasterLayerCombo(self.dlg.comboBox_vegdsm2, self.data_path, initLayer="")
        self.layerComboManagerWH = tslc.RasterLayerCombo(self.dlg.comboBox_wallheight, self.data_path)
        # tslc.RasterLayerCombo(self.dlg.comboBox_wallheight, self.data_path, initLayer="")
        self.layerComboManagerWA = tslc.RasterLayerCombo(self.dlg.comboBox_wallaspect, self.data_path)
        # tslc.RasterLayerCombo(self.dlg.comboBox_wallaspect, self.data_path, initLayer="")
        self.layerComboManagerALB = tslc.RasterLayerCombo(self.dlg.comboBox_albedo, self.data_path)

        keys, params = pc.load_data(self.celltdata)
        self.ComboPVmount = pc.ParametersCombo(self.dlg.comboPVmount, keys, params)
        keys, params = pc.load_data(self.pvdata)
        self.ComboPVtech = pc.ParametersCombo(self.dlg.comboPVtech, keys, params)
        self.dlg.linePnom.setText('1.')

        # Signal to each ComboBox, connect with function to get current selected item:
        self.dlg.comboBox_dsm.currentIndexChanged.connect(self.layerComboManagerDSM.changed_selection)
        self.dlg.comboBox_vegdsm.currentIndexChanged.connect(self.layerComboManagerVEGDSM.changed_selection)
        self.dlg.comboBox_vegdsm2.currentIndexChanged.connect(self.layerComboManagerVEGDSM2.changed_selection)
        self.dlg.comboBox_wallheight.currentIndexChanged.connect(self.layerComboManagerWH.changed_selection)
        self.dlg.comboBox_wallaspect.currentIndexChanged.connect(self.layerComboManagerWA.changed_selection)
        self.dlg.comboBox_albedo.currentIndexChanged.connect(self.layerComboManagerALB.changed_selection)
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
        self.albedoRaster = None
        self.usevegdem = None
        self.folderPathMetdata = None
        self.metdata = None
        self.radmatfile = None
        # self.saveIntermedi = False

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
                # folder path must be <string> for testing!!
                self.metdata = np.loadtxt(str(self.folderPathMetdata[0]), skiprows=headernum, delimiter=delim)
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
                print "Meteorological data succefully loaded"
            # self.iface.messageBar().pushMessage("SEBE", "Meteorological data succefully loaded",
            # level=QgsMessageBar.INFO, duration=3)
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
            if self.ComboPVtech.get_current_item() == "Solar Irrad":
                self.dlg.linePnom.setText("1000.")
            else:
                pass
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
        if self.folderPath is None:
            QMessageBox.critical(None, "Error", "No output folder selected")
            return
        else:
            # dsmlayer = self.layerComboManagerDSM.getLayer()
            dsmlayer = self.layerComboManagerDSM.currentItem

            if dsmlayer is None:
                QMessageBox.critical(None, "Error", "No valid DSM raster layer is selected")
                return

            # provider = dsmlayer.dataProvider()
            # filepath_dsm = str(provider.dataSourceUri())
            filepath_dsm = self.data_path + dsmlayer
            # self.dsmpath = filepath_dsm
            self.gdal_dsm = gdal.Open(filepath_dsm)
            self.dsm = self.gdal_dsm.ReadAsArray().astype(np.float)
            sizex = self.dsm.shape[0]
            sizey = self.dsm.shape[1]

            # Get latlon from grid coordinate system
            old_cs = osr.SpatialReference()
            # dsm_ref = dsmlayer.crs().toWkt()
            # old_cs.ImportFromWkt(dsm_ref)
            old_cs.ImportFromWkt(self.gdal_dsm.GetProjectionRef())

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
                # self.vegdsm = self.layerComboManagerVEGDSM.getLayer()
                self.vegdsm = self.layerComboManagerVEGDSM.currentItem

                if self.vegdsm is None:
                    QMessageBox.critical(None, "Error", "No valid vegetation DSM selected")
                    return

                # load raster
                gdal.AllRegister()
                # provider = self.vegdsm.dataProvider()
                # filePathOld = str(provider.dataSourceUri())
                filePathOld = self.data_path + self.vegdsm
                dataSet = gdal.Open(filePathOld)
                self.vegdsm = dataSet.ReadAsArray().astype(np.float)

                vegsizex = self.vegdsm.shape[0]
                vegsizey = self.vegdsm.shape[1]

                if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                    QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                    return

                if self.dlg.checkBoxTrunkExist.isChecked():
                    # self.vegdsm2 = self.layerComboManagerVEGDSM2.getLayer()
                    self.vegdsm2 = self.layerComboManagerVEGDSM2.currentItem

                    if self.vegdsm2 is None:
                        QMessageBox.critical(None, "Error", "No valid trunk zone DSM selected")
                        return

                    # load raster
                    gdal.AllRegister()
                    # provider = self.vegdsm.dataProvider()
                    # filePathOld = str(provider.dataSourceUri())
                    filePathOld = self.data_path + self.vegdsm2
                    dataSet = gdal.Open(filePathOld)
                    self.vegdsm2 = dataSet.ReadAsArray().astype(np.float)
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
            # whlayer = self.layerComboManagerWH.getLayer()
            whlayer = self.layerComboManagerWH.currentItem
            if whlayer is None:
                QMessageBox.critical(None, "Error", "No valid wall height raster layer is selected")
                return
            # provider = whlayer.dataProvider()
            # filepath_wh= str(provider.dataSourceUri())
            filepath_wh = self.data_path + whlayer
            self.gdal_wh = gdal.Open(filepath_wh)
            self.wheight = self.gdal_wh.ReadAsArray().astype(np.float)
            vhsizex = self.wheight.shape[0]
            vhsizey = self.wheight.shape[1]
            if not (vhsizex == sizex) & (vhsizey == sizey):  # &
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

            # wall aspect layer
            # walayer = self.layerComboManagerWA.getLayer()
            walayer = self.layerComboManagerWA.currentItem
            if walayer is None:
                QMessageBox.critical(None, "Error", "No valid wall aspect raster layer is selected")
                return
            # provider = walayer.dataProvider()
            # filepath_wa= str(provider.dataSourceUri())
            filepath_wa = self.data_path + walayer
            self.gdal_wa = gdal.Open(filepath_wa)
            self.waspect = self.gdal_wa.ReadAsArray().astype(np.float)
            vasizex = self.waspect.shape[0]
            vasizey = self.waspect.shape[1]
            if not (vasizex == sizex) & (vasizey == sizey):
                QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                return

            # ground/roof albedo layer
            alblayer = self.layerComboManagerALB.currentItem
            if alblayer is None:
                self.albedoRaster = None
                QMessageBox.warning(None, "Info",
                                    "No ground albedo raster layer is selected. Continue with selected albedo!")
            else:
                filepath_alb = self.data_path + alblayer
                gdal_alb = gdal.Open(filepath_alb)
                self.albedoRaster = gdal_alb.ReadAsArray().astype(np.float)
                vasizex = self.albedoRaster.shape[0]
                vasizey = self.albedoRaster.shape[1]
                if not (vasizex == sizex) & (vasizey == sizey):
                    QMessageBox.critical(None, "Error", "All grids must be of same extent and resolution")
                    return

            # Prepare metdata
            alt = self.dsm.mean()
            location = {'longitude': lon, 'latitude': lat, 'altitude': alt}
            YYYY, altitude, azimuth, zen, jday, leafon, dectime, altmax = \
                Solweig_2015a_metdata_noload(self.metdata,location, UTC)
            # header = '%altitude azimuth altmax'
            # numformat = '%6.2f %6.2f %6.2f'
            # np.savetxt('C:/Users/xlinfr/Desktop/test.txt', np.hstack((altitude.T,azimuth.T,altmax.T)), fmt=numformat, header=header, comments='')

            # moved sunmapcreator inside worker!!
            # radmatI, radmatD, radmatR = sunmapcreator_2015a(self.metdata, altitude, azimuth,
            #                                                 onlyglobal, output, jday, albedo, location, zen)

            # delete following block: can't be used with PV version!!
            # if self.dlg.checkBoxUseIrradience.isChecked():
            #     if self.radmatfile is None:
            #         QMessageBox.critical(None, "Error", "Specify file for sky irradiance file")
            #         return
            #     else:
            #         metout = np.zeros((145, 4))
            #         metout[:, 0] = radmatI[:, 0]
            #         metout[:, 1] = radmatI[:, 1]
            #         metout[:, 2] = radmatI[:, 2]
            #         metout[:, 3] = radmatD[:, 2]
            #         # metout[:, 4] = radmatR[:, 2]
            #         header = '%altitude azimuth radI radD'
            #         numformat = '%6.2f %6.2f %6.2f %6.2f'
            #         np.savetxt(self.radmatfile, metout, fmt=numformat, header=header, comments='')

            building_slope, building_aspect = get_ders(self.dsm, self.scale)
            # np.savetxt("slope.txt", building_slope, fmt="%.2f", comments='')
            # np.savetxt("aspect.txt", building_aspect, fmt="%.2f", comments='')
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

            leng_met_ok = np.logical_and((self.metdata[:, 14] > 0), (altitude > 2)).sum()  # G and alt > 0
            # self.dlg.progressBar.setRange(0, 145 * (1 + 2 * len(self.metdata[:, 0])))
            self.dlg.progressBar.setRange(0, 145 + (2 * 145 * leng_met_ok) + len(self.metdata[:, 0]) - leng_met_ok)

            self.startWorker(self.dsm, self.scale, building_slope, building_aspect, voxelheight, sizey, sizex,
                             self.vegdsm, self.vegdsm2, self.wheight, self.waspect, self.albedoRaster, albedo, psi,
                             self.metdata, altitude, azimuth, onlyglobal, output, jday, location, zen,
                             self.usevegdem, calc_month, self.dlg, pvmodel, celltemp,
                             self.folderPath)

    def startWorker(self, dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex, vegdsm, vegdsm2,
                    wheight, waspect, albedo_raster, albedo, psi, metdata, altitude, azimuth, onlyglobal, output, jday,
                    location, zen, usevegdem, calc_month, dlg, pvm, tcel, output_folder):
        # create a new worker instance
        worker = Worker(dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex, vegdsm, vegdsm2,
                        wheight, waspect, albedo_raster, albedo, psi, metdata, altitude, azimuth, onlyglobal, output, jday,
                        location, zen, usevegdem, calc_month, dlg, pvm, tcel, output_folder)

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
            EnergyyearroofI = ret["EnergyyearroofI"]
            EnergyyearroofD = ret["EnergyyearroofD"]
            EnergyyearroofR = ret["EnergyyearroofR"]

            Energyyearwall = ret["PVEnergyyearwall"]
            EnergyyearwallI = ret["EnergyyearwallI"]
            EnergyyearwallD = ret["EnergyyearwallD"]
            EnergyyearwallR = ret["EnergyyearwallR"]
            vegdata = ret["vegdata"]
            # layer, total_area = ret
            # ### folder paths must be <string> for testing!!
            saveraster(self.gdal_dsm, str(self.folderPath[0]) + '/dsm.tif', self.dsm)
            filenameroof = str(self.folderPath[0]) + '/PVEnergyyearroof.tif'
            saveraster(self.gdal_dsm, filenameroof, Energyyearroof)
            #
            filenameroof = str(self.folderPath[0]) + '/EnergyyearroofI.tif'
            saveraster(self.gdal_dsm, filenameroof, EnergyyearroofI)
            #
            filenameroof = str(self.folderPath[0]) + '/EnergyyearroofD.tif'
            saveraster(self.gdal_dsm, filenameroof, EnergyyearroofD)
            #
            filenameroof = str(self.folderPath[0]) + '/EnergyyearroofR.tif'
            saveraster(self.gdal_dsm, filenameroof, EnergyyearroofR)

            filenamewall = str(self.folderPath[0]) + '/PVEnergyyearwall.txt'
            header = '%row col irradiance'
            numformat = '%4d %4d ' + '%.4E ' * (Energyyearwall.shape[1] - 2)    # format origina: %6.2f instead of %.4E
            np.savetxt(filenamewall, Energyyearwall, fmt=numformat, header=header, comments='')
            #
            filenamewall = str(self.folderPath[0]) + '/EnergyyearwallI.txt'
            header = '%row col irradiance'
            numformat = '%4d %4d ' + '%.4E ' * (EnergyyearwallI.shape[1] - 2)    # format origina: %6.2f instead of %.4E
            np.savetxt(filenamewall, EnergyyearwallI, fmt=numformat, header=header, comments='')
            #
            filenamewall = str(self.folderPath[0]) + '/EnergyyearwallD.txt'
            header = '%row col irradiance'
            numformat = '%4d %4d ' + '%.4E ' * (EnergyyearwallD.shape[1] - 2)    # format origina: %6.2f instead of %.4E
            np.savetxt(filenamewall, EnergyyearwallD, fmt=numformat, header=header, comments='')
            #
            filenamewall = str(self.folderPath[0]) + '/EnergyyearwallR.txt'
            header = '%row col irradiance'
            numformat = '%4d %4d ' + '%.4E ' * (EnergyyearwallR.shape[1] - 2)    # format origina: %6.2f instead of %.4E
            np.savetxt(filenamewall, EnergyyearwallR, fmt=numformat, header=header, comments='')
            if self.usevegdem == 1:
                filenamewall = str(self.folderPath[0]) + '/Vegetationdata.txt'
                header = '%row col height'
                numformat = '%4d %4d %.4E'    #%6.2f'
                np.savetxt(filenamewall, vegdata, fmt=numformat, header=header, comments='')
            QMessageBox.information(None, "SEBEpv", "Calculation succesfully completed")
        else:
            # notify the user that something went wrong
            QMessageBox.information(None, "SEBEpv",
                                    'Operations cancelled either by user or error. See the General tab '+
                                    'in Log Meassages Panel (speech bubble, lower right) for more information.')
        self.dlg.runButton.setText('Run')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.steps = 0
        self.dlg.progressBar.setValue(self.steps)
        self.dlg.pushButtonClose.setEnabled(True)

    def workerError(self, errorstring):
        QMessageBox.critical(None, "Error", errorstring)

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = "https://bitbucket.org/pvoptiray/umep-3d/wiki/Manual#!sebepv"
        webbrowser.open_new_tab(url)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sebepv = SEBEpv(app)
    sebepv.run()
    sys.exit(app.exec_())
