from builtins import str
from builtins import map
from builtins import object
from datetime import date as dtd
import datetime as dt
from ...Utilities import f90nml as nml

#Enter date as YYYY,MM,DD
#StartDate = dt.date(raw_input("Enter Date YYYY/MM/DD:"))
def to_date(x):
    return dt.datetime.strptime(x, '%Y-%m-%d').date()

class Config(object):
    def __init__(self):

        self.dt_start = None
        self.dt_end = None
        self.all_qf = None

        self.sensible_qf = None
        self.latent_qf = None
        self.wastewater_qf = None

        self.expected_names =  ['start_dates', 'end_dates', 'all_qf', 'sensible_qf', 'latent_qf', 'wastewater_qf']

    def checkInput(self, inputDict):
        matchedNames = set(inputDict.keys()).intersection(self.expected_names)
        missingNames = set(self.expected_names).difference(matchedNames)
        if len(missingNames) > 0:
            raise ValueError('Required entries missing from config file. This should have ' + str(missingNames))



    # Option 1 to populate config object: Load from a dictionary (so long as it has all the names needed) - used in QGIS
    def loadFromDictionary(self, configDict):
        self.checkInput(configDict)
        self.all_qf = 1 if configDict['all_qf'] else 0
        self.sensible_qf = 1 if configDict['sensible_qf'] else 0
        self.latent_qf = 1 if  configDict['latent_qf'] else 0
        self.wastewater_qf = 1 if configDict['wastewater_qf'] else 0
        self.dt_start = configDict['start_dates'] # Assume already datetime objects
        self.dt_end = configDict['end_dates']

    # Option 2: Load from namelist (used as standalone)
    def loadFromNamelist(self, configFile):
        # Load the properties from a namelist
        try:
            CONFIG = nml.read(configFile)
        except Exception as e:
            raise ValueError('Could not process config file ' + configFile + ': ' + str(e))

        # Try dates out
        try:
            self.dt_start = list(map(function=to_date, sequence=CONFIG['input_nml']['start_dates']))
            self.dt_end = list(map(function=to_date, sequence=CONFIG['input_nml']['end_dates']))
        except Exception as e:
            raise ValueError('Could not interpret dates for model configuration: ' + str(e))

        self.checkInput(CONFIG['input_nml'])
        self.all_qf = CONFIG['input_nml']['all_qf']
        self.sensible_qf = CONFIG['input_nml']['sensible_qf']
        self.latent_qf = CONFIG['input_nml']['latent_qf']
        self.wastewater_qf = CONFIG['input_nml']['wastewater_qf']


    def saveNamelist(self, filename):
        '''
        Write a namelist file to the requested path based on the current content of this object
        :param filename: the path of the file to write
        :return: None
        '''
        a = {'input_nml':{}}
        a['input_nml']['all_qf'] = self.all_qf
        a['input_nml']['sensible_qf'] = self.sensible_qf
        a['input_nml']['latent_qf'] = self.latent_qf
        a['input_nml']['wastewater_qf'] = self.wastewater_qf
        a['input_nml']['start_date'] = self.dt_start.strftime('YYYY-mm-dd')
        a['input_nml']['end_date'] = self.dt_start.strftime('YYYY-mm-dd')
        nml.write(a, filename)

# def testIt():
#     a = Config()
#     b = {}
#     b['all_qf'] = 1
#     b['sensible_qf'] =1
#     b['latent_qf'] = 0
#     b['wastewater_qf'] = 1
#     b['start_date'] = '2016-01-01'
#     b['end_date'] = '2017-01-01'
#     a.loadFromDictionary(b)
#     a.saveNamelist('c:\\testoutput\\namelist.nml')