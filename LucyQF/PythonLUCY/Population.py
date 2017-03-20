from datetime import datetime

from PyQt4.QtCore import QSettings

from DataManagement.SpatialTemporalResampler_LUCY import SpatialTemporalResampler_LUCY
from DataManagement.spatialHelpers import *
from DataManagement.LookupLogger import LookupLogger
class Population:
    # Store spatially and temporally resolved residential  population
    # Provides population density for each feateure
    # Makes heavy use of QGIS API

    def __init__(self, logger=LookupLogger()):
        self.logger = logger
        self.residential = SpatialTemporalResampler_LUCY(logger)

        self.templateShapefile = None
        self.templateEpsgCode = None
        self.templateIdField = None
        self.outputLayer = None  # actual qgsVectorLayer

        # set new QGIS project layers (created herein) to inherit the project EPSG code (initially) to avoid annoying popups
        s = QSettings()
        s.setValue("/Projections/defaultBehaviour", "useProject")

    def setOutputShapefile(self, filename, epsgCode, id_field=None):
        # Associate the same output shapefile with all the constituents
        self.residential.setOutputShapefile(filename, epsgCode, id_field)

    # SETTERS
    def setResPop(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        '''
        Add and disaggregate residential population shapefile, which will be used as of startTime
        Population field is named by attributeToUse
        :param input: Shapefile path, layer or single float value
        :param startTime: datetime: Date from which to use this input data
        :param attributeToUse: Attribute containing residential population
        :param inputFieldId: Str field name containing unique IDs for this shapefile
        :param weight_by: (optional) Name of output layer attribute to weight by when disaggregating
        :param epsgCode: EPSG code of input layer
        :return: QgsVectorLayer of disaggregated data
        '''
        return self.residential.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)

    def injectResPop(self, input, startTime, attributeToUse, epsgCode=None):
        '''
        Adds a shapefile layer to the object - performs NO DISAGGREGATION. Spatial units must already be identical to
         the output layer
        :param input: Shapefile path, layer or single float value
        :param startTime: datetime: Date from which to use this input data
        :param attributeToUse: Attribute containing residential population
        :param weight_by: (optional) Name of output layer attribute to weight by when disaggregating
        :param epsgCode: EPSG code of input layer
        :return: QgsVectorLayer of input data
        '''
        return self.residential.injectInput(input, epsgCode, attributeToUse, startTime)

    # GETTERS

    def getOutputLayer(self):
        # Gets the output layer
        if self.residential.outputLayer is not None:
            return self.residential.outputLayer
        else:
            raise Exception('The output layer has not yet been set!')

    def getPopTable(self, requestDate, popType):
        # Get pandas data frame of population density (/m2) for each feature on requested date

        if type(popType) is not list:
            popType = [popType]

        types = []
        typeLabels = []

        if 'res' in popType:
            types.append(self.residential.getTableForDate(requestDate))
            typeLabels.append('Residential')

        if len(types) > 1:
            combined_refined = pd.concat(types, axis=1)
        else:
            combined_refined = types[0]

        combined_refined.columns = typeLabels

        # Convert to population density
        combined_refined = combined_refined.divide(self.residential.getAreas(), axis='index')
        return combined_refined

    def getResPopValue(self, featureId, requestDate):
        # Returns the value of residential population density (/m2) for the given feature ID and date
        table = self.getPopTable(requestDate, 'res')
       # if featureId not in table.index:
       #     raise ValueError('Index ' + featureId + ' not found in population table')
        return table['Residential'][featureId]

    ### Getters for individual layers - convert kWh/year/feature to W/m2 in each feature ###

    def getResPopLayer(self, requestDate):
        # Return QGSVectorLayer for residential population (NOT DENSITY) on specified requestDate
        (layer, attrib) = self.residential.getLayerForDate(requestDate)
        return  (layer, attrib)
