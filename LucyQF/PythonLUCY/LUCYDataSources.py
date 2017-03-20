from ...Utilities import f90nml as nml
import os
from datetime import datetime as dt
try:
    import numpy as np
except:
    pass
from string import upper


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

class LUCYDataSources:
    ''' Loads the data sources namelist, conducts validation and structures inputs for use with data management routines
    '''
    def __init__(self, configFile):
        # Lists of the config parameters for spatial datasets
        self.resPop_spat = []
        self.outputAreas_spat = []
        self.database = None
        # And the same for the temporal datasets
        self.diurnTraffic = []
        self.diurnMetab = []
        self.dailyTemp = []
        self.diurnEnergy = []

        try:
            ds = nml.read(configFile)
        except Exception, e:
            raise ValueError('Unable to read data sources config file at: ' + str(configFile))

        # Are all main entries present?
        # For shapefile inputs
        expectedKeys_spatial = ['outputareas',
                                'residentialpop']

        # Get the database
        try:
            self.database = ds['database']['path']
        except Exception,e:
            raise ValueError('Could not set LQF database locations: %s'%str(e))

        if not os.path.exists(self.database):
            raise ValueError('LQF database file (%s) does not exist'%ds['database'])
        missing = list(set(expectedKeys_spatial).difference(ds.keys()))
        if len(missing) > 0:
            raise ValueError('Spatial entries missing from ' + str(configFile) + ' in namelist: ' + str(missing))

        # Loop over the spatial data sources to validate
        for subEntry in expectedKeys_spatial:
            content = ds[subEntry]
            # Check it's all lists or no lists
            types = np.unique(map(type, content.values()))
            # are all required sub-entries present?
            if subEntry == "outputareas": # Special case for output areas
                expectedNames_spat = ['shapefile', 'epsgCode', 'featureIds']
            elif subEntry == "residentialpop":
                expectedNames_spat = ['shapefiles', 'startDates', 'epsgCodes', 'featureIds']
            elif subEntry == "database":
                expectedNames_spat = ['path']

            missing = list(set(map(upper, expectedNames_spat)).difference(map(upper, content.keys())))
            if len(missing) > 0:
                raise ValueError('Entries missing from ' + subEntry + ' in namelist: ' + str(missing))

            for k in content.keys():
                if content[k] == '':
                    content[k] = None
                content[k] = [content[k]]

            map(validateInput, content[expectedNames_spat[0]])

            # Having gotten this far means the entries are valid, so populate the object field
            if subEntry == "outputareas": # Special case for output areas
                entries = {      'shapefile': content['shapefile'][0],
                                 'epsgCode': content['epsgcode'][0],
                                 'featureIds': content['featureids'][0]}
                self.outputAreas_spat = entries
            else:
                try:
                    content['startDates'] = map(makeTimey, content['startDates'])
                except Exception, e:
                    raise ValueError('One or more startDate entries is not in YYYY-mm-dd format for ' + subEntry + ':' + str(e))

                # Ensure dates within a subentry are unique
                if len(np.unique(content['startDates'])) != len(content['startDates']):
                    raise ValueError('One or more startDates is duplicated for ' + subEntry + ':')

                # User can define 1 world database and 1..n residential populations to track time evolution
                # Local residential populations for city in question
                if subEntry == "residentialpop":
                    for i in range(0, len(content['shapefiles']), 1):
                        self.resPop_spat.append({'shapefile': content['shapefiles'][i],
                                        'epsgCode': content['epsgCodes'][i],
                                        'attribToUse': 'Pop', # Residential population MUST be in a field named "Pop"
                                        'startDate': content['startDates'][i],
                                        'featureIds': content['featureIds'][i]})

                # World database (user can't choose names of fields here)
                if subEntry == "database":
                    for i in range(0, len(content['shapefiles']), 1):
                        self.database = content['path'][0]



        # Mandatory: Get temperature data
        if 'dailytemperature' not in ds['temporal'].keys():
            raise ValueError('Temperature data file(s) not specified')

        if type(ds['temporal']['dailyTemperature']) is not list:
            tempList = [ds['temporal']['dailyTemperature']]
        else:
            tempList = ds['temporal']['dailyTemperature']

        for temperatureFile in tempList:
            if os.path.exists(temperatureFile):
                self.dailyTemp.append(temperatureFile)
            else:
                raise ValueError('Temperature data file %s not found'%temperatureFile)

        # Optional: Get diurnal profiles for metabolism, traffic and/or energy use
        cycles = ['diurnEnergy', 'diurnTraffic', 'diurnMetab']
        labels = {'diurnEnergy':'Energy use',
                  'diurnTraffic':'Traffic flow',
                  'diurnMetab':'Metabolism'}
        for c in cycles:
            if c.lower() not in ds['temporal'].keys():
                setattr(self, c, None)
                continue # No cycle(s) specified
            fileList = []
            cycleList = ds['temporal'][c]
            if type(cycleList) is not list:
                cycleList = [cycleList]
            for file in cycleList:
                if os.path.exists(file):
                    fileList.append(file)
                else:
                    raise ValueError('Diurnal %s profile file not found: %s'%(labels[c], file))
            setattr(self, c, fileList)

def test():
    a = LUCYDataSources('N:/QF_Heraklion/LUCYConfig/LUCYdataSources.nml')
    print a.diurnEnergy
    print a.diurnTraffic
    print a.diurnMetab

