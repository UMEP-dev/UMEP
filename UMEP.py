# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UMEP
                                 A QGIS plugin
 UMEP
                              -------------------
        begin                : 2015-04-29
        git sha              : $Format:%H$
        copyright            : (C) 2015 by fredrikl@gvc.gu.se
        email                : Fredrik Lindberg
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from UMEP_dialog import UMEPDialog
from ShadowGenerator.shadow_generator import ShadowGenerator
from ImageMorphParam.image_morph_param import ImageMorphParam
from ImageMorphParmsPoint.imagemorphparmspoint_v1 import ImageMorphParmsPoint
from SkyViewFactorCalculator.svf_calculator import SkyViewFactorCalculator
from pydev import pydevd
import os.path
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass


class UMEP:
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
            'UMEP_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = UMEPDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&UMEP')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'UMEP')
        self.toolbar.setObjectName(u'UMEP')

        # Main menu
        self.UMEP_Menu = QMenu("UMEP")

        # First-order sub-menus
        self.Pre_Menu = QMenu("Pre-Processor")
        self.UMEP_Menu.addMenu(self.Pre_Menu)
        self.Pro_Menu = QMenu("Processor")
        self.UMEP_Menu.addMenu(self.Pro_Menu)
        self.Pos_Menu = QMenu("Post-Processor")
        self.UMEP_Menu.addMenu(self.Pos_Menu)
        self.Pos_Menu.setEnabled(False)
        self.About_Menu = QMenu("Help")
        self.UMEP_Menu.addMenu(self.About_Menu)

        # Sub-menus to Pre-processor
        self.SM_Menu = QMenu("Urban Morphology")
        self.Pre_Menu.addMenu(self.SM_Menu)
        self.MD_Menu = QMenu("Meteorological Data")
        self.Pre_Menu.addMenu(self.MD_Menu)
        self.UG_Menu = QMenu("Urban Geometry")
        self.Pre_Menu.addMenu(self.UG_Menu)
        self.ULC_Menu = QMenu("Urban Land Cover")
        self.Pre_Menu.addMenu(self.ULC_Menu)

        # Sub-actions to Surface Morphology
        self.IMCG_Action = QAction("Image Morphometric Calculator (Grid)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.IMCG_Action)
        self.IMCG_Action.triggered.connect(self.IMCG)
        self.IMCP_Action = QAction("Image Morphometric Calculator (Point)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.IMCP_Action)
        self.IMCP_Action.triggered.connect(self.IMCP)
        self.ULCUEBG_Action = QAction("Land Cover Fractions (Grid)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.ULCUEBG_Action)
        self.ULCUEBG_Action.setEnabled(False)
        self.ULCUEBP_Action = QAction("Land Cover Fractions (Point)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.ULCUEBP_Action)
        self.ULCUEBP_Action.setEnabled(False)

        # Sub-actions to Meteorological Data Preparation
        self.PED_Action = QAction("Prepare Existing Data", self.iface.mainWindow())
        self.MD_Menu.addAction(self.PED_Action)
        self.PED_Action.setEnabled(False)
        self.PFD_Action = QAction("Prepare Fictitious Data", self.iface.mainWindow())
        self.MD_Menu.addAction(self.PFD_Action)
        self.PFD_Action.setEnabled(False)

        # Sub-actions to Urban Geometry
        self.SVF_Action = QAction("Sky View Factor", self.iface.mainWindow())
        self.UG_Menu.addAction(self.SVF_Action)
        self.SVF_Action.triggered.connect(self.SVF)
        self.HW_Action = QAction("Height/Width Ratio", self.iface.mainWindow())
        self.UG_Menu.addAction(self.HW_Action)
        self.HW_Action.setEnabled(False)

        # Sub-menus to Processor
        self.OTC_Menu = QMenu("Outdoor Thermal Comfort")
        self.Pro_Menu.addMenu(self.OTC_Menu)
        self.UEB_Menu = QMenu("Urban Energy Balance")
        self.Pro_Menu.addMenu(self.UEB_Menu)
        self.SUN_Menu = QMenu("Solar radiation")
        self.Pro_Menu.addMenu(self.SUN_Menu)
        # self.NUHI_Action = QAction("Nocturnal Urban Heat Island", self.iface.mainWindow())
        # self.Pro_Menu.addAction(self.NUHI_Action)

        # Sub-menus to Outdoor Thermal Comfort
        self.PET_Action = QAction("Comfort Index (PET/UCTI)", self.iface.mainWindow())
        self.OTC_Menu.addAction(self.PET_Action)
        self.PET_Action.setEnabled(False)
        self.MRT_Action = QAction("Mean Radiant Temperature (SOLWEIG)", self.iface.mainWindow())
        self.OTC_Menu.addAction(self.MRT_Action)
        self.MRT_Action.setEnabled(False)
        self.PWS_Action = QAction("Pedestrian Wind Speed", self.iface.mainWindow())
        self.OTC_Menu.addAction(self.PWS_Action)
        self.PWS_Action.setEnabled(False)

        # Sub-menus to Urban Energy Balance
        self.QF_Action = QAction("Antropogenic heat (Qf) (LUCY)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.QF_Action)
        self.QF_Action.setEnabled(False)
        self.SUEWS_Action = QAction("Urban Energy Balance (SUEWS)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.SUEWS_Action)
        self.SUEWS_Action.setEnabled(False)
        self.LUMPS_Action = QAction("Urban Energy Balance (LUMPS)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.LUMPS_Action)
        self.LUMPS_Action.setEnabled(False)
        self.CBL_Action = QAction("UEB + CBL (BLUEWS/BLUMPS)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.CBL_Action)
        self.CBL_Action.setEnabled(False)

        # Sub-menus to Solar radiation
        self.SEBE_Action = QAction("Solar Energy on Building Envelopes (SEBE)", self.iface.mainWindow())
        self.SUN_Menu.addAction(self.SEBE_Action)
        self.SEBE_Action.setEnabled(False)
        self.DSP_Action = QAction("Daily Shadow Pattern", self.iface.mainWindow())
        self.SUN_Menu.addAction(self.DSP_Action)
        self.DSP_Action.triggered.connect(self.SH)

        # Sub-menus to About
        self.About_Action = QAction("About", self.iface.mainWindow())
        self.About_Menu.addAction(self.About_Action)
        self.About_Action.setEnabled(False)
        self.Manual_Action = QAction("Manual", self.iface.mainWindow())
        self.About_Menu.addAction(self.Manual_Action)
        self.Manual_Action.setEnabled(False)

        self.iface.mainWindow().menuBar().insertMenu(self.iface.firstRightStandardMenu().menuAction(), self.UMEP_Menu)

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
        return QCoreApplication.translate('UMEP', message)

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

        #if add_to_toolbar:
        #    self.toolbar.addAction(action)

        #if add_to_menu:
        #    self.iface.addPluginToMenu(
        #        self.menu,
        #        action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/UMEP/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'UMEP'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UMEP'),
                action)
            self.iface.removeToolBarIcon(action)
            self.iface.mainWindow().menuBar().removeAction(self.UMEP_Menu.menuAction())

    def SH(self):
        sg = ShadowGenerator(self.iface)
        sg.run()
        
    def IMCG(self):
        sg = ImageMorphParam(self.iface)
        sg.run()

    def IMCP(self):
        sg = ImageMorphParmsPoint(self.iface)
        # pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True) #used for debugging
        sg.run()

    def SVF(self):
        sg = SkyViewFactorCalculator(self.iface)
        sg.run()

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        self.dlg.exec_()


