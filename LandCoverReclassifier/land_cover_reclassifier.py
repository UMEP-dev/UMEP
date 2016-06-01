# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandCoverReclassifier
                                 A QGIS plugin
 Reclassifies a raster to a UMEP land cover grid
                              -------------------
        begin                : 2015-07-13
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
from osgeo import gdal
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from ..Utilities.qgiscombomanager import *
from land_cover_reclassifier_dialog import LandCoverReclassifierDialog
import os.path
import numpy as np
from ..Utilities.misc import *
import webbrowser

class LandCoverReclassifier:
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
            'LandCoverReclassifier_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LandCoverReclassifierDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.save_file_place)
        self.dlg.helpButton.clicked.connect(self.help)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(0)
        self.fileDialog.setAcceptMode(1)  # Save
        self.fileDialog.setNameFilter("(*.tif *.tiff)")

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Land Cover Reclassifier')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'LandCoverReclassifier')
        # self.toolbar.setObjectName(u'LandCoverReclassifier')

        self.layerComboManagerLCgrid = RasterLayerCombo(self.dlg.comboBox_lcgrid)
        RasterLayerCombo(self.dlg.comboBox_lcgrid, initLayer="")

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
        return QCoreApplication.translate('LandCoverReclassifier', message)


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

        icon_path = ':/plugins/LandCoverReclassifier/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Reclassifies a raster to a UMEP land cover grid'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Land Cover Reclassifier'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def save_file_place(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        # filename = QFileDialog.getSaveFileName(self.dlg, "Save as geotiff ", '*.tif')
        if result == 1:
            self.filePath = self.fileDialog.selectedFiles()
            self.filePath[0] = self.filePath[0] + '.tif'
            self.dlg.textOutput.setText(self.filePath[0])

    def start_progress(self):

        lc_grid = self.layerComboManagerLCgrid.getLayer()
        if lc_grid is None:
            QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            return

        if self.filePath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

        # Reclass
        # self.dlg.pai_1_g.setInputMask("0.00")
        lc_type = np.zeros((14, 3))
        lc_type[0, 0] = float(self.dlg.Box_1.currentIndex())
        if lc_type[0, 0] > 0:
            lc_type[0, 1] = self.dlg.pai_1_g.text()
            lc_type[0, 2] = self.dlg.pai_1_s.text()
        lc_type[1, 0] = float(self.dlg.Box_2.currentIndex())
        if lc_type[1, 0] > 0:
            lc_type[1, 1] = self.dlg.pai_2_g.text()
            lc_type[1, 2] = self.dlg.pai_2_s.text()
        lc_type[2, 0] = float(self.dlg.Box_3.currentIndex())
        if lc_type[2, 0] > 0:
            lc_type[2, 1] = self.dlg.pai_3_g.text()
            lc_type[2, 2] = self.dlg.pai_3_s.text()
        lc_type[3, 0] = float(self.dlg.Box_4.currentIndex())
        if lc_type[3, 0] > 0:
            lc_type[3, 1] = self.dlg.pai_4_g.text()
            lc_type[3, 2] = self.dlg.pai_4_s.text()
        lc_type[4, 0] = float(self.dlg.Box_5.currentIndex())
        if lc_type[4, 0] > 0:
            lc_type[4, 1] = self.dlg.pai_5_g.text()
            lc_type[4, 2] = self.dlg.pai_5_s.text()
        lc_type[5, 0] = float(self.dlg.Box_6.currentIndex())
        if lc_type[5, 0] > 0:
            lc_type[5, 1] = self.dlg.pai_6_g.text()
            lc_type[5, 2] = self.dlg.pai_6_s.text()
        lc_type[6, 0] = float(self.dlg.Box_7.currentIndex())
        if lc_type[6, 0] > 0:
            lc_type[6, 1] = self.dlg.pai_7_g.text()
            lc_type[6, 2] = self.dlg.pai_7_s.text()

        lc_type[7, 0] = float(self.dlg.Box_8.currentIndex())
        if lc_type[7, 0] > 0:
            lc_type[7, 1] = self.dlg.pai_8_g.text()
            lc_type[7, 2] = self.dlg.pai_8_s.text()
        lc_type[8, 0] = float(self.dlg.Box_9.currentIndex())
        if lc_type[8, 0] > 0:
            lc_type[8, 1] = self.dlg.pai_9_g.text()
            lc_type[8, 2] = self.dlg.pai_9_s.text()
        lc_type[9, 0] = float(self.dlg.Box_10.currentIndex())
        if lc_type[9, 0] > 0:
            lc_type[9, 1] = self.dlg.pai_10_g.text()
            lc_type[9, 2] = self.dlg.pai_10_s.text()
        lc_type[10, 0] = float(self.dlg.Box_11.currentIndex())
        if lc_type[10, 0] > 0:
            lc_type[10, 1] = self.dlg.pai_11_g.text()
            lc_type[10, 2] = self.dlg.pai_11_s.text()
        lc_type[11, 0] = float(self.dlg.Box_12.currentIndex())
        if lc_type[11, 0] > 0:
            lc_type[11, 1] = self.dlg.pai_12_g.text()
            lc_type[11, 2] = self.dlg.pai_12_s.text()
        lc_type[12, 0] = float(self.dlg.Box_13.currentIndex())
        if lc_type[12, 0] > 0:
            lc_type[12, 1] = self.dlg.pai_13_g.text()
            lc_type[12, 2] = self.dlg.pai_13_s.text()
        lc_type[13, 0] = float(self.dlg.Box_14.currentIndex())
        if lc_type[13, 0] > 0:
            lc_type[13, 1] = self.dlg.pai_14_g.text()
            lc_type[13, 2] = self.dlg.pai_14_s.text()

        provider = lc_grid.dataProvider()
        filepath_lc_grid= str(provider.dataSourceUri())
        gdal_lc_grid = gdal.Open(filepath_lc_grid)

        lc_grid = gdal_lc_grid.ReadAsArray().astype(np.float)
        sizex = lc_grid.shape[0]
        sizey = lc_grid.shape[1]
        lc_grid_rc = np.zeros((sizex, sizey))

        # populating new grid with values
        for i in range(lc_type.shape[0]):
            lc_grid_rc[np.where((lc_grid > lc_type[i, 1]) & (lc_grid <= lc_type[i, 2]))] = lc_type[i, 0]

        filename = self.filePath[0]
        saveraster(gdal_lc_grid, filename, lc_grid_rc)

        # load result into canvas
        rlayer = self.iface.addRasterLayer(filename)

        # This is not working, yet... almost now. only now showing names in layer window
        rlayer.loadNamedStyle(self.plugin_dir + '/landcoverstyle.qml')
        # self.QgsMapLayerRegistry.instance().addMapLayer(rlayer)

        # Trigger a repaint
        if hasattr(rlayer, "setCacheImage"):
            rlayer.setCacheImage(None)
        rlayer.triggerRepaint()

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = "file://" + self.plugin_dir + "/help/Index.html"
        webbrowser.open_new_tab(url)

