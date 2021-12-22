# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UWGAnalyser
                                 A QGIS plugin
 Analyse output from UWG
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-12-08
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Fredrik Lindberg
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel, QgsVectorLayer, QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer, QgsVectorDataProvider, QgsField
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .uwg_analyser_dialog import UWGAnalyserDialog
import os.path
# from .umep_uwg_export_component import read_uwg_file
from ..Utilities.umep_uwg_export_component import read_uwg_file
import datetime
import numpy as np
try:
    import matplotlib.pylab as plt
    import matplotlib.dates as dt
    nomatplot = 0
except ImportError:
    nomatplot = 1
    pass
import webbrowser
import shutil
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import *


class UWGAnalyser:
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
            'UWGAnalyser_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&UWG Analyser')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        self.timelist = []

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
        return QCoreApplication.translate('UWGAnalyser', message)


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
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/uwg_analyser/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UWG Analyser'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        self.dlg = UWGAnalyserDialog()

        self.fileDialog = QFileDialog()

        self.fileDialogIn = QFileDialog()
        self.fileDialogIn.setFileMode(QFileDialog.Directory)
        self.fileDialogIn.setOption(QFileDialog.ShowDirsOnly, True)

        self.fileDialogOut = QFileDialog()
        self.fileDialogOut.setFileMode(QFileDialog.Directory)
        self.fileDialogOut.setOption(QFileDialog.ShowDirsOnly, True)

        self.dlg.pushButtonInFolder.clicked.connect(self.folder_path_inmodel)
        self.dlg.pushButtonOutFolder.clicked.connect(self.folder_path_outmodel)
        self.dlg.runButtonPlot.clicked.connect(self.plotpoint)
        self.dlg.runButtonSpatial.clicked.connect(self.spatial)
        self.dlg.pushButtonSave.clicked.connect(self.geotiff_save)

        self.layerComboManagerPolygrid = QgsMapLayerComboBox(self.dlg.widgetPolygrid)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyfield = QgsFieldComboBox(self.dlg.widgetField)
        self.layerComboManagerPolyfield.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolyfield.setFixedWidth(125)
        self.layerComboManagerPolygrid.layerChanged.connect(self.layerComboManagerPolyfield.setLayer)

        # show the dialog
        self.dlg.show()
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            pass
        else:
            self.dlg.__init__()


    def clearentries(self):
        # clear old entries
        self.dlg.comboBox_POIField.clear()
        self.dlg.comboBox_POIDOYMin.clear()
        self.dlg.comboBox_POIDOYMax.clear()
        self.dlg.comboBox_POIField.addItem('Not Specified')
        self.dlg.comboBox_POIDOYMin.addItem('Not Specified')
        self.dlg.comboBox_POIDOYMax.addItem('Not Specified')
        self.dlg.comboBox_SpatialDOYMin.clear()
        self.dlg.comboBox_SpatialDOYMax.clear()
        self.dlg.textOutput.clear()
        self.dlg.comboBox_SpatialDOYMin.addItem('Not Specified')
        self.dlg.comboBox_SpatialDOYMax.addItem('Not Specified')
        self.dlg.textOutput.setText('Not Specified')


    def folder_path_inmodel(self):
        
        self.clearentries()

        self.fileDialogIn.open()
        result = self.fileDialogIn.exec_()
        if result == 1:
            self.folderPath = self.fileDialogIn.selectedFiles()
            self.dlg.textModelInFolder.setText(self.folderPath[0])

            self.infileList = os.listdir(self.folderPath[0])
            a = self.infileList[0].find("_")
            self.prefix = self.infileList[0][0:a]

            uwgDict = read_uwg_file(self.folderPath[0], self.infileList[0][:-4])
            mm = uwgDict['Month']
            dd = uwgDict['Day']
            nDays = uwgDict['nDay']

            # populate availabe grids in GUI
            self.l = os.listdir(self.folderPath[0])
            for file in self.l:
                if file.startswith(self.prefix):
                    self.timelist.append(int(file[len(self.prefix) + 1:-4]))
                    
            l = sorted(list(set(self.timelist)))
            for i in l:
                self.dlg.comboBox_POIField.addItem(str(i))

            # populate available days
            startDate = datetime.date(int(1985), int(mm), int(dd))
            for i in range(0, int(nDays)):
                startDate.strftime('%d %b')
                endDate = startDate + datetime.timedelta(days=int(i))
                self.dlg.comboBox_POIDOYMin.addItem(endDate.strftime('%d %b'))
                self.dlg.comboBox_POIDOYMax.addItem(endDate.strftime('%d %b'))
                self.dlg.comboBox_SpatialDOYMin.addItem(endDate.strftime('%d %b'))
                self.dlg.comboBox_SpatialDOYMax.addItem(endDate.strftime('%d %b'))

            self.dlg.pushButtonOutFolder.setEnabled(1)
            self.dlg.textModelOutFolder.setEnabled(1)


    def folder_path_outmodel(self):

        self.fileDialogOut.open()
        result = self.fileDialogOut.exec_()
        if result == 1:
            self.folderPathOut = self.fileDialogOut.selectedFiles()
            self.dlg.textModelOutFolder.setText(self.folderPathOut[0])

            self.dlg.pushButtonSave.setEnabled(1)
            self.dlg.textOutput.setEnabled(1)
            self.dlg.runButtonSpatial.setEnabled(1)
            self.dlg.runButtonPlot.setEnabled(1)


    def plotpoint(self):
        self.varpoi1 = self.dlg.comboBox_POIField.currentText()

        if self.dlg.comboBox_POIField.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Grid ID is selected")
            return

        if self.dlg.comboBox_POIDOYMin.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Minimum DOY is selected")
            return
        else:
            startDate = datetime.datetime.strptime(self.dlg.comboBox_POIDOYMin.currentText(), '%d %b')
            startday = int(startDate.strftime('%j'))

        if self.dlg.comboBox_POIDOYMax.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
            return
        else:
            endDate = datetime.datetime.strptime(self.dlg.comboBox_POIDOYMax.currentText(), '%d %b')
            endday = int(endDate.strftime('%j'))

        if startday > endday:
            QMessageBox.critical(self.dlg, "Error", "Start day happens after end day")
            return

        if startday == endday:
            QMessageBox.critical(self.dlg, "Error", "End day must be higher than start day")
            return

        # Load rural data
        sitein = self.folderPathOut[0] + '/metdata_UMEP.txt'
        dataref = np.genfromtxt(sitein, skip_header=1)
        self.yyyy = dataref[0,0]
        
        # Load UWG data
        datawhole = np.genfromtxt(self.folderPathOut[0] + '/' + self.prefix + '_' + self.varpoi1 + '_UMEP_UWG.txt', skip_header=1)

        start = np.min(np.where(datawhole[:, 1] == startday))
        if endday > np.max(datawhole[:, 1]):
            ending = np.max(np.where(datawhole[:, 1] == endday - 1))
        else:
            ending = np.min(np.where(datawhole[:, 1] == endday))
        data1 = datawhole[start:ending + 12, :] # + 12 to include whole final night 
        dataref1 = dataref[start:ending + 12, :] # + 12 to include whole final night 

        dates = []
        for i in range(0, data1.shape[0]):  # making date number
            dates.append(
                dt.datetime.datetime(int(data1[i, 0]), 1, 1) + datetime.timedelta(days=data1[i, 1] - 1,
                                                                                    hours=data1[i, 2],
                                                                                    minutes=data1[i, 3]))

        plt.figure(1, figsize=(15, 7), facecolor='white')
        plt.title('General weather parameters and model output')
        ax1 = plt.subplot(2, 1, 1)
        ax2 = ax1.twinx()
        ax1.plot(dates, dataref1[:, 9], 'b') 
        ax1.set_ylim([0, max(dataref1[:, 9])])
        ax2.plot(dates, dataref1[:, 14], 'r') 
        ax1.set_ylabel('Wind speed ($m/s$)', color='b', fontsize=14)
        ax2.set_ylabel('Global radiation ($W/m^2$)', color='r', fontsize=14)
        plt.title('General weather parameters and model output')
        
        ax3 = plt.subplot(2, 1, 2, sharex=ax1)
        ax3.plot(dates, dataref1[:, 11], 'g', label='Rural')
        ax3.plot(dates, data1[:, 11], 'r', label='Urbanised')
        ax3.set_ylabel('Air Temperature ($^{o}C$)', color='b', fontsize=14)
        ax3.legend(loc=2)
        ax1.grid(True)
        ax3.grid(True)
        ax3.set_xlabel('Time', fontsize=14)
        
        plt.show()


    def spatial(self):

        if self.dlg.comboBox_SpatialDOYMax.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
            return

        poly = self.layerComboManagerPolygrid.currentLayer()
        if poly is None:
            QMessageBox.critical(self.dlg, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(self.dlg, "Error", "No valid Polygon layer is selected")
            return

        poly_field = self.layerComboManagerPolyfield.currentField()
        if poly_field is None:
            QMessageBox.critical(self.dlg, "Error", "An attribute with unique fields/records must be selected (same as used in the model run to analyze)")
            return

        if not (self.dlg.addResultToGrid.isChecked() or self.dlg.addResultToGeotiff.isChecked()):
            QMessageBox.critical(self.dlg, "Error", "No output method has been selected (Add results to polygon grid OR Save as GeoTIFF)")
            return

        if self.dlg.comboBox_SpatialDOYMin.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Minimum DOY is selected")
            return
        else:
            startDate = datetime.datetime.strptime(self.dlg.comboBox_SpatialDOYMin.currentText(), '%d %b')
            startday = int(startDate.strftime('%j'))
            startD = startday
            
        if self.dlg.comboBox_SpatialDOYMax.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
            return
        else:
            endDate = datetime.datetime.strptime(self.dlg.comboBox_SpatialDOYMax.currentText(), '%d %b')
            endday = int(endDate.strftime('%j'))
            endD = endday

        if startday > endday:
            QMessageBox.critical(self.dlg, "Error", "Start day happens after end day")
            return

        if startday == endday:
            QMessageBox.critical(self.dlg, "Error", "End day must be higher than start day")
            return

        # load, cut data and calculate statistics
        statvectemp = [0]
        statresult = [0]
        idvec = [0]

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        # idx = vlayer.fieldNameIndex(poly_field)
        idx = vlayer.fields().indexFromName(poly_field)
        typetest = fields.at(idx).type()
        if typetest == 10:
            QMessageBox.critical(self.dlg, "ID field is string type", "ID field must be either integer or float")
            return

        # Load rural data
        sitein = self.folderPathOut[0] + '/metdata_UMEP.txt'
        dataref = np.genfromtxt(sitein, skip_header=1)

        # for i in range(0, self.idgrid.shape[0]): # loop over vector grid instead
                # for i in range(0, self.idgrid.shape[0]): # loop over vector grid instead
        # nGrids = vlayer.featureCount()
        for f in vlayer.getFeatures():

            gid = str(int(f.attributes()[idx]))

            datawhole = np.genfromtxt(self.folderPathOut[0] + '/' + self.prefix + '_' + gid + '_UMEP_UWG.txt', skip_header=1)

            # cut UWG data
            start = np.min(np.where(datawhole[:, 1] == startD))
            if endD > np.max(datawhole[:, 1]):
                ending = np.max(np.where(datawhole[:, 1] == endD - 1))
            else:
                ending = np.min(np.where(datawhole[:, 1] == endD))
            data1 = datawhole[start:int(ending + 12), :] # + 12 to include whole final night 

            data1 = data1[np.where(data1[:, 14] < 1.), :] # include only nighttime. 14 is position for global radiation
            data1 = data1[0][:]

            # cut ref data
            if endD > np.max(dataref[:, 1]):
                ending = np.max(np.where(dataref[:, 1] == endD - 1))
            else:
                ending = np.min(np.where(dataref[:, 1] == endD))
            data2 = dataref[start:int(ending + 12), :] # + 12 to include whole final night 

            data2 = data2[np.where(data2[:, 14] < 1.), :] # include only nighttime. 14 is position for global radiation
            data2 = data2[0][:]
            
            # if dayTypeStr == '1':
            #     data1 = data1[np.where(data1[:, altpos] < 90.), :]
            #     data1 = data1[0][:]
            # if dayTypeStr == '2':
            #     data1 = data1[np.where(data1[:, altpos] > 90.), :]
            #     data1 = data1[0][:]

            vardatauwg = data1[:, 11] # 11 is temperature column
            vardataref = data2[:, 11] 
            vardata = vardatauwg - vardataref

            if self.dlg.radioButtonMean.isChecked():
                statresult = np.nanmean(vardata)
                header = 'mean'
            # if self.dlg.radioButtonMin.isChecked():
            #     statresult = np.nanmin(vardata)
            if self.dlg.radioButtonMax.isChecked():
                statresult = np.nanmax(vardata)
                header = 'max'
            if self.dlg.radioButtonMed.isChecked():
                statresult = np.nanmedian(vardata)
                header = 'median'
            # if self.dlg.radioButtonIQR.isChecked():
            #     statresult = np.nanpercentile(vardata, 75) - np.percentile(vardata, 25)

            # if statTypeStr == '0':
            #     statresult = np.nanmean(vardata)
            #     header = 'mean'
            # if statTypeStr == '1':
            #     statresult = np.nanmin(vardata)
            #     header = 'max'
            # if statTypeStr == '2':
            #     statresult = np.nanpercentile(vardata, 50)
            #     header = 'median'
            # if statTypeStr == '3':
            #     statresult = np.nanpercentile(vardata, 75)
            #     header = '75precentile'
            # if statTypeStr == '4':
            #     statresult = np.nanpercentile(vardata, 95)
            #     header = '95precentile'

            statvectemp = np.vstack((statvectemp, statresult))
            idvec = np.vstack((idvec, int(gid)))

        statvector = statvectemp[1:, :]
        # fix_print_with_import
        statmat = np.hstack((idvec[1:, :], statvector))

        if self.dlg.addResultToGrid.isChecked():
            self.addattributes(vlayer, statmat, header)

        if self.dlg.addResultToGeotiff.isChecked():
            extent = vlayer.extent()
            # xmax = extent.xMaximum()
            # xmin = extent.xMinimum()
            # ymax = extent.yMaximum()
            # ymin = extent.yMinimum()
        
            if self.dlg.checkBoxIrregular.isChecked():
                resx = self.dlg.doubleSpinBoxRes.value()
            else:
                for f in vlayer.getFeatures():  # Taking first polygon. Could probably be done nicer
                    geom = f.geometry().asMultiPolygon()
                    break
                resx = np.abs(geom[0][0][0][0] - geom[0][0][2][0])  # x
                resy = np.abs(geom[0][0][0][1] - geom[0][0][2][1])  # y

                if not resx == resy:
                    QMessageBox.critical(self.dlg, "Error", "Polygons not squared in current CRS")
                    return

            if self.dlg.textOutput.text() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No output filename for GeoTIFF is added")
                return
            else:
                filename = self.dlg.textOutput.text()
            
            if os.path.isfile(self.plugin_dir + '/tempgrid.tif'): # response to issue 103
                try:
                    shutil.rmtree(self.plugin_dir + '/tempgrid.tif')
                except OSError:
                    os.remove(self.plugin_dir + '/tempgrid.tif')
            
            extent = vlayer.extent()
            crs = vlayer.crs().toWkt()

            path=vlayer.dataProvider().dataSourceUri()
            polygonpath = path [:path.rfind('|')] # work around. Probably other solution exists
            print(str(poly_field))

            self.rasterize(polygonpath, str(self.plugin_dir + '/tempgrid.tif'), str(poly_field), resx, crs, extent)

            dataset = gdal.Open(self.plugin_dir + '/tempgrid.tif')
            idgrid_array = dataset.ReadAsArray().astype(float)

            gridout = np.zeros((idgrid_array.shape[0], idgrid_array.shape[1]))

            for i in range(0, statmat.shape[0]):
                gridout[idgrid_array == statmat[i, 0]] = statmat[i, 1]

            print(gridout)

            self.saveraster(dataset, filename, gridout)

            # load result into canvas
            
            if self.dlg.checkBoxIntoCanvas.isChecked():
                rlayer = self.iface.addRasterLayer(filename)

                # Set opacity
                rlayer.renderer().setOpacity(1.0)

                # # Set colors
                s = QgsRasterShader()
                c = QgsColorRampShader()
                c.setColorRampType(QgsColorRampShader.Interpolated)
                i = []
                i.append(QgsColorRampShader.ColorRampItem(np.nanmin(gridout), QtGui.QColor('#2b83ba'), str(np.nanmin(gridout))))
                i.append(QgsColorRampShader.ColorRampItem(np.nanmedian(gridout), QtGui.QColor('#ffffbf'), str(np.nanmedian(gridout))))
                i.append(QgsColorRampShader.ColorRampItem(np.nanmax(gridout), QtGui.QColor('#d7191c'),str(np.nanmax(gridout))))
                c.setColorRampItemList(i)
                s.setRasterShaderFunction(c)
                ps = QgsSingleBandPseudoColorRenderer(rlayer.dataProvider(), 1, s)
                rlayer.setRenderer(ps)

                # Trigger a repaint
                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

        QMessageBox.information(self.dlg, "SUEWS Analyser", "Process completed")


    def geotiff_save(self):
        self.outputfile = self.fileDialog.getSaveFileName(None, "Save File As:", None, "GeoTIFF (*.tif)")
        self.dlg.textOutput.setText(self.outputfile[0])


    def saveraster(self, gdal_data, filename, raster):
        rows = gdal_data.RasterYSize
        cols = gdal_data.RasterXSize

        outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
        outBand = outDs.GetRasterBand(1)

        # write the data
        outBand.WriteArray(raster, 0, 0)
        # flush data to disk, set the NoData value and calculate stats
        outBand.FlushCache()
        outBand.SetNoDataValue(-9999)

        # georeference the image and set the projection
        outDs.SetGeoTransform(gdal_data.GetGeoTransform())
        outDs.SetProjection(gdal_data.GetProjection())


    def rasterize(self, src, dst, attribute, resolution, crs, extent, all_touch=False, na=-9999):

        # Open shapefile, retrieve the layer
        # print(src)
        src_data = ogr.Open(src)
        layer = src_data.GetLayer()

        # Use transform to derive coordinates and dimensions
        xmax = extent.xMaximum()
        xmin = extent.xMinimum()
        ymax = extent.yMaximum()
        ymin = extent.yMinimum()

        # Create the target raster layer
        cols = int((xmax - xmin)/resolution)
        # rows = int((ymax - ymin)/resolution) + 1
        rows = int((ymax - ymin)/resolution)  # issue 164
        trgt = gdal.GetDriverByName("GTiff").Create(dst, cols, rows, 1, GDT_Float32)
        trgt.SetGeoTransform((xmin, resolution, 0, ymax, 0, -resolution))

        # Add crs
        refs = osr.SpatialReference()
        refs.ImportFromWkt(crs)
        trgt.SetProjection(refs.ExportToWkt())

        # Set no value
        band = trgt.GetRasterBand(1)
        band.SetNoDataValue(na)

        # Set options
        if all_touch is True:
            ops = ["-at", "ATTRIBUTE=" + attribute]
        else:
            ops = ["ATTRIBUTE=" + attribute]

        # Finally rasterize
        gdal.RasterizeLayer(trgt, [1], layer, options=ops)

        # Close target an source rasters
        del trgt
        del src_data 

    
    def addattributes(self, vlayer, matdata, header):
        current_index_length = len(vlayer.dataProvider().attributeIndexes())
        caps = vlayer.dataProvider().capabilities()
        if caps & QgsVectorDataProvider.AddAttributes:
            vlayer.dataProvider().addAttributes([QgsField(header, QVariant.Double)])
            attr_dict = {}
            for y in range(0, matdata.shape[0]):
                attr_dict.clear()
                idx = int(matdata[y, 0])
                attr_dict[current_index_length] = float(matdata[y, 1])
                vlayer.dataProvider().changeAttributeValues({y: attr_dict})

            vlayer.updateFields()
        else:
            QMessageBox.critical(None, "Error", "Vector Layer does not support adding attributes")


    def help(self):
        url = 'https://umep-docs.readthedocs.io/en/latest/post_processor/Urban%20Heat%20Island%20UWG%20Analyser.html'
        webbrowser.open_new_tab(url)



            