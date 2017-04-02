# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BenchMarking
                                 A QGIS plugin
 This plugin can perform benchmarking between datasets
                              -------------------
        begin                : 2017-03-22
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Fredrik Lindberg
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
# Initialize Qt resources from file resources.py
# import resources
# Import the code for the dialog
from benchmarking_dialog import BenchMarkingDialog
import os.path
from ..Utilities import f90nml

import Benchmark_SUEWS as bss
import numpy as np
import webbrowser
import shutil

class BenchMarking:
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
            'BenchMarking_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = BenchMarkingDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonImport.clicked.connect(self.import_basefile)
        self.dlg.pushButtonRefData.clicked.connect(self.import_reffile)
        self.dlg.pushButtonData_2.clicked.connect(self.import_data2file)
        self.dlg.pushButtonData_3.clicked.connect(self.import_data3file)
        self.dlg.pushButtonData_4.clicked.connect(self.import_data4file)
        self.dlg.pushButtonData_5.clicked.connect(self.import_data5file)
        self.dlg.pushButtonPDF.clicked.connect(self.pdf_save)
        self.dlg.pushButtonNamelistOut.clicked.connect(self.nml_save)
        self.dlg.pushButtonHelp.clicked.connect(self.help)

        # self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.fileDialogBaseData = QFileDialog()
        self.fileDialogRefData = QFileDialog()
        self.fileDialogData2 = QFileDialog()
        self.fileDialogData3 = QFileDialog()
        self.fileDialogData4 = QFileDialog()
        self.fileDialogData5 = QFileDialog()
        self.fileDialogPDF = QFileDialog()
        self.fileDialogNMLout = QFileDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Benchmarking')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'BenchMarking')
        self.toolbar.setObjectName(u'BenchMarking')

        self.headernum = 1
        self.delim = None
        self.folderPath = 'None'
        self.folderPath1 = ''
        self.folderPath2 = ''
        self.folderPath3 = ''
        self.folderPath4 = ''
        self.folderPath5 = ''

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('BenchMarking', message)

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
        icon_path = ':/plugins/BenchMarking/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Benchmarking'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Benchmarking'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):

        # Check the more unusual dependencies to prevent confusing errors later
        try:
            import pandas
        except Exception, e:
            QMessageBox.critical(None, 'Error', 'The Benchmarking feature requires the pandas package to be installed. '
                                                'Please consult the FAQ in the manual for further information on how'
                                                'to install missing python packages.')
            return

        self.dlg.show()
        self.dlg.exec_()

    def import_basefile(self):
        self.fileDialogBaseData.open()
        result = self.fileDialogBaseData.exec_()
        if result == 1:
            self.folderPath = self.fileDialogBaseData.selectedFiles()
            self.dlg.textInput_BaseData.setText(self.folderPath[0])
            self.headernum = self.dlg.spinBoxHeader.value()
            delimnum = self.dlg.comboBox_sep.currentIndex()
            if delimnum == 0:
                self.delim = ','
            elif delimnum == 1:
                self.delim = None  # space
            elif delimnum == 2:
                self.delim = '\t'
            elif delimnum == 3:
                self.delim = ';'
            elif delimnum == 4:
                self.delim = ':'

            try:
                self.data = np.loadtxt(self.folderPath[0], skiprows=self.headernum, delimiter=self.delim)
            except:
                QMessageBox.critical(None, "Import Error",
                                     "Check number of header lines, delimiter format and if nodata are present")
                return

    def import_reffile(self):
        self.fileDialogRefData.open()
        result = self.fileDialogRefData.exec_()
        if result == 1:
            self.folderPath1 = self.fileDialogRefData.selectedFiles()
            self.dlg.textInput_RefData.setText(self.folderPath1[0])

            try:
                self.data = np.loadtxt(self.folderPath1[0], skiprows=self.headernum, delimiter=self.delim)
            except:
                QMessageBox.critical(None, "Import Error",
                                     "Check number of header lines, delimiter format and if nodata are present")
                return

    def import_data2file(self):
        self.fileDialogData2.open()
        result = self.fileDialogData2.exec_()
        if result == 1:
            self.folderPath2 = self.fileDialogData2.selectedFiles()
            self.dlg.textInput_Data2.setText(self.folderPath2[0])

            try:
                self.data = np.loadtxt(self.folderPath2[0], skiprows=self.headernum, delimiter=self.delim)
            except:
                QMessageBox.critical(None, "Import Error",
                                     "Check number of header lines, delimiter format and if nodata are present")
                return

    def import_data3file(self):
        self.fileDialogData3.open()
        result = self.fileDialogData3.exec_()
        if result == 1:
            self.folderPath3 = self.fileDialogData3.selectedFiles()
            self.dlg.textInput_Data3.setText(self.folderPath3[0])

            try:
                self.data = np.loadtxt(self.folderPath3[0], skiprows=self.headernum, delimiter=self.delim)
            except:
                QMessageBox.critical(None, "Import Error",
                                     "Check number of header lines, delimiter format and if nodata are present")
                return

    def import_data4file(self):
        self.fileDialogData4.open()
        result = self.fileDialogData4.exec_()
        if result == 1:
            self.folderPath4 = self.fileDialogData4.selectedFiles()
            self.dlg.textInput_Data4.setText(self.folderPath4[0])

            try:
                self.data = np.loadtxt(self.folderPath4[0], skiprows=self.headernum, delimiter=self.delim)
            except:
                QMessageBox.critical(None, "Import Error",
                                     "Check number of header lines, delimiter format and if nodata are present")
                return

    def import_data5file(self):
        self.fileDialogData5.open()
        result = self.fileDialogData5.exec_()
        if result == 1:
            self.folderPath5 = self.fileDialogData5.selectedFiles()
            self.dlg.textInput_Data5.setText(self.folderPath5[0])

            try:
                self.data = np.loadtxt(self.folderPath5[0], skiprows=self.headernum, delimiter=self.delim)
            except:
                QMessageBox.critical(None, "Import Error",
                                     "Check number of header lines, delimiter format and if nodata are present")
                return

    def nml_save(self):
        self.outputfile = self.fileDialogNMLout.getSaveFileName(None, "Save File As:", None, "namelist (*.nml)")
        self.dlg.textInput_NamelistOut.setText(self.outputfile)

    def pdf_save(self):
        self.outputfile = self.fileDialogPDF.getSaveFileName(None, "Save File As:", None, "PDF (*.pdf)")
        self.dlg.textOutputPDF.setText(self.outputfile)

    def start_progress(self):

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid input base dataset")
            return

        # change namelist settings
        prm = f90nml.read(self.plugin_dir + '/benchmark_orig.nml')

        prm['file']['input_basefile'] = str(self.folderPath[0])

        if self.folderPath1 == '':
            QMessageBox.critical(None, "Error", "Select a valid reference dataset")
            return
        else:
            prm['file']['input_reffile'] = str(self.folderPath1[0])

        if self.dlg.checkBox_Data2.isChecked():
            if self.folderPath2 == '':
                QMessageBox.critical(None, "Error", "Select a valid reference dataset")
                return
            else:
                prm['file']['input_cfgfiles(1)'] = str(self.folderPath2[0])

        if self.dlg.checkBox_Data3.isChecked():
            if self.folderPath3 == '':
                QMessageBox.critical(None, "Error", "Select a valid reference dataset")
                return
            else:
                prm['file']['input_cfgfiles(2)'] = str(self.folderPath3[0])

        if self.dlg.checkBox_Data4.isChecked():
            if self.folderPath4 == '':
                QMessageBox.critical(None, "Error", "Select a valid reference dataset")
                return
            else:
                prm['file']['input_cfgfiles(3)'] = str(self.folderPath4[0])

        if self.dlg.checkBox_Data5.isChecked():
            if self.folderPath5 == '':
                QMessageBox.critical(None, "Error", "Select a valid reference dataset")
                return
            else:
                prm['file']['input_cfgfiles(4)'] = str(self.folderPath2[0])

        prm['file']['output_pdf'] = str(self.dlg.textOutputPDF.text())

        prm.write(self.plugin_dir + '/benchmark.nml', force=True)

        bss.report_benchmark(self.plugin_dir + '/benchmark.nml', self.plugin_dir)

        if self.dlg.checkBox_NamelistOut.isChecked():
            shutil.copy(self.plugin_dir + '/benchmark.nml', self.dlg.textInput_NamelistOut.text())

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = "http://www.urban-climate.net/umep"
        webbrowser.open_new_tab(url)

