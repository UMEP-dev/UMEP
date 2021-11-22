# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UWGPrepare
                                 A QGIS plugin
 Prepares input data to UWG
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-11-18
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel, QgsVectorLayer, Qgis
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .uwg_prepare_dialog import UWGPrepareDialog
import os.path, os
import webbrowser
from .umep_uwg_export_component import create_uwgdict, get_uwg_file


class UWGPrepare:
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
            'UWGPrepare_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&UWG Prepare')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        # self.first_start = None

        self.output_dir = None
        self.LCFfile_path = None
        self.IMPfile_path = None
        self.zone = 0

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
        return QCoreApplication.translate('UWGPrepare', message)


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

        icon_path = ':/plugins/uwg_prepare/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'UWG PRepare'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UWG Prepare'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        # if self.first_start == True:
            # self.first_start = False

        if not (os.path.isdir(self.plugin_dir + '/tempdata')):
            os.mkdir(self.plugin_dir + '/tempdata')

        self.dlg = UWGPrepareDialog()

        self.outputDialog = QFileDialog()
        self.outputDialog.setFileMode(QFileDialog.Directory)
        self.outputDialog.setOption(QFileDialog.ShowDirsOnly, True)

        self.fileDialog = QFileDialog()
        # self.fileDialog.setFileMode(QFileDialog.ExistingFile)
        self.fileDialog.setNameFilter("(*.txt)")

        self.dlg.pushButtonImportLCF.clicked.connect(lambda: self.set_LCFfile_path())
        self.dlg.pushButtonImportIMPBuild.clicked.connect(lambda: self.set_IMPfile_path())
        self.dlg.closeButton.clicked.connect(lambda: self.close_plugin())

        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.outputButton.clicked.connect(self.set_output_folder)
        self.dlg.runButton.clicked.connect(self.generate)

        self.layerComboManagerPolygrid = QgsMapLayerComboBox(self.dlg.widgetPolygonLayer)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyField = QgsFieldComboBox(self.dlg.widgetPolyField)
        self.layerComboManagerPolyField.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.layerComboManagerPolyField.setLayer)

        self.layerComboManagerPolygridBT = QgsMapLayerComboBox(self.dlg.widgetPolygonLayerBT)
        self.layerComboManagerPolygridBT.setCurrentIndex(-1)
        self.layerComboManagerPolygridBT.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygridBT.setFixedWidth(175)
        # self.layerComboManagerPolyFieldBT = QgsFieldComboBox(self.dlg.widgetPolyFieldBT)
        # self.layerComboManagerPolyFieldBT.setFilters(QgsFieldProxyModel.Numeric)
        # self.layerComboManagerPolygridBT.layerChanged.connect(self.layerComboManagerPolyFieldBT.setLayer)

        self.dlg.comboBoxClimateZone.currentIndexChanged.connect(lambda: self.zone_changed(self.dlg.comboBoxClimateZone.
                                                                                             currentIndex()))

        # show the dialog
        self.dlg.show()
        self.dlg.exec_()


    def set_LCFfile_path(self):
        self.LCFfile_path = self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.LCFfile_path = self.fileDialog.selectedFiles()
        
        if self.LCFfile_path:
            self.dlg.textInputLCFData.setText(self.LCFfile_path[0])
        else:
            self.dlg.textInputLCFData.setText('No file selected')


    def set_IMPfile_path(self):
        self.IMPfile_path = self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.IMPfile_path = self.fileDialog.selectedFiles()
        
        if self.IMPfile_path:
            self.dlg.textInputIMPData.setText(self.IMPfile_path[0])
        else:
            self.dlg.textInputIMPData.setText('No file selected')


    def set_output_folder(self):
        self.outputDialog.open()
        result = self.outputDialog.exec_()
        if result == 1:
            self.output_dir = self.outputDialog.selectedFiles()
            self.dlg.textOutput.setText(self.output_dir[0])
            self.dlg.runButton.setEnabled(1)

    
    def zone_changed(self, index):
        self.zone = index


    def help(self):
        url = "http://umep-docs.readthedocs.io/en/latest/pre-processor/SUEWS%20Prepare.html"
        webbrowser.open_new_tab(url)


    def generate(self):
        self.steps = 0
        if self.output_dir is None:
            QMessageBox.critical(self.dlg, "Error", "No output directory selected")
            return

        # Access grip polygon layer
        poly = self.layerComboManagerPolygrid.currentLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon grid layer is selected")
            return

        poly_field = self.layerComboManagerPolyField.currentField()
        if poly_field == '':
            QMessageBox.critical(None, "Error", "An attribute field with unique fields must be selected")
            return

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")

        map_units = vlayer.crs().mapUnits()
        if not map_units == 0 or map_units == 1 or map_units == 2:
            QMessageBox.critical(self.dlg, "Error", "Could not identify the map units of the polygon layer coordinate "
                                 "reference system")
            return

        # Access Building type layer
        polyBT = self.layerComboManagerPolygridBT.currentLayer()
        if polyBT is None:
            self.iface.messageBar().pushMessage(
                'No valid building type polygon layer is selected. All buildings are classified as mid-rise residental buildings.',
                level=Qgis.Warning, duration=5)
            vlayerBT = None
        else:
        #     poly_fieldBT = self.layerComboManagerPolyFieldBT.currentField()
        #     if poly_fieldBT == '':
        #         QMessageBox.critical(None, "Error", "An attribute field with unique fields must be selected")
        #         return

            vlayerBT = QgsVectorLayer(polyBT.source(), "polygon", "ogr")

        # Check if textfiles are available 
        if self.LCFfile_path is None:
            QMessageBox.critical(None, "Error", "Land cover fractions file has not been provided,"
                                                    " please check the main tab")
            return
        if not os.path.isfile(self.LCFfile_path[0]):
            QMessageBox.critical(None, "Error", "Could not find the file containing land cover fractions")
            return

        if self.IMPfile_path is None:
            QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
                                                " please check the main tab")
            return
        if not os.path.isfile(self.IMPfile_path[0]):
            QMessageBox.critical(None, "Error", "Could not find the file containing building morphology")
            return

        if self.zone == 0:
            QMessageBox.critical(None, "Error", "Please specify a climate zone.")
            return
        else:
            a = self.dlg.comboBoxClimateZone.currentText()
            zone = a[0:a.find(';')]

        if not self.dlg.fileCodeLineEdit.text():
            QMessageBox.critical(None, "Error", "Please specify a file prefix.")
            return
        else:
            prefix = self.dlg.fileCodeLineEdit.text()

        self.dlg.progressBar.setMaximum(vlayer.featureCount())

        # Intersect grids with building type polygons 
        if vlayerBT:
            import processing
            urbantypelayer = self.plugin_dir + '/tempdata/' + 'intersected.shp'

            intersectPrefix = 'i'
            parin = { 'INPUT' : poly.source(), 
            'INPUT_FIELDS' : [], 
            'OUTPUT' : urbantypelayer, 
            'OVERLAY' : polyBT.source(), 
            'OVERLAY_FIELDS' : [], 
            'OVERLAY_FIELDS_PREFIX' : intersectPrefix }

            processing.run('native:intersection', parin)

            vlayertype = QgsVectorLayer(urbantypelayer, "polygon", "ogr")
            type_field = parin['OVERLAY_FIELDS_PREFIX'] + 'uwgType'
            time_field = parin['OVERLAY_FIELDS_PREFIX'] + 'uwgTime'


        #Start loop of polygon grids
        ##land cover and morphology
        index = 0
        for feature in vlayer.getFeatures():
            index = index + 1
            self.dlg.progressBar.setValue(index)
            feat_id = int(feature.attribute(poly_field))

            # create a default dict with all input
            uwgDict = create_uwgdict()

            # uwgDict['Month'] = 3 # starting month (1-12)
            # uwgDict['Day'] = 1 # starting day (1-31)
            # uwgDict['nDay'] = 5 # number of days to run simulation
            uwgDict['zone'] = zone
            uwgDict['charLength'] = feature.geometry().area() ** 0.5

            with open(self.LCFfile_path[0]) as file:
                next(file)
                for line in file:
                    split = line.split()
                    if feat_id == int(split[0]):
                        # LCF_paved = split[1]
                        LCF_buildings = split[2]
                        LCF_evergreen = split[3]
                        LCF_decidious = split[4]
                        LCF_grass = split[5]
                        # LCF_baresoil = split[6]
                        # LCF_water = split[7]
                        #found_LCF_line = True
                        break
            
            with open(self.IMPfile_path[0]) as file:
                next(file)
                for line in file:
                    split = line.split()
                    if feat_id == int(split[0]):
                        IMP_heights_mean = split[3]
                        # IMP_z0 = split[6]
                        # IMP_zd = split[7]
                        # IMP_fai = split[2]
                        # IMP_max = split[4]
                        # IMP_sd = split[5]
                        IMP_wai = split[8]
                        # found_IMP_line = True
                        break

            # Populate dict from UMEP
            uwgDict['bldHeight'] = IMP_heights_mean # average building height (m)
            uwgDict['bldDensity'] = LCF_buildings # urban area building plan density (0-1)
            uwgDict['verToHor'] = IMP_wai # urban area vertical to horizontal ratio
            uwgDict['grasscover'] = LCF_grass # Fraction of the urban ground covered in grass/shrubs only (0-1)
            uwgDict['treeCover'] = str(float(LCF_decidious) + float(LCF_evergreen)) # Fraction of the urban ground covered in trees (0-1)

            ## urban type fractions
            if vlayerBT:
                fracDict = {}
                totarea = 0.0
                types = ['FullServiceRestaurant','Hospital','LargeHotel','LargeOffice','MedOffice',
                    'MidRiseApartment','OutPatient','PrimarySchool','QuickServiceRestaurant',
                    'SecondarySchool','SmallHotel','SmallOffice','StandAloneRetail','StripMall',
                    'SuperMarket','Warehouse']
                buildtime = ['Pst80','Pst80','Pst80','Pst80','Pst80','Pre80','Pst80','Pst80',
                    'Pst80','Pst80','Pst80','Pst80','Pst80','Pst80','Pst80','Pst80'] #this should also come from an unique post for each polygon...
                fractions = [.0,.0,.0,.0,.0,.0,.0,.0,.0,.0,.0,.0,.0,.0,.0,.0]

                fracDict = dict(zip(types, fractions))
                timeDict = dict(zip(types, buildtime))

                # populate dict with area for each available urban type within grid
                for featureType in vlayertype.getFeatures():
                    if feat_id == int(featureType.attribute(poly_field)):
                        area = featureType.geometry().area()
                        fracDict[featureType.attribute(type_field)] = fracDict[featureType.attribute(type_field)] + area
                        timeDict[featureType.attribute(type_field)] = featureType.attribute(time_field)
                        totarea = totarea + area
                for key in fracDict:
                    fracDict[key] = fracDict[key] / totarea
                
                # Populate dict from type polygon layer
                for i in range(0, len(uwgDict['bld'][0])):
                    uwgDict['bld'][1][i] = timeDict[types[i]] 
                    uwgDict['bld'][2][i] = fracDict[types[i]]

            ## generate input files for UWG
            _name = prefix + '_' + str(feat_id)
            get_uwg_file(uwgDict, self.output_dir[0] + '/', _name)

        QMessageBox.information(self.dlg, "UWG Prepare", "Urban Weather Generator input files succesfully generated")
        self.dlg.progressBar.setValue(0)

    def close_plugin(self):
        os.rmdir(self.plugin_dir + '/tempdata')



        


    