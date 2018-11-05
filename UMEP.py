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
from __future__ import absolute_import
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QMenu, QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from .UMEP_dialog import UMEPDialog
from .MetdataProcessor.metdata_processor import MetdataProcessor
from .ShadowGenerator.shadow_generator import ShadowGenerator
from .SkyViewFactorCalculator.svf_calculator import SkyViewFactorCalculator
from .ImageMorphParam.image_morph_param import ImageMorphParam
from .ImageMorphParmsPoint.imagemorphparmspoint_v1 import ImageMorphParmsPoint
from .LandCoverFractionGrid.landcoverfraction_grid import LandCoverFractionGrid
from .LandCoverFractionPoint.landcover_fraction_point import LandCoverFractionPoint
from .LandCoverReclassifier.land_cover_reclassifier import LandCoverReclassifier
from .WallHeight.wall_height import WallHeight
from .TreeGenerator.tree_generator import TreeGenerator
from .FootprintModel.footprint_model import FootprintModel
from .LCZ_Converter.LCZ_converter import LCZ_test
from .UMEPDownloader.umep_downloader import UMEP_Data_Download
from .DSMGenerator.dsm_generator import DSMGenerator  # TODO: Working except for OSMImport
from .WATCHData.watch import WATCHData
# from .GreaterQF.greater_qf import GreaterQF  # TODO: Multiple changes required :Plugin blocker
from .ExtremeFinder.extreme_finder import ExtremeFinder
from .LucyQF.LQF import LQF  # TODO: Multiple changes required :Plugin blocker
from .SEBE.sebe import SEBE
from .SuewsSimple.suews_simple import SuewsSimple
from .SUEWSPrepare.suews_prepare import SUEWSPrepare
from .SUEWS.suews import SUEWS
from .SOLWEIG.solweig import SOLWEIG
from .BenchMarking.benchmarking import BenchMarking
# from .SEBEVisual.sun import Sun  # TODO: Not able to run 2to3 converter :Plugin blocker
from .SolweigAnalyzer.solweig_analyzer import SolweigAnalyzer
from .SUEWSAnalyzer.suews_analyzer import SUEWSAnalyzer
from .UMEP_about import UMEPDialogAbout
import os.path
import webbrowser

# Uncomment the section below if you want to debug in QGIS
# import sys
# sys.path.append('C:/OSGeo4W64/apps/Python27/Lib/site-packages/pydev')
# import pydevd


class UMEP(object):
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
        #self.toolbar = self.iface.addToolBar(u'UMEP')
        #self.toolbar.setObjectName(u'UMEP')

        # Main menu
        self.UMEP_Menu = QMenu("UMEP")

        # First-order sub-menus
        self.Pre_Menu = QMenu("Pre-Processor")
        self.UMEP_Menu.addMenu(self.Pre_Menu)
        self.Pro_Menu = QMenu("Processor")
        self.UMEP_Menu.addMenu(self.Pro_Menu)
        self.Pos_Menu = QMenu("Post-Processor")
        self.UMEP_Menu.addMenu(self.Pos_Menu)
        self.About_Menu = QMenu("Help")
        self.UMEP_Menu.addMenu(self.About_Menu)

        # Sub-menus and actions to Pre-processor
        self.MD_Menu = QMenu("Meteorological Data")
        self.Pre_Menu.addMenu(self.MD_Menu)
        self.SP_Menu = QMenu("Spatial Data")
        self.Pre_Menu.addMenu(self.SP_Menu)
        self.UG_Menu = QMenu("Urban Geometry")
        self.Pre_Menu.addMenu(self.UG_Menu)
        self.ULC_Menu = QMenu("Urban Land Cover")
        self.Pre_Menu.addMenu(self.ULC_Menu)
        self.SM_Menu = QMenu("Urban Morphology")
        self.Pre_Menu.addMenu(self.SM_Menu)
        self.SUEWSPrepare_Action = QAction("SUEWS Prepare", self.iface.mainWindow())
        self.Pre_Menu.addAction(self.SUEWSPrepare_Action)
        self.SUEWSPrepare_Action.triggered.connect(self.SUEWS_Prepare)


        # Sub-actions to Surface Morphology
        self.IMCP_Action = QAction("Morphometric Calculator (Point)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.IMCP_Action)
        self.IMCP_Action.triggered.connect(self.IMCP)
        self.IMCG_Action = QAction("Morphometric Calculator (Grid)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.IMCG_Action)
        self.IMCG_Action.triggered.connect(self.IMCG)
        self.FP_Action = QAction("Source Area Model (Point)", self.iface.mainWindow())
        self.SM_Menu.addAction(self.FP_Action)
        self.FP_Action.triggered.connect(self.FP)

        # Sub-actions to Meteorological Data Preparation
        self.PED_Action = QAction("Prepare Existing Data", self.iface.mainWindow())
        self.MD_Menu.addAction(self.PED_Action)
        self.PED_Action.triggered.connect(self.PED)
        self.PFD_Action = QAction("Download data (WATCH)", self.iface.mainWindow())
        self.MD_Menu.addAction(self.PFD_Action)
        self.PFD_Action.triggered.connect(self.WA)

        # Sub-actions to Spatial Data Preparation
        self.SDD_Action = QAction("Spatial Data Downloader", self.iface.mainWindow())
        self.SP_Menu.addAction(self.SDD_Action)
        self.SDD_Action.triggered.connect(self.UD)
        self.DSMGenerator_Action = QAction("DSM Generator", self.iface.mainWindow())
        self.SP_Menu.addAction(self.DSMGenerator_Action)
        self.DSMGenerator_Action.triggered.connect(self.DSMG)
        self.TreeGenerator_Action = QAction("Tree Generator", self.iface.mainWindow())
        self.SP_Menu.addAction(self.TreeGenerator_Action)
        self.TreeGenerator_Action.triggered.connect(self.TG)
        self.WC_Action = QAction("LCZ Converter", self.iface.mainWindow())
        self.SP_Menu.addAction(self.WC_Action)
        self.WC_Action.triggered.connect(self.WC)

        # Sub-actions to Urban Geometry
        self.SVF_Action = QAction("Sky View Factor", self.iface.mainWindow())
        self.UG_Menu.addAction(self.SVF_Action)
        self.SVF_Action.triggered.connect(self.SVF)
        # self.HW_Action = QAction("Height/Width Ratio", self.iface.mainWindow())
        # self.UG_Menu.addAction(self.HW_Action)
        # self.HW_Action.setEnabled(False)
        self.WH_Action = QAction("Wall Height and Aspect", self.iface.mainWindow())
        self.UG_Menu.addAction(self.WH_Action)
        self.WH_Action.triggered.connect(self.WH)

        # Sub-actions to Urban Land Cover
        self.ULCUEBRC_Action = QAction("Land Cover Reclassifier", self.iface.mainWindow())
        self.ULC_Menu.addAction(self.ULCUEBRC_Action)
        self.ULCUEBRC_Action.triggered.connect(self.LCRC)
        self.ULCUEBP_Action = QAction("Land Cover Fraction (Point)", self.iface.mainWindow())
        self.ULC_Menu.addAction(self.ULCUEBP_Action)
        self.ULCUEBP_Action.triggered.connect(self.LCP)
        self.ULCUEBG_Action = QAction("Land Cover Fraction (Grid)", self.iface.mainWindow())
        self.ULC_Menu.addAction(self.ULCUEBG_Action)
        self.ULCUEBG_Action.triggered.connect(self.LCG)

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
        self.MRT_Action.triggered.connect(self.SO)
        self.PWS_Action = QAction("Pedestrian Wind Speed", self.iface.mainWindow())
        self.OTC_Menu.addAction(self.PWS_Action)
        self.PWS_Action.setEnabled(False)
        self.EF_Action = QAction("Extreme Finder", self.iface.mainWindow())
        self.OTC_Menu.addAction(self.EF_Action)
        self.EF_Action.triggered.connect(self.EF)

        # Sub-menus to Urban Energy Balance
        self.QFL_Action = QAction("Antropogenic heat - GQf (Greater Qf)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.QFL_Action)
        self.QFL_Action.triggered.connect(self.GF)
        self.QF_Action = QAction("Antropogenic heat - LQf (LUCY)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.QF_Action)
        self.QF_Action.triggered.connect(self.LF)
        self.SUEWSSIMPLE_Action = QAction("Urban Energy Balance (SUEWS, Simple)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.SUEWSSIMPLE_Action)
        self.SUEWSSIMPLE_Action.triggered.connect(self.SUEWS_simple)
        self.SUEWS_Action = QAction("Urban Energy Balance (SUEWS/BLUEWS, Advanced)", self.iface.mainWindow())
        self.UEB_Menu.addAction(self.SUEWS_Action)
        self.SUEWS_Action.triggered.connect(self.SUEWS_advanced)
        # self.LUMPS_Action = QAction("Urban Energy Balance (LUMPS)", self.iface.mainWindow())
        # self.UEB_Menu.addAction(self.LUMPS_Action)
        # self.LUMPS_Action.setEnabled(False)
        # self.CBL_Action = QAction("UEB + CBL (BLUEWS/BLUMPS)", self.iface.mainWindow())
        # self.UEB_Menu.addAction(self.CBL_Action)
        # self.CBL_Action.setEnabled(False)

        # Sub-menus to Solar radiation
        self.SEBE_Action = QAction("Solar Energy on Building Envelopes (SEBE)", self.iface.mainWindow())
        self.SUN_Menu.addAction(self.SEBE_Action)
        self.SEBE_Action.triggered.connect(self.SE)
        self.DSP_Action = QAction("Daily Shadow Pattern", self.iface.mainWindow())
        self.SUN_Menu.addAction(self.DSP_Action)
        self.DSP_Action.triggered.connect(self.SH)

        # Sub-menus to Post-processing
        self.SUNpos_Menu = QMenu("Solar Radiation")
        self.Pos_Menu.addMenu(self.SUNpos_Menu)
        self.OTCpos_Menu = QMenu("Outdoor Thermal Comfort")
        self.Pos_Menu.addMenu(self.OTCpos_Menu)
        self.UEBpos_Menu = QMenu("Urban Energy Balance")
        self.Pos_Menu.addMenu(self.UEBpos_Menu)
        self.BSS_Action = QAction("Benchmarking System", self.iface.mainWindow())
        self.Pos_Menu.addAction(self.BSS_Action)
        self.BSS_Action.triggered.connect(self.BSS)

        # Sub-menus to Solar radiation, post processing
        self.SEBEv_Action = QAction("SEBE (Visualisation)", self.iface.mainWindow())
        self.SUNpos_Menu.addAction(self.SEBEv_Action)
        self.SEBEv_Action.triggered.connect(self.SEv)

        # Sub-menus to Outdoor thermal comfort, post processing
        self.SOLWEIGa_Action = QAction("SOLWEIG Analyzer", self.iface.mainWindow())
        self.OTCpos_Menu.addAction(self.SOLWEIGa_Action)
        self.SOLWEIGa_Action.triggered.connect(self.SOv)

        # Sub-menus to Urban Energy Balance, post processing
        self.SUEWSa_Action = QAction("SUEWS Analyzer", self.iface.mainWindow())
        self.UEBpos_Menu.addAction(self.SUEWSa_Action)
        self.SUEWSa_Action.triggered.connect(self.SUv)

        # Sub-menus to About
        self.About_Action = QAction("About", self.iface.mainWindow())
        self.About_Menu.addAction(self.About_Action)
        self.About_Action.triggered.connect(self.About)
        self.Manual_Action = QAction("UMEP on the web", self.iface.mainWindow())
        self.About_Menu.addAction(self.Manual_Action)
        self.Manual_Action.triggered.connect(self.help)

        # Icons
        self.SUEWSPrepare_Action.setIcon(QIcon(self.plugin_dir + "/Icons/SuewsLogo.png"))
        self.SUEWSSIMPLE_Action.setIcon(QIcon(self.plugin_dir + "/Icons/SuewsLogo.png"))
        self.SUEWS_Action.setIcon(QIcon(self.plugin_dir + "/Icons/SuewsLogo.png"))
        self.SVF_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_svf.png"))
        self.IMCG_Action.setIcon(QIcon(self.plugin_dir + "/Icons/ImageMorphIcon.png"))
        self.IMCP_Action.setIcon(QIcon(self.plugin_dir + "/Icons/ImageMorphIconPoint.png"))
        self.DSP_Action.setIcon(QIcon(self.plugin_dir + "/Icons/ShadowIcon.png"))
        self.ULCUEBG_Action.setIcon(QIcon(self.plugin_dir + "/Icons/LandCoverFractionGridIcon.png"))
        self.ULCUEBP_Action.setIcon(QIcon(self.plugin_dir + "/Icons/LandCoverFractionPointIcon.png"))
        self.ULCUEBRC_Action.setIcon(QIcon(self.plugin_dir + "/Icons/LandCoverReclassifierIcon.png"))
        self.WH_Action.setIcon(QIcon(self.plugin_dir + "/Icons/WallsIcon.png"))
        self.SEBE_Action.setIcon(QIcon(self.plugin_dir + "/Icons/sebeIcon.png"))
        self.SEBEv_Action.setIcon(QIcon(self.plugin_dir + "/Icons/sebeIcon.png"))
        self.FP_Action.setIcon(QIcon(self.plugin_dir + "/Icons/FootPrint.png"))
        self.About_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_umep.png"))
        self.Manual_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_umep.png"))
        self.PED_Action.setIcon(QIcon(self.plugin_dir + "/Icons/metdata.png"))
        self.PFD_Action.setIcon(QIcon(self.plugin_dir + "/Icons/watch.png"))
        self.MRT_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_solweig.png"))
        self.SOLWEIGa_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_solweig.png"))
        self.SUEWSa_Action.setIcon(QIcon(self.plugin_dir + "/Icons/SuewsLogo.png"))
        self.TreeGenerator_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_tree.png"))
        self.DSMGenerator_Action.setIcon(QIcon(self.plugin_dir + "/Icons/DSMGeneratorIcon.png"))
        self.EF_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_extreme.png"))
        self.WC_Action.setIcon(QIcon(self.plugin_dir + "/Icons/LCZ_icon.png"))
        self.SDD_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_spatialdownloader.png"))
        self.QFL_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_GQF.png"))
        self.QF_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_LQF.png"))
        self.BSS_Action.setIcon(QIcon(self.plugin_dir + "/Icons/icon_BSS.png"))

        self.iface.mainWindow().menuBar().insertMenu(self.iface.firstRightStandardMenu().menuAction(), self.UMEP_Menu)
        self.dlgAbout = UMEPDialogAbout()

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
        enabled_flag=False,
        add_to_menu=False,
        add_to_toolbar=False,
        status_tip=None,
        whats_this=None,
        parent=None):

        """Add a toolbar icon to the toolbar.
        Not Used
        """

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/UMEP/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'UMEP'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Code to show the about dialog
        # QObject.connect(self.About_Action, SIGNAL("triggered()"), self.dlgAbout, SLOT("show()"))
        # QObject.signal.connect(self.dlgAbout)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UMEP'),
                action)
            self.iface.removeToolBarIcon(action)
            self.iface.mainWindow().menuBar().removeAction(self.UMEP_Menu.menuAction())

    def About(self):
        self.dlgAbout.show()

    def PED(self):
        sg = MetdataProcessor(self.iface)
        sg.run()

    def SH(self):
        sg = ShadowGenerator(self.iface)
        sg.run()
        
    def IMCG(self):
        sg = ImageMorphParam(self.iface)
        sg.run()

    def IMCP(self):
        sg = ImageMorphParmsPoint(self.iface)
        sg.run()

    def SVF(self):
        sg = SkyViewFactorCalculator(self.iface)
        sg.run()

    def SUEWS_simple(self):
        sg = SuewsSimple(self.iface)
        sg.run()

    def SUEWS_advanced(self):
        sg = SUEWS(self.iface)
        sg.run()

    def SUEWS_Prepare(self):
        sg = SUEWSPrepare(self.iface)
        sg.run()

    def LCG(self):
        sg = LandCoverFractionGrid(self.iface)
        sg.run()

    def LCP(self):
        sg = LandCoverFractionPoint(self.iface)
        sg.run()

    def LCRC(self):
        sg = LandCoverReclassifier(self.iface)
        sg.run()

    def WH(self):
        sg = WallHeight(self.iface)
        # pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True)  #used for debugging
        sg.run()

    def SE(self):
        sg = SEBE(self.iface)
        sg.run()

    def SEv(self):
        QMessageBox.critical(self.dlg, "Plugin blocker",
                             "This tool is not yet ported to QGIS3. Work still in progress.")
        return
        sg = Sun(self.iface)
        sg.run()

    def FP(self):
        sg = FootprintModel(self.iface)
        sg.run()

    def WA(self):
        sg = WATCHData(self.iface)
        sg.run()

    def GF(self):
        QMessageBox.critical(self.dlg, "Plugin blocker",
                             "This tool is not yet ported to QGIS3. Work still in progress.")
        return
        sg = GreaterQF(self.iface)
        sg.run()

    def SO(self):
        sg = SOLWEIG(self.iface)
        sg.run()

    def TG(self):
        sg = TreeGenerator(self.iface)
        sg.run()

    def DSMG(self):
        sg = DSMGenerator(self.iface)
        sg.run()

    def EF(self):
        sg = ExtremeFinder(self.iface)
        sg.run()

    def SOv(self):
        sg = SolweigAnalyzer(self.iface)
        sg.run()

    def SUv(self):
        sg = SUEWSAnalyzer(self.iface)
        sg.run()

    def UD(self):
        sg = UMEP_Data_Download(self.iface)
        sg.run()

    def WC(self):
        sg = LCZ_test(self.iface)
        sg.run()

    def LF(self):
        # QMessageBox.critical(self.dlg, "Plugin blocker",
        #                      "This tool is not yet ported to QGIS3. Work still in progress.")
        # return
        sg = LQF(self.iface)
        sg.run()

    def BSS(self):
        sg = BenchMarking(self.iface)
        sg.run()

    def run(self):
        # This function starts the plugin
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = "https://umep-docs.readthedocs.io/en/latest/index.html"
        webbrowser.open_new_tab(url)


