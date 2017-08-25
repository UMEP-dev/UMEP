from ...Utilities import f90nml as nml
import os
from datetime import datetime as dt
try:
    import numpy as np
except:
    pass
from string import upper, lower

# Validate "shapefile" as either numeric or a valid file location
def validateInput(x):
    try:
        numVal = float(x)
    except Exception:
        if not os.path.exists(x):
            raise ValueError(x + ' could not be found on the filesystem and is not a valid number')

# Convert start dates to datetime
def makeTimey(x):
    return dt.strptime(x, '%Y-%m-%d')

def validFile(x):
    if not os.path.exists(x):
        raise ValueError('The diurnal input file ' + str(x) + ' was not found')

class DataSources:
    ''' Loads the data sources namelist, conducts validation and structures inputs for use with data management routines
    '''
    def __init__(self, configFile):

        self.inputFile = configFile
        # Lists of the config parameters for spatial datasets
        self.outputAreas_spat = []
        self.transport_spat = []
        self.indGas_spat = []
        self.indElec_spat = []
        self.domGas_spat = []
        self.domElec_spat = []
        self.eco7_spat = []
        self.resPop_spat = []
        self.workPop_spat = []

        # And the same for the temporal datasets
        self.dailyEnergy = []
        self.diurnDomElec = []
        self.diurnDomGas = []
        self.diurnIndGas = []
        self.diurnIndElec = []
        self.diurnMetab = []
        self.diurnEco7 = []
        self.diurnalTraffic = []
        self.fuelConsumption = []

        try:
            ds = nml.read(configFile)
        except Exception, e:
            raise ValueError('Unable to read data sources config file at: ' + str(configFile))

        # Are all main entries present?
        # For shapefile inputs
        expectedKeys_spatial = ['outputareas',
                                'annualindgas',
                                'annualindelec',
                                'annualdomgas',
                                'annualdomelec',
                                'annualeco7',
                                'residentialpop',
                                'workplacepop',
                                'transportdata']

        # Which object attributes are populated by which expectedKeys?
        destinations_spatial = {'outputareas':'outputAreas_spat',
                                'annualindgas':'indGas_spat',
                                'annualindelec':'indElec_spat',
                                'annualdomgas':'domGas_spat',
                                'annualdomelec':'domElec_spat',
                                'annualeco7':'eco7_spat',
                                'residentialpop':'resPop_spat',
                                'workplacepop':'workPop_spat',
                                'transportdata':'transport_spat'}

        missing = list(set(expectedKeys_spatial).difference(ds.keys()))
        if len(missing) > 0:
            raise ValueError('Spatial entries missing from ' + str(configFile) + ' in namelist: ' + str(missing))

        # Loop over the spatial data sources to validate
        for subEntry in expectedKeys_spatial:
            content_orig = ds[subEntry]
            # Do string matching, so make it all upper case
            content = {upper(k):content_orig[k] for k in content_orig.keys()}

            # Check it's all lists or no lists
            types = np.unique(map(type, content.values()))
            # are all sub-entries present?
            expectedNames_spat = ['shapefiles', 'startDates', 'epsgCodes', 'attribToUse', 'featureIds']

            if subEntry == "outputareas":                   # Special case for outputAreas
                expectedNames_spat = ['shapefile', 'epsgCode', 'featureids']

            if subEntry == "transportdata":                 #Special case for transportData, which is very complex
                expectedNames_spat = ['shapefiles',
                                      'startDates',
                                      'epsgCodes',
                                      'featureIds',
                                      'speed_available',
                                      'total_AADT_available',
                                      'vehicle_AADT_available',
                                      'class_field',
                                      'motorway_class',
                                      'primary_class',
                                      'secondary_class',
                                      'speed_field',
                                      'speed_multiplier',
                                      'AADT_total',
                                      'AADT_diesel_car',
                                      'AADT_petrol_car',
                                      'AADT_total_car',
                                      'AADT_diesel_LGV',
                                      'AADT_petrol_LGV',
                                      'AADT_total_LGV',
                                      'AADT_motorcycle',
                                      'AADT_taxi',
                                      'AADT_bus',
                                      'AADT_coach',
                                      'AADT_rigid',
                                      'AADT_artic']

            expectedNames_spat = map(upper, expectedNames_spat)
            missing = list(set(map(upper, expectedNames_spat)).difference(content.keys()))
            if len(missing) > 0:
                raise ValueError('Entries missing from ' + subEntry + ' in namelist: ' + str(missing))

            # TODO: Uncomment this when a sensible way of dealing with multiple attributes per time interval is worked out
            # Are all sub-entries consistent lengths?
            #if len(types) > 1 and list in types:
            #    raise ValueError(
            #        'The namelist entries for ' + subEntry + ' have inconsistent lengths: some are lists and some are not')
            #if list not in types:
            for k in content.keys():
                if content[k] == '':
                    content[k] = None
                content[k] = [content[k]]

            #lengths = map(len, content.values())
            #if len(np.unique(lengths)) > 1:
            #    raise ValueError('The namelist entries for ' + subEntry + ' have inconsistent list lengths')

            map(validateInput, content[expectedNames_spat[0]])
            # Validate start dates
            if 'STARTDATES' in content.keys():
                try:
                    content['STARTDATES'] = map(makeTimey, content['STARTDATES'])
                except Exception, e:
                    raise ValueError('One or more startDate entries is not in YYYY-mm-dd format for ' + subEntry + ':' + str(e))

                # Ensure dates within a subentry are unique
                if len(np.unique(content['STARTDATES'])) != len(content['STARTDATES']):
                    raise ValueError('One or more startDates is duplicated for ' + subEntry + ':')

            # Having gotten this far means the entries are valid, so populate the object field
            entries = getattr(self, destinations_spatial[subEntry])

            if subEntry == "outputareas": # Special case for output areas
                entries = {'shapefile': content['SHAPEFILE'][0],
                                 'epsgCode': content['EPSGCODE'][0],
                                 'featureIds': content['FEATUREIDS'][0]}

            elif subEntry == "transportdata": # Special case for transportdate
                dataValues = {'shapefile':content['SHAPEFILES'][i],
                                      'startDate':content['STARTDATES'][i],
                                      'epsgCode':content['EPSGCODES'][i],
                                      'featureIds':content['FEATUREIDS'][i],
                                      'speed_available':content['SPEED_AVAILABLE'][i],
                                      'total_AADT_available':content['TOTAL_AADT_AVAILABLE'][i],
                                      'vehicle_AADT_available':content['VEHICLE_AADT_AVAILABLE'][i],
                                      'class_field':content['CLASS_FIELD'][i],
                                      'motorway_class':content['MOTORWAY_CLASS'][i],
                                      'primary_class':content['PRIMARY_CLASS'][i],
                                      'secondary_class':content['SECONDARY_CLASS'][i],
                                      'speed_field':content['SPEED_FIELD'][i],
                                      'speed_multiplier':content['SPEED_MULTIPLIER'][i],
                                      'AADT_total':content['AADT_TOTAL'][i],
                                      'AADT_diesel_car':content[upper('AADT_diesel_car')][i],
                                      'AADT_petrol_car':content[upper('AADT_petrol_car')][i],
                                      'AADT_total_car':content[upper('AADT_total_car')][i],
                                      'AADT_diesel_LGV':content[upper('AADT_diesel_LGV')][i],
                                      'AADT_petrol_LGV':content[upper('AADT_petrol_LGV')][i],
                                      'AADT_total_LGV':content[upper('AADT_total_LGV')][i],
                                      'AADT_motorcycle':content[upper('AADT_motorcycle')][i],
                                      'AADT_taxi':content[upper('AADT_taxi')][i],
                                      'AADT_bus':content[upper('AADT_bus')][i],
                                      'AADT_coach':content[upper('AADT_coach')][i],
                                      'AADT_rigid':content[upper('AADT_RIGID')][i],
                                      'AADT_artic':content[upper('AADT_ARTIC')][i]}

                validate_transport(dataValues)
                aadtByVehicle =       ['AADT_diesel_car',
                                      'AADT_petrol_car',
                                      'AADT_total_car',
                                      'AADT_diesel_LGV',
                                      'AADT_petrol_LGV',
                                      'AADT_total_LGV',
                                      'AADT_motorcycle',
                                      'AADT_taxi',
                                      'AADT_bus',
                                      'AADT_coach',
                                      'AADT_rigid',
                                      'AADT_artic']

                # Build dict of the available AADT fields
                aadtFields = {}
                for a in aadtByVehicle:
                    if dataValues[a] is not None:
                        aadtFields[lower(a[5:])] = dataValues[a]
                mandatoryFields =  ['shapefile',
                                    'startDate',
                                    'epsgCode',
                                    'featureIds',
                                    'speed_available',
                                    'speed_multiplier',
                                    'AADT_total',
                                    'class_field',
                                    'speed_field']
                structuredData = {}
                for m in mandatoryFields:
                    structuredData[m] = dataValues[m]

                structuredData['AADT_fields'] = aadtFields
                structuredData['road_types'] = {'motorway':dataValues['motorway_class'],
                                                'primary_road':dataValues['primary_class'],
                                                'secondary_road':dataValues['secondary_class']}

                entries.append(structuredData)

            else: # Everything else spatial is a data source
                for i in range(0, len(content['SHAPEFILES']), 1):
                    entries.append({'shapefile': content['SHAPEFILES'][i],
                                    'epsgCode': content['EPSGCODES'][i],
                                    'attribToUse': content['ATTRIBTOUSE'][i],
                                    'featureIds': content['FEATUREIDS'][i],
                                    'startDate': content['STARTDATES'][i]})

            setattr(self, destinations_spatial[subEntry], entries)

        # Now the same for the temporal entries
        destinations_temporal = {'dailyenergyuse': 'dailyEnergy',
                                 'diurnaldomelec': 'diurnDomElec',
                                 'diurnaldomgas': 'diurnDomGas',
                                 'diurnalindgas': 'diurnIndGas',
                                 'diurnalindelec': 'diurnIndElec',
                                 'diurnaleco7': 'diurnEco7',
                                 'diurnaltraffic': 'diurnalTraffic',
                                 'diurnalmetabolism': 'diurnMetab',
                                 'fuelconsumption': 'fuelConsumption'}

        expectedKeys_temporal = destinations_temporal.keys()
        expectedNames_temporal = ['profileFiles']
        missing = list(set(map(upper, expectedKeys_temporal)).difference(map(upper, ds.keys())))

        if len(missing) > 0:
            raise ValueError('Temporal entries missing from ' + str(configFile) + ' in namelist: ' + str(missing))

        for entry in expectedKeys_temporal:
            content = ds[entry]
            # Validate sub-entries
            missing = list(set(map(upper, expectedNames_temporal)).difference(map(upper, content.keys())))
            if len(missing) > 0:
                raise ValueError('Entries missing from ' + entry + ' in namelist: ' + str(missing))

            # Make sure everything is a list or everyting is a string
            types = np.unique(map(type, content.values()))
            if len(types) > 1 and list in types:
                raise ValueError('The namelist entries for ' + entry + ' have inconsistent lengths: some are lists and some are not')
            #if list not in types:
            for k in content.keys():
                # Replace empties with None, and make lists if not lists already
                if len(content[k]) == 0:
                    content[k] = None
                if type(content[k]) is not list:
                    content[k] = [content[k]]

            # Validate filenames
            map(validFile, content['profileFiles'])
            # Having gotten this far means the entries are valid, so populate the object field
            entries = getattr(self, destinations_temporal[entry])
            for i in range(0, len(content['profileFiles']), 1):
                entries.append({'profileFile': content['profileFiles'][i]})
            setattr(self, destinations_temporal[entry], entries)

            # Any further problems with the files are dealt with when they are loaded
def validate_transport(inputDict):
    expectedNames = ['shapefile',
                          'startDate',
                          'epsgCode',
                          'speed_available',
                          'total_AADT_available',
                          'vehicle_AADT_available',
                          'class_field',
                          'motorway_class',
                          'primary_class',
                          'secondary_class',
                          'speed_field',
                          'speed_multiplier',
                          'AADT_total',
                          'AADT_diesel_car',
                          'AADT_petrol_car',
                          'AADT_total_car',
                          'AADT_diesel_LGV',
                          'AADT_petrol_LGV',
                          'AADT_total_LGV',
                          'AADT_motorcycle',
                          'AADT_taxi',
                          'AADT_bus',
                          'AADT_coach',
                          'AADT_rigid',
                          'AADT_artic']

    missing = list(set(expectedNames).difference(inputDict.keys()))
    if(len(missing) > 0):
        raise ValueError('Entries missing from transportData section of data sources file:' + str(missing))
    road_class_entries = ['class_field', 'motorway_class', 'primary_class', 'secondary_class']
    for mandatory in road_class_entries:
        if type(inputDict[mandatory]) is not str:
            raise ValueError('Error in data sources file: "' + mandatory + '" in transportData is mandatory')

    # Determine if things are consistent in terms of available entries
    if inputDict['speed_available'] == 1:
        if type(inputDict['speed_field']) is not str:
            raise ValueError('Error in data sources file: "speed" in transportData must be a field name if speed_available set to 1')
        try:
            a = float(inputDict['speed_multiplier'])
        except Exception:
            raise ValueError('Error in data sources file: "speed_multiplier" in transportData must be a number if speed_available set to 1')

    if inputDict['total_AADT_available'] == 1:
        if type(inputDict['AADT_total']) is not str:
            raise ValueError('"AADT_total" in transportData must be a field name if total_AADT_available set to 1')

    if inputDict['vehicle_AADT_available'] == 1:
        # See if the mandatory AADT fields exist (even if blank)
        mandatory_aadts = ['AADT_motorcycle',
                          'AADT_taxi',
                          'AADT_bus',
                          'AADT_coach',
                          'AADT_rigid',
                          'AADT_artic']
        missing = list(set(mandatory_aadts).difference(inputDict.keys()))
        if len(missing) > 0:
            raise ValueError('The following AADT field names are missing from the transportData section of the data sources file: ' + str(missing))

        # See if the conditionally optional fields exist
        combination_aadts = {'AADT_total_LGV': ['AADT_petrol_LGV', 'AADT_diesel_LGV'],
                             'AADT_total_car': ['AADT_petrol_car', 'AADT_diesel_car']}
        for one in combination_aadts.keys():
            if type(inputDict[one]) is not str: # If the total value is not present, the other values must be
                for other in combination_aadts[one]:
                    if type(inputDict[other]) is not str:
                        raise Exception('Entry ' + other + ' in transportData section of data sources file must be an attribute name if ' + one + ' is not set')


if __name__=="__main__":
    a = DataSources('C:\Users\pn910202\.qgis2\python\plugins\GreaterQF\PythonQF2\GQFInputs\dataSources_working.nml')
    print a.resPop_spat
    print a.outputAreas_spat
    print a.transport_spat
    print a.transport_spat[0]['AADT_fields']
    print a.indGas_spat
    print a.indElec_spat
    print a.domGas_spat
    print a.domElec_spat
    print a.eco7_spat
    print a.resPop_spat
    print a.workPop_spat
    print a.fuelConsumption

