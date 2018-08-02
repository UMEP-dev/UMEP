# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SUEWS
                                 A QGIS plugin
 Full version of SUEWS v2015a
                              -------------------
        begin                : 2015-09-27
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Sue Grimmond
        email                : sue.grimmond@reading.ac.uk
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
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgsMessageBar
from .suews_dialog import SUEWSDialog
import os
import shutil
import sys
import webbrowser
import urllib.request, urllib.parse, urllib.error
from ..Utilities import f90nml
from ..suewsmodel import Suews_wrapper_v2018a


class SUEWS(object):
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
            'SUEWS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SUEWSDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonLoad.clicked.connect(self.folder_path_in)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path_out)
        self.dlg.helpButton.clicked.connect(self.help)
        self.fileDialog = QFileDialog()
        # self.fileDialog.setFileMode(4)
        # self.fileDialog.setAcceptMode(1)
        self.fileDialog.setFileMode(QFileDialog.Directory)
        self.fileDialog.setOption(QFileDialog.ShowDirsOnly, True)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SUEWS')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SUEWS')
        # self.toolbar.setObjectName(u'SUEWS')

        self.model_dir = os.path.normpath(self.plugin_dir + os.sep + os.pardir + os.sep + 'suewsmodel')
        # self.iface.messageBar().pushMessage("test: ", model_dir)

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
        return QCoreApplication.translate('SUEWS', message)

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

        icon_path = ':/plugins/SUEWS/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'SUEWS 2015a'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SUEWS'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        # del self.toolbar

    def run(self):
        if not (os.path.isfile(self.model_dir + os.sep + 'SUEWS_V2018a') or os.path.isfile(self.model_dir + os.sep + 'SUEWS_V2018a.exe')):
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
                                                           "Do you want to contiune with the download?",
                                    QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
                # testfile = urllib.URLopener()
                if sys.platform == 'win32':
                    urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695894_suews_v2018a.exe',
                                      self.model_dir + os.sep + 'SUEWS_V2018a.exe')
                    # testfile2 = urllib.URLopener()
                    # testfile2.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cyggcc_s-seh-1.dll',
                    #                    self.model_dir + os.sep + 'cyggcc_s-seh-1.dll')
                    # testfile3 = urllib.URLopener()
                    # testfile3.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cyggfortran-3.dll',
                    #                    self.model_dir + os.sep + 'cyggfortran-3.dll')
                    # testfile4 = urllib.URLopener()
                    # testfile4.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cygquadmath-0.dll',
                    #                    self.model_dir + os.sep + 'cygquadmath-0.dll')
                    # testfile5 = urllib.URLopener()
                    # testfile5.retrieve('http://www.urban-climate.net/umep/repo/nib/win/cygwin1.dll',
                    #                    self.model_dir + os.sep + 'cygwin1.dll')
                if sys.platform == 'linux2':
                    urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695887_suews_v2018a',
                                      self.model_dir + os.sep + 'SUEWS_V2018a')
                if sys.platform == 'darwin':
                    urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695886_suews_v2018a',
                                      self.model_dir + os.sep + 'SUEWS_V2018a')

            else:
                QMessageBox.critical(self.iface.mainWindow(), "Binaries not downloaded",
                                 "This plugin will not be able to start before binaries are downloaded")
                return

        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = "http://umep-docs.readthedocs.io/en/latest/processor/Urban%20Energy%20Balance%20Urban%20Energy%20" \
              "Balance%20(SUEWS.BLUEWS,%20advanced).html"
        webbrowser.open_new_tab(url)

    def folder_path_out(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathOut = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPathOut[0])

    def folder_path_in(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPathOut = self.fileDialog.selectedFiles()
            self.dlg.textInput.setText(self.folderPathOut[0])

    def start_progress(self):

        # No Plots
        plot = 0
        plotnml = f90nml.read(self.model_dir + '/plot.nml')
        plotnml['plot']['plotbasic'] = plot
        plotnml['plot']['plotmonthlystat'] = plot
        plotnml.write(self.model_dir + '/plot.nml', force=True)

        # Create modified RunControl
        infolder = self.dlg.textInput.text()
        if self.dlg.checkBoxFromSP.isChecked():
            for file in os.listdir(infolder):
                if 'data' in file:
                    filenamemetdata = file

            underscorePos = ([pos for pos, char in enumerate(filenamemetdata) if char == '_'])
            numunderscores = underscorePos.__len__()
            inputRes = filenamemetdata[underscorePos[numunderscores - 1] + 1:filenamemetdata.find('.')]
            filecode = filenamemetdata[0:underscorePos[0]]
        else:
            inputRes = self.dlg.InputRes.text()
            filecode = self.dlg.FileCode.text()

        outputRes = self.dlg.OutputRes.text()
        outfolder = self.dlg.textOutput.text()
        AeroD = self.dlg.comboBoxAeroD.currentIndex()
        Net = self.dlg.comboBoxNet.currentIndex()
        OHM = self.dlg.comboBoxOHM.currentIndex()
        Qf = self.dlg.comboBoxQf.currentIndex()
        Qs = self.dlg.comboBoxQs.currentIndex()
        SMD = self.dlg.comboBoxSMD.currentIndex()
        Stab = self.dlg.comboBoxStab.currentIndex()
        WU = self.dlg.comboBoxWU.currentIndex()
        Z0 = self.dlg.comboBoxZ0.currentIndex()
        if self.dlg.checkBoxSnow.isChecked():
            usesnow = 1
        else:
            usesnow = 0

        # if self.dlg.checkBoxCBL.isChecked():
        #     usecbl = 1
        # else:
        usecbl = 0

        # if self.dlg.checkBoxSOLWEIG.isChecked():
        #     usesolweig = 1
        # else:
        usesolweig = 0

        nml = f90nml.read(self.model_dir + '/BaseFiles/RunControl.nml')
        nml['runcontrol']['CBLuse'] = int(usecbl)
        nml['runcontrol']['SnowUse'] = int(usesnow)
        nml['runcontrol']['NetRadiationMethod'] = int(Net)
        nml['runcontrol']['EmissionsMethod'] = int(Qf)
        nml['runcontrol']['OHMIncQF'] = int(OHM)
        nml['runcontrol']['StabilityMethod'] = int(Stab) + 2
        nml['runcontrol']['StorageHeatMethod'] = int(Qs) + 1
        nml['runcontrol']['RoughLenMomMethod'] = int(AeroD) + 1
        nml['runcontrol']['RoughLenHeatMethod'] = int(Z0) + 1
        nml['runcontrol']['SMDMethod'] = int(SMD)
        nml['runcontrol']['WaterUseMethod'] = int(WU)
        # nml['runcontrol']['SOLWEIGuse'] = int(usesolweig)
        nml['runcontrol']['fileCode'] = str(filecode)
        nml['runcontrol']['fileinputpath'] = str(infolder) + "/"
        nml['runcontrol']['fileoutputpath'] = str(outfolder) + "/"
        nml['runcontrol']['ResolutionFilesOut'] = int(int(outputRes) * 60.)
        nml['runcontrol']['ResolutionFilesIn'] = int(int(inputRes) * 60.)

        nml.write(self.model_dir + '/RunControl.nml', force=True)

        # TODO: Put suews in a worker
        # self.startWorker(self.iface, self.plugin_dir, self.dlg)
        if self.dlg.checkBoxSpinup.isChecked():
            # Open SiteSelect to get year and gridnames
            sitein = infolder + "/" + 'SUEWS_SiteSelect.txt'
            fs = open(sitein)
            lin = fs.readlines()
            index = 3
            gridcode = ''
            lines = lin[index].split()
            yyyy = int(lines[1])

            if (yyyy % 4) == 0:
                if (yyyy % 100) == 0:
                    if (yyyy % 400) == 0:
                        leapyear = 1
                        minperyear = 527040
                    else:
                        leapyear = 0
                        minperyear = 525600
                else:
                    leapyear = 1
                    minperyear = 527040
            else:
                leapyear = 0
                minperyear = 525600

            count = 0
            for line in open(infolder + "/" + filecode + "_" + str(yyyy) + "_data_" + inputRes + ".txt"): count += 1

            linesperyear = int(minperyear / 60.)

            if (count - 1) == linesperyear:
                QMessageBox.information(None, "Model information", "Model run will now start. QGIS might freeze during "
                                                           "calcualtion. This will be fixed in future versions. As spin-up"
                                                                   "is choosen model will run twice (double computation time required).")
            else:
                QMessageBox.critical(None, "Error in spin-up", "The meteorological forcing data is not one year long."
                                                               "Either adjust your file or run without spin-up.")
                return
        else:
            QMessageBox.information(None, "Model information", "Model run will now start. QGIS might freeze during "
                                                               "calcualtion. This will be fixed in future versions.")

        try:
            Suews_wrapper_v2018a.wrapper(self.model_dir)

            # Use spin up:
            if self.dlg.checkBoxSpinup.isChecked():

                nml = f90nml.read(self.model_dir + '/RunControl.nml')
                nml['runcontrol']['multipleinitfiles'] = int(1)
                nml.write(self.model_dir + '/RunControl.nml', force=True)

                # Open SiteSelect to get year and gridnames
                sitein = infolder + "/" + 'SUEWS_SiteSelect.txt'
                fs = open(sitein)
                lin = fs.readlines()
                index = 2
                gridcode = ''
                while gridcode != '-9':
                    lines = lin[index].split()
                    yyyy = int(lines[1])
                    gridcode = lines[0]

                    # if os.path.isfile(infolder + '/InitialConditions' + filecode + '_' + str(yyyy) + '.nml'):
                    #     os.remove(infolder + '/InitialConditions' + filecode + '_' + str(yyyy) + '.nml')

                    os.rename(infolder + '/InitialConditions' + filecode + gridcode + '_' + str(yyyy + 1) + '.nml',
                              infolder + '/InitialConditions' + filecode + gridcode + '_' + str(yyyy) + '.nml')
                    index += 1
                    lines = lin[index].split()
                    gridcode = lines[0]

                for filename in os.listdir(outfolder):
                    filepath = os.path.join(outfolder, filename)
                    try:
                        shutil.rmtree(filepath)
                    except OSError:
                        os.remove(filepath)

                fs.close()

                Suews_wrapper_v2018a.wrapper(self.model_dir)

        except Exception as e:
            QMessageBox.critical(None, "An error occurred", str(e) + "\r\n\r\n"
                                       "Also check problems.txt in " + self.model_dir + "\r\n\r\n"
                                       "Please report any errors to https://bitbucket.org/fredrik_ucg/umep/issues")
            return

        # print outfolder
        shutil.copy(self.model_dir + '/RunControl.nml', outfolder + '/RunControl.nml')
        self.iface.messageBar().pushMessage("Model run finished", "Check problems.txt in " + self.model_dir +
                                            " for additional information about the run", level=QgsMessageBar.INFO)