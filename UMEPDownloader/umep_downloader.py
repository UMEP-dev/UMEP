# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UMEP_Data_Download
                                 A QGIS plugin
 UMEP approved data downloader
                              -------------------
        begin                : 2017-01-19
        git sha              : $Format:%H$
        copyright            : (C) 2017 by a
        email                : a
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
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QThread
from qgis.PyQt.QtWidgets import QAction, QAbstractItemView, QMessageBox, QWidget, QHeaderView, QTableWidgetItem, QListWidgetItem, QFileDialog
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle, QgsPointXY, QgsGeometry, QgsRasterLayer, QgsProject
# Initialize Qt resources from file resources.py
# from . import resources
# Import the code for the dialog
from .umep_downloader_dialog import UMEP_Data_DownloadDialog
import os.path
from osgeo import gdal
import shutil
import osr
try:
    # Assuming in UMEP folder strcuture, so get f90nml from Utilities
    from ..Utilities import f90nml
except:
    # If not present, assume plugin is standalone and has its own f90nml
    import f90nml

import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as etree
import tempfile
import numpy as np
from .GetMetaWorker import GetMetaWorker
from .DownloadDataWorker import DownloadDataWorker
import sys, os, subprocess

def getLayerMetadata(baseURL, layer_name):
    ''' Uses WCS DescribeCoverage request to get metadata from a layer of interest on a remote server
    :param baseURL:
    :param layer_name:
    :return dict describing the grid {nXpoints, nYpoints, minX, minY, maxX, maxY
    '''

    #### WCS data: For grid resolution and other detailed stuff
    # Get data
    coverageInfoURL = baseURL + '/wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=DescribeCoverage&coverage=%s'%(layer_name,)
    f = urllib.request.urlopen(coverageInfoURL)
    data = f.read()
    f.close()
    root = etree.fromstring(data)
    offering = root.find("{http://www.opengis.net/wcs}CoverageOffering")
    if offering is None:
        return None # There must be a problem with this data source if there's no offering

    spatialDomainField = root.find("{http://www.opengis.net/wcs}CoverageOffering/"+
            "{http://www.opengis.net/wcs}domainSet/"+
            "{http://www.opengis.net/wcs}spatialDomain")

    envelopeField = spatialDomainField.find("{http://www.opengis.net/gml}Envelope")
    srs = envelopeField.get('srsName')
    gridField = spatialDomainField.find("{http://www.opengis.net/gml}RectifiedGrid")

    # Get resolution of raster
    dimensionsOrder = []
    resolutions = []
    for k in gridField:
        # Get the order of the x and y dimensions. These must come before the resolutions
        # if k.tag == '{http://www.opengis.net/gml}axisName':
        #     temp = dimensionsOrder.append('x') if k.text == "x" else None
        #     temp = dimensionsOrder.append('y') if k.text == "y" else None
        # # Get the resolutions of the respective dimensions
        # if k.tag == '{http://www.opengis.net/gml}offsetVector':
        #     # Pull out the right dimension based on the order identified above
        #     vals = k.text.split(' ')
        #     if (len(resolutions) == 1):
        #         resolutions.append(float(vals[0])) if dimensionsOrder[1]=='x' else resolutions.append(vals[1])
        #     if (len(resolutions) == 0):
        #         resolutions.append(float(vals[0])) if dimensionsOrder[0]=='x' else resolutions.append(vals[1])
        if k.tag == '{http://www.opengis.net/gml}offsetVector':
            # assume the offset vector is always specified with horizontal component first
            vals = k.text.split(' ')
            if (len(resolutions) == 1): # Second offset
                resolutions.append(float(vals[1]))
            if (len(resolutions) == 0): # First offset
                resolutions.append(float(vals[0]))
    if len(resolutions) != 2:
        res = None
    else:
        # res = {'x':float(resolutions[dimensionsOrder.index('x')]),
        #        'y':float(resolutions[dimensionsOrder.index('y')])}
        res = {'x':abs(float(resolutions[0])),
               'y':abs(float(resolutions[1]))}
    # Get number of grid cells of raster
    limField = gridField.find("{http://www.opengis.net/gml}limits/")
    numPoints = None
    if limField is not None:
        lowVals = limField.find("{http://www.opengis.net/gml}low")
        highVals = limField.find("{http://www.opengis.net/gml}high")
        if (lowVals is not None) and (highVals is not None):
            lowVals = list(map(int, lowVals.text.split(" ")))
            highVals = list(map(int, highVals.text.split(" ")))
            numXpoints = highVals[0] - lowVals[0]
            numYpoints = highVals[1] - lowVals[1]
            numPoints = {'x':numXpoints, 'y':numYpoints}
    # Get origin of grid in native CRS
    originField = gridField.find("{http://www.opengis.net/gml}origin/{http://www.opengis.net/gml}pos")
    origin = list(map(float, originField.text.split(" "))) # assume x and y respectively.
    originDict = {'x':origin[0], 'y':origin[1]}

    # Get grid extent in native SRS
    if envelopeField is not None:
        envelopeVals = envelopeField.findall("{http://www.opengis.net/gml}pos")
        lowVals = envelopeVals[0]
        highVals = envelopeVals[1]
        if (lowVals is not None) and (highVals is not None):

            lowVals = list(map(float, lowVals.text.split(" ")))

            highVals = list(map(float, highVals.text.split(" ")))
            extentDict = {'xMin':lowVals[0], 'xMax':highVals[0], 'yMin':lowVals[1], 'yMax':highVals[1]}


    result ={'SRS':srs, 'gridPoints': numPoints, 'resolution':res, 'origin':originDict, 'extent':extentDict}

    return result

class UMEP_Data_Download(object):
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
            'UMEP_Data_Download_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = UMEP_Data_DownloadDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&UMEP data downloader')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'UMEP_Data_Download')
        self.toolbar.setObjectName(u'UMEP_Data_Download')

        self.bbox = {}

        self.dlg.cmdRunCancel.clicked.connect(self.runDownload_errorWrapper)

        self.dlg.cmdClose.clicked.connect(self.dlg.close)
        self.dlg.cmdUseCanvas.clicked.connect(self.getCanvasExtent)
        self.dlg.cmdRefreshCatalogue.clicked.connect(self.refreshList)
        self.dlg.tblDatasets.itemSelectionChanged.connect(self.updateAbstract)
        self.dlg.progressBar.setRange(0,100)
        self.dlg.progressBar.setValue(0)
        self.rasterLayer = None
        self.extraAbstractText = ''
        # Get remote namelist and save to temp file
        self.refreshList()  # Load remotely-stored catalogue of data sources

    def runDownload_errorWrapper(self):
        try:
            self.runDownload()
        except Exception as e:
            QMessageBox.critical(None, 'Error', str(e))

    def updateAbstract(self):
        '''
        Update abstract box using WMS information (if available)
        :return:
        '''

        if self.dlg.tblDatasets.currentRow() in [-1, None]:
            return
        collection = self.dlg.lstCategory.selectedItems()
        collection = self.readacross[collection[0].text()]
        # Omit first key from list as it should just be collection label

        if self.dlg.tblDatasets.currentRow() > len(list(self.catalogue[collection].keys()))-1:
            # If the selected row is beyond the end of the requested data, it's probably a bug
            return
        try:
            subEntry = list(self.catalogue[collection].keys())[1:][self.dlg.tblDatasets.currentRow()]
        except:
            return
        baseURL =           self.catalogue[collection][subEntry][2]
        dataSourceType =    self.catalogue[collection][subEntry][1]
        layerName =         self.catalogue[collection][subEntry][3]
        dataSourceName =    self.catalogue[collection][subEntry][0]
        layerDescription =  self.catalogue[collection][subEntry][4]
        layerDate =         self.catalogue[collection][subEntry][5]
        self.extraAbstractText = '\n\nAdditional Information:\n' + self.catalogue[collection][subEntry][8]  # Extra text for abstract box from namelist
        # Get the WMS info in another thread because it takes just a little time
        wmsMetaDataWorker = GetMetaWorker(baseURL, layerName)
        thr = QThread(self.dlg)
        wmsMetaDataWorker.moveToThread(thr)
        wmsMetaDataWorker.update.connect(self.updateAbstractBox)
        wmsMetaDataWorker.finished.connect(self.wmsWorkerFinished)
        thr.started.connect(wmsMetaDataWorker.run)
        thr.start()
        self.thread = thr
        self.worker = wmsMetaDataWorker

    def wmsWorkerFinished(self, returns):
        try:
            self.worker.deleteLater()
            self.thread.quit()
            self.thread.wait()
            self.thread.deleteLater()
            self.updateAbstractBox(returns)
        except:
            pass

    def updateAbstractBox(self, absData):
        if absData['Abstract'] is None:
            abs = 'No abstract available.'
        else:
            abs = absData['Abstract'] + self.extraAbstractText
        self.dlg.txtAbstract.setPlainText(abs)

    def refreshList(self):
        try:
            self.dlg.lstCategory.itemSelectionChanged.disconnect()
        except Exception:
            pass

        # urllib.request.urlretrieve('http://www.urban-climate.net/umep/repo/catalogue.nml', self.plugin_dir + '/catalogue.nml')
        tempFile = self.plugin_dir + '/catalogue.nml'

        # THIS PART DOES NOT WORK IN QGIS3
        # tempFile = tempfile.mktemp(".nml")
        # with open(tempFile, "w") as tmp:
        #     tmp.write(str(f.read()))
        # f.close()
        # tmp.close()

        self.catalogue = f90nml.read(tempFile)

        # Populate categories side
        self.dlg.tblDatasets.setColumnCount(5)

        self.dlg.tblDatasets.setHorizontalHeaderLabels("Source;Description;Date;Resolution;Extent".split(";"))
        self.readacross = {}
        self.dlg.lstCategory.clear()
        for i, key in enumerate(self.catalogue.keys()):  # Each group
            try:
                label = self.catalogue[key]['_label_']
                self.readacross[label] = key
                item = QListWidgetItem(label)
                self.dlg.lstCategory.addItem(item)

                if i == 0:
                    self.dlg.lstCategory.itemSelectionChanged.connect(self.updateList)
                    item.setSelected(True)

            except:
                raise ValueError('The catalogue file was not valid')

    def getCanvasExtent(self):
        ''' Get extent of canvas as WGS84 co-ordinates.
            Lots of new untested for QGIS3 '''

        canvas = self.iface.mapCanvas()
        # canvasEPSG = canvas.mapRenderer().destinationCrs().authid()
        canvasEPSG = canvas.mapSettings().destinationCrs().authid()  # New for QGIS3
        # If EPSG:4326 (WGS84), then no need to do anything. If not, then transform.
        if canvasEPSG != "EPSG:4326":
            # Reproject to WGS84 (EPSG:4326)
            # canvas_crs = QgsCoordinateReferenceSystem()
            # canvas_crs.createFromUserInput(canvasEPSG)

            can_wkt = canvas.mapSettings().destinationCrs().toWkt()
            canvas_crs = osr.SpatialReference()
            canvas_crs.ImportFromWkt(can_wkt)

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

            target_crs = osr.SpatialReference()
            target_crs.ImportFromWkt(wgs84_wkt)

            # transform = osr.CoordinateTransformation(old_cs, new_cs)
            # target_crs = QgsCoordinateReferenceSystem(4326)
            # target_crs.createFromUserInput('EPSG:4326')
            # crsSrc = QgsCoordinateReferenceSystem(4326)
            # crs_transform = QgsCoordinateTransform(canvas_crs, target_crs)
            crs_transform = osr.CoordinateTransformation(canvas_crs, target_crs)  # New for QGIS3
            # canvas_geom = crs_transform.transform(canvas.extent())
            # canvas_geom = crs_transform.TransformPoints(canvas.extent())

            extentCanvas = self.iface.mapCanvas().extent()

            canminx = extentCanvas.xMinimum()
            canmaxx = extentCanvas.xMaximum()
            canminy = extentCanvas.yMinimum()
            canmaxy = extentCanvas.yMaximum()

            canxymin = crs_transform.TransformPoint(canminx, canminy)
            canxymax = crs_transform.TransformPoint(canmaxx, canmaxy)

            self.bbox['xmin'] = float(canxymin[0])
            self.bbox['xmax'] = float(canxymax[0])
            self.bbox['ymin'] = float(canxymin[1])
            self.bbox['ymax'] = float(canxymax[1])
        else:
            canvas_geom = canvas.extent()

            self.bbox['xmin'] = canvas_geom.xMinimum()
            self.bbox['xmax'] = canvas_geom.xMaximum()
            self.bbox['ymin'] = canvas_geom.yMinimum()
            self.bbox['ymax'] = canvas_geom.yMaximum()

        # Update UI elements
        self.dlg.txtLowerLeftLong.setValue(self.bbox['xmin'])
        self.dlg.txtLowerLeftLat.setValue(self.bbox['ymin'])
        self.dlg.txtUpperRightLong.setValue(self.bbox['xmax'])
        self.dlg.txtUpperRightLat.setValue(self.bbox['ymax'])

    def updateList(self):
        # Triggers when lstCategory is updated to refresh the table of datasets

        items = self.dlg.lstCategory.selectedItems()
        self.dlg.tblDatasets.clearSelection()
        self.dlg.tblDatasets.clear()

        txt = self.readacross[items[0].text()]

        self.dlg.tblDatasets.setRowCount(len(list(self.catalogue[txt].keys()))-1)
        self.dlg.tblDatasets.setHorizontalHeaderLabels("Source;Description;Date;Resolution;Extent".split(";"))
        self.dlg.tblDatasets.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.dlg.tblDatasets.horizontalHeader()
        header.setResizeMode(0, QHeaderView.ResizeToContents)
        header.setResizeMode(1, QHeaderView.ResizeToContents)
        header.setResizeMode(2, QHeaderView.ResizeToContents)
        header.setResizeMode(3, QHeaderView.ResizeToContents)
        header.setResizeMode(4, QHeaderView.ResizeToContents)
        # Set column widths
        indicesToUse = [0, 4, 5, 6, 7]  # Use these entries from each list in the catalogue file
        idx = 0
        for i,dataSource in enumerate(self.catalogue[txt]):  # Each resource within each group
            if dataSource == '_label_':
                continue # This is the category label
            for j in range(len(indicesToUse)):
                text = self.catalogue[txt][dataSource][indicesToUse[j]]
                item= QTableWidgetItem(text)
                item.setFlags( Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.dlg.tblDatasets.setItem(idx,j, item)
            idx+=1

        # Select the first entry in the selected category
        # Clear the abstract box
        self.dlg.txtAbstract.setPlainText('Please choose a dataset')

    def runDownload(self):
        # Figure out which entry the user wants
        # validate inputs

        collection = self.dlg.lstCategory.selectedItems()
        if len(collection) == 0:
            raise ValueError('Please select a category and dataset')

        if self.dlg.tblDatasets.currentRow() in [-1,None]:
            raise ValueError('Please select a dataset from the chosen catgory')

        # Validate bounding box
        try:
            self.bbox['xmin'] = float(self.dlg.txtLowerLeftLong.value())
            self.bbox['ymin'] = float(self.dlg.txtLowerLeftLat.value())
            self.bbox['xmax'] = float(self.dlg.txtUpperRightLong.value())
            self.bbox['ymax'] = float(self.dlg.txtUpperRightLat.value())
        except ValueError:
            raise ValueError('Bounding box co-ordinates must be numeric')

        if self.bbox['xmin'] >= self.bbox['xmax']:
            self.bbox = {}
            raise ValueError('Lower left longitude must be less than upper right longitude')

        if self.bbox['ymin'] >= self.bbox['ymax']:
            self.bbox = {}
            raise ValueError('Lower left latitude must be less than upper right longitude')

        collection = self.readacross[collection[0].text()]
        # Omit first key from list as it should just be collection label

        if self.dlg.tblDatasets.currentRow() > len(list(self.catalogue[collection].keys())[1:]):
            # If the selected row is beyond the end of the requested data, it's probably a bug
            return

        subEntry = list(self.catalogue[collection].keys())[1:][self.dlg.tblDatasets.currentRow()]
        baseURL =           self.catalogue[collection][subEntry][2]
        #dataSourceType =    self.catalogue[collection][subEntry][1]
        layerName =         self.catalogue[collection][subEntry][3]
        #dataSourceName =    self.catalogue[collection][subEntry][0]
        #layerDescription =  self.catalogue[collection][subEntry][4]
        #layerDate =         self.catalogue[collection][subEntry][5]

        # Compare the requested data with the native parameters of the layer and tell the user something helpful
        # Read metadata
        try:
            meta = getLayerMetadata(baseURL, urllib.parse.quote(layerName))
        except:
            meta = None

        if meta is None:
            raise Exception('This dataset is not currently available')

        # Transform the requested domain into the CRS of the layer on the server
        if meta['SRS'] != "EPSG:4326":
            request_crs = QgsCoordinateReferenceSystem()
            request_crs.createFromUserInput("EPSG:4326")
            target_crs = QgsCoordinateReferenceSystem()
            target_crs.createFromUserInput(meta['SRS'])
            crs_transform = QgsCoordinateTransform(request_crs, target_crs)
            requested_rect = QgsRectangle(QgsPointXY(self.bbox['xmin'], self.bbox['ymin']), QgsPointXY(self.bbox['xmax'], self.bbox['ymax']))
            transformed_rect = QgsGeometry().fromRect(crs_transform.transform(requested_rect)).boundingBox()
        else:
            transformed_rect = QgsRectangle(QgsPointXY(self.bbox['xmin'], self.bbox['ymin']), QgsPointXY(self.bbox['xmax'], self.bbox['ymax']))

        request_bbox = {}
        request_bbox['xmin'] = transformed_rect.xMinimum()
        request_bbox['xmax'] = transformed_rect.xMaximum()
        request_bbox['ymin'] = transformed_rect.yMinimum()
        request_bbox['ymax'] = transformed_rect.yMaximum()

        # Check that some of the raster data actually falls in the requested bbox
        if (meta['extent']['xMax'] < request_bbox['xmin']) | (meta['extent']['xMin'] > request_bbox['xmax']):
            raise ValueError('There is no data in the requested bounding box (invalid longitude range)')

        if (meta['extent']['yMax'] < request_bbox['ymin']) | (meta['extent']['yMin'] > request_bbox['ymax']):
            raise ValueError('There is no data in the requested bounding box (invalid latitude range)')

        # Estimate resolution of request in native CRS of layer
        req_resX = (request_bbox['xmax'] - request_bbox['xmin'])/500.0
        req_resY = (request_bbox['ymax'] - request_bbox['ymin'])/500.0

        if (req_resY > meta['resolution']['y']) or (req_resX > meta['resolution']['x']):
            res_message = 'The largest raster returned by this program is 500x500. The dataset has higher native ' \
                          'resolution than this, so the downloaded file will be interpolated. Is this OK?'
            req_res = {'x': req_resX, 'y': req_resY}
            native = False
        else:
            if not self.dlg.checkBoxReproject.isChecked():
                res_message = 'The data will be downloaded at its native resolution. Is this OK?'
            req_res = {'x':meta['resolution']['x'], 'y':meta['resolution']['y']}
            native = True

        if not self.dlg.checkBoxReproject.isChecked():
            reply = QMessageBox.question(QWidget(), 'Data extraction', res_message, QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        # If downloading at native resolution, then ensure the requested bounding box aligns with grid of raster. Prevents interpolation effects.
        if native:
            xLocs = np.arange(meta['extent']['xMin'],
                              meta['extent']['xMin'] + meta['resolution']['x']*(meta['gridPoints']['x']+1),
                              meta['resolution']['x'])
            xMinLoc = np.argmin(abs(request_bbox['xmin'] - xLocs)) # Index of nearest x grid line to minimum
            xMaxLoc = np.argmin(abs(request_bbox['xmax'] - xLocs)) # Index of nearest x grid line to maximum

            yLocs = np.arange(meta['extent']['yMin'],
                              meta['extent']['yMin'] + meta['resolution']['y']*(meta['gridPoints']['y']+1),
                              meta['resolution']['y'])
            yMinLoc = np.argmin(abs(request_bbox['ymin'] - yLocs)) # Index of nearest y grid line to minimum
            yMaxLoc = np.argmin(abs(request_bbox['ymax'] - yLocs)) # Index of nearest u grid line to maximum

            # Set box edges - based on inspection of results, we need to shift the coordinates derived above by 0.5* resolution
            request_bbox['xmin'] = xLocs[xMinLoc] - 1 * meta['resolution']['x']
            request_bbox['xmax'] = xLocs[xMaxLoc] + 1 * meta['resolution']['x']
            request_bbox['ymin'] = yLocs[yMinLoc] - 1 * meta['resolution']['y']
            request_bbox['ymax'] = yLocs[yMaxLoc] + 1 * meta['resolution']['y']

        if (abs(request_bbox['xmin']-request_bbox['xmax']) < 3*meta['resolution']['x']) | (abs(request_bbox['ymin']-request_bbox['ymax']) < 3*meta['resolution']['y']):
            raise ValueError('The requested area is too small. It must be at least 3x3 pixels. Widen the area and try again')

        # Everything checks out, so try downloading the layer. Present the user with a Save As...
        self.filename = QFileDialog.getSaveFileName(caption='Save GeoTIFF file as...', filter='*.tif')
        if self.filename is None:
            return

        if self.dlg.checkBoxReproject.isChecked():
            if self.dlg.spinBoxResolution.value() < 1:
                QMessageBox.critical(None, 'Error in pixel resolution raster data', "Pixel resolution must be greater than 1 map unit")
                return

            self.filename2 = self.filename[0]
            self.filename = self.plugin_dir + '/tempgrid.tif'
            self.crs = meta['SRS']

        ## TESTING
        # bboxString = "%f,%f,%f,%f" % (self.bbox['xmin'], self.bbox['ymin'], self.bbox['xmax'], self.bbox['ymax'])
        # bigURL = baseURL + '/wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&coverage=%s&identifier=%s&bbox=%s&FORMAT=image/geotiff&CRS=%s&RESX=%f&RESY=%f'%(layerName, layerName, bboxString, meta['SRS'], req_res['x'], req_res['y'])
        # print(bigURL)
        # dataOut = "c:/temp/testing.tif"
        # urllib.request.urlretrieve(bigURL, dataOut)
        # return

        # Get the WMS info in another thread because it takes just a little time
        downloadWorker = DownloadDataWorker(baseURL, layerName, self.filename[0], request_bbox, req_res, meta['SRS'])
        thr = QThread(self.dlg)
        downloadWorker.moveToThread(thr)
        downloadWorker.update.connect(self.updateProgress)
        downloadWorker.error.connect(self.error)
        downloadWorker.finished.connect(self.downloadWorkerFinished)
        thr.started.connect(downloadWorker.run)
        thr.start()
        self.downloadThread = thr
        self.downloadWorker = downloadWorker

    def updateProgress(self, returns):
        self.dlg.progressBar.setValue(returns['progress'])

    def error(self, errorContent):
        msgBox = QMessageBox.critical(None, 'Error downloading raster data', str(errorContent))

    def downloadWorkerFinished(self, returns):
        self.downloadWorker.deleteLater()
        self.downloadThread.quit()
        self.downloadThread.wait()
        self.downloadThread.deleteLater()

        # reproject into canvas CRS
        if self.dlg.checkBoxReproject.isChecked():
            canvas = self.iface.mapCanvas()
            # canvasEPSG = canvas.mapRenderer().destinationCrs().authid()
            canvasEPSG = canvas.mapSettings().destinationCrs().authid()  # New for QGIS3
            res = self.dlg.spinBoxResolution.value()

            if not self.crs == canvasEPSG:
                # if sys.platform == 'win32':
                #     si = subprocess.STARTUPINFO()
                #     si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                # else:
                #     si = None
                # gdalwarptext = 'gdalwarp -overwrite -q -s_srs ' + self.crs + ' -t_srs ' + canvasEPSG + ' -tr ' + \
                #                str(res) + ' ' + str(res) + ' -of GTiff ' + self.filename + ' ' + self.filename2
                # print(gdalwarptext)
                # if sys.platform == 'win32':
                #     subprocess.call(gdalwarptext, startupinfo=si)
                # else:
                #     os.system(gdalwarptext)
                gdal.Warp(self.filename2, self.filename, srcSRS=str(self.crs), dstSRS=str(canvasEPSG), xRes=res, yRes=res)
            else:
                shutil.copy(self.filename, self.filename2)

            os.remove(self.filename)
            returns['filename'] = self.filename2

        print(returns['filename'])

        # Set progress bar to 100 or 0
        self.dlg.progressBar.setValue(100)
        # Get filename to use as layer label
        lab = os.path.splitext(os.path.split(str(returns['filename']))[1])[0]

        # Add to QGIS canvas as saved filename
        self.rasterLayer = QgsRasterLayer(str(returns['filename']), "%s"%(lab,))

        if not self.dlg.checkBoxReproject.isChecked():
            # Ensure the layer CRS is as declared (some WCS rasters lose their CRS embedded info for some reasons)
            crs = self.rasterLayer.crs()
            crs.createFromId(int(returns['srs'].split(':')[1]))
            self.rasterLayer.setCrs(crs)

        QgsProject.instance().addMapLayer(self.rasterLayer)

    def tr(self, message):
        return QCoreApplication.translate('UMEP_Data_Download', message)

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

        icon_path = ':/plugins/UMEP_Data_Download/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'UMEP downloader'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UMEP data data downloader'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.exec_()


