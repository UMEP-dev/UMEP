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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QVariant
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QColor
from PyQt4 import QtGui
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from suews_analyzer_dialog import SUEWSAnalyzerDialog
import os.path
import webbrowser
from osgeo import gdal
from osgeo.gdalconst import *
from ..Utilities import f90nml
import numpy as np
from ..suewsmodel import suewsdataprocessing
from ..suewsmodel import suewsplotting
import sys
import subprocess

try:
    import matplotlib.pylab as plt
    import matplotlib.dates as dt
    nomatplot = 0
except ImportError:
    nomatplot = 1
    pass


class SUEWSAnalyzer:
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
        # self.layerComboManagerPolygrid = VectorLayerCombo(self.dlg.comboBox_Polygrid, initLayer="",
        #                                                   options={"geomType": QGis.Polygon})
        # fieldgen = VectorLayerCombo(self.dlg.comboBox_Polygrid, initLayer="", options={"geomType": QGis.Polygon})
        # self.layerComboManagerPolyField = FieldCombo(self.dlg.comboBox_Field, fieldgen)
        self.layerComboManagerPolygrid = QgsMapLayerComboBox(self.dlg.widgetPolygrid)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyfield = QgsFieldComboBox(self.dlg.widgetField)
        self.layerComboManagerPolyfield.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.layerComboManagerPolyfield.setLayer)

        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.pushButtonRunControl.clicked.connect(self.get_runcontrol)
        self.dlg.pushButtonSave.clicked.connect(self.geotiff_save)
        self.dlg.runButtonPlot.clicked.connect(self.plotpoint)
        self.dlg.runButtonSpatial.clicked.connect(self.spatial)

        self.dlg.comboBox_POIField.activated.connect(self.changeGridPOI)
        self.dlg.comboBox_POIYYYY.activated.connect(self.changeYearPOI)
        self.dlg.comboBox_SpatialYYYY.activated.connect(self.changeYearSP)

        self.fileDialog = QFileDialog()
        self.fileDialognml = QFileDialog()
        self.fileDialognml.setNameFilter("(RunControl.nml)")

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

        self.clearentries()

        self.fileDialognml.open()
        result = self.fileDialognml.exec_()
        if result == 1:
            self.nmlPath = self.fileDialognml.selectedFiles()
            self.dlg.textModelFolder.setText(self.nmlPath[0])
            nml = f90nml.read(self.nmlPath[0])

            self.fileinputpath = nml['runcontrol']['fileinputpath']
            if self.fileinputpath.startswith("."):
                nmlfolder = self.nmlPath[0][:-15]
                self.fileinputpath = nmlfolder + self.fileinputpath[1:]

            self.fileoutputpath = nml['runcontrol']['fileoutputpath']
            if self.fileoutputpath.startswith("."):
                nmlfolder = self.nmlPath[0][:-15]
                self.fileoutputpath = nmlfolder + self.fileoutputpath[1:]

            resolutionFilesOut = nml['runcontrol']['resolutionfilesout']
            self.resout = int(float(resolutionFilesOut) / 60)
            self.fileCode = nml['runcontrol']['filecode']
            self.multiplemetfiles = nml['runcontrol']['multiplemetfiles']
            resolutionFilesIn = nml['runcontrol']['resolutionFilesIn']
            self.resin = int(resolutionFilesIn / 60)

            tstep = nml['runcontrol']['tstep']
            self.tstep = int(float(tstep) / 60)

            mm = 0
            while mm < 60:
                self.dlg.comboBox_mm.addItem(str(mm))
                mm += self.resout

            sitein = self.fileinputpath + 'SUEWS_SiteSelect.txt'
            f = open(sitein)
            lin = f.readlines()
            self.YYYY = -99
            self.gridcodemetID = -99
            index = 2
            loop_out = ''
            gridcodemetmat = [0]
            while loop_out != '-9':
                lines = lin[index].split()
                if not int(lines[1]) == self.YYYY:
                    self.YYYY = int(lines[1])
                    self.dlg.comboBox_POIYYYY.addItem(str(self.YYYY))
                    self.dlg.comboBox_SpatialYYYY.addItem(str(self.YYYY))

                if not np.any(int(lines[0]) == gridcodemetmat):
                    self.gridcodemetID = int(lines[0])
                    self.dlg.comboBox_POIField.addItem(str(self.gridcodemetID))
                    self.dlg.comboBox_POIField_2.addItem(str(self.gridcodemetID))
                    gridtemp = [self.gridcodemetID]
                    gridcodemetmat = np.vstack((gridcodemetmat, gridtemp))

                if index == 2:
                    if self.multiplemetfiles == 0:
                        self.gridcodemet = ''
                    else:
                        self.gridcodemet = lines[0]
                    data_in = self.fileinputpath + self.fileCode + self.gridcodemet + '_' + str(self.YYYY) + '_data_' + str(self.resin) + '.txt'
                    self.met_data = np.genfromtxt(data_in, skip_header=1, missing_values='**********', filling_values=-9999)  # , skip_footer=2

                lines = lin[index + 1].split()
                loop_out = lines[0]
                index += 1

            f.close()
            self.idgrid = gridcodemetmat[1:, :]

            dataunit = self.fileoutputpath + '/' + self.fileCode + '_YYYY_' + str(
                self.resout) + '_OutputFormat.txt'
            f = open(dataunit)
            lin = f.readlines()
            self.lineunit = lin[3].split(";")
            self.linevar = lin[1].split(";")
            self.linevarlong = lin[2].split(";")
            f.close()

            for i in range(0, self.linevarlong.__len__()):
                self.dlg.comboBox_POIVariable.addItem(self.linevarlong[i])
                self.dlg.comboBox_POIVariable_2.addItem(self.linevarlong[i])
                self.dlg.comboBox_SpatialVariable.addItem(self.linevarlong[i])

            # for i in range(int(np.min(self.met_data[:, 1])), int(np.max(self.met_data[:, 1]))):
            #     self.dlg.comboBox_POIDOYMin.addItem(str(self.met_data[i, 1]))
            #     self.dlg.comboBox_POIDOYMax.addItem(str(self.met_data[i, 1]))
            #     self.dlg.comboBox_SpatialDOYMin.addItem(str(self.met_data[i, 1]))
            #     self.dlg.comboBox_SpatialDOYMax.addItem(str(self.met_data[i, 1]))

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

        if self.multiplemetfiles == 0:
            self.gridcodemet = ''
        else:
            self.gridcodemet = self.dlg.comboBox_POIField.currentText()

        data_in = self.fileinputpath + self.fileCode + self.gridcodemet + '_' + str(self.YYYY) + '_data_' + str(
            self.resin) + '.txt'
        self.met_data = np.genfromtxt(data_in, skip_header=1, missing_values='**********', filling_values=-9999)

        if np.min(self.met_data[:, 0]) - np.max(self.met_data[:, 0]) < 0:
            minis = np.min(self.met_data[:-1, 1])
            maxis = np.max(self.met_data[:, 1])
        else:
            minis = np.min(self.met_data[:, 1])
            maxis = np.max(self.met_data[:, 1])

        # QMessageBox.critical(self.dlg, "Min", str(minis))
        # QMessageBox.critical(self.dlg, "Max", str(maxis))
        # return

        for i in range(int(minis), int(maxis)):
                self.dlg.comboBox_POIDOYMin.addItem(str(i))
                self.dlg.comboBox_POIDOYMax.addItem(str(i))

        # self.dlg.comboBox_POIDOYMin.setCurrentIndex(0)
        # self.dlg.comboBox_POIDOYMax.setCurrentIndex(0)

    def changeYearSP(self):
        self.dlg.comboBox_SpatialDOYMin.clear()
        self.dlg.comboBox_SpatialDOYMax.clear()
        self.dlg.comboBox_SpatialDOYMin.addItem('Not Specified')
        self.dlg.comboBox_SpatialDOYMax.addItem('Not Specified')

        self.YYYY = self.dlg.comboBox_SpatialYYYY.currentText()

        # if self.multiplemetfiles == 0:
        #     self.gridcodemet = ''
        # else:
        #     self.gridcodemet = self.dlg.comboBox_POIField.currentText()

        data_in = self.fileinputpath + self.fileCode + self.gridcodemet + '_' + str(self.YYYY) + '_data_' + str(
            self.resin) + '.txt'
        self.met_data = np.genfromtxt(data_in, skip_header=1, missing_values='**********', filling_values=-9999)

        if np.min(self.met_data[:, 0]) - np.max(self.met_data[:, 0]) < 0:
            minis = np.min(self.met_data[:-1, 1])
            maxis = np.max(self.met_data[:, 1])
        else:
            minis = np.min(self.met_data[:, 1])
            maxis = np.max(self.met_data[:, 1])

        # QMessageBox.critical(self.dlg, "Min", str(minis))
        # QMessageBox.critical(self.dlg, "Max", str(maxis))
        # return

        for i in range(int(minis), int(maxis)):
            self.dlg.comboBox_SpatialDOYMin.addItem(str(i))
            self.dlg.comboBox_SpatialDOYMax.addItem(str(i))

        # self.dlg.comboBox_POIDOYMin.setCurrentIndex(0)
        # self.dlg.comboBox_POIDOYMax.setCurrentIndex(0)

    def geotiff_save(self):
        self.outputfile = self.fileDialog.getSaveFileName(None, "Save File As:", None, "GeoTIFF (*.tif)")
        self.dlg.textOutput.setText(self.outputfile)

    def get_unit(self):
        uni = self.lineunit[self.id]
        if uni == 'W_m-2':
            self.unit = '$W$'' ''$m ^{-2}$'
        elif uni == 'mm':
            self.unit = '$mm$'
        elif uni == 'degC':
            self.unit = '$^{o}C$'
        elif uni == 'deg':
            self.unit = '$Degrees(^{o})$'
        elif uni == '-':
            self.unit = '$-$'
        elif uni == 'm2_m-2':
            self.unit = '$m ^{2}$'' ''$m ^{-2}$'
        elif uni == 'm':
            self.unit = '$m$'
        elif uni == 'm_s-1':
            self.unit = '$m$'' ''$s ^{-1}$'
        elif uni == 'umol_m-2_s-1':
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

        if self.dlg.comboBox_SpatialDOYMin.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Minimum DOY is selected")
            return

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

        poly_field = self.layerComboManagerPolyField.currentField()
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
            startday = int(self.dlg.comboBox_SpatialDOYMin.currentText())

        if self.dlg.comboBox_SpatialDOYMax.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
            return
        else:
            endday = int(self.dlg.comboBox_SpatialDOYMax.currentText())

        if startday > endday:
            QMessageBox.critical(self.dlg, "Error", "Start day happens after end day")
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
        for i in range(0,self.idgrid.shape[0]):
            datawhole = np.genfromtxt(self.fileoutputpath + '/' + self.fileCode + str(self.idgrid[i, 0]) + '_'
                                     + str(self.YYYY) + '_' + str(self.resout) + '.txt', skip_header=1,
                                     missing_values='**********', filling_values=-9999)
            start = np.min(np.where(datawhole[:, 1] == startday))
            ending = np.max(np.where(datawhole[:, 1] == endday))
            data1 = datawhole[start:ending, :]

            if self.dlg.checkBox_TOD.isChecked():
                hh = self.dlg.comboBox_HH.currentText()
                hhdata = np.where(data1[:, 2] == int(hh))
                data1 = data1[hhdata, :]
                minute = self.dlg.comboBox_mm.currentText()
                mmdata = np.where(data1[0][:, 3] == int(minute))
                # QMessageBox.critical(self.dlg, "test", str(mmdata))
                data1 = data1[0][mmdata, :]
                data1 = data1[0][:]
                # QMessageBox.critical(self.dlg, "test", str(data1))
                # return
            else:
                if self.dlg.radioButtonDaytime.isChecked():
                    data1 = data1[np.where(data1[:, 52] < 90.), :]
                    data1 = data1[0][:]
                    # QMessageBox.critical(self.dlg, "day", str(data1))
                    # return
                if self.dlg.radioButtonNighttime.isChecked():
                    data1 = data1[np.where(data1[:, 52] > 90.), :]
                    data1 = data1[0][:]
                    # QMessageBox.critical(self.dlg, "night", str(data1))
                    # return

            vardata = data1[:, self.id]

            if self.dlg.radioButtonMean.isChecked():
                statresult = np.nanmean(vardata)
            if self.dlg.radioButtonMin.isChecked():
                statresult = np.nanmin(vardata)
            if self.dlg.radioButtonMax.isChecked():
                statresult = np.nanmax(vardata)
            if self.dlg.radioButtonMed.isChecked():
                statresult = np.nanmedian(vardata)
            if self.dlg.radioButtonIQR.isChecked():
                statresult = np.nanpercentile(vardata, 75) - np.percentile(vardata, 25)

            statvectemp = np.vstack((statvectemp, statresult))

        statvector = statvectemp[1:, :]

        statmat = np.hstack((self.idgrid, statvector))

        numformat2 = '%8d %5.3f'
        header2 = 'id value'
        np.savetxt(self.plugin_dir + 'test.txt', statmat,
                   fmt=numformat2, delimiter=' ', header=header2, comments='')

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        idx = vlayer.fieldNameIndex(poly_field)

        typetest = fields.at(idx).type()
        if typetest == 10:
            QMessageBox.critical(self.dlg, "ID field is sting type", "ID field must be either integer or float")
            return

        header = self.linevar[self.id]
        if self.dlg.addResultToGrid.isChecked():
            self.addattributes(vlayer, statmat, header)

        if self.dlg.addResultToGeotiff.isChecked():
            extent = vlayer.extent()
            xmax = extent.xMaximum()
            xmin = extent.xMinimum()
            ymax = extent.yMaximum()
            ymin = extent.yMinimum()

            if self.dlg.checkBoxIrregular.isChecked():
                resx = self.dlg.doubleSpinBoxRes.value()
            else:
                for f in vlayer.getFeatures():  # Taking first polygon. Could probably be done nicer
                    geom = f.geometry().asPolygon()
                    break

                resx = np.abs(geom[0][0].x() - geom[0][2].x())
                resy = np.abs(geom[0][0].y() - geom[0][2].y())

                if not resx == resy:
                    QMessageBox.critical(self.dlg, "Error", "Polygons not squared in current CRS")
                    return

            polyname = self.dlg.comboBox_Polygrid.currentText()
            if self.dlg.textOutput.text() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No output filename for GeoTIFF is added")
                return
            else:
                filename = self.dlg.textOutput.text()

            gdalraster = 'gdal_rasterize -a ' + str(poly_field) + ' -ot Float32 -of GTiff -te ' + str(xmin) + ' ' \
                         + str(ymin) + ' ' + str(xmax) + ' ' + str(ymax) + ' -tr ' + str(resx) + ' ' + str(resx) + \
                         ' -co COMPRESS=DEFLATE -co PREDICTOR=1 -co ZLEVEL=5 -l ' + polyname + ' "' + \
                         poly.source() + '" "' + self.plugin_dir + '/tempgrid.tif"'

            if sys.platform == 'win32':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.call(gdalraster, startupinfo=si)
            else:
                os.system(gdalraster)

            dataset = gdal.Open(self.plugin_dir + '/tempgrid.tif')
            idgrid_array = dataset.ReadAsArray().astype(np.float)

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
                c.setColorRampType(QgsColorRampShader.INTERPOLATED)
                i = []
                i.append(QgsColorRampShader.ColorRampItem(np.nanmin(gridout), QtGui.QColor('#2b83ba'), str(np.nanmin(gridout))))
                # i.append(QgsColorRampShader.ColorRampItem(900, QtGui.QColor('#fdae61'), ‘900’))
                i.append(QgsColorRampShader.ColorRampItem(np.nanmedian(gridout), QtGui.QColor('#ffffbf'), str(np.nanmedian(gridout))))
                # i.append(QgsColorRampShader.ColorRampItem(2000, QtGui.QColor('#abdda4'), ‘2000’))
                i.append(QgsColorRampShader.ColorRampItem(np.nanmax(gridout), QtGui.QColor('#d7191c'),str(np.nanmax(gridout))))
                c.setColorRampItemList(i)
                s.setRasterShaderFunction(c)
                ps = QgsSingleBandPseudoColorRenderer(rlayer.dataProvider(), 1, s)
                rlayer.setRenderer(ps)

                # Trigger a repaint
                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

        QMessageBox.information(self.dlg, "SUEWS Analyser", "Spatial grid generated")

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
            # vlayer.startEditing()
            vlayer.dataProvider().addAttributes([QgsField(header, QVariant.Double)])
            # vlayer.commitChanges()
            # vlayer.startEditing()
            attr_dict = {}
            for y in range(0, matdata.shape[0]):
                attr_dict.clear()
                idx = int(matdata[y, 0])

                # QMessageBox.information(None, "Error", str(idx))
                attr_dict[current_index_length] = float(matdata[y, 1])

                # QMessageBox.information(None, "Error", str(matdata[y, 1]))
                # vlayer.dataProvider().changeAttributeValue({idx: attr_dict})
                vlayer.dataProvider().changeAttributeValues({y: attr_dict})

            vlayer.updateFields()
            #
            # vlayer.commitChanges()
        else:
            QMessageBox.critical(None, "Error", "Vector Layer does not support adding attributes")

    def plotpoint(self):
        self.varpoi1 = self.dlg.comboBox_POIField.currentText()

        if self.dlg.comboBox_POIField.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Grid ID is selected")
            return

        if self.dlg.comboBox_POIYYYY.currentText() == 'Not Specified':
            QMessageBox.critical(self.dlg, "Error", "No Year is selected")
            return

        if not self.dlg.checkboxPlotBasic.isChecked():

            if self.dlg.comboBox_POIDOYMin.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No Minimum DOY is selected")
                return
            else:
                startday = int(self.dlg.comboBox_POIDOYMin.currentText())

            if self.dlg.comboBox_POIDOYMax.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No Maximum DOY is selected")
                return
            else:
                endday = int(self.dlg.comboBox_POIDOYMax.currentText())

            if startday > endday:
                QMessageBox.critical(self.dlg, "Error", "Start day happens after end day")
                return

            # QMessageBox.critical(self.dlg, "Test", self.fileoutputpath + '/' + self.fileCode + self.varpoi1 + '_' + str(self.YYYY) + '_' + str(self.resout) + '.txt')
            # return
			
			# load and cut data
            # datawhole = np.loadtxt(
            #     self.fileoutputpath + '/' + self.fileCode + self.gridcodemet + '_' + str(self.YYYY) + '_' + str(
            #         self.resout) + '.txt', skiprows=1)
            datawhole = np.genfromtxt(self.fileoutputpath + '/' + self.fileCode + self.varpoi1 + '_' +
                                      str(self.YYYY) + '_' + str(self.resout) + '.txt', skip_header=1,
                                      missing_values='**********', filling_values=-9999)

            start = np.min(np.where(datawhole[:, 1] == startday))
            ending = np.max(np.where(datawhole[:, 1] == endday))
            data1 = datawhole[start:ending, :]

            if self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                QMessageBox.critical(self.dlg, "Error", "No plot variable is selected")
                return

            datenum_yy = np.zeros(data1.shape[0])
            for i in range(0, data1.shape[0]):  # making date number
                datenum_yy[i] = dt.date2num(dt.datetime.datetime(int(data1[i, 0]), 1, 1))

            dectime = datenum_yy + data1[:, 4]
            dates = dt.num2date(dectime)

            if not self.dlg.checkboxPOIAnother.isChecked():
                # One variable
                self.id = self.dlg.comboBox_POIVariable.currentIndex() - 1

                if self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                    QMessageBox.critical(self.dlg, "Error", "No plotting variable is selected")
                    return

                plt.figure(1, figsize=(15, 7), facecolor='white')
                plt.title(self.dlg.comboBox_POIVariable.currentText())
                ax1 = plt.subplot(1, 1, 1)
                ax1.plot(dates, data1[:, self.id], 'r', label='$' + self.dlg.comboBox_POIVariable.currentText() + '$')
                self.get_unit()
                ax1.set_ylabel(self.unit, fontsize=14)
                ax1.set_xlabel('Time', fontsize=14)
                # plt.setp(plt.gca().xaxis.get_majorticklabels(), 'rotation', 45)
                ax1.grid(True)
            else:
                # Two variables
                id1 = self.dlg.comboBox_POIVariable.currentIndex() - 1
                self.id = id1
                self.get_unit()
                varunit1 = self.unit
                id2 = self.dlg.comboBox_POIVariable_2.currentIndex() - 1
                self.id = id2
                self.get_unit()
                varunit2 = self.unit
                if self.dlg.comboBox_POIVariable_2.currentText() == 'Not Specified' or self.dlg.comboBox_POIVariable.currentText() == 'Not Specified':
                    QMessageBox.critical(self.dlg, "Error", "No plotting variable is selected")
                    return
                # self.varpoi1 = self.dlg.comboBox_POIField.currentText()
                self.varpoi2 = self.dlg.comboBox_POIField_2.currentText()
                # data2whole = np.loadtxt(
                #     self.fileoutputpath + '/' + self.fileCode + self.varpoi2 + '_' + str(self.YYYY) + '_' + str(
                #         self.resout) + '.txt', skiprows=1)
                data2whole = np.genfromtxt(
                    self.fileoutputpath + '/' + self.fileCode + self.varpoi2 + '_' + str(self.YYYY) + '_' + str(
                        self.resout) + '.txt', skip_header=1, missing_values='**********', filling_values=-9999)
                data2 = data2whole[start:ending, :]

                if self.dlg.checkboxScatterbox.isChecked():
                    plt.figure(1, figsize=(11, 11), facecolor='white')
                    plt.title(
                        self.dlg.comboBox_POIVariable.currentText() + '(' + self.varpoi1 + ') vs ' + self.dlg.comboBox_POIVariable_2.currentText() + '(' + self.varpoi2 + ')')
                    ax1 = plt.subplot(1, 1, 1)
                    ax1.plot(data1[:, id1], data2[:, id2], "k.")
                    ax1.set_ylabel(self.dlg.comboBox_POIVariable.currentText() + ' (' + varunit1 + ')', fontsize=14)
                    ax1.set_xlabel(self.dlg.comboBox_POIVariable_2.currentText() + ' (' + varunit2 + ')', fontsize=14)
                else:
                    plt.figure(1, figsize=(15, 7), facecolor='white')
                    plt.title(
                        self.dlg.comboBox_POIVariable.currentText() + '(' + self.varpoi1 + ') and ' + self.dlg.comboBox_POIVariable_2.currentText() + '(' + self.varpoi2 + ')')
                    ax1 = plt.subplot(1, 1, 1)
                    if not varunit1 == varunit2:
                        ax2 = ax1.twinx()
                        ax1.plot(dates, data1[:, id1], 'r',
                                 label='$' + self.dlg.comboBox_POIVariable.currentText() + ' (' + self.varpoi1 + ')$')
                        ax1.legend(loc=1)
                        ax2.plot(dates, data2[:, id2], 'b',
                                 label='$' + self.dlg.comboBox_POIVariable_2.currentText() + ' (' + self.varpoi2 + ')$')
                        ax2.legend(loc=2)
                        ax1.set_ylabel(varunit1, color='r', fontsize=14)
                        ax2.set_ylabel(varunit2, color='b', fontsize=14)
                    else:
                        ax1.plot(dates, data1[:, id1], 'r',
                                 label='$' + self.dlg.comboBox_POIVariable.currentText() + ' (' + self.varpoi1 + ')$')
                        ax1.plot(dates, data2[:, id2], 'b',
                                 label='$' + self.dlg.comboBox_POIVariable_2.currentText() + ' (' + self.varpoi2 + ')$')
                        ax1.legend(loc=2)
                        ax1.set_ylabel(varunit1, fontsize=14)

                    # plt.setp(plt.gca().xaxis.get_majorticklabels(), 'rotation', 45)
                    ax1.grid(True)
                    ax1.set_xlabel('Time', fontsize=14)

            plt.show()
        else:
            su = suewsdataprocessing.SuewsDataProcessing()
            pl = suewsplotting.SuewsPlotting()
            TimeCol_plot = np.array([1, 2, 3, 4]) - 1
            SumCol_plot = np.array([14]) - 1
            LastCol_plot = np.array([16]) - 1
            timeaggregation = int(self.resout)

            met_new = su.tofivemin_v1(self.met_data)
            suews_plottimeold = su.from5mintoanytime(met_new, SumCol_plot, LastCol_plot, TimeCol_plot, timeaggregation)
            dataplotbasic = np.genfromtxt(self.fileoutputpath + '/' + self.fileCode + self.varpoi1 + '_' + str(self.YYYY) + '_' +
                          str(self.resout) + '.txt', skip_header=1, missing_values='**********', filling_values=-9999)
            # dataplotbasic = np.loadtxt(self.fileoutputpath + '/' + self.fileCode + self.gridcodemet + '_' + str(self.YYYY) + '_' + str(self.resout) + '.txt', skiprows=1)
            pl.plotbasic(dataplotbasic, suews_plottimeold)
            plt.show()

    def help(self):
        url = 'http://www.urban-climate.net/umep/UMEP_Manual#Urban_Energy_Balance:_SUEWS_Analyser'
        webbrowser.open_new_tab(url)