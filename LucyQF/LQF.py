# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LQF
                                 A QGIS plugin
 LQF anthropogenic heat flux model
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
from __future__ import absolute_import
from builtins import str
from builtins import object

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread, Qt
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog
from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgsMessageBar
from qgis.core import QgsVectorLayer, QgsMessageLog, Qgis
from .LQF_dialog import LQFDialog
import os.path
import webbrowser
# LUCY specific code
from .PythonLUCY.LUCY import Model
from .time_displayer import time_displayer
from datetime import datetime as dt
from datetime import timedelta as timedelta
from .PythonLUCY.Disaggregate import DisaggregateWorker, disaggregate
import traceback

try:
    import pandas as pd
    import matplotlib
except:
    pass


class LQF(object):
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
            'LQF_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Check dependencies
        try:
            import pandas
        except Exception as e:
            QMessageBox.critical(None, 'Error',
                                 'This plugin requires the pandas package to be installed. '
                                 'Please consult the manual for further information')
            return

        # Check dependencies
        try:
            import netCDF4
        except Exception as e:
            QMessageBox.critical(None, 'Error',
                                 'This plugin requires the NetCDF4 package to be installed. '
                                 'Please consult the manual for further information')
            return

        # Check dependencies
        try:
            import matplotlib
        except Exception as e:
            QMessageBox.critical(None, 'Error',
                                 'This plugin requires the matplotlib package to be installed. '
                                 'Please consult the manual for further information')
            return

        # Create the dialog (after translation) and keep reference
        self.dlg = LQFDialog()
        self.initialise() # Initialize text boxes and model fields
        self.setup() # Connect all push buttons

        self.dlg.cmdRunCancel.clicked.connect(self.startWorker, Qt.UniqueConnection)
        self.dlg.pushButtonClose.clicked.connect(self.dlg.close, Qt.UniqueConnection)                                # Close this dialog

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&LQF')
        # self.toolbar = self.iface.addToolBar(u'LQF')
        # self.toolbar.setObjectName(u'LQF')

    def initialise(self):
        self.model = Model()                #LQF object
        # Dialog attributes
        self.landCoverFractionData = None   # Paths to raster files (paved fraction)
        self.polygonGridFile = None         # building fraction
        self.dateRange = True               # Does the user want to model a date range (True) or use a date list (False)?

        # Populate text boxes with default entries
        self.dlg.txtParams.setText('')
        self.dlg.txtDataSources.setText('')
        self.dlg.textOutput_raw.setText('')
        self.dlg.txtProcessedDataPath.setText('')
        self.dlg.txtLandCoverFraction.setText('')
        self.dlg.txtPolygonGrid.setText('')

        # Set initial button states
        self.dlg.pushButtonParams.setEnabled(True)
        self.dlg.pushButtonDataSources.setEnabled(True)
        self.dlg.cmdRunCancel.setEnabled(False) # Until data sources ready
        self.dlg.pushButtonClose.setEnabled(True)
        self.dlg.cmdVisualise.setEnabled(False) # Until results available
        self.dlg.cmdPrepare.setEnabled(False) # Until data sources, config file and output path set
        self.dlg.cmdProcessedDataPath.setEnabled(False) # Until output folder set

        # Default: USe date range rather than list
        self.dlg.chkDateRange.setChecked(True)
        self.dlg.chkDateList.setChecked(False)
        self.dlg.txtDateList.setText('')
        self.useDateRange()

        self.pickledResultsLocation = None                                                      # Location of a file containing pickled results

    def setup(self):
        ''' Set up the dialog box with empty parameters and a fresh model object'''
         # Create the dialog (after translation) and keep reference

        # Connect buttons to events
        # File loading events

        self.dlg.pushButtonParams.clicked.connect(self.loadParams, Qt.UniqueConnection)              # Params file
        self.dlg.pushButtonDataSources.clicked.connect(self.dataSources, Qt.UniqueConnection)          # Data sources file
        self.dlg.cmdLandCoverFraction.clicked.connect(self.landCoverFraction, Qt.UniqueConnection)     # Raster for % land cover buildings
        self.dlg.cmdPolygonGrid.clicked.connect(self.polygonGrid, Qt.UniqueConnection)                 # land cover paved
        self.dlg.lstPrimaryKey.currentIndexChanged.connect(self.polygonGridID, Qt.UniqueConnection)
        self.dlg.chkDateRange.clicked.connect(self.useDateRange, Qt.UniqueConnection)
        self.dlg.chkDateList.clicked.connect(self.useDateList, Qt.UniqueConnection)

        # Other interface buttons
        self.dlg.cmdVisualise.clicked.connect(self.visualise, Qt.UniqueConnection)                                    # Visualisation dialog
        self.dlg.pushButtonRaw.clicked.connect(self.outputFolder, Qt.UniqueConnection)                               # Output folder
        self.dlg.cmdPrepare.clicked.connect(self.disaggregate, Qt.UniqueConnection)                                  # Prepare input data
        self.dlg.cmdLoadResults.clicked.connect(self.loadResults, Qt.UniqueConnection)                               # Load a previous model run's results

        # Run model
        self.dlg.cmdProcessedDataPath.clicked.connect(self.chooseProcessedDataPath, Qt.UniqueConnection)             # Select prepared input data
        self.dlg.pushButtonHelp.clicked.connect(self.help, Qt.UniqueConnection) # Launch web-based help

    def useDateRange(self):
        '''
        Enable date range boxes and disable date list box
        :return:
        '''
        self.dlg.startDate.setEnabled(True)
        self.dlg.endDate.setEnabled(True)
        self.dlg.txtDateList.setEnabled(False)
        self.dateRange = True

    def useDateList(self):
        '''
        Enable date list box and disable date range boxes
        :return:
        '''
        self.dlg.startDate.setEnabled(False)
        self.dlg.endDate.setEnabled(False)
        self.dlg.txtDateList.setEnabled(True)
        self.dateRange = False

    def chooseProcessedDataPath(self):
        '''
        Allows user to select folder containing pre-processed input data. Validates the folder and checks for a valid manifest.
        :return:
        '''
        fileDialog = QFileDialog()
        # fileDialog.setFileMode(2)
        # fileDialog.setAcceptMode(0)
        fileDialog.setFileMode(QFileDialog.Directory)
        fileDialog.setOption(QFileDialog.ShowDirsOnly, True)
        result = fileDialog.exec_()
        if result == 1:
            selectedFolder = fileDialog.selectedFiles()[0]
            # Check for manifest file or reject
            try:
                self.model.setPreProcessedInputFolder(selectedFolder)
            except Exception as e:
                QMessageBox.critical(None, 'Error setting processed data path', str(e))
                return
            self.dlg.txtProcessedDataPath.setText(selectedFolder)
            # Enable model run button
            self.dlg.cmdRunCancel.setEnabled(True)          # Now data is available, allow user to run model

    def outputFolder(self):
        # Let user select folder into which model outputs will be saved
        fileDialog = QFileDialog()
        fileDialog.setFileMode(QFileDialog.Directory)
        # fileDialog.setFileMode(4)
        # fileDialog.setAcceptMode(1)
        result = fileDialog.exec_()
        if result == 1:
            self.model.setOutputDir(fileDialog.selectedFiles()[0])
            self.dlg.textOutput_raw.setText(fileDialog.selectedFiles()[0])

        # Reset processed data path (this needs to get copied to output folder)
        self.dlg.txtProcessedDataPath.setText('')
        self.dlg.cmdProcessedDataPath.setEnabled(True)  # Let user pick some pre-prcessed input data

    def updateWorker(self, val):
        self.dlg.progressBar.setValue(int(val))

    def disaggregate(self):
        '''
        Disaggregates model inputs to files on hard drive (saves user having to repeat over and over)
        :return: Dict containing information about each disaggregated file, for use by model
        '''

        # TODO: this is a temprary fix for running outside the worker. Worker not working 20111123 Fredrik Needs to be fixed
        self.dlg.cmdPrepare.setEnabled(False)
        if QMessageBox.question(self.dlg, "Prepare input data",
                                "QGIS will freeze for a moment while preparing input. Du you want to continue?",
                                QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
            run = 1
        else:
            QMessageBox.critical(self.dlg, "Prepare input data", "No input data prepared. Model cannot be executed")
            run = 0

        if run == 1:
            strDirectory = disaggregate(self.model.ds, self.model.parameters, self.model.downscaledPath,
                                        self.model.UMEPgrid, self.model.UMEPcoverFractions, self.model.UMEPgridID, None)
            self.dlg.cmdRunCancel.setEnabled(True)  # Model can now be run
            self.dlg.pushButtonClose.setEnabled(True)
            self.dlg.cmdLoadResults.setEnabled(True)
            self.dlg.progressBar.setValue(100)
            self.model.setPreProcessedInputFolder(strDirectory)
            self.dlg.txtProcessedDataPath.setText(strDirectory)

        self.dlg.cmdPrepare.setEnabled(True)

        ## Worker not working 20111123 Fredrik Needs to be fixed
        # # This is shifted to another thread
        # worker = DisaggregateWorker(ds=self.model.ds, params=self.model.parameters, outputFolder=self.model.downscaledPath, UMEPgrid=self.model.UMEPgrid, UMEPcoverFractions=self.model.UMEPcoverFractions, UMEPgridID=self.model.UMEPgridID)
        #
        # thr = QThread(self.dlg)
        # worker.moveToThread(thr)
        # worker.finished.connect(self.disaggWorkerFinished)
        # worker.error.connect(self.workerError)
        # worker.update.connect(self.updateWorker)
        # thr.started.connect(worker.run)
        #
        # self.dlg.cmdPrepare.setText('Cancel')
        # self.dlg.cmdPrepare.clicked.disconnect()
        # self.dlg.cmdPrepare.clicked.connect(worker.kill, Qt.UniqueConnection)
        # self.dlg.pushButtonClose.setEnabled(False)
        # self.dlg.cmdRunCancel.setEnabled(False)
        # self.dlg.pushButtonClose.setEnabled(False)
        # self.dlg.cmdLoadResults.setEnabled(False)
        # self.dlg.cmdPrepare.setEnabled(False)
        # thr.start()
        # self.thread = thr
        # self.worker = worker

    def disaggWorkerFinished(self, strDirectory):
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()  # Wait for quit
        self.thread.deleteLater()  # Flag for deletion
        self.dlg.cmdPrepare.setText('Prepare input data using Data sources')
        self.dlg.cmdPrepare.clicked.disconnect()
        self.dlg.cmdPrepare.clicked.connect(self.disaggregate, Qt.UniqueConnection)
        self.dlg.cmdRunCancel.setEnabled(True) # Model can now be run
        self.dlg.pushButtonClose.setEnabled(True)
        self.dlg.cmdLoadResults.setEnabled(True)
        self.model.setPreProcessedInputFolder(strDirectory)
        self.dlg.txtProcessedDataPath.setText(strDirectory)
        self.dlg.cmdPrepare.setEnabled(True)
        self.iface.messageBar().pushMessage("LQF", "Input data has been processed. Model can now be run", level=Qgis.Info)

    def workerError(self, strException):
        QMessageBox.critical(None, 'Data pre-processing error:', str(strException))
        QgsMessageLog.logMessage(traceback.format_exc(), level=Qgis.Warning)

        self.dlg.progressBar.setValue(0)
        self.dlg.cmdPrepare.setText('Prepare input data using Data sources')
        self.dlg.cmdPrepare.clicked.disconnect()
        self.dlg.cmdPrepare.clicked.connect(self.disaggregate, Qt.UniqueConnection)
        self.dlg.cmdRunCancel.setEnabled(True) # Model can now be run
        self.dlg.pushButtonClose.setEnabled(True)
        self.dlg.cmdLoadResults.setEnabled(True)
        self.dlg.cmdPrepare.setEnabled(True)

    def help(self):
        url = "https://umep-docs.readthedocs.io/en/latest/processor/Urban%20Energy%20Balance%20LQ.html"
        webbrowser.open_new_tab(url)

    def dataSources(self):
        # Select and parse data sources file
        a = QFileDialog()
        a.open()
        result = a.exec_()
        if result == 1:
            df = a.selectedFiles()
            try:
                self.model.setDataSources(df[0])
            except Exception as e:
                QMessageBox.critical(None, 'Invalid Data Sources file provided', str(e))
                return

            self.dlg.txtDataSources.setText(df[0])
            self.dlg.cmdPrepare.setEnabled(True)

    def landCoverFraction(self):
        # Select a CSV file generated by UMEP that contains land cover fractions
        # Produce extra-disaggregated population and road length layers that will be used as the output folder
        a = QFileDialog()
        a.open()
        result = a.exec_()
        if result == 1:
            df = a.selectedFiles()
            self.dlg.txtLandCoverFraction.setText(df[0])
            if not os.path.exists(df[0]):
                QMessageBox.critical(None, 'Invalid land cover fraction file specified')
            self.model.setLandCoverData(df[0])

    def polygonGrid(self):
        # Select a polygon shapefile corresponding to land cover fraction data
        a = QFileDialog()
        a.open()
        result = a.exec_()

        if result == 1:
            df = a.selectedFiles()
            self.dlg.txtPolygonGrid.setText(df[0])
            if not os.path.exists(df[0]):
                QMessageBox.critical(None, 'Problem with extra disaggregation', 'Invalid path to shapefile grid specified')
            self.model.setLandCoverGrid(df[0])
            # Populate dropdown box with available fields
            try:
                a=QgsVectorLayer(df[0], 'a', 'ogr')
            except Exception:
                QMessageBox.critical(None, 'Problem with extra disaggregation', 'Invalid shapefile grid specified')

            self.dlg.lstPrimaryKey.clear()
            [self.dlg.lstPrimaryKey.addItem(str(label.name())) for label in a.fields()]
            self.dlg.lstPrimaryKey.setEnabled(True)
            a= None

    def polygonGridID(self, text):
        # Set land cover polygon shapefile ID field based on dropdown
        self.model.setLandCoverGridID(self.dlg.lstPrimaryKey.currentText())

    def visualise(self):
        # Launch results visualisation dialog, specifying the current model outputs directory as the one to use
        if not self.model.resultsAvailable:
            QMessageBox.critical(None, 'No results available', 'Nothing to plot: Either run the model or load some previous results')#
            return

        a = time_displayer(self.model, self.iface)
        a.exec_()

    def loadParams(self):
        # Select and parse parameters namelist
        a = QFileDialog()
        a.open()
        result = a.exec_()
        if result == 1:
            cf = a.selectedFiles()
            try:
                self.model.setParameters(cf[0])
            except Exception as e:
                QMessageBox.critical(None, 'Invalid parameters file', str(e))
                return

            self.dlg.txtParams.setText(cf[0])

    def loadResults(self):
        ''' Load a previous model run for visualisation'''
        fileDialog = QFileDialog()
        # fileDialog.setFileMode(2)
        # fileDialog.setAcceptMode(0)
        fileDialog.setFileMode(QFileDialog.Directory)
        fileDialog.setOption(QFileDialog.ShowDirsOnly, True)
        result = fileDialog.exec_()
        if result == 1:
            selectedFolder = fileDialog.selectedFiles()[0]
            # Check for manifest file or reject
            try:
                locations = self.model.loadModelResults(selectedFolder)
            except Exception as e:
                QMessageBox.critical(None, 'Error loading previous model results', str(e))
                return

            # Let user re-run the loaded model.
            self.dlg.cmdRunCancel.setText('Re-Run')
            self.dlg.cmdRunCancel.setEnabled(True)

            self.dlg.cmdLoadResults.setText('Clear results')
            self.dlg.cmdLoadResults.clicked.disconnect()
            self.dlg.cmdLoadResults.clicked.connect(self.reset, Qt.UniqueConnection)

            self.dlg.cmdVisualise.setEnabled(True)

            # Update text boxes with file locations for user information
            self.dlg.txtProcessedDataPath.setText(locations['processedInputData'])
            self.dlg.textOutput_raw.setText(locations['outputPath'])
            self.dlg.txtDataSources.setText(locations['dsFile'])
            self.dlg.txtParams.setText(locations['paramsFile'])



    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('LQF', message)

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

        icon_path = ':/plugins/LUCY/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'LQF'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&LUCY'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def startWorker(self):

        #TODO: this is a temprary fix for running outside the worker. Worker not working 20111123 Fredrik Needs to be fixed
        self.dlg.cmdPrepare.setEnabled(False)
        if QMessageBox.question(self.dlg, "Running model",
                                "QGIS will freeze for a moment while calculating anthropogenic heat. Du you want to continue?",
                                QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
            run = 1
        else:
            QMessageBox.critical(self.dlg, "Running model", "Operation cancelled. Model will not be executed")
            run = 0

        if run == 1:
            # Do input validation
            # Get start date(s): One start date if a range, multiple if a list
            if self.dateRange:
                # Date range supplied
                if self.dlg.startDate.date().toPyDate() >= self.dlg.endDate.date().toPyDate():
                    QMessageBox.critical(None, 'Error', 'Start date must be earlier than end date')
                    return
                startDates = [self.dlg.startDate.date().toPyDate()]
                endDates = [self.dlg.endDate.date().toPyDate()]
            else:
                # Date list supplied
                # Parse date list
                text = self.dlg.txtDateList.text()
                dateList = text.split(',')
                startDates = []
                endDates = []
                for date in dateList:
                    try:
                        startDates.append(dt.strptime(date.strip(), '%Y-%m-%d'))
                        endDates.append(startDates[-1] + timedelta(hours=24))
                    except Exception:
                         QMessageBox.critical(None, 'Error', 'Invalid date list: ' + date + '. Must be comma-separated and in format YYYY-mm-dd')
                         return

            # Does the user want to also create SUEWS input files?
            # makeNcdf = self.dlg.chkSUEWS.isChecked()
            makeNcdf = False
            # If a list, then generate end dates 24h after each start date
            # Create a config dict for the model to use
            self.dlg.cmdRunCancel.setEnabled(False)
            self.dlg.pushButtonClose.setEnabled(False)
            self.dlg.cmdLoadResults.setEnabled(False)
            config = {'startDates':startDates, 'endDates':endDates, 'makeNetCDF':makeNcdf}
            self.model.setConfig(config)

            try:
                self.model.run()
                self.dlg.progressBar.setValue(100)
                self.iface.messageBar().pushMessage("LQF", "Model run complete. Click 'visualise' to view output",
                                                level=Qgis.Info)

                # Change Run button to Clear button
                self.dlg.cmdLoadResults.setText('Clear results')
                self.dlg.cmdLoadResults.clicked.disconnect()
                self.dlg.cmdLoadResults.clicked.connect(self.reset, Qt.UniqueConnection)
                self.dlg.cmdLoadResults.setEnabled(True)
                self.dlg.cmdVisualise.setEnabled(True)

            except Exception as e:
                QMessageBox.critical(None, 'Error running LQF', str(e))
                QgsMessageLog.logMessage(traceback.format_exc(), level=Qgis.Warning)

            self.dlg.cmdRunCancel.setText('Re-Run')
            self.dlg.cmdRunCancel.setEnabled(True)
            self.dlg.pushButtonClose.setEnabled(True)

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def reset(self):
        ''' Reset model object and dialogues so that user can start again'''
        self.initialise()
        # Reset the "run" button
        self.dlg.cmdRunCancel.clicked.disconnect()
        self.dlg.cmdRunCancel.clicked.connect(self.startWorker, Qt.UniqueConnection)
        self.dlg.cmdRunCancel.setText('Run')
        self.dlg.cmdRunCancel.setEnabled(True)
        # Reset the "load results" button
        self.dlg.cmdLoadResults.clicked.disconnect()
        self.dlg.cmdLoadResults.setText('Load results')
        self.dlg.cmdLoadResults.clicked.connect(self.loadResults, Qt.UniqueConnection)  # Load a previous run's results
        self.dlg.cmdLoadResults.setEnabled(True)

