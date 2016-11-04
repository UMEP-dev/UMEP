# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MetdataProcessor
                                 A QGIS plugin
 Process metdata to be used in UMEP processor
                              -------------------
        begin                : 2015-06-06
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
from PyQt4.QtGui import *
# Initialize Qt resources from file resources.py
# import resources_rc
# Import the code for the dialog
from metdata_processor_dialog import MetdataProcessorDialog
import os.path
import numpy as np
import webbrowser
#import suewsdataprocessing_v4 as su


class MetdataProcessor:
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
            'MetdataProcessor_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = MetdataProcessorDialog()
        self.dlg.pushButtonImport.clicked.connect(self.import_file)
        self.dlg.pushButtonExport.clicked.connect(self.start_progress)
        self.dlg.helpButton.clicked.connect(self.help)
        self.fileDialog = QFileDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Metdata processor')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'MetdataProcessor')
        # self.toolbar.setObjectName(u'MetdataProcessor')

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
        return QCoreApplication.translate('MetdataProcessor', message)

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

        icon_path = ':/plugins/MetdataProcessor/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Metdata processor'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Metdata processor'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def import_file(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.dlg.pushButtonExport.setEnabled(True)
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textInput.setText(self.folderPath[0])
            headernum = self.dlg.spinBoxHeader.value()
            # delim = self.dlg.comboBox_sep.currentText()
            delimnum = self.dlg.comboBox_sep.currentIndex()
            if delimnum == 0:
                delim = ','
            elif delimnum == 1:
                delim = None  # space
            elif delimnum == 2:
                delim = '\t'
            elif delimnum == 3:
                delim = ';'
            elif delimnum == 4:
                delim = ':'

            # QMessageBox.information(None, "Metdata pre-processor", delim)

            f = open(self.folderPath[0])
            header = f.readline().split()

            for i in range(0, header.__len__()):
                self.dlg.comboBox_yyyy.addItem(header[i])
                self.dlg.comboBox_doy.addItem(header[i])
                self.dlg.comboBox_month.addItem(header[i])
                self.dlg.comboBox_dom.addItem(header[i])
                self.dlg.comboBox_dectime.addItem(header[i])
                self.dlg.comboBox_hour.addItem(header[i])
                self.dlg.comboBox_minute.addItem(header[i])
                self.dlg.comboBox_RH.addItem(header[i])
                self.dlg.comboBox_Tair.addItem(header[i])
                self.dlg.comboBox_Wd.addItem(header[i])
                self.dlg.comboBox_Wuh.addItem(header[i])
                self.dlg.comboBox_fcld.addItem(header[i])
                self.dlg.comboBox_kdiff.addItem(header[i])
                self.dlg.comboBox_kdir.addItem(header[i])
                self.dlg.comboBox_kdown.addItem(header[i])
                self.dlg.comboBox_lai.addItem(header[i])
                self.dlg.comboBox_ldown.addItem(header[i])
                self.dlg.comboBox_pres.addItem(header[i])
                self.dlg.comboBox_qe.addItem(header[i])
                self.dlg.comboBox_qf.addItem(header[i])
                self.dlg.comboBox_qh.addItem(header[i])
                self.dlg.comboBox_qn.addItem(header[i])
                self.dlg.comboBox_qs.addItem(header[i])
                self.dlg.comboBox_rain.addItem(header[i])
                self.dlg.comboBox_snow.addItem(header[i])
                self.dlg.comboBox_ws.addItem(header[i])
                self.dlg.comboBox_xsmd.addItem(header[i])
            # self.data = np.loadtxt(self.folderPath[0], skiprows=headernum, delimiter=delim)
            try:
                self.data = np.loadtxt(self.folderPath[0], skiprows=headernum, delimiter=delim)
            except:
                QMessageBox.critical(None, "Import Error", "Check number of header lines, delimiter format and if nodata are present")
                return

    def start_progress(self):

        outputfile = self.fileDialog.getSaveFileName(None, "Save File As:", None, "Text Files (*.txt)")

        if not outputfile:
            QMessageBox.critical(None, "Error", "An output text file (.txt) must be specified")
            return

        self.dlg.progressBar.setRange(0, 10)

        rownum = self.data.shape[0]
        met_old = self.data
        met_new = np.zeros((met_old.shape[0], 24)) - 999

        if self.dlg.checkBoxYear.isChecked():
            yyyy_col = self.dlg.comboBox_yyyy.currentIndex()
            met_new[:, 0] = met_old[:, yyyy_col]
        else:
            met_new[:, 0] = self.dlg.spinBoxYear.value()

        self.dlg.progressBar.setValue(1)

        if self.dlg.checkBoxDOY.isChecked():
            doy_col = self.dlg.comboBox_doy.currentIndex()
            met_new[:, 1] = met_old[:, doy_col]
        else:
            mm = met_old[:, self.dlg.comboBox_month.currentIndex()]
            dd = met_old[:, self.dlg.comboBox_dom.currentIndex()]
            for i in range(0, rownum):
                yy = int(met_new[i, 0])
                if (yy % 4) == 0:
                    if (yy % 100) == 0:
                        if (yy % 400) == 0:
                            leapyear = 1
                        else:
                            leapyear = 0
                    else:
                        leapyear = 1
                else:
                    leapyear = 0
                if leapyear == 1:
                    dayspermonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                else:
                    dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                met_new[i, 1] = sum(dayspermonth[0:int(mm[i] - 1)]) + dd[i]

        self.dlg.progressBar.setValue(2)

        if self.dlg.checkBoxDectime.isChecked():
            dectime_col = self.dlg.comboBox_dectime.currentIndex()
            dechour = (met_old[:, dectime_col] - np.floor(met_old[:, dectime_col])) * 24
            met_new[:, 2] = dechour
            minute = np.round((dechour - np.floor(dechour)) * 60)
            minute[(minute == 60)] = 0
            met_new[:, 3] = minute
        else:
            met_new[:, 2] = met_old[:, self.dlg.comboBox_hour.currentIndex()]
            met_new[:, 3] = met_old[:, self.dlg.comboBox_minute.currentIndex()]

        self.dlg.progressBar.setValue(3)

        # Met variables
        if self.dlg.checkBox_kdown.isChecked():
            met_new[:, 14] = met_old[:, self.dlg.comboBox_kdown.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 14] < 0.0) | (met_new[:, 14] > 1200.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Kdown - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 14] = -999.0

        if self.dlg.checkBox_ws.isChecked():
            met_new[:, 9] = met_old[:, self.dlg.comboBox_ws.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 9] < 0.0) | (met_new[:, 9] > 60.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Wind speed - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 9] = -999.0

        if self.dlg.checkBox_Tair.isChecked():
            met_new[:, 11] = met_old[:, self.dlg.comboBox_Tair.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 11] < -30.0) | (met_new[:, 11] > 55.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Air temperature - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 11] = -999.0

        self.dlg.progressBar.setValue(4)

        if self.dlg.checkBox_RH.isChecked():
            met_new[:, 10] = met_old[:, self.dlg.comboBox_RH.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 10] < 0.00) | (met_new[:, 10] > 100.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Relative humidity - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 10] = -999.0

        if self.dlg.checkBox_pres.isChecked():
            met_new[:, 12] = met_old[:, self.dlg.comboBox_pres.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 12] < 70.0) | (met_new[:, 12] > 107.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Pressure - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 12] = -999.0

        if self.dlg.checkBox_rain.isChecked():
            met_new[:, 13] = met_old[:, self.dlg.comboBox_rain.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 13] < 0.0) | (met_new[:, 13] > 30.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Rain - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 13] = -999.0

        self.dlg.progressBar.setValue(5)

        if self.dlg.checkBox_snow.isChecked():
            met_new[:, 15] = met_old[:, self.dlg.comboBox_snow.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 15] < 0.0) | (met_new[:, 15] > 300.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Snow - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 15] = -999.0

        if self.dlg.checkBox_ldown.isChecked():
            met_new[:, 16] = met_old[:, self.dlg.comboBox_ldown.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 16] < 100.0) | (met_new[:, 16] > 600.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Ldown - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 16] = -999.0

        if self.dlg.checkBox_fcld.isChecked():
            met_new[:, 17] = met_old[:, self.dlg.comboBox_fcld.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 17] < 0.0) | (met_new[:, 17] > 1.01))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Fraction of cloud - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 17] = -999.0

        self.dlg.progressBar.setValue(6)

        if self.dlg.checkBox_Wuh.isChecked():
            met_new[:, 18] = met_old[:, self.dlg.comboBox_Wuh.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 18] < 0.0) | (met_new[:, 18] > 10.01))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "External water use - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 18] = -999.0

        if self.dlg.checkBox_xcmd.isChecked():
            met_new[:, 19] = met_old[:, self.dlg.comboBox_xcmd.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 19] < 0.01) | (met_new[:, 19] > 0.5))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Soil moisture - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
                    return
        else:
            met_new[:, 19] = -999.0

        if self.dlg.checkBox_lai.isChecked():
            met_new[:, 20] = met_old[:, self.dlg.comboBox_lai.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 20] < 0.0) | (met_new[:, 20] > 15.01))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Leaf area index - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 20] = -999.0

        self.dlg.progressBar.setValue(7)

        if self.dlg.checkBox_kdiff.isChecked():
            met_new[:, 21] = met_old[:, self.dlg.comboBox_kdiff.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 21] < 0.0) | (met_new[:, 21] > 600.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Diffuse shortwave radiation - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 21] = -999.0

        if self.dlg.checkBox_kdir.isChecked():
            met_new[:, 22] = met_old[:, self.dlg.comboBox_kdir.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 22] < 0.0) | (met_new[:, 22] > 1200.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Direct shortwave radiation - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 22] = -999.0

        if self.dlg.checkBox_Wd.isChecked():
            met_new[:, 23] = met_old[:, self.dlg.comboBox_Wd.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 23] < 0.0) | (met_new[:, 23] > 360.01))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Wind directions - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 23] = -999.0

        self.dlg.progressBar.setValue(8)

        if self.dlg.checkBox_qn.isChecked():
            met_new[:, 4] = met_old[:, self.dlg.comboBox_qn.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 4] < -200.0) | (met_new[:, 4] > 800.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Net radiation - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 4] = -999.0

        if self.dlg.checkBox_qh.isChecked():
            met_new[:, 5] = met_old[:, self.dlg.comboBox_qh.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 5] < -200.0) | (met_new[:, 5] > 750.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Sensible heat flux - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 5] = -999.0

        if self.dlg.checkBox_qe.isChecked():
            met_new[:, 6] = met_old[:, self.dlg.comboBox_qe.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 6] < -100.0) | (met_new[:, 6] > 650.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Latent heat flux - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 6] = -999.0

        self.dlg.progressBar.setValue(9)

        if self.dlg.checkBox_qs.isChecked():
            met_new[:, 7] = met_old[:, self.dlg.comboBox_qs.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 7] < -200.0) | (met_new[:, 7] > 650.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Storage heat flux - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 7] = -999.0

        if self.dlg.checkBox_qf.isChecked():
            met_new[:, 8] = met_old[:, self.dlg.comboBox_qf.currentIndex()]
            if self.dlg.checkBoxQuality.isChecked():
                testwhere = np.where((met_new[:, 8] < 0.0) | (met_new[:, 8] > 1500.0))
                if testwhere[0].__len__() > 0:
                    QMessageBox.critical(None, "Value error", "Anthropogenic heat flux - beyond what is expected at line:"
                                                              " \n" + str(testwhere[0] + 1))
        else:
            met_new[:, 8] = -999.0

        # if self.dlg.checkBoxSOLWEIG.isChecked(): #NOT READY
        #     # Moving one hour
        #     Ta[1:np.size(Ta)] = Ta[0:np.size(Ta) - 1]
        #     Ta[0] = Ta[1]
        #     RH[1:np.size(RH)] = RH[0:np.size(RH) - 1]
        #     RH[0] = RH[1]
        #     G[1:np.size(G)] = G[0:np.size(G) - 1]
        #     G[0] = G[1]
        #     D[1:np.size(D)] = D[0:np.size(D) - 1]
        #     D[0] = D[1]
        #     I[1:np.size(I)] = I[0:np.size(I) - 1]
        #     I[0] = I[1]
        #     Ws[1:np.size(Ws)] = Ws[0:np.size(Ws) - 1]
        #     Ws[0] = Ws[1]
                                                                  #
        header = '%iy  id  it imin   Q*      QH      QE      Qs      Qf    Wind    RH     Td     press   rain ' \
                 '   Kdn    snow    ldown   fcld    wuh     xsmd    lai_hr  Kdiff   Kdir    Wd'
        # #Save as text files
        # numformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f ' \
        #             '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f'
        numformat = '%d %d %d %d %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f ' \
                    '%.2f %.2f %.2f %.2f %.2f %.2f %.2f'
        np.savetxt(outputfile, met_new, fmt=numformat, header=header, comments='')

        self.dlg.progressBar.setValue(10)

        QMessageBox.information(None, "Metdata pre-processor", "Input data to UMEP processor generated")

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = 'http://www.urban-climate.net/umep/UMEP_Manual#Pre-Processor:_Meteorological_Data:_MetPreprocessor'
        webbrowser.open_new_tab(url)
