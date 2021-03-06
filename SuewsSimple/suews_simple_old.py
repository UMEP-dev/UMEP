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
from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import *
from qgis.gui import *
from .suews_simple_dialog import SuewsSimpleDialog
from ..suewsmodel import Suews_wrapper_v2018a
from ..ImageMorphParmsPoint.imagemorphparmspoint_v1 import ImageMorphParmsPoint
from ..LandCoverFractionPoint.landcover_fraction_point import LandCoverFractionPoint
from ..Utilities import f90nml
import urllib.request, urllib.parse, urllib.error
import numpy as np
import shutil
import sys
import os.path
import webbrowser
import time
# from suewssimpleworker import Worker


class SuewsSimple(object):
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
        # self.fileDialogOut.setFileMode(4)
        # self.fileDialogOut.setAcceptMode(1)
        self.fileDialogOut.setFileMode(QFileDialog.Directory)
        self.fileDialogOut.setOption(QFileDialog.ShowDirsOnly, True)
        self.folderPathOut = None
        self.folderPath = None

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
        # fix_print_with_import
        # print(self.model_dir)

        if not (os.path.isfile(self.model_dir + os.sep + 'SUEWS_V2018a') or os.path.isfile(self.model_dir + os.sep + 'SUEWS_V2018a.exe')):
            # QMessageBox.information(self.iface.mainWindow(),
            if QMessageBox.question(self.iface.mainWindow(), "OS specific binaries missing",
                                 "Before you start to use this plugin for the very first time, the OS specific suews\r\n"
                                 "program (4Mb) must be be download from the UMEP repository and stored\r\n"
                                 "in your plugin directory: "
                                 "(" + self.model_dir + ").\r\n"
                                                        "\r\n"
                                 "Join the email-list for updates and other information:\r\n"
                                 "http://www.lists.rdg.ac.uk/mailman/listinfo/met-umep.\r\n"
                                                        "\r\n"
                                 "UMEP on the web:\r\n"
                                 "http://www.urban-climate.net/umep/\r\n"
                                                        "\r\n"
                                                        "\r\n"
                                 "Do you want to contiune with the download?", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
                # testfile = urllib.URLopener()
                if sys.platform == 'win32':
                    # print self.model_dir + os.sep + 'SUEWS_V2017b.exe'
                    # testfile.retrieve('http://www.urban-climate.net/umep/repo/nib/win/SUEWS_V2017b.exe', self.model_dir + os.sep + 'SUEWS_V2017b.exe')
                    urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695894_suews_v2018a.exe',
                                      self.model_dir + os.sep + 'SUEWS_V2018a.exe')
                    # testfile2 = urllib.URLopener()
                    # testfile2.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cyggcc_s-seh-1.dll', self.model_dir + os.sep + 'cyggcc_s-seh-1.dll')
                    # testfile3 = urllib.URLopener()
                    # testfile3.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cyggfortran-3.dll', self.model_dir + os.sep + 'cyggfortran-3.dll')
                    # testfile4 = urllib.URLopener()
                    # testfile4.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cygquadmath-0.dll', self.model_dir + os.sep + 'cygquadmath-0.dll')
                    # testfile5 = urllib.URLopener()
                    # testfile5.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cygwin1.dll', self.model_dir + os.sep + 'cygwin1.dll')
                if sys.platform == 'linux2':
                    urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695887_suews_v2018a', self.model_dir + os.sep + 'SUEWS_V2018a')
                if sys.platform == 'darwin':
                    urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695886_suews_v2018a', self.model_dir + os.sep + 'SUEWS_V2018a')
            else:
                QMessageBox.critical(self.iface.mainWindow(), "Binaries not downloaded", "This plugin will not be able to start before binaries are downloaded")
                return

        self.dlg.show()
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
            self.dlg.textOutput.setText(self.folderPathOut[0] + '/')

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
        self.fileDialogInit.open()
        result = self.fileDialogInit.exec_()
        if result == 1:
            self.folderPathInit = self.fileDialogInit.selectedFiles()
            nml = f90nml.read(self.folderPathInit[0])
            # dayssincerain = nml['initialconditions']['dayssincerain']
            # dailymeantemperature = nml['initialconditions']['temp_c0']
            # self.dlg.DaysSinceRain.setText(str(dayssincerain))
            # self.dlg.DailyMeanT.setText(str(dailymeantemperature))
            self.dlg.comboBoxLeafCycle.setCurrentIndex(1)

    def export_initial(self):
        outputfile = self.fileDialog.getSaveFileName(None, "Save As:", None, "Namelist (*.nml)")
        # self.fileDialogInit.open()
        # result = self.fileDialogInit.exec_()
        if outputfile:
            self.folderPathInit = outputfile
            self.write_to_init(self.model_dir + '/BaseFiles/InitialConditionsKc_2012.nml', self.folderPathInit)

    def set_default_settings(self):
        f = open(self.model_dir + '/BaseFiles/SUEWS_SiteSelect.txt')
        lin = f.readlines()
        index = 2
        lines = lin[index].split()
        self.dlg.lineEdit_YYYY.setText(lines[1])
        self.dlg.pai_paved.setText(lines[13])
        self.dlg.pai_build.setText(lines[14])
        self.dlg.pai_evergreen.setText(lines[15])
        self.dlg.pai_decid.setText(lines[16])
        self.dlg.pai_grass.setText(lines[17])
        self.dlg.pai_baresoil.setText(lines[18])
        self.dlg.pai_water.setText(lines[19])
        self.dlg.lineEdit_zHBuild.setText(lines[23])
        self.dlg.lineEdit_faiBuild.setText(lines[28])
        self.dlg.lineEdit_paiBuild.setText(lines[14])
        self.dlg.lineEdit_zHveg.setText(str((float(lines[24]) + float(lines[25])) / 2))
        self.dlg.lineEdit_faiveg.setText(str((float(lines[29]) + float(lines[30])) / 2))
        self.dlg.lineEdit_paiveg.setText(str(float(lines[15]) + float(lines[16])))
        self.dlg.Latitude.setText(lines[4])
        self.dlg.Longitude.setText(lines[5])
        self.dlg.PopDensNight.setText(lines[32])
        self.dlg.Height.setText(lines[9])

        # nml = f90nml.read(self.model_dir + '/BaseFiles/InitialConditionsKc_2012.nml')
        # dayssincerain = nml['initialconditions']['dayssincerain']
        # dailymeantemperature = nml['initialconditions']['temp_c0']
        # self.dlg.DaysSinceRain.setText(str(dayssincerain))
        # self.dlg.DailyMeanT.setText(str(dailymeantemperature))
        self.dlg.comboBoxLeafCycle.setCurrentIndex(1)

        nml = f90nml.read(self.model_dir + '/BaseFiles/RunControl.nml')

        self.dlg.FileCode.setText(str(nml['runcontrol']['FileCode']))

        self.dlg.UTC.setText('0')

        self.dlg.textInputMetdata.setText(self.model_dir + '/BaseFiles/Kc_2012_data_60.txt')
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
                "building fraction between the Vegetation DSM and the landcover grid was found: " + str(float(self.dlg.pai_decid.text()) + float(self.dlg.pai_evergreen.text()) - float(self.dlg.lineEdit_paiveg.text())))
            return

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
        filecode = self.dlg.FileCode.text()
        utc = self.dlg.UTC.text()
        z = self.dlg.Height.text()

        # Checking LC fractions = 1
        LCtest = float(pai_paved) + float(pai_build) + float(pai_evergreen) + float(pai_decid) + float(pai_grass) + float(pai_baresoil) + float(pai_water)
        if not LCtest == 1.:
            QMessageBox.critical(self.iface.mainWindow(), "Non-consistency Error", "Sum of Land cover fraction is not"
                                                                                   " equal to 1 (" + str(LCtest) + ")")
            return

        # Create new SiteSelect
        f = open(self.model_dir + '/BaseFiles/SUEWS_SiteSelect.txt', 'r')
        lin = f.readlines()
        index = 2
        lines = np.array(lin[index].split())
        newdata = lines
        # gridcode = newdata[0]
        newdata[1] = YYYY
        newdata[4] = lat
        newdata[5] = lon
        newdata[6] = int(utc)
        newdata[9] = float(z)
        newdata[13] = pai_paved
        newdata[14] = pai_build
        newdata[15] = pai_evergreen
        newdata[16] = pai_decid
        newdata[17] = pai_grass
        newdata[18] = pai_baresoil
        newdata[19] = pai_water
        newdata[23] = zHBuild
        newdata[24] = zHveg
        newdata[25] = zHveg
        newdata[28] = faiBuild
        newdata[29] = faiveg
        newdata[30] = faiveg
        newdata[32] = popdens
        self.write_site_select(1, newdata)
        f.close()

        # Plots or not
        if self.dlg.checkBoxPlots.isChecked():
            plot = 1
        else:
            plot = 0
        plotnml = f90nml.read(self.model_dir + '/plot.nml')
        plotnml['plot']['plotbasic'] = plot
        plotnml['plot']['plotmonthlystat'] = plot
        plotnml.write(self.model_dir + '/plot.nml', force=True)

        # Create new RunControl
        inmetfile = self.dlg.textInputMetdata.text()
        outfolder = self.dlg.textOutput.text() + '/'
        nml = f90nml.read(self.model_dir + '/BaseFiles/RunControl.nml')
        if not (faiBuild == -999.0 or faiveg == -999.0):
            nml['runcontrol']['RoughLenMomMethod'] = 3

        resolutionfilesin = nml['runcontrol']['resolutionfilesin']
        runmetfile = self.model_dir + '/Input/' + str(filecode) + '_' + self.dlg.lineEdit_YYYY.text() + '_data_' + str(int(int(resolutionfilesin) / 60.)) + '.txt'
        try:
            shutil.copy(inmetfile, runmetfile)
        except:
            os.remove(inmetfile)
            shutil.copy(inmetfile, runmetfile)

        nml['runcontrol']['fileCode'] = str(filecode)
        nml['runcontrol']['fileoutputpath'] = str(outfolder)
        nml['runcontrol']['fileinputpath'] = self.model_dir + '/Input/'
        nml.write(self.model_dir + '/RunControl.nml', force=True)

        initfilein = self.model_dir + '/BaseFiles/InitialConditionsKc_2012.nml'
        initfileout = self.model_dir + '/Input/InitialConditions' + str(filecode) + '_' + str(YYYY) + '.nml'
        self.write_to_init(initfilein, initfileout)

        # TODO: Put suews in a worker
        # self.startWorker(self.iface, self.model_dir, self.dlg)

        QMessageBox.information(self.dlg,
                                "Model information", "Model run will now start. QGIS might freeze during calcualtion."
                                "This will be fixed in future versions")
        # Suews_wrapper_v2018a.wrapper(self.model_dir)
        try:
            Suews_wrapper_v2018a.wrapper(self.model_dir)
            time.sleep(1)
            self.iface.messageBar().pushMessage("Model run finished", "Check problems.txt in " + self.model_dir + " for "
                            "additional information about the run", level=Qgis.Success)
        except Exception as e:
            time.sleep(1)
            QMessageBox.critical(self.dlg, "An error occurred", str(e) + "\r\n\r\n"
                                        "Also check problems.txt in " + self.model_dir + "\r\n\r\n"
                                        "Please report any errors to https://bitbucket.org/fredrik_ucg/umep/issues")
            return

        shutil.copy(self.model_dir + '/RunControl.nml', outfolder + '/RunControl.nml')

    def write_to_init(self, initfilein, initfileout):
        LeafCycle = self.dlg.comboBoxLeafCycle.currentIndex()
        SoilMoisture = self.dlg.spinBoxSoilMoisture.value()
        moist = int(SoilMoisture * 1.5)

        nml = f90nml.read(initfilein)

        nml['initialconditions']['soilstorepavedstate'] = moist
        nml['initialconditions']['soilstorebldgsstate'] = moist
        nml['initialconditions']['soilstoreevetrstate'] = moist
        nml['initialconditions']['soilstoredectrstate'] = moist
        nml['initialconditions']['soilstoregrassstate'] = moist
        nml['initialconditions']['soilstorebsoilstate'] = moist

        if not (LeafCycle == 1 or LeafCycle == 5):
            self.iface.messageBar().pushMessage("Warning", "A transition period between Winter and Summer has been "
                                                           "choosen. Preferably start the model run during Winter or "
                                                           "Summer.", level=QgsMessageBar.WARNING)

        # Based on London data
        if LeafCycle == 1:  # Winter
            nml['initialconditions']['gdd_1_0'] = 0
            nml['initialconditions']['gdd_2_0'] = -450
            nml['initialconditions']['laiinitialevetr'] = 4
            nml['initialconditions']['laiinitialdectr'] = 1
            nml['initialconditions']['laiinitialgrass'] = 1.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.3
            nml['initialconditions']['porosity0'] = 0.2
        elif LeafCycle == 2:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.4
            nml['initialconditions']['porosity0'] = 0.3
        elif LeafCycle == 3:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.6
            nml['initialconditions']['porosity0'] = 0.5
        elif LeafCycle == 4:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4.5
            nml['initialconditions']['laiinitialgrass'] = 4.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.8
            nml['initialconditions']['porosity0'] = 0.6
        elif LeafCycle == 5:  # Summer
            nml['initialconditions']['gdd_1_0'] = 300
            nml['initialconditions']['gdd_2_0'] = 0
            nml['initialconditions']['laiinitialevetr'] = 5.1
            nml['initialconditions']['laiinitialdectr'] = 5.5
            nml['initialconditions']['laiinitialgrass'] = 5.9
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.8
            nml['initialconditions']['porosity0'] = 0.6
        elif LeafCycle == 6:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4, 5
            nml['initialconditions']['laiinitialgrass'] = 4.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.8
            nml['initialconditions']['porosity0'] = 0.5
        elif LeafCycle == 7:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.5
            nml['initialconditions']['porosity0'] = 0.4
        elif LeafCycle == 8:  # Late Autumn
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.4
            nml['initialconditions']['porosity0'] = 0.2

        nml.write(initfileout, force=True)

    def help(self):
        url = 'http://umep-docs.readthedocs.io/en/latest/processor/Urban%20Energy%20Balance%20Urban%20Energy%20' \
              'Balance%20(SUEWS,%20simple).html'
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