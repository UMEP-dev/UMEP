import numpy as np
from ParameterCombo import load_data

def convert_params_to_float(params):
    if type(params) == tuple:
        params = list(params)
        for i, v in enumerate(params):
            params[i] = float(v)
        params = tuple(params)
    elif type(params) == list:
        for i, v in enumerate(params):
            params[i] = float(v)
    return params

class TemperatureModel:
    """
        A class for PV temperature model parameters.

        Defines parameters at initialisation,
        defines a function to check if the model-name given by a configuration file is valid,
        ...
    """
    def __init__(self, datapath):
        """
            TempModel:
            source for values:
              [1] King, D. et al, 2004, "Sandia Photovoltaic Array Performance Model", SAND Report
            3535, Sandia National Laboratories, Albuquerque, NM
              [2] SAPM code, version 2, pvlib.pvl_sapmcelltemp.pvl_sapmcelltemp()
        """

        self.modelskeys, values = load_data(datapath)
        self.modelsdict = {}
        self.modelparams = None       # selected model parameters
        self.modelname = None         # selected model name

        for i in range(len(self.modelskeys)):
            self.modelsdict[self.modelskeys[i]] = values[i]

    def set_model(self, modelname):
        """ Set model in use. """
        self.modelname = modelname
        self.modelparams = convert_params_to_float(self.modelsdict[modelname])

    def set_modelparams(self, para1, para2, para3):
        """ Set model in use. """
        self.modelname = None
        self.modelparams = convert_params_to_float([para1, para2, para3])

    def get_model(self):
        return self.modelname, self.modelparams

    def get_modelskeys(self):
        """ Return a list with keys from modelsdict. """
        return self.modelskeys

    def celltemp(self, irrad, tamb, wind):
        """
        Estimate cell temperature from irradiance, windspeed, ambient temperature, and module parameters (SAPM)

        Estimate cell and module temperatures per the Sandia PV Array
        Performance model (SAPM, SAND2004-3535), when given the incident
        irradiance, wind speed, ambient temperature, and SAPM module
        parameters.

        Returns
        --------
        Tcell : float or DataFrame
                Cell temperatures in degrees C.
        Tmodule : float or DataFrame
                Module back temperature in degrees C.

        References
        ----------
        [1] King, D. et al, 2004, "Sandia Photovoltaic Array Performance Model", SAND Report
        3535, Sandia National Laboratories, Albuquerque, NM
        """
        a = self.modelparams[0]
        b = self.modelparams[1]
        delta = self.modelparams[2]
        irrad0 = 1000.  # Reference irradiance

        tmodule = irrad * (np.exp(a + b * wind)) + tamb
        tcell = tmodule + irrad / irrad0 * delta

        return tcell


class PhotovoltaicModel:
    """
        A class for Photovoltaic model.

        Defines parameters at initialisation,
        defines a function to check if the model-name given by a configuration file is valid,
        ...
    """

    def __init__(self, datapath):
        """

        """

        self.modelskeys, values = load_data(datapath)
        self.modelsdict = {}
        self.modelparams = None       # selected model parameters
        self.modelname = None         # selected model name
        self.power = 1.     # Nominal Power in Watt (W) at STC (1000W/m2 25degC)

        for i in range(len(self.modelskeys)):
            self.modelsdict[self.modelskeys[i]] = tuple(values[i])

    def set_model(self, modelname):
        """ Set model in use. """
        self.modelname = modelname
        self.modelparams = convert_params_to_float(self.modelsdict[modelname])

    def set_modelparams(self, power, k1, k2, k3, k4, k5, k6):
        """ Set model in use. """
        self.modelname = None
        self.modelparams = convert_params_to_float(tuple(k1, k2, k3, k4, k5, k6))
        self.power = float(power)

    def get_model(self):
        return self.modelname, self.modelparams

    def get_modelskeys(self):
        """ Return a list with keys from modelsdict. """
        return self.modelskeys

    def set_peakpower(self, power):
        self.power = float(power)

    def get_peakpower(self):
        return self.power

    def calcpower(self, irrad, temp):
        """simple model (by Thomas Huld)
           for determining annual loss rate and correcting data for that loss.

           irrad: irradiation [W m^-2]
           temp:  cell temperature [deg C]
           power: nominal peak power at STC (1000W/m2 25degC) in [W]
        """
        k1, k2, k3, k4, k5, k6 = self.modelparams
        temp0 = 25.
        irrad0 = 1000.

        irr = irrad / irrad0
        irr = np.where(irr > 0.001, irr, 0)
        try:
            logirr = np.where(irr > 0.001, np.log(irr), 0)
        except RuntimeWarning:
            print 'logirr: ', logirr, 'irr: ', irr
        t = temp - temp0

        return (irr * self.power * (1 +
                                   k1 * logirr +
                                   k2 * (logirr ** 2) +
                                   k3 * t +
                                   k4 * t * logirr +
                                   k5 * t * (logirr ** 2) +
                                   k6 * (t ** 2)
                               )
                )

    def energy_yield(self, timedelta, poweroutput):
        """
        Arguments
        deltaTime <float>: time steps used for calculating energy from power, expressed in units of 1 hour.
        PeakPower: units of Wp
        PowerOutput: units of W

        Return: EnergyYield <float> units of kWh/kWp
        """
        energyoutput = self.energy_output(timedelta, poweroutput)
        return float(energyoutput * 1000 / self.power)

    def energy_output(self, timedelta, poweroutputext):
        """
        Arguments
        deltaTime <float>: time steps used for calculating energy from power, expressed in units of 1 hour.
        PowerOutput: units of W

        Return: Energy <float> units of kWh
        """
        poweroutput = poweroutputext.copy() * timedelta
        energyoutput = poweroutput.sum()
        return float(energyoutput * .001)

if __name__ == '__main__':
    # data = "../ModelParameters/temperature_model.txt"
    # k,p = pc.load_data(data)
    # print k
    # print p

    datapath = "../ModelParameters/temperature_model.txt"
    tm = TemperatureModel(datapath)
    tm.set_model('Open rack cell glassback')
    # cellt = tm.celltemp(np.array(700.,750.,600.), 29., 3.)
    cellt = tm.celltemp(750., 29., 3.)
    datapath = "../ModelParameters/photovoltaic_model.txt"
    pvm = PhotovoltaicModel(datapath)
    pvm.set_model('mc-Si Huld')
    # p = pvm.calcpower(np.array(700.,750.,600.), cellt)
    p = pvm.calcpower(750., cellt)
    print p, cellt