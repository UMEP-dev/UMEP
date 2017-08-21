# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageMorphParam
                                 A QGIS plugin
 This plugin calculates morphometric parameters based on high resolution urban DSMs
                              -------------------
        begin                : 2015-01-06
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg, GU
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
from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
from qgis.gui import *
from qgis.core import *
import os
from ..Utilities.qgiscombomanager import *
from osgeo import gdal
from ..Utilities.imageMorphometricParms_v1 import *
from impgworker import Worker
from image_morph_param_dialog import ImageMorphParamDialog
import webbrowser

# Initialize Qt resources from file resources.py
import resources_rc

class ImageMorphParam:
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
            'ImageMorphParam_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ImageMorphParamDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.progressBar.setValue(0)
        self.dlg.checkBoxOnlyBuilding.toggled.connect(self.text_enable)

        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        for i in range(1, 25):
            if 360 % i == 0:
                self.dlg.degreeBox.addItem(str(i))
        self.dlg.degreeBox.setCurrentIndex(4)

        self.folderPath = 'None'
        self.degree = 5.0
        self.dsm = None
        self.dem = None
        self.scale = None
        self.thread = None
        self.worker = None
        self.steps = 0

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Image Morphometric Parameters')
        # self.toolbar = self.iface.addToolBar(u'ImageMorphParam')
        # self.toolbar.setObjectName(u'ImageMorphParam')

        # self.layerComboManagerPolygrid = VectorLayerCombo(self.dlg.comboBox_Polygrid)
        # fieldgen = VectorLayerCombo(self.dlg.comboBox_Polygrid, initLayer="", options={"geomType": QGis.Polygon})
        # self.layerComboManagerPolyField = FieldCombo(self.dlg.comboBox_Field, fieldgen, initField="")
        self.layerComboManagerPolygrid = QgsMapLayerComboBox(self.dlg.widgetPolygrid)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyField  = QgsFieldComboBox(self.dlg.widgetField)
        self.layerComboManagerPolyField .setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid .layerChanged.connect(self.layerComboManagerPolyField.setLayer)

        # self.layerComboManagerDSMbuildground = RasterLayerCombo(self.dlg.comboBox_DSMbuildground)
        # RasterLayerCombo(self.dlg.comboBox_DSMbuildground, initLayer="")
        # self.layerComboManagerDEM = RasterLayerCombo(self.dlg.comboBox_DEM)
        # RasterLayerCombo(self.dlg.comboBox_DEM, initLayer="")
        # self.layerComboManagerDSMbuild = RasterLayerCombo(self.dlg.comboBox_DSMbuild)
        # RasterLayerCombo(self.dlg.comboBox_DSMbuild, initLayer="")
        self.layerComboManagerDSMbuildground = QgsMapLayerComboBox(self.dlg.widgetDSMbuildground)
        self.layerComboManagerDSMbuildground.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSMbuildground.setFixedWidth(175)
        self.layerComboManagerDSMbuildground.setCurrentIndex(-1)
        self.layerComboManagerDEM = QgsMapLayerComboBox(self.dlg.widgetDEM)
        self.layerComboManagerDEM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDEM.setFixedWidth(175)
        self.layerComboManagerDEM.setCurrentIndex(-1)
        self.layerComboManagerDSMbuild = QgsMapLayerComboBox(self.dlg.widgetDSMbuild)
        self.layerComboManagerDSMbuild.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerDSMbuild.setFixedWidth(175)
        self.layerComboManagerDSMbuild.setCurrentIndex(-1)

        if not (os.path.isdir(self.plugin_dir + '/data')):
            os.mkdir(self.plugin_dir + '/data')

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
        return QCoreApplication.translate('ImageMorphParam', message)

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

        icon_path = ':/plugins/ImageMorphParam/ImageMorphIcon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Image Morphometric Parameters'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Image Morphometric Parameters'),
                action)
            self.iface.removeToolBarIcon(action)

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def text_enable(self):
        if self.dlg.checkBoxOnlyBuilding.isChecked():
            self.dlg.label_2.setEnabled(False)
            self.dlg.label_3.setEnabled(False)
            self.dlg.label_4.setEnabled(True)
        else:
            self.dlg.label_2.setEnabled(True)
            self.dlg.label_3.setEnabled(True)
            self.dlg.label_4.setEnabled(False)

    # Metod som startar traden, knyter signaler fran traden till metoder. Se impgworker.py for det arbete som traden utfor.
    def startWorker(self, dsm, dem, dsm_build, poly, poly_field, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                    folderPath, dlg, imid, radius, degree, rm):
        # create a new worker instance
        # Skapar en instans av metoden som innehaller det arbete som ska utforas i en trad

        worker = Worker(dsm, dem, dsm_build, poly, poly_field, vlayer, prov, fields, idx, dir_poly, iface,
                        plugin_dir, folderPath, dlg, imid, radius, degree, rm)

        # andrar knappen som startar verktyget till en knapp som avbryter tradens arbete.
        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.closeButton.setEnabled(False)

        # Skapar en trad som arbetet fran worker ska utforas i.
        thread = QThread(self.dlg)
        worker.moveToThread(thread)
        # kopplar signaler fran traden till metoder i denna "fil"
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        # startar traden
        thread.start()
        self.thread = thread
        self.worker = worker

    # Metod som ar kopplad till en signal som Worker(traden) skickar nar den utfort sitt arbete, killed ar en Boolean som
    # skiljer mellan om traden blev "fardig" for att den gjorde sitt arbete eller om den avbrots
    def workerFinished(self, ret):
        # Tar bort arbetaren (Worker) och traden den kors i
        try:
            self.worker.deleteLater()
        except RuntimeError:
             pass
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        #andra tillbaka Run-knappen till sitt vanliga tillstand och skicka ett meddelande till anvanderen.
        if ret == 1:
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.closeButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            # QMessageBox.information(None, "Image Morphometric Parameters",
            #                         "Process finished! Check General Messages (speech bubble, lower left) "
            #                         "to obtain information of the process.")
            self.iface.messageBar().pushMessage("Image Morphometric Parameters",
                                    "Process finished! Check General Messages (speech bubble, lower left) "
                                    "to obtain information of the process.", duration=5)
        else:
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.closeButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            QMessageBox.information(None, "Image Morphometric Parameters", "Operations cancelled, "
                                                                           "process unsuccessful! See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.")

    #Metod som tar emot en signal fran traden ifall nagot gick fel, felmeddelanden skrivs till QGIS message log.
    def workerError(self, errorstring):
        #strerror = str(errorstring)
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)

    #Metod som tar emot signaler koontinuerligt fran traden som berattar att ett berakningsframsteg gjorts, uppdaterar
    #progressbar
    def progress_update(self):
        self.steps +=1
        self.dlg.progressBar.setValue(self.steps)

    #Metoden som kors genom run-knappen, precis som tidigare.
    def start_progress(self):
        #Steg for uppdatering av
        self.steps = 0
        poly = self.layerComboManagerPolygrid.currentLayer()
        if poly is None:
            QMessageBox.critical(self.dlg, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(self.dlg, "Error", "No valid Polygon layer is selected")
            return

        poly_field = self.layerComboManagerPolyField.currentField()
        if poly_field is None:
            QMessageBox.critical(self.dlg, "Error", "An attribute filed with unique fields must be selected")
            return
        # QMessageBox.information(None, "TEst", str(poly_field) )
        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        idx = vlayer.fieldNameIndex(poly_field)

        dir_poly = self.plugin_dir + '/data/poly_temp.shp'
        # j = 0
        self.dlg.progressBar.setMaximum(vlayer.featureCount())

        # skapar referenser till lagern som laddas in av anvandaren i comboboxes
        if self.dlg.checkBoxOnlyBuilding.isChecked():  # Only building heights
            dsm_build = self.layerComboManagerDSMbuild.currentLayer()
            dsm = None
            dem = None
            if dsm_build is None:
                QMessageBox.critical(self.dlg, "Error", "No valid building DSM raster layer is selected")
                return

        else:  # Both building ground heights
            dsm = self.layerComboManagerDSMbuildground.currentLayer()
            dem = self.layerComboManagerDEM.currentLayer()
            dsm_build = None
            if dsm is None:
                QMessageBox.critical(None, "Error", "No valid ground and building DSM raster layer is selected")
                return
            if dem is None:
                QMessageBox.critical(None, "Error", "No valid ground DEM raster layer is selected")
                return

        if self.dlg.radioButtonExtent.isChecked():  # What search method to use
            imid = 0
        else:
            imid = 1

        # #Calculate Z0m and Zdm depending on the Z0 method
        ro = self.dlg.comboBox_Roughness.currentIndex()
        if ro == 0:
            rm = 'RT'
        elif ro == 1:
            rm = 'Rau'
        elif ro == 2:
            rm = 'Bot'
        elif ro == 3:
            rm = 'Mac'
        elif ro == 4:
            rm = 'Mho'
        else:
            rm = 'Kan'

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

        radius = self.dlg.spinBoxDistance.value()
        degree = float(self.dlg.degreeBox.currentText())

        # Startar arbetarmetoden och traden, se startworker metoden ovan.
        self.startWorker(dsm, dem, dsm_build, poly, poly_field, vlayer, prov, fields, idx, dir_poly, self.iface,
                         self.plugin_dir, self.folderPath, self.dlg, imid, radius, degree, rm)

        # Allt som ska ske efter att arbetaren startats hanteras genom metoderna som tar emot signaler fran traden.
        # Framforallt workerFinished metoden. Se impgworker.py filen for implementering av det arbete som traden utfor.

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        self.dlg.exec_()

        gdal.UseExceptions()
        gdal.AllRegister()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = "http://www.urban-climate.net/umep/UMEP_Manual#Urban_Morphology:" \
              "_Image_Morphometric_Parameter_Calculator_.28Grid.29"
        webbrowser.open_new_tab(url)