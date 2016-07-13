# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GreaterQF
                                 A QGIS plugin
 GreaterQF model
                              -------------------
        begin                : 2016-06-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by University of reading
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
from qgis.core import QgsMessageLog,  QgsMapLayerRegistry, QgsSymbolV2, QgsGraduatedSymbolRendererV2, QgsRendererRangeV2
from qgis.gui import QgsMessageBar
from PyQt4.QtGui import QAction, QIcon, QColor, QMessageBox, QFileDialog
from PyQt4 import QtCore
import tempfile
# Initialize Qt resources from file resources.py
# Import the code for the dialog
from greater_qf_dialog import GreaterQFDialog
from greaterQFWorker import GreaterQFWorker

# System
import copy
import os.path
import urllib
import gzip
import webbrowser
try:
    import pandas as pd
except:
    pass
# GreaterQF functions
from PythonQF.spatialHelpers import *
from PythonQF.AllParts import getQFComponents
#from EnergyUseData import *
def workerError(e, strException):
    QgsMessageLog.logMessage('GreaterQF worker exception {}:\n'.format(strException), level=QgsMessageLog.CRITICAL)

def downloadData(manifest, destination):
    # Downloads non-compressed data and deposits it somewhere
    for file in manifest:
        opener = urllib.URLopener()
        try:
            opener.retrieve('http://www.urban-climate.net/GreaterQF/' + file, os.path.join(destination, file))
        except Exception, e:
            raise Exception('Could not download input data file:' + str(e))

def download1km(destination):
    # Download 1km shapefiles
    manifest = ['Grid1000x1000m2.shp',
                'Grid1000x1000m2.dbf',
                'Grid1000x1000m2.GridID.atx',
                'Grid1000x1000m2.shx',
                'Grid1000x1000m2.sbn',
                'Grid1000x1000m2.sbx']

    downloadData(manifest, destination)

def downloadLocalAuthority(destination):
    manifest = ['London_Borough_Excluding_MHW.dbf',
                'London_Borough_Excluding_MHW.GSS_CODE.atx',
                'London_Borough_Excluding_MHW.NAME.atx',
                'London_Borough_Excluding_MHW.prj',
                'London_Borough_Excluding_MHW.sbn',
                'London_Borough_Excluding_MHW.sbx',
                'London_Borough_Excluding_MHW.shp',
                'London_Borough_Excluding_MHW.shx']
    downloadData(manifest, destination)


def downloadInputData(destination):
    '''Downloads and decompresses input data files'''
    manifest = ['AreaList.csv',
                'GORData.csv',
                'Grid200Data.csv',
                'Gridkm2Data.csv',
                'Index1_Transportation.csv',
                'Index2_EnergyHourly.csv',
                'Index3_EnergyDaily.csv',
                'Index4_Metabolism.csv',
                'Index5_HeatCombustion.csv',
                'LAData.csv',
                'LLSOAData.csv',
                'MLSOAData.csv',
                'OAData.csv',
                'SubOA200Data.csv']

    for file in manifest:
        opener = urllib.URLopener()
        try:
            temp_destination = os.path.join(tempfile.gettempdir(), file + '.gz')
            opener.retrieve('http://www.urban-climate.net/GreaterQF/' + file + '.gz', temp_destination)
        except Exception, e:
            raise Exception('Could not download input data file:' + str(e))

        try:
            destination_file = os.path.join(destination, file)
            # Gunzip and install in InputData folder
            with gzip.open(temp_destination, 'rb') as zipFile:
                a = zipFile.read()
            with open(destination_file, 'wb') as outFile:
                outFile.write(a)
        except Exception, e:
            raise Exception('Problem occurred decompressing file: ' + str(e))
        finally:
            os.remove(temp_destination)


class GreaterQF:
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
            'GreaterQF_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = GreaterQFDialog()
        self.folderPathRaw = None
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        self.dlg.cmdRunCancel.clicked.connect(self.startWorker)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonClose.clicked.connect(self.dlg.close)
        self.dlg.pushButtonRaw.clicked.connect(self.raw_path)
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GreaterQF')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'GreaterQF')
        # self.toolbar.setObjectName(u'GreaterQF')

    def help(self):
        url = "http://urban-climate.net/umep/UMEP_Manual#Processor:_Urban_Energy_Balance:_GreaterQF"
        webbrowser.open_new_tab(url)

    def raw_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathRaw = self.fileDialog.selectedFiles()
            self.dlg.textOutput_raw.setText(self.folderPathRaw[0])
            self.folderPathRaw = self.folderPathRaw[0]
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
        return QCoreApplication.translate('GreaterQF', message)


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

        icon_path = ':/plugins/GreaterQF/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'GreaterQF'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GreaterQF'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def startWorker(self):
        # Check dependencies
        try:
            import pandas
        except Exception, e:
            QMessageBox.critical(None, 'Error',
                                 'GreaterQF requires the pandas package to be installed. Please consult the manual for further information')
            return

        # Do input validation
        if self.folderPathRaw is None:
            QMessageBox.critical(None, 'Error', 'Please specify an output folder')
            return
        if not os.path.exists(self.folderPathRaw):
            QMessageBox.critical(None, 'Error', 'Invalid output folder specified')
            return
        if self.dlg.startDate.date().toPyDate() >= self.dlg.endDate.date().toPyDate():
            QMessageBox.critical(None, 'Error', 'Start date must be earlier than end date')
            return

        self.dlg.pushButtonClose.setEnabled(False)
        self.dlg.cmdRunCancel.setEnabled(False)
        # Download the source data if it's not already present
        input_dir = os.path.join(self.plugin_dir, 'PythonQF', 'InputData')
        if not os.path.exists(os.path.join(input_dir, 'Grid200Data.csv')):
            QMessageBox.information(None, 'Input data needed', 'The input data will be automatically downloaded to your computer. This needs around 100 MB of space.')
            # Get input data
            downloadInputData(input_dir)

            # Get areas
            download1km(os.path.join(self.plugin_dir, 'PythonQF', 'Shapefile_Grid1000x1000'))
            downloadLocalAuthority(os.path.join(self.plugin_dir, 'PythonQF', 'statistical-gis-boundaries-london', 'ESRI'))




        # Set up GreaterQF worker thread
        # Component options (checkboxes)
        componentOptions = {'sensible':self.dlg.chkSensibleQf.checkState()>0, 'latent':self.dlg.chkLatentQf.checkState()>0, 'wastewater':self.dlg.chkWastewaterQf.checkState()>0}
        outputArea = None
        if self.dlg.lstAreas.currentText() == '1km grid':
            outputArea = 'Gridkm2Data'
        if self.dlg.lstAreas.currentText() == 'Local Authority':
            outputArea = 'LAData'

        if outputArea is None:
            raise ValueError('Invalid output area selected')

        worker = GreaterQFWorker(self.dlg.startDate.date(), self.dlg.endDate.date(), componentOptions, outputArea)

        # # Swap the Cancel button to a Run button
        # self.dlg.cmdRunCancel.clicked.disconnect()
        # self.dlg.cmdRunCancel.clicked.connect(worker.kill)
        # self.dlg.cmdRunCancel.setText('Abort')
        # Reset progress bar
        self.dlg.progressBar.setValue(0)
        # Instantiate worker and move to thread
        thr = QtCore.QThread(self.dlg)
        worker.moveToThread(thr)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(workerError)
        worker.progress.connect(self.dlg.progressBar.setValue)
        thr.started.connect(worker.run)
        thr.start()
        self.thread = thr
        self.worker = worker

    def workerFinished(self, returnVal):
        # Deal with output and plot first time step of model in QGIS as useful feedback
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()  # Wait for quit
        self.thread.deleteLater()  # Flag for deletion

        if returnVal is None:
            raise Exception('Model run failed')
        # Locations of PythonQF relative to this script
        dir = os.path.join(os.path.dirname(__file__), 'PythonQF')

        shapefiles = {}
        shapefiles['LAData'] = {'file': 'statistical-gis-boundaries-london/ESRI/London_Borough_Excluding_MHW.shp',
                                'primaryKey': 'GSS_CODE', 'EPSG':27700}
        shapefiles['Gridkm2Data'] = {'file': 'Shapefile_Grid1000x1000/Grid1000x1000m2.shp', 'primaryKey': 'Gr1000Code', 'EPSG':27700}
        shapefiles['Grid200Data'] = {'file': 'Shapefile_Grid200x200/Grid200x200m2.shp', 'primaryKey': 'Gr200Code', 'EPSG':27700}

        # Some need working out
        shapefiles['GORData'] = ''
        shapefiles['MLSOAData'] = ''
        shapefiles['LLSOAData'] = ''
        shapefiles['OAData'] = ''

        # Write outputs as text files
        components = getQFComponents()
        dates = pd.date_range(start=self.dlg.startDate.date().toPyDate().strftime('%Y-%m-%d %H:30:00'),
                              periods=returnVal['Data'].shape[2], freq='30min')

        for cmp in getQFComponents().keys():
            df = pd.DataFrame(returnVal['Data'][:,cmp,:].transpose(), columns=returnVal['ID'], index=dates)
            df.to_csv(os.path.join(self.folderPathRaw, 'GreaterQF_' + components[cmp] + '.csv'))
        self.dlg.progressBar.setValue(90)
        # Generate example shapefile from model outputs
        i=0  # use first time step
        templateShapeFile = os.path.join(dir, shapefiles[returnVal['SpatialDomain']]['file'])
        primaryKey = shapefiles[returnVal['SpatialDomain']]['primaryKey']
        proj = shapefiles[returnVal['SpatialDomain']]['EPSG']
        displayLayer = populateShapefileFromTemplate(components, returnVal['ID'], returnVal['Data'][:,:,i], primaryKey, templateShapeFile, proj)

        # Colour map by "Everything"
        rangeList = []
        opacity = 1
        minima = [0, 1, 5, 10, 20, 30, 50, 75]
        maxima = [1, 5, 10, 20, 30, 50, 75, 200]
        colours = ['#000080', '#5555AA', '#AAAAD4','#FFFFFF','#DFBFBF','#BF7F7F','#9F3F3F','#800000']

        for i in range(0, len(minima)):
            symbol = QgsSymbolV2.defaultSymbol(displayLayer.geometryType())
            symbol.setColor(QColor(colours[i]))
            symbol.setAlpha(opacity)
            valueRange = QgsRendererRangeV2(minima[i], maxima[i], symbol, str(minima[i]) + ' - ' + str(maxima[i]))
            rangeList.append(valueRange)

        renderer = QgsGraduatedSymbolRendererV2('', rangeList)
        renderer.setMode(QgsGraduatedSymbolRendererV2.EqualInterval)
        renderer.setClassAttribute('Everything')
        displayLayer.setRendererV2(renderer)
        QgsMapLayerRegistry.instance().addMapLayer(displayLayer)

        # Swap the cancel button to a run button
        # self.dlg.cmdRunCancel.clicked.disconnect()
        # self.dlg.cmdRunCancel.clicked.connect(self.startWorker)
        # self.dlg.cmdRunCancel.setText('Run')
        self.dlg.cmdRunCancel.setEnabled(True)
        self.dlg.pushButtonClose.setEnabled(True)
        self.dlg.progressBar.setValue(100)
        self.iface.messageBar().pushMessage("GreaterQF", "Model run complete. Showing output from first time step", level=QgsMessageBar.INFO)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.exec_()

