from datetime import date as dtd
import datetime as dt
from ...Utilities import f90nml as nml

#Enter date as YYYY,MM,DD
#StartDate = dt.date(raw_input("Enter Date YYYY/MM/DD:"))

# Allowed values for spatial domain
#    GORData: Greater London - 1 domain
#    LAData: Local Auhority - 33 domains
#    MLSOAData: middle level super output areas - 983 domains
#    Gridkm2Data: km2 grid - 1730 domains
#    LLSOAData: lower level super output areas - 4765 domains
#    OAData: output areas - 24140 domains
#    Grid200Data: 200m x 200m grid - 40632 domains
# SpatialDomain='LAData'  #spatial domain file name entered as string

class Config:
    def __init__(self):

        self.dt_start = None
        self.dt_end = None
        self.all_qf = None
        self.spatial_domain = None
        self.sensible_qf = None
        self.latent_qf = None
        self.wastewater_qf = None
        self.input_data_dir = None

        self.expected_names =  ['start_date', 'end_date', 'spatial_domain', 'all_qf', 'sensible_qf', 'latent_qf', 'wastewater_qf', 'input_data_dir']
        self.spatialDomains = ['GORData', 'LAData', 'MLSOAData', 'Gridkm2Data', 'LLSOAData', 'OAData', 'Grid200Data']
        self.dataStartDate = dt.date(2005, 1, 1)  # data starts on 01/01/2005. This is used to aid lookups from files TODO: Make dynamic

    def checkInput(self, inputDict):
        if len(set(inputDict.keys()).intersection(self.expected_names)) != len(self.expected_names):
            raise ValueError('Required present in config file. This should have ' + str(self.expected_names))

        if inputDict['spatial_domain'] not in self.spatialDomains:
            raise ValueError('Illegal Spatial Domain specified. Allowed values are ' + str(self.spatialDomains))

        # Check values set as input are valid. Prevent the object being returned if invalid
        try:
            self.dt_start = dt.datetime.strptime(inputDict['start_date'], '%Y-%m-%d').date()
            self.dt_end = dt.datetime.strptime(inputDict['end_date'], '%Y-%m-%d').date()
        except Exception, e:
            raise ValueError('Could not interpret dates for model configuration: ' + str(e))

        if self.dt_end < self.dt_start:
            raise ValueError('Start date %s after end date %s')

    # Option 1 to populate config object: Load from a dictionary (so long as it has all the names needed) - used in QGIS
    def loadFromDictionary(self, configDict):
        self.checkInput(configDict)
        self.spatial_domain = configDict['spatial_domain']
        self.all_qf = 1 if configDict['all_qf'] else 0
        self.sensible_qf = 1 if configDict['sensible_qf'] else 0
        self.latent_qf = 1 if  configDict['latent_qf'] else 0
        self.wastewater_qf = 1 if configDict['wastewater_qf'] else 0
        self.input_data_dir = configDict['input_data_dir']

    # Option 2: Load from namelist (used as standalone)
    def loadFromNamelist(self, configFile):
        # Load the properties from a namelist
        try:
            CONFIG = nml.read(configFile)
        except Exception,e:
            raise ValueError('Could not process config file ' + configFile + ': ' + str(e))

        self.checkInput(CONFIG['input_nml'])
        self.spatial_domain = CONFIG['input_nml']['spatial_domain']
        self.all_qf = CONFIG['input_nml']['all_qf']
        self.sensible_qf = CONFIG['input_nml']['sensible_qf']
        self.latent_qf = CONFIG['input_nml']['latent_qf']
        self.wastewater_qf = CONFIG['input_nml']['wastewater_qf']
        self.input_data_dir = CONFIG['input_nml']['input_data_dir']

