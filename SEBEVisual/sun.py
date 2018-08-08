# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Sun
                                 A QGIS plugin
 Creates a sun energy analyzing environment with statistics and 3D model 
                              -------------------
        begin                : 2014-03-20
        copyright            : (C) 2014 by Niklas Krave
        email                : niklaskrave@gmail.com
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
from builtins import str
from builtins import object
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QThread, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox # , QMovie
from qgis.core import *
from qgis.utils import *

# Initialize Qt resources from file resources.py
from . import resources

import os.path
from osgeo import gdal
import subprocess
import numpy as np
import math
import webbrowser

from .listworker import Worker

# Import the code for the GUI dialog
from .visualizer_dialog import VisualizerDialog

#import tools
from .tools.areaTool import AreaTool

#3d Model import
#import tools.GLWindow as GLWindow
# import tools.GLWidget
try:
    # import tools.GLWidget as GLWidget
    from . import tools.GLWidget
except ImportError:
    pass


class Sun(object):
    
    #Runs when QGis starts up and the plugin is set to be active
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'sun_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.visDlg = VisualizerDialog()

        self.polyLayer = None
        self.dir_path = None
        self.layer = None
        self.point1 = None
        self.point2 = None
        self.gl_widget = None
        self.max_energy = 0
        self.energy_array = None
        self.asc_array = None

        self.ncols = None
        self.nrows = None
        self.xllcorner = None
        self.yllcorner = None
        self.cellsize = None

        self.roofground_file = 'Energyyearroof.tif'
        self.veg_file = 'Vegetationdata.txt'
        self.wall_file = 'Energyyearwall.txt'
        self.height_file = 'dsm.tif'

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(2)
        self.fileDialog.setAcceptMode(0)

        #Create a reference to the map canvas
        self.canvas = self.iface.mapCanvas()
        
        #Create tools
        self.areaTool = AreaTool(self.canvas)

        self.thread = None
        self.worker = None
        self.steps = 0

        self.areaTool.areaComplete.connect(self.display_area)

        self.visDlg.pushButtonSelect.clicked.connect(self.area)
        self.visDlg.pushButtonDirectory.clicked.connect(self.path_directory)
        self.visDlg.pushButtonVisualize.clicked.connect(self.visualize)
        self.visDlg.helpButton.clicked.connect(self.help)

    def initGui(self):
        #create toolbar
        self.toolBar = self.iface.addToolBar("Sun Toolbar")
     
        #Action for initializing the plugin, will add shape-files and OLlayer to the QGis-project
        self.initialize = QAction(
            QIcon(":/plugins/sun/initicon.png"),
            u"Initialize plugin environment", self.iface.mainWindow())

        self.initialize.triggered.connect(self.run)

        self.toolBar.addAction(self.initialize)

        self.areaTool.areaComplete.connect(self.display_area)

        self.visDlg.pushButtonSelect.clicked.connect(self.area)
        self.visDlg.pushButtonDirectory.clicked.connect(self.path_directory)
        self.visDlg.pushButtonVisualize.clicked.connect(self.visualize)
    
    #Runs when the plugin is deleted 
    def unload(self):
        # Remove the plugin toolbar
        del self.toolBar

    # Initialization method
    def run(self):
        self.visDlg.open()
        self.visDlg.exec_()

    def help(self):
        url = "http://umep-docs.readthedocs.io/en/latest/post_processor/Solar%20Radiation%20SEBE%20(Visualisation).html"
        webbrowser.open_new_tab(url)

    def area(self):
        self.canvas.setMapTool(self.areaTool)

    def path_directory(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.dir_path = self.fileDialog.selectedFiles()
            self.visDlg.textOutput.setText(self.dir_path[0])

        self.layer = QgsRasterLayer(self.dir_path[0] + '/Energyyearroof.tif', "Energy Roof Layer")
        test = QgsMapLayerRegistry.instance().addMapLayer(self.layer)
        test.loadNamedStyle(self.plugin_dir + '/SEBE_kwh.qml')
        test.triggerRepaint()

        # rlayer = self.iface.addRasterLayer(self.dir_path[0] + '/Energyyearroof.tif')
        #
        # # Trigger a repaint
        # if hasattr(rlayer, "setCacheImage"):
        #     rlayer.setCacheImage(None)
        # rlayer.triggerRepaint()
        #
        # rlayer.loadNamedStyle(self.plugin_dir + '/SEBE_kwh.qml')
        # # self.QgsMapLayerRegistry.instance().addMapLayer(rlayer)
        #
        # if hasattr(rlayer, "setCacheImage"):
        #     rlayer.setCacheImage(None)
        # rlayer.triggerRepaint()


        # with open(self.dir_path[0] + '/' + self.height_file, 'r') as f:
        #     line = f.readline()
        #     splitline = line.split()
        #     self.ncols = float(splitline[1])
        #     line = f.readline()
        #     splitline = line.split()
        #     self.nrows = float(splitline[1])
        #     line = f.readline()
        #     splitline = line.split()
        #     self.xllcorner = float(splitline[1])
        #     line = f.readline()
        #     splitline = line.split()
        #     self.yllcorner = float(splitline[1])
        #     line = f.readline()
        #     splitline = line.split()
        #     self.cellsize = float(splitline[1])

        if not self.layer.isValid():
            QMessageBox.critical(None, "Error", "Could not find valid .tif file in directory")
            return

        self.gdal_dsm = gdal.Open(self.dir_path[0] + '/' + self.height_file)
        self.ncols = self.gdal_dsm.RasterXSize
        self.nrows = self.gdal_dsm.RasterYSize
        geotransform = self.gdal_dsm.GetGeoTransform()
        self.xllcorner = geotransform[0]
        self.yllcorner = geotransform[3] + self.ncols * geotransform[4] + self.nrows * geotransform[5]
        self.cellsize = geotransform[1]

        # self.iface.messageBar().pushMessage(str(self.xllcorner) + ' ' +, level=QgsMessageBar.CRITICAL, duration=3)

        self.visDlg.pushButtonSelect.setEnabled(1)

    def display_area(self, point1, point2):

        self.point1 = point1
        self.point2 = point2

        if self.polyLayer is not None:
            self.polyLayer.startEditing()
            self.polyLayer.selectAll()
            self.polyLayer.deleteSelectedFeatures()
            self.polyLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.polyLayer.id())

        srs = self.canvas.mapSettings().destinationCrs()
        crs = str(srs.authid())
        uri = "Polygon?field=id:integer&index=yes&crs=" + crs
        self.polyLayer = QgsVectorLayer(uri, "Study area", "memory")
        provider = self.polyLayer.dataProvider()

        fc = int(provider.featureCount())
        featurepoly = QgsFeature()

        rect = QgsRectangle(point1, point2)
        featurepoly.setGeometry(QgsGeometry.fromRect(rect))
        featurepoly.setAttributes([fc])
        self.polyLayer.startEditing()
        self.polyLayer.addFeature(featurepoly, True)
        self.polyLayer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(self.polyLayer)

        self.polyLayer.setLayerTransparency(42)

        self.polyLayer.triggerRepaint()
        self.visDlg.pushButtonVisualize.setEnabled(1)
        self.visDlg.activateWindow()

    def visualize(self):
        self.steps = 0
        gdal.UseExceptions()

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if self.point1.x() > self.point2.x():
            minx = math.floor(self.point2.x())
            maxx = math.ceil(self.point1.x())
        else:
            minx = math.floor(self.point1.x())
            maxx = math.ceil(self.point2.x())

        if self.point1.y() > self.point2.y():
            miny = math.floor(self.point2.y())
            maxy = math.ceil(self.point1.y())
        else:
            miny = math.floor(self.point1.y())
            maxy = math.ceil(self.point2.y())

        dataset_full = gdal.Open(self.dir_path[0] + '/' + self.roofground_file)
        full_array = dataset_full.ReadAsArray().astype(np.float)

        fullsizex = full_array.shape[1]
        fullsizey = full_array.shape[0]

        toplefty = self.yllcorner + fullsizey

        gdalclip_build = 'gdal_translate -a_nodata -9999 -projwin ' + str(minx) + ' ' + str(maxy)\
                         + ' ' + str(maxx) + ' ' + str(miny) + \
                         ' -of GTiff ' + self.dir_path[0] + '/' + self.roofground_file + ' ' \
                         + self.plugin_dir + '/data/temp.tif'

        subprocess.call(gdalclip_build, startupinfo=si)

        dataset = gdal.Open(self.plugin_dir + '/data/temp.tif')
        self.energy_array = dataset.ReadAsArray().astype(np.float)

        sizex = self.energy_array.shape[1]
        sizey = self.energy_array.shape[0]

        gdalclipasc_build = 'gdal_translate -a_nodata -9999 -projwin ' + str(minx) + ' ' + str(maxy) + ' ' + str(maxx) +\
                            ' ' + str(miny) + ' -of GTiff ' + self.dir_path[0] + '/' + self.height_file + ' ' + \
                            self.plugin_dir + '/data/temp_asc.tif'

        subprocess.call(gdalclipasc_build, startupinfo=si)

        dataset = gdal.Open(self.plugin_dir + '/data/temp_asc.tif')
        self.asc_array = dataset.ReadAsArray().astype(np.float)

        # movie = QMovie(self.plugin_dir + '/loader.gif')
        # self.visDlg.label.setMovie(movie)
        # self.visDlg.label.show()
        # movie.start()

        self.start_listworker(minx, maxy, sizex, sizey, toplefty)

    def start_listworker(self, minx, maxy, sizex, sizey, toplefty):
        # create a new worker instance
        worker = Worker(minx, maxy, sizex, sizey, self.point1, self.point2, self.xllcorner, toplefty,
                        self.cellsize, self.dir_path, self.wall_file)

        self.visDlg.pushButtonVisualize.setText('Cancel')
        self.visDlg.pushButtonVisualize.clicked.disconnect()
        self.visDlg.pushButtonVisualize.clicked.connect(self.kill_worker)
        self.visDlg.pushButton.setEnabled(False)

        # start the worker in a new thread
        thread = QThread(self.visDlg)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerError(self, e, exception_string):
        strerror = "Worker thread raised an exception: " + str(e)
        QgsMessageLog.logMessage(strerror.format(exception_string), level=QgsMessageLog.CRITICAL)

    def progress_update(self):
        pass

    def kill_worker(self, worker):
        self.visDlg.label.hide()
        self.worker.kill()

    def workerFinished(self, ret):
        # clean up the worker and thread
        wall_array = ret
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        if ret is not None:
            QgsMessageLog.logMessage('WALL_ARRAY length: ' + str(len(ret)), level=QgsMessageLog.CRITICAL)
            QgsMessageLog.logMessage('WALL_ARRAY: ' + str(ret), level=QgsMessageLog.CRITICAL)
            QgsMessageLog.logMessage('ASC_ARRAY: ' + str(self.asc_array), level=QgsMessageLog.CRITICAL)
            if self.gl_widget is not None:
                self.visDlg.layout.removeWidget(self.gl_widget)

            self.gl_widget = tools.GLWidget.GLWidget(self.energy_array, self.asc_array, wall_array, self.cellsize,
                                               self.visDlg)
            self.visDlg.layout.addWidget(self.gl_widget)

        self.visDlg.pushButtonVisualize.setText('Visualize')
        self.visDlg.pushButtonVisualize.clicked.disconnect()
        self.visDlg.pushButtonVisualize.clicked.connect(self.visualize)
        self.visDlg.pushButton.setEnabled(True)
        #self.visDlg.label.hide()

    # def wall_list(self, minx, miny, sizex, sizey):
    #     wall_array = []
    #     xstart = minx - self.xllcorner
    #     ystart = miny - self.yllcorner
    #     xend = xstart + sizex
    #     yend = ystart + sizey
    #     rectpoint = QgsPoint(xstart, yend)
    #     rectpoint2 = QgsPoint(xend, ystart)
    #     rect = QgsRectangle(rectpoint, rectpoint2)
    #
    #     with open(self.dir_path[0] + '/' + self.wall_file) as wallfile:
    #         next(wallfile)
    #         for line in wallfile:
    #             wall_list = []
    #             string = line.split()
    #             x = float(string[1])
    #             y = float(string[0])
    #             testpoint = QgsPoint(x,y)
    #             testpoint2 = QgsPoint(x + self.cellsize - 0.00001, y + self.cellsize - 0.00001)
    #             testrect = QgsRectangle(testpoint, testpoint2)
    #             if testrect.intersects(rect):
    #                 for e in string:
    #                     if float(e) > 0:
    #                         wall_list.append(float(e))
    #                 wall_list[0] = y - ystart
    #                 wall_list[1] = x - xstart
    #                 wall_array.append(wall_list)
    #
    #     return wall_array

