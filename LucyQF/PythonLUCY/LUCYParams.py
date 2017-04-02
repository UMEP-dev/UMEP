import os
from ...Utilities import f90nml
from datetime import datetime as dt
from string import lower

class LUCYParams:
    def __init__(self, file):
        '''
        Read LUCY parameters file and return object or exception
        :param file: Location of LUCY config file
        '''
        if not os.path.exists(file):
            raise IOError('Parameters file ' + str(file) + ' not found')
        self.inputFile = file
        nml = f90nml.read(file)

        try:
            # Maths params
            self.avg_speed =         float(nml['params']['avgspeed'])
            if self.avg_speed > 64000:
                raise ValueError('Average vehicle speed must not exceed 64 kph')

            self.emission_factors =  map(float, nml['params']['emissionfactors'])
            self.BP_temp =           float(nml['params']['balance_point_temperature'])
            self.QV_multfactor =     float(nml['params']['QV_multfactor'])
            self.sleep_metab =     float(nml['params']['sleep_metab'])
            self.work_metab =     float(nml['params']['work_metab'])
            self.landCoverWeights =  {}
            try:
                a=nml['landCoverWeights']
            except Exception:
                raise ValueError('Entry \'landCoverWeights\' not in configuration file ' + file)

            self.lcw(nml, file) # Dict of land cover weightings for extra disaggregation {class: {building: float, transport: float, metabolism: float}}

            # Model date options
            try:
                self.timezone = nml['params']['timezone']
            except KeyError:
                raise KeyError('Entry "timezone" not found in parameters file')
            except Exception:
                raise ValueError('Invalid "timezone" entry. Must be a recognised time zone string in the format Continent/City (e.g. "Europe/London")')

            self.use_uk_hols = True if nml['params']['use_uk_holidays'] == 1 else False
            self.use_custom_hols = True if nml['params']['use_custom_holidays'] == 1 else False
            self.custom_holidays = []
            if self.use_custom_hols: # Only try and deal with custom holidays entry if it's set to 1
                def toDate(x): return dt.strptime(x, '%Y-%m-%d').date()
                try:
                    self.custom_holidays = map(toDate, nml['params']['custom_holidays'])
                except Exception:
                    raise ValueError('Custom holidays in parameters file must be in formatted YYYY-mm-dd')

        except KeyError,e:
            raise Exception('Entry missing from parameters file: ' + str(e))
        except Exception,e:
            raise Exception('Problem reading parameters file: ' + str(e))


    def lcw(self, PARAMS, paramsFile):
        # Validate land cover weightings (used for additional disaggregation)
        expectedClasses = ["paved", "buildings", "evergreentrees", "decidioustrees", "grass", "baresoil", "water"]
        types = ['building', 'transport', 'metabolism']
        missing = set(map(lower,expectedClasses)).difference(map(lower, PARAMS['landCoverWeights'].keys()))
        if len(missing) > 0:
            raise ValueError(paramsFile + ' is missing the following entries under "landCoverWeights": ' + str(missing))

        for cl in expectedClasses:
            if len(PARAMS['landCoverWeights'][cl]) != 3:
                raise ValueError('Land cover weights in parameters file should each have 3 entries, but ' + str(cl) + ' does not')

            self.landCoverWeights[cl] = {}
            for ty in range(0,len(types)):
                try:
                    self.landCoverWeights[cl][types[ty]] = float(PARAMS['landCoverWeights'][cl][ty])
                except Exception:
                    raise ValueError('Land cover weights in parameters file had invalid number in entry: ' + str(cl))

def testit():
    a = LUCYParams('N:/QF_Heraklion/LUCYConfig/LUCYConfig.nml')
