# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SuewsSimple
                                 A QGIS plugin
 SUEWS in simple mode
                              -------------------
        begin                : 2015-06-30
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from suews_simple_dialog import SuewsSimpleDialog
import os.path
import Suews_wrapper_v7
from ..ImageMorphParmsPoint.imagemorphparmspoint_v1 import ImageMorphParmsPoint
from ..LandCoverFractionPoint.landcover_fraction_point import LandCoverFractionPoint
import webbrowser
import numpy as np
import shutil
import time

#from f90nml import *

class SuewsSimple:
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
            'SuewsSimple_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SuewsSimpleDialog()
        self.dlg.pushButtonIMPcalcBuild.clicked.connect(self.IMCP)
        self.dlg.pushButtonIMPcalcVeg.clicked.connect(self.IMCP)
        self.dlg.pushButtonLCFPcalc.clicked.connect(self.LCFP)
        self.dlg.pushButtonImport_IMPB.clicked.connect(self.import_file_IMPB)
        self.dlg.pushButtonImport_IMPV.clicked.connect(self.import_file_IMPV)
        self.dlg.pushButtonImport_LCFP.clicked.connect(self.import_file_LCFP)
        self.dlg.defaultButton.clicked.connect(self.set_default_settings)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.pushButtonImport.clicked.connect(self.met_file)
        self.dlg.pushButtonImportInitial.clicked.connect(self.import_initial)
        self.dlg.pushButtonExportInitial.clicked.connect(self.export_initial)

        self.fileDialog = QFileDialog()
        self.fileDialog.setNameFilter("(*Point_isotropic.txt)")

        self.fileDialogInit = QFileDialog()
        self.fileDialogInit.setNameFilter("(*.nml)")

        self.fileDialogMet = QFileDialog()
        self.fileDialogMet.setNameFilter("(*.txt)")

        self.fileDialogOut = QFileDialog()
        self.fileDialogOut.setFileMode(4)
        self.fileDialogOut.setAcceptMode(1)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Suews Simple')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SuewsSimple')
        # self.toolbar.setObjectName(u'SuewsSimple')

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
        return QCoreApplication.translate('SuewsSimple', message)


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

        icon_path = ':/plugins/SuewsSimple/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'SUEWS (simple)'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Suews Simple'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        self.dlg.exec_()

    def IMCP(self):
        sg = ImageMorphParmsPoint(self.iface)
        self.dlg.setEnabled(False)
        sg.run()
        self.dlg.setEnabled(True)

    def LCFP(self):
        sg = LandCoverFractionPoint(self.iface)
        self.dlg.setEnabled(False)
        sg.run()
        self.dlg.setEnabled(True)

    def folder_path(self):
        self.fileDialogOut.open()
        result = self.fileDialogOut.exec_()
        if result == 1:
            self.folderPathOut = self.fileDialogOut.selectedFiles()
            self.dlg.textOutput.setText(self.folderPathOut[0])

    def met_file(self):
        self.fileDialogMet.open()
        result = self.fileDialogMet.exec_()
        if result == 1:
            self.folderPathMet = self.fileDialogMet.selectedFiles()
            self.dlg.textInputMetdata.setText(self.folderPathMet[0])

    def import_file_IMPB(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            headernum = 1
            delim = ' '
            try:
                data = np.loadtxt(self.folderPath[0],skiprows=headernum, delimiter=delim)
            except:
                QMessageBox.critical(None, "Import Error", "The file does not have the correct format")
                return
            self.dlg.lineEdit_zHBuild.setText(str(data[2]))
            self.dlg.lineEdit_faiBuild.setText(str(data[1]))
            self.dlg.lineEdit_paiBuild.setText(str(data[0]))
            if self.dlg.pai_build.text():
                if np.abs(float(self.dlg.pai_build.text()) - data[0]) > 0.05:
                    self.iface.messageBar().pushMessage("Non-consistency warning", "A relatively large difference in "
                    "building fraction between the DSM and the landcover grid was found: " + str(float(self.dlg.pai_build.text())
                                - data[0]), level=QgsMessageBar.WARNING)

    def import_file_IMPV(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            headernum = 1
            delim = ' '
            try:
                data = np.loadtxt(self.folderPath[0],skiprows=headernum, delimiter=delim)
            except:
                QMessageBox.critical(None, "Import Error", "The file does not have the correct format")
                return
            self.dlg.lineEdit_zHveg.setText(str(data[2]))
            self.dlg.lineEdit_faiveg.setText(str(data[1]))
            self.dlg.lineEdit_paiveg.setText(str(data[0]))
            if self.dlg.pai_evergreen.text() or self.dlg.pai_decid.text():
                if np.abs(float(self.dlg.pai_decid.text()) + float(self.dlg.pai_evergreen.text()) - data[0]) > 0.05:
                    self.iface.messageBar().pushMessage("Non-consistency warning", "A relatively large difference in "
                    "vegetation fraction between the canopy DSM and the landcover grid was found: " + str(float(self.dlg.pai_decid.text()) + float(self.dlg.pai_evergreen.text())
                                - data[0]), level=QgsMessageBar.WARNING)

    def import_file_LCFP(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            headernum = 1
            delim = ' '
            try:
                data = np.loadtxt(self.folderPath[0],skiprows=headernum, delimiter=delim)
            except:
                QMessageBox.critical(None, "Import Error", "The file does not have the correct format")
                return
            self.dlg.pai_paved.setText(str(data[0]))
            self.dlg.pai_build.setText(str(data[1]))
            self.dlg.pai_evergreen.setText(str(data[2]))
            self.dlg.pai_decid.setText(str(data[3]))
            self.dlg.pai_grass.setText(str(data[4]))
            self.dlg.pai_baresoil.setText(str(data[5]))
            self.dlg.pai_water.setText(str(data[6]))
            if self.dlg.lineEdit_paiBuild.text():
                if np.abs(float(self.dlg.lineEdit_paiBuild.text()) - data[1]) > 0.05:
                    self.iface.messageBar().pushMessage("Non-consistency warning", "A relatively large difference in "
                    "building fraction between the DSM and the landcover grid was found: " + str(float(self.dlg.lineEdit_paiBuild.text()) - data[1]), level=QgsMessageBar.WARNING)
            if self.dlg.lineEdit_paiveg.text():
                if np.abs(float(self.dlg.lineEdit_paiveg.text()) - data[2] - data[3]) > 0.05:
                    self.iface.messageBar().pushMessage("Non-consistency warning", "A relatively large difference in "
                    "vegetation fraction between the canopy DSM and the landcover grid was found: " + str(float(self.dlg.lineEdit_paiveg.text()) - data[2] - data[3]), level=QgsMessageBar.WARNING)

    def import_initial(self):
        import sys
        sys.path.append(self.plugin_dir)
        import f90nml
        self.fileDialogInit.open()
        result = self.fileDialogInit.exec_()
        if result == 1:
            self.folderPathInit = self.fileDialogInit.selectedFiles()
            nml = f90nml.read(self.folderPathInit[0])
            dayssincerain = nml['initialconditions']['dayssincerain']
            dailymeantemperature = nml['initialconditions']['temp_c0']
            self.dlg.DaysSinceRain.setText(str(dayssincerain))
            self.dlg.DailyMeanT.setText(str(dailymeantemperature))
            self.dlg.comboBoxLeafCycle.setCurrentIndex(1)

    def export_initial(self):
        import sys
        sys.path.append(self.plugin_dir)
        import f90nml
        self.fileDialogInit.open()
        result = self.fileDialogInit.exec_()
        if result == 1:
            self.folderPathInit = self.fileDialogInit.selectedFiles()

            DaysSinceRain = self.dlg.DaysSinceRain.text()
            DailyMeanT = self.dlg.DailyMeanT.text()
            LeafCycle = self.dlg.comboBoxLeafCycle.currentIndex() - 1.
            SoilMoisture = self.dlg.spinBoxSoilMoisture.value()
            moist = int(SoilMoisture * 1.5)

            nml = f90nml.read(self.plugin_dir + '/BaseFiles/InitialConditionsKc1_2012.nml')
            nml['initialconditions']['dayssincerain'] = int(DaysSinceRain)
            nml['initialconditions']['temp_c0'] = float(DailyMeanT)
            nml['initialconditions']['soilstorepavedstate'] = moist
            nml['initialconditions']['soilstorebldgsstate'] = moist
            nml['initialconditions']['soilstoreevetrstate'] = moist
            nml['initialconditions']['soilstoredectrstate'] = moist
            nml['initialconditions']['soilstoregrassstate'] = moist
            nml['initialconditions']['soilstorebsoilstate'] = moist

            if LeafCycle == 0: # Winter
                nml['initialconditions']['gdd_1_0'] = 0
                nml['initialconditions']['gdd_2_0'] = -450
                nml['initialconditions']['laiinitialevetr'] = 4
                nml['initialconditions']['laiinitialdectr'] = 1
                nml['initialconditions']['laiinitialgrass'] = 1.6
            elif LeafCycle == 1:
                nml['initialconditions']['gdd_1_0'] = 50
                nml['initialconditions']['gdd_2_0'] = -400
                nml['initialconditions']['laiinitialevetr'] = 4.2
                nml['initialconditions']['laiinitialdectr'] = 2.0
                nml['initialconditions']['laiinitialgrass'] = 2.6
            elif LeafCycle == 2:
                nml['initialconditions']['gdd_1_0'] = 150
                nml['initialconditions']['gdd_2_0'] = -300
                nml['initialconditions']['laiinitialevetr'] = 4.6
                nml['initialconditions']['laiinitialdectr'] = 3.0
                nml['initialconditions']['laiinitialgrass'] = 3.6
            elif LeafCycle == 3:
                nml['initialconditions']['gdd_1_0'] = 225
                nml['initialconditions']['gdd_2_0'] = -150
                nml['initialconditions']['laiinitialevetr'] = 4.9
                nml['initialconditions']['laiinitialdectr'] = 4.5
                nml['initialconditions']['laiinitialgrass'] = 4.6
            elif LeafCycle == 4: # Summer
                nml['initialconditions']['gdd_1_0'] = 300
                nml['initialconditions']['gdd_2_0'] = 0
                nml['initialconditions']['laiinitialevetr'] = 5.1
                nml['initialconditions']['laiinitialdectr'] = 5.5
                nml['initialconditions']['laiinitialgrass'] = 5.9
            elif LeafCycle == 5:
                nml['initialconditions']['gdd_1_0'] = 225
                nml['initialconditions']['gdd_2_0'] = -150
                nml['initialconditions']['laiinitialevetr'] = 4.9
                nml['initialconditions']['laiinitialdectr'] = 4,5
                nml['initialconditions']['laiinitialgrass'] = 4.6
            elif LeafCycle == 6:
                nml['initialconditions']['gdd_1_0'] = 150
                nml['initialconditions']['gdd_2_0'] = -300
                nml['initialconditions']['laiinitialevetr'] = 4.6
                nml['initialconditions']['laiinitialdectr'] = 3.0
                nml['initialconditions']['laiinitialgrass'] = 3.6
            elif LeafCycle == 7:
                nml['initialconditions']['gdd_1_0'] = 50
                nml['initialconditions']['gdd_2_0'] = -400
                nml['initialconditions']['laiinitialevetr'] = 4.2
                nml['initialconditions']['laiinitialdectr'] = 2.0
                nml['initialconditions']['laiinitialgrass'] = 2.6
            nml.write(self.folderPathInit[0], force=True)

    def set_default_settings(self):
        import sys
        sys.path.append(self.plugin_dir)
        import f90nml
        f = open(self.plugin_dir + '/BaseFiles/SUEWS_SiteSelect.txt')
        lin = f.readlines()
        index = 2
        lines = lin[index].split()
        self.dlg.lineEdit_YYYY.setText(lines[1])
        self.dlg.pai_paved.setText(lines[11])
        self.dlg.pai_build.setText(lines[12])
        self.dlg.pai_evergreen.setText(lines[13])
        self.dlg.pai_decid.setText(lines[14])
        self.dlg.pai_grass.setText(lines[15])
        self.dlg.pai_baresoil.setText(lines[16])
        self.dlg.pai_water.setText(lines[17])
        self.dlg.lineEdit_zHBuild.setText(lines[21])
        self.dlg.lineEdit_faiBuild.setText(lines[26])
        self.dlg.lineEdit_paiBuild.setText(lines[12])
        self.dlg.lineEdit_zHveg.setText(str((float(lines[22]) + float(lines[23])) / 2))
        self.dlg.lineEdit_faiveg.setText(str((float(lines[27]) + float(lines[28])) / 2))
        self.dlg.lineEdit_paiveg.setText(str((float(lines[13]) + float(lines[14])) / 2))
        self.dlg.Latitude.setText(lines[4])
        self.dlg.Longitude.setText(lines[5])

        nml = f90nml.read(self.plugin_dir + '/BaseFiles/InitialConditionsKc1_2012.nml')
        dayssincerain = nml['initialconditions']['dayssincerain']
        dailymeantemperature = nml['initialconditions']['temp_c0']
        self.dlg.DaysSinceRain.setText(str(dayssincerain))
        self.dlg.DailyMeanT.setText(str(dailymeantemperature))
        self.dlg.comboBoxLeafCycle.setCurrentIndex(1)

        self.dlg.UTC.setText('0')

        self.dlg.textInputMetdata.setText(self.plugin_dir + '/BaseFiles/Kc1_data.txt')
        self.dlg.textOutput.setText(self.plugin_dir + '/Output/')
        self.dlg.spinBoxSoilMoisture.setValue(100)

        self.dlg.runButton.setEnabled(True)

    def write_site_select(self, numoflines, newdata):
        f = open(self.plugin_dir + '/BaseFiles/SUEWS_SiteSelect.txt', 'r')
        lin = f.readlines()
        f2 = open(self.plugin_dir + '/Input/SUEWS_SiteSelect.txt', 'w')

        # write to file
        f2.write(lin[0])
        f2.write(lin[1])
        for l in range(0, numoflines):
            for i in range(0, newdata.__len__()):
                f2.write(str(newdata[i]))
                f2.write('\t')
            f2.write('\n')
        f2.write(lin[2 + numoflines])
        f2.write(lin[3 + numoflines])
        f.close()
        f2.close()

    def start_progress(self):
        import sys
        sys.path.append(self.plugin_dir)
        import f90nml
        try:
            import matplotlib.pyplot
        except ImportError:
            pass
            self.iface.messageBar().pushMessage("Unable to import Matplotlib module", "Plots will not be produced", level=QgsMessageBar.WARNING)

        # Getting values from GUI
        YYYY = self.dlg.lineEdit_YYYY.text()
        pai_paved = self.dlg.pai_paved.text()
        pai_build = self.dlg.pai_build.text()
        pai_evergreen = self.dlg.pai_evergreen.text()
        pai_decid = self.dlg.pai_decid.text()
        pai_grass = self.dlg.pai_grass.text()
        pai_baresoil = self.dlg.pai_baresoil.text()
        pai_water = self.dlg.pai_water.text()
        zHBuild = self.dlg.lineEdit_zHBuild.text()
        faiBuild = float(self.dlg.lineEdit_faiBuild.text())
        paiBuild = self.dlg.lineEdit_paiBuild.text()
        zHveg = self.dlg.lineEdit_zHveg.text()
        faiveg = float(self.dlg.lineEdit_faiveg.text())
        paiveg = self.dlg.lineEdit_paiveg.text()
        lat =self.dlg.Latitude.text()
        lon = self.dlg.Longitude.text()

        # Create new SiteSelect
        f = open(self.plugin_dir + '/BaseFiles/SUEWS_SiteSelect.txt', 'r')
        lin = f.readlines()
        index = 2
        lines = np.array(lin[index].split())
        newdata = lines
        newdata[1] = YYYY
        newdata[4] = lat
        newdata[5] = lon
        newdata[11] = pai_paved
        newdata[12] = pai_build
        newdata[13] = pai_evergreen
        newdata[14] = pai_decid
        newdata[15] = pai_grass
        newdata[16] = pai_baresoil
        newdata[17] = pai_water
        newdata[21] = zHBuild
        newdata[22] = zHveg
        newdata[23] = zHveg
        newdata[26] = faiBuild
        newdata[27] = faiveg
        newdata[28] = faiveg
        self.write_site_select(1, newdata)
        f.close()

        # Create new RunControl
        utc = self.dlg.UTC.text()
        inmetfile = self.dlg.textInputMetdata.text()
        outfolder = self.dlg.textOutput.text()
        nml = f90nml.read(self.plugin_dir + '/BaseFiles/RunControl.nml')
        nml['runcontrol']['timezone'] = int(utc)
        if not (faiBuild == -999.0 or faiveg == -999.0):
            nml['runcontrol']['z0_method'] = 3
        shutil.copy(inmetfile, self.plugin_dir + '/Input')
        #os.rename() FIXTHIS!!!
        nml['runcontrol']['fileoutputpath'] = str(outfolder)
        nml['runcontrol']['fileinputpath'] = './Input/'
        nml.write(self.plugin_dir + '/RunControl.nml', force=True)

        # Initial conditions
        DaysSinceRain = self.dlg.DaysSinceRain.text()
        DailyMeanT = self.dlg.DailyMeanT.text()
        LeafCycle = self.dlg.comboBoxLeafCycle.currentIndex() - 1.
        SoilMoisture = self.dlg.spinBoxSoilMoisture.value()
        moist = int(SoilMoisture * 1.5)

        nml = f90nml.read(self.plugin_dir + '/BaseFiles/InitialConditionsKc1_2012.nml')
        nml['initialconditions']['dayssincerain'] = int(DaysSinceRain)
        nml['initialconditions']['temp_c0'] = float(DailyMeanT)
        nml['initialconditions']['soilstorepavedstate'] = moist
        nml['initialconditions']['soilstorebldgsstate'] = moist
        nml['initialconditions']['soilstoreevetrstate'] = moist
        nml['initialconditions']['soilstoredectrstate'] = moist
        nml['initialconditions']['soilstoregrassstate'] = moist
        nml['initialconditions']['soilstorebsoilstate'] = moist

        f = open(self.plugin_dir + '/Input/Kc1_data.txt', 'r')
        lin = f.readlines()
        index = 1
        lines = np.array(lin[index].split())
        nml['initialconditions']['id_prev'] = int(lines[1]) - 1
        f.close()

        if not (LeafCycle == 0 or LeafCycle == 4):
            self.iface.messageBar().pushMessage("Warning", "A transition period between Winter and Summer has been "
                                                           "choosen. Preferably start the model run during Winter or "
                                                           "Summer.", level=QgsMessageBar.WARNING)

        if LeafCycle == 0: # Winter
            nml['initialconditions']['gdd_1_0'] = 0
            nml['initialconditions']['gdd_2_0'] = -450
            nml['initialconditions']['laiinitialevetr'] = 4
            nml['initialconditions']['laiinitialdectr'] = 1
            nml['initialconditions']['laiinitialgrass'] = 1.6
        elif LeafCycle == 1:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
        elif LeafCycle == 2:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
        elif LeafCycle == 3:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4.5
            nml['initialconditions']['laiinitialgrass'] = 4.6
        elif LeafCycle == 4: # Summer
            nml['initialconditions']['gdd_1_0'] = 300
            nml['initialconditions']['gdd_2_0'] = 0
            nml['initialconditions']['laiinitialevetr'] = 5.1
            nml['initialconditions']['laiinitialdectr'] = 5.5
            nml['initialconditions']['laiinitialgrass'] = 5.9
        elif LeafCycle == 5:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4,5
            nml['initialconditions']['laiinitialgrass'] = 4.6
        elif LeafCycle == 6:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
        elif LeafCycle == 7:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6

        nml.write(self.plugin_dir + '/Input/InitialConditionsKc1_2012.nml', force=True)

        # self.iface.messageBar().pushMessage("test: ", str(LeafCycle / 8.))
        try:
            # self.iface.messageBar().pushMessage("Model run started", "Process will take a couple of minutes based on "
            #             "length of meteorological data and computer resources.", level=QgsMessageBar.INFO, duration=10)
            Suews_wrapper_v7.wrapper(self.plugin_dir)
        except:
            f = open(self.plugin_dir + '/problems.txt')
            lines = f.readlines()
            QMessageBox.critical(None, "Model run unsuccessful", str(lines))
            return

        self.iface.messageBar().pushMessage("Model run sucessful", "Check problems.txt in " + self.plugin_dir + " for "
                            "additional information about the run", level=QgsMessageBar.INFO)

        # QMessageBox.information(None, "Image Morphometric Parameters", "Process successful!")

    def help(self):
        url = "file://" + self.plugin_dir + "/help/build/html/index.html"
        webbrowser.open_new_tab(url)