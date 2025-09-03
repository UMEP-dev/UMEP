# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SUEWSAnalyzer
                                 A QGIS plugin
 This plugin analyzes performs bacis analysis of model output from the SUEWS model
                              -------------------
        begin                : 2016-11-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Fredrik Lindberg
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
from __future__ import print_function
from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QVariant, QCoreApplication, Qt

from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt import QtGui

from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
# from . import resources_rc
# Import the code for the dialog
from .suews_analyzer_dialog import SUEWSAnalyzerDialog
import os.path
import webbrowser
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import *
from ..Utilities import f90nml
from ..Utilities.misc import get_resolution_from_umep_forcing
import numpy as np
from ..suewsmodel import suewsdataprocessing
from ..suewsmodel.suewsdataprocessing import SUEWS_txt_to_df, SUEWS_met_txt_to_df, resample_dataframe
from ..suewsmodel import suewsplotting
from .params_dict import params_dict, unit_dict
# import sys
# import subprocess
import datetime
import shutil
import yaml
import pandas as pd

try:
    import matplotlib.pylab as plt
    import matplotlib.dates as dt
    nomatplot = 0
except ImportError:
    nomatplot = 1
    pass

su = suewsdataprocessing.SuewsDataProcessing()
pl = suewsplotting.SuewsPlotting()

class SUEWSAnalyzer(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SUEWSAnalyzer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SUEWSAnalyzerDialog()

        self.layerComboManagerPolygrid = QgsMapLayerComboBox(self.dlg.widgetPolygrid)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyfield = QgsFieldComboBox(self.dlg.widgetField)
        self.layerComboManagerPolyfield.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.layerComboManagerPolyfield.setLayer)
        
        self.dlg.comboBox_POIVariable.currentIndexChanged.connect(self.variable_changed)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonRunControl.clicked.connect(self.get_runcontrol)
        self.dlg.pushButtonSave.clicked.connect(self.geotiff_save)
        self.dlg.runButtonPlot.clicked.connect(self.plotpoint)
        self.dlg.runButtonSpatial.clicked.connect(self.spatial)

        self.dlg.comboBox_POIField.activated.connect(self.changeGridPOI)
        self.dlg.comboBox_POIYYYY.activated.connect(self.changeYearPOI)
        self.dlg.comboBox_SpatialYYYY.activated.connect(self.changeYearSP)

        self.fileDialog = QFileDialog()
        self.fileDialogyaml = QFileDialog()
        self.fileDialogyaml.setNameFilter("(*.yml)")

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SUEWS Analyzer')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SUEWSAnalyzer')
        # self.toolbar.setObjectName(u'SUEWSAnalyzer')

        self.outputfile = None
        self.unit = None
        self.resout = None
        self.fileCode = None
        self.gridcodemetmat = []

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('SUEWSAnalyzer', message)

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

        icon_path = ':/plugins/SUEWSAnalyzer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SUEWS Analyzer'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        self.dlg.show()
        self.dlg.exec_()
        self.clearentries()
        self.dlg.textModelFolder.clear()

    def clearentries(self):
        # clear old entries
        self.dlg.comboBox_POIField.clear()
        self.dlg.comboBox_POIYYYY.clear()
        self.dlg.comboBox_POIDOYMin.clear()
        self.dlg.comboBox_POIDOYMax.clear()
        self.dlg.comboBox_POIVariable.clear()
        self.dlg.comboBox_POIField_2.clear()
        self.dlg.comboBox_POIVariable_2.clear()
        self.dlg.comboBox_POIField.addItem('Not Specified')
        self.dlg.comboBox_POIYYYY.addItem('Not Specified')
        self.dlg.comboBox_POIDOYMin.addItem('Not Specified')
        self.dlg.comboBox_POIDOYMax.addItem('Not Specified')
        self.dlg.comboBox_POIVariable.addItem('Not Specified')
        self.dlg.comboBox_POIField_2.addItem('Not Specified')
        self.dlg.comboBox_POIVariable_2.addItem('Not Specified')
        self.dlg.comboBox_SpatialVariable.clear()
        self.dlg.comboBox_SpatialYYYY.clear()
        self.dlg.comboBox_SpatialDOYMin.clear()
        self.dlg.comboBox_SpatialDOYMax.clear()
        self.dlg.textOutput.clear()
        self.dlg.comboBox_SpatialVariable.addItem('Not Specified')
        self.dlg.comboBox_SpatialYYYY.addItem('Not Specified')
        self.dlg.comboBox_SpatialDOYMin.addItem('Not Specified')
        self.dlg.comboBox_SpatialDOYMax.addItem('Not Specified')
        self.dlg.textOutput.setText('Not Specified')

    def get_runcontrol(self):
        # now using yml-files instead
        self.clearentries()

        self.fileDialogyaml.open()
        result = self.fileDialogyaml.exec_()
        if result == 1:
            self.yamlPath = self.fileDialogyaml.selectedFiles()
            self.dlg.textModelFolder.setText(self.yamlPath[0])
            with open(self.yamlPath[0], 'r') as f:
                yaml_dict = yaml.load(f, Loader=yaml.SafeLoader)

            self.fileoutputpath = yaml_dict['model']['control']['output_file']
            
            if self.fileoutputpath.startswith("."):
                yamlfolder = self.yamlPath[0][:-15]
                self.fileoutputpath = yamlfolder + self.fileoutputpath[1:]

            grid_list = [] 
            for n in range(len(yaml_dict['sites'])):
                grid_list.append(yaml_dict['sites'][n]['gridiv'])

            grid_list = list(map(str, grid_list))

            self.dlg.comboBox_POIField.addItems(grid_list)
            self.dlg.comboBox_POIField_2.addItems(grid_list)

            resolutionFilesOut = get_resolution_from_umep_forcing(yaml_dict['model']['control']['forcing_file']['value'])
            self.resout = int(float(resolutionFilesOut) / 60)

            resolutionFilesIn = resolutionFilesOut
            self.resin = int(resolutionFilesIn / 60)

            met_data = SUEWS_met_txt_to_df(yaml_dict['model']['control']['forcing_file']['value'])
            self.met_data = met_data
            # pd.read_csv(yaml_dict['model']['control']['forcing_file']['value'], delim_whitespace= True)
            # self.met_data['Datetime'] = pd.to_datetime(self.met_data[['iy', 'id', 'it', 'imin']].astype(str).agg('-'.join, axis=1), format='%Y-%j-%H-%M')
            # self.met_data.set_index('Datetime', inplace=True)

            years = list(self.met_data.index.year.unique())
            years = list(map(str, years))
            firstyear = years[0]

            # Fix 2025-06-24: If only one row from metdata exists in a yers, this year will not be shown in the list of availible years. OB
            for year in years:
                if len(self.met_data.loc[year]) == 1:
                    years.remove(year)

            self.dlg.comboBox_POIYYYY.addItems(years)
            self.dlg.comboBox_SpatialYYYY.addItems(years)
           
            mm = 0 #This doesn't work when hourly file starts with e.g.15
            while mm < 60:
                self.dlg.comboBox_mm.addItem(str(mm))
                mm += self.resout

            # New structure for 2025.6.2.dev0

            outfile = str(yaml_dict['sites'][0]['gridiv']) + '_' + str(firstyear) + '_SUEWS_60.txt'
            
            # # Set the datetime column as the index
  
            self.YYYY = -99
            self.gridcodemetID = -99

            for item in list(sorted(list(params_dict.keys()))):
                for cbox in [self.dlg.comboBox_POIVariable, self.dlg.comboBox_POIVariable_2,self.dlg.comboBox_SpatialVariable]:
                    item_desc = item + f" ({params_dict[item]['description']})" #773
                    cbox.addItem(item_desc)

            self.dlg.runButtonPlot.setEnabled(1)
            self.dlg.runButtonSpatial.setEnabled(1)

    def changeGridPOI(self):
        self.dlg.comboBox_POIYYYY.setCurrentIndex(0)
        self.dlg.comboBox_POIDOYMin.setCurrentIndex(0)
        self.dlg.comboBox_POIDOYMax.setCurrentIndex(0)

    def changeYearPOI(self):
        self.dlg.comboBox_POIDOYMin.clear()
        self.dlg.comboBox_POIDOYMax.clear()
        self.dlg.comboBox_POIDOYMin.addItem('Not Specified')
        self.dlg.comboBox_POIDOYMax.addItem('Not Specified')

        self.YYYY = self.dlg.comboBox_POIYYYY.currentText()

        # if self.multiplemetfiles == 0:
        #     self.gridcodemet = ''
        # else: 
        self.gridcodemet = self.dlg.comboBox_POIField.currentText()

        if self.YYYY == 'Not Specified':

            doy_list = self.met_data.index.strftime('%Y-%m-%d').unique().tolist()

            self.dlg.comboBox_POIDOYMin.addItems(doy_list)
            self.dlg.comboBox_POIDOYMax.addItems(doy_list)

        else:
            doy_list = self.met_data.loc[self.YYYY].index.strftime('%Y-%m-%d').unique().tolist()

            self.dlg.comboBox_POIDOYMin.addItems(doy_list)
            self.dlg.comboBox_POIDOYMax.addItems(doy_list)


    def changeYearSP(self):
        self.dlg.comboBox_SpatialDOYMin.clear()
        self.dlg.comboBox_SpatialDOYMax.clear()
        self.dlg.comboBox_SpatialDOYMin.addItem('Not Specified')
        self.dlg.comboBox_SpatialDOYMax.addItem('Not Specified')

        self.YYYY = self.dlg.comboBox_SpatialYYYY.currentText()

        if self.YYYY == 'Not Specified':

            doy_list = self.met_data.index.strftime('%Y-%m-%d').unique().tolist()

            self.dlg.comboBox_SpatialDOYMin.addItems(doy_list)
            self.dlg.comboBox_SpatialDOYMax.addItems(doy_list)

        else:
            doy_list = self.met_data.loc[self.YYYY].index.strftime('%Y-%m-%d').unique().tolist()

            self.dlg.comboBox_SpatialDOYMin.addItems(doy_list)
            self.dlg.comboBox_SpatialDOYMax.addItems(doy_list)


    def geotiff_save(self):
        self.outputfile = self.fileDialog.getSaveFileName(None, "Save File As:", None, "GeoTIFF (*.tif)")
        self.dlg.textOutput.setText(self.outputfile[0])


    def get_unit(self):
        uni = self.lineunit[self.id]
        if uni == 'W m-2':
            self.unit = '$W$'' ''$m ^{-2}$'
        elif uni == 'mm':
            self.unit = '$mm$'
        elif uni == 'degC':
            self.unit = '$^{o}C$'
        elif uni == 'deg':
            self.unit = '$Degrees(^{o})$'
        elif uni == '-':
            self.unit = '$-$'
        elif uni == 'm2 m-2':
            self.unit = '$m ^{2}$'' ''$m ^{-2}$'
        elif uni == 'm':
            self.unit = '$m$'
        elif uni == 'm s-1':
            self.unit = '$m$'' ''$s ^{-1}$'
        elif uni == 'umol m-2 s-1':
            self.unit = '$umol ^{2}$'' ''$m ^{-2}$'' ''$s ^{-1}$'
        elif uni == 'YYYY':
            self.unit = '$Year$'
        elif uni == 'DOY':
            self.unit = '$Day of Year$'
        elif uni == 'HH':
            self.unit = '$Hour$'
        elif uni == 'mm':
            self.unit = '$Minute$'
        elif uni == 'day':
            self.unit = '$Decimal Time$'


    def spatial(self):
        # self.iface.messageBar().pushMessage("SUEWS Analyzer", "Generating statistics grid", duration=5)

        if self.dlg.comboBox_SpatialVariable.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No analyzing variable is selected")
            return
        else:
            self.id = self.dlg.comboBox_SpatialVariable.currentIndex() - 1

        if self.dlg.comboBox_SpatialYYYY.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Year is selected")
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
            startday = self.dlg.comboBox_SpatialDOYMin.currentText() 

        if self.dlg.comboBox_SpatialDOYMax.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
            return
        else:
            endday = self.dlg.comboBox_SpatialDOYMax.currentText()

        if startday > endday:
            QMessageBox.critical(self.dlg, "Error", "Start day happens after end day")
            return

        if startday == endday:
            QMessageBox.critical(self.dlg, "Error", "End day must be higher than start day")
            return

        if self.dlg.checkBox_TOD.isChecked():
            if self.dlg.comboBox_HH.currentText() == ' ':
                QMessageBox.critical(self.dlg, "Error", "No Hour specified")
                return
            if self.dlg.comboBox_mm.currentText() == ' ':
                QMessageBox.critical(self.dlg, "Error", "No Minute specified")
                return

        # load, cut data and calculate statistics
        statvectemp = [0]
        statresult = [0]
        idvec = [0]

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        grid_list = [feature[poly_field] for feature in vlayer.getFeatures()]

        # for i in range(0, self.idgrid.shape[0]): # loop over vector grid instead
        for grid in grid_list:

            datawhole = SUEWS_txt_to_df(self.fileoutputpath + '/' + str(grid) + '_' +
                                      str(self.YYYY) + '_SUEWS_' + str(self.resout) + '.txt')
            
            data1 = datawhole.loc[startday:endday]

            if self.dlg.checkBox_TOD.isChecked():
                hh = self.dlg.comboBox_HH.currentText()
                minute = self.dlg.comboBox_mm.currentText()
                data1 = data1[data1.index.time == datetime.time(hh, minute)]
            else:
                if self.dlg.radioButtonDaytime.isChecked():
                    data1 = data1[data1.loc[:, 'Zenith'] < 90]
                if self.dlg.radioButtonNighttime.isChecked():
                    data1 = data1[data1.loc[:, 'Zenith'] > 90.]

            var = self.dlg.comboBox_SpatialVariable.currentText().split('(')[0].strip()
            vardata = data1.loc[:, var]

            if self.dlg.radioButtonMean.isChecked():
                statresult = np.nanmean(vardata)
                suffix = '_mean'
            if self.dlg.radioButtonMin.isChecked():
                statresult = np.nanmin(vardata)
                suffix = '_min'
            if self.dlg.radioButtonMax.isChecked():
                statresult = np.nanmax(vardata)
                suffix = '_max'
            if self.dlg.radioButtonMed.isChecked():
                statresult = np.nanmedian(vardata)
                suffix = '_median'
            if self.dlg.radioButtonIQR.isChecked():
                statresult = np.nanpercentile(vardata, 75) - np.percentile(vardata, 25)
                suffix = '_IQR'
            statvectemp = np.vstack((statvectemp, statresult))
            idvec = np.vstack((idvec, int(grid)))

        statvector = statvectemp[1:, :]

        statmat = np.hstack((idvec[1:, :], statvector))

        header = var + suffix
        if self.dlg.addResultToGrid.isChecked():
            self.addattributes(vlayer, statmat, header)

        if self.dlg.addResultToGeotiff.isChecked():
            extent = vlayer.extent()

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

            crs = vlayer.crs().toWkt()
            path=vlayer.dataProvider().dataSourceUri()
            # polygonpath = path [:path.rfind('|')] # work around. Probably other solution exists
            if path.rfind('|') > 0:
                polygonpath = path [:path.rfind('|')] # work around. Probably other solution exists
            else:
                polygonpath = path
            self.rasterize(str(polygonpath), str(self.plugin_dir + '/tempgrid.tif'), str(poly_field), resx, crs, extent)

            dataset = gdal.Open(self.plugin_dir + '/tempgrid.tif')
            idgrid_array = dataset.ReadAsArray().astype(float)

            gridout = np.zeros((idgrid_array.shape[0], idgrid_array.shape[1]))

            for i in range(0, statmat.shape[0]):
                gridout[idgrid_array == statmat[i, 0]] = statmat[i, 1]

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

        del outDs, outBand

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

    def plotpoint(self):
        self.varpoi1 = self.dlg.comboBox_POIField.currentText()

        if self.dlg.comboBox_POIField.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Grid ID is selected")
            return

        if not self.dlg.checkboxPlotBasic.isChecked():

            if self.dlg.comboBox_POIDOYMin.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No Minimum DOY is selected")
                return
            else:
                startday = self.dlg.comboBox_POIDOYMin.currentText()

            if self.dlg.comboBox_POIDOYMax.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
                return
            else:
                endday = self.dlg.comboBox_POIDOYMax.currentText()

            if startday > endday:
                QMessageBox.critical(self.dlg, "Error", "Start day happens after end day")
                return

            if startday == endday:
                QMessageBox.critical(self.dlg, "Error", "End day must be higher than start day")
                return
            
            datawhole = SUEWS_txt_to_df(self.fileoutputpath + '/' + self.varpoi1 + '_' +
                                      str(self.YYYY) + '_SUEWS_' + str(self.resout) + '.txt')
    

            if self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No plot variable is selected")
                return

            if not self.dlg.checkboxPOIAnother.isChecked():
                # One variable

                if self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                    QMessageBox.critical(self.dlg, "Error", "No plotting variable is selected")
                    return

                plt.figure(1, figsize=(15, 7), facecolor='white')
                plt.title(self.dlg.comboBox_POIVariable.currentText())
                ax1 = plt.subplot(1, 1, 1)
                var = self.dlg.comboBox_POIVariable.currentText().split('(')[0].strip()
                datawhole.loc[startday:endday, var].plot(color = 'r', label='$' + self.dlg.comboBox_POIVariable.currentText() + '$', ax = ax1)
                
                ax1.set_ylabel(unit_dict[params_dict[var]['unit']], fontsize=14)
                ax1.set_xlabel('Time', fontsize=14)
                ax1.grid(True)
            else:
                # Two variables
                var1 = self.dlg.comboBox_POIVariable.currentText().split('(')[0].strip()
                var2 = self.dlg.comboBox_POIVariable_2.currentText().split('(')[0].strip()
                varunit1 = unit_dict[params_dict[var1]['unit']]
                varunit2 = unit_dict[params_dict[var2]['unit']]

                if self.dlg.comboBox_POIVariable_2.currentText() == 'Not Specified' or self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                    QMessageBox.critical(self.dlg, "Error", "No plotting variable is selected")
                    return
                
                POIgrid1 = self.dlg.comboBox_POIField.currentText()
                POIgrid2 = self.dlg.comboBox_POIField_2.currentText()

                datawhole2 = SUEWS_txt_to_df(self.fileoutputpath + '/' + POIgrid2 + '_' +
                                      str(self.YYYY) + '_SUEWS_' + str(self.resout) + '.txt')

                if self.dlg.checkboxScatterbox.isChecked():
                    plt.figure(1, figsize=(8, 8), facecolor='white')
                    plt.title(
                        var1 + '(' + POIgrid1 + ') vs ' + var2 + '(' + POIgrid2 + ')')
                    ax1 = plt.subplot(1, 1, 1)
                    ax1.plot(datawhole.loc[startday: endday, var1], datawhole2.loc[startday: endday, var2], "k.")
                    ax1.set_ylabel(var1 + ' (' + varunit1 + ')', fontsize=14)
                    ax1.set_xlabel(var2 + ' (' + varunit2 + ')', fontsize=14)
                else:

                    plt.figure(1, figsize=(15, 7), facecolor='white')
                    plt.title(
                        var1 + '(' + POIgrid1 + ') and ' + var2 + '(' + POIgrid2 + ')')
                    ax1 = plt.subplot(1, 1, 1)

                    if varunit1 != varunit2:
                        ax2 = ax1.twinx()
                        datawhole.loc[startday: endday, var1].plot(
                            color = 'r', 
                            label='$' + var1 + ' (' + POIgrid1 + ')$', 
                            ax = ax1)
                        ax1.legend(loc=1)
                        datawhole.loc[startday: endday, var2].plot(
                            color = 'b', 
                            label='$' + var2 + ' (' + POIgrid2 + ')$', 
                            ax = ax2)

                        ax2.legend(loc=2)
                        ax1.set_ylabel(varunit1, color='r', fontsize=14)
                        ax2.set_ylabel(varunit2, color='b', fontsize=14)
                    else:
                        datawhole.loc[startday: endday, var1].plot(
                            color = 'r', 
                            label='$' + var1 + ' (' + POIgrid1 + ')$', 
                            ax = ax1)
                        datawhole.loc[startday: endday, var2].plot(
                            color = 'b', 
                            label='$' + var2 + ' (' + POIgrid2 + ')$', 
                            ax = ax1)
 
                        ax1.legend(loc=2)
                        ax1.set_ylabel(varunit1, fontsize=14)

                    ax1.grid(True)
                    ax1.set_xlabel('Time', fontsize=14)

            plt.show()
        else:
            
            timeaggregation = int(self.resout)

            df_met_data = resample_dataframe(self.met_data, timeaggregation, interpolate_method='linear')
            df_dataplotbasic = SUEWS_txt_to_df(self.fileoutputpath + '/'  + self.varpoi1 + '_' + str(self.YYYY) + '_SUEWS_' + str(self.resout) + '.txt')
                                                  
            pl.plotbasic(df_dataplotbasic, df_met_data)
            plt.show()

    def help(self):
        url = 'http://umep-docs.readthedocs.io/en/latest/post_processor/Urban%20Energy%20Balance%20SUEWS%20Analyser.html'
        webbrowser.open_new_tab(url)

    def rasterize(self, src, dst, attribute, resolution, crs, extent, all_touch=False, na=-9999):

        # Open shapefile, retrieve the layer
        src_data = ogr.Open(src)
        layer = src_data.GetLayer()

        # Use transform to derive coordinates and dimensions
        xmax = extent.xMaximum()
        xmin = extent.xMinimum()
        ymax = extent.yMaximum()
        ymin = extent.yMinimum()

        # Create the target raster layer
        cols = int((xmax - xmin)/resolution)
        rows = int((ymax - ymin)/resolution)  # issue 164
        trgt = gdal.GetDriverByName("GTiff").Create(dst, cols, rows, 1, gdal.GDT_Float32)
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

    def variable_changed(self):
        variable = self.dlg.comboBox_POIVariable.currentText()
        try:
            description = params_dict[variable]['description']
            self.dlg.comboBox_POIVariable.setToolTip(description)
        except:
            pass
        
    