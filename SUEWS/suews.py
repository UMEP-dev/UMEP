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
from qgis.core import Qgis
from qgis.gui import QgsMessageBar
from .suews_dialog import SUEWSDialog
import os
import shutil
import sys
import webbrowser
import urllib.request, urllib.parse, urllib.error
from ..Utilities import f90nml
from ..suewsmodel import suews_wrapper
import zipfile
import tempfile
from pathlib import Path

class SUEWS(object):
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
        self.fileDialog.setFileMode(QFileDialog.Directory)
        self.fileDialog.setOption(QFileDialog.ShowDirsOnly, True)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SUEWS')
        # TODO: We are going to let the user set this up in a future iteration

        self.model_dir = os.path.normpath(self.plugin_dir + os.sep + os.pardir + os.sep + 'suewsmodel')

        if not (os.path.isdir(self.model_dir + '/Input')):
            os.mkdir(self.model_dir + '/Input')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
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

<<<<<<< HEAD
        try:
            import supy
        except Exception as e:
            QMessageBox.critical(None, 'SUEWS Advanced', 'This plugin requires the supy package to be installed OR upgraded. '
                                                'See Section 2.3 in the UMEP-manual for further information on how ' 
                                                'to install external python packages in QGIS3.')
            return

        self.supylib = sys.modules["supy"].__path__[0]
        # modelver = 'SUEWS_V2018c'
        # if not (os.path.isfile(self.model_dir + os.sep + modelver) or os.path.isfile(
        #         self.model_dir + os.sep + modelver + '.exe')):
        #     if QMessageBox.question(self.iface.mainWindow(), "OS specific binaries missing",
        #                             "Before you start to use this plugin for the very first time, the OS specific suews\r\n"
        #                             "program (1Mb) must be be download from the UMEP repository and stored\r\n"
        #                             "in your plugin directory: "
        #                             "(" + self.model_dir + ").\r\n"
        #                                                    "\r\n"
        #                                                    "Join the email-list for updates and other information:\r\n"
        #                                                    "http://www.lists.rdg.ac.uk/mailman/listinfo/met-umep.\r\n"
        #                                                    "\r\n"
        #                                                    "UMEP on the web:\r\n"
        #                                                    "http://www.urban-climate.net/umep/\r\n"
        #                                                    "\r\n"
        #                                                    "\r\n"
        #                                                    "Do you want to contiune with the download?",
        #                             QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
        #         if sys.platform == 'win32':
        #             urllib.request.urlretrieve(
        #                 'https://zenodo.org/record/2574410/files/SUEWS_2018c_win64.zip?download=1',
        #                 self.model_dir + os.sep + 'temp.zip')
        #             zipped = zipfile.ZipFile(self.model_dir + os.sep + 'temp.zip')
        #             zipped.extract(modelver + '.exe', self.model_dir)
        #             # urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695894_suews_v2018a.exe', self.model_dir + os.sep + 'SUEWS_V2018a.exe')
        #         if sys.platform == 'linux2':
        #             urllib.request.urlretrieve(
        #                 'https://zenodo.org/record/2574410/files/SUEWS_2018c_Linux.zip?download=1',
        #                 self.model_dir + os.sep + 'temp.zip')
        #             zipped = zipfile.ZipFile(self.model_dir + os.sep + 'temp.zip')
        #             zipped.extract(modelver, self.model_dir)
        #             # urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695887_suews_v2018a', self.model_dir + os.sep + 'SUEWS_V2018a')
        #         if sys.platform == 'darwin':
        #             urllib.request.urlretrieve(
        #                 'https://zenodo.org/record/2574410/files/SUEWS_2018c_macOS.zip?download=1',
        #                 self.model_dir + os.sep + 'temp.zip')
        #             zipped = zipfile.ZipFile(self.model_dir + os.sep + 'temp.zip')
        #             zipped.extract(modelver, self.model_dir)
        #             # urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695886_suews_v2018a', self.model_dir + os.sep + 'SUEWS_V2018a')
        #         zipped.close()
        #         os.remove(self.model_dir + os.sep + 'temp.zip')
        #     else:
        #         QMessageBox.critical(self.iface.mainWindow(), "Binaries not downloaded",
        #                              "This plugin will not be able to start before binaries are downloaded")
        #         return
=======
        # try:
        #     import supy
        # except Exception as e:
        #     QMessageBox.critical(None, 'Error', 'This plugin requires the supy package to be installed OR upgraded. '
        #                                         'Please see Section 2.2 in the UMEP-manual for further information on '
        #                                         'how to install missing python packages in QGIS3.')
        #     return

        modelver = 'SUEWS_V2018c'
        if not (os.path.isfile(self.model_dir + os.sep + modelver) or os.path.isfile(
                self.model_dir + os.sep + modelver + '.exe')):
            if QMessageBox.question(self.iface.mainWindow(), "OS specific binaries missing",
                                    "Before you start to use this plugin for the very first time, the OS specific suews\r\n"
                                    "program (1Mb) must be be download from the UMEP repository and stored\r\n"
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
                if sys.platform == 'win32':
                    urllib.request.urlretrieve(
                        'https://zenodo.org/record/2574410/files/SUEWS_2018c_win64.zip?download=1',
                        self.model_dir + os.sep + 'temp.zip')
                    zipped = zipfile.ZipFile(self.model_dir + os.sep + 'temp.zip')
                    zipped.extract(modelver + '.exe', self.model_dir)
                    # urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695894_suews_v2018a.exe', self.model_dir + os.sep + 'SUEWS_V2018a.exe')
                if sys.platform.startswith('linux'):
                    urllib.request.urlretrieve(
                        'https://zenodo.org/record/2574410/files/SUEWS_2018c_Linux.zip?download=1',
                        self.model_dir + os.sep + 'temp.zip')
                    zipped = zipfile.ZipFile(self.model_dir + os.sep + 'temp.zip')
                    zipped.extract(modelver, self.model_dir)
                    # urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695887_suews_v2018a', self.model_dir + os.sep + 'SUEWS_V2018a')
                if sys.platform == 'darwin':
                    urllib.request.urlretrieve(
                        'https://zenodo.org/record/2574410/files/SUEWS_2018c_macOS.zip?download=1',
                        self.model_dir + os.sep + 'temp.zip')
                    zipped = zipfile.ZipFile(self.model_dir + os.sep + 'temp.zip')
                    zipped.extract(modelver, self.model_dir)
                    # urllib.request.urlretrieve('https://gvc.gu.se/digitalAssets/1695/1695886_suews_v2018a', self.model_dir + os.sep + 'SUEWS_V2018a')
                zipped.close()
                os.remove(self.model_dir + os.sep + 'temp.zip')
            else:
                QMessageBox.critical(self.iface.mainWindow(), "Binaries not downloaded",
                                     "This plugin will not be able to start before binaries are downloaded")
                return
>>>>>>> QGIS3

        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = "https://umep-docs.readthedocs.io/en/latest/processor/Urban%20Energy%20Balance%20Urban%20Energy%20Balance%20(SUEWS.BLUEWS,%20advanced).html"
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
        plotnml['plot']['plotforcing'] = plot
        plotnml.write(self.model_dir + '/plot.nml', force=True)

        # Create modified RunControl.nml
        infolder = self.dlg.textInput.text()
        if self.dlg.checkBoxFromSP.isChecked():
            filenamemetdata = None
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

        # nml = f90nml.read(self.model_dir + '/BaseFiles/RunControl.nml')
        nml = f90nml.read(self.supylib + '/sample_run/RunControl.nml')
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
        nml['runcontrol']['fileCode'] = str(filecode)
        nml['runcontrol']['fileinputpath'] = str(infolder) + "/"
        nml['runcontrol']['fileoutputpath'] = str(outfolder) + "/"
        nml['runcontrol']['ResolutionFilesOut'] = int(int(outputRes) * 60.)
        nml['runcontrol']['ResolutionFilesIn'] = int(int(inputRes) * 60.)

        nml.write(self.model_dir + '/RunControl.nml', force=True)

        # TODO: Put suews in a worker
        # self.startWorker(self.iface, self.plugin_dir, self.dlg)

        ### Code for spin-up
        # df_sate_init = sp.init_supy(self.model_dir + '/RunControl.nml')
        # df_forcing = sp.load_forcing_grid('./RunControl.nml', 98)
        # # create a preceding yar forcing dataframe
        # df_forcing_fake = df_forcing.copy()
        # df_forcing_fake.Year -= 1
        # # create a complete forcing data frame
        # df_forcing_fake = df_forcing.copy()
        # df_forcing_fake = df_forcing_fake.shift(-366, freq='D')
        # df_forcing_fake.iy = df_forcing_fake.index.year
        # df_forcing_fake.id = df_forcing_fake.index.dayofyear
        # # combine your forcing dfs
        # df_forcing_all = pd.concat([df_forcing_fake, df_forcing])
        # df_forcing_all.index.freq =‘300s'
        # # run simulatoin
        # df_output, df_state_final = sp.run_supy(df_forcing_all, df_sate_init)
        # # select your period of interest
        # df_sel = df_output.loc[98].loc['2012']

        if self.dlg.checkBoxSpinup.isChecked():
            # Open SiteSelect to get year and gridnames
            sitein = infolder + "/" + 'SUEWS_SiteSelect.txt'
            fs = open(sitein)
            lin = fs.readlines()
            index = 2
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
                                                           "calculation. This will be fixed in future versions. As spin-up"
                                                                   "is choosen model will run twice (double computation time required).")
            else:
                QMessageBox.critical(None, "Error in spin-up", "The meteorological forcing data is not one year long."
                                                               "Either adjust your file or run without spin-up.")
                return
        else:
            QMessageBox.information(None, "Model information", "Model run will now start. QGIS might freeze during "
                                                               "calcualtion. This will be fixed in future versions.")
        try:
            suews_wrapper.wrapper(self.model_dir)

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

                    os.rename(outfolder + '/InitialConditions' + filecode + gridcode + '_' + str(yyyy + 1) + '_EndofRun.nml',
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

                suews_wrapper.wrapper(self.model_dir)

        except Exception as e:
            QMessageBox.critical(self.dlg, "An error occurred", str(e) + "\r\n\r\n"
                                "Check: " + str(list(Path(tempfile.gettempdir()).glob('SuPy.log'))[0]) + "\r\n\r\n"
                                "Please report any errors to https://bitbucket.org/fredrik_ucg/umep/issues")
            return

        shutil.copy(self.model_dir + '/RunControl.nml', outfolder + '/RunControl.nml')
        self.iface.messageBar().pushMessage("Model run successful", "Model run finished", level=Qgis.Success)