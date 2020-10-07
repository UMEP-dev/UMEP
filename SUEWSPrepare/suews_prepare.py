# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SUEWSPrepare
                                 A QGIS plugin
 This pluin prepares input data to SUEWS v2015a
                              -------------------
        begin                : 2015-10-25
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
from builtins import next
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QThread, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QFileDialog
from qgis.PyQt.QtGui import QIcon, QImage, QPixmap
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from .suews_prepare_dialog import SUEWSPrepareDialog
from .tabs.template_widget import TemplateWidget
from .tabs.template_tab import TemplateTab
from .tabs.main_tab import MainTab
from .tabs.changeDialog import ChangeDialog
from .tabs.photodialog import PhotoDialog
import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__) + '/Modules')
from .Modules.xlutils.copy import copy
from .prepare_worker import Worker
import urllib.request, urllib.error, urllib.parse
import fileinput
import itertools
import webbrowser
import os
import shutil

try:
    import xlrd
except ImportError:
    QMessageBox.critical(None, 'Missing Python library', 'This plugin requires the xlrd package to be installed. '
                                                         'Please consult the UMEP manual for further information')
    pass


class SUEWSPrepare(object):
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
            'SUEWSPrepare_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.output_file_list = []

        self.input_path = self.plugin_dir + '/Input/'
        self.output_path = self.plugin_dir[:-12] + 'suewsmodel/'
        self.output_heat = 'SUEWS_AnthropogenicEmission.txt' #'SUEWS_AnthropogenicHeat.txt'
        self.output_file_list.append(self.output_heat)
        self.output_cond = 'SUEWS_Conductance.txt'
        self.output_file_list.append(self.output_cond)
        self.output_irr = 'SUEWS_Irrigation.txt'
        self.output_file_list.append(self.output_irr)
        self.output_nonveg = 'SUEWS_NonVeg.txt'
        self.output_file_list.append(self.output_nonveg)
        self.output_OHMcoeff = 'SUEWS_OHMCoefficients.txt'
        self.output_file_list.append(self.output_OHMcoeff)
        self.output_prof = 'SUEWS_Profiles.txt'
        self.output_file_list.append(self.output_prof)
        self.output_snow = 'SUEWS_Snow.txt'
        self.output_file_list.append(self.output_snow)
        self.output_soil = 'SUEWS_Soil.txt'
        self.output_file_list.append(self.output_soil)
        self.output_water = 'SUEWS_Water.txt'
        self.output_file_list.append(self.output_water)
        self.output_veg = 'SUEWS_Veg.txt'
        self.output_file_list.append(self.output_veg)
        self.output_watergrid = 'SUEWS_WithinGridWaterDist.txt'
        self.output_file_list.append(self.output_watergrid)
        self.output_ESTMcoeff = 'SUEWS_ESTMCoefficients.txt'
        self.output_file_list.append(self.output_ESTMcoeff)
        self.output_biogen = 'SUEWS_BiogenCO2.txt'
        self.output_file_list.append(self.output_biogen)
        self.output_dir = None
        self.LCFfile_path = None
        self.IMPfile_path = None
        self.IMPvegfile_path = None
        self.Metfile_path = None
        self.land_use_file_path = None
        self.LCF_from_file = True
        self.IMP_from_file = True
        self.IMPveg_from_file = True
        self.wall_area_info = False
        self.land_use_from_file = False

        # Copy basefiles from sample_run
        self.supylib = sys.modules["supy"].__path__[0]
        if not (os.path.isdir(self.output_path + '/Input')):
            os.mkdir(self.output_path + '/Input')
        basefiles = ['ESTMinput.nml', 'SUEWS_AnthropogenicEmission.txt', 'SUEWS_BiogenCO2.txt', 'SUEWS_Conductance.txt', 'SUEWS_ESTMCoefficients.txt', 'SUEWS_Irrigation.txt', 
        'SUEWS_NonVeg.txt', 'SUEWS_OHMCoefficients.txt', 'SUEWS_Profiles.txt', 'SUEWS_Snow.txt', 'SUEWS_Soil.txt', 'SUEWS_Water.txt', 'SUEWS_Veg.txt', 'SUEWS_WithinGridWaterDist.txt']
        for i in range(0, basefiles.__len__()):
            if not (os.path.isfile(self.output_path + '/Input/' + basefiles[i])):
                try:
                    shutil.copy(self.supylib + '/sample_run/Input/' + basefiles[i], self.output_path + '/Input/' + basefiles[i])
                except:
                    os.remove(self.output_path + '/Input/' + basefiles[i])
                    shutil.copy(self.supylib + '/sample_run/Input/' + basefiles[i], self.output_path + '/Input/' + basefiles[i])

        self.file_path = self.plugin_dir + '/Input/SUEWS_SiteLibrary.xls'
        self.init_path = self.plugin_dir + '/Input/SUEWS_init.xlsx'
        self.header_file_path = self.plugin_dir + '/Input/SUEWS_SiteSelect.xlsx'
        self.line_list = []
        self.widget_list = []
        self.data = xlrd.open_workbook(self.file_path)
        self.init_data = xlrd.open_workbook(self.init_path)
        self.header_data = xlrd.open_workbook(self.header_file_path)
        self.isEditable = False
        self.heatsheet = self.data.sheet_by_name("SUEWS_AnthropogenicEmission") #SUEWS_AnthropogenicHeat")
        self.condsheet = self.data.sheet_by_name("SUEWS_Conductance")
        self.irrsheet = self.data.sheet_by_name("SUEWS_Irrigation")
        self.impsheet = self.data.sheet_by_name("SUEWS_NonVeg")
        self.OHMcoefsheet = self.data.sheet_by_name("SUEWS_OHMCoefficients")
        self.profsheet = self.data.sheet_by_name("SUEWS_Profiles")
        self.snowsheet = self.data.sheet_by_name("SUEWS_Snow")
        self.soilsheet = self.data.sheet_by_name("SUEWS_Soil")
        self.watersheet = self.data.sheet_by_name("SUEWS_Water")
        self.vegsheet = self.data.sheet_by_name("SUEWS_Veg")
        self.waterdistsheet = self.data.sheet_by_name("SUEWS_WithinGridWaterDist")

        self.header_sheet = self.header_data.sheet_by_name("SUEWS_SiteSelect")

        self.dlg = SUEWSPrepareDialog()

        self.dlg.helpButton.clicked.connect(self.help)

        self.dlg.outputButton.clicked.connect(self.set_output_folder)
        self.dlg.runButton.clicked.connect(self.generate)

        self.outputDialog = QFileDialog()
        self.outputDialog.setFileMode(QFileDialog.Directory)
        self.outputDialog.setOption(QFileDialog.ShowDirsOnly, True)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(QFileDialog.ExistingFile)

        self.change_dialog = ChangeDialog()

        self.photo_dialog = PhotoDialog()

        self.layerComboManagerPolygrid = None
        self.layerComboManagerPolyField = None
        self.fieldgen = None
        self.LCF_Paved = None
        self.LCF_Buildings = None
        self.LCF_Evergreen = None
        self.LCF_Decidious = None
        self.LCF_Grass = None
        self.LCF_Baresoil = None
        self.LCF_Water = None
        self.pop_density = None
        self.pop_density_day = None
        self.IMP_mean_height = None
        self.IMP_z0 = None
        self.IMP_zd = None
        self.IMP_fai = None
        self.IMPveg_mean_height_dec = None
        self.IMPveg_mean_height_eve = None
        self.IMPveg_fai_dec = None
        self.IMPveg_fai_eve = None
        self.wall_area = None
        self.daypop = 0
        self.start_DLS = 85
        self.end_DLS = 302
        self.day_since_rain = 0
        self.leaf_cycle = 0
        self.soil_moisture = 100
        self.utc = 0
        self.file_code = ''
        self.steps = 0

        # Declare instance attributes
        self.actions = []

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SUEWSPrepare', message)

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
        icon_path = ':/plugins/SUEWSPrepare/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'SUEWS Prepare'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SUEWS Prepare'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def setup_tabs(self):
        self.dlg.tabWidget.clear()
        self.widget_list = []

        main_tab = MainTab()
        self.setup_maintab(main_tab)

        self.dlg.tabWidget.addTab(main_tab, "Main settings")
        sheet_names = self.init_data.sheet_names()

        for shidx in range(1, self.init_data.nsheets):
            sheet = self.init_data.sheet_by_index(shidx)
            title = sheet_names[shidx]
            self.setup_tab(title, sheet)

    def setup_tab(self, title, sheet):
        QgsMessageLog.logMessage("Setting up tab: " + str(title), level=Qgis.Critical)
        tab = TemplateTab()
        x = 0
        y = 0
        for row in range(0, sheet.nrows):
            values = sheet.row_values(row)
            input_sheet = self.data.sheet_by_name(str(values[0]))
            file_path = str(values[1])
            widget_title = str(values[2])
            if values[3] is None:
                code = None
            elif values[3] == "":
                code = None
            else:
                try:
                    code = int(values[3])
                except ValueError as e:
                    QgsMessageLog.logMessage("Value error for plugin titled " + title + " for input code: " + str(e), level=Qgis.Critical)
                    code = None
            if values[4] is None:
                default_combo = None
            elif values[4] == "":
                default_combo = None
            else:
                try:
                    default_combo = int(values[4])
                except ValueError as e:
                    QgsMessageLog.logMessage("Value error for plugin titled " + title + " for default combo: " + str(e), level=Qgis.Critical)
                    default_combo = None
            if values[5] is None:
                sitelist_pos = None
            elif values[5] == "":
                sitelist_pos = None
            else:
                try:
                    sitelist_pos = int(values[5])
                except ValueError as e:
                    QgsMessageLog.logMessage("Value error for plugin titled " + title + " for site list position: " + str(e), level=Qgis.Critical)
                    sitelist_pos = None

            widget = TemplateWidget(input_sheet, file_path, widget_title, code, default_combo, sitelist_pos)
            self.widget_list.append(widget)
            widget.setup_widget()
            widget.make_edits_signal.connect(self.make_edits)
            widget.edit_mode_signal.connect(self.edit_mode)
            widget.cancel_edits_signal.connect(self.cancel_edits)
            widget.checkbox_signal.connect(lambda: self.fill_combobox(widget))

            self.tab_combo = QgsFieldComboBox(widget.comboBox_uniquecodes)
            self.tab_combo.setFilters(QgsFieldProxyModel.Numeric)
            self.layerComboManagerPolygrid.layerChanged.connect(self.tab_combo.setLayer)

            tab.Layout.addWidget(widget, x, y)

            if y < 1:
                y += 1
            else:
                x += 1
                y = 0

        self.dlg.tabWidget.addTab(tab, str(title))

    def setup_maintab(self, widget):

        self.LCF_from_file = True
        self.IMP_from_file = True
        self.IMPveg_from_file = True
        widget.LCF_Frame.hide()
        widget.IMP_Frame.hide()
        widget.IMPveg_Frame.hide()

        widget.LCF_checkBox.stateChanged.connect(lambda: self.hide_show_LCF(widget))
        widget.IMP_checkBox.stateChanged.connect(lambda: self.hide_show_IMP(widget))
        widget.IMPveg_checkBox.stateChanged.connect(lambda: self.hide_show_IMPveg(widget))
        widget.LUF_checkBox.stateChanged.connect(lambda: self.LUF_file(widget))
        widget.WallArea_checkBox.stateChanged.connect(lambda: self.enable_wall_area(widget))

        widget.checkBox_day.stateChanged.connect(lambda: self.popdaystate(widget))

        self.layerComboManagerPolygrid = QgsMapLayerComboBox(widget.widgetPolygonLayer)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyField = QgsFieldComboBox(widget.widgetPolyField)
        self.layerComboManagerPolyField.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.layerComboManagerPolyField.setLayer)

        # self.pop_density = FieldCombo(widget.comboBox_popdens, self.fieldgen, initField="")
        self.pop_density = QgsFieldComboBox(widget.widgetPop)
        self.pop_density.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.pop_density.setLayer)

        self.pop_density_day = QgsFieldComboBox(widget.widgetPopDay)
        self.pop_density_day.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.pop_density_day.setLayer)

        # self.wall_area = FieldCombo(widget.comboBox_wallArea, self.fieldgen, initField="")
        self.wall_area = QgsFieldComboBox(widget.widgetWallArea)
        self.wall_area.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.wall_area.setLayer)

        widget.pushButtonImportLCF.clicked.connect(lambda: self.set_LCFfile_path(widget))
        widget.pushButtonImportIMPVeg.clicked.connect(lambda: self.set_IMPvegfile_path(widget))

        widget.pushButtonImportIMPVeg_eve.clicked.connect(lambda: self.set_IMPvegfile_path_eve(widget))
        widget.pushButtonImportIMPVeg_dec.clicked.connect(lambda: self.set_IMPvegfile_path_dec(widget))

        widget.pushButtonImportIMPBuild.clicked.connect(lambda: self.set_IMPfile_path(widget))
        widget.pushButtonImportMet.clicked.connect(lambda: self.set_metfile_path(widget))
        widget.pushButtonImportLUF.clicked.connect(lambda: self.set_LUFfile_path(widget))

        widget.spinBoxStartDLS.valueChanged.connect(lambda: self.start_DLS_changed(widget.spinBoxStartDLS.value()))
        widget.spinBoxEndDLS.valueChanged.connect(lambda: self.end_DLS_changed(widget.spinBoxEndDLS.value()))

        widget.spinBoxSoilMoisture.valueChanged.connect(lambda: self.soil_moisture_changed(widget.spinBoxSoilMoisture.
                                                                                           value()))
        widget.comboBoxLeafCycle.currentIndexChanged.connect(lambda: self.leaf_cycle_changed(widget.comboBoxLeafCycle.
                                                                                             currentIndex()))
        widget.fileCodeLineEdit.textChanged.connect(lambda: self.file_code_changed(widget.fileCodeLineEdit.text()))
        widget.lineEditUTC.textChanged.connect(lambda: self.utc_changed(widget.lineEditUTC.text()))

    def soil_moisture_changed(self, value):
        self.soil_moisture = value

    def utc_changed(self, index):
        self.utc = index

    def leaf_cycle_changed(self, index):
        self.leaf_cycle = index

    def file_code_changed(self, code):
        self.file_code = code

    def hide_show_LCF(self, widget):
        if widget.LCF_checkBox.isChecked():
            self.LCF_from_file = False
            widget.LCF_Frame.show()
            widget.pushButtonImportLCF.hide()
            widget.textInputLCFData.hide()
        else:
            self.LCF_from_file = True
            widget.LCF_Frame.hide()
            widget.pushButtonImportLCF.show()
            widget.textInputLCFData.show()

    def hide_show_IMP(self, widget):
        if widget.IMP_checkBox.isChecked():
            self.IMP_from_file = False
            widget.IMP_Frame.show()
            widget.pushButtonImportIMPBuild.hide()
            widget.textInputIMPData.hide()
        else:
            self.IMP_from_file = True
            widget.IMP_Frame.hide()
            widget.pushButtonImportIMPBuild.show()
            widget.textInputIMPData.show()

    def hide_show_IMPveg(self, widget):
        if widget.IMPveg_checkBox.isChecked():
            self.IMPveg_from_file = False
            widget.IMPveg_Frame.show()
            widget.pushButtonImportIMPVeg.hide()
            widget.textInputIMPVegData.hide()
            widget.checkBox_twovegfiles.hide()
            widget.pushButtonImportIMPVeg_eve.hide()
            widget.pushButtonImportIMPVeg_dec.hide()
            widget.textInputIMPEveData.hide()
            widget.textInputIMPDecData.hide()
        else:
            self.IMPveg_from_file = True
            widget.IMPveg_Frame.hide()
            widget.pushButtonImportIMPVeg.show()
            widget.textInputIMPVegData.show()
            widget.checkBox_twovegfiles.show()
            widget.pushButtonImportIMPVeg_eve.show()
            widget.pushButtonImportIMPVeg_dec.show()
            widget.textInputIMPEveData.show()
            widget.textInputIMPDecData.show()

    def LUF_file(self, widget):
        if widget.LUF_checkBox.isChecked():
            self.land_use_from_file = True
            widget.pushButtonImportLUF.setEnabled(1)
        else:
            self.land_use_from_file = False
            widget.pushButtonImportLUF.setEnabled(0)

    def popdaystate(self, widget):
        if widget.checkBox_day.isChecked():
            self.daypop = 1
        else:
            self.daypop = 0

    def enable_wall_area(self, widget):
        if widget.WallArea_checkBox.isChecked():
            self.wall_area_info = True
            widget.widgetWallArea.setEnabled(1)
        else:
            self.wall_area_info = False
            widget.widgetWallArea.setEnabled(0)

    def setup_widget(self, widget, sheet, outputfile, title, code=None, default_combo=None):
        widget.tab_name.setText(title)
        lineedit_list = self.setup_dynamically(widget, sheet)
        if code is None:
            if default_combo is None:
                self.setup_combo(widget, sheet)
            else:
                self.setup_combo(widget, sheet, None, default_combo)
        else:
            if default_combo is None:
                self.setup_combo(widget, sheet, code)
            else:
                self.setup_combo(widget, sheet, code, default_combo)
        self.setup_values(widget, sheet, lineedit_list)
        widget.comboBox.currentIndexChanged.connect(lambda: self.setup_values(widget, sheet, lineedit_list))
        if code is None:
            self.setup_buttons(widget, outputfile, sheet, lineedit_list)
        else:
            self.setup_buttons(widget, outputfile, sheet, lineedit_list, code)

    def setup_combo(self, widget, sheet, code=None, default_combo=None):
        if widget.comboBox.count() > 0:
            widget.comboBox.clear()
        for row in range(3, sheet.nrows):
            val = sheet.cell_value(row, 0)
            if int(val) == -9:
                break
            else:
                if code is None:
                    widget.comboBox.addItem(str(int(val)))
                else:
                    if code == int(sheet.cell_value(row, sheet.ncols-1)):
                        widget.comboBox.addItem(str(int(val)))
                    else:
                        pass
        if default_combo is not None:
            index = widget.comboBox.findText(str(default_combo))
            widget.comboBox.setCurrentIndex(index)

    def setup_values(self, widget, sheet, lineedit_list):
        try:
            code = widget.comboBox.currentText()
            code = int(code)
            for row in range(3, sheet.nrows):
                self.setup_image(widget, sheet, row)
                val = sheet.cell_value(row, 0)
                val = int(val)
                if val == code:
                    values = sheet.row_values(row, 1)
                    for x in range(0, len(values)):
                        if values[x] == "!":
                            explanation = ""
                            for y in range(len(values)-4, 0, -1):
                                if values[y] == "!":
                                    break
                                else:
                                    explanation += str(sheet.cell_value(1, y+1))
                                    explanation += ": "
                                    explanation += str(values[y])
                                    explanation += "\n"
                            widget.exp_label.setText(explanation)
                            break
                        lineEdit = lineedit_list[x]
                        lineEdit.setText(str(values[x]))
                    break
        except ValueError as e:
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
            pass

    def setup_buttons(self, widget, outputfile, sheet, lineedit_list, code=None):
        widget.editButton.clicked.connect(lambda: self.edit_mode(widget, lineedit_list))
        widget.cancelButton.clicked.connect(lambda: self.cancel_edits(widget, lineedit_list))
        if code is None:
            widget.changeButton.clicked.connect(lambda: self.make_edits(widget, outputfile, sheet, lineedit_list))
        else:
            widget.changeButton.clicked.connect(lambda: self.make_edits(widget, outputfile, sheet, lineedit_list, code))

    def fill_combobox(self, widget):
        poly = self.layerComboManagerPolygrid.currentLayer()
        if poly is None:
            QMessageBox.information(None, "Error", "No polygon grid added in main settings yet")
            widget.checkBox.setCheckState(0)
        else:
            widget.checkBox.setCheckState(1)
            # FieldCombo(widget.comboBox_uniquecodes, self.fieldgen, initField="")

    def edit_mode(self):
        for index in range(0, self.dlg.tabWidget.count()):
            if index == self.dlg.tabWidget.currentIndex():
                pass
            else:
                self.dlg.tabWidget.setTabEnabled(index, False)
        self.isEditable = True

    def edit_mode_outdated(self, widget, lineedit_list):
        for index in range(0, self.dlg.tabWidget.count()):
            if index == self.dlg.tabWidget.currentIndex():
                pass
            else:
                self.dlg.tabWidget.setTabEnabled(index, False)
        for x in range(0, len(lineedit_list)):
            lineedit_list[x].setEnabled(1)
        widget.editButton.setEnabled(0)
        widget.changeButton.setEnabled(1)
        widget.cancelButton.setEnabled(1)
        self.isEditable = True

    def cancel_edits(self):
        for index in range(0, self.dlg.tabWidget.count()):
            if index == self.dlg.tabWidget.currentIndex():
                pass
            else:
                self.dlg.tabWidget.setTabEnabled(index, True)
        self.isEditable = False

    def cancel_edits_outdated(self, widget, lineedit_list):
        for index in range(0, self.dlg.tabWidget.count()):
            if index == self.dlg.tabWidget.currentIndex():
                pass
            else:
                self.dlg.tabWidget.setTabEnabled(index, True)
        for x in range(0, len(lineedit_list)):
            lineedit_list[x].setEnabled(0)
        widget.editButton.setEnabled(1)
        widget.changeButton.setEnabled(0)
        widget.cancelButton.setEnabled(0)
        self.isEditable = False

    def make_edits(self, outputfile, sheet, lineedit_list, code=None):

        if code is None:
            self.edit_file(outputfile, sheet, lineedit_list)
        else:
            self.edit_file(outputfile, sheet, lineedit_list, code)

        self.update_sheets()

        current_index = self.dlg.tabWidget.currentIndex()
        self.setup_tabs()
        self.dlg.tabWidget.setCurrentIndex(current_index)

        for index in range(0, self.dlg.tabWidget.count()):
            if index == self.dlg.tabWidget.currentIndex():
                pass
            else:
                self.dlg.tabWidget.setTabEnabled(index, True)

        self.isEditable = False
        QMessageBox.information(None, "Complete", "Your entry has been added")

    def edit_file(self, outputfile, sheet, lineedit_list, code=None):
        try:
            wb = copy(self.data)
            wrote_line = False
            wrote_excel = False
            file_path = self.output_path + "Input/" + outputfile
            str_list = []

            self.setup_change_dialog(sheet)

            self.change_dialog.show()

            result = self.change_dialog.exec_()

            if result:
                start_code = self.line_list[0].text()

                if start_code.isdigit() is False:
                    QMessageBox.critical(None, "Error", "Identification code needs to be an integer")
                    self.clear_layout()
                else:
                    str_list.append(start_code)

                    if os.path.isfile(file_path):
                        with open(file_path, 'r') as file:
                            line = file.readline()
                            line_split = line.split()
                            next(file)
                            for x in range(0, len(lineedit_list)):
                                value = lineedit_list[x].text()
                                str_list.append(str(value))
                            str_list.append("!")
                            file.close()
                        for x in range(len(self.line_list)-1, 0, -1):
                            str_list.append(self.line_list[x].text())
                        for line in fileinput.input(file_path, inplace=1):
                            if line.startswith('-9'):
                                if wrote_line is False:
                                    string_to_print = ''
                                    for element in str_list:
                                        string_to_print += element + '\t'
                                    # fix_print_with_import
                                    print(string_to_print)
                                    # fix_print_with_import
                                    print(line, end=' ')
                                    wrote_line = True
                                else:
                                    # fix_print_with_import
                                    print(line, end=' ')
                            else:
                                # fix_print_with_import
                                print(line, end=' ')
                        photo = QMessageBox.question(None, "Photo",
                                                     "Would you like to add a url to a suitable photo of the area?",
                                                     QMessageBox.Yes | QMessageBox.No)
                        if photo == QMessageBox.Yes:
                            self.photo_dialog.show()
                            result = self.photo_dialog.exec_()
                            if result:
                                try:
                                    url = self.photo_dialog.lineEdit.text()
                                    QgsMessageLog.logMessage("URL: " + str(url), level=Qgis.Critical)
                                    req = urllib.request.Request(str(url))
                                    try:
                                        resp = urllib.request.urlopen(req)
                                    except urllib.error.HTTPError as e:
                                        QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                                        QMessageBox.information(None, "Error", "Couldn't reach url")
                                        str_list.append('')
                                    except urllib.error.URLError as e:
                                        QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                                        QMessageBox.information(None, "Error", "Couldn't reach url")
                                        str_list.append('')
                                    else:
                                        str_list.append(str(url))
                                except ValueError as e:
                                    QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                                    QMessageBox.information(None, "Error", "Couldn't reach url")
                                    str_list.append('')
                            else:
                                str_list.append('')
                        else:
                            str_list.append('')

                        if code is None:
                            str_list.append("not used")
                        else:
                            str_list.append('not used')
                            str_list.append(code)

                        for x in range(3, sheet.nrows):
                            if wrote_excel is False:
                                val = sheet.cell_value(x, 0)
                                if int(val) == -9:
                                    write_sheet = self.get_sheet_by_name(wb, sheet.name)
                                    for y in range(0, len(str_list)):
                                        try:
                                            int(str_list[y])
                                            write_sheet.write(x, y, int(str_list[y]))
                                        except ValueError as e:
                                            try:
                                                float(str_list[y])
                                                write_sheet.write(x, y, float(str_list[y]))
                                            except ValueError as e:
                                                write_sheet.write(x, y, str_list[y])
                                    write_sheet.write(x+1, 0, -9)
                                    write_sheet.write(x+2, 0, -9)
                                    wb.save(self.file_path)
                                    wrote_excel = True
                                else:
                                    pass
                            else:
                                break

                        self.clear_layout()
                    else:
                        QMessageBox.critical(None, "Error", "Could not find the file:" + outputfile)
                        self.clear_layout()
            else:
                self.clear_layout()
        except IOError as e:
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
            QMessageBox.critical(None, "Error", "Cannot access Excel file, might already be in use.")

    def setup_change_dialog(self, sheet):
        self.clear_layout()
        self.line_list = []
        label = QLabel("Identification code:")
        lineEdit = QLineEdit()
        lineEdit.textEdited.connect(lambda: self.code_validator(sheet))
        self.change_dialog.Layout2.addRow(label, lineEdit)
        self.line_list.append(lineEdit)
        values = sheet.row_values(3)
        for x in range(len(values)-4, 0, -1):
            if values[x] == "!":
                break
            else:
                title = str(sheet.cell_value(1, x)) + ":"
                label = QLabel(title)
                lineEdit = QLineEdit()
                self.change_dialog.Layout.addRow(label, lineEdit)
                self.line_list.append(lineEdit)

    def update_sheets(self):
        self.data = xlrd.open_workbook(self.file_path)
        self.heatsheet = self.data.sheet_by_name("SUEWS_AnthropogenicEmission") #SUEWS_AnthropogenicHeat")
        self.condsheet = self.data.sheet_by_name("SUEWS_Conductance")
        self.irrsheet = self.data.sheet_by_name("SUEWS_Irrigation")
        self.impsheet = self.data.sheet_by_name("SUEWS_NonVeg")
        self.OHMcoefsheet = self.data.sheet_by_name("SUEWS_OHMCoefficients")
        self.profsheet = self.data.sheet_by_name("SUEWS_Profiles")
        self.snowsheet = self.data.sheet_by_name("SUEWS_Snow")
        self.soilsheet = self.data.sheet_by_name("SUEWS_Soil")
        self.watersheet = self.data.sheet_by_name("SUEWS_Water")
        self.vegsheet = self.data.sheet_by_name("SUEWS_Veg")
        self.waterdistsheet = self.data.sheet_by_name("SUEWS_WithinGridWaterDist")

    def update_combobox(self, widget, sheet, code=None):
        self.update_sheets()
        sheet = self.data.sheet_by_name(sheet.name)
        if widget.comboBox.count() > 0:
            widget.comboBox.clear()
        for row in range(3, sheet.nrows):
            val = sheet.cell_value(row, 0)
            if int(val) == -9:
                break
            else:
                if code is None:
                    widget.comboBox.addItem(str(int(val)))
                else:
                    if code == int(sheet.cell_value(row, sheet.ncols-1)):
                        widget.comboBox.addItem(str(int(val)))
                    else:
                        pass

    def setup_image(self, widget, sheet, row):
        values = sheet.row_values(row, 0)
        url = values[len(values)-3]
        # fix_print_with_import
        print(url)
        if url == '':
            widget.Image.clear()
        else:
            req = urllib.request.Request(str(url))
            try:
                resp = urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    QgsMessageLog.logMessage("Image URL encountered a 404 problem", level=Qgis.Critical)
                    widget.Image.clear()
                else:
                    QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                    widget.Image.clear()
            except urllib.error.URLError as e:
                QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                widget.Image.clear()
            else:
                data = resp.read()
                image = QImage()
                image.loadFromData(data)

                widget.Image.setPixmap(QPixmap(image).scaledToWidth(139))

    def clear_layout(self):
        while self.change_dialog.Layout.count() > 0:
            item = self.change_dialog.Layout.takeAt(0)
            item.widget().deleteLater()
        while self.change_dialog.Layout2.count() > 0:
            item = self.change_dialog.Layout2.takeAt(0)
            item.widget().deleteLater()
        self.change_dialog.icon.clear()
        self.change_dialog.icon_description.clear()

    def code_validator(self, sheet):
        text = self.line_list[0].text()
        if text.isdigit():
            if self.is_duplicate(text, sheet):
                self.change_dialog.icon_description.setText("Code already exists")
                pixmap = QPixmap(self.plugin_dir + "/crossmark.png")
                self.change_dialog.icon.setPixmap(pixmap.scaledToHeight(12))
                self.change_dialog.icon.show()
                self.change_dialog.okButton.setEnabled(0)
            else:
                self.change_dialog.icon_description.setText("Acceptable")
                pixmap = QPixmap(self.plugin_dir + "/checkmark.png")
                self.change_dialog.icon.setPixmap(pixmap.scaledToHeight(12))
                self.change_dialog.icon.show()
                self.change_dialog.okButton.setEnabled(1)
        else:
            self.change_dialog.icon_description.setText("Must be integer")
            pixmap = QPixmap(self.plugin_dir + "/crossmark.png")
            self.change_dialog.icon.setPixmap(pixmap.scaledToHeight(12))
            self.change_dialog.icon.show()
            self.change_dialog.okButton.setEnabled(0)

    def is_duplicate(self, text, sheet):
        is_duplicate = False
        for x in range(3, sheet.nrows):
            value = sheet.cell_value(x, 0)
            if int(value) == -9:
                return is_duplicate
            else:
                if int(text) == int(value):
                    is_duplicate = True

    def setup_dynamically(self, widget, sheet):
        lineEdit_list = []
        Layout = QGridLayout()
        row = 0
        col = 0
        values = sheet.row_values(3, 1)
        for x in range(1, len(values)):
            if values[x-1] == "!":
                break
            else:
                cell = sheet.cell_value(1, x)
                tool_tip = sheet.cell_value(2, x)
                Layout2 = QVBoxLayout()
                label = QLabel(str(cell))
                lineedit = QLineEdit()
                lineedit.setToolTip(str(tool_tip))
                lineedit.setEnabled(0)
                Layout2.addWidget(label)
                Layout2.addWidget(lineedit)
                vert_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Maximum)
                Layout2.addItem(vert_spacer)
                Layout.addLayout(Layout2, row, col)
                lineEdit_list.append(lineedit)
                if x > 0:
                    if x % 5 == 0:
                        row += 1
                        col = 0
                        vert_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Maximum)
                        Layout.addItem(vert_spacer)
                    else:
                        col += 1
        widget.groupBox2.setLayout(Layout)
        return lineEdit_list

    def get_sheet_by_name(self, book, name):
        try:
            for idx in itertools.count():
                sheet = book.get_sheet(idx)
                if sheet.name == name:
                    return sheet
        except IndexError as e:
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
            return None

    def set_output_folder(self):
        self.outputDialog.open()
        result = self.outputDialog.exec_()
        if result == 1:
            self.output_dir = self.outputDialog.selectedFiles()
            self.dlg.textOutput.setText(self.output_dir[0])
            self.dlg.runButton.setEnabled(1)

    def set_LCFfile_path(self, widget):
        self.LCFfile_path = self.fileDialog.getOpenFileName()
        widget.textInputLCFData.setText(self.LCFfile_path[0])

    def set_IMPfile_path(self, widget):
        self.IMPfile_path = self.fileDialog.getOpenFileName()
        widget.textInputIMPData.setText(self.IMPfile_path[0])

    def set_IMPvegfile_path(self, widget):
        self.IMPvegfile_path = self.fileDialog.getOpenFileName()
        widget.textInputIMPVegData.setText(self.IMPvegfile_path[0])

    def set_IMPvegfile_path_dec(self, widget):
        self.IMPvegfile_path_dec = self.fileDialog.getOpenFileName()
        widget.textInputIMPDecData.setText(self.IMPvegfile_path_dec)

    def set_IMPvegfile_path_eve(self, widget):
        self.IMPvegfile_path_dec = self.fileDialog.getOpenFileName()
        widget.textInputIMPEveData.setText(self.IMPvegfile_path_eve[0])

    def set_metfile_path(self, widget):
        self.Metfile_path = self.fileDialog.getOpenFileName()
        widget.textInputMetData.setText(self.Metfile_path[0])

    def set_LUFfile_path(self, widget):
        self.land_use_file_path = self.fileDialog.getOpenFileName()
        widget.textInputLUFData.setText(self.land_use_file_path[0])

    def start_DLS_changed(self, value):
        self.start_DLS = value

    def end_DLS_changed(self, value):
        self.end_DLS = value

    def unload_widget(self):
        self.dlg.tabWidget.clear()

    def run(self):
        self.output_dir = None
        self.LCFfile_path = None
        self.IMPfile_path = None
        self.IMPvegfile_path = None
        self.IMPvegfile_path_dec = None
        self.IMPvegfile_path_eve = None
        self.checkBox_twovegfiles = None
        self.land_use_file_path = None
        self.dlg.textOutput.clear()
        self.setup_tabs()
        self.dlg.show()
        self.dlg.exec_()
        self.layerComboManagerPolygrid = None
        self.layerComboManagerPolyField = None
        self.fieldgen = None
        self.LCF_Paved = None
        self.LCF_Buildings = None
        self.LCF_Evergreen = None
        self.LCF_Decidious = None
        self.LCF_Grass = None
        self.LCF_Baresoil = None
        self.LCF_Water = None
        self.pop_density = None
        self.pop_density_day = None
        self.IMP_mean_height = None
        self.IMP_z0 = None
        self.IMP_zd = None
        self.IMP_fai = None
        self.IMPveg_mean_height_dec = None
        self.IMPveg_mean_height_eve = None
        self.IMPveg_fai_dec = None
        self.IMPveg_fai_eve = None
        self.wall_area = None
        # self.dlg.checkBox_day = None

    def generate(self):
        self.steps = 0
        if self.output_dir is None:
            QMessageBox.critical(self.dlg, "Error", "No output directory selected")
            return

        lines_to_write = []
        nbr_header = []
        nbr = 1
        header = []
        values = self.header_sheet.row_values(1)
        for value in values:
            if value is None:
                pass
            elif value == "":
                pass
            else:
                header.append(value)
                nbr_header.append(nbr)
                nbr += 1

        lines_to_write.append(nbr_header)
        lines_to_write.append(header)

        poly = self.layerComboManagerPolygrid.currentLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return

        poly_field = self.layerComboManagerPolyField.currentField()
        if poly_field == '':
            QMessageBox.critical(None, "Error", "An attribute field with unique fields must be selected")
            return

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")

        year = None
        year2 = None

        if self.Metfile_path is None:
            QMessageBox.critical(self.dlg, "Error", "Meteorological data file has not been provided,"
                                                " please check the main tab")
            return
        elif os.path.isfile(self.Metfile_path[0]):
            with open(self.Metfile_path[0]) as metfile:
                next(metfile)
                for line in metfile:
                    split = line.split()
                    if year == split[0]:
                        break
                    else:
                        if year2 == split[0]:
                            year = split[0]
                            break
                        elif year is None:
                            year = split[0]
                        else:
                            year2 = split[0]
        else:
            QMessageBox.critical(self.dlg, "Error", "Could not find the file containing meteorological data")
            return

        pop_field = self.pop_density.currentField()
        if pop_field == '':
            QMessageBox.critical(None, "Error", "An attribute field including population desity (pp/ha) must be selected")
            return
        
        if self.leaf_cycle == 0:
            QMessageBox.critical(self.dlg, "Error", "No leaf cycle period has been selected")
            return
        else:
            if not (self.leaf_cycle == 1 or self.leaf_cycle == 5):
                QMessageBox.critical(self.dlg,"Warning", "A transition period between Winter and Summer has been "
                                     "choosen. Preferably start the model run during Winter or Summer.")

        map_units = vlayer.crs().mapUnits()
        if not map_units == 0 or map_units == 1 or map_units == 2:
            QMessageBox.critical(self.dlg, "Error", "Could not identify the map units of the polygon layer coordinate "
                                 "reference system")
            return

        if self.LCF_from_file:
            if self.LCFfile_path is None:
                QMessageBox.critical(None, "Error", "Land cover fractions file has not been provided,"
                                                        " please check the main tab")
                return
            if not os.path.isfile(self.LCFfile_path[0]):
                QMessageBox.critical(None, "Error", "Could not find the file containing land cover fractions")
                return

        if self.IMP_from_file:
            if self.IMPfile_path is None:
                QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
                                                    " please check the main tab")
                return
            if not os.path.isfile(self.IMPfile_path[0]):
                QMessageBox.critical(None, "Error", "Could not find the file containing building morphology")
                return

        if self.IMPveg_from_file:
            if self.IMPvegfile_path is None:
                QMessageBox.critical(None, "Error", "Vegetation morphology file has not been provided,"
                                                    " please check the main tab")
                return
            if not os.path.isfile(self.IMPvegfile_path[0]):
                QMessageBox.critical(None, "Error", "Could not find the file containing vegetation morphology")
                return

        if self.land_use_from_file:
            if self.land_use_file_path is None:
                QMessageBox.critical(None, "Error", "Land use fractions file has not been provided,"
                                                    " please check the main tab")
                return
            if not os.path.isfile(self.land_use_file_path[0]):
                QMessageBox.critical(None, "Error", "Could not find the file containing land use cover fractions")
                return

        self.dlg.progressBar.setMaximum(vlayer.featureCount())

        self.startWorker(vlayer, nbr_header, poly_field, self.Metfile_path, self.start_DLS, self.end_DLS, self.LCF_from_file, self.LCFfile_path,
                         self.LCF_Paved, self.LCF_Buildings, self.LCF_Evergreen, self.LCF_Decidious, self.LCF_Grass, self.LCF_Baresoil,
                         self.LCF_Water, self.IMP_from_file, self.IMPfile_path, self.IMP_mean_height, self.IMP_z0, self.IMP_zd,
                         self.IMP_fai, self.IMPveg_from_file, self.IMPvegfile_path, self.IMPveg_mean_height_eve,
                         self.IMPveg_mean_height_dec, self.IMPveg_fai_eve, self.IMPveg_fai_dec, self.pop_density, self.widget_list, self.wall_area,
                         self.land_use_from_file, self.land_use_file_path, lines_to_write, self.plugin_dir, self.output_file_list, map_units,
                         self.header_sheet, self.wall_area_info, self.output_dir, self.day_since_rain, self.leaf_cycle, self.soil_moisture, self.file_code,
                         self.utc, self.checkBox_twovegfiles, self.IMPvegfile_path_dec, self.IMPvegfile_path_eve, self.pop_density_day, self.daypop)

    def startWorker(self, vlayer, nbr_header, poly_field, Metfile_path, start_DLS, end_DLS, LCF_from_file, LCFfile_path, LCF_Paved,
                 LCF_buildings, LCF_evergreen, LCF_decidious, LCF_grass, LCF_baresoil, LCF_water, IMP_from_file, IMPfile_path,
                 IMP_heights_mean, IMP_z0, IMP_zd, IMP_fai, IMPveg_from_file, IMPvegfile_path, IMPveg_heights_mean_eve,
                 IMPveg_heights_mean_dec, IMPveg_fai_eve, IMPveg_fai_dec, pop_density, widget_list, wall_area,
                 land_use_from_file, land_use_file_path, lines_to_write, plugin_dir, output_file_list, map_units, header_sheet, wall_area_info, output_dir,
                 day_since_rain, leaf_cycle, soil_moisture, file_code, utc, checkBox_twovegfiles, IMPvegfile_path_dec, IMPvegfile_path_eve, pop_density_day, daypop):

        worker = Worker(vlayer, nbr_header, poly_field, Metfile_path, start_DLS, end_DLS, LCF_from_file, LCFfile_path, LCF_Paved,
                 LCF_buildings, LCF_evergreen, LCF_decidious, LCF_grass, LCF_baresoil, LCF_water, IMP_from_file, IMPfile_path,
                 IMP_heights_mean, IMP_z0, IMP_zd, IMP_fai, IMPveg_from_file, IMPvegfile_path, IMPveg_heights_mean_eve,
                 IMPveg_heights_mean_dec, IMPveg_fai_eve, IMPveg_fai_dec, pop_density, widget_list, wall_area,
                 land_use_from_file, land_use_file_path, lines_to_write, plugin_dir, output_file_list, map_units, header_sheet, wall_area_info, output_dir,
                 day_since_rain, leaf_cycle, soil_moisture, file_code, utc, checkBox_twovegfiles, IMPvegfile_path_dec, IMPvegfile_path_eve, pop_density_day, daypop)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.closeButton.setEnabled(False)

        thread = QThread(self.dlg)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, ret):
        try:
            self.worker.deleteLater()
        except RuntimeError:
            pass
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        if ret == 1:
            self.dlg.runButton.setText('Generate')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.generate)
            self.dlg.closeButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            self.iface.messageBar().pushMessage("SUEWS Prepare",
                                                "Process finished! Check General Messages (speech bubble, lower left) "
                                                "to obtain information of the process.", duration=5)
        else:
            self.dlg.runButton.setText('Generate')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.generate)
            self.dlg.closeButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            QMessageBox.information(None, "SUEWS Prepare", "Operations cancelled, "
                                    "process unsuccessful! See the General tab in Log Meassages Panel "
                                    "(speech bubble, lower right) for more information.")

    def workerError(self, errorstring):
        QgsMessageLog.logMessage(errorstring, level=Qgis.Critical)

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def help(self):
        url = "http://umep-docs.readthedocs.io/en/latest/pre-processor/SUEWS%20Prepare.html"
        webbrowser.open_new_tab(url)


        #     for feature in vlayer.getFeatures():
        #         new_line = [None] * len(nbr_header)
        #         print_line = True
        #         feat_id = int(feature.attribute(poly_field))
        #         code = "Grid"
        #         index = self.find_index(code)
        #         new_line[index] = str(feat_id)
        #
        #         # self.dlg.progressBar.setValue(ind)
        #
        #         year = None
        #         year2 = None
        #
        #         if self.Metfile_path is None:
        #             QMessageBox.critical(None, "Error", "Meteorological data file has not been provided,"
        #                                                 " please check the main tab")
        #             return
        #         elif os.path.isfile(self.Metfile_path):
        #             with open(self.Metfile_path) as file:
        #                 next(file)
        #                 for line in file:
        #                     split = line.split()
        #                     if year == split[0]:
        #                         break
        #                     else:
        #                         if year2 == split[0]:
        #                             year = split[0]
        #                             break
        #                         elif year is None:
        #                             year = split[0]
        #                         else:
        #                             year2 = split[0]
        #
        #         else:
        #             QMessageBox.critical(None, "Error", "Could not find the file containing meteorological data")
        #             return
        #
        #         code = "Year"
        #         index = self.find_index(code)
        #         new_line[index] = str(year)
        #         code = "StartDLS"
        #         index = self.find_index(code)
        #         new_line[index] = str(self.start_DLS)
        #         code = "EndDLS"
        #         index = self.find_index(code)
        #         new_line[index] = str(self.end_DLS)
        #
        #         old_cs = osr.SpatialReference()
        #         vlayer_ref = vlayer.crs().toWkt()
        #         old_cs.ImportFromWkt(vlayer_ref)
        #
        #         wgs84_wkt = """
        #         GEOGCS["WGS 84",
        #             DATUM["WGS_1984",
        #                 SPHEROID["WGS 84",6378137,298.257223563,
        #                     AUTHORITY["EPSG","7030"]],
        #                 AUTHORITY["EPSG","6326"]],
        #             PRIMEM["Greenwich",0,
        #                 AUTHORITY["EPSG","8901"]],
        #             UNIT["degree",0.01745329251994328,
        #                 AUTHORITY["EPSG","9122"]],
        #             AUTHORITY["EPSG","4326"]]"""
        #
        #         new_cs = osr.SpatialReference()
        #         new_cs.ImportFromWkt(wgs84_wkt)
        #
        #         # area_wkt = """
        #         # GEOCCS["WGS 84 (geocentric)",
        #         #     DATUM["World Geodetic System 1984",
        #         #         SPHEROID["WGS 84",6378137.0,298.257223563,
        #         #             AUTHORITY["EPSG","7030"]],
        #         #         AUTHORITY["EPSG","6326"]],
        #         #     PRIMEM["Greenwich",0.0,
        #         #         AUTHORITY["EPSG","8901"]],
        #         #     UNIT["m",1.0],
        #         #     AXIS["Geocentric X",OTHER],
        #         #     AXIS["Geocentric Y",EAST],
        #         #     AXIS["Geocentric Z",NORTH],
        #         #     AUTHORITY["EPSG","4328"]]"""
        #
        #         # new_cs_area = QgsCoordinateReferenceSystem(area_wkt)
        #
        #         transform = osr.CoordinateTransformation(old_cs, new_cs)
        #
        #         centroid = feature.geometry().centroid().asPoint()
        #         #areatransform = QgsCoordinateTransform(old_cs_area, new_cs_area)
        #         #feature.geometry().transform(areatransform)
        #         area = feature.geometry().area()
        #         map_units = vlayer.crs().mapUnits()
        #
        #         if map_units == 0:
        #             hectare = area * 0.0001
        #
        #         elif map_units == 1:
        #             hectare = area/107640.
        #
        #         elif map_units == 2:
        #             hectare = area
        #
        #         else:
        #             QMessageBox.critical(None, "Error", "Could not identify the map units of the polygon layer coordinate "
        #                                                 "reference system")
        #             return
        #
        #         lonlat = transform.TransformPoint(centroid.x(), centroid.y())
        #         code = "lat"
        #         index = self.find_index(code)
        #         new_line[index] = str(lonlat[1])
        #         code = "lng"
        #         index = self.find_index(code)
        #         new_line[index] = str(lonlat[0])
        #         code = "SurfaceArea"
        #         index = self.find_index(code)
        #         new_line[index] = str(hectare)
        #
        #         altitude = 0
        #         day = 1
        #         hour = 0
        #         minute = 0
        #
        #         code = "Alt"
        #         index = self.find_index(code)
        #         new_line[index] = str(altitude)
        #         code = "id"
        #         index = self.find_index(code)
        #         new_line[index] = str(day)
        #         code = "ih"
        #         index = self.find_index(code)
        #         new_line[index] = str(hour)
        #         code = "imin"
        #         index = self.find_index(code)
        #         new_line[index] = str(minute)
        #
        #         if self.LCF_from_file:
        #             found_LCF_line = False
        #
        #             if self.LCFfile_path is None:
        #                 QMessageBox.critical(None, "Error", "Land cover fractions file has not been provided,"
        #                                                     " please check the main tab")
        #                 return
        #             elif os.path.isfile(self.LCFfile_path):
        #                 with open(self.LCFfile_path) as file:
        #                     next(file)
        #                     for line in file:
        #                         split = line.split()
        #                         if feat_id == int(split[0]):
        #                             LCF_paved = split[1]
        #                             LCF_buildings = split[2]
        #                             LCF_evergreen = split[3]
        #                             LCF_decidious = split[4]
        #                             LCF_grass = split[5]
        #                             LCF_baresoil = split[6]
        #                             LCF_water = split[7]
        #                             found_LCF_line = True
        #                             break
        #                     if not found_LCF_line:
        #                             LCF_paved = -999
        #                             LCF_buildings = -999
        #                             LCF_evergreen = -999
        #                             LCF_decidious = -999
        #                             LCF_grass = -999
        #                             LCF_baresoil = -999
        #                             LCF_water = -999
        #                             print_line = False
        #             else:
        #                 QMessageBox.critical(None, "Error", "Could not find the file containing land cover fractions")
        #                 return
        #         else:
        #             LCF_paved = feature.attribute(self.LCF_Paved.getFieldName())
        #             LCF_buildings = feature.attribute(self.LCF_Buildings.getFieldName())
        #             LCF_evergreen = feature.attribute(self.LCF_Evergreen.getFieldName())
        #             LCF_decidious = feature.attribute(self.LCF_Decidious.getFieldName())
        #             LCF_grass = feature.attribute(self.LCF_Grass.getFieldName())
        #             LCF_baresoil = feature.attribute(self.LCF_Baresoil.getFieldName())
        #             LCF_water = feature.attribute(self.LCF_Water.getFieldName())
        #
        #         code = "Fr_Paved"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_paved)
        #         code = "Fr_Bldgs"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_buildings)
        #         code = "Fr_EveTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_evergreen)
        #         code = "Fr_DecTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_decidious)
        #         code = "Fr_Grass"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_grass)
        #         code = "Fr_Bsoil"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_baresoil)
        #         code = "Fr_Water"
        #         index = self.find_index(code)
        #         new_line[index] = str(LCF_water)
        #
        #         irrFr_EveTr = 0
        #         irrFr_DecTr = 0
        #         irrFr_Grass = 0
        #
        #         code = "IrrFr_EveTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(irrFr_EveTr)
        #         code = "IrrFr_DecTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(irrFr_DecTr)
        #         code = "IrrFr_Grass"
        #         index = self.find_index(code)
        #         new_line[index] = str(irrFr_Grass)
        #
        #         Traffic_Rate = 99999
        #         BuildEnergy_Use = 99999
        #
        #         code = "TrafficRate"
        #         index = self.find_index(code)
        #         new_line[index] = str(Traffic_Rate)
        #         code = "BuildEnergyUse"
        #         index = self.find_index(code)
        #         new_line[index] = str(BuildEnergy_Use)
        #
        #         Activity_ProfWD = 55663
        #         Activity_ProfWE = 55664
        #
        #         code = "ActivityProfWD"
        #         index = self.find_index(code)
        #         new_line[index] = str(Activity_ProfWD)
        #         code = "ActivityProfWE"
        #         index = self.find_index(code)
        #         new_line[index] = str(Activity_ProfWE)
        #
        #         if self.IMP_from_file:
        #             found_IMP_line = False
        #
        #             if self.IMPfile_path is None:
        #                 QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
        #                                                     " please check the main tab")
        #                 return
        #             elif os.path.isfile(self.IMPfile_path):
        #                 with open(self.IMPfile_path) as file:
        #                     next(file)
        #                     for line in file:
        #                         split = line.split()
        #                         if feat_id == int(split[0]):
        #                             IMP_heights_mean = split[3]
        #                             IMP_z0 = split[6]
        #                             IMP_zd = split[7]
        #                             IMP_fai = split[2]
        #                             found_IMP_line = True
        #                             break
        #                     if not found_IMP_line:
        #                             IMP_heights_mean = -999
        #                             IMP_z0 = -999
        #                             IMP_zd = -999
        #                             IMP_fai = -999
        #                             print_line = False
        #             else:
        #                 QMessageBox.critical(None, "Error", "Could not find the file containing building morphology")
        #                 return
        #         else:
        #             IMP_heights_mean = feature.attribute(self.IMP_mean_height.getFieldName())
        #             IMP_z0 = feature.attribute(self.IMP_z0.getFieldName())
        #             IMP_zd = feature.attribute(self.IMP_zd.getFieldName())
        #             IMP_fai = feature.attribute(self.IMP_fai.getFieldName())
        #
        #         if self.IMPveg_from_file:
        #             found_IMPveg_line = False
        #
        #             if self.IMPvegfile_path is None:
        #                 QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
        #                                                     " please check the main tab")
        #                 return
        #             elif os.path.isfile(self.IMPvegfile_path):
        #                 with open(self.IMPvegfile_path) as file:
        #                     next(file)
        #                     for line in file:
        #                         split = line.split()
        #                         if feat_id == int(split[0]):
        #                             IMPveg_heights_mean_eve = split[3]
        #                             IMPveg_heights_mean_dec = split[3]
        #                             IMPveg_fai_eve = split[2]
        #                             IMPveg_fai_dec = split[2]
        #                             found_IMPveg_line = True
        #                             break
        #                     if not found_IMPveg_line:
        #                             IMPveg_heights_mean_eve = -999
        #                             IMPveg_heights_mean_dec = -999
        #                             IMPveg_fai_eve = -999
        #                             IMPveg_fai_dec = -999
        #                             print_line = False
        #             else:
        #                 QMessageBox.critical(None, "Error", "Could not find the file containing building morphology")
        #                 return
        #         else:
        #             IMPveg_heights_mean_eve = feature.attribute(self.IMPveg_mean_height_eve.getFieldName())
        #             IMPveg_heights_mean_dec = feature.attribute(self.IMPveg_mean_height_dec.getFieldName())
        #             IMPveg_fai_eve = feature.attribute(self.IMPveg_fai_eve.getFieldName())
        #             IMPveg_fai_dec = feature.attribute(self.IMPveg_fai_dec.getFieldName())
        #
        #         if IMP_z0 == 0:
        #             IMP_z0 = 0.03
        #
        #         if IMP_zd == 0:
        #             IMP_zd = 0.1
        #
        #         code = "H_Bldgs"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMP_heights_mean)
        #         code = "H_EveTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMPveg_heights_mean_eve)
        #         code = "H_DecTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMPveg_heights_mean_dec)
        #         code = "z0"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMP_z0)
        #         code = "zd"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMP_zd)
        #         code = "FAI_Bldgs"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMP_fai)
        #         code = "FAI_EveTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMPveg_fai_eve)
        #         code = "FAI_DecTr"
        #         index = self.find_index(code)
        #         new_line[index] = str(IMPveg_fai_dec)
        #
        #         if self.pop_density is not None:
        #             pop_density_night = feature.attribute(self.pop_density.getFieldName())
        #         else:
        #             pop_density_night = -999
        #
        #         pop_density_day = -999
        #
        #         code = "PopDensDay"
        #         index = self.find_index(code)
        #         new_line[index] = str(pop_density_day)
        #         code = "PopDensNight"
        #         index = self.find_index(code)
        #         new_line[index] = str(pop_density_night)
        #
        #         for widget in self.widget_list:
        #             if widget.get_checkstate():
        #                 code_field = str(widget.comboBox_uniquecodes.currentText())
        #                 try:
        #                     code = int(feature.attribute(code_field))
        #                 except ValueError as e:
        #                     QMessageBox.critical(None, "Error", "Unique code field for widget " + widget.get_title() +
        #                                          " should only contain integers")
        #                     return
        #                 match = widget.comboBox.findText(str(code))
        #                 if match == -1:
        #                     QMessageBox.critical(None, "Error", "Unique code field for widget " + widget.get_title() +
        #                                          " contains one or more codes with no match in site library")
        #                     return
        #                 index = widget.get_sitelistpos()
        #                 new_line[index-1] = str(code)
        #
        #             else:
        #                 code = widget.get_combo_text()
        #                 index = widget.get_sitelistpos()
        #                 new_line[index-1] = str(code)
        #
        #         LUMPS_drate = 0.25
        #         LUMPS_Cover = 1
        #         LUMPS_MaxRes = 10
        #         NARP_Trans = 1
        #
        #         code = "LUMPS_DrRate"
        #         index = self.find_index(code)
        #         new_line[index] = str(LUMPS_drate)
        #         code = "LUMPS_Cover"
        #         index = self.find_index(code)
        #         new_line[index] = str(LUMPS_Cover)
        #         code = "LUMPS_MaxRes"
        #         index = self.find_index(code)
        #         new_line[index] = str(LUMPS_MaxRes)
        #         code = "NARP_Trans"
        #         index = self.find_index(code)
        #         new_line[index] = str(NARP_Trans)
        #
        #         flow_change = 0
        #         RunoffToWater = 0.1
        #         PipeCap = 100
        #         GridConn1of8 = 0
        #         Fraction1of8 = 0
        #         GridConn2of8 = 0
        #         Fraction2of8 = 0
        #         GridConn3of8 = 0
        #         Fraction3of8 = 0
        #         GridConn4of8 = 0
        #         Fraction4of8 = 0
        #         GridConn5of8 = 0
        #         Fraction5of8 = 0
        #         GridConn6of8 = 0
        #         Fraction6of8 = 0
        #         GridConn7of8 = 0
        #         Fraction7of8 = 0
        #         GridConn8of8 = 0
        #         Fraction8of8 = 0
        #
        #         code = "FlowChange"
        #         index = self.find_index(code)
        #         new_line[index] = str(flow_change)
        #         code = "RunoffToWater"
        #         index = self.find_index(code)
        #         new_line[index] = str(RunoffToWater)
        #         code = "PipeCapacity"
        #         index = self.find_index(code)
        #         new_line[index] = str(PipeCap)
        #         code = "GridConnection1of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn1of8)
        #         code = "Fraction1of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction1of8)
        #         code = "GridConnection2of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn2of8)
        #         code = "Fraction2of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction2of8)
        #         code = "GridConnection3of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn3of8)
        #         code = "Fraction3of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction3of8)
        #         code = "GridConnection4of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn4of8)
        #         code = "Fraction4of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction4of8)
        #         code = "GridConnection5of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn5of8)
        #         code = "Fraction5of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction5of8)
        #         code = "GridConnection6of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn6of8)
        #         code = "Fraction6of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction6of8)
        #         code = "GridConnection7of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn7of8)
        #         code = "Fraction7of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction7of8)
        #         code = "GridConnection8of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(GridConn8of8)
        #         code = "Fraction8of8"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fraction8of8)
        #
        #         WhitinGridPav = 661
        #         WhitinGridBldg = 662
        #         WhitinGridEve = 663
        #         WhitinGridDec = 664
        #         WhitinGridGrass = 665
        #         WhitinGridUnmanBsoil = 666
        #         WhitinGridWaterCode = 667
        #
        #         code = "WithinGridPavedCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridPav)
        #         code = "WithinGridBldgsCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridBldg)
        #         code = "WithinGridEveTrCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridEve)
        #         code = "WithinGridDecTrCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridDec)
        #         code = "WithinGridGrassCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridGrass)
        #         code = "WithinGridUnmanBSoilCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridUnmanBsoil)
        #         code = "WithinGridWaterCode"
        #         index = self.find_index(code)
        #         new_line[index] = str(WhitinGridWaterCode)
        #
        #         if self.wall_area_info:
        #             wall_area = feature.attribute(self.wall_area.getFieldName())
        #         else:
        #             wall_area = -999
        #
        #         code = "AreaWall"
        #         index = self.find_index(code)
        #         new_line[index] = str(wall_area)
        #
        #         if self.land_use_from_file:
        #             if self.land_use_file_path is None:
        #                 QMessageBox.critical(None, "Error", "Land use fractions file has not been provided,"
        #                                                     " please check the main tab")
        #                 return
        #             elif os.path.isfile(self.land_use_file_path):
        #                 with open(self.land_use_file_path) as file:
        #                     next(file)
        #                     found_LUF_line = False
        #                     for line in file:
        #                         split = line.split()
        #                         if feat_id == int(split[0]):
        #                             Fr_ESTMClass_Paved1 = split[1]
        #                             Fr_ESTMClass_Paved2 = split[2]
        #                             Fr_ESTMClass_Paved3 = split[3]
        #                             Code_ESTMClass_Paved1 = split[4]
        #                             Code_ESTMClass_Paved2 = split[5]
        #                             Code_ESTMClass_Paved3 = split[6]
        #                             Fr_ESTMClass_Bldgs1 = split[7]
        #                             Fr_ESTMClass_Bldgs2 = split[8]
        #                             Fr_ESTMClass_Bldgs3 = split[9]
        #                             Fr_ESTMClass_Bldgs4 = split[10]
        #                             Fr_ESTMClass_Bldgs5 = split[11]
        #                             Code_ESTMClass_Bldgs1 = split[12]
        #                             Code_ESTMClass_Bldgs2 = split[13]
        #                             Code_ESTMClass_Bldgs3 = split[14]
        #                             Code_ESTMClass_Bldgs4 = split[15]
        #                             Code_ESTMClass_Bldgs5 = split[16]
        #
        #                             # if (float(Fr_ESTMClass_Paved1) + float(Fr_ESTMClass_Paved2) + float(Fr_ESTMClass_Paved3)) != 1:
        #                             #     QMessageBox.critical(None, "Error", "Land use fractions for paved not equal to 1 at " + str(feat_id))
        #                             #     return
        #                             #
        #                             # if (float(Fr_ESTMClass_Bldgs1) + float(Fr_ESTMClass_Bldgs2) + float(Fr_ESTMClass_Bldgs3) + float(Fr_ESTMClass_Bldgs4) + float(Fr_ESTMClass_Bldgs5)) != 1:
        #                             #     QMessageBox.critical(None, "Error", "Land use fractions for buildings not equal to 1 at " + str(feat_id))
        #                             #     return
        #
        #                             found_LUF_line = True
        #                             break
        #
        #                     if not found_LUF_line:
        #                             Fr_ESTMClass_Paved1 = 1.
        #                             Fr_ESTMClass_Paved2 = 0.
        #                             Fr_ESTMClass_Paved3 = 0.
        #                             Code_ESTMClass_Paved1 = 807
        #                             Code_ESTMClass_Paved2 = 99999
        #                             Code_ESTMClass_Paved3 = 99999
        #                             Fr_ESTMClass_Bldgs1 = 1.0
        #                             Fr_ESTMClass_Bldgs2 = 0.
        #                             Fr_ESTMClass_Bldgs3 = 0.
        #                             Fr_ESTMClass_Bldgs4 = 0.
        #                             Fr_ESTMClass_Bldgs5 = 0.
        #                             Code_ESTMClass_Bldgs1 = 801
        #                             Code_ESTMClass_Bldgs2 = 99999
        #                             Code_ESTMClass_Bldgs3 = 99999
        #                             Code_ESTMClass_Bldgs4 = 99999
        #                             Code_ESTMClass_Bldgs5 = 99999
        #             else:
        #                 QMessageBox.critical(None, "Error", "Could not find the file containing land use cover fractions")
        #                 return
        #         else:
        #             Fr_ESTMClass_Paved1 = 1.
        #             Fr_ESTMClass_Paved2 = 0.
        #             Fr_ESTMClass_Paved3 = 0.
        #             Code_ESTMClass_Paved1 = 807
        #             Code_ESTMClass_Paved2 = 99999
        #             Code_ESTMClass_Paved3 = 99999
        #             Fr_ESTMClass_Bldgs1 = 1.
        #             Fr_ESTMClass_Bldgs2 = 0.
        #             Fr_ESTMClass_Bldgs3 = 0.
        #             Fr_ESTMClass_Bldgs4 = 0.
        #             Fr_ESTMClass_Bldgs5 = 0.
        #             Code_ESTMClass_Bldgs1 = 801
        #             Code_ESTMClass_Bldgs2 = 99999
        #             Code_ESTMClass_Bldgs3 = 99999
        #             Code_ESTMClass_Bldgs4 = 99999
        #             Code_ESTMClass_Bldgs5 = 99999
        #
        #         code = "Fr_ESTMClass_Bldgs1"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Bldgs1)
        #         code = "Fr_ESTMClass_Bldgs2"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Bldgs2)
        #         code = "Fr_ESTMClass_Bldgs3"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Bldgs3)
        #         code = "Fr_ESTMClass_Bldgs4"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Bldgs4)
        #         code = "Fr_ESTMClass_Bldgs5"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Bldgs5)
        #         code = "Fr_ESTMClass_Paved1"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Paved1)
        #         code = "Fr_ESTMClass_Paved2"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Paved2)
        #         code = "Fr_ESTMClass_Paved3"
        #         index = self.find_index(code)
        #         new_line[index] = str(Fr_ESTMClass_Paved3)
        #         code = "Code_ESTMClass_Bldgs1"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Bldgs1)
        #         code = "Code_ESTMClass_Bldgs2"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Bldgs2)
        #         code = "Code_ESTMClass_Bldgs3"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Bldgs3)
        #         code = "Code_ESTMClass_Bldgs4"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Bldgs4)
        #         code = "Code_ESTMClass_Bldgs5"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Bldgs5)
        #         code = "Code_ESTMClass_Paved1"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Paved1)
        #         code = "Code_ESTMClass_Paved2"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Paved2)
        #         code = "Code_ESTMClass_Paved3"
        #         index = self.find_index(code)
        #         new_line[index] = str(Code_ESTMClass_Paved3)
        #
        #         new_line.append("!")
        #
        #         if print_line:
        #             lines_to_write.append(new_line)
        #             self.initial_conditions(year, feat_id)
        #
        #         ind += 1
        #
        #     output_lines = []
        #     output_file = self.output_dir[0] + "/SUEWS_SiteSelect.txt"
        #     with open(output_file, 'w+') as ofile:
        #         for line in lines_to_write:
        #             string_to_print = ''
        #             for element in line:
        #                 string_to_print += str(element) + '\t'
        #             string_to_print += "\n"
        #             output_lines.append(string_to_print)
        #         output_lines.append("-9\n")
        #         output_lines.append("-9\n")
        #         ofile.writelines(output_lines)
        #         for input_file in self.output_file_list:
        #             try:
        #                 copyfile(self.output_path + input_file, self.output_dir[0] + "/" + input_file)
        #             except IOError as e:
        #                 QgsMessageLog.logMessage("Error copying output files with SUEWS_SiteSelect.txt: " + str(e), level=QgsMessageLog.CRITICAL)
        #         copyfile(self.Metfile_path, self.output_dir[0] + "/" + self.file_code + '_data.txt')
        #         QMessageBox.information(None, "Complete", "File successfully created as SUEWS_SiteSelect.txt in Output "
        #                                                   "Folder: " + self.output_dir[0])
        #
        # def find_index(self, code):
        #     values = self.header_sheet.row_values(1)
        #     index = values.index(code)
        #     return index
        #
        # def initial_conditions(self, year, gridid):
        #     nml = f90nml.read(self.input_path + 'InitialConditions.nml')
        #     DaysSinceRain = self.day_since_rain
        #     LeafCycle = self.leaf_cycle
        #     SoilMoisture = self.soil_moisture
        #     moist = int(int(SoilMoisture) * 1.5)
        #
        #     DailyMeanT = self.find_daily_mean_temp()
        #
        #     nml['initialconditions']['dayssincerain'] = int(DaysSinceRain)
        #     nml['initialconditions']['temp_c0'] = float(DailyMeanT)
        #     nml['initialconditions']['soilstorepavedstate'] = moist
        #     nml['initialconditions']['soilstorebldgsstate'] = moist
        #     nml['initialconditions']['soilstoreevetrstate'] = moist
        #     nml['initialconditions']['soilstoredectrstate'] = moist
        #     nml['initialconditions']['soilstoregrassstate'] = moist
        #     nml['initialconditions']['soilstorebsoilstate'] = moist
        #
        #     f = open(self.Metfile_path, 'r')
        #     lin = f.readlines()
        #     index = 1
        #     lines = np.array(lin[index].split())
        #     nml['initialconditions']['id_prev'] = int(lines[1]) - 1
        #     f.close()
        #
        #     if LeafCycle == 0: # Winter
        #         nml['initialconditions']['gdd_1_0'] = 0
        #         nml['initialconditions']['gdd_2_0'] = -450
        #         nml['initialconditions']['laiinitialevetr'] = 4
        #         nml['initialconditions']['laiinitialdectr'] = 1
        #         nml['initialconditions']['laiinitialgrass'] = 1.6
        #     elif LeafCycle == 1:
        #         nml['initialconditions']['gdd_1_0'] = 50
        #         nml['initialconditions']['gdd_2_0'] = -400
        #         nml['initialconditions']['laiinitialevetr'] = 4.2
        #         nml['initialconditions']['laiinitialdectr'] = 2.0
        #         nml['initialconditions']['laiinitialgrass'] = 2.6
        #     elif LeafCycle == 2:
        #         nml['initialconditions']['gdd_1_0'] = 150
        #         nml['initialconditions']['gdd_2_0'] = -300
        #         nml['initialconditions']['laiinitialevetr'] = 4.6
        #         nml['initialconditions']['laiinitialdectr'] = 3.0
        #         nml['initialconditions']['laiinitialgrass'] = 3.6
        #     elif LeafCycle == 3:
        #         nml['initialconditions']['gdd_1_0'] = 225
        #         nml['initialconditions']['gdd_2_0'] = -150
        #         nml['initialconditions']['laiinitialevetr'] = 4.9
        #         nml['initialconditions']['laiinitialdectr'] = 4.5
        #         nml['initialconditions']['laiinitialgrass'] = 4.6
        #     elif LeafCycle == 4: # Summer
        #         nml['initialconditions']['gdd_1_0'] = 300
        #         nml['initialconditions']['gdd_2_0'] = 0
        #         nml['initialconditions']['laiinitialevetr'] = 5.1
        #         nml['initialconditions']['laiinitialdectr'] = 5.5
        #         nml['initialconditions']['laiinitialgrass'] = 5.9
        #     elif LeafCycle == 5:
        #         nml['initialconditions']['gdd_1_0'] = 225
        #         nml['initialconditions']['gdd_2_0'] = -150
        #         nml['initialconditions']['laiinitialevetr'] = 4.9
        #         nml['initialconditions']['laiinitialdectr'] = 4,5
        #         nml['initialconditions']['laiinitialgrass'] = 4.6
        #     # elif LeafCycle == 6:
        #     #     nml['initialconditions']['gdd_1_0'] = 150
        #     #     nml['initialconditions']['gdd_2_0'] = -300
        #     #     nml['initialconditions']['laiinitialevetr'] = 4.6
        #     #     nml['initialconditions']['laiinitialdectr'] = 3.0
        #     #     nml['initialconditions']['laiinitialgrass'] = 3.6
        #     elif LeafCycle == 6: # dummy for londonsmall
        #         nml['initialconditions']['gdd_1_0'] = 150
        #         nml['initialconditions']['gdd_2_0'] = -300
        #         nml['initialconditions']['laiinitialevetr'] = 4.6
        #         nml['initialconditions']['laiinitialdectr'] = 5.0
        #         nml['initialconditions']['laiinitialgrass'] = 5.6
        #     elif LeafCycle == 7:
        #         nml['initialconditions']['gdd_1_0'] = 50
        #         nml['initialconditions']['gdd_2_0'] = -400
        #         nml['initialconditions']['laiinitialevetr'] = 4.2
        #         nml['initialconditions']['laiinitialdectr'] = 2.0
        #         nml['initialconditions']['laiinitialgrass'] = 2.6
        #
        #     nml.write(self.output_dir[0] + '/InitialConditions' + str(self.file_code) + str(gridid) + '_' + str(year) +
        #               '.nml', force=True)
        #
        # def find_daily_mean_temp(self):
        #     if os.path.isfile(self.Metfile_path):
        #         with open(self.Metfile_path) as file:
        #             next(file)
        #             line = next(file)
        #             split = line.split()
        #             day = int(split[1])
        #             number_of_hours = 1
        #             total_temp = float(split[11])
        #             for line in file:
        #                 split = line.split()
        #                 if day == int(split[1]):
        #                     total_temp += float(split[11])
        #                     number_of_hours += 1
        #
        #             mean_temp = float(total_temp)/int(number_of_hours)
        #             return mean_temp