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
from qgis.gui import *
from osgeo import osr, ogr
# from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from extreme_finder_dialog import ExtremeFinderDialog
import os.path
# from datetime import datetime, timedelta, time
# import os
# import math
from ..Utilities import f90nml
# import webbrowser
# import datetime
# import time
# import gzip
# import StringIO
# import urllib2
# import tempfile
from HeatWave.findHW import *
from HeatWave.plotHW import plotHW
#from WFDEIDownloader.WFDEI_Interpolator import *

# # pandas, netCDF4 and numpy might not be shipped with QGIS
# try:
#     import pandas as pd
# except:
#     pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it
#
# try:
#     from netCDF4 import Dataset, date2num
# except:
#     raise Exception('NetCDF4 library was not found on this machine. Extremefinder will not run')
#     pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it
#
# try:
#     import numpy as np
# except:
#     pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it


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
        self.dlg.selectpoint.clicked.connect(self.select_point)
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonClose.clicked.connect(self.dlg.close)
        self.dlg.pushButtonSave.clicked.connect(self.outfile)
        self.dlg.pushButtonSave_2.clicked.connect(self.infile)

        self.dlg.pushButtonSave_2.setEnabled(False)
        self.dlg.checkBox.stateChanged.connect(self.activate_button)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)
        self.folderPathRaw = 'None'
        self.outputfile = 'None'

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Extreme Finder')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ExtremeFinder')
        self.toolbar.setObjectName(u'ExtremeFinder')

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

        # text_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'WFDEIDownloader/WFDEI-land-long-lat-height.txt')
        # gzip_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'WFDEIDownloader/WFDEI-land-long-lat-height.txt.gz')
        # try:
        #     a = open(text_file)
        # except IOError,e:
        #     try:
        #         import gzip
        #         with gzip.open(gzip_file, 'rb') as zipFile:
        #             a = zipFile.read()
        #         with open(text_file, 'wb') as outFile:
        #             outFile.write(a)
        #     except Exception, e:
        #         QMessageBox.critical(None, 'ha', str(e))
        #         raise Exception('Could not locate mappings textfile, nor decompress its zipped copy')

    def activate_button(self):
        if self.dlg.checkBox.isChecked():
            self.dlg.pushButtonSave_2.setEnabled(True)
        else:
            self.dlg.pushButtonSave_2.setEnabled(False)
            self.dlg.textInput.clear()


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

        # pandas, netCDF4 and numpy might not be shipped with QGIS
        # try:
        #     import pandas as pd
        # except:
        #     pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

        # try:
        #     from netCDF4 import Dataset, date2num
        # except:
        #     raise Exception('NetCDF4 library was not found on this machine. Extremefinder will not run')
        #     pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it
        #
        # try:
        #     import numpy as np
        # except:
        #     pass  # Suppress warnings at QGIS loading time, but an error is shown later to make up for it

        # Check the more unusual dependencies to prevent confusing errors later
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

    def infile(self):
        filename1 = QFileDialog.getOpenFileName()
        self.dlg.textInput.setText(filename1)

    def outfile(self):
        outputfile = self.fileDialog.getSaveFileName(
            None, "Save File As:", None, "Text Files (*.txt)")
        # self.fileDialog.open()
        # result = self.fileDialog.exec_()
        if not outputfile == 'None':
            self.outputfile = outputfile
            self.dlg.textOutput.setText(self.outputfile)

    def start_progress(self):
        self.dlg.runButton.setEnabled(False)

        # get current working directory
        pwd = os.path.dirname(os.path.realpath(__file__))

        # read the namelist file
        # with open() as nml_file:
        nml = f90nml.read(os.path.join(pwd, 'input.nml'))

        threshold_year_start = nml['time_control']['reference_start_year']
        threshold_year_end = nml['time_control']['reference_end_year']

        t1_quantile_Meehl = nml['method']['t1_quantile_Meehl']
        t2_quantile_Meehl = nml['method']['t2_quantile_Meehl']
        t3_quantile_Fischer = nml['method']['t3_quantile_Fischer']
        t4_quantile_Schoetter = nml['method']['t4_quantile_Schoetter']
        t5_quantile_Vautard = nml['method']['t5_quantile_Vautard']
        t6_quantile_Keevallik = nml['method']['t6_quantile_Keevallik']
        TempDif_Srivastava = nml['method']['TempDif_Srivastava']
        TempDif_Busuioc = nml['method']['TempDif_Busuioc']

        data_start_time = nml['change_data_set']['data_start_time']
        data_end_time = nml['change_data_set']['data_end_time']
        data_variable_name = nml['change_data_set']['data_variable_name']

        hw_start = self.dlg.dateEditStart.text()
        hw_start = datetime.datetime.strptime(hw_start, '%Y-%m-%d')
        hw_end = self.dlg.dateEditEnd.text()
        hw_end = datetime.datetime.strptime(hw_end, '%Y-%m-%d')
        hw_year_start = int(str(hw_start).split("-", 1)[0])
        hw_year_end = int(str(hw_end).split("-", 1)[0])
        filein = self.dlg.textInput.text()
        fileout = self.dlg.textOutput.text()
        if not os.path.exists(os.path.split(fileout)[0]):
            QMessageBox.critical(
                None, "Error", "Invalid output file location entered")
            self.dlg.runButton.setEnabled(True)
            return

        try:
            lat = float(self.dlg.textOutput_lat.text())
            if not (-90 < lat < 90):
                raise ValueError('Invalid WFDEI co-ordinates entered')
        except Exception, e:
            QMessageBox.critical(None, "Error", "Invalid latitude")
            self.dlg.runButton.setEnabled(True)
            return

        try:
            lon = float(self.dlg.textOutput_lon.text())
            if not (-180 < lon < 180):
                raise ValueError('Invalid WFDEI co-ordinates entered')
        except Exception, e:
            QMessageBox.critical(None, "Error", "Invalid longitude")
            self.dlg.runButton.setEnabled(True)
            return

        #######################################################################
        # Find heat waves
        #######################################################################
        # download Tmax data
        try:
            # get land index from the local file
            pwd = os.path.dirname(os.path.realpath(__file__))
            ncfn = os.path.join(pwd, 'validGrid.txt')
            nc_global_land = pd.read_csv(ncfn,header=None)
            land_global = nc_global_land[0].values
            xland = WFD_get_city_index(lat, lon)
            if not xland in land_global:
                raise ValueError('Invalid WATCH co-ordinates entered')
        except Exception, e:
            QMessageBox.critical(None, "Error", "Invalid location: " + str(xland))
            self.dlg.runButton.setEnabled(True)
            return

        if self.dlg.checkBox.isChecked():
            try:
                if threshold_year_start < int(str(data_start_time).split('-')[0]) or threshold_year_end > int(str(data_end_time).split('-')[0]):
                    raise ValueError('Reference year error')
            except Exception, e:
                QMessageBox.critical(None, "Error", "Invalid reference year")
                self.dlg.runButton.setEnabled(True)
                return
            file_name = filein
            Tdata = get_data(file_name, threshold_year_start, threshold_year_end, data_variable_name, data_start_time, data_end_time)
            Tmax = Tdata
            Tavg = Tdata
            Tmin = Tdata
        else:
            file_name = download(xland)
            Tmax = get_Tmax(file_name, threshold_year_start, threshold_year_end)
            Tavg = get_Tavg(file_name, threshold_year_start, threshold_year_end)
            Tmin = get_Tmin(file_name, threshold_year_start, threshold_year_end)

        try:
            if self.dlg.comboBox_HW.currentIndex()==0 and self.dlg.comboBox_CW.currentIndex()==0:
                raise ValueError('Invalid method for extreme event')
        except Exception, e:
            QMessageBox.critical(None, "Error", "Please select a method for extreme event")
            self.dlg.runButton.setEnabled(True)
            return

        try:
            if self.dlg.comboBox_HW.currentIndex()>0 and self.dlg.comboBox_CW.currentIndex()>0:
                raise ValueError('Invalid method for extreme event')
        except Exception, e:
            QMessageBox.critical(None, "Error", "Please select only one method for extreme event")
            self.dlg.runButton.setEnabled(True)
            return

        try:
            if threshold_year_start > int(str(hw_start).split('-')[0]) or threshold_year_end < int(str(hw_end).split('-')[0]):
                raise ValueError('time period error')
        except Exception, e:
            QMessageBox.critical(None, "Error", "Time period error, please change the start time or the end time")
            self.dlg.runButton.setEnabled(True)
            return

        # identify HW periods
        if self.dlg.comboBox_HW.currentIndex()==1:
            xHW = findHW_Meehl(Tmax,
                         hw_start, hw_end,
                         threshold_year_start, threshold_year_end,
                         t1_quantile_Meehl, t2_quantile_Meehl)
            Tplot = Tmax
            labelsForPlot = ['Tmax','Heat Wave','HWs']

        elif self.dlg.comboBox_HW.currentIndex()==2:
            xHW = findHW_Fischer(Tmax,
                         hw_start, hw_end,
                         threshold_year_start, threshold_year_end,
                         t3_quantile_Fischer)
            Tplot = Tmax
            labelsForPlot = ['Tmax','Heat Wave','HWs']

        elif self.dlg.comboBox_HW.currentIndex()==3:
            xHW = findHW_Schoetter(Tmax,
                         hw_start, hw_end,
                         threshold_year_start, threshold_year_end,
                         t4_quantile_Schoetter, lat)
            Tplot = Tmax
            labelsForPlot = ['Tmax','Heat Wave','HWs']

        elif self.dlg.comboBox_HW.currentIndex()==4:
            xHW = findHW_Vautard(Tavg,
                         hw_start, hw_end,
                         threshold_year_start, threshold_year_end,
                         t5_quantile_Vautard)
            Tplot = Tavg
            labelsForPlot = ['Tavg','Heat Wave','HWs']

        elif self.dlg.comboBox_CW.currentIndex()==1:
            xHW = findCW_Keevallik(Tmin,
                       hw_start, hw_end,
                       threshold_year_start, threshold_year_end,
                       t6_quantile_Keevallik)
            Tplot = Tmin
            labelsForPlot = ['Tmin','Cold Wave','CWs']

        elif self.dlg.comboBox_CW.currentIndex()==2:
            xHW = findCW_Srivastava(Tmin, hw_start, hw_end, threshold_year_start, threshold_year_end, TempDif_Srivastava)
            Tplot = Tmin
            labelsForPlot = ['Tmin','Cold Wave','CWs']

        elif self.dlg.comboBox_CW.currentIndex()==3:
            xHW = findCW_Busuioc(Tmin, hw_start, hw_end, threshold_year_start, threshold_year_end, TempDif_Busuioc)
            Tplot = Tmin
            labelsForPlot = ['Tmin','Cold Wave','CWs']

        # write out HW results
        result = outputHW(fileout, xHW)
        try:
            if len(result) == 0:
                raise ValueError('No Heat/Cold Wave Found')
        except Exception, e:
            if self.dlg.comboBox_HW.currentIndex()>0:
                QMessageBox.critical(None, "Error", "No Heat Wave Found")
            elif self.dlg.comboBox_CW.currentIndex()>0:
                QMessageBox.critical(None, "Error", "No Cold Wave Found")
            self.dlg.runButton.setEnabled(True)
            return
        else:
            result.to_csv(fileout, sep=" ", index=True, float_format='%.4f')
        # result.to_csv(fileout, sep=" ", index=True, float_format='%.4f')

        ###########################################
        # plot
        ###########################################

        plotHW(lat,lon,Tplot, xHW, hw_year_start, hw_year_end, labelsForPlot)

        self.dlg.runButton.setEnabled(True)
