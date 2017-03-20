from PyQt4 import QtGui, uic
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
import os
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'time_displayer.ui'))
from qgis.core import QgsMessageLog,  QgsMapLayerRegistry, QgsVectorLayer, QgsMapRenderer, QgsRectangle
from PythonLUCY.DataManagement.spatialHelpers import populateShapefileFromTemplate, colourRanges, openShapeFileInMemory, duplicateVectorLayer
try:
    import pandas as pd
    from matplotlib import pyplot
except:
    pass
from datetime import datetime as dt
from PyQt4.QtGui import QImage, QColor, QPainter
from PyQt4.QtCore import QSize

# Creates a dialog box that allow different model output time slices to be visualised in QGIS
def intOrString(x):
    # Return integer representation if possible, or string if not
    try:
        return int(x)
    except:
        return str(x)

class time_displayer(QtGui.QDialog, FORM_CLASS):
    def __init__(self, model, iface, parent=None):
        '''
        Given a folder containing model outputs and DataSources object, this widget displays all available time steps
        No sanity is applied: if a valid GreaterQF output file is present in the folder, this widget will try to display it
        :param dataSources: GreaterQF DataSources object for the model run
        :param modelOutputFolder: Folder containing model outputs for the model run
        :param parent:
        '''
        """Constructor."""
        super(time_displayer, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.cmdTimeseries.clicked.connect(self.makeTimeseries)
        self.cmdAddMap.clicked.connect(self.updateDisplay)
        self.model = model
        self.selectedTime = None # The time currently selected
        self.selectedArea = None # The area currently selected

        # Deal with output layer
        outlay = self.model.getOutputLayerInfo()
        self.featureIdField = outlay['featureIds']
        self.outputEPSG = outlay['EPSG']
        self.outputLayer = outlay['file']# Holds the map template
        self.mapLayer = None # Holds the decorated map
        # File name format
        self.componentDict = {0:"Qf (Total)", 1:"Qb (Building)", 2:"Qt (Transport)", 3:"Qm (Metabolism)"} # Total, buildings, transport, metabolism
        # Translate between component names and column headers produced by model.fetchResultsForLocation()

        # Translate between component names and file headers
        self.componentTranslation = {"Qf (Total)":"Qf",
                                     "Qb (Building)": "Qb",
                                     "Qt (Transport)":"Qt",
                                     "Qm (Metabolism)":"Qm"}
        # Populate list boxes
        self.populateAreaList()
        self.populateTimeList()

    def makeTimeseries(self):
        '''
        Produce a time series  plot using matplotlib and the currently selected area ID
        :return: None
        '''
        id = self.lstAreas.currentItem().text()
        result = self.model.fetchResultsForLocation(intOrString(id), dt(1900,01,01), dt(2200,01,01))
        fig = pyplot.figure(id)
        pyplot.subplot(311)
        pltQb= pyplot.plot(result.index, result[self.componentTranslation['Qb (Building)']])
        pyplot.title('Building')
        pyplot.ylabel('W m-2')
        pyplot.subplot(312)
        pltQb = pyplot.plot(result.index, result[self.componentTranslation['Qt (Transport)']])
        pyplot.ylabel('W m-2')
        pyplot.title('Transport')
        pyplot.subplot(313)
        pltQb = pyplot.plot(result.index, result[self.componentTranslation['Qm (Metabolism)']])
        pyplot.title('Metabolism')
        pyplot.ylabel('W m-2')
        pyplot.xlabel('Time (UTC)')
        pyplot.tight_layout()
        pyplot.show()

    def populateTimeList(self):
        '''
        Populate the time listbox
        :param timeIndex:
        :return:
        '''
        def toString(x): return x.strftime('%Y-%m-%d %H:%M')
        timeLabels = map(toString, self.model.getTimeSteps())
        for label in timeLabels:
            time = QListWidgetItem(label)
            self.lstTimes.addItem(time)

    def populateAreaList(self):
        '''
        Populate the area ID listbox
        '''
        [self.lstAreas.addItem(QListWidgetItem(str(intOrString(label)))) for label in self.model.getOutputAreaIDs()]

    def updateDisplay(self):
        ''' Add map(s) of all QF components to the canvas based on what's selected in self.lstTimes'''
        timestamps = [pd.datetime.strptime(newItem.text(), '%Y-%m-%d %H:%M') for newItem in self.lstTimes.selectedItems()]

        for t in timestamps:
            outs = pd.read_csv(self.model.getFileList()[t], header=0, index_col=0)
            outLayer = self.outputLayer
            # Make sure the output file is properly appended (this gets evaluated for non-extra-disaggregated datasets)
            # because I didn't set an output shapefile path properl

            if os.path.split(self.outputLayer)[0] == '':
                outLayer = os.path.join(self.model.downscaledPath, os.path.split(self.outputLayer)[1])

            fileToPopulate = self.outputLayer
            new_layer = populateShapefileFromTemplate(outs, self.featureIdField, outLayer , int(self.outputEPSG), title=t.strftime(' %Y-%m-%d %H:%M UTC'))

            # Set ranges suited to all the different QF types
            range_minima = [0, 0.000001, 0.1, 1, 10, 100]
            range_maxima = [0.000001, 0.1, 1, 10, 100, 1000]
            colours = ['#CECECE', '#FEE6CE', '#FDAE6B', '#F16913', '#D94801', '#7F2704']
            opacity = 1
            for component in self.componentTranslation.values():
                layerName = component + t.strftime(' %Y-%m-%d %H:%M UTC')
                if component == self.componentTranslation.values()[0]:
                    colourRanges(new_layer, component, opacity, range_minima, range_maxima, colours)
                    new_layer.setLayerName(layerName)
                    layerId = new_layer.id()
                    QgsMapLayerRegistry.instance().addMapLayer(new_layer)
                    proportion = new_layer.extent().height() / new_layer.extent().width()

                else:
                    # Have to clone. Can't seem to duplicate a map layer...
                    layer = duplicateVectorLayer(new_layer)
                    layer.setLayerName(layerName)
                    colourRanges(layer, component, opacity, range_minima, range_maxima, colours)
                    layerId = layer.id()
                    QgsMapLayerRegistry.instance().addMapLayer(layer)
                    proportion = layer.extent().height() / layer.extent().width()


                maxSize = 2000 # Max size of output image
                if proportion > 1:
                    hSize = maxSize / proportion
                    vSize = maxSize
                else:
                    hSize = maxSize
                    vSize = maxSize*proportion

                print(hSize, vSize)
                # create image in proportion with layer
                img = QImage(QSize(hSize, vSize), QImage.Format_ARGB32_Premultiplied)

                # set image's background color
                color = QColor(255, 255, 255)
                img.fill(color.rgb())

                # create painter
                p = QPainter()
                p.begin(img)
                p.setRenderHint(QPainter.Antialiasing)

                render = QgsMapRenderer()

                # set layer set
                lst = [layerId]  # add ID of every layer
                render.setLayerSet(lst)

                # set extent
                rect = QgsRectangle(render.fullExtent())
                rect.scale(1.1)
                render.setExtent(rect)

                # set output size
                render.setOutputSize(img.size(), img.logicalDpiX())

                # do the rendering
                render.render(p)
                p.end()

                # save image
                img.save(os.path.join(self.model.renderPath, component + t.strftime('_%Y-%m-%d_%H-%M_UTC.png')),"png")

                    #
                    #
                    # # From http://gis.stackexchange.com/questions/189735/how-to-iterate-over-layers-and-export-them-as-png-images-with-pyqgis-in-a-standa
                    # from PyQt4.QtCore import QTimer
                    #
                    # fileName = "c:/testoutput/" + str(layer.id()) + ".png"
                    # layerToPlot = QgsMapLayerRegistry.instance().mapLayers()[layerId]
                    # self.iface.legendInterface().setLayerVisible(layerToPlot, True)
                    #
                    # def prepareMap(): # Arrange layers
                    #     self.iface.actionHideAllLayers().trigger() # make all layers invisible
                    #     self.iface.legendInterface().setLayerVisible(layerToPlot, True)
                    #     QTimer.singleShot(1000, exportMap) # Wait a second and export the map
                    #
                    # def exportMap(): # Save the map as a PNG
                    #     #global count # We need this because we'll modify its value
                    #     self.iface.mapCanvas().saveAsImage( fileName  )
                    #     print "Map with layer exported!"
                    #     #if count < len([])-1:
                    #     QTimer.singleShot(1000, prepareMap) # Wait a second and prepare next map
                    #     #count += 1
                    #
                    # prepareMap() # Let's start the fun
                    #

