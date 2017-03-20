from PyQt4 import QtGui, uic
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
import os
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'time_displayer.ui'))
from qgis.core import QgsMessageLog,  QgsMapLayerRegistry, QgsVectorLayer, QgsMapRenderer, QgsRectangle
from PythonQF2.DataManagement.spatialHelpers import populateShapefileFromTemplate, colourRanges, openShapeFileInMemory, duplicateVectorLayer
try:
    import pandas as pd
    import numpy as np
    from matplotlib.patches import Rectangle
    from matplotlib import pyplot
except:
    pass

from datetime import datetime as dt
from PyQt4.QtGui import QImage, QColor, QPainter
from PyQt4.QtCore import QSize

def makeRect(color):
    return Rectangle((0,0), 1, 1,fc=color)

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
        self.componentTranslation = {"Qf (Total)":"AllTot",
                                     "Qb (Building)": "BldTot",
                                     "Qt (Transport)":"TransTot",
                                     "Qm (Metabolism)":"Metab"}
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

        pyplot.rcParams["font.family"] = "arial"
        fig = pyplot.figure(id, facecolor='white',figsize=(8,17), dpi=80)
        # Make 4 entries
        # 1: Total QF, broken down by buildings, transport and metabolism
        a1 = pyplot.subplot(411)
        # pltQb= pyplot.plot(result.index, result[self.componentTranslation['Qb (Building)']])
        b_col = 'grey'
        m_col = 'navy'
        t_col = 'firebrick'
        legendtext = 12 # LEgend text size
        titletext = 12 # Title (inc axes) text size
        a1.stackplot(result.index, np.array(result[self.componentTranslation['Qb (Building)']]).astype('float'),
                 np.array(result[self.componentTranslation['Qt (Transport)']]).astype('float'),
                 np.array(result[self.componentTranslation['Qm (Metabolism)']]).astype('float'),
                 linewidth=0,
                 colors=[b_col, t_col, m_col])
        pyplot.title('Total', fontsize=titletext)
        rects1 = map(makeRect, [b_col, t_col, m_col])
        a1.legend(rects1, ('Bldg', 'Tran', 'Met'), loc='best', fontsize=legendtext)

        a1.set_ylim((0, a1.get_ylim()[1]))
        pyplot.ylabel('W m-2', fontsize=titletext)

        # 2: Building QF, broken down by sector
        domelec = "firebrick"
        domgas =  "red" # Reds for domestic
        eco7 = "salmon"
        indelec =  "navy"# Blues for industrial
        indgas =  "royalblue"
        other =  "grey" # Grey for other
        colourOrder2 = [domelec, domgas, eco7, indelec, indgas, other]
        a2 = pyplot.subplot(412)
        a2.stackplot(result.index, np.array(result["ElDmUnr"]).astype('float'),
                     np.array(result["GasDm"]).astype('float'),
                     np.array(result["ElDmE7"]).astype('float'),
                     np.array(result["ElId"]).astype('float'),
                     np.array(result["GasId"]).astype('float'),
                     np.array(result["OthrId"]).astype('float'),
                     linewidth=0,
                     colors=colourOrder2)
        pyplot.title('Buildings', fontsize=titletext)
        rects2 = map(makeRect, colourOrder2)
        a2.legend(rects2, ('Dom E', 'Dom G', 'Eco 7', 'Ind E', 'Ind G', 'Oth'), loc='best', fontsize=legendtext)
        a2.set_ylim((0, a2.get_ylim()[1]))
        pyplot.ylabel('W m-2', fontsize=titletext)

        # 3: Building QF, broken down by sector
        mcyc = "firebrick" # Reds for people transport
        taxi =  "red"
        car = "salmon"
        bus =  "grey" # Grey bus
        lgv =  "navy"# Blues for goods transport
        rigd =  "royalblue"
        art =  "steelblue"

        colourOrder3 = [mcyc, taxi, car, bus, lgv, rigd, art]
        a3 = pyplot.subplot(413)
        a3.stackplot(result.index,
                     np.array(result["Mcyc"]).astype('float'),
                     np.array(result["Taxi"]).astype('float'),
                     np.array(result["Car"]).astype('float'),
                     np.array(result["Bus"]).astype('float'),
                     np.array(result["LGV"]).astype('float'),
                     np.array(result["Rigd"]).astype('float'),
                     np.array(result["Art"]).astype('float'),
                     linewidth=0,
                     colors=colourOrder3)
        a3.set_ylim((0, a3.get_ylim()[1]))
        # Set X limit to accommodate legend
        pyplot.title('Transport', fontsize=titletext)

        rects3 = map(makeRect, colourOrder3)
        a3.legend(rects3, ('Moto', 'Taxi', 'Car', 'Bus', 'LGV', 'Rigid', 'Artic'), loc='best', fontsize=legendtext)
        pyplot.ylabel('$W m^{-2}$', fontsize=titletext)

        #4 Just overall metabolism
        a4 = pyplot.subplot(414)
        pyplot.plot(result.index, result[self.componentTranslation['Qm (Metabolism)']])
        pyplot.title('Metabolism', fontsize=titletext)
        pyplot.ylabel('W m-2', fontsize=titletext)
        pyplot.xlabel('Time (UTC)', fontsize=titletext)
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
