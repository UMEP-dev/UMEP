# Object that loads and stores GreaterQF parameters, given a namelist file
from datetime import datetime as dt
from datetime import timedelta as timedelta
# import f90nml as nml
from ...Utilities import f90nml as nml
from .string_func import lower
import pytz

class Params:
    def __init__(self, paramsFile):
        try:
            PARAMS = nml.read(paramsFile)
        except Exception as e:
            raise ValueError('Could not process params file ' + paramsFile + ': ' + str(e))

        self.inputFile = paramsFile
        self.city = None # City being modelled (a time zone string e.g. Europe/London)
        self.heaterEffic = None
        self.waterHeatFract = None
        self.metabolicLatentHeatFract = None
        self.metabolicSensibleHeatFract = None
        self.heaterEffic = {}
        self.waterHeatFract = {}  # Proportion of a given energy source used to heat water in a given setting
        self.heatOfCombustion = {}
        self.vehicleAge = None       # Vehicle age in years (relative to current modelled time step)

        self.useUKholidays = None # Boolean flag for whether or not to use UK public holidays (calculated)
        self.customHolidays = [] # List of custom public holidays to use with or without UK holidays
        # Traffic parameters
        self.roadAADTs = {} # Default AADTs by road type
        self.roadSpeeds = {} # Default vehicle speeds by road type
        self.vehicleFractions = {} # Fraction of each vehicle type on each type of road (and overall)
        self.fuelFractions = {} # Fraction of each vehicle type that's petrol and diesel

        expectedSections = ['params', 'waterHeatingFractions', 'roadAADTs', 'roadSpeeds', 'vehicleFractions', 'heatOfCombustion', 'petrolDieselFractions']
        missingSections = list(set(map(lower, expectedSections)).difference(list(map(lower, list(PARAMS.keys())))))
        if len(missingSections) > 0:
            raise ValueError('The parameters file ' + paramsFile + ' is missing the following sections: ' + str(missingSections))

        self.latentPartitioning(PARAMS)
        self.roadData(PARAMS, paramsFile)
        self.hoc(PARAMS, paramsFile) # Heat of combustion
        self.bankHolidays(PARAMS, paramsFile)
        try:
            pytz.timezone(PARAMS['params']['city'])
        except KeyError:
            raise ValueError('"city" entry not found in parameters file')
        except Exception:
            raise ValueError('"city" entry in parameters file is invalid. Must be in same format as time zone string (e.g. Europe/London)')
        self.city = PARAMS['params']['city']

    def latentPartitioning(self, PARAMS):
        # Deal with latent and sensible heat partitioning
        # Fraction of metabolic energy going to latent heat for average office worker
        self.metabolicLatentHeatFract = PARAMS['params']['metabolicLatentHeatFract']

        # Dynamically estimate other parameters using assumptions
        self.metabolicSensibleHeatFract = PARAMS['params']['metabolicSensibleHeatFract']

        # Parameters for the partitioning of QF to wastewater flux.
        self.heaterEffic['elec'] = PARAMS['params']['heaterEffic_elec'] # Mean efficiency of electric water heater
        self.heaterEffic['gas'] = PARAMS['params']['heaterEffic_gas']  # Mean efficiency of gas water heater

        self.waterHeatFract['domestic'] = {}
        self.waterHeatFract['domestic']['elec'] = PARAMS['waterHeatingFractions']['domestic_elec'] # Proportion of domestic electricity used to heat water
        self.waterHeatFract['domestic']['eco7'] = PARAMS['waterHeatingFractions']['domestic_eco7'] # Proportion of economy 7 domestic electricity used to heat water
        self.waterHeatFract['domestic']['gas'] = PARAMS['waterHeatingFractions']['domestic_gas']   # Proportion of domestic gas to heat water
        self.waterHeatFract['domestic']['crude_oil'] = PARAMS['waterHeatingFractions']['domestic_crude_oil']   # Proportion of domestic gas to heat water

        self.waterHeatFract['industrial'] = {}
        self.waterHeatFract['industrial']['elec'] = PARAMS['waterHeatingFractions']['industrial_elec'] # Proportion of industrial electricity used to heat water
        self.waterHeatFract['industrial']['gas'] = PARAMS['waterHeatingFractions']['industrial_gas']  # Proportion of industrial gas to heat water
        self.waterHeatFract['industrial']['crude_oil'] = PARAMS['waterHeatingFractions']['industrial_crude_oil']  # Proportion of industrial fuels other than electricity/gas to heat water

    def roadData(self, PARAMS, paramsFile):
        # Road AADTs
        road_types = ['motorway', 'primary_road', 'secondary_road', 'other']
        missing = list(set(road_types).difference(list(PARAMS['roadAADTs'].keys())))
        if len(missing) == 0:
            self.roadAADTs = PARAMS['roadAADTs']
        else:
            raise ValueError('Entry "roadAADTs" in parameters file should contain entries ' + str(road_types) + ' but contains ' + str(list(PARAMS['roadAADTs'].keys())))
        # Road speeds
        missing = list(set(road_types).difference(list(PARAMS['roadSpeeds'].keys())))
        if len(missing) == 0:
            self.roadSpeeds = PARAMS['roadSpeeds']
        else:
            raise ValueError('Entry "roadSpeeds" in parameters file should contain entries ' + str(road_types) + ' but contains ' + str(PARAMS['roadSpeeds']))

        if 'vehicleage' not in list(PARAMS['params'].keys()):
            raise ValueError('Entry "params" in parameters file should contain "vehicleAge" parameter for vehicle age' + str(list(PARAMS['params'].keys())))
        else:
            try:
                self.vehicleAge = timedelta(days = 365 * float(PARAMS['params']['vehicleage']))
            except Exception:
                raise ValueError('Entry "vehicleAge" in parameters file must be a valid number')

        # Vehicle fractions
        required_fractions = ['motorway', 'primary_road', 'secondary_road', 'other']
        missing = list(set(required_fractions).difference(list(PARAMS['vehicleFractions'].keys())))

        if len(missing) == 0:
            veh_frac_headings = ['car', 'lgv', 'motorcycle', 'taxi', 'bus', 'rigid', 'artic']
            # Each of the entries of PARAMS['vehicleFractions'] is a list corresponding to vehicle_fraction_headings

            # Loop around and build the dictionary of values
            for fractionType in list(PARAMS['vehicleFractions'].keys()):
                if len(PARAMS['vehicleFractions'][fractionType]) < len(veh_frac_headings):
                    raise ValueError('"' + fractionType +
                                     '" under "vehicleFractions" in parameters file has only ' +
                                     str(len(PARAMS['vehicleFractions'])) +
                                     ' entries. It should contain ' + str(len(veh_frac_headings)))

                self.vehicleFractions[fractionType] = {veh_frac_headings[i]:PARAMS['vehicleFractions'][fractionType][i] for i in range(0,len(veh_frac_headings))}
        else:
            raise ValueError('Entry "vehicleFractions" in parameters file should contain entries ' + str(required_fractions) + ' but is missing ' + str(missing))

        # Petrol and diesel fuel fractions
        expectedVehicles = ['motorcycle', 'taxi', 'car', 'bus', 'lgv', 'rigid', 'artic']
        missingVehicles = set(expectedVehicles).difference(list(PARAMS['petrolDieselFractions'].keys()))
        if len(missingVehicles) > 0:
            raise ValueError(paramsFile + ' is missing the following vehicles: ' + str(missingVehicles))

        fracNames = {0:'petrol', 1:'diesel'}
        for veh in expectedVehicles:
            self.fuelFractions[veh] = {}

            for frac in [0,1]:
                self.fuelFractions[veh][fracNames[frac]] = PARAMS['petrolDieselFractions'][veh][frac]

    def hoc(self, PARAMS, paramsFile):
        # Heat of combustion. Read in [MJ/kg] and convert to [J/kg]
        expectedFuels = ['gas', 'petrol', 'diesel', 'crude_oil']
        missingFuels = set(expectedFuels).difference(list(PARAMS['heatOfCombustion'].keys()))
        if len(missingFuels) > 0:
            raise ValueError(paramsFile + ' is missing the following entries: ' + str(missingFuels))

        combustionNames = {0:'net', 1:'gross'}
        for fuel in expectedFuels:
            self.heatOfCombustion[fuel] = {}
            for type in [0,1]:
                self.heatOfCombustion[fuel][combustionNames[type]] = PARAMS['heatOfCombustion'][fuel][type]*1000000.0 # Convert to J/kg

    def bankHolidays(self, PARAMS, paramsFile):
        # Public holidays
        self.useUKholidays = PARAMS['params']['use_uk_holidays'] == 1
        if PARAMS['params']['use_custom_holidays'] == 1:
            if type(PARAMS['params']['custom_holidays']) is not list:
                PARAMS['params']['custom_holidays'] = [PARAMS['params']['custom_holidays']]
            for hol in PARAMS['params']['custom_holidays']:
                try:
                    self.customHolidays.append(dt.strptime(hol, '%Y-%m-%d').date())
                except Exception as e:
                    raise ValueError('Invalid custom holiday "' + str(hol) + '" specified. Must be in format YYYY-mm-dd')