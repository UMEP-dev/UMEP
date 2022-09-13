from datetime import datetime as dt
from .string_func import lower
from .DataManagement.LookupLogger import LookupLogger
from .DataManagement.SpatialTemporalResampler import SpatialTemporalResampler
from .DataManagement.spatialHelpers import *
from qgis.core import QgsSpatialIndex
from shutil import rmtree


class Transport():
    '''Produce transport energy data based on input vector map of road segments, along with traffic data'''

    def __init__(self, fuelConsumption, modelParams, logger=LookupLogger()):
        '''
        :param fuelConsumption: FuelConsumption: Populated GQF fuel consumption object
        :param modelParams: Parameters: Populated GQF Model parameters
        :param logger: LookupLogger object (optional) to record the results of disaggregations and lookups
        '''
        self.logger = logger
        self.modelParams = modelParams
        self.fc = fuelConsumption
        self.transport = SpatialTemporalResampler(logger=logger)
        # If traffic flow data for each road segment is broken down by vehicle, two sets of vehicle types are accepted
        # 1. The most detailed breakdown (by vehicle) of traffic counts. Based on LAEI data.
        self.completeInputs = ['diesel_car', 'petrol_car', 'diesel_lgv',
                               'petrol_lgv', 'motorcycle', 'taxi', 'bus', 'coach', 'rigid', 'artic']
        # 2. A less specific breakdown that matches the model outputs.
        self.modelledTypes = ['car', 'lgv', 'motorcycle',
                              'taxi', 'bus', 'rigid', 'artic']
        # The road type headings used internally by the model
        self.roadTypes = ['motorway', 'primary_road', 'secondary_road']

        # The methods in this object manufacture a shapefile of fuel consumption in each area. The names of the fields:
        self.dieselNames = {'motorcycle': '_FC_Dmcyc', 'artic': '_FC_Dart', 'rigid': '_FC_Drig',
                            'taxi': '_FC_Dtaxi', 'car': '_FC_Dcar', 'bus': '_FC_Dbus', 'lgv': '_FC_Dlgv'}
        self.petrolNames = {'motorcycle': '_FC_Pmcyc', 'artic': '_FC_Part', 'rigid': '_FC_Prig',
                            'taxi': '_FC_Ptaxi', 'car': '_FC_Pcar', 'bus': '_FC_Pbus', 'lgv': '_FC_Plgv'}

    # SETTERS
    def setOutputShapefile(self, filename, epsgCode, id_field):
        # Associate the same output shapefile with all the constituents
        self.transport.setOutputShapefile(filename, epsgCode, id_field)

    def validateInputs(self, startTime, shapefile, epsgCode, roadTypeField, roadTypeNames):
        # Validate the initial inputs to the Transport object
      # Validate the start time
        if type(startTime) is not type(dt.now()):
            raise ValueError('Start time must be a DateTime object')

        if startTime.tzinfo is None:
            raise ValueError('Start time must have a timezone attached')

        # Validate the state of the transport object
        if self.transport.outputLayer == None:
            raise Exception(
                'Output shapefile must be set before adding any input vector layers')

        # Validate shapefile filename
        if type(shapefile) is not type(''):
            raise ValueError(
                'Shapefile filename (' + str(shapefile) + ') is not a string')

        if not os.path.exists(shapefile):
            raise ValueError(
                'Shapefile  (' + str(shapefile) + ') does not exist')

        try:
            epsgCode = float(epsgCode)
        except Exception:
            raise ValueError(
                'Numeric EPSG code of input shapefile must be provided')

        if type(roadTypeField) is not str:
            raise ValueError(
                'Name of attribute containing road classification must be a string')

        # Check the list of identifiers for road types contain all three types
        matchingRoadClasses = set(self.roadTypes).difference(
            list(roadTypeNames.keys()))
        if len(matchingRoadClasses) > 0:
            raise ValueError(
                'Dict containing road class identifiers must have keys: ' + str(self.roadTypes))

    def injectFuelConsumption(self, filename, startDate, epsgCode):
        '''
        Add a pre-prepared (by this object) disaggregated map of fuel consumption.
        Shapefile must be EXACTLY on-spec, having the same output areas as the output layer, and the same attribute
        names that this object assigns for all vehicle types
        :param filename: Filename of shapefile to load
        :param startDate: dateTime of the date from which to use this shapefile
        :param epsgCode: EPSG code of shapefile
        :return: QgsVectorLayer of the shapefile provided
        '''
        allFuelFields = list(self.dieselNames.values())
        allFuelFields.extend(list(self.petrolNames.values()))
        return self.transport.injectInput(filename, epsgCode, allFuelFields, startDate)

    def addTransportData(self, shapefile, startTime, epsgCode, roadTypeField, roadTypeNames, inputIdField, speedDataField=None, speedConversionFactor=None, totalAADTField=None, vAADTFields=None):
        ''' Adds transport data to the object, associates it with a start time and calculates disaggregated hourly mean transport QF
        :param shapefile: string: path to input shapefile
        :param startTime: datetime: time from which this data should be used
        :param roadTypeField: string: Attribute containing the road classification
        :param roadTypeNames: dict: How the main road types are identified in the shapefile {'motorway':str, 'primary_road':str, 'secondary_road':str}
        :param inputIdField: str: Name of shapefile field containing unique identifiers for each road segment
        :param speedDataField: str: shapefile attribute containing speed data (None if not available)
        :param speedConversionFactor: float: if speed is read from shapefile, multiply it by this factor to convert it to km/h
        :param totalAADTField: str: shapefile attribute containing total Annual Averaged Daily Total traffic count (total across all vechile types) (None if not available)
        :param vADDTflds: dict: shapefile attributes to use for each separate vehicle type's AADT
            Two variants allowed, one with separate fuels for LGVs and cars, and one without:
            Allowed keys 1: diesel_car, petrol_car, diesel_lgv, petrol_lgv, motorcycle, taxi, bus, coach, rigid, artic
            Allowed keys 2: total_car, total_lgv, motorcycle, taxi, bus, coach, rigid, artic
        :param epsgCode: int: EPSG code of shapefile
        :return: QgsVectorLayer: Mean hourly transport heat flux in each output area polygon
        '''

        # Flags to identify the level of detail of the input data
        speedDataAvailable = False   # Mean traffic speed available for each road segment
        # AADT is broken down into the vehicles listed in completeInputs
        completeInputAADTprovided = False
        # AADT data is broken down into the vehicles listed in modelledTypes
        modelledTypesAADTprovided = False
        self.validateInputs(startTime, shapefile, epsgCode,
                            roadTypeField, roadTypeNames)

        # This is a way to look up our version of the road type, given the shapefile's version of the road type
        roadTypeLookup = {roadTypeNames[key]: key for key in self.roadTypes}
        # For all other road types that don't match the above
        roadTypeLookup['other'] = 'other'

        # Establish what speed data is available
        # TODO: Use speed in fuel efficiency lookup
        # Master list of all the fields to sample from the shapefile. Gets built up as we go along...
        fieldsToSample = [roadTypeField]

        if type(speedDataField) is str:
            speedDataAvailable = True
            try:
                speedConversionFactor = float(speedConversionFactor)
            except Exception:
                raise ValueError('Vehicle speed multiplier must be a number')
            fieldsToSample.append(speedDataField)

        # Establish what AADT data is available
        if type(totalAADTField) is str:
            fieldsToSample.append(totalAADTField)

        # Validate fields for AADT by vehicle type, if it was provided
        if type(vAADTFields) is dict:
            allowedKeys1 = self.completeInputs
            allowedKeys2 = self.modelledTypes
            missingFrom1 = list(
                set(allowedKeys1).difference(list(vAADTFields.keys())))
            missingFrom2 = list(
                set(allowedKeys2).difference(list(vAADTFields.keys())))
            if len(missingFrom1) == 0:
                completeInputAADTprovided = True
            elif len(missingFrom2) == 0:
                modelledTypesAADTprovided = True
            else:
                raise ValueError('The vehicle AADT field names provided are incomplete. Expected: ' + str(
                    allowedKeys1) + ' OR ' + str(allowedKeys2) + '. Got: ' + str(list(vAADTFields.keys())))
            fieldsToSample.extend(list(vAADTFields.values()))

        # Make a copy of the shapefile in a temp folder (we wish to change it)
        # Ensure the input layer has the right projection when it gets there
        shapefile = reprojectVectorLayer(
            shapefile, self.transport.templateEpsgCode)
        #inputLayer = loadShapeFile(shapefile)
        inputLayer = openShapeFileInMemory(
            shapefile, self.transport.templateEpsgCode, 'transport')

        try:
            # Try to delete tempfile but don't explode if fail as QGIS sometimes hangs onto them for slightly too long
            rmtree(os.path.dirname(shapefile))
        except:
            pass

        # TODO: Explain to the logger what we are doing with the various fields

        # Get lookup between field names and indices
        fieldNames = {a.name(): i for i, a in enumerate(
            inputLayer.dataProvider().fields())}

        # Check that the requested field names are actually present in the layer
        missingFields = list(
            set(fieldsToSample).difference(list(fieldNames.keys())))
        if len(missingFields) > 0:
            raise ValueError(
                'Some of the transport shapefile fields referenced were not found in the shapefile:' + str(missingFields))

        # Calculate fuel use in each segment
        # TODO 2: Support a vehicle age profile (only a static profile is likely to be tractable)
        # TODO 1: Get this from the parameters file
        # For now, just assumes every vehicle was made in 2005 and looks up values from the fuel consumption object
        vehDate = pd.datetime.strptime('2005-01-01', '%Y-%m-%d')

        # Come up with a read-across between transport road types and euroclass road types
        # Any roads not matching these are assumed to be very minor and are omitted
        # TODO: Refine this treatment

        # Clone the output layer (populate this with [dis]aggregated data) and create spatial index
        outputLayer = duplicateVectorLayer(
            self.transport.outputLayer, targetEPSG=self.transport.templateEpsgCode)
        inputIndex = QgsSpatialIndex()

        for feat in inputLayer.getFeatures():
            inputIndex.addFeature(feat)

        # Get translation to look up internal feature ID based on our preferred ID field
        t = shapefile_attributes(outputLayer)[self.transport.templateIdField]
        featureMapper = pd.Series(index=list(
            map(intOrString, t.values)), data=list(map(intOrString, t.index)))
        t = None

        # Convert road lengths and AADT data to total fuel use each day on each segment of road
        fuelUseDict = calculate_fuel_use(
            inputLayer, inputIdField,
            totalAADTField=totalAADTField,
            roadTypeField=roadTypeField,
            vAADTFields=vAADTFields,
            completeInputs=self.completeInputs,
            modelParams=self.modelParams,
            age=vehDate,
            fuelCon=self.fc,
            roadTypeLookup=roadTypeLookup,
            completeInputAADTprovided=completeInputAADTprovided,
            modelledTypesAADTprovided=modelledTypesAADTprovided)

        fuelUseData = fuelUseDict['fuelUse']
        fuelUseNames = fuelUseDict['names']
        allFuelFields = list(fuelUseNames['petrol'].values())
        allFuelFields.extend(list(fuelUseNames['diesel'].values()))
        # Get road segment lengths inside each output polygon, along with attributes of each of these intersected segments
        intersectedLines = intersecting_amounts(
            [], inputIndex, inputLayer, outputLayer, inputIdField, self.transport.templateIdField)

        # Add total fuel consumption fields to output layer into which fuel consumption will go]
        for newField in allFuelFields:
            outputLayer = addNewField(outputLayer, newField)
        # Find out where new fields reside
        newFieldIndices = [get_field_index(
            outputLayer, fn) for fn in fuelUseData.columns]
        # Refer to everything in terms of field index instead
        fuelUseData.columns = newFieldIndices

        # intersecting_amounts gives us enough information (original segment length and intersected length)
        # to disaggregate fuel use into each output feature, and to calculate total fuel use in each output feature
        areas = self.transport.getAreas()
        outputLayer.startEditing()
        fuelConsumption = pd.DataFrame(
            index=list(intersectedLines.keys()),
            columns=newFieldIndices)  # Results container for each feature
        for outfeat_id in list(intersectedLines.keys()):
            fuelConsumption[:].loc[outfeat_id] = 0

            if len(intersectedLines[outfeat_id]) > 0:
                # If there are any areas intersected by this polygon
                # Total fuel consumption within this output area
                lengths = pd.DataFrame().from_dict(
                    intersectedLines[outfeat_id]).T

                proportionIntersected = lengths['amountIntersected'] / \
                    lengths['originalAmount']
                # Get total of each fuel/vehicle combination by summing across segments in output area
                fuelConsumption[:].loc[outfeat_id] = fuelUseData[:].loc[lengths.index]\
                    .multiply(proportionIntersected, axis=0)\
                    .sum(axis=0, skipna=True)
            # Update shapefile attributes one by one. Doing it in bulk via the dataprovider /should/ work too, but doesn't seem to
            # Convert to kg fuel per square metre of output area too
            [
                outputLayer.changeAttributeValue(
                    featureMapper[outfeat_id],
                    fi,
                    float(fuelConsumption[fi][outfeat_id]
                          )/float(areas[outfeat_id])
                )
                for fi in newFieldIndices
            ]

        outputLayer.commitChanges()

        # This output layer is a set of polygons with associated fuel use and can be treated like any other
        # fuel consumption input shapefile
        confirmedOutput = self.transport.addInput(
            outputLayer, startTime, allFuelFields, self.transport.templateIdField, epsgCode=epsgCode)
        return confirmedOutput

    # GETTERS
    def getFuelConsTable(self, requestDate):
        # Get pandas data frame of fuel consumption [kg] in each output area by fuel and vehicle type
        a = self.transport.getTableForDate(requestDate)
        return a

    def getColumnName(self, vehType, fuelType):
        '''
        Returns the column name for the output of self.getFuelCons() given a vehicle and fuel
        :param vehType: vehicle type (string)
        :param fuelType: fuel ('diesel' or 'petrol)
        :return: String of the column name to use
        '''

        if lower(fuelType) == 'petrol':
            name = self.petrolNames[vehType]
        if lower(fuelType) == 'diesel':
            name = self.dieselNames[vehType]

        return name

    def getOutputLayer(self):
        # Gets the output layer
        if self.transport.outputLayer is not None:
            return self.transport.outputLayer
        else:
            raise Exception('The output layer has not yet been set!')

    def getMotorcycle(self, featureId, fuel, requestDate):
        '''
        Return motorcycle fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="motorcycle")].loc[featureId]

    def getTaxi(self, featureId, fuel, requestDate):
        '''
        Return motorcycle fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="taxi")].loc[featureId]

    def getCar(self, featureId, fuel, requestDate):
        '''
        Return Car fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="car")].loc[featureId]

    def getArtic(self, featureId, fuel, requestDate):
        '''
        Return articulate HGV fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="artic")].loc[featureId]

    def getRigid(self, featureId, fuel, requestDate):
        '''
        Return rigid HGV fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="rigid")].loc[featureId]

    def getBus(self, featureId, fuel, requestDate):
        '''
        Return bus fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="bus")].loc[featureId]

    def getLGV(self, featureId, fuel, requestDate):
        '''
        Return LGV fuel consumption density for this output area [kg/m2] for the requested fuel (diesel or petrol)
        for the given timestamp
        :param fuel: 'petrol' or 'diesel'
        :param timestamp: datetime or pandas.datetime object for the date of the request
        :param featureId: ID of the feature(s) (or the identifying field of the output layer)
        :return: Float or pd.Series of fuel consumption [kg/m2] for feature Id(s) requested
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        return self.getFuelConsTable(requestDate)[self.getColumnName(fuelType=fuel, vehType="lgv")].loc[featureId]
