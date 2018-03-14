# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExtremeFinder
                                 A QGIS plugin
 This plugin is for finding extreme events.
                              -------------------
        begin                : 2016-10-12
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Bei Huang
        email                : b.huang@pgr.reading.ac.uk
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
from extreme_finder_dialog import ExtremeFinderDialog
import os.path
import webbrowser
from ..Utilities import f90nml
from HeatWave.findHW import *
from HeatWave.plotHW import plotHW
from PyQt4.QtCore import QDate, QObject, pyqtSignal, QThread
###########################################################################
#
#                               Plugin
#
###########################################################################


class ExtremeFinder:
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
            'ExtremeFinder_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.dlg = ExtremeFinderDialog()
        self.dlg.runButton.clicked.connect(self.start_progress_wrapped)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonClose.clicked.connect(self.dlg.close)
        self.dlg.pushButtonSave.clicked.connect(self.outfile)
        self.dlg.pushButtonSave_2.clicked.connect(self.infile)
        self.dlg.pushButtonSave_2.setEnabled(True)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)
        self.folderPathRaw = 'None'
        self.save_file = None
        self.outputfile = 'None'
        self.watch_vars =  ['Tair',
                                 'Wind',
                                 'LWdown',
                                 'PSurf',
                                 'Qair',
                                 'Rainf',
                                 'Snowf',
                                 'SWdown']
        self.hw_start =  None
        self.hw_end = None
        self.lat = None
        self.lon = None
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Extreme Finder')

        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ExtremeFinder')
        self.toolbar.setObjectName(u'ExtremeFinder')

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
        return QCoreApplication.translate('ExtremeFinder', message)

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

        # Create the dialog (after translation) and keep reference

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

    def disableButtons(self):
        ''' Disable all dialog buttons (except download/cancel)'''
        self.dlg.selectpoint.setEnabled(False)
        self.dlg.runButton.setEnabled(False)
        self.dlg.pushButtonHelp.setEnabled(False)
        self.dlg.pushButtonClose.setEnabled(False)
        self.dlg.pushButtonSave.setEnabled(False)
        self.dlg.pushButtonSave_2.setEnabled(False)
        self.dlg.dateEditStart.setEnabled(False)
        self.dlg.dateEditEnd.setEnabled(False)
        self.dlg.textOutput_lat.setEnabled(False)
        self.dlg.textOutput_lon.setEnabled(False)

    def enableButtons(self):
        ''' Enable all dialog buttons'''
        self.dlg.selectpoint.setEnabled(True)
        self.dlg.runButton.setEnabled(True)
        self.dlg.pushButtonHelp.setEnabled(True)
        self.dlg.pushButtonClose.setEnabled(True)
        self.dlg.pushButtonSave.setEnabled(True)
        self.dlg.pushButtonSave_2.setEnabled(True)
        self.dlg.dateEditStart.setEnabled(True)
        self.dlg.dateEditEnd.setEnabled(True)
        self.dlg.textOutput_lat.setEnabled(True)
        self.dlg.textOutput_lon.setEnabled(True)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/ExtremeFinder/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Find HWs'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Extreme Finder'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def help(self):
        url = "http://urban-climate.net/umep/UMEP_Manual#Outdoor_Thermal_Comfort:_ExtremeFinder"
        webbrowser.open_new_tab(url)

    def run(self):

        try:
            import pandas as pd
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The Extreme Finder requires the pandas package '
                                                'to be installed. Please consult the manual for further information')
            return
        try:
            from netCDF4 import Dataset, date2num
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The Extreme Finder requires the netCDF4 package '
                                                'to be installed. Please consult the manual for further information')
            return

        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed

    def validateInputDates(self):
        # validate date range and add to object properties if OK
        self.hw_start =  None
        self.hw_end = None

        hw_start = self.dlg.dateEditStart.text()
        try:
            hw_start = datetime.datetime.strptime(hw_start, '%Y-%m-%d')
        except Exception:
            raise ValueError('Invalid start date (%s) entered'%(hw_start))
        hw_end = self.dlg.dateEditEnd.text()
        try:
            hw_end = datetime.datetime.strptime(hw_end, '%Y-%m-%d')
        except Exception:
            raise ValueError('Invalid end date (%s) entered'%(hw_end))

        self.hw_start = hw_start
        self.hw_end = hw_end

    def validateInputCoordinates(self):
        ''' validate and record the  latitude and longitude boxes (must be WGS84)'''
        lon = float(self.dlg.textOutput_lon.text())
        if not (-180 < lon < 180):
            raise ValueError('Invalid co-ordinates entered')

        lat = float(self.dlg.textOutput_lat.text())
        if not (-90 < lat < 90):
            raise ValueError('Invalid co-ordinates entered')

        self.lat = lat
        self.lon = lon

    def error(self, exception, text):
        self.enableButtons()
        QMessageBox.critical(None, "Error", 'Data download not completed: %s'%(str(exception),))

    def infile(self):
        filename = QFileDialog.getOpenFileName()
        if filename.split('.')[-1]=='nc':
            # If a NetCDF file, try and get metadata to populate the dialog elements
            (lat, lon, start_date, end_date) = get_ncmetadata(filename)

        self.dlg.textInput.setText(filename)
        if (lat is not None) and (lon is not None):
            self.dlg.textOutput_lat.setText(str(lat))
            self.dlg.textOutput_lon.setText(str(lon))

        self.dlg.dateEditStart.setDate(start_date)
        self.dlg.dateEditEnd.setDate(end_date)

    def outfile(self):
        outputfile = self.fileDialog.getSaveFileName(
            None, "Save File As:", None, "Text Files (*.txt)")
        # self.fileDialog.open()
        # result = self.fileDialog.exec_()
        if not outputfile == 'None':
            self.outputfile = outputfile
            self.dlg.textOutput.setText(self.outputfile)

    def start_progress_wrapped(self):
        '''
        Runs start_progress but wraps in an error dialog box to catch exceptions
        '''
        try:
            self.start_progress()
        except Exception, e:
            QMessageBox.critical(None, "Error", str(e))
            self.dlg.runButton.setEnabled(True)

    def start_progress(self):
        # get current working directory
        pwd = os.path.dirname(os.path.realpath(__file__))
        self.dlg.runButton.setEnabled(False)
        # read the namelist file
        # with open() as nml_file:
        nml = f90nml.read(os.path.join(pwd, 'input.nml'))

        t1_quantile_Meehl = nml['method']['t1_quantile_Meehl']
        t2_quantile_Meehl = nml['method']['t2_quantile_Meehl']
        t3_quantile_Fischer = nml['method']['t3_quantile_Fischer']
        t4_quantile_Schoetter = nml['method']['t4_quantile_Schoetter']
        t5_quantile_Vautard = nml['method']['t5_quantile_Vautard']
        t6_quantile_Keevallik = nml['method']['t6_quantile_Keevallik']
        TempDif_Srivastava = nml['method']['TempDif_Srivastava']
        TempDif_Busuioc = nml['method']['TempDif_Busuioc']

        # Does user want heatwave or coldwave?
        filein = self.dlg.textInput.text()
        fileout = self.dlg.textOutput.text()
        if not os.path.exists(os.path.split(fileout)[0]):
            raise ValueError("Invalid output file location entered")

        # Is user looking at HW or CW tab of toolbox?
        mode = None
        var = None
        if self.dlg.toolBox.currentIndex() == 0:
            mode = 'HW'
            var = str(self.dlg.cmbHWvar.currentText())
            if self.dlg.comboBox_HW.currentIndex()==0:
                self.dlg.runButton.setEnabled(True)
                raise ValueError('Please choose a calculation method')

        elif self.dlg.toolBox.currentIndex() == 1:
            mode = 'CW'
            var = str(self.dlg.cmbCWvar.currentText())
            if self.dlg.comboBox_CW.currentIndex()==0:
                self.dlg.runButton.setEnabled(True)
                raise ValueError('Please choose a calculation method')

        else:
            self.dlg.runButton.setEnabled(True)
            raise ValueError('Please choose whether to investigate extreme high or low values')

        # Validate selected variable
        if var not in self.watch_vars:
            self.dlg.runButton.setEnabled(True)
            raise ValueError('Invalid meterological variable chosen')
        try:
            if filein.split('.')[-1]=='nc' or filein.split('.')[-1]=='txt':
                file_name = filein
            else:
                raise ValueError('Invalid data format')
        except Exception, e:
            raise Exception('Invalid input file data format')

        self.validateInputDates()

        if filein.split('.')[-1]=='nc':
            try:
                Tdata, unit, self.lat, self.lon, self.hw_start, self.hw_end = get_ncdata(file_name, self.hw_start.year, self.hw_end.year, var)
            except KeyError,e:
                raise Exception('NetCDF file must contain the variable %s in order to continue'%(e,))
            except Exception,e:
                raise e

            unit = '(' + str(unit) + ')'
            sd = QDate.fromString(self.hw_start.strftime('%Y-%m-%d'), 'yyyy-MM-dd')
            ed = QDate.fromString(self.hw_end.strftime('%Y-%m-%d'), 'yyyy-MM-dd')
            self.dlg.dateEditStart.setDate(sd)
            self.dlg.dateEditEnd.setDate(ed)
            self.dlg.textOutput_lat.setText(str(self.lat))
            self.dlg.textOutput_lon.setText(str(self.lon))

            daily_max = Tdata.resample('24H').max()
            daily_avg = Tdata.resample('24H').mean()
            daily_min = Tdata.resample('24H').min()

        elif filein.split('.')[-1]=='txt':
            # Ensure user has entered valid lat, lon, start and end times for this data
            self.validateInputCoordinates()
            self.validateInputDates()
            if var != "Tair":
                raise ValueError('Only Tair may be analysed using a text file for data. '
                                 'Other variables can be analysed if a NetCDF (.nc) input file is used, or if data is downloaded')
            Tdata = get_txtdata(file_name, self.hw_start.year, self.hw_end.year, self.hw_start, self.hw_end)
            daily_max = Tdata # we don't know what we've been given, so assume the user knows which method(s) to use given the input data
            daily_avg = Tdata
            daily_min = Tdata
            unit = u'(\N{DEGREE SIGN}C)'


        # identify HW periods
        labelsForPlot = None
        if mode == "HW":
            if self.dlg.comboBox_HW.currentIndex()==1:
                xHW = findHW_Meehl(daily_max,
                             self.hw_start, self.hw_end,
                             self.hw_start.year, self.hw_end.year,
                             t1_quantile_Meehl, t2_quantile_Meehl)
                Tplot = daily_max
                labelsForPlot = [var+'_max','Extreme high values (Meehl and Tebaldi)','HVs', unit]

            elif self.dlg.comboBox_HW.currentIndex()==2:
                xHW = findHW_Fischer(daily_max,
                             self.hw_start, self.hw_end,
                             self.hw_start.year, self.hw_end.year,
                             t3_quantile_Fischer)
                Tplot = daily_max
                labelsForPlot = [var+'_max','Extreme high values (Fischer and Schar)','HVs', unit]

            elif self.dlg.comboBox_HW.currentIndex()==3:
                xHW = findHW_Schoetter(daily_max,
                             self.hw_start, self.hw_end,
                             self.hw_start.year, self.hw_end.year,
                             t4_quantile_Schoetter, self.lat)
                Tplot = daily_max
                labelsForPlot = [var+'_max','Extreme high values (Shoetter)','HVs', unit]

            elif self.dlg.comboBox_HW.currentIndex()==4:
                xHW = findHW_Vautard(daily_avg,
                             self.hw_start, self.hw_end,
                             self.hw_start.year, self.hw_end.year,
                             t5_quantile_Vautard)
                Tplot = daily_avg
                labelsForPlot = [var+'_avg','Extreme high values (Vautard)','HVs', unit]

        if mode == "CW":
            if self.dlg.comboBox_CW.currentIndex()==1:
                xHW = findCW_Keevallik(daily_min,
                           self.hw_start, self.hw_end,
                           self.hw_start.year, self.hw_end.year,
                           t6_quantile_Keevallik)
                Tplot = daily_min
                labelsForPlot = [var+'_min','Extreme low values (Keevallik)','LVs', unit]

            elif self.dlg.comboBox_CW.currentIndex()==2:
                xHW = findCW_Srivastava(daily_min, self.hw_start, self.hw_end, TempDif_Srivastava)
                Tplot = daily_min
                labelsForPlot = [var+'_min','Extreme low values (Srivastava)','LVs', unit]

            elif self.dlg.comboBox_CW.currentIndex()==3:
                xHW = findCW_Busuioc(daily_min, self.hw_start, self.hw_end, TempDif_Busuioc)
                Tplot = daily_min
                labelsForPlot = [var+'_min','Extreme low values (Busuioc)','LVs', unit]

        if labelsForPlot is None:
            raise ValueError('Please select a calculation method')

        # write out HW results
        result = outputHW(fileout, xHW)
        try:
            if len(result) == 0:
                raise ValueError('No Heat/Cold Wave Found')
        except Exception, e:
            if mode == "HW":
                QMessageBox.critical(None, "Error", "No extreme high values found")
            if mode == "CW":
                QMessageBox.critical(None, "Error", "No extreme low values found")
            self.dlg.runButton.setEnabled(True)
            return
        else:
            result.to_csv(fileout, sep=" ", index=True, float_format='%.4f')

        ###########################################
        # plot
        ###########################################

        plotHW(self.lat, self.lon, Tplot, xHW, int(self.hw_start.strftime('%Y')), int(self.hw_end.strftime('%Y')), labelsForPlot)
        self.dlg.runButton.setEnabled(True)
