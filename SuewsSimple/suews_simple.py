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
# Import QGIS and PyQt
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
# import resources_rc
# Import the code for the dialog and other parts of the plugin
from suews_simple_dialog import SuewsSimpleDialog
# from ..suewsmodel import Suews_wrapper_v12
from ..suewsmodel import Suews_wrapper_v2016b
from ..ImageMorphParmsPoint.imagemorphparmspoint_v1 import ImageMorphParmsPoint
from ..LandCoverFractionPoint.landcover_fraction_point import LandCoverFractionPoint
# from suewssimpleworker import Worker
from ..Utilities import f90nml

# Import other python stuff
import urllib
import numpy as np
import shutil
import sys
import os.path
import webbrowser
import time
import traceback


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
        self.dlg.helpButton.clicked.connect(self.help)
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

        self.ret = 0

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Suews Simple')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SuewsSimple')
        # self.toolbar.setObjectName(u'SuewsSimple')

        self.model_dir = os.path.normpath(self.plugin_dir + os.sep + os.pardir + os.sep + 'suewsmodel')
        # sys.path.append(self.model_dir)

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
        if os.path.isfile(self.model_dir + os.sep + 'SUEWS_V2016b') or os.path.isfile(self.model_dir + os.sep + 'SUEWS_V2016b.exe'):
            test = 4
        else:
            QMessageBox.information(self.iface.mainWindow(),
                                 "OS specific binaries missing",
                                 "Before you start to use this plugin for the very first time, the OS specific suews program\r\n"
                                 "will automatically be download from the UMEP repository and stored in your plugin directory:\r\n"
                                 "(" + self.model_dir + ").\r\n"
                                                        "\r\n"
                                 "Join the email-list for updates and other information:\r\n"
                                 "http://www.lists.rdg.ac.uk/mailman/listinfo/met-umep.\r\n"
                                                        "\r\n"
                                 "UMEP on the web:\r\n"
                                 "http://www.urban-climate.net/umep/", QMessageBox.Ok)
            testfile = urllib.URLopener()
            if sys.platform == 'win32':
                testfile.retrieve('http://www.urban-climate.net/umep/repo/nib/win/SUEWS_V2016b.exe', self.model_dir + os.sep + 'SUEWS_V2016b.exe')
                testfile2 = urllib.URLopener()
                testfile2.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cyggcc_s-seh-1.dll', self.model_dir + os.sep + 'cyggcc_s-seh-1.dll')
                testfile3 = urllib.URLopener()
                testfile3.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cyggfortran-3.dll', self.model_dir + os.sep + 'cyggfortran-3.dll')
                testfile4 = urllib.URLopener()
                testfile4.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cygquadmath-0.dll', self.model_dir + os.sep + 'cygquadmath-0.dll')
                testfile5 = urllib.URLopener()
                testfile5.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cygwin1.dll', self.model_dir + os.sep + 'cygwin1.dll')
            if sys.platform == 'linux2':
                testfile.retrieve('http://www.urban-climate.net/umep/repo/nib/linux/SUEWS_V2016b', self.model_dir + os.sep + 'SUEWS_V2016b')
            if sys.platform == 'darwin':
                testfile.retrieve('http://www.urban-climate.net/umep/repo/nib/mac/SUEWS_V2016b', self.model_dir + os.sep + 'SUEWS_V2016b')

        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = "file://" + self.plugin_dir + "/help/Index.html"
        webbrowser.open_new_tab(url)

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

        self.dlg.runButton.setEnabled(True)

    def met_file(self):
        self.fileDialogMet.open()
        result = self.fileDialogMet.exec_()
        if result == 1:
            self.folderPathMet = self.fileDialogMet.selectedFiles()
            self.dlg.textInputMetdata.setText(self.folderPathMet[0])

        self.dlg.runButton.setEnabled(True)

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
                if np.abs(float(self.dlg.pai_build.text()) - data[0]) > 0.01:
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
                if np.abs(float(self.dlg.pai_decid.text()) + float(self.dlg.pai_evergreen.text()) - data[0]) > 0.01:
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
                QMessageBox.critical(self.iface.mainWindow(), "Import Error", "The file does not have the correct format")
                return
            self.dlg.pai_paved.setText(str(data[0]))
            self.dlg.pai_build.setText(str(data[1]))
            self.dlg.pai_evergreen.setText(str(data[2]))
            self.dlg.pai_decid.setText(str(data[3]))
            self.dlg.pai_grass.setText(str(data[4]))
            self.dlg.pai_baresoil.setText(str(data[5]))
            self.dlg.pai_water.setText(str(data[6]))
            if self.dlg.lineEdit_paiBuild.text():
                if np.abs(float(self.dlg.lineEdit_paiBuild.text()) - data[1]) > 0.01:
                    self.iface.messageBar().pushMessage("Non-consistency warning", "A relatively large difference in "
                    "building fraction between the DSM and the landcover grid was found: " + str(float(self.dlg.lineEdit_paiBuild.text()) - data[1]), level=QgsMessageBar.WARNING)
            if self.dlg.lineEdit_paiveg.text():
                if np.abs(float(self.dlg.lineEdit_paiveg.text()) - data[2] - data[3]) > 0.01:
                    self.iface.messageBar().pushMessage("Non-consistency warning", "A relatively large difference in "
                    "vegetation fraction between the canopy DSM and the landcover grid was found: " + str(float(self.dlg.lineEdit_paiveg.text()) - data[2] - data[3]), level=QgsMessageBar.WARNING)

    def import_initial(self):
        # sys.path.append(self.model_dir)
        # from ..Utilities import f90nml
        # import f90nml
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
        # sys.path.append(self.model_dir)
        # import f90nml
        self.fileDialogInit.open()
        result = self.fileDialogInit.exec_()
        if result == 1:
            self.folderPathInit = self.fileDialogInit.selectedFiles()

            DaysSinceRain = self.dlg.DaysSinceRain.text()
            DailyMeanT = self.dlg.DailyMeanT.text()
            LeafCycle = self.dlg.comboBoxLeafCycle.currentIndex() - 1.
            SoilMoisture = self.dlg.spinBoxSoilMoisture.value()
            moist = int(SoilMoisture * 1.5)

            nml = f90nml.read(self.model_dir + '/BaseFiles/InitialConditionsKc1_2012.nml')
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
        # sys.path.append(self.model_dir)
        # import f90nml
        f = open(self.model_dir + '/BaseFiles/SUEWS_SiteSelect.txt')
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
        self.dlg.PopDensNight.setText(lines[30])

        nml = f90nml.read(self.model_dir + '/BaseFiles/InitialConditionsKc1_2012.nml')
        dayssincerain = nml['initialconditions']['dayssincerain']
        dailymeantemperature = nml['initialconditions']['temp_c0']
        self.dlg.DaysSinceRain.setText(str(dayssincerain))
        self.dlg.DailyMeanT.setText(str(dailymeantemperature))
        self.dlg.comboBoxLeafCycle.setCurrentIndex(1)

        nml = f90nml.read(self.model_dir + '/BaseFiles/RunControl.nml')
        self.dlg.Height.setText(str(nml['runcontrol']['z']))

        self.dlg.UTC.setText('0')

        self.dlg.textInputMetdata.setText(self.model_dir + '/BaseFiles/Kc_data.txt')
        self.dlg.textOutput.setText(self.model_dir + '/Output/')
        self.dlg.spinBoxSoilMoisture.setValue(100)

        self.dlg.runButton.setEnabled(True)

    def write_site_select(self, numoflines, newdata):
        f = open(self.model_dir + '/BaseFiles/SUEWS_SiteSelect.txt', 'r')
        lin = f.readlines()
        f2 = open(self.model_dir + '/Input/SUEWS_SiteSelect.txt', 'w')

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
        # import sys
        # sys.path.append(self.model_dir)
        # import f90nml
        try:
            import matplotlib.pyplot
        except ImportError:
            pass
            self.iface.messageBar().pushMessage("Unable to import Matplotlib module. Plots will not be produced",
                                                "Visit UMEP webpage for installation instructions.", level=QgsMessageBar.WARNING)

        # Checking consistency between fractions
        if np.abs(float(self.dlg.pai_build.text()) - float(self.dlg.lineEdit_paiBuild.text())) > 0.05:
            QMessageBox.critical(self.iface.mainWindow(), "Non-consistency Error", "A relatively large difference in "
                "building fraction between the DSM and the landcover grid was found: " + str(float(self.dlg.pai_build.text()) - float(self.dlg.lineEdit_paiBuild.text())))
            return
        if np.abs(float(self.dlg.pai_decid.text()) + float(self.dlg.pai_evergreen.text()) - float(self.dlg.lineEdit_paiveg.text())) > 0.05:
            QMessageBox.critical(self.iface.mainWindow(), "Non-consistency Error", "A relatively large difference in "
                "building fraction between the DSM and the landcover grid was found: " + str(float(self.dlg.pai_decid.text()) + float(self.dlg.pai_evergreen.text()) - float(self.dlg.lineEdit_paiveg.text())))
            return
        # self.iface.messageBar().pushMessage("test", self.dlg.textInputMetdata.text(), level=QgsMessageBar.INFO)

        # Checking consistency between fractions
        # if isinstance(s, basestring)self.dlg.textInputMetdata.text():
        #     QMessageBox.critical(self.iface.mainWindow(), "Information missing", "Both meteorological file and output directory "
        #                                                                          "needs to be specified.")
        #     return

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
        lat = self.dlg.Latitude.text()
        lon = self.dlg.Longitude.text()
        popdens = float(self.dlg.PopDensNight.text())

        # Create new SiteSelect
        f = open(self.model_dir + '/BaseFiles/SUEWS_SiteSelect.txt', 'r')
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
        newdata[30] = popdens
        self.write_site_select(1, newdata)
        f.close()

        # Plots or not
        if self.dlg.checkBoxPlots.isChecked():
            plot = 1
        else:
            plot = 0
        # self.iface.messageBar().pushMessage("Warning", str(plot), level=QgsMessageBar.WARNING)
        plotnml = f90nml.read(self.model_dir + '/plot.nml')
        plotnml['plot']['plotbasic'] = plot
        plotnml['plot']['plotmonthlystat'] = plot
        plotnml.write(self.model_dir + '/plot.nml', force=True)

        # Create new RunControl
        utc = self.dlg.UTC.text()
        z = self.dlg.Height.text()
        inmetfile = self.dlg.textInputMetdata.text()
        outfolder = self.dlg.textOutput.text()
        nml = f90nml.read(self.model_dir + '/BaseFiles/RunControl.nml')
        nml['runcontrol']['timezone'] = int(utc)
        nml['runcontrol']['z'] = float(z)
        if not (faiBuild == -999.0 or faiveg == -999.0):
            nml['runcontrol']['z0_method'] = 3
        shutil.copy(inmetfile, self.model_dir + '/Input')
        #os.rename() FIXTHIS!!!
        nml['runcontrol']['fileoutputpath'] = str(outfolder)
        nml['runcontrol']['fileinputpath'] = self.model_dir + '/Input/'
        nml.write(self.model_dir + '/RunControl.nml', force=True)

        # Initial conditions
        DaysSinceRain = self.dlg.DaysSinceRain.text()
        DailyMeanT = self.dlg.DailyMeanT.text()
        LeafCycle = self.dlg.comboBoxLeafCycle.currentIndex()
        SoilMoisture = self.dlg.spinBoxSoilMoisture.value()
        moist = int(SoilMoisture * 1.5)

        nml = f90nml.read(self.model_dir + '/BaseFiles/InitialConditionsKc1_2012.nml')
        nml['initialconditions']['dayssincerain'] = int(DaysSinceRain)
        nml['initialconditions']['temp_c0'] = float(DailyMeanT)
        nml['initialconditions']['soilstorepavedstate'] = moist
        nml['initialconditions']['soilstorebldgsstate'] = moist
        nml['initialconditions']['soilstoreevetrstate'] = moist
        nml['initialconditions']['soilstoredectrstate'] = moist
        nml['initialconditions']['soilstoregrassstate'] = moist
        nml['initialconditions']['soilstorebsoilstate'] = moist

        f = open(self.model_dir + '/Input/Kc_data.txt', 'r')
        lin = f.readlines()
        index = 1
        lines = np.array(lin[index].split())
        nml['initialconditions']['id_prev'] = int(lines[1]) - 1
        f.close()

        if not (LeafCycle == 1 or LeafCycle == 5):
            self.iface.messageBar().pushMessage("Warning", "A transition period between Winter and Summer has been "
                                                           "choosen. Preferably start the model run during Winter or "
                                                           "Summer.", level=QgsMessageBar.WARNING)

        # nml = self.leaf_cycle(nml,LeafCycle) ### TRY THIS LATER
        if LeafCycle == 1: # Winter
            nml['initialconditions']['gdd_1_0'] = 0
            nml['initialconditions']['gdd_2_0'] = -450
            nml['initialconditions']['laiinitialevetr'] = 4
            nml['initialconditions']['laiinitialdectr'] = 1
            nml['initialconditions']['laiinitialgrass'] = 1.6
        elif LeafCycle == 2:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
        elif LeafCycle == 3:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
        elif LeafCycle == 4:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4.5
            nml['initialconditions']['laiinitialgrass'] = 4.6
        elif LeafCycle == 5: # Summer
            nml['initialconditions']['gdd_1_0'] = 300
            nml['initialconditions']['gdd_2_0'] = 0
            nml['initialconditions']['laiinitialevetr'] = 5.1
            nml['initialconditions']['laiinitialdectr'] = 5.5
            nml['initialconditions']['laiinitialgrass'] = 5.9
        elif LeafCycle == 6:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4,5
            nml['initialconditions']['laiinitialgrass'] = 4.6
        elif LeafCycle == 7:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
        elif LeafCycle == 8: # Late Autumn
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6

        nml.write(self.model_dir + '/Input/InitialConditionsKc1_2012.nml', force=True)

        # TODO: Put suews in a worker
        # self.startWorker(self.iface, self.model_dir, self.dlg)

        QMessageBox.information(None,
                                "Model information", "Model run will now start. QGIS might freeze during calcualtion."
                                "This will be fixed in future versions")
        # Suews_wrapper_v2016b.wrapper(self.model_dir)
        try:
            # Suews_wrapper_v12.wrapper(self.model_dir)
            Suews_wrapper_v2016b.wrapper(self.model_dir)
            time.sleep(1)
            self.iface.messageBar().pushMessage("Model run finished", "Check problems.txt in " + self.model_dir + " for "
                            "additional information about the run", level=QgsMessageBar.INFO)
            # self.test = 1
        except Exception as e:
            # self.test = 0
            time.sleep(1)
            QMessageBox.critical(None, "An error occurred", str(e) + "\r\n\r\n"
                                        "Also check problems.txt in " + self.model_dir + "\r\n\r\n"
                                        "Please report any errors to https://bitbucket.org/fredrik_ucg/umep/issues")
            return

        # if self.test == 1:
        #     self.iface.messageBar().pushMessage("Model run finished", "Check problems.txt in " + self.plugin_dir + " for "
        #                     "additional information about the run", level=QgsMessageBar.INFO)
        # elif self.test == 0:
        #     f = open(self.model_dir + '/problems.txt')
        #     lines = f.readlines()
        #     QMessageBox.critical(None, "Model run unsuccessful", str(lines))
        #     return

    def leaf_cycle(self, nml, LeafCycle):
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

        return nml

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = 'http://www.urban-climate.net/umep/UMEP_Manual#Processor:' \
              '_Urban_Energy_Balance:_Urban_Energy_Balance_.28SUEWS.2C_simple.29'
        webbrowser.open_new_tab(url)

    # def startWorker(self, iface, model_dir, dlg):
    #
    #     worker = Worker(iface, model_dir, dlg)
    #
    #     self.dlg.runButton.setText('Cancel')
    #     self.dlg.runButton.clicked.disconnect()
    #     self.dlg.runButton.clicked.connect(worker.kill)
    #     self.dlg.closeButton.setEnabled(False)
    #
    #     thread = QThread(self.dlg)
    #     worker.moveToThread(thread)
    #     worker.finished.connect(self.workerFinished)
    #     worker.error.connect(self.workerError)
    #     # worker.progress.connect(self.progress_update)
    #     thread.started.connect(worker.run)
    #     thread.start()
    #     self.thread = thread
    #     self.worker = worker
    #
    # def workerFinished(self, ret):
    #     # Tar bort arbetaren (Worker) och traden den kors i
    #     try:
    #         self.worker.deleteLater()
    #     except RuntimeError:
    #          pass
    #     self.thread.quit()
    #     self.thread.wait()
    #     self.thread.deleteLater()
    #
    #     self.iface.messageBar().pushMessage("Model run finished", "Check problems.txt in " + self.plugin_dir + " for "
    #                         "additional information about the run", level=QgsMessageBar.INFO)
    #
    #     #andra tillbaka Run-knappen till sitt vanliga tillstand och skicka ett meddelande till anvanderen.
    #     if ret == 0:
    #         # self.dlg.runButton.setText('Run')
    #         # self.dlg.runButton.clicked.disconnect()
    #         # self.dlg.runButton.clicked.connect(self.start_progress)
    #         # self.dlg.closeButton.setEnabled(True)
    #         # # self.dlg.progressBar.setValue(0)
    #         # QMessageBox.information(self.iface.mainWindow(), "Suews Simple", "Operations cancelled, process unsuccessful!")
    #         self.test = 1
    #     else:
    #         self.test = 0
    #         # self.dlg.runButton.setText('Run')
    #         # self.dlg.runButton.clicked.disconnect()
    #         # self.dlg.runButton.clicked.connect(self.start_progress)
    #         # self.dlg.closeButton.setEnabled(True)
    #         # # self.dlg.progressBar.setValue(0)
    #         # self.iface.messageBar().pushMessage("Model run successful", "Check problems.txt in " + self.model_dir + " for "
    #         #                 "additional information about the run", level=QgsMessageBar.INFO)
    #         # self.iface.messageBar().pushMessage("Suews Simple",
    #         #                         "Process finished! Check General Messages (speech bubble, lower left) "
    #         #                         "to obtain information of the process.")
    #
    #     self.ret = ret
    #
    # def workerError(self, e, exception_string):
    #     strerror = "Worker thread raised an exception: " + str(e)
    #     QgsMessageLog.logMessage(strerror.format(exception_string), level=QgsMessageLog.CRITICAL)
    #     f = open(self.model_dir + '/problems.txt')
    #     lines = f.readlines()
    #     QMessageBox.critical(self.iface.mainWindow(), "Model run unsuccessful", str(lines))