# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WATCHData
                                 A QGIS plugin
 Downloads and process WATCH data for UMEP applications
                              -------------------
        begin                : 2016-07-08
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Andrew Mark Gabey
        email                : a.m.gabey@reading.ac.uk
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
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from PyQt4.QtCore import QThread
# from qgis.gui import QgsMessageBar
from qgis.gui import *
from qgis.core import *
from osgeo import osr, ogr
# Import the code for the dialog
from watch_dialog import WATCHDataDialog
import os.path
import webbrowser

from WFDEIDownloader.WFDEI_Interpolator import *
import datetime
from WatchWorker import WatchWorker

class WATCHData:
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
            'WATCHData_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = WATCHDataDialog()
        self.dlg.selectpoint.clicked.connect(self.select_point)
        # Check dependencies first

        # connections to buttons
        self.dlg.runButton.clicked.connect(self.start_progress) # Ensures "GO" button is enabled/disabled appropriately
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonRaw.clicked.connect(self.raw_path)
        self.dlg.pushButtonAH.clicked.connect(self.folderAH)
        self.dlg.pushButtonSave.clicked.connect(self.outfile)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)
        self.folderPathRaw = 'None'
        self.outputfile = 'None'
        self.folderPathAH = 'None'

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&WATCH data')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'WATCHData')
        # self.toolbar.setObjectName(u'WATCHData')

        # get reference to the canvas
        self.canvas = self.iface.mapCanvas()
        self.degree = 5.0
        self.point = None
        self.pointx = None
        self.pointy = None

        # #g pin tool
        self.pointTool = QgsMapToolEmitPoint(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)

        # Inflate mappings file if needed

        text_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'WFDEIDownloader/WFDEI-land-long-lat-height.txt')
        gzip_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'WFDEIDownloader/WFDEI-land-long-lat-height.txt.gz')
        try:
            a = open(text_file)
        except IOError,e:
            try:
                import gzip
                with gzip.open(gzip_file, 'rb') as zipFile:
                    a = zipFile.read()
                with open(text_file, 'wb') as outFile:
                    outFile.write(a)
            except Exception, e:
                QMessageBox.critical(None, 'ha', str(e))
                raise Exception('Could not locate mappings textfile, nor decompress its zipped copy')

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
        return QCoreApplication.translate('WATCHData', message)

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

        icon_path = ':/plugins/WATCHData/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&WATCH data'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        # del self.toolbar

    def select_point(self):  # Connected to "Secelct Point on Canves"
        self.canvas.setMapTool(self.pointTool)  # Calls a canvas click and create_point
        self.dlg.setEnabled(False)

    def create_point(self, point):  # Var kommer point ifran???
        # report map coordinates from a canvas click
        self.dlg.setEnabled(True)
        self.dlg.activateWindow()

        canvas = self.iface.mapCanvas()
        srs = canvas.mapSettings().destinationCrs()
        crs = str(srs.authid())
        # self.iface.messageBar().pushMessage("Coordinate selected", str(crs[5:]))
        old_cs = osr.SpatialReference()
        old_cs.ImportFromEPSG(int(crs[5:]))

        new_cs = osr.SpatialReference()
        new_cs.ImportFromEPSG(4326)

        transform = osr.CoordinateTransformation(old_cs, new_cs)

        latlon = ogr.CreateGeometryFromWkt('POINT (' + str(point.x()) + ' ' + str(point.y()) + ')')
        latlon.Transform(transform)

        self.dlg.textOutput_lon.setText(str(latlon.GetX()))
        self.dlg.textOutput_lat.setText(str(latlon.GetY()))

    def run(self):
        # Check the more unusual dependencies to prevent confusing errors later
        try:
            import pandas
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the pandas package '
                                                'to be installed. Please consult the FAQ in the manual for further information')
            return
        try:
            import ftplib
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the ftplib package '
                                                'to be installed. Please consult the FAQ in the manual for further information')
            return
        try:
            import scipy
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the scipy package '
                                                'to be installed. Please consult the FAQ in the manual for further information')
            return

        self.dlg.show()
        result = self.dlg.exec_()

    def raw_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathRaw = self.fileDialog.selectedFiles()
            self.dlg.textOutput_raw.setText(self.folderPathRaw[0])

    def outfile(self):
        outputfile = self.fileDialog.getSaveFileName(None, "Save File As:", None, "Text Files (*.txt)")
        # self.fileDialog.open()
        # result = self.fileDialog.exec_()
        if not outputfile == 'None':
            self.outputfile = outputfile
            self.dlg.textOutput.setText(self.outputfile)

    def folderAH(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathAH = self.fileDialog.selectedFiles()
            self.dlg.textOutput_AH.setText(self.folderPathAH[0])

    def help(self):
        url = "http://urban-climate.net/umep/UMEP_Manual#Meteorological_Data:_WATCH_data"
        webbrowser.open_new_tab(url)

    def start_progress(self):
        self.dlg.runButton.setEnabled(False)
        if self.folderPathRaw == 'None':
            QMessageBox.critical(None, "Error", "Specify the folder where the WATCH raw data is [to be] downloaded")
            self.dlg.runButton.setEnabled(True)
            return

        if self.outputfile == 'None':
            QMessageBox.critical(None, "Error", "Specify the extracted data file")
            self.dlg.runButton.setEnabled(True)
            return
        try:
            lat = float(self.dlg.textOutput_lat.text())
            if not (-90 < lat < 90):
                raise ValueError('Invalid WFDEI co-ordinates entered')
        except Exception,e:
            QMessageBox.critical(None, "Error", "Invalid latitude")
            self.dlg.runButton.setEnabled(True)
            return

        try:
            lon = float(self.dlg.textOutput_lon.text())
            if not (-180 < lon < 180):
                raise ValueError('Invalid WFDEI co-ordinates entered')
        except Exception,e:
            QMessageBox.critical(None, "Error", "Invalid longitude")
            self.dlg.runButton.setEnabled(True)
            return

        try:
            hgt = float(self.dlg.textOutput_hgt.text())
            if hgt<0:
                raise ValueError('negative site height entered')
        except Exception,e:
            QMessageBox.critical(None, "Error", "Invalid site height")
            self.dlg.runButton.setEnabled(True)
            return

        datestart = self.dlg.dateEditStart.text()
        datestart = datetime.datetime.strptime(datestart, '%Y-%m')

        dateend= self.dlg.dateEditEnd.text()
        dateend = datetime.datetime.strptime(dateend, '%Y-%m')

        rawdata = self.dlg.textOutput_raw.text()
        if not os.path.exists(rawdata):
            QMessageBox.critical(None, "Error", "Invalid download destination entered")
            self.dlg.runButton.setEnabled(True)
            return

        fileout = self.dlg.textOutput.text()
        if not os.path.exists(os.path.split(fileout)[0]):
            QMessageBox.critical(None, "Error", "Invalid output file location entered")
            self.dlg.runButton.setEnabled(True)
            return

        # Which files should be downloaded from WATCH for SUEWS?
        required_variables = ['LWdown_WFDEI', 'PSurf_WFDEI', 'Qair_WFDEI', 'Rainf_WFDEI_CRU', 'SWdown_WFDEI',
                              'Tair_WFDEI','Wind_WFDEI']

        # Notify the user how much space will be required, giving them a chance to free it up
        numMonths = max((dateend-datestart).days//30. + 1 if (dateend-datestart).days % 30. > 0 else 0, 1) # At least one month

        megPerFile = 80.0
        # Tell the user for their information

        dialog_string = 'Downloaded files will require approximately ' + str(int(numMonths * megPerFile * len(required_variables))) + 'MB of free space. Do you wish to continue?'
        reply = QMessageBox.question(None, 'Storage space needed', dialog_string, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            self.dlg.runButton.setEnabled(True)
            return

        UTC_offset_h = self.dlg.spinBoxUTC.value()
        input_AH_path = self.dlg.textOutput_AH.text()
        rainAmongN = self.dlg.spinBoxRain.value()

        input_path = os.path.join(rawdata, 'WFDEI')
        output_path = fileout
        # Set up and start worker thread
        worker = WatchWorker(rawdata, required_variables, datestart, dateend,
                             input_path, input_AH_path, output_path, lat, lon, hgt,
                             UTC_offset_h, rainAmongN, self.dlg.lblStatus)
        thr = QThread(self.dlg)
        worker.moveToThread(thr)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        thr.started.connect(worker.run)
        thr.start()
        self.thread = thr
        self.worker = worker

    def workerFinished(self):
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()  # Wait for quit
        self.thread.deleteLater()  # Flag for deletion
        self.dlg.runButton.setEnabled(True)
        self.iface.messageBar().pushMessage("WATCH data", "Data downloaded and processed", level=QgsMessageBar.INFO)
        self.dlg.lblStatus.setText('')

    def workerError(self, strException):
        if type(strException) is not str:
            strException = str(strException)

        QMessageBox.information(None, "WATCH extraction error:", strException)
