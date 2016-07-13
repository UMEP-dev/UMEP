# Object that loads and stores parameters, given a namelist file

from ...Utilities import f90nml as nml
class Params:
    def __init__(self, paramsFile):
        try:
            PARAMS = nml.read(paramsFile)
        except Exception,e:
            raise ValueError('Could not process params file ' + paramsFile + ': ' + str(e))

        self.heaterEffic = None
        self.waterHeatFract = None
        self.metabolicLatentHeatFract = None
        self.metabolicSensibleHeatFract = None
        self.heaterEffic = {}
        self.waterHeatFract = {}  # Proportion of a given energy source used to heat water in a given setting

        # Fraction of metabolic energy going to latent heat for average office worker
        self.metabolicLatentHeatFract = PARAMS['params']['metabolicLatentHeatFract']

        # Dynamically estimate other parameters using assumptions
        self.metabolicSensibleHeatFract = PARAMS['params']['metabolicSensibleHeatFract']

        # Parameters for the partitioning of QF to wastewater flux.
        self.heaterEffic['elec'] = PARAMS['params']['heaterEffic_elec'] # Mean efficiency of electric water heater
        self.heaterEffic['gas'] = PARAMS['params']['heaterEffic_gas']  # Mean efficiency of gas water heater

        self.waterHeatFract['domestic'] = {}
        self.waterHeatFract['domestic']['elec'] = PARAMS['waterHeatingFractions']['domestic_elec'] # Proportion of domestic electricity used to heat water
        self.waterHeatFract['domestic']['gas'] = PARAMS['waterHeatingFractions']['domestic_gas']   # Proportion of domestic gas to heat water

        self.waterHeatFract['industrial'] = {}
        self.waterHeatFract['industrial']['elec'] = PARAMS['waterHeatingFractions']['industrial_elec'] # Proportion of industrial electricity used to heat water
        self.waterHeatFract['industrial']['gas'] = PARAMS['waterHeatingFractions']['industrial_gas']  # Proportion of industrial gas to heat water
        self.waterHeatFract['industrial']['other'] = PARAMS['waterHeatingFractions']['industrial_other']  # Proportion of industrial fuels other than electricity/gas to heat water