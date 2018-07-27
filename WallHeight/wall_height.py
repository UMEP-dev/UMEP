# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WallHeight
                                 A QGIS plugin
 This plugin identifies wall pixels on a DSM and derives wall height and aspect 
                              -------------------
        begin                : 2015-09-16
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from qgis.gui import *
from qgis.core import QgsMessageLog
from wall_height_dialog import WallHeightDialog
import os.path
import wallalgorithms as wa
from ..Utilities.misc import *
from wallworker import Worker
import webbrowser

class WallHeight:
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
            'WallHeight_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = WallHeightDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSaveHeight.clicked.connect(self.save_file_place_height)
        self.dlg.pushButtonSaveAspect.clicked.connect(self.save_file_place_aspect)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(0)
        self.fileDialog.setAcceptMode(1)  # Save
        self.fileDialog.setNameFilter("(*.tif *.tiff)")

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Wall Height')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'WallHeight')
        # self.toolbar.setObjectName(u'WallHeight')

        # self.layerComboManagerDSM = RasterLayerCombo(self.dlg.comboBox_dsm)
        # RasterLayerCombo(self.dlg.comboBox_dsm, initLayer="")
        self.layerComboManagerDSM = QgsMapLayerComboBox(self.dlg.widgetDSM)
        self.layerComboManagerDSM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSM.setFixedWidth(175)
        self.layerComboManagerDSM.setCurrentIndex(-1)

        self.thread = None
        self.worker = None
        self.steps = 0

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
        return QCoreApplication.translate('WallHeight', message)

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

        icon_path = ':/plugins/WallHeight/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Wall Height'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def save_file_place_height(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.filePathH = self.fileDialog.selectedFiles()
            self.filePathH[0] = self.filePathH[0] + '.tif'
            self.dlg.textOutputHeight.setText(self.filePathH[0])
            self.dlg.runButton.setEnabled(1)

    def save_file_place_aspect(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.filePathA = self.fileDialog.selectedFiles()
            self.filePathA[0] = self.filePathA[0] + '.tif'
            self.dlg.textOutputAspect.setText(self.filePathA[0])

    def run(self):
        self.dlg.show()
        self.dlg.exec_()

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def start_progress(self):
        self.dlg.progressBar.setRange(0, 180)
        if self.filePathH is None:
            QMessageBox.critical(self.dlg, "Error", "No wall height file specified")
        else:
            #dsmlayer = self.layerComboManagerDSM.getLayer()
            dsmlayer = self.layerComboManagerDSM.currentLayer()

            if dsmlayer is None:
                    QMessageBox.critical(self.dlg, "Error", "No valid raster layer is selected")
                    return

            provider = dsmlayer.dataProvider()
            filepath_dsm = str(provider.dataSourceUri())

            # self.gdal_dsm = gdal.Open(filepath_dsm, gdal.GA_ReadOnly)
            # myBand = self.gdal_dsm.GetRasterBand(1)
            # scanline = myBand.ReadRaster(0, 0, myBand.XSize, 1, myBand.XSize, 1, gdal.GDT_Byte)
            # import array
            # self.dsm = array.array('B', scanline)
            # myBand = None
            # myImg = None

            self.gdal_dsm = gdal.Open(filepath_dsm)
            self.dsm = self.gdal_dsm.ReadAsArray().astype(np.float)
            geotransform = self.gdal_dsm.GetGeoTransform()
            self.scale = 1 / geotransform[1]
            # self.iface.messageBar().pushMessage("scale", str(self.scale))
            # return

            walllimit = self.dlg.doubleSpinBoxHeight.value()
            # self.iface.messageBar().pushMessage("SEBE", str(walllimit))
            self.walls = wa.findwalls(self.dsm, walllimit)
            saveraster(self.gdal_dsm, self.filePathH[0], self.walls)
            # dirwalls = wa.filter1Goodwin_as_aspect_v3(self.walls, self.scale, self.dsm)
            if self.dlg.checkBoxAspect.isChecked():
                self.startWorker(self.walls, self.scale, self.dsm, self.dlg)
                # dirwalls = wa.filter1Goodwin_as_aspect_v3(walls, self.scale, self.dsm)
        #         saveraster(self.gdal_dsm, self.filePathA[0], dirwalls)
        #
        # QMessageBox.information(None, "Wall generator", "Wall grid(s) successfully generated")
        # # self.iface.messageBar().pushMessage("Wall generator", "Wall grid(s) successfully generated")
        #
        # load height result into canvas
        if self.dlg.checkBoxIntoCanvas.isChecked():
            rlayer = self.iface.addRasterLayer(self.filePathH[0])

            if hasattr(rlayer, "setCacheImage"):
                rlayer.setCacheImage(None)
            rlayer.triggerRepaint()

            # if self.filePathA[0]:
            #     rlayer2 = self.iface.addRasterLayer(self.filePathA[0])
            #
            #     if hasattr(rlayer2, "setCacheImage"):
            #         rlayer2.setCacheImage(None)
            #     rlayer2.triggerRepaint()

    def startWorker(self, walls, scale, dsm, dlg):

        # create a new worker instance
        worker = Worker(walls, scale, dsm, dlg)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.pushButton.setEnabled(False)

        # start the worker in a new thread
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
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # remove widget from message bar
        if ret is not None:
            # report the result
            dirwalls = ret["dirwalls"]
            # Energyyearwall = ret["Energyyearwall"]
            # vegdata = ret["vegdata"]
            # layer, total_area = ret
            saveraster(self.gdal_dsm, self.filePathA[0], dirwalls)

            # QMessageBox.information(None, "Wall generator", "Wall grid(s) successfully generated")
            # self.iface.messageBar().pushMessage("Wall generator", "Wall grid(s) successfully generated")

            # load aspect result into canvas
            if self.dlg.checkBoxAspect.isChecked():
                if self.dlg.checkBoxIntoCanvas.isChecked():
                    rlayer = self.iface.addRasterLayer(self.filePathA[0])

                    if hasattr(rlayer, "setCacheImage"):
                        rlayer.setCacheImage(None)
                    rlayer.triggerRepaint()

            QMessageBox.information(None, "Wall aspect", "Calculation succesfully completed")
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton.setEnabled(True)
        else:
            # notify the user that something went wrong
            self.iface.messageBar().pushMessage('Operations cancelled either by user or error. See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.', level=QgsMessageBar.CRITICAL, duration=5)
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)

    def workerError(self, errorstring):
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def help(self):
        url = 'http://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Geometry%20Wall%20' \
              'Height%20and%20Aspect.html'
        webbrowser.open_new_tab(url)