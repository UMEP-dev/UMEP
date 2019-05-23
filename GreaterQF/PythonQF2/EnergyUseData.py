from datetime import datetime
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.SpatialTemporalResampler import SpatialTemporalResampler
from .DataManagement.spatialHelpers import *
from qgis.PyQt.QtCore import QSettings

class EnergyUseData:
    # Store spatially and temporally resolved energy use data for GreaterQF model
    # Makes heavy use of QGIS API

    def __init__(self, logger=LookupLogger()):
        '''
        :param logger: LookupLogger object (optional)
        '''

        self.logger = logger

        self.domGas = SpatialTemporalResampler(self.logger)
        self.indGas = SpatialTemporalResampler(self.logger)
        self.domElec = SpatialTemporalResampler(self.logger)
        self.indElec = SpatialTemporalResampler(self.logger)
        self.economy7Elec = SpatialTemporalResampler(self.logger)

        self.templateShapefile = None
        self.templateEpsgCode = None
        self.templateIdField = None

        # set new QGIS project layers (created herein) to inherit the project EPSG code (initially) to avoid annoying popups
        s = QSettings()
        s.setValue("/Projections/defaultBehaviour", "useProject")

    def setOutputShapefile(self, layer, epsgCode, id_field):
        '''
        Associate an output layer (or shapefile filename containing the layer) with all the constituents
        :param layer: filename or QgsVectorLayer containing output features
        :param epsgCode: EPSG code (numeric) of layer
        :param id_field: field (attribute) name containing unique identifiers
        :return: None
        '''
        self.domGas.setOutputShapefile(layer, epsgCode, id_field)
        self.indGas.setOutputShapefile(layer, epsgCode, id_field)
        self.domElec.setOutputShapefile(layer, epsgCode, id_field)
        self.indElec.setOutputShapefile(layer, epsgCode, id_field)
        self.economy7Elec.setOutputShapefile(layer, epsgCode, id_field)

    # SETTERS
    # Add an energy consumption electricity layer with its start time
    def setDomesticElec(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        '''
        Take a Shapefile (filename), QgsVectorLayer or single value for domestic electricity consumption (annual)
         and spatially disaggregate the chosen attribute across the output area based (optionally) on an attribute
         of the output areas
        :param input: filename, float or QgsVectorLayer of data to disaggregate
        :param startTime: Time as of when to use this data
        :param attributeToUse: Attribute of input data to disaggregate
        :param weight_by: Attribute of output layer to weight by when disaggregating
        :param epsgCode: EPSG code of input layer
        :param inputFieldId: Name of field in shapefile containing unique identifiers for each feature
        :return: QgsVectorLayer of disaggregated ata
        '''
        return self.domElec.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)

    def injectDomesticElec(self, input, startTime, attributeToUse, epsgCode=None):
        '''
        Does everything setDomesticElec does, except without the disaggregation.
        The data must use the exact same spatial units as the output areas
        :param input: Filename of shapefile
        :param startTime: Date from which to use this data
        :param attributeToUse: Attribute to extract from shapefile
        :param epsgCode: EPSG code of shapefile
        :return: QgsVectorLayer of the shapefile injected
        '''
        return self.domElec.injectInput(input, epsgCode, attributeToUse, startTime)

    def setIndustrialElec(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        return self.indElec.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)
    def injectIndustrialElec(self, input, startTime, attributeToUse, epsgCode=None):
        return self.indElec.injectInput(input, epsgCode, attributeToUse, startTime)

    def setDomesticGas(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        return self.domGas.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)
    def injectDomesticGas(self, input, startTime, attributeToUse, epsgCode=None):
        return self.domGas.injectInput(input, epsgCode, attributeToUse, startTime)

    def setIndustrialGas(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        return self.indGas.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)
    def injectIndustrialGas(self, input, startTime, attributeToUse, epsgCode=None):
        return self.indGas.injectInput(input, epsgCode, attributeToUse, startTime)

    def setEconomy7Elec(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        return self.economy7Elec.addInput(input, startTime, attributeToUse, inputFieldId, weight_by=weight_by, epsgCode=epsgCode)
    def injectEconomy7Elec(self, input, startTime, attributeToUse, epsgCode=None):
        return self.economy7Elec.injectInput(input, epsgCode, attributeToUse, startTime)


    # GETTERS
    def getEnergyTable(self, requestDate, energyType):
        # Get pandas data frame of all energy usage for requested date and for requested energy type(s)
        if type(energyType) is not type(list()):
            energyType = [energyType]

        types = []
        typeLabels = []
        #self.logger.addEvent('Lookup', requestDate.date(), None, str(typeLabels), 'Requesting energy data from shapefile attributes')
        if 'de' in energyType:
            de = self.domElec.getTableForDate(requestDate)
            # print(type(de*1))
            # print(de.values)
            # print(de.values[0])
            # print(type(de.values[0,0]))
            # print(type(de.values[0,0]+1))
            # print(de.values[0, 0])
            # print(de.values[0, 0]+1)
            # for x in de.values.flat:
            #     if not isinstance(x,float):
            #         print(x)
            #         print(type(x))
            # val = np.array([x if isinstance(x,float) else np.nan for x in de.values.flat]).reshape(-1, 1)
            # de = pd.DataFrame(val, index=de.index, columns=de.columns)
            # print(type(val[0,0]))
            types.append(de)
            typeLabels.append('DomElec')

        if 'ig' in energyType:
            ig = self.indGas.getTableForDate(requestDate)
            #print('ig',ig.values[0, 0])
            types.append(ig)
            typeLabels.append('IndGas')

        if 'ie' in energyType:
            ie = self.indElec.getTableForDate(requestDate)
            #print('ie', ie.values[0, 0])
            types.append(ie)
            typeLabels.append('IndElec')

        if 'dg' in energyType:
            dg = self.domGas.getTableForDate(requestDate)
            #print('dg', dg.values[0, 0])
            types.append(dg)
            typeLabels.append('DomGas')

        if 'e7' in energyType:
            e7 = self.economy7Elec.getTableForDate(requestDate)
            #print('e7', e7.values[0, 0])
            types.append(e7)
            typeLabels.append('Eco7')

        if len(types) > 1:
            combined_refined = pd.concat(types, axis=1)
        else:
            combined_refined = types[0]


        combined_refined.columns = typeLabels
        # Since energy data is all still kWh/year, convert it to W
        # print(combined_refined.dtype, type(combined_refined))
        combined_refined = combined_refined.astype('float') * 1000 / (365.25 * 24)
        # print('seems pass',1/0)

        # And normalise by area of each polygon to get W/m2
        combined_refined = combined_refined.divide(self.domElec.getAreas(), axis='index')
        self.logger.addEvent('Lookup', requestDate.date(), None, str(typeLabels), 'Converting from kWh/yr to W/m2')
        return combined_refined

    def getOutputLayer(self):
        # Gets the output layer
        if self.domElec.outputLayer is not None:
            return self.domElec.outputLayer
        else:
            raise Exception('The output layer has not yet been set!')

    def getDomesticElecValue(self, featureId, requestDate):
        # Returns the value of domestic electricity usage (kWh/m2) for the given feature ID and date
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        table = self.getEnergyTable(requestDate, 'de')
        return table['DomElec'][featureId]

    def getIndustrialGasValue(self, featureId, requestDate):
        # Returns the value of industrial gas usage (kWh/m2) for the given feature ID and date
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()
        table = self.getEnergyTable(requestDate, 'ig')
        return table['IndGas'][featureId]

    def getIndustrialElecValue(self, featureId, requestDate):
        # Returns the value of industrial electricity usage for the given feature ID and date
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()
        table = self.getEnergyTable(requestDate, 'ie')
        return table['IndElec'][featureId]

    def getDomesticGasValue(self, featureId, requestDate):
        # Returns the value of domestic gas usage for the given feature ID and date
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()
        table = self.getEnergyTable(requestDate, 'dg')
        return table['DomGas'][featureId]

    def getEconomy7ElecValue(self, featureId, requestDate):
        # Returns the value of domestic economy 7 usage for the given feature ID and date
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()
        table = self.getEnergyTable(requestDate, 'e7')
        return table['Eco7'][featureId]

    def getIndustrialOtherValue(self, featureId, requestDate):
        # TODO: IMplement this if needed
        return 0

    def convertToEnergyDensity(self, layer, attrib):
        # Scale this to get W/m2 rather than kWh/yr
        layer = convert_to_spatial_density(layer, attrib)
        layer = multiply_shapefile_attribute(layer, attrib, 1000.0 / (365.25 * 24))
        return layer

    ### Getters for individual layers - convert kWh/year/feature to W/m2 in each feature ###
    def getDomesticElecLayer(self, requestDate):
        (layer, attrib) = self.domElec.getLayerForDate(requestDate)
        return (layer, attrib)

    def getIndustrialElecLayer(self, requestDate):
        (layer, attrib) = self.indElec.getLayerForDate(requestDate)
        return (layer, attrib)

    def getDomesticGasLayer(self, requestDate):
        (layer, attrib) = self.domGas.getLayerForDate(requestDate)
        return (layer, attrib)

    def getIndustrialGasLayer(self, requestDate):
        (layer, attrib) = self.indGas.getLayerForDate(requestDate)
        return (layer, attrib)

    def getEconomy7ElecLayer(self, requestDate):
        (layer, attrib) = self.economy7Elec.getLayerForDate(requestDate)
        return (layer, attrib)


def testIt():
    # Set up output polygons
    a = EnergyUseData()
    LLSOApolygons = 'C:\\Users\pn910202\Dropbox\Shapefilecombos\PopDens\PopDens_2014_LSOA.shp'
    LLSOAproj = 27700
    a.setOutputShapefile(LLSOApolygons, LLSOAproj, id_field="LSOA11CD")
    MSOApolygons = 'N:/GreaterQF_input/GreaterLondon_Shapefiles/MSOA/MSOA_2011_London_gen_MHW.shp'
    MSOAproj = 27700

    # Domestic gas shapefile - must be kWh/year
    domestic_gas = {}
    domestic_gas['shapefile'] = 'C:\\Users\pn910202\Dropbox\Shapefilecombos\LSOA_elec_gas_2014\LSOA_elec_gas_2014.shp'
    domestic_gas['epsg'] = 27700
    domestic_gas['field_to_use'] = 'GasDom'  # Can be found in QGIS > view attributes table
    domestic_gas['start_date'] = datetime.strptime('2014-01-01', '%Y-%m-%d')

    # Domestic electricity - must be kWh/year
    domestic_elec = {}
    domestic_elec['shapefile'] = 'C:\\Users\pn910202\Dropbox\Shapefilecombos\LSOA_elec_gas_2014\LSOA_elec_gas_2014.shp'
    domestic_elec['epsg'] = 27700
    domestic_elec['field_to_use'] = 'TElDom'  # Can be found in QGIS > view attributes table
    domestic_elec['start_date'] = datetime.strptime('2014-01-01', '%Y-%m-%d')

    # Industrial gas - must be kWh/year
    industrial_gas = {}
    industrial_gas['shapefile'] = 'C:\\Users\pn910202\Dropbox\Shapefilecombos\MSOA_elec_gas_2014\MSOA_elec_gas_2014.shp'
    industrial_gas['epsg'] = 27700
    industrial_gas['field_to_use'] = 'GasInd'  # Can be found in QGIS > view attributes table
    industrial_gas['start_date'] = datetime.strptime('2014-01-01', '%Y-%m-%d')

    # Industrial Electricity - must be kWh/year
    industrial_elec = {}
    industrial_elec['shapefile'] = 'C:\\Users\pn910202\Dropbox\Shapefilecombos\LA_energy_2014\LA_energy_2014.shp'
    industrial_elec['epsg'] = 4326
    industrial_elec['field_to_use'] = 'ElInd_kWh'  # Can be found in QGIS > view attributes table
    industrial_elec['start_date'] = datetime.strptime('2014-01-01', '%Y-%m-%d')

    # Set simple values for each component for 2014
    a.setDomesticElec(domestic_elec['shapefile'], datetime.strptime('2014-01-01', '%Y-%m-%d'),
                      domestic_elec['field_to_use'], epsgCode=domestic_elec['epsg'])
    a.setDomesticGas(1.0, datetime.strptime('2014-01-01', '%Y-%m-%d'), 'DomGas',)
    a.setIndustrialElec(2.0, datetime.strptime('2014-01-01', '%Y-%m-%d'), 'DomGas')
    a.setIndustrialGas(3.0, datetime.strptime('2014-01-01', '%Y-%m-%d'), 'DomGas')
    a.setEconomy7Elec(7.0, datetime.strptime('2014-01-01', '%Y-%m-%d'), 'DomGas')
    # Get downscaled shapefiles for 2014
    print(a.getEnergyTable(datetime.strptime('2013-01-01', '%Y-%m-%d')))

    return a.getDomesticElecLayer(datetime.strptime('2014-01-01', '%Y-%m-%d'))
