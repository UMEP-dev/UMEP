from __future__ import print_function
from __future__ import absolute_import
from builtins import object
from datetime import datetime
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.SpatialTemporalResampler import SpatialTemporalResampler
from .DataManagement.spatialHelpers import *
from qgis.PyQt.QtCore import QSettings


class TransportEnergyData(object):
    # Read in raw transport inputs (a mixture of single values, spatial polygons and point counts)
    # and produce energy estimates in spatial units as specified by a template shapefile

    def __init__(self, logger=LookupLogger()):

        self.logger = logger

        self.roadLengths = SpatialTemporalResampler(logger=self.logger)
        self.vehicleOwnership = SpatialTemporalResampler(logger=self.logger)
        self.energy = SpatialTemporalResampler(logger=self.logger) # TODO: Remove this because we want to calculate it

        self.templateShapefile = None
        self.templateEpsgCode = None
        self.templateIdField = None
        self.outputLayer = None  # actual qgsVectorLayer

        # set new QGIS project layers (created herein) to inherit the project EPSG code (initially) to avoid annoying popups
        s = QSettings()
        s.setValue("/Projections/defaultBehaviour", "useProject")

    def setOutputShapefile(self, filename, epsgCode, id_field=None):
        # Associate the same output shapefile with all the constituents
        self.roadLengths.setOutputShapefile(filename, epsgCode, id_field)
        self.vehicleOwnership.setOutputShapefile(filename, epsgCode, id_field)
        self.energy.setOutputShapefile(filename, epsgCode, id_field)

    # SETTERS
    # Add an road length summary layer with its start time
    def setRoadLengths(self, input, startTime, attributeToUse, weight_by=None, epsgCode=None):
        self.roadLengths.addInput(input, startTime, attributeToUse, weight_by=weight_by, epsgCode=epsgCode)

    def setVehicleOwnership(self, input, startTime, attributeToUse, weight_by=None, epsgCode=None):
        self.vehicleOwnership.addInput(input, startTime, attributeToUse, weight_by=weight_by, epsgCode=epsgCode)

    def calculateEnergy(self):
        # Take the inputs for the given time period and calculate energy use for each vehicle type. Produce new shapefile layer.
        raise Exception('SOMETHING MAGICAL HAPPENS HERE BUT IT IS NOT YET IMPLEMENTED')

    # GETTERS
    def getEnergyTable(self, requestDate):
        # TODO: Make this use the actual inputs instead of the cheating energy-only version
        # Get pandas data frame of energy by vehicle type (columns) and spatial area index (rows)
        combined_refined = 0
        #table = self.vehicleOwnership.getTableForDate()
        #print 'PRODUCING TEST DATA FOR TRANSPORT'

        a = self.energy.getTableForDate(requestDate)
        a.columns = ['motorcycles', 'taxi', 'car', 'bus', 'lgv', 'rigid',  'artic']  # Can be found in QGIS > view attributes table
        # TODO: Get proper energies and then normalize by area
        #areas = pd.Series(feature_areas(self.domElec.outputLayer))
        #areas.index = self.workday.featureMapper[areas.index]
        return a

    def getOutputLayer(self):
        # Gets the output layer
        if self.energy.outputLayer is not None:
            return self.energy.outputLayer
        else:
            raise Exception('The output layer has not yet been set!')

    def getMotorcycles(self, featureId, requestDate):
        # Returns the value of domestic electricity usage (kWh/m2) for the given feature ID and date
        table = self.getEnergyTable(requestDate)
        return table['motorcycles'][featureId]
        #if featureId not in table.index:
        #    raise ValueError('Index ' + featureId + ' not found in domestic electricity table')
        #return ['DomElec', featureId]

    def getTaxis(self, featureId, requestDate):
        table = self.getEnergyTable(requestDate)
        return table['taxi'][featureId]

    def getCars(self, featureId, requestDate):
        table = self.getEnergyTable(requestDate)
        return table['car'][featureId]

    def getBuses(self, featureId, requestDate):
        table = self.getEnergyTable(requestDate)
        return table['bus'][featureId]

    def getLVGs(self, featureId, requestDate):
        table = self.getEnergyTable(requestDate)
        return table['lgv'][featureId]

    def getRigids(self, featureId, requestDate):
        table = self.getEnergyTable(requestDate)
        return table['rigid'][featureId]

    def getArtics(self, featureId, requestDate):
        table = self.getEnergyTable(requestDate)
        return table['artic'][featureId]

    def convertToEnergyDensity(self, layer, attrib):
        # Scale this to get W/m2 rather than kWh/yr
        layer = convert_to_spatial_density(layer, attrib)
        layer = multiply_shapefile_attribute(layer, attrib, 1000.0 / (365.25 * 24))
        return layer

    # TODO: REMOVE THESE AND REPLACE WITH CALCULATIONS
    def setEnergy(self, input, startTime, attributeToUse, weight_by=None, epsgCode=None):
        self.energy.addInput(input, startTime, attributeToUse, weight_by=weight_by, epsgCode=epsgCode)

def testIt():
    # Set up output polygons
    a = TransportEnergyData()
    LLSOApolygons = 'C:\Users\pn910202\Dropbox\Shapefilecombos\PopDens\PopDens_2014_LSOA.shp'
    LLSOAproj = 27700
    a.setOutputShapefile(LLSOApolygons, LLSOAproj, id_field="LSOA11CD")

    # Domestic gas shapefile - must be kWh/year
    trans = {}
    trans['shapefile'] = 'C:\\Users\\pn910202\\Dropbox\\Shapefilecombos\\Transport\\08transport.shp'
    trans['epsg'] = 27700
    trans['field_to_use'] = ['Motorc', 'Taxi', 'Cars', 'Bus', 'LGV', 'HGVRig', 'HGVArt']  # Can be found in QGIS > view attributes table
    trans['start_date'] = datetime.strptime('2008-01-01', '%Y-%m-%d')
    a.setEnergy(trans['shapefile'], trans['start_date'], trans['field_to_use'], epsgCode=trans['epsg'])
    # Get downscaled shapefiles for 2014
    # fix_print_with_import
    print(a.getEnergyTable(datetime.strptime('2013-01-01', '%Y-%m-%d')))

