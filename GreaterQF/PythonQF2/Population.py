from datetime import datetime
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.SpatialTemporalResampler import SpatialTemporalResampler
from .DataManagement.spatialHelpers import *
from qgis.PyQt.QtCore import QSettings
class Population:
    # Store spatially and temporally resolved residential and workday population
    # Provides population density for each feateure
    # Makes heavy use of QGIS API

    def __init__(self, logger=LookupLogger()):
        self.logger = logger
        self.residential = SpatialTemporalResampler(logger)
        self.workday = SpatialTemporalResampler(logger)

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
        self.workday.setOutputShapefile(filename, epsgCode, id_field)

    # SETTERS
    def setResPop(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        '''
        Add and disaggregate residential population shapefile, which will be used as of startTime
        Population field is named by attributeToUse
        :param input: Shapefile path, layer or single float value
        :param startTime: datetime: Date from which to use this input data
        :param attributeToUse: Attribute containing residential population
        :param inputFieldId: Attribute containing unique ID
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


    def setWorkPop(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        '''
        Add and disaggregate workday population shapefile, which will be used as of startTime
        Population field is named by attributeToUse
        :param input: Shapefile path, layer or single float value
        :param startTime: datetime: Date from which to use this input data
        :param attributeToUse: Attribute containing residential population
        :param inputFieldId: Attribute containing unique ID
        :param weight_by: (optional) Name of output layer attribute to weight by when disaggregating
        :param epsgCode: EPSG code of input layer
        :return: QgsVectorLayer of disaggregated data
        '''

        return self.workday.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)

    def injectWorkPop(self, input, startTime, attributeToUse, epsgCode=None):
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
        return self.workday.injectInput(input, epsgCode, attributeToUse, startTime)

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
        if 'work' in popType:
            types.append(self.workday.getTableForDate(requestDate))
            typeLabels.append('Workday')
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

    def getWorkPopValue(self, featureId, requestDate):
        # Returns the value of industrial gas usage (kWh/m2) for the given feature ID and date
        table = self.getPopTable(requestDate, 'work')
        #if featureId not in table.index:
        #    raise ValueError('Index ' + featureId + ' not found in population table')
        return table['Workday'][featureId]

    ### Getters for individual layers - convert kWh/year/feature to W/m2 in each feature ###
    def getWorkPopLayer(self, requestDate):
        # Return QGSVectorLayer for workplace population (NOT DENSITY) on specified requestDate
        (layer, attrib) = self.workday.getLayerForDate(requestDate)
        return (layer, attrib)

    def getResPopLayer(self, requestDate):
        # Return QGSVectorLayer for residential population (NOT DENSITY) on specified requestDate
        (layer, attrib) = self.residential.getLayerForDate(requestDate)
        return  (layer, attrib)



def testIt():
    # Set up output polygons
    a = Population()
    LLSOApolygons = 'C:\\Users\\pn910202\\Dropbox\\Shapefilecombos\\PopDens\\PopDens_2014_LSOA.shp'
    LLSOAproj = 27700
    a.setOutputShapefile(LLSOApolygons, LLSOAproj, id_field="LSOA11CD")

    # Raw residential population data in OAs
    resid = {}
    resid['shapefile'] = 'C:\\Users\\pn910202\\Dropbox\\Shapefilecombos\\populations\\popOA2014.shp'
    resid['epsg'] = 27700
    resid['field_to_use'] = 'Pop'  # Can be found in QGIS > view attributes table
    resid['start_date'] = datetime.strptime('2014-01-01', '%Y-%m-%d')

    # Raw workplace population data in LSOAs
    wp = {}
    wp['shapefile'] = 'C:\\Users\\pn910202\\Dropbox\\Shapefilecombos\\PopDens\\PopDens_2014_LSOA.shp'
    wp['epsg'] = 27700
    wp['field_to_use'] = 'WorkPop'  # Can be found in QGIS > view attributes table
    wp['start_date'] = datetime.strptime('2014-01-01', '%Y-%m-%d')

    # Set simple values for each component for 2014
    a.setResPop(resid['shapefile'], resid['start_date'], resid['field_to_use'], epsgCode=resid['epsg'])
    a.setWorkPop(wp['shapefile'], wp['start_date'], wp['field_to_use'], epsgCode=wp['epsg'])

    # Get downscaled shapefiles for 2014
    print(a.getPopTable(datetime.strptime('2013-01-01', '%Y-%m-%d')))

    return a.getResPopLayer(datetime.strptime('2014-01-01', '%Y-%m-%d'))
