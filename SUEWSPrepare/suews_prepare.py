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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QImage, QLabel, QPixmap, QLineEdit, QFormLayout, QIntValidator, \
    QGroupBox, QGridLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QFileDialog
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from suews_prepare_dialog import SUEWSPrepareDialog

from tabs.paved import PavedTab
from tabs.buildings import BuildingsTab
from tabs.evergreen import EvergreenTab
from tabs.decidious import DecidiousTab
from tabs.grass import GrassTab
from tabs.baresoil import BareSoilTab
from tabs.water import WaterTab
from tabs.conductance import ConductanceTab
from tabs.snow import SnowTab
from tabs.anthropogenic import AnthroTab
from tabs.energy import EnergyTab
from tabs.irrigation import IrrigationTab
from tabs.wateruse import WaterUseTab

from tabs.template_widget import TemplateWidget
from tabs.template_tab import TemplateTab

from tabs.main_tab import MainTab

from tabs.changeDialog import ChangeDialog

from tabs.photodialog import PhotoDialog

#from tabs.testwidget import TestTab
#from tabs.test import Test
import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__) + '/Modules')
# from Modules import xlrd
from Modules.xlutils.copy import copy
import xlrd  # from QGIS installation

#import setup_maintab as sm
#import xlrd
#import xlwt
#from Modules import xlutils
# from Modules import xlwt
# from Modules import openpyxl
# from Modules.qgiscombomanager import *
from ..Utilities.qgiscombomanager import *
# import urllib
import urllib2
import fileinput
import itertools
from osgeo import gdal, osr
from shutil import copyfile
import webbrowser


class SUEWSPrepare:
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
            'SUEWSPrepare_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.output_file_list = []

        self.input_path = self.plugin_dir + '/Input/'
        self.output_path = self.plugin_dir + '/Output/'
        self.output_heat = 'SUEWS_AnthropogenicHeat.txt'
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

        self.file_path = self.plugin_dir + '/Input/SUEWS_SiteLibrary.xls'
        self.init_path = self.plugin_dir + '/Input/SUEWS_init.xlsx'
        #self.file_path = self.plugin_dir + '/Input/SUEWS_SiteInfo18_Lo_SUEWSPrepare.xlsm'
        self.header_file_path = self.plugin_dir + '/Input/SUEWS_SiteSelect.xlsx'
        self.line_list = []
        self.widget_list = []
        self.data = xlrd.open_workbook(self.file_path)
        self.init_data = xlrd.open_workbook(self.init_path)
        self.header_data = xlrd.open_workbook(self.header_file_path)
        self.isEditable = False
        self.heatsheet = self.data.sheet_by_name("SUEWS_AnthropogenicHeat")
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
        #self.test_widget = TestTab()
        #self.test_widget2 = TestTab()
        #self.test_window = Test()

        self.outputDialog = QFileDialog()
        self.outputDialog.setFileMode(4)
        self.outputDialog.setAcceptMode(1)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(0)
        self.fileDialog.setAcceptMode(0)

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
        self.IMP_mean_height = None
        self.IMP_z0 = None
        self.IMP_zd = None
        self.IMP_fai = None
        self.IMPveg_mean_height_dec = None
        self.IMPveg_mean_height_eve = None
        self.IMPveg_fai_dec = None
        self.IMPveg_fai_eve = None
        self.wall_area = None

        self.start_DLS = 85
        self.end_DLS = 302

        # Declare instance attributes

        self.actions = []
        # self.menu = self.tr(u'&SUEWS Prepare')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SUEWSPrepare')
        # self.toolbar.setObjectName(u'SUEWSPrepare')

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

        icon_path = ':/plugins/SUEWSPrepare/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'SUEWS Prepare'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
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

        for shidx in xrange(1, self.init_data.nsheets):
            sheet = self.init_data.sheet_by_index(shidx)
            title = sheet_names[shidx]
            self.setup_tab(title, sheet)

    def setup_tab(self, title, sheet):
        tab = TemplateTab()
        x = 0
        y = 0
        for row in xrange(0, sheet.nrows):
            values = sheet.row_values(row)
            QgsMessageLog.logMessage(str(values), level=QgsMessageLog.CRITICAL)
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
                    QgsMessageLog.logMessage("Value error for plugin titled " + title + " for input code: " + str(e), level=QgsMessageLog.CRITICAL)
                    code = None
            if values[4] is None:
                default_combo = None
            elif values[4] == "":
                default_combo = None
            else:
                try:
                    default_combo = int(values[4])
                except ValueError as e:
                    QgsMessageLog.logMessage("Value error for plugin titled " + title + " for default combo: " + str(e), level=QgsMessageLog.CRITICAL)
                    default_combo = None
            if values[5] is None:
                sitelist_pos = None
            elif values[5] == "":
                sitelist_pos = None
            else:
                try:
                    sitelist_pos = int(values[5])
                except ValueError as e:
                    QgsMessageLog.logMessage("Value error for plugin titled " + title + " for site list position: " + str(e), level=QgsMessageLog.CRITICAL)
                    sitelist_pos = None

            widget = TemplateWidget(input_sheet, file_path, widget_title, code, default_combo, sitelist_pos)
            self.widget_list.append(widget)
            widget.setup_widget()
            widget.make_edits_signal.connect(self.make_edits)
            widget.edit_mode_signal.connect(self.edit_mode)
            widget.cancel_edits_signal.connect(self.cancel_edits)
            widget.checkbox_signal.connect(lambda: self.fill_combobox(widget))

            tab.Layout.addWidget(widget, x, y)

            if y < 1:
                y += 1
            else:
                x += 1
                y = 0

        self.dlg.tabWidget.addTab(tab, str(title))

    def setup_tabs_outdated2(self):

        self.dlg.tabWidget.clear()
        self.widget_list = []

        main_tab = MainTab()
        self.setup_maintab(main_tab)

        paved_tab = PavedTab()
        buildings_tab = BuildingsTab()
        evergreen_tab = EvergreenTab()
        decidious_tab = DecidiousTab()
        grass_tab = GrassTab()
        baresoil_tab = BareSoilTab()
        water_tab = WaterTab()
        conductance_tab = ConductanceTab()
        snow_tab = SnowTab()
        anthro_tab = AnthroTab()
        energy_tab = EnergyTab()
        irrigation_tab = IrrigationTab()
        wateruse_tab = WaterUseTab()

        imp_paved_widget = TemplateWidget(self.impsheet, self.output_nonveg, "Paved surface characteristics", 1, 661)
        self.widget_list.append(imp_paved_widget)
        imp_buildings_widget = TemplateWidget(self.impsheet, self.output_nonveg, "Building surface characteristics", 2,
                                              662)
        self.widget_list.append(imp_buildings_widget)
        veg_evergreen_widget = TemplateWidget(self.vegsheet, self.output_veg, "Evergreen surface characteristics", 3,
                          661)
        self.widget_list.append(veg_evergreen_widget)
        veg_decidious_widget = TemplateWidget(self.vegsheet, self.output_veg, "Decidious surface characteristics", 4,
                          662)
        self.widget_list.append(veg_decidious_widget)
        veg_grass_widget = TemplateWidget(self.vegsheet, self.output_veg, "Grass surface characteristics", 5, 663)
        self.widget_list.append(veg_grass_widget)
        imp_baresoil_widget = TemplateWidget(self.impsheet, self.output_nonveg, "Bare soil surface characteristics", 6,
                                             663)
        self.widget_list.append(imp_baresoil_widget)
        water_widget = TemplateWidget(self.watersheet, self.output_water, "Water surface characteristics", None, 661)
        self.widget_list.append(water_widget)
        conductance_widget = TemplateWidget(self.condsheet, self.output_cond, "Surface conductance parameters", None,
                                            100)
        self.widget_list.append(conductance_widget)
        snow_widget = TemplateWidget(self.snowsheet, self.output_snow, "Snow surface characteristics", None, 660)
        self.widget_list.append(snow_widget)
        prof_snow1_widget = TemplateWidget(self.profsheet, self.output_prof, "Snow clearing profile (Weekdays)", 1, 660)
        self.widget_list.append(prof_snow1_widget)
        prof_snow2_widget = TemplateWidget(self.profsheet, self.output_prof, "Snow clearing profile (Weekends)", 1, 660)
        self.widget_list.append(prof_snow2_widget)
        heat_widget = TemplateWidget(self.heatsheet, self.output_heat, "Modelling anthropogenic heat flux", None, 661)
        self.widget_list.append(heat_widget)
        prof_energy1_widget = TemplateWidget(self.profsheet, self.output_prof, "Energy use profile (Weekdays)", 2, 661)
        self.widget_list.append(prof_energy1_widget)
        prof_energy2_widget = TemplateWidget(self.profsheet, self.output_prof, "Energy use profile (Weekends)", 3, 662)
        self.widget_list.append(prof_energy2_widget)
        irr_widget = TemplateWidget(self.irrsheet, self.output_irr, "Modelling irrigation", None, 660)
        self.widget_list.append(irr_widget)
        prof_wateruse1_widget = TemplateWidget(self.profsheet, self.output_prof,
                                               "Water use profile (Manual irrigation, Weekdays)", 1, 660)
        self.widget_list.append(prof_wateruse1_widget)
        prof_wateruse2_widget = TemplateWidget(self.profsheet, self.output_prof,
                                               "Water use profile (Manual irrigation, Weekends)", 1, 660)
        self.widget_list.append(prof_wateruse2_widget)
        prof_wateruse3_widget = TemplateWidget(self.profsheet, self.output_prof,
                                               "Water use profile (Automatic irrigation, Weekdays)", 1, 660)
        self.widget_list.append(prof_wateruse3_widget)
        prof_wateruse4_widget = TemplateWidget(self.profsheet, self.output_prof,
                                               "Water use profile (Automatic irrigation, Weekends)", 1, 660)
        self.widget_list.append(prof_wateruse4_widget)

        paved_tab.Layout.addWidget(imp_paved_widget)

        buildings_tab.Layout.addWidget(imp_buildings_widget)

        evergreen_tab.Layout.addWidget(veg_evergreen_widget)

        decidious_tab.Layout.addWidget(veg_decidious_widget)

        grass_tab.Layout.addWidget(veg_grass_widget)

        baresoil_tab.Layout.addWidget(imp_baresoil_widget)

        water_tab.Layout.addWidget(water_widget)

        conductance_tab.Layout.addWidget(conductance_widget)

        snow_tab.Layout.addWidget(snow_widget)
        snow_tab.Layout2.addWidget(prof_snow1_widget)
        snow_tab.Layout2.addWidget(prof_snow2_widget)

        anthro_tab.Layout.addWidget(heat_widget)

        energy_tab.Layout.addWidget(prof_energy1_widget)
        energy_tab.Layout.addWidget(prof_energy2_widget)

        irrigation_tab.Layout.addWidget(irr_widget)

        wateruse_tab.Layout.addWidget(prof_wateruse1_widget)
        wateruse_tab.Layout.addWidget(prof_wateruse2_widget)
        wateruse_tab.Layout2.addWidget(prof_wateruse3_widget)
        wateruse_tab.Layout2.addWidget(prof_wateruse4_widget)

        self.dlg.tabWidget.addTab(main_tab, "Main settings")
        self.dlg.tabWidget.addTab(paved_tab, "Paved")
        self.dlg.tabWidget.addTab(buildings_tab, "Building")
        self.dlg.tabWidget.addTab(evergreen_tab, "Evergreen")
        self.dlg.tabWidget.addTab(decidious_tab, "Decidious")
        self.dlg.tabWidget.addTab(grass_tab, "Grass")
        self.dlg.tabWidget.addTab(baresoil_tab, "Bare Soil")
        self.dlg.tabWidget.addTab(water_tab, "Water")
        self.dlg.tabWidget.addTab(conductance_tab, "Conductance")
        self.dlg.tabWidget.addTab(snow_tab, "Snow")
        self.dlg.tabWidget.addTab(anthro_tab, "Anthropogenic")
        self.dlg.tabWidget.addTab(energy_tab, "Energy")
        self.dlg.tabWidget.addTab(irrigation_tab, "Irrigation")
        self.dlg.tabWidget.addTab(wateruse_tab, "Water Use")

        for widget in self.widget_list:
            widget.setup_widget()
            widget.make_edits_signal.connect(self.make_edits)
            widget.edit_mode_signal.connect(self.edit_mode)
            widget.cancel_edits_signal.connect(self.cancel_edits)

    def setup_tabs_outdated(self):
        self.dlg.tabWidget.clear()

        main_tab = MainTab()
        self.setup_maintab(main_tab)

        paved_tab = PavedTab()
        buildings_tab = BuildingsTab()
        baresoil_tab = BareSoilTab()
        evergreen_tab = EvergreenTab()
        decidious_tab = DecidiousTab()
        grass_tab = GrassTab()
        water_tab = WaterTab()
        conductance_tab = ConductanceTab()
        snow_tab = SnowTab()
        anthro_tab = AnthroTab()
        energy_tab = EnergyTab()
        irrigation_tab = IrrigationTab()
        wateruse_tab = WaterUseTab()

        conductance_widget = TemplateWidget()
        heat_widget = TemplateWidget()
        imp_paved_widget = TemplateWidget()
        imp_buildings_widget = TemplateWidget()
        irr_widget = TemplateWidget()
        imp_baresoil_widget = TemplateWidget()
        prof_snow1_widget = TemplateWidget()
        prof_snow2_widget = TemplateWidget()
        prof_energy1_widget = TemplateWidget()
        prof_energy2_widget = TemplateWidget()
        prof_wateruse1_widget = TemplateWidget()
        prof_wateruse2_widget = TemplateWidget()
        prof_wateruse3_widget = TemplateWidget()
        prof_wateruse4_widget = TemplateWidget()
        snow_widget = TemplateWidget()
        water_widget = TemplateWidget()
        veg_evergreen_widget = TemplateWidget()
        veg_decidious_widget = TemplateWidget()
        veg_grass_widget = TemplateWidget()

        paved_tab.Layout.addWidget(imp_paved_widget)

        buildings_tab.Layout.addWidget(imp_buildings_widget)

        baresoil_tab.Layout.addWidget(imp_baresoil_widget)

        evergreen_tab.Layout.addWidget(veg_evergreen_widget)

        decidious_tab.Layout.addWidget(veg_decidious_widget)

        grass_tab.Layout.addWidget(veg_grass_widget)

        water_tab.Layout.addWidget(water_widget)

        conductance_tab.Layout.addWidget(conductance_widget)

        snow_tab.Layout.addWidget(snow_widget)
        snow_tab.Layout2.addWidget(prof_snow1_widget)
        snow_tab.Layout2.addWidget(prof_snow2_widget)

        anthro_tab.Layout.addWidget(heat_widget)

        energy_tab.Layout.addWidget(prof_energy1_widget)
        energy_tab.Layout.addWidget(prof_energy2_widget)

        irrigation_tab.Layout.addWidget(irr_widget)

        wateruse_tab.Layout.addWidget(prof_wateruse1_widget)
        wateruse_tab.Layout.addWidget(prof_wateruse2_widget)
        wateruse_tab.Layout2.addWidget(prof_wateruse3_widget)
        wateruse_tab.Layout2.addWidget(prof_wateruse4_widget)

        self.dlg.tabWidget.addTab(main_tab, "Main settings")
        self.dlg.tabWidget.addTab(paved_tab, "Paved")
        self.dlg.tabWidget.addTab(buildings_tab, "Building")
        self.dlg.tabWidget.addTab(baresoil_tab, "Bare Soil")
        self.dlg.tabWidget.addTab(evergreen_tab, "Evergreen")
        self.dlg.tabWidget.addTab(decidious_tab, "Decidious")
        self.dlg.tabWidget.addTab(grass_tab, "Grass")
        self.dlg.tabWidget.addTab(water_tab, "Water")
        self.dlg.tabWidget.addTab(conductance_tab, "Conductance")
        self.dlg.tabWidget.addTab(snow_tab, "Snow")
        self.dlg.tabWidget.addTab(anthro_tab, "Anthropogenic")
        self.dlg.tabWidget.addTab(energy_tab, "Energy")
        self.dlg.tabWidget.addTab(irrigation_tab, "Irrigation")
        self.dlg.tabWidget.addTab(wateruse_tab, "Water Use")

        self.setup_widget(imp_paved_widget, self.impsheet, self.output_nonveg, "Paved surface characteristics", 1, 661)

        self.setup_widget(imp_buildings_widget, self.impsheet, self.output_nonveg,
                          "Building surface characteristics", 2, 662)

        self.setup_widget(veg_evergreen_widget, self.vegsheet, self.output_veg, "Evergreen surface characteristics", 3,
                          661)

        self.setup_widget(veg_decidious_widget, self.vegsheet, self.output_veg, "Decidious surface characteristics", 4,
                          662)

        self.setup_widget(veg_grass_widget, self.vegsheet, self.output_veg, "Grass surface characteristics", 5, 663)

        self.setup_widget(imp_baresoil_widget, self.impsheet, self.output_nonveg,
                          "Bare soil surface characteristics", 6, 663)

        self.setup_widget(water_widget, self.watersheet, self.output_water, "Water surface characteristics", None, 661)

        self.setup_widget(conductance_widget, self.condsheet, self.output_cond, "Surface conductance parameters", None,
                          100)

        self.setup_widget(snow_widget, self.snowsheet, self.output_snow, "Snow surface characteristics", None, 660)

        self.setup_widget(prof_snow1_widget, self.profsheet, self.output_prof, "Snow clearing profile (Weekdays)", 1)

        self.setup_widget(prof_snow2_widget, self.profsheet, self.output_prof, "Snow clearing profile (Weekends)", 2)

        self.setup_widget(heat_widget, self.heatsheet, self.output_heat, "Modelling anthropogenic heat flux")

        self.setup_widget(prof_energy1_widget, self.profsheet, self.output_prof, "Energy use profile (Weekdays)", 3)

        self.setup_widget(prof_energy2_widget, self.profsheet, self.output_prof, "Energy use profile (Weekends)", 4)

        self.setup_widget(irr_widget, self.irrsheet, self.output_irr, "Modelling irrigation")

        self.setup_widget(prof_wateruse1_widget, self.profsheet, self.output_prof,
                          "Water use profile (Manual irrigation, Weekdays)", 5)

        self.setup_widget(prof_wateruse2_widget, self.profsheet, self.output_prof,
                          "Water use profile (Manual irrigation, Weekends)", 6)

        self.setup_widget(prof_wateruse3_widget, self.profsheet, self.output_prof,
                          "Water use profile (Automatic irrigation, Weekdays)", 7)

        self.setup_widget(prof_wateruse4_widget, self.profsheet, self.output_prof,
                          "Water use profile (Automatic irrigation, Weekends)", 8)

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

        self.layerComboManagerPolygrid = VectorLayerCombo(widget.comboBox_Polygrid)
        self.fieldgen = VectorLayerCombo(widget.comboBox_Polygrid, initLayer="", options={"geomType": QGis.Polygon})
        self.layerComboManagerPolyField = FieldCombo(widget.comboBox_Field, self.fieldgen, initField="")

        self.pop_density = FieldCombo(widget.comboBox_popdens, self.fieldgen, initField="")
        self.wall_area = FieldCombo(widget.comboBox_wallArea, self.fieldgen, initField="")

        self.LCF_Paved = FieldCombo(widget.LCF_Paved, self.fieldgen, initField="")
        self.LCF_Buildings = FieldCombo(widget.LCF_Buildings, self.fieldgen, initField="")
        self.LCF_Evergreen = FieldCombo(widget.LCF_Evergreen, self.fieldgen, initField="")
        self.LCF_Decidious = FieldCombo(widget.LCF_Decidious, self.fieldgen, initField="")
        self.LCF_Grass = FieldCombo(widget.LCF_Grass, self.fieldgen, initField="")
        self.LCF_Baresoil = FieldCombo(widget.LCF_Baresoil, self.fieldgen, initField="")
        self.LCF_Water = FieldCombo(widget.LCF_Water, self.fieldgen, initField="")

        self.IMP_mean_height = FieldCombo(widget.IMP_mean, self.fieldgen, initField="")
        self.IMP_z0 = FieldCombo(widget.IMP_z0, self.fieldgen, initField="")
        self.IMP_zd = FieldCombo(widget.IMP_zd, self.fieldgen, initField="")
        self.IMP_fai = FieldCombo(widget.IMP_fai, self.fieldgen, initField="")

        self.IMPveg_mean_height_dec = FieldCombo(widget.IMPveg_mean_dec, self.fieldgen, initField="")
        self.IMPveg_mean_height_eve = FieldCombo(widget.IMPveg_mean_eve, self.fieldgen, initField="")
        self.IMPveg_fai_dec = FieldCombo(widget.IMPveg_fai_dec, self.fieldgen, initField="")
        self.IMPveg_fai_eve = FieldCombo(widget.IMPveg_fai_eve, self.fieldgen, initField="")

        widget.pushButtonImportLCF.clicked.connect(lambda: self.set_LCFfile_path(widget))
        widget.pushButtonImportIMPVeg.clicked.connect(lambda: self.set_IMPvegfile_path(widget))
        widget.pushButtonImportIMPBuild.clicked.connect(lambda: self.set_IMPfile_path(widget))
        widget.pushButtonImportMet.clicked.connect(lambda: self.set_metfile_path(widget))
        widget.pushButtonImportLUF.clicked.connect(lambda: self.set_LUFfile_path(widget))

        widget.spinBoxStartDLS.valueChanged.connect(lambda: self.start_DLS_changed(widget.spinBoxStartDLS.value()))
        widget.spinBoxEndDLS.valueChanged.connect(lambda: self.end_DLS_changed(widget.spinBoxEndDLS.value()))

    def hide_show_LCF(self, widget):
        if widget.LCF_checkBox.isChecked():
            self.LCF_from_file = False
            widget.LCF_Frame.show()
            widget.pushButtonImportLCF.hide()
            widget.textInputLCFData.hide()
            #self.dlg.adjustSize()
        else:
            self.LCF_from_file = True
            widget.LCF_Frame.hide()
            widget.pushButtonImportLCF.show()
            widget.textInputLCFData.show()
            #self.dlg.adjustSize()

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
            widget.checkBox_files.hide()
            widget.pushButtonImportIMPVeg_eve.hide()
            widget.pushButtonImportIMPVeg_dec.hide()
        else:
            self.IMPveg_from_file = True
            widget.IMPveg_Frame.hide()
            widget.pushButtonImportIMPVeg.show()
            widget.textInputIMPVegData.show()
            widget.checkBox_files.show()
            widget.pushButtonImportIMPVeg_eve.show()
            widget.pushButtonImportIMPVeg_dec.show()

    def LUF_file(self, widget):
        if widget.LUF_checkBox.isChecked():
            self.land_use_info = True
            self.land_use_from_file = True
            widget.pushButtonImportLUF.setEnabled(1)
        else:
            self.land_use_info = False
            self.land_use_from_file = False
            widget.pushButtonImportLUF.setEnabled(0)

    def enable_wall_area(self, widget):
        if widget.WallArea_checkBox.isChecked():
            self.wall_area_info = True
            widget.comboBox_wallArea.setEnabled(1)
        else:
            self.wall_area_info = False
            widget.comboBox_wallArea.setEnabled(0)

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
                #self.setup_image(widget, sheet, row)
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
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
            pass

    def setup_buttons(self, widget, outputfile, sheet, lineedit_list, code=None):
        widget.editButton.clicked.connect(lambda: self.edit_mode(widget, lineedit_list))
        widget.cancelButton.clicked.connect(lambda: self.cancel_edits(widget, lineedit_list))
        if code is None:
            widget.changeButton.clicked.connect(lambda: self.make_edits(widget, outputfile, sheet, lineedit_list))
        else:
            widget.changeButton.clicked.connect(lambda: self.make_edits(widget, outputfile, sheet, lineedit_list,
                                                                        code))

    def fill_combobox(self, widget):
        poly = self.layerComboManagerPolygrid.getLayer()
        if poly is None:
            QMessageBox.information(None, "Error", "No polygon grid added in main settings yet")
            widget.checkBox.setCheckState(0)
        else:
            FieldCombo(widget.comboBox_uniquecodes, self.fieldgen, initField="")

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

    #def make_edits(self, widget, outputfile, sheet, lineedit_list, code=None):
    def make_edits(self, outputfile, sheet, lineedit_list, code=None):

        if code is None:
            self.edit_file(outputfile, sheet, lineedit_list)
        else:
            self.edit_file(outputfile, sheet, lineedit_list, code)

        self.update_sheets()
        #if code is None:
        #    self.update_combobox(widget, sheet)
        #else:
        #    self.update_combobox(widget, sheet, code)
        current_index = self.dlg.tabWidget.currentIndex()
        self.setup_tabs()
        self.dlg.tabWidget.setCurrentIndex(current_index)

        for index in range(0, self.dlg.tabWidget.count()):
            if index == self.dlg.tabWidget.currentIndex():
                pass
            else:
                self.dlg.tabWidget.setTabEnabled(index, True)
        # for x in range(0, len(lineedit_list)):
        #     lineedit_list[x].setEnabled(0)
        # widget.editButton.setEnabled(1)
        # widget.changeButton.setEnabled(0)
        # widget.cancelButton.setEnabled(0)
        self.isEditable = False
        QMessageBox.information(None, "Complete", "Your entry has been added")

    def edit_file(self, outputfile, sheet, lineedit_list, code=None):
        try:
            wb = copy(self.data)
            wrote_line = False
            wrote_excel = False
            file_path = self.output_path + outputfile
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
                                    print string_to_print
                                    print line,
                                    wrote_line = True
                                else:
                                    print line,
                            else:
                                print line,
                        photo = QMessageBox.question(None, "Photo",
                                                     "Would you like to add a url to a suitable photo of the area?",
                                                     QMessageBox.Yes | QMessageBox.No)
                        if photo == QMessageBox.Yes:
                            self.photo_dialog.show()
                            result = self.photo_dialog.exec_()
                            if result:
                                try:
                                    url = self.photo_dialog.lineEdit.text()
                                    QgsMessageLog.logMessage("URL: " + str(url), level=QgsMessageLog.CRITICAL)
                                    req = urllib2.Request(str(url))
                                    try:
                                        resp = urllib2.urlopen(req)
                                    except urllib2.HTTPError as e:
                                        QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
                                        QMessageBox.information(None, "Error", "Couldn't reach url")
                                        str_list.append('')
                                    except urllib2.URLError as e:
                                        QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
                                        QMessageBox.information(None, "Error", "Couldn't reach url")
                                        str_list.append('')
                                    else:
                                        str_list.append(str(url))
                                except ValueError as e:
                                    QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
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
                        #if code is None:
                            #self.update_combobox(widget, sheet)
                        #else:
                            #self.update_combobox(widget, sheet, code)
                        self.clear_layout()
                    else:
                        QMessageBox.critical(None, "Error", "Could not find the file:" + outputfile)
                        self.clear_layout()
            else:
                #QMessageBox.critical(None, "Error", "No changes has been made")
                self.clear_layout()
        except IOError as e:
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
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
        self.heatsheet = self.data.sheet_by_name("SUEWS_AnthropogenicHeat")
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
        if url == '':
            widget.Image.clear()
        else:
            req = urllib2.Request(str(url))
            try:
                resp = urllib2.urlopen(req)
            except urllib2.HTTPError as e:
                if e.code == 404:
                    QgsMessageLog.logMessage("Image URL encountered a 404 problem", level=QgsMessageLog.CRITICAL)
                    widget.Image.clear()
                else:
                    QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
                    widget.Image.clear()
            except urllib2.URLError as e:
                QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
                widget.Image.clear()
            else:
                data = resp.read()
                #data = urllib.urlopen(str(url)).read()

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
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
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
        widget.textInputLCFData.setText(self.LCFfile_path)

    def set_IMPfile_path(self, widget):
        self.IMPfile_path = self.fileDialog.getOpenFileName()
        widget.textInputIMPData.setText(self.IMPfile_path)

    def set_IMPvegfile_path(self, widget):
        self.IMPvegfile_path = self.fileDialog.getOpenFileName()
        widget.textInputIMPVegData.setText(self.IMPvegfile_path)

    def set_metfile_path(self, widget):
        self.Metfile_path = self.fileDialog.getOpenFileName()
        widget.textInputMetData.setText(self.Metfile_path)

    def set_LUFfile_path(self, widget):
        self.land_use_file_path = self.fileDialog.getOpenFileName()
        widget.textInputLUFData.setText(self.land_use_file_path)

    def start_DLS_changed(self, value):
        self.start_DLS = value
        QgsMessageLog.logMessage(str(self.start_DLS), level=QgsMessageLog.CRITICAL)

    def end_DLS_changed(self, value):
        self.end_DLS = value
        QgsMessageLog.logMessage(str(self.end_DLS), level=QgsMessageLog.CRITICAL)

    def generate(self):

        #Remove before release
        #self.output_dir = "C:/test"

        if self.output_dir is None:
                QMessageBox.critical(None, "Error", "No output directory selected")
                return

        #empty_line = []
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
                #empty_line.append("empty")

        lines_to_write.append(nbr_header)
        lines_to_write.append(header)

        poly = self.layerComboManagerPolygrid.getLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return

        poly_field = self.layerComboManagerPolyField.getFieldName()
        if poly_field is None:
            QMessageBox.critical(None, "Error", "An attribute filed with unique fields must be selected")
            return

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        id_index = vlayer.fieldNameIndex(poly_field)

        for feature in vlayer.getFeatures():
            #QgsMessageLog.logMessage(str(feature.attribute(poly_field)), level=QgsMessageLog.CRITICAL)

            new_line = []
            #new_line = empty_line
            print_line = True
            feat_id = int(feature.attribute(poly_field))
            code = "Grid"
            index = self.find_index(code)
            new_line.insert(index, str(feat_id))

            year = None
            year2 = None

            #REMOVE BEFORE RELEASE
            #self.Metfile_path = "C:/test/Kc_data.txt"
            #REMOVE BEFORE RELEASE

            if self.Metfile_path is None:
                QMessageBox.critical(None, "Error", "Meteorological data file has not been provided,"
                                                    " please check the main tab")
                return
            elif os.path.isfile(self.Metfile_path):
                with open(self.Metfile_path) as file:
                    next(file)
                    for line in file:
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
                QMessageBox.critical(None, "Error", "Could not find the file containing meteorological data")
                return

            code = "Year"
            index = self.find_index(code)
            new_line.insert(index, str(year))
            code = "StartDLS"
            index = self.find_index(code)
            new_line.insert(index, str(self.start_DLS))
            code = "EndDLS"
            index = self.find_index(code)
            new_line.insert(index, str(self.end_DLS))

            old_cs = osr.SpatialReference()
            old_cs_area = vlayer.crs()
            vlayer_ref = vlayer.crs().toWkt()
            old_cs.ImportFromWkt(vlayer_ref)

            wgs84_wkt = """
            GEOGCS["WGS 84",
                DATUM["WGS_1984",
                    SPHEROID["WGS 84",6378137,298.257223563,
                        AUTHORITY["EPSG","7030"]],
                    AUTHORITY["EPSG","6326"]],
                PRIMEM["Greenwich",0,
                    AUTHORITY["EPSG","8901"]],
                UNIT["degree",0.01745329251994328,
                    AUTHORITY["EPSG","9122"]],
                AUTHORITY["EPSG","4326"]]"""

            new_cs = osr.SpatialReference()
            new_cs.ImportFromWkt(wgs84_wkt)

            area_wkt = """
            GEOCCS["WGS 84 (geocentric)",
                DATUM["World Geodetic System 1984",
                    SPHEROID["WGS 84",6378137.0,298.257223563,
                        AUTHORITY["EPSG","7030"]],
                    AUTHORITY["EPSG","6326"]],
                PRIMEM["Greenwich",0.0,
                    AUTHORITY["EPSG","8901"]],
                UNIT["m",1.0],
                AXIS["Geocentric X",OTHER],
                AXIS["Geocentric Y",EAST],
                AXIS["Geocentric Z",NORTH],
                AUTHORITY["EPSG","4328"]]"""

            new_cs_area = QgsCoordinateReferenceSystem(area_wkt)

            transform = osr.CoordinateTransformation(old_cs, new_cs)

            centroid = feature.geometry().centroid().asPoint()
            #areatransform = QgsCoordinateTransform(old_cs_area, new_cs_area)
            #feature.geometry().transform(areatransform)
            area = feature.geometry().area()
            map_units = vlayer.crs().mapUnits()

            if map_units == 0:
                hectare = area * 0.0001

            elif map_units == 1:
                hectare = area/107640

            elif map_units == 2:
                hectare = area

            else:
                QMessageBox.critical(None, "Error", "Could not identify the map units of the polygon layer coordinate "
                                                    "reference system")
                return

            lonlat = transform.TransformPoint(centroid.x(), centroid.y())
            code = "lat"
            index = self.find_index(code)
            new_line.insert(index, str(lonlat[1]))
            code = "lng"
            index = self.find_index(code)
            new_line.insert(index, str(lonlat[0]))
            code = "SurfaceArea"
            index = self.find_index(code)
            new_line.insert(index, str(hectare))

            altitude = 0
            day = 1
            hour = 0
            minute = 0

            code = "Alt"
            index = self.find_index(code)
            new_line.insert(index, str(altitude))
            code = "id"
            index = self.find_index(code)
            new_line.insert(index, str(day))
            code = "ih"
            index = self.find_index(code)
            new_line.insert(index, str(hour))
            code = "imin"
            index = self.find_index(code)
            new_line.insert(index, str(minute))

            #TA BORT INNAN RELEASE
            #self.LCFfile_path = "C:/test/barb_LCFG_isotropic.txt"
            if self.LCF_from_file:
                found_LCF_line = False

                if self.LCFfile_path is None:
                    QMessageBox.critical(None, "Error", "Land cover fractions file has not been provided,"
                                                        " please check the main tab")
                    return
                elif os.path.isfile(self.LCFfile_path):
                    with open(self.LCFfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                LCF_paved = split[1]
                                LCF_buildings = split[2]
                                LCF_evergreen = split[3]
                                LCF_decidious = split[4]
                                LCF_grass = split[5]
                                LCF_baresoil = split[6]
                                LCF_water = split[7]
                                found_LCF_line = True
                                break
                        if not found_LCF_line:
                                #LCF_paved = -999
                                #LCF_buildings = -999
                                #LCF_evergreen = -999
                                #LCF_decidious = -999
                                #LCF_grass = -999
                                #LCF_baresoil = -999
                                #LCF_water = -999
                                print_line = False
                else:
                    QMessageBox.critical(None, "Error", "Could not find the file containing land cover fractions")
                    return
            else:
                LCF_paved = feature.attribute(self.LCF_Paved.getFieldName())
                LCF_buildings = feature.attribute(self.LCF_Buildings.getFieldName())
                LCF_evergreen = feature.attribute(self.LCF_Evergreen.getFieldName())
                LCF_decidious = feature.attribute(self.LCF_Decidious.getFieldName())
                LCF_grass = feature.attribute(self.LCF_Grass.getFieldName())
                LCF_baresoil = feature.attribute(self.LCF_Baresoil.getFieldName())
                LCF_water = feature.attribute(self.LCF_Water.getFieldName())

            code = "Fr_Paved"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_paved))
            code = "Fr_Bldgs"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_buildings))
            code = "Fr_EveTr"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_evergreen))
            code = "Fr_DecTr"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_decidious))
            code = "Fr_Grass"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_grass))
            code = "Fr_Bsoil"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_baresoil))
            code = "Fr_Water"
            index = self.find_index(code)
            new_line.insert(index, str(LCF_water))

            irrFr_EveTr = 0
            irrFr_DecTr = 0
            irrFr_Grass = 0

            code = "IrrFr_EveTr"
            index = self.find_index(code)
            new_line.insert(index, str(irrFr_EveTr))
            code = "IrrFr_DecTr"
            index = self.find_index(code)
            new_line.insert(index, str(irrFr_DecTr))
            code = "IrrFr_Grass"
            index = self.find_index(code)
            new_line.insert(index, str(irrFr_Grass))

            #TA BORT INNAN RELEASE
            #self.IMPfile_path = "C:/test/barb_IMPGrid_isotropic.txt"
            if self.IMP_from_file:
                found_IMP_line = False

                if self.IMPfile_path is None:
                    QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
                                                        " please check the main tab")
                    return
                elif os.path.isfile(self.IMPfile_path):
                    with open(self.IMPfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                IMP_heights_mean = split[3]
                                IMP_z0 = split[6]
                                IMP_zd = split[7]
                                IMP_fai = split[2]
                                found_LCF_line = True
                                break
                        if not found_LCF_line:
                                #IMP_heights_mean = -999
                                #IMP_z0 = -999
                                #IMP_zd = -999
                                #IMP_fai = -999
                                print_line = False
                else:
                    QMessageBox.critical(None, "Error", "Could not find the file containing building morphology")
                    return
            else:
                IMP_heights_mean = feature.attribute(self.IMP_mean_height.getFieldName())
                IMP_z0 = feature.attribute(self.IMP_z0.getFieldName())
                IMP_zd = feature.attribute(self.IMP_zd.getFieldName())
                IMP_fai = feature.attribute(self.IMP_fai.getFieldName())


            #REMOVE BEFORE RELEASE
            #self.IMPvegfile_path = "C:/test/barbveg_IMPGrid_isotropic.txt"

            found_IMPveg_line = False
            if self.IMPveg_from_file:
                if self.IMPvegfile_path is None:
                    QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
                                                        " please check the main tab")
                    return
                elif os.path.isfile(self.IMPvegfile_path):
                    with open(self.IMPvegfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                IMPveg_heights_mean_eve = split[3]
                                IMPveg_heights_mean_dec = split[3]
                                IMPveg_fai_eve = split[2]
                                IMPveg_fai_dec = split[2]
                                found_LCF_line = True
                                break
                        if not found_LCF_line:
                                #IMPveg_heights_mean_eve = -999
                                #IMPveg_heights_mean_dec = -999
                                #IMPveg_fai_eve = -999
                                #IMPveg_fai_dec = -999
                                print_line = False
                else:
                    QMessageBox.critical(None, "Error", "Could not find the file containing building morphology")
                    return
            else:
                IMPveg_heights_mean_eve = feature.attribute(self.IMPveg_mean_height_eve.getFieldName())
                IMPveg_heights_mean_dec = feature.attribute(self.IMPveg_mean_height_dec.getFieldName())
                IMPveg_fai_eve = feature.attribute(self.IMPveg_fai_eve.getFieldName())
                IMPveg_fai_dec = feature.attribute(self.IMPveg_fai_dec.getFieldName())

            code = "H_Bldgs"
            index = self.find_index(code)
            new_line.insert(index, str(IMP_heights_mean))
            code = "H_EveTr"
            index = self.find_index(code)
            new_line.insert(index, str(IMPveg_heights_mean_eve))
            code = "H_DecTr"
            index = self.find_index(code)
            new_line.insert(index, str(IMPveg_heights_mean_dec))
            code = "z0"
            index = self.find_index(code)
            new_line.insert(index, str(IMP_z0))
            code = "zd"
            index = self.find_index(code)
            new_line.insert(index, str(IMP_zd))
            code = "FAI_Bldgs"
            index = self.find_index(code)
            new_line.insert(index, str(IMP_fai))
            code = "FAI_EveTr"
            index = self.find_index(code)
            new_line.insert(index, str(IMPveg_fai_eve))
            code = "FAI_DecTr"
            index = self.find_index(code)
            new_line.insert(index, str(IMPveg_fai_dec))

            if self.pop_density is not None:
                pop_density_day = feature.attribute(self.pop_density.getFieldName())
                pop_density_night = feature.attribute(self.pop_density.getFieldName())
            else:
                pop_density_day = -999
                pop_density_night = -999

            code = "PopDensDay"
            index = self.find_index(code)
            new_line.insert(index, str(pop_density_day))
            code = "PopDensNight"
            index = self.find_index(code)
            new_line.insert(index, str(pop_density_night))

            for widget in self.widget_list:
                if widget.get_checkstate():
                    code_field = str(widget.comboBox_uniquecodes.currentText())
                    try:
                        code = int(feature.attribute(code_field))
                    except ValueError as e:
                        QMessageBox.critical(None, "Error", "Unique code field for widget " + widget.get_title() +
                                             " should only contain integers")
                        return
                    match = widget.comboBox.findText(str(code))
                    if match == -1:
                        QMessageBox.critical(None, "Error", "Unique code field for widget " + widget.get_title() +
                                             " contains one or more codes with no match in site library")
                        return
                    index = widget.get_sitelistpos()
                    new_line.insert(index - 1, str(code))

                else:
                    code = widget.get_combo_text()
                    index = widget.get_sitelistpos()
                    new_line.insert(index - 1, str(code))

            LUMPS_drate = 0.25
            LUMPS_Cover = 1
            LUMPS_MaxRes = 10
            NARP_Trans = 1

            code = "LUMPS_DrRate"
            index = self.find_index(code)
            new_line.insert(index, str(LUMPS_drate))
            code = "LUMPS_Cover"
            index = self.find_index(code)
            new_line.insert(index, str(LUMPS_Cover))
            code = "LUMPS_MaxRes"
            index = self.find_index(code)
            new_line.insert(index, str(LUMPS_MaxRes))
            code = "NARP_Trans"
            index = self.find_index(code)
            new_line.insert(index, str(NARP_Trans))

            #for x in xrange(7, 19):
                #code = self.widget_list[x].get_combo_text()
                #new_line.append(str(code))

            flow_change = 0
            RunoffToWater = 0.1
            PipeCap = 100
            GridConn1of8 = 0
            Fraction1of8 = 0
            GridConn2of8 = 0
            Fraction2of8 = 0
            GridConn3of8 = 0
            Fraction3of8 = 0
            GridConn4of8 = 0
            Fraction4of8 = 0
            GridConn5of8 = 0
            Fraction5of8 = 0
            GridConn6of8 = 0
            Fraction6of8 = 0
            GridConn7of8 = 0
            Fraction7of8 = 0
            GridConn8of8 = 0
            Fraction8of8 = 0

            code = "FlowChange"
            index = self.find_index(code)
            new_line.insert(index, flow_change)
            code = "RunoffToWater"
            index = self.find_index(code)
            new_line.insert(index, RunoffToWater)
            code = "PipeCapacity"
            index = self.find_index(code)
            new_line.insert(index, PipeCap)
            code = "GridConnection1of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn1of8)
            code = "Fraction1of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction1of8)
            code = "GridConnection2of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn2of8)
            code = "Fraction2of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction2of8)
            code = "GridConnection3of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn3of8)
            code = "Fraction3of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction3of8)
            code = "GridConnection4of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn4of8)
            code = "Fraction4of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction4of8)
            code = "GridConnection5of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn5of8)
            code = "Fraction5of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction5of8)
            code = "GridConnection6of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn6of8)
            code = "Fraction6of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction6of8)
            code = "GridConnection7of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn7of8)
            code = "Fraction7of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction7of8)
            code = "GridConnection8of8"
            index = self.find_index(code)
            new_line.insert(index, GridConn8of8)
            code = "Fraction8of8"
            index = self.find_index(code)
            new_line.insert(index, Fraction8of8)

            WhitinGridPav = 661
            WhitinGridBldg = 662
            WhitinGridEve = 663
            WhitinGridDec = 664
            WhitinGridGrass = 665
            WhitinGridUnmanBsoil = 666
            WhitinGridWaterCode = 667

            code = "WithinGridPavedCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridPav)
            code = "WithinGridBldgsCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridBldg)
            code = "WithinGridEveTrCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridEve)
            code = "WithinGridDecTrCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridDec)
            code = "WithinGridGrassCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridGrass)
            code = "WithinGridUnmanBSoilCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridUnmanBsoil)
            code = "WithinGridWaterCode"
            index = self.find_index(code)
            new_line.insert(index, WhitinGridWaterCode)

            if self.wall_area_info:
                wall_area = feature.attribute(self.wall_area.getFieldName())
            else:
                wall_area = -999

            code = "wallarea"
            index = self.find_index(code)
            new_line.insert(index, wall_area)

            # TODO fix so that it optional
            if self.land_use_from_file:
                if self.land_use_file_path is None:
                    QMessageBox.critical(None, "Error", "Land use fractions file has not been provided,"
                                                        " please check the main tab")
                    return
                elif os.path.isfile(self.land_use_file_path):
                    with open(self.land_use_file_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                flub1 = split[1]
                                Code_LUbuilding1 = split[2]
                                flub2 = split[3]
                                Code_LUbuilding2 = split[4]
                                flub3 = split[5]
                                Code_LUbuilding3 = split[6]
                                flub4 = split[7]
                                Code_LUbuilding4 = split[8]
                                flub5 = split[7]
                                Code_LUbuilding5 = split[8]
                                fLUp1 = split[9]
                                Code_LUpaved1 = split[10]
                                fLUp2 = split[11]
                                Code_LUpaved2 = split[12]
                                fLUp3 = split[13]
                                Code_LUpaved3 = split[14]

                                found_LCF_line = True
                                break
                        if not found_LCF_line:
                                flub1 = -999
                                Code_LUbuilding1 = -999
                                flub2 = split[3]
                                Code_LUbuilding2 = -999
                                flub3 = split[5]
                                Code_LUbuilding3 = -999
                                flub4 = split[7]
                                Code_LUbuilding4 = -999
                                flub5 = split[7]
                                Code_LUbuilding5 = -999
                                fLUp1 = split[9]
                                Code_LUpaved1 = -999
                                fLUp2 = split[11]
                                Code_LUpaved2 = -999
                                fLUp3 = split[13]
                                Code_LUpaved3 = -999
                else:
                    QMessageBox.critical(None, "Error", "Could not find the file containing land use cover fractions")
                    return
            else:
                flub1 = -999
                Code_LUbuilding1 = -999
                flub2 = -999
                Code_LUbuilding2 = -999
                flub3 = -999
                Code_LUbuilding3 = -999
                flub4 = -999
                Code_LUbuilding4 = -999
                flub5 = -999
                Code_LUbuilding5 = -999
                fLUp1 = -999
                Code_LUpaved1 = -999
                fLUp2 = -999
                Code_LUpaved2 = -999
                fLUp3 = -999
                Code_LUpaved3 = -999

            code = "fLUb1"
            index = self.find_index(code)
            new_line.insert(index, flub1)
            code = "fLUb2"
            index = self.find_index(code)
            new_line.insert(index, flub2)
            code = "fLUb3"
            index = self.find_index(code)
            new_line.insert(index, flub3)
            code = "fLUb4"
            index = self.find_index(code)
            new_line.insert(index, flub4)
            code = "fLUb5"
            index = self.find_index(code)
            new_line.insert(index, flub5)
            code = "fLUp1"
            index = self.find_index(code)
            new_line.insert(index, fLUp1)
            code = "fLUp2"
            index = self.find_index(code)
            new_line.insert(index, fLUp2)
            code = "fLUp3"
            index = self.find_index(code)
            new_line.insert(index, fLUp3)
            code = "Code_LUbuilding1"
            index = self.find_index(code)
            new_line.insert(index, Code_LUbuilding1)
            code = "Code_LUbuilding2"
            index = self.find_index(code)
            new_line.insert(index, Code_LUbuilding2)
            code = "Code_LUbuilding3"
            index = self.find_index(code)
            new_line.insert(index, Code_LUbuilding3)
            code = "Code_LUbuilding4"
            index = self.find_index(code)
            new_line.insert(index, Code_LUbuilding4)
            code = "Code_LUbuilding5"
            index = self.find_index(code)
            new_line.insert(index, Code_LUbuilding5)
            code = "Code_LUpaved1"
            index = self.find_index(code)
            new_line.insert(index, Code_LUpaved1)
            code = "Code_LUpaved2"
            index = self.find_index(code)
            new_line.insert(index, Code_LUpaved2)
            code = "Code_LUpaved3"
            index = self.find_index(code)
            new_line.insert(index, Code_LUpaved3)

            new_line.append("!")

            #QgsMessageLog.logMessage(str(new_line), level=QgsMessageLog.CRITICAL)
            if print_line:
                lines_to_write.append(new_line)

        #QgsMessageLog.logMessage(str(lines_to_write), level=QgsMessageLog.CRITICAL)
        output_lines = []
        output_file = self.output_dir[0] + "/SUEWS_SiteSelect.txt"
        with open(output_file, 'w+') as ofile:
            for line in lines_to_write:
                string_to_print = ''
                for element in line:
                    string_to_print += str(element) + '\t'
                string_to_print += "\n"
                output_lines.append(string_to_print)
            output_lines.append("-9\n")
            output_lines.append("-9\n")
            ofile.writelines(output_lines)
            for input_file in self.output_file_list:
                try:
                    copyfile(self.output_path + input_file, self.output_dir[0] + "/" + input_file)
                except IOError as e:
                    QgsMessageLog.logMessage("Error copying output files with SUEWS_SiteSelect.txt: " + str(e), level=QgsMessageLog.CRITICAL)
            QMessageBox.information(None, "Complete", "File successfully created as SUEWS_SiteSelect.txt in Output "
                                                      "Folder: " + self.output_dir[0])

    def find_index(self, code):
        values = self.header_sheet.row_values(1)
        index = values.index(code)
        return index

    def unload_widget(self):
        self.dlg.tabWidget.clear()

    def run(self):
        self.output_dir = None
        self.LCFfile_path = None
        self.IMPfile_path = None
        self.IMPvegfile_path = None
        self.land_use_file_path = None
        #self.dlg.runButton.setEnabled(0)
        self.dlg.textOutput.clear()

        self.setup_tabs()

        self.dlg.show()
        #self.test_widget.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

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
        self.IMP_mean_height = None
        self.IMP_z0 = None
        self.IMP_zd = None
        self.IMP_fai = None
        self.IMPveg_mean_height_dec = None
        self.IMPveg_mean_height_eve = None
        self.IMPveg_fai_dec = None
        self.IMPveg_fai_eve = None
        self.wall_area = None

        # See if OK was pressed
        #if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            #pass
        #if self.isEditable:
            #self.placeholder()

        #for widget in self.widgetlist:
            #widget.comboBox.currentIndexChanged.disconnect()
            #widget.comboBox.clear()


    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = "http://www.urban-climate.net/umep/UMEP_Manual#PrePreprocessor:_SUEWS_Prepare"
        webbrowser.open_new_tab(url)