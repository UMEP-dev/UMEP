from builtins import object
import csv
class Partitions(object):
    '''
    Class that stores latent, sensible and (where applicable), wastewater partitioning coefficients for each QF component.
    This reflects the model configuration, with certain components all set to 0 if they are switched off. NB "switched off"
    means they are not included, not that the energy from this component is shifted into the other components.
    '''

    def __init__(self, conf, params):
        '''
        :param conf: GQF Config object
        :param params: GQF Params object
        '''
        # Sensible and wastewater for gas and electricity depend on building type
        # Latent does not depend on building type
        self.latent = {'petrol':None, 'diesel':None, 'gas':None, 'crude_oil':None, 'elec':None, 'metab':None, 'eco7':None}
        self.wasteWater = {'industrial':{'crude_oil':None, 'elec':None, 'gas':None},
                           'domestic':{'crude_oil':None, 'eco7':None, 'elec':None, 'gas':None}}
        self.sensible = {'petrol':None, 'diesel':None, 'metab':None,
                         'industrial':{'crude_oil':None, 'elec':None, 'gas':None},
                         'domestic':{'eco7':None, 'elec':None, 'gas':None, 'crude_oil':None}}

        # Latent heat fractions
        self.latent['petrol'] =    1 - (params.heatOfCombustion['petrol']['net']    / params.heatOfCombustion['petrol']['gross'])
        self.latent['diesel'] =    1 - (params.heatOfCombustion['diesel']['net']    / params.heatOfCombustion['diesel']['gross'])
        self.latent['gas'] =       1 - (params.heatOfCombustion['gas']['net']       / params.heatOfCombustion['gas']['gross'])
        self.latent['crude_oil'] = 1 - (params.heatOfCombustion['crude_oil']['net'] / params.heatOfCombustion['crude_oil']['gross'])
        self.latent['elec'] = 0
        self.latent['eco7'] = 0
        self.latent['metab']  =  params.metabolicLatentHeatFract

        # Sensible heat fractions: The wastewater fractions are removed for buildings
        self.sensible['domestic']['eco7'] = (1 - self.latent['elec']) * \
                                                 (1 - (params.waterHeatFract['domestic']['eco7'] * params.heaterEffic['elec']))

        self.sensible['domestic']['elec'] = (1 - self.latent['elec']) * \
                                                 (1 - (params.waterHeatFract['domestic']['elec'] * params.heaterEffic['elec']))

        self.sensible['domestic']['gas'] =  (1 - self.latent['gas']) * \
                                                 (1 - (params.waterHeatFract['domestic']['gas'] * params.heaterEffic['gas']))

        self.sensible['domestic']['crude_oil'] =  (1 - self.latent['crude_oil']) * \
                                                        (1 - (params.waterHeatFract['domestic']['crude_oil'] * params.heaterEffic['gas']))

        self.sensible['industrial']['elec'] = (1 - self.latent['elec']) * \
                                                 (1 - (params.waterHeatFract['industrial']['elec'] * params.heaterEffic['elec']))

        self.sensible['industrial']['gas'] =  (1 - self.latent['gas']) * \
                                                 (1 - (params.waterHeatFract['industrial']['gas'] * params.heaterEffic['gas']))

        self.sensible['industrial']['crude_oil'] = (1 - self.latent['crude_oil']) * \
                                                        (1 - (params.waterHeatFract['industrial']['crude_oil'] * params.heaterEffic['gas']))

        self.sensible['petrol'] = 1 - self.latent['petrol']
        self.sensible['diesel'] = 1 - self.latent['diesel']
        self.sensible['metab'] = params.metabolicSensibleHeatFract

        # Water heating fractions of total energy use
        self.wasteWater['domestic']['eco7'] =   (1 - self.latent['elec']) * params.waterHeatFract['domestic']['eco7']  * params.heaterEffic['elec']
        self.wasteWater['domestic']['elec'] =   (1 - self.latent['elec']) * params.waterHeatFract['domestic']['elec']  * params.heaterEffic['elec']
        self.wasteWater['domestic']['gas'] =    (1 - self.latent['gas']) * params.waterHeatFract['domestic']['gas']   * params.heaterEffic['gas']
        self.wasteWater['domestic']['crude_oil'] = (1 - self.latent['crude_oil']) *params.waterHeatFract['domestic']['crude_oil']   * params.heaterEffic['gas']
        self.wasteWater['industrial']['elec'] = (1 - self.latent['elec']) * params.waterHeatFract['industrial']['elec']* params.heaterEffic['elec']
        self.wasteWater['industrial']['gas'] =   (1 - self.latent['gas']) *params.waterHeatFract['industrial']['gas'] * params.heaterEffic['gas']
        self.wasteWater['industrial']['crude_oil'] = (1 - self.latent['crude_oil']) * params.waterHeatFract['industrial']['crude_oil']* params.heaterEffic['gas']

        # Set some or all of these components to 0 based on model run configuration
        for k in list(self.wasteWater.keys()):
            for c in list(self.wasteWater[k].keys()):
                self.wasteWater[k][c] = conf.wastewater_qf * self.wasteWater[k][c]

        for k in list(self.sensible.keys()):
            if type(self.sensible[k]) is dict:
                for c in list(self.sensible[k].keys()):
                    self.sensible[k][c] = conf.sensible_qf * self.sensible[k][c]
            else:
                self.sensible[k] = conf.sensible_qf * self.sensible[k]

        for k in list(self.latent.keys()):
                self.latent[k] = conf.latent_qf * self.latent[k]

        # As a slightly redundant shortcut, what is the total flux for each fuel and/or sector after the user choices are acconuted for?
        self.fluxProp = {}
        for k in list(self.sensible.keys()):
            if type(self.sensible[k]) is dict:
                self.fluxProp[k] = {}
                for c in list(self.sensible[k].keys()):
                    self.fluxProp[k][c] = self.wasteWater[k][c] + self.sensible[k][c] + self.latent[c]
            else:
                self.fluxProp[k] = self.sensible[k] + self.latent[k]