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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread, QUrl
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from svf_calculator_dialog import SkyViewFactorCalculatorDialog
import os.path
import numpy as np
from ..Utilities.qgiscombomanager import *
from osgeo import gdal
import Skyviewfactor4d as svf
from svfworker import Worker
from svfvegworker import VegWorker
from osgeo.gdalconst import *
import webbrowser
import zipfile
import sys

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
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.checkBoxUseVeg.toggled.connect(self.text_enable)
        self.dlg.checkBoxTrunkExist.toggled.connect(self.text_enable2)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Sky View Factor Calculator')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SkyViewFactorCalculator')
        # self.toolbar.setObjectName(u'SkyViewFactorCalculator')

        self.layerComboManagerDSM = RasterLayerCombo(self.dlg.comboBox_dsm)
        RasterLayerCombo(self.dlg.comboBox_dsm, initLayer="")
        self.layerComboManagerVEGDSM = RasterLayerCombo(self.dlg.comboBox_vegdsm)
        RasterLayerCombo(self.dlg.comboBox_vegdsm, initLayer="")
        self.layerComboManagerVEGDSM2 = RasterLayerCombo(self.dlg.comboBox_vegdsm2)
        RasterLayerCombo(self.dlg.comboBox_vegdsm2, initLayer="")

        self.thread = None
        self.worker = None
        self.vegthread = None
        self.vegworker = None
        self.svftotal = None
        self.folderPath = None
        self.usevegdem = None
        self.vegdsm = None
        self.vegdsm2 = None
        self.svfbu = None
        self.dsm = None
        self.scale = None
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

    def text_enable(self):
        if self.dlg.checkBoxUseVeg.isChecked():
            self.dlg.label_2.setEnabled(True)

        else:
            self.dlg.label_2.setEnabled(False)

    def text_enable2(self):
        if self.dlg.checkBoxTrunkExist.isChecked():
            self.dlg.label_3.setEnabled(True)
        else:
            self.dlg.label_3.setEnabled(False)

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def startWorker(self, dsm, scale, dlg):
        # create a new worker instance
        worker = Worker(dsm, scale, dlg)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.pushButton.setEnabled(False)

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

    def startVegWorker(self, dsm, scale, vegdsm, vegdsm2, dlg):
        # create a new worker instance
        vegworker = VegWorker(dsm, scale, vegdsm, vegdsm2, dlg)

        # self.dlg.runButton.setText('Cancel')
        # self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(vegworker.kill)

        # start the worker in a new thread
        vegthread = QThread(self.dlg)
        vegworker.moveToThread(vegthread)
        vegworker.finished.connect(self.vegWorkerFinished)
        vegworker.error.connect(self.vegWorkerError)
        vegworker.progress.connect(self.progress_update)
        vegthread.started.connect(vegworker.run)
        vegthread.start()
        self.vegthread = vegthread
        self.vegworker = vegworker

    def workerFinished(self, ret):
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # remove widget from message bar
        # self.iface.messageBar().popWidget(self.messageBar)

        # temporary fix for mac, ISSUE #15
        pf = sys.platform
        if pf == 'darwin' or pf == 'linux2':
            if not os.path.exists(self.folderPath[0]):
                os.makedirs(self.folderPath[0])

        if ret is not None:
            # report the result
            # layer, total_area = ret
            # self.iface.messageBar().pushMessage('The total area of {name} is {area}.'.format(name=layer.name(), area=total_area))
            self.svfbu = ret["svf"]
            svfbuE = ret["svfE"]
            svfbuS = ret["svfS"]
            svfbuW = ret["svfW"]
            svfbuN = ret["svfN"]

            svfbuname = ret.keys()

            # svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + svfbuname[0] + '.tif', self.svfbu)
            # svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + svfbuname[1] + '.tif', svfbuE)
            # svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + svfbuname[2] + '.tif', svfbuS)
            # svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + svfbuname[3] + '.tif', svfbuW)
            # svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + svfbuname[4] + '.tif', svfbuN)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svf.tif', self.svfbu)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfE.tif', svfbuE)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfS.tif', svfbuS)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfW.tif', svfbuW)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfN.tif', svfbuN)

            if os.path.isfile(self.folderPath[0] + '/' + 'svfs.zip'):
                os.remove(self.folderPath[0] + '/' + 'svfs.zip')

            zip = zipfile.ZipFile(self.folderPath[0] + '/' + 'svfs.zip', 'a')
            zip.write(self.folderPath[0] + '/' + 'svf.tif', 'svf.tif')
            zip.write(self.folderPath[0] + '/' + 'svfE.tif', 'svfE.tif')
            zip.write(self.folderPath[0] + '/' + 'svfS.tif', 'svfS.tif')
            zip.write(self.folderPath[0] + '/' + 'svfW.tif', 'svfW.tif')
            zip.write(self.folderPath[0] + '/' + 'svfN.tif', 'svfN.tif')
            zip.close()

            os.remove(self.folderPath[0] + '/' + 'svf.tif')
            os.remove(self.folderPath[0] + '/' + 'svfE.tif')
            os.remove(self.folderPath[0] + '/' + 'svfS.tif')
            os.remove(self.folderPath[0] + '/' + 'svfW.tif')
            os.remove(self.folderPath[0] + '/' + 'svfN.tif')

            if self.usevegdem == 0:
                self.svftotal = self.svfbu

                filename = self.folderPath[0] + '/' + 'SkyViewFactor' + '.tif'

                svf.saveraster(self.gdal_dsm, filename, self.svftotal)

                if self.dlg.checkBoxIntoCanvas.isChecked():
                    rlayer = self.iface.addRasterLayer(filename)

                    # Set opacity
                    rlayer.renderer().setOpacity(0.5)

                    # Trigger a repaint
                    if hasattr(rlayer, "setCacheImage"):
                        rlayer.repaintRequested.emit()
                        #rlayer.setCacheImage(None)
                    rlayer.triggerRepaint()

                QMessageBox.information(self.iface.mainWindow(), "Sky View Factor Calculator", "SVF grid(s) successfully generated")
                self.dlg.runButton.setText('Run')
                self.dlg.runButton.clicked.disconnect()
                self.dlg.runButton.clicked.connect(self.start_progress)
                self.dlg.pushButton.setEnabled(True)
            #else:
                #self.startVegWorker(self.dsm, self.scale, self.vegdsm, self.vegdsm2, self.dlg)

        else:
            # notify the user that something went wrong
            self.iface.messageBar().pushMessage('Operations cancelled either by user or error. See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.', level=QgsMessageBar.CRITICAL, duration=3)
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)


    def vegWorkerFinished(self, ret):
        # clean up the worker and thread
        #self.vegworker.deleteLater()
        self.vegthread.quit()
        self.vegthread.wait()
        self.vegthread.deleteLater()

        # temporary fix for mac, ISSUE #15
        pf = sys.platform
        if pf == 'darwin' or pf == 'linux2':
            if not os.path.exists(self.folderPath[0]):
                os.makedirs(self.folderPath[0])

        if ret is not None:
            # report the result
            #layer, total_area = ret
            #self.iface.messageBar().pushMessage('The total area of {name} is {area}.'.format(name=layer.name(), area=total_area))
            svfveg = ret["svfveg"]
            svfEveg = ret["svfEveg"]
            svfSveg = ret["svfSveg"]
            svfWveg = ret["svfWveg"]
            svfNveg = ret["svfNveg"]
            svfaveg = ret["svfaveg"]
            svfEaveg = ret["svfEaveg"]
            svfSaveg = ret["svfSaveg"]
            svfWaveg = ret["svfWaveg"]
            svfNaveg = ret["svfNaveg"]

            svfvegname = ret.keys()

            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfveg.tif', svfveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfEveg.tif', svfEveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfSveg.tif', svfSveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfWveg.tif', svfWveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfNveg.tif', svfNveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfaveg.tif', svfaveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfEaveg.tif', svfEaveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfSaveg.tif', svfSaveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfWaveg.tif', svfWaveg)
            svf.saveraster(self.gdal_dsm, self.folderPath[0] + '/' + 'svfNaveg.tif', svfNaveg)

            zip = zipfile.ZipFile(self.folderPath[0] + '/' + 'svfs.zip', 'a')
            zip.write(self.folderPath[0] + '/' + 'svfveg.tif', 'svfveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfEveg.tif', 'svfEveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfSveg.tif', 'svfSveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfWveg.tif', 'svfWveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfNveg.tif', 'svfNveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfaveg.tif', 'svfaveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfEaveg.tif', 'svfEaveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfSaveg.tif', 'svfSaveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfWaveg.tif', 'svfWaveg.tif')
            zip.write(self.folderPath[0] + '/' + 'svfNaveg.tif', 'svfNaveg.tif')
            zip.close()

            os.remove(self.folderPath[0] + '/' + 'svfveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfEveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfSveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfWveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfNveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfaveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfEaveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfSaveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfWaveg.tif')
            os.remove(self.folderPath[0] + '/' + 'svfNaveg.tif')

            trans = self.dlg.spinBoxTrans.value() / 100.0

            self.svftotal = (self.svfbu-(1-svfveg)*(1-trans))
            filename = self.folderPath[0] + '/' + 'SkyViewFactor' + '.tif'
            svf.saveraster(self.gdal_dsm, filename, self.svftotal)

            if self.dlg.checkBoxIntoCanvas.isChecked():
                rlayer = self.iface.addRasterLayer(filename)
                # Set opacity
                rlayer.renderer().setOpacity(0.5)
                # Trigger a repaint
                if hasattr(rlayer, "setCacheImage"):
                    #rlayer.setCacheImage(None)
                    rlayer.repaintRequested.emit()
                rlayer.triggerRepaint()

            QMessageBox.information(self.iface.mainWindow(), "Sky View Factor Calculator", "SVF grid(s) successfully generated")

            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton.setEnabled(True)

        else:
            # notify the user that something went wrong
            self.iface.messageBar().pushMessage('Operations cancelled either by user or error. See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.', level=QgsMessageBar.CRITICAL, duration=3)
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)

    def workerError(self, errorstring):
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)

    def vegWorkerError(self, errorstring):
        #QgsMessageLog.logMessage('Vegetation Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)
        #QMessageBox.information(None, "Sky View Factor Calculator", str(e))

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def start_progress(self):
        self.steps = 0
        if self.folderPath is None:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "No save folder selected")

        else:
        #self.dlg.textOutput.setText(self.folderPath[0])
            dsmlayer = self.layerComboManagerDSM.getLayer()

            if dsmlayer is None:
                    QMessageBox.critical(self.iface.mainWindow(), "Error", "No valid raster layer is selected")
                    return

            provider = dsmlayer.dataProvider()
            filepath_dsm = str(provider.dataSourceUri())
            self.gdal_dsm = gdal.Open(filepath_dsm)
            self.dsm = self.gdal_dsm.ReadAsArray().astype(np.float)
            sizex = self.dsm.shape[0]
            sizey = self.dsm.shape[1]
            geotransform = self.gdal_dsm.GetGeoTransform()
            self.scale = 1 / geotransform[1]

            if (sizex * sizey) > 250000 and (sizex * sizey) <= 1000000:
                QMessageBox.warning(self.iface.mainWindow(), "Semi lage grid", "This process will take a couple of minutes. "
                                                        "Go and make yourself a cup of tea...")

            if (sizex * sizey) > 1000000 and (sizex * sizey) <= 4000000:
                QMessageBox.warning(self.iface.mainWindow(), "Large grid", "This process will take some time. "
                                                        "Go for lunch...")

            if (sizex * sizey) > 4000000 and (sizex * sizey) <= 16000000:
                QMessageBox.warning(self.iface.mainWindow(), "Very large grid", "This process will take a long time. "
                                                        "Go for lunch and for a walk...")

            if (sizex * sizey) > 16000000:
                QMessageBox.warning(self.iface.mainWindow(), "Huge grid", "This process will take a very long time. "
                                                        "Go home for the weekend or consider to tile your grid")

            if self.dlg.checkBoxUseVeg.isChecked():
                self.usevegdem = 1
                #trans = self.dlg.spinBoxTrans.value() / 100.0

                self.vegdsm = self.layerComboManagerVEGDSM.getLayer()

                if self.vegdsm is None:
                    QMessageBox.critical(None, "Error", "No valid vegetation DSM selected")
                    return

                # load raster
                gdal.AllRegister()
                provider = self.vegdsm.dataProvider()
                filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(filePathOld)
                self.vegdsm = dataSet.ReadAsArray().astype(np.float)

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
                    provider = self.vegdsm2.dataProvider()
                    filePathOld = str(provider.dataSourceUri())
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

            if self.usevegdem == 0:
                self.dlg.progressBar.setRange(0, 655)
            else:
                self.dlg.progressBar.setRange(0, 1310)

            if self.folderPath is 'None':
                QMessageBox.critical(None, "Error", "No selected folder")
                return
            else:

                #svfresult = svf.Skyviewfactor4d(dsm, scale, self.dlg)
                self.startWorker(self.dsm, self.scale, self.dlg)
                # svfbu = svfresult["svf"]
                # svfbuE = svfresult["svfE"]
                # svfbuS = svfresult["svfS"]
                # svfbuW = svfresult["svfW"]
                # svfbuW = svfresult["svfW"]
                # svfbuN = svfresult["svfN"]
                #
                # svfbuname = svfresult.keys()
                #
                # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[0] + '.tif', svfbu)
                # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[1] + '.tif', svfbuE)
                # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[2] + '.tif', svfbuS)
                # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[3] + '.tif', svfbuW)
                # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfbuname[4] + '.tif', svfbuN)

                if self.usevegdem == 1:
                    self.startVegWorker(self.dsm, self.scale, self.vegdsm, self.vegdsm2, self.dlg)
                    #svfvegresult = svf.Skyviewfactor4d_veg(dsm, scale, vegdsm, vegdsm2, self.dlg)
                    # svfveg = svfvegresult["svfveg"]
                    # svfEveg = svfvegresult["svfEveg"]
                    # svfSveg = svfvegresult["svfSveg"]
                    # svfWveg = svfvegresult["svfWveg"]
                    # svfNveg = svfvegresult["svfNveg"]
                    # svfaveg = svfvegresult["svfaveg"]
                    # svfEaveg = svfvegresult["svfEaveg"]
                    # svfSaveg = svfvegresult["svfSaveg"]
                    # svfWaveg = svfvegresult["svfWaveg"]
                    # svfNaveg = svfvegresult["svfNaveg"]
                    #
                    # svfvegname = svfvegresult.keys()
                    #
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[0] + '.tif', svfveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[1] + '.tif', svfEveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[2] + '.tif', svfSveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[3] + '.tif', svfWveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[4] + '.tif', svfNveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[5] + '.tif', svfaveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[6] + '.tif', svfEaveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[7] + '.tif', svfSaveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[8] + '.tif', svfWaveg)
                    # svf.saveraster(gdal_dsm, self.folderPath[0] + '/' + svfvegname[9] + '.tif', svfNaveg)
                    #
                    # svftotal = (svfbu-(1-svfveg)*(1-trans))
                #else:
                    #svftotal = svfbu

                #filename = self.folderPath[0] + '/' + 'SkyViewFactor' + '.tif'

                #svf.saveraster(self.gdal_dsm, filename, self.svftotal)


            # self.iface.messageBar().pushMessage("ShadowGenerator", "Shadow grid(s) successfully generated")

            # load result into canvas

    def run(self):
        """Run method that performs all the real work"""
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = 'http://www.urban-climate.net/umep/UMEP_Manual#Urban_Geometry:_Sky_View_Factor_Calculator'
        # QDesktopServices.openUrl(QUrl(url))
        webbrowser.open_new_tab(url)


