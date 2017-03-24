# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GQF
                                 A QGIS plugin
 GreaterQF anthropogenic heat flux model
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
import tempfile

from PyQt4 import QtCore
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
from qgis.core import QgsMessageLog,  QgsMapLayerRegistry, QgsRasterLayer
from qgis.gui import QgsMessageBar

# Initialize Qt resources from file resources.py
# Import the code for the dialog
from greater_qf_dialog import GreaterQFDialog
from datetime import timedelta
from datetime import datetime as dt
# System
import os.path
import webbrowser
from qgis.core import QgsVectorLayer
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtCore import QThread, Qt

# GQF specific code
from PythonQF2.Config import Config
from PythonQF2.GreaterQF import Model
from time_displayer import time_displayer

try:
    import pandas as pd
    import matplotlib as plt
except:
    pass

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

        # Check dependencies
        try:
            import pandas
            import matplotlib as plt
        except Exception, e:
            QMessageBox.critical(None, 'Error',
                                 'GQF requires the pandas and matplotlib packages to be installed. Please consult the manual for further information')
            return
        self.dlg = GreaterQFDialog()
        self.setup() # Establish all object params
        self.connectButtons()
        self.dlg.cmdRunCancel.clicked.connect(self.startWorker, Qt.UniqueConnection)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GQF')
        self.toolbar = self.iface.addToolBar(u'GQF')
        self.toolbar.setObjectName(u'GQF')

    def connectButtons(self):
        ''' Connect buttons to default actions '''
        self.dlg.cmdVisualise.clicked.connect(self.visualise, Qt.UniqueConnection)                                   # Visualisation dialog
        self.dlg.pushButtonClose.clicked.connect(self.dlg.close, Qt.UniqueConnection)                                # Close this dialog
        self.dlg.pushButtonRaw.clicked.connect(self.outputFolder, Qt.UniqueConnection)                               # Output folder
        self.dlg.cmdPrepare.clicked.connect(self.disaggregate, Qt.UniqueConnection)                                  # Prepare input data
        self.dlg.cmdLoadResults.clicked.connect(self.loadResults, Qt.UniqueConnection)                               # Load a previous model run's results
        self.dlg.chkDateRange.clicked.connect(self.useDateRange, Qt.UniqueConnection)
        self.dlg.chkDateList.clicked.connect(self.useDateList, Qt.UniqueConnection)
        self.dlg.pushButtonParams.clicked.connect(self.loadParams, Qt.UniqueConnection)              # Params file
        self.dlg.pushButtonDataSources.clicked.connect(self.dataSources, Qt.UniqueConnection)        # Data sources file
        self.dlg.pushButtonHelp.clicked.connect(self.help, Qt.UniqueConnection) # Launch web-based help
        self.dlg.cmdProcessedDataPath.clicked.connect(self.chooseProcessedDataPath, Qt.UniqueConnection)             # Select prepared input data

    def setup(self):
        ''' Set up the dialog box with empty parameters and a fresh model object'''
         # Create the dialog (after translation) and keep reference
        self.model = Model()
        self.useDateRange()

        # Populate text boxes with default entries
        self.dlg.txtParams.setText('')
        self.dlg.txtDataSources.setText('')
        self.dlg.textOutput_raw.setText('')
        self.dlg.txtProcessedDataPath.setText('')
        self.dlg.txtDateList.setText('')


    def chooseProcessedDataPath(self):
        '''
        Allows user to select folder containing pre-processed input data. Validates the folder and checks for a valid manifest.
        :return:
        '''

        fileDialog = QFileDialog()
        fileDialog.setFileMode(2)
        fileDialog.setAcceptMode(0)
        result = fileDialog.exec_()
        if result == 1:
            selectedFolder = fileDialog.selectedFiles()[0]
            # Check for manifest file or reject
            try:
                self.model.setPreProcessedInputFolder(selectedFolder)
            except Exception,e:
                QMessageBox.critical(None, 'Error setting processed data path', str(e))
                return
            self.dlg.txtProcessedDataPath.setText(selectedFolder)
            self.processedDataPath = selectedFolder
            # Enable model run button
            self.dlg.cmdRunCancel.setEnabled(True)

    def outputFolder(self):
        # Let user select folder into which model outputs will be saved
        fileDialog = QFileDialog()
        fileDialog.setFileMode(4)
        fileDialog.setAcceptMode(1)
        result = fileDialog.exec_()
        if result == 1:
            self.model.setOutputDir(fileDialog.selectedFiles()[0])
            self.dlg.textOutput_raw.setText(fileDialog.selectedFiles()[0])

    def dataSources(self):
        # Select and parse data sources file
        a = QFileDialog()
        a.open()
        result = a.exec_()
        if result == 1:
            df = a.selectedFiles()
            try:
                self.model.setDataSources(df[0])
            except Exception,e:
                QMessageBox.critical(None, 'Invalid Data Sources file provided', str(e))
                return

            self.dlg.txtDataSources.setText(df[0])

    def disaggregate(self):
        '''
        Disaggregates model inputs to files on hard drive (saves user having to repeat over and over)
        :return: Dict containing information about each disaggregated file, for use by model
        '''
        processed = self.model.processInputData()
        self.dlg.txtProcessedDataPath.setText(processed) # Update the UI to show path being used
        self.model.setPreProcessedInputFolder(processed)

    def help(self):
        url = "http://urban-climate.net/umep/UMEP_Manual#Processor:_Urban_Energy_Balance:_GQF"
        webbrowser.open_new_tab(url)

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
            except Exception, e:
                QMessageBox.critical(None, 'Invalid parameters file', str(e))
                return

            self.dlg.txtParams.setText(cf[0])

    def loadResults(self):
        ''' Load a previous model run for visualisation'''
        self.reset() # Clear everything as we are loading previous results

        fileDialog = QFileDialog()
        fileDialog.setFileMode(2)
        fileDialog.setAcceptMode(0)
        result = fileDialog.exec_()
        if result == 1:
            selectedFolder = fileDialog.selectedFiles()[0]
            # Check for manifest file or reject
            try:
                locations = self.model.loadModelResults(selectedFolder)
            except Exception,e:
                QMessageBox.critical(None, 'Error loading previous model results', str(e))
                return


            self.dlg.cmdLoadResults.clicked.disconnect()
            self.dlg.cmdLoadResults.clicked.connect(self.reset, Qt.UniqueConnection)
            self.dlg.cmdLoadResults.setText('Clear data')
            self.dlg.cmdVisualise.setEnabled(True)

            # Update text boxes with file locations for user information
            self.dlg.txtProcessedDataPath.setText(locations['processedInputData'])
            self.dlg.textOutput_raw.setText(locations['outputPath'])
            self.dlg.txtDataSources.setText(locations['dsFile'])

            try:
                self.model.setDataSources(locations['dsFile'])
            except Exception,e:
                QMessageBox.critical(None, 'Error loading previous model data sources', str(e) + '. Re-runs not available')
                self.dlg.cmdRunCancel.setEnabled(False)

            self.dlg.txtParams.setText(locations['paramsFile'])
            try:
                self.model.setParameters(locations['paramsFile'])
            except Exception,e:
                QMessageBox.critical(None, 'Error loading previous model configuration', str(e) + '. Re-runs not available')
                self.dlg.cmdRunCancel.setEnabled(False)




    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('GQF', message)

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
            text=self.tr(u'GQF'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GQF'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def startWorker(self):
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
                    raise ValueError('Invalid date list: ' + date + '. Must be comma-separated and in format YYYY-mm-dd')

        if self.dlg.startDate.date().toPyDate() >= self.dlg.endDate.date().toPyDate():
            QMessageBox.critical(None, 'Error', 'Start date must be earlier than end date')
            return

        # Run-time configuration
        # Component options (checkboxes)
        componentOptions = {'sensible':self.dlg.chkSensibleQf.checkState()>0, 'latent':self.dlg.chkLatentQf.checkState()>0, 'wastewater':self.dlg.chkWastewaterQf.checkState()>0}
        startDate = self.dlg.startDate.date().toPyDate().strftime('%Y-%m-%d')
        endDate = self.dlg.endDate.date().toPyDate().strftime('%Y-%m-%d')

        doLatent = componentOptions['latent']
        doSensible = componentOptions['sensible']
        doWastewater = componentOptions['wastewater']
        doAll = doLatent & doWastewater & doSensible

        # Create a Config object based on form entries
        configParams = {'start_dates': startDates,
                        'end_dates': endDates,
                        'all_qf': doAll,
                        'sensible_qf': doSensible,
                        'latent_qf': doLatent,
                        'wastewater_qf': doWastewater}

        config = Config()
        config.loadFromDictionary(configParams)
        self.model.setConfig(config)
        self.dlg.cmdRunCancel.setEnabled(False)
        self.dlg.pushButtonClose.setEnabled(False)
        # RUN MODEL HERE

        try:
            self.model.run()
            self.dlg.progressBar.setValue(100)
            self.iface.messageBar().pushMessage("GQF", "Model run complete. Click 'visualise' to view output",
                                            level=QgsMessageBar.INFO)
            # Swap the "load" button to a "Clear" button
            self.dlg.cmdLoadResults.clicked.disconnect()
            self.dlg.cmdLoadResults.clicked.connect(self.reset, Qt.UniqueConnection)
            self.dlg.cmdLoadResults.setText('Clear data')
        except Exception, e:
            QMessageBox.critical(None, 'Error running GQF', str(e))

        self.dlg.cmdRunCancel.setEnabled(True)
        self.dlg.pushButtonClose.setEnabled(True)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.exec_()

    def reset(self):
        ''' Reset model object and dialogues so that user can start again'''
        self.setup()
        # Replace the "clear results" box with "Load results"
        self.dlg.cmdLoadResults.clicked.disconnect()
        self.dlg.cmdLoadResults.clicked.connect(self.loadResults, Qt.UniqueConnection)
        self.dlg.cmdLoadResults.setText('Load results')
        self.dlg.cmdRunCancel.setEnabled(True)
        self.dlg.chkDateRange.setChecked(True)
        self.dlg.chkDateList.setChecked(False)

    def useDateRange(self):
        '''
        Enable date range boxes and disable date list box
        :return:
        '''
        self.dateRange = True
        self.dlg.startDate.setEnabled(True)
        self.dlg.endDate.setEnabled(True)
        self.dlg.txtDateList.setEnabled(False)

    def useDateList(self):
        '''
        Enable date list box and disable date range boxes
        :return:
        '''
        self.dateRange = False
        self.dlg.startDate.setEnabled(False)
        self.dlg.endDate.setEnabled(False)
        self.dlg.txtDateList.setEnabled(True)
