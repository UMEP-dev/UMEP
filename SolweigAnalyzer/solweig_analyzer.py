# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SolweigAnalyzer
                                 A QGIS plugin
 This plugin postprocess model output from the SOLWEIG model
                              -------------------
        begin                : 2016-10-21
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Fredrik Lindberg
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
# Initialize Qt resources from file resources.py
# import resources
# Import the code for the dialog
from solweig_analyzer_dialog import SolweigAnalyzerDialog
import os
import webbrowser
from ..Utilities.qgiscombomanager import *
from osgeo import gdal
from osgeo.gdalconst import *
import numpy as np
try:
    # import matplotlib
    # matplotlib.use("Agg")
    # import matplotlib.animation as manimation
    import matplotlib.pylab as plt
    import matplotlib.dates as dt
    from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange
    nomatplot = 0
except ImportError:
    nomatplot = 1
    pass


class SolweigAnalyzer:
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
            'SolweigAnalyzer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SolweigAnalyzerDialog()
        self.dlg.runButtonSpatial.clicked.connect(self.start_progress_spatial)
        self.dlg.runButtonPlot.clicked.connect(self.plotpoi)
        self.dlg.runButtonMovie.clicked.connect(self.movieshow)
        # self.dlg.runButtonPOI.clicked.connect(self.start_progress_poi)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonModelFolder.clicked.connect(self.folder_path_model)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path_save)
        self.dlg.comboBoxSpatialVariables.currentIndexChanged.connect(self.tmrtchosen)
        self.dlg.comboBoxSpatialVariables.currentIndexChanged.connect(self.moviescale)
        self.fileDialog = QFileDialog()

        self.layerComboManagerDSM = RasterLayerCombo(self.dlg.comboBox_buildings)
        RasterLayerCombo(self.dlg.comboBox_buildings, initLayer="")

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SOLWEIG Analyzer')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SolweigAnalyzer')
        # self.toolbar.setObjectName(u'SolweigAnalyzer')

        self.timelist = []
        self.tmrtPresent = 0
        self.kdownPresent = 0
        self.kupPresent = 0
        self.ldownPresent = 0
        self.lupPresent = 0
        self.shadowPresent = 0
        self.POIPresent = 0
        self.posAll = []
        self.posDay = []
        self.posNight = []
        self.posSpecMean = []
        self.posSpecMax = []
        self.posSpecMin = []
        self.l = None
        self.var = None
        self.varpoi1 = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('SolweigAnalyzer', message)


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
        icon_path = ':/plugins/SolweigAnalyzer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SOLWEIG Analyzer'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def folder_path_model(self):
        self.fileDialog.setFileMode(4)  # only folders
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textModelFolder.setText(self.folderPath[0])

            self.l = os.listdir(self.folderPath[0])
            index = 0
            for file in self.l:
                if file.startswith("Tmrt_") and file.endswith(".tif"):
                    self.tmrtPresent = 1
                if file.startswith("Kdown_") and file.endswith(".tif"):
                    self.kdownPresent = 1
                if file.startswith("Kup_") and file.endswith(".tif"):
                    self.kupPresent = 1
                if file.startswith("Ldown_") and file.endswith(".tif"):
                    self.ldownPresent = 1
                if file.startswith("Lup_") and file.endswith(".tif"):
                    self.lupPresent = 1
                if file.startswith("Shadow_") and file.endswith(".tif"):
                    self.shadowPresent = 1
                if file.endswith('N.tif') or file.endswith('D.tif'):
                    self.timelist.append(file[-9:-5])
                if file.startswith("POI_"):
                    self.POIPresent = 1
                    self.dlg.comboBox_POI.addItem(file[4:-4])
                    self.dlg.comboBox_POI_2.addItem(file[4:-4])
                index += 1

            l = sorted(list(set(self.timelist)))
            self.dlg.comboBoxSpecificMean.addItems(l)
            self.dlg.comboBoxSpecificMax.addItems(l)
            self.dlg.comboBoxSpecificMin.addItems(l)

            if self.tmrtPresent == 1:
                self.dlg.comboBoxSpatialVariables.addItem('Tmrt')
            if self.kdownPresent == 1:
                self.dlg.comboBoxSpatialVariables.addItem('Kdown')
            if self.kupPresent == 1:
                self.dlg.comboBoxSpatialVariables.addItem('Kup')
            if self.ldownPresent == 1:
                self.dlg.comboBoxSpatialVariables.addItem('Ldown')
            if self.lupPresent == 1:
                self.dlg.comboBoxSpatialVariables.addItem('Lup')
            if self.shadowPresent == 1:
                self.dlg.comboBoxSpatialVariables.addItem('Shadow')

            if self.tmrtPresent == 1 or self.kdownPresent == 1 or self.kupPresent == 1 or self.ldownPresent == 1 or \
                            self.lupPresent == 1 or self.shadowPresent == 1:
                self.dlg.pushButtonSave.setEnabled(1)
                self.dlg.runButtonMovie.setEnabled(1)
            if self.POIPresent == 1:
                self.dlg.runButtonPlot.setEnabled(1)
                self.dlg.spinBoxMovieMin.setEnabled(1)
                self.dlg.spinBoxMovieMax.setEnabled(1)

    def tmrtchosen(self):
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Tmrt':
            self.dlg.checkboxTmrtHighRisk.setEnabled(1)
            self.dlg.checkboxTmrtLowRisk.setEnabled(1)
            self.dlg.doubleSpinBoxTmrtHighRisk.setEnabled(1)
            self.dlg.doubleSpinBoxTmrtLowRisk.setEnabled(1)
        else:
            self.dlg.checkboxTmrtHighRisk.setEnabled(0)
            self.dlg.checkboxTmrtLowRisk.setEnabled(0)
            self.dlg.doubleSpinBoxTmrtHighRisk.setEnabled(0)
            self.dlg.doubleSpinBoxTmrtLowRisk.setEnabled(0)

    def moviescale(self):
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Tmrt':
            self.dlg.spinBoxMovieMin.setValue(-10)
            self.dlg.spinBoxMovieMax.setValue(70)
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Kdown':
            self.dlg.spinBoxMovieMin.setValue(0)
            self.dlg.spinBoxMovieMax.setValue(1000)
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Kup':
            self.dlg.spinBoxMovieMin.setValue(0)
            self.dlg.spinBoxMovieMax.setValue(200)
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Ldown':
            self.dlg.spinBoxMovieMin.setValue(300)
            self.dlg.spinBoxMovieMax.setValue(500)
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Lup':
            self.dlg.spinBoxMovieMin.setValue(300)
            self.dlg.spinBoxMovieMax.setValue(600)
        if self.dlg.comboBoxSpatialVariables.currentText() == 'Shadow':
            self.dlg.spinBoxMovieMin.setValue(0)
            self.dlg.spinBoxMovieMax.setValue(1)

    def folder_path_save(self):
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathSave = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPathSave[0])
            self.dlg.runButtonSpatial.setEnabled(1)

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def plotpoi(self):
        self.varpoi1 = self.dlg.comboBox_POI.currentText()

        if self.dlg.comboBox_POI.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No POI is selected")
            return

        data1 = np.loadtxt(self.folderPath[0] + '/POI_' + self.varpoi1 + '.txt', skiprows=1)
        varpos = [5, 6, 9, 7, 8, 10, 11, 16, 17, 22, 23, 24, 25, 26, 27, 28, 29]
        wm2 = '$W$'' ''$m ^{-2}$'
        degC = '$^{o}C$'
        deg = '$Degrees(^{o})$'
        frac = ''
        varunit = [deg, deg, wm2, wm2, wm2, wm2, wm2, wm2, wm2, degC, degC, frac, frac, degC, wm2, frac, frac]

        datenum_yy = np.zeros(data1.shape[0])
        for i in range(0, data1.shape[0]):  # making date number
            datenum_yy[i] = dt.date2num(dt.datetime.datetime(int(data1[i, 0]), 1, 1))

        dectime = datenum_yy + data1[:, 4]

        dates = dt.num2date(dectime)
        # QMessageBox.critical(self.dlg, "data", str(dates))

        if not self.dlg.checkboxUsePOI.isChecked():
            # One variable
            id = self.dlg.comboBox_POIVariable.currentIndex() - 1

            if self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No plotting variable is selected")
                return

            plt.figure(1, figsize=(15, 7), facecolor='white')
            plt.title(self.dlg.comboBox_POIVariable.currentText())
            ax1 = plt.subplot(1, 1, 1)
            ax1.plot(dates, data1[:, varpos[id]], 'r', label='$' + self.dlg.comboBox_POIVariable.currentText() + '$')
            plt.setp(plt.gca().xaxis.get_majorticklabels(),'rotation', 45)
            ax1.grid(True)

            if (np.max(data1[:, 1]) - np.min(data1[:, 1])) > 1:
                ax1.xaxis.set_major_locator(DayLocator())
                ax1.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            else:
                ax1.xaxis.set_minor_locator(HourLocator())
                ax1.xaxis.set_major_formatter(DateFormatter("%H:%M"))

            ax1.set_ylabel(varunit[id], fontsize=14)
            ax1.set_xlabel('Time', fontsize=14)
        else:
            # Two variables
            id1 = self.dlg.comboBox_POIVariable.currentIndex() - 1
            id2 = self.dlg.comboBox_POIVariable_2.currentIndex() - 1
            if self.dlg.comboBox_POIVariable_2.currentText() == 'Not Specified' or self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No plotting variable is selected")
                return
            self.varpoi2 = self.dlg.comboBox_POI_2.currentText()
            data2 = np.loadtxt(self.folderPath[0] + '/POI_' + self.varpoi2 + '.txt', skiprows=1)

            if self.dlg.checkboxScatterbox.isChecked():
                plt.figure(1, figsize=(11, 11), facecolor='white')
                plt.title(self.dlg.comboBox_POIVariable.currentText() + '(' + self.varpoi1 + ') vs ' + self.dlg.comboBox_POIVariable_2.currentText() + '(' + self.varpoi2 + ')')
                ax1 = plt.subplot(1, 1, 1)
                ax1.plot(data1[:, varpos[id1]], data2[:, varpos[id2]], "k.")
                ax1.set_ylabel(varunit[id2], fontsize=14)
                ax1.set_xlabel(varunit[id1], fontsize=14)
            else:
                plt.figure(1, figsize=(15, 7), facecolor='white')
                plt.title(self.dlg.comboBox_POIVariable.currentText() + '(' + self.varpoi1 + ') and ' + self.dlg.comboBox_POIVariable_2.currentText() + '(' + self.varpoi2 + ')')
                ax1 = plt.subplot(1, 1, 1)
                if not varunit[id1] == varunit[id2]:
                    ax2 = ax1.twinx()
                    ax1.plot(dates, data1[:, varpos[id1]], 'r', label='$' + self.dlg.comboBox_POIVariable.currentText() + ' (' + self.varpoi1 + ')$')
                    ax1.legend(loc=1)
                    ax2.plot(dates, data2[:, varpos[id2]], 'b', label='$' + self.dlg.comboBox_POIVariable_2.currentText() + ' (' + self.varpoi2 + ')$')
                    ax2.legend(loc=2)
                    ax1.set_ylabel(varunit[id1], color='r', fontsize=14)
                    ax2.set_ylabel(varunit[id2], color='b', fontsize=14)
                else:
                    ax1.plot(dates, data1[:, varpos[id1]], 'r', label='$' + self.dlg.comboBox_POIVariable.currentText() + ' (' + self.varpoi1 + ')$')
                    ax1.plot(dates, data2[:, varpos[id2]], 'b', label='$' + self.dlg.comboBox_POIVariable_2.currentText() + ' (' + self.varpoi2 + ')$')
                    ax1.legend(loc=2)
                    ax1.set_ylabel(varunit[id1], fontsize=14)

                plt.setp(plt.gca().xaxis.get_majorticklabels(), 'rotation', 45)
                ax1.grid(True)

                if (np.max(data1[:, 1]) - np.min(data1[:, 1])) > 1:
                    ax1.xaxis.set_major_locator(DayLocator())
                    ax1.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d %H:%M"))
                else:
                    ax1.xaxis.set_minor_locator(HourLocator())
                    ax1.xaxis.set_major_formatter(DateFormatter("%H:%M"))

                ax1.set_xlabel('Time', fontsize=14)
        plt.show()

    def movieshow(self):
        self.var = self.dlg.comboBoxSpatialVariables.currentText()

        if self.var == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No variable is selected")
            return

        cmin = self.dlg.spinBoxMovieMin.value()
        cmax = self.dlg.spinBoxMovieMax.value()

        plt.figure(1, figsize=(9, 9), facecolor='white')
        plt.ion()
        index = 0
        for file in self.l:
            if file.startswith(self.var + '_') and file.endswith('.tif'):
                self.posAll.append(index)
            index += 1
        # QMessageBox.critical(self.dlg, "Error", str(self.posAll))

        index = 0
        for i in self.posAll:
            gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
            grid = gdal_dsm.ReadAsArray().astype(np.float)
            plt.imshow(grid, clim=(cmin, cmax))
            plt.title(self.l[i])
            if index == 0:
                plt.colorbar(orientation='horizontal')
            plt.show()
            plt.pause(0.5)
            index += 1

        del self.posAll[:]

    def start_progress_spatial(self):
        self.var = self.dlg.comboBoxSpatialVariables.currentText()

        if self.var == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No variable is selected")
            return

        index = 0
        for file in self.l:
            if file.startswith(self.var + '_'):
                self.posAll.append(index)
                if file.endswith('D.tif'):
                    self.posDay.append(index)
                if file.endswith('N.tif'):
                    self.posNight.append(index)
                if file[-9:-5] == self.dlg.comboBoxSpecificMean.currentText():
                    self.posSpecMean.append(index)
                if file[-9:-5] == self.dlg.comboBoxSpecificMax.currentText():
                    self.posSpecMax.append(index)
                if file[-9:-5] == self.dlg.comboBoxSpecificMin.currentText():
                    self.posSpecMin.append(index)
            index += 1

        # Exclude buildings
        if self.dlg.checkboxExcludeBuildings.isChecked():
            dsmlayer = self.layerComboManagerDSM.getLayer()

            if dsmlayer is None:
                QMessageBox.critical(self.dlg, "Error", "No valid raster layer is selected")
                return

            if self.folderPath[0] is None:
                QMessageBox.critical(self.dlg, "Error", "No building grid specified")
            else:
                dsmlayer = self.layerComboManagerDSM.getLayer()

                if dsmlayer is None:
                    QMessageBox.critical(self.dlg, "Error", "No valid building raster layer is selected")
                    return

                provider = dsmlayer.dataProvider()
                filepath_dsm = str(provider.dataSourceUri())
                self.gdal_dsm = gdal.Open(filepath_dsm)
                self.build = self.gdal_dsm.ReadAsArray().astype(np.float)
                geotransform = self.gdal_dsm.GetGeoTransform()
                self.scale = 1 / geotransform[1]

        # Diurnal mean
        if self.dlg.checkboxMean.isChecked():
            index = 0
            for i in self.posAll:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    gridall = np.zeros((sizex, sizey))
                gridall += grid
                index += 1

            gridall = gridall / index

            if self.dlg.checkboxExcludeBuildings.isChecked():
                gridall[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_diurnal_mean.tif', gridall)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_diurnal_mean.tif')

        # Daytime mean
        if self.dlg.checkboxDayMean.isChecked():
            index = 0
            for i in self.posDay:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey))
                daymean += grid
                index += 1

            daymean = daymean / index

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_daytime_mean.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_daytime_mean.tif')

        # Nighttime mean
        if self.dlg.checkboxNightMean.isChecked():
            index = 0
            for i in self.posNight:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey))
                daymean += grid
                index += 1

            daymean = daymean / index

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_nighttime_mean.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_nighttime_mean.tif')

        # Max
        if self.dlg.checkboxMax.isChecked():
            index = 0
            for i in self.posAll:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    gridall = np.zeros((sizex, sizey)) - 100.
                gridall = np.maximum(gridall, grid)
                index += 1

            if self.dlg.checkboxExcludeBuildings.isChecked():
                gridall[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_max.tif', gridall)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_max.tif')

        # Min
        if self.dlg.checkboxMin.isChecked():
            index = 0
            for i in self.posAll:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    gridall = np.zeros((sizex, sizey)) + 100.
                gridall = np.minimum(gridall, grid)
                index += 1

            if self.dlg.checkboxExcludeBuildings.isChecked():
                gridall[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_min.tif', gridall)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_min.tif')

        # Specific time mean
        if not self.dlg.comboBoxSpecificMean.currentText() == 'Not Specified':
            index = 0
            for i in self.posSpecMean:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey))
                daymean += grid
                index += 1

            daymean = daymean / index

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_' +
                            self.dlg.comboBoxSpecificMean.currentText() + '_mean.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var +'_' + self.dlg.comboBoxSpecificMean.currentText() + '_mean.tif')

        # Specific time max
        if not self.dlg.comboBoxSpecificMax.currentText() == 'Not Specified':
            index = 0
            for i in self.posSpecMax:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey)) - 100.
                daymean = np.maximum(daymean, grid)
                index += 1

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_' + self.dlg.comboBoxSpecificMax.currentText() + '_max.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_' + self.dlg.comboBoxSpecificMax.currentText() + '_max.tif')

        # Specific time min
        if not self.dlg.comboBoxSpecificMin.currentText() == 'Not Specified':
            index = 0
            for i in self.posSpecMin:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey)) + 100.
                daymean = np.minimum(daymean, grid)
                index += 1

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/' + self.var + '_' +
                            self.dlg.comboBoxSpecificMin.currentText() + '_min.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/' + self.var + '_' + self.dlg.comboBoxSpecificMin.currentText() + '_min.tif')

        # Tmrt threshold above
        if self.dlg.checkboxTmrtHighRisk.isChecked():
            index = 0
            for i in self.posAll:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey))

                tempgrid = (grid > self.dlg.doubleSpinBoxTmrtHighRisk.value()).astype(float)
                daymean = daymean + tempgrid
                index += 1

            daymean = daymean / index

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/PercentOfTime' + self.var + 'Above_' +
                            str(self.dlg.doubleSpinBoxTmrtHighRisk.value()) + '.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/PercentOfTime' + self.var + 'Above_' +
                            str(self.dlg.doubleSpinBoxTmrtHighRisk.value()) + '.tif')

        # Tmrt threshold below
        if self.dlg.checkboxTmrtLowRisk.isChecked():
            index = 0
            for i in self.posAll:
                gdal_dsm = gdal.Open(self.folderPath[0] + '/' + self.l[i])
                grid = gdal_dsm.ReadAsArray().astype(np.float)
                if index == 0:
                    sizex = grid.shape[0]
                    sizey = grid.shape[1]
                    daymean = np.zeros((sizex, sizey))
                tempgrid = (grid < self.dlg.doubleSpinBoxTmrtLowRisk.value()).astype(float)
                daymean = daymean + tempgrid
                index += 1

            daymean = daymean / index

            if self.dlg.checkboxExcludeBuildings.isChecked():
                daymean[self.build == 0] = -9999

            self.saveraster(gdal_dsm, self.folderPathSave[0] + '/PercentOfTime' + self.var + 'Below_' +
                            str(self.dlg.doubleSpinBoxTmrtLowRisk.value()) + '.tif', daymean)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                self.intoCanvas(self.folderPathSave[0] + '/PercentOfTime' + self.var + 'Below_' +
                                str(self.dlg.doubleSpinBoxTmrtLowRisk.value()) + '.tif')

        del self.posAll[:]

    def intoCanvas(self, fileName):
        # load height result into canvas
        rlayer = self.iface.addRasterLayer(fileName)

        if hasattr(rlayer, "setCacheImage"):
            rlayer.setCacheImage(None)
        rlayer.triggerRepaint()

    def start_progress_poi(self):
        self.steps = 0

    def help(self):
        url = 'http://www.urban-climate.net/umep/UMEP_Manual#Outdoor_Thermal_Comfort:_SOLWEIG_Analyzer'
        webbrowser.open_new_tab(url)

    def saveraster(self, gdal_data, filename, raster):
        rows = gdal_data.RasterYSize
        cols = gdal_data.RasterXSize

        outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
        outBand = outDs.GetRasterBand(1)

        # write the data
        outBand.WriteArray(raster, 0, 0)
        # flush data to disk, set the NoData value and calculate stats
        outBand.FlushCache()
        outBand.SetNoDataValue(-9999)

        # georeference the image and set the projection
        outDs.SetGeoTransform(gdal_data.GetGeoTransform())
        outDs.SetProjection(gdal_data.GetProjection())