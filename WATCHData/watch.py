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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QObject, pyqtSignal, QThread
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.gui import *
from osgeo import osr, ogr
from watch_dialog import WATCHDataDialog
from calendar import monthrange
import os.path
import shutil
import webbrowser
from ..Utilities.ncWMSConnector import NCWMS_Connector
from WFDEIDownloader.WFDEI_Interpolator import *
import traceback
import datetime
from WatchWorker import WatchWorker

class DownloadDataWorker(QObject):
    # Worker to get netCDF data using a separate thread
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    def __init__(self, hw_start, hw_end, watch_vars, ll_lat, ll_lon, ur_lat, ur_lon):
        QObject.__init__(self)
        self.hw_start = hw_start
        self.hw_end = hw_end
        self.watch_vars = watch_vars
        self.ll_lat = ll_lat
        self.ll_lon = ll_lon
        self.ur_lat = ur_lat
        self.ur_lon = ur_lon
        self.downloader = NCWMS_Connector()

    def kill(self):
        self.downloader.kill()

    def run(self):
        try:
            output = self.webToTimeseries(self.hw_start, self.hw_end, self.watch_vars, self.ll_lat, self.ll_lon,self. ur_lat, self.ur_lon, self.update)
            self.finished.emit(output)
        except Exception,e:
            self.error.emit(e, traceback.format_exc())

    def webToTimeseries(self, hw_start, hw_end, watch_vars, ll_lat, ll_lon, ur_lat, ur_lon, update=None):
        '''
        Take WCS raster layer and save to local geoTiff
        :param baseURL: Server URL up to the /wcs? part where the query string begins (not including the question mark)
        :param layer_name: The coverage name on the WCS server
        :param output_file: File to save as (GeoTIFF)
        :param bbox: dict with WGS84 coordinates {xmin: float <lower left longitude>, xmax:float, ymin:float <upper right latitude>, ymax:float}
        :param resolution: dict {x:float, y:float} containing the resolution to use
        :param srs: string e.g. EPSG:4326: The layer CRS string
        :return: Path to output file
        '''
        self.downloader.get_data(start_date=hw_start, # Connector will take the first moment of this date
                            end_date=hw_end, # Connector will take the final second of this date
                            variables=watch_vars, # Get all variables
                            lowerleft_lat = ll_lat,
                            lowerleft_lon = ll_lon,
                            upperright_lat= ur_lat,
                            upperright_lon= ur_lon,
                            update=update)
        temp_netcdf = self.downloader.average_data(None, 'mean')
        return temp_netcdf

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
        # connections to buttons

        self.dlg = WATCHDataDialog()
        self.dlg.cmdSelectPoint.clicked.connect(self.select_point)
        self.dlg.cmdRunDownload.clicked.connect(self.download)
        self.dlg.cmdChooseLQFResults.clicked.connect(self.folderAH)
        self.dlg.cmdRunRefine.clicked.connect(self.refine)
        self.dlg.pushButtonHelp.clicked.connect(self.help)

        # Disable refiner buttons to start with (no downloaded data to refine!)
        self.dlg.cmdChooseLQFResults.setEnabled(False)
        self.dlg.cmdRunRefine.setEnabled(False)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        self.dlg.progressBar.setRange(0,100)
        self.dlg.progressBar.setValue(0)

        self.watch_vars =  ['Tair',
                                 'Wind',
                                 'LWdown',
                                 'PSurf',
                                 'Qair',
                                 'Rainf',
                                 'Snowf',
                                 'SWdown']
        # Parameters for downloader
        self.lat = None
        self.lon = None
        self.start_date = None
        self.end_date = None
        self.save_downloaded_file = None

        # Parameters for refiner
        self.site_height = None
        self.utc_offset = None
        self.rainy_hours = None
        self.save_refined_file = None
        self.lqf_path = None

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&WATCH data')
        # TODO: We are going to let the user set this up in a future iteration

        # get reference to the canvas
        self.canvas = self.iface.mapCanvas()
        self.degree = 5.0
        self.point = None
        self.pointx = None
        self.pointy = None

        # #g pin tool
        self.pointTool = QgsMapToolEmitPoint(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)

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

    def validate_downloader_input(self):
        ''' Validates user input for downloader section of form. Raises exception if a problem, commits
        parameters to object if OK '''

        # validate and record the  latitude and longitude boxes (must be WGS84)'''
        try:
            lon = float(self.dlg.txtLon.text())
        except:
            raise ValueError('Invalid longitude co-ordinate entered')

        if not (-180 < lon < 180):
            raise ValueError('Invalid longitude co-ordinate entered (must be -180 to 180)')

        try:
            lat = float(self.dlg.txtLat.text())
        except:
            raise ValueError('Invalid latitude co-ordinate entered')
        if not (-90 < lat < 90):
            raise ValueError('Invalid latitude co-ordinate entered (must be -90 to 90)')

        self.lat = lat
        self.lon = lon

        # validate date range and add to object properties if OK
        start_date = self.dlg.txtStartDate.text()
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m')
        except Exception:
            raise ValueError('Invalid start date (%s) entered'%(start_date,))

        end_date = self.dlg.txtEndDate.text()
        try:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m')
        except Exception:
            raise ValueError('Invalid end date (%s) entered'%(end_date,))

        days = monthrange(end_date.year, end_date.month)[1]
        td = datetime.timedelta(days=days-1) # Use final day of month. ncWMSconnector takes the full final day of data
        end_date = end_date + td
        self.start_date = start_date
        self.end_date = end_date

    def validate_refiner_input(self):
        ''' Validates user input for downloader section of form. Raises exception if a problem, commits
        parameters to object if OK '''
        try:
            hgt = float(self.dlg.textOutput_hgt.text())
        except:
            raise ValueError('Site height must be a number')
        if hgt<0:
            raise ValueError('Site height must be positive or zero')

        self.site_height = hgt
        self.rainy_hours = self.dlg.spinBoxRain.value()

        input_AH_path = self.dlg.textOutput_AH.text()
        if len(input_AH_path) != 0:
            if not os.path.exists(input_AH_path):
                raise ValueError('Directory containing LQF outputs (%s) not found'%(input_AH_path,))
            self.lqf_path = input_AH_path

    def refine(self):
        ''' Refines downloaded data'''
        try:
            self.validate_refiner_input() # Validate input co-ordinates and time range
            # Before starting, ask user where to save netCDF file
            refined_filename = self.fileDialog.getSaveFileName(None, "Save refined climate data to...", None, "Text Files (*.txt)")
            if (refined_filename is None) or (len(refined_filename) == 0):
                return
        except Exception, e:
            QMessageBox.critical(None, "Error", str(e))
            self.setRefinerButtonState(True)
            self.setDownloaderButtonState(True)
            return

        self.save_refined_file = refined_filename
        self.setDownloaderButtonState(False)
        self.setRefinerButtonState(False)
        UTC_offset_h = self.dlg.spinBoxUTC.value()

        # Set up and start worker thread
        worker = WatchWorker(rawdata=self.save_downloaded_file,
                             datestart=self.start_date,
                             dateend=self.end_date,
                             input_AH_path=self.lqf_path,
                             output_path=self.save_refined_file,
                             lat=self.lat,
                             lon=self.lon,
                             hgt=self.site_height,
                             UTC_offset_h=UTC_offset_h,
                             rainAmongN=self.rainy_hours)

        thr = QThread(self.dlg)
        worker.moveToThread(thr)
        worker.finished.connect(self.refine_worker_finished)
        worker.error.connect(self.refine_worker_error)
        worker.update.connect(self.update_progress)

        thr.started.connect(worker.run)
        thr.start()
        self.refine_thread = thr
        self.refine_worker = worker
        self.dlg.progressBar.setValue(0)

    def select_point(self):  # Connected to "Seelct Point on Canves"
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

        self.dlg.txtLon.setText(str(latlon.GetX()))
        self.dlg.txtLat.setText(str(latlon.GetY()))

    def run(self):
        # Check the more unusual dependencies to prevent confusing errors later
        try:
            import pandas
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the pandas package '
                                                'to be installed. Please consult the FAQ in the manual for further '
                                                'information on how to install missing python packages.')
            return
        try:
            import ftplib
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the ftplib package '
                                                'to be installed. Please consult the FAQ in the manual for further '
                                                'information on how to install missing python packages.')
            return
        try:
            import scipy
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the scipy package '
                                                'to be installed. Please consult the FAQ in the manual for further '
                                                'information on how to install missing python packages.')
            return
        try:
            import requests
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The WATCH data download/extract feature requires the requests package '
                                                'to be installed. Please consult the FAQ in the manual for further '
                                                'information on how to install missing python packages.')
            return
        try:
            import netCDF4 as nc4
        except Exception, e:
            QMessageBox.critical(None, 'Error',
                                 'The WATCH data download/extract feature requires the NetCDF4 Python package '
                                 'to be installed. Please consult the FAQ in the manual for further '
                                 'information on how to install missing python packages.')
            return
        self.dlg.show()
        result = self.dlg.exec_()

    def folderAH(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathAH = self.fileDialog.selectedFiles()
            self.dlg.textOutput_AH.setText(self.folderPathAH[0])

    def help(self):
        url = "http://umep-docs.readthedocs.io/en/latest/pre-processor/Meteorological%20Data%20" \
              "Download%20data%20(WATCH).html"
        webbrowser.open_new_tab(url)

    def refine_worker_finished(self):
        self.refine_worker.deleteLater()
        self.refine_thread.quit()
        self.refine_thread.wait()  # Wait for quit
        self.refine_thread.deleteLater()  # Flag for deletion
        self.setRefinerButtonState(True)
        self.setDownloaderButtonState(True)
        QMessageBox.information(None, "Climate data refiner", "Data processed")
        # self.iface.messageBar().pushMessage("Climate data refiner", "Data processed", level=QgsMessageBar.INFO)
        file_pattern = os.path.splitext(self.save_refined_file)[0] + '<YEAR>.txt'
        self.dlg.lblSavedRefined.setText(file_pattern)

    def refine_worker_error(self, strException):
        if type(strException) is not str:
            strException = str(strException)
        QMessageBox.critical(None, "Climate data refiner error:", strException)

    def download(self):
        '''
        Downloads WATCH data to netCDF file locally.
        Returns
        -------
        '''

        try:
            self.validate_downloader_input() # Validate input co-ordinates and time range
            # Before starting, ask user where to save netCDF file
            download_filename = self.fileDialog.getSaveFileName(None, "Save downloaded WATCH data to...", None, "NetCDF Files (*.nc)")
            if (download_filename is None) or (len(download_filename) == 0):
                return
        except Exception, e:
            QMessageBox.critical(None, "Error", str(e))
            return

        self.setDownloaderButtonState(False)
        self.setRefinerButtonState(False)

        self.save_downloaded_file = download_filename

        # Since NCWMS connector needs a bbox, place these coordinates at the centre of a very small box
        ll_lat = self.lat - 0.0001
        ll_lon = self.lon - 0.0001
        ur_lat = self.lat + 0.0001
        ur_lon = self.lon + 0.0001

        # Do download in separate thread and track progress
        downloadWorker = DownloadDataWorker(self.start_date, self.end_date, self.watch_vars, ll_lat, ll_lon, ur_lat, ur_lon)
        thr = QThread(self.dlg)
        downloadWorker.moveToThread(thr)
        downloadWorker.update.connect(self.update_progress)
        downloadWorker.error.connect(self.download_error)
        downloadWorker.finished.connect(self.downloadWorkerFinished)
        thr.started.connect(downloadWorker.run)
        thr.start()

        self.downloadThread = thr
        self.downloadWorker = downloadWorker
        self.dlg.cmdRunDownload.clicked.disconnect()
        self.dlg.cmdRunDownload.setText('Cancel')
        self.dlg.cmdRunDownload.clicked.connect(self.abort_download)
        self.dlg.progressBar.setValue(0)

    def update_progress(self, returns):
        ''' Updates progress bar during download'''
        self.dlg.progressBar.setValue(returns['progress'])

    def download_error(self, exception, text):
        self.setDownloaderButtonState(True)
        self.setRefinerButtonState(False)
        QMessageBox.critical(None, "Error", 'Data download not completed: %s'%(str(exception),))

    def abort_download(self):
        self.downloadWorker.kill()
        self.setDownloaderButtonState(True)  # Enable all buttons in downloader.
        self.setRefinerButtonState(False)    # Disable refiner as we've lost track of the old data now
        self.dlg.cmdRunDownload.clicked.disconnect()
        self.dlg.cmdRunDownload.setText('Run')
        self.dlg.cmdRunDownload.clicked.connect(self.download)
        self.dlg.progressBar.setValue(0)

    def downloadWorkerFinished(self, temp_netcdf):
        # Ask the user where they'd like to save the file
        self.setDownloaderButtonState(True)  # Enable all buttons
        self.setRefinerButtonState(True)
        self.dlg.cmdRunDownload.clicked.disconnect()
        self.dlg.cmdRunDownload.setText('Run')
        self.dlg.cmdRunDownload.clicked.connect(self.download)
        if self.save_downloaded_file is not None:
            shutil.copyfile(temp_netcdf, self.save_downloaded_file)

        if os.path.exists(temp_netcdf): # remove the temp file
            try:
                os.remove(temp_netcdf)
            except:
                pass

        # Update the UI to reflect the saved file
        self.dlg.lblSavedDownloaded.setText(self.save_downloaded_file)

    def setDownloaderButtonState(self, state):
        ''' Enable or disable all dialog buttons in downloader section
        :param state: boolean: True or False. Reflects button state'''
        self.dlg.cmdSelectPoint.setEnabled(state)
        self.dlg.cmdRunDownload.setEnabled(state)
        self.dlg.cmdChooseLQFResults.setEnabled(state)
        self.dlg.cmdRunRefine.setEnabled(state)
        self.dlg.cmdClose.setEnabled(state)
        self.dlg.txtLat.setEnabled(state)
        self.dlg.txtLon.setEnabled(state)
        self.dlg.txtStartDate.setEnabled(state)
        self.dlg.txtEndDate.setEnabled(state)

    def setRefinerButtonState(self, state):
        ''' Enable or disable all dialog buttons in refiner section
        :param state: boolean: True or False. Reflects button state'''
        self.dlg.cmdSelectPoint.setEnabled(state)
        self.dlg.cmdRunDownload.setEnabled(state)
        self.dlg.textOutput_hgt.setEnabled(state)
        self.dlg.spinBoxUTC.setEnabled(state)
        self.dlg.spinBoxRain.setEnabled(state)
        self.dlg.textOutput_AH.setEnabled(state)