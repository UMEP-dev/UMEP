from __future__ import print_function
from __future__ import absolute_import
# LUCY core calculations
try:
    import pandas as pd
except:
    pass
# calculation parameters: The relationship between heating and cooling and socio-economic class (1-4). -1 is a placeholder for "no information" and returns zero
def increasePerHDD():
    return pd.Series({-1:0.0, 1:0.0021, 2:0.0010,  3:0.00075, 4:0.000125})

def increasePerCDD():
    return pd.Series({-1:0.0, 1:0.0010, 2:0.00060, 3:0.00035, 4:6.25E-05})

def offset():
    return pd.Series({-1:0.0, 1:0.7,    2:0.8,     3:0.9,     4:0.95})

def getTMF(temperature, BP, attribs):
    '''
    returns multiplication factor to account for increased energy use by buildings
    due to heating/air conditioning
    :param temperature: Daily mean tempereature (celsius)
    :param BP: Balance point temperature (celsius)
    :param attribs: pd.Dataframe containing ('summer_cooling', 'increasePerCDD', 'increasePerHDD', 'offset')
                    These are (i) Summer cooling flag: 1 or 0, (ii) Cooling Degree Day factor, (iii) Heating degree day factor
                    and (iv) offset applied to cooling/heating degree day factors

    :return: Float: Multiplication factor
    '''
    # Convert values to integers but preserve nans if present
    try:
        attribs.loc[attribs['ecostatus'].notnull(), 'ecostatus'] = attribs.loc[attribs['ecostatus'].notnull(), 'ecostatus'].astype('int')
    except Exception:
        raise ValueError('Database error: Economic class must be numeric')

    if len(set(attribs['ecostatus'].dropna()).difference([-1,1,2,3,4])) > 0:
        raise ValueError('Database error: Economic class must be 1-4 exactly, or -1 as a placeholder for an empty country')

    try:
         attribs.loc[attribs['summer_cooling'].notnull(), 'summer_cooling'] = attribs.loc[attribs['summer_cooling'].notnull(), 'summer_cooling'].astype('int')

    except Exception:
        raise ValueError('Database error: Summer_cooling value must be numeric')


    if len(set(attribs['summer_cooling'].dropna()).difference([1,0])) > 0:
        raise ValueError('Database error: Summer_cooling value must be 0 or 1')

    # For LUCY 2013a (Lindberg et al. 2013) Heating and Cooling degree days are just |temperature-BP| * 30
    daysPerMonth = 30

    HDD = max(0, BP-temperature) * daysPerMonth # Heating degree days
    CDD = max(0, temperature-BP) * daysPerMonth # Cooling degree days

    # Default values
    areaCDDIncrease = 0
    areaHDDIncrease = 0

    if HDD > 0:
        if HDD > 600:
            # Special case for extreme climates
            areaHDDIncrease = ((3E-10 * HDD ** 2) - (1E-6 * HDD) + 2.9E-3) # Eq (2) Lindberg et al. 2013
        else:
            # More normal climate - allow values to vary per area
            areaHDDIncrease = attribs['increasePerHDD']
    if CDD > 0:
        areaCDDIncrease =  attribs['increasePerCDD']

    # Return pandas series of coefficients: one for each area
    return attribs['offset'] + (attribs['summer_cooling'] * areaCDDIncrease * CDD) + (areaHDDIncrease * HDD)

def customTResponse(temperature, config):
    '''
    Calculates daily energy scaling factor based on a user-defined set of parameters
    :param temperature:
    :param config:
    :return:

    '''
    # Is temperature < min or > max? Function is constant with T in these regimes
    temperature = max(temperature, config.TResponse['Tmin'])
    temperature = min(temperature, config.TResponse['Tmax'])
    # Is this a heating or cooling regime?
    coef = None
    if temperature > config.TResponse['Tc']: # In a cooling regime
        coef = abs(config.TResponse['Ac'])
        diff = abs(config.TResponse['Tc'] - temperature)
    if temperature < config.TResponse['Th']:
        coef = abs(config.TResponse['Ah'])
        diff = abs(temperature - config.TResponse['Th'])

    # If temperature falls in between Tc and Th, the value should be the function minimum
    if coef is None:
        return config.TResponse['c'] #
    else:
        # Calculate value of function based on temperature
        return config.TResponse['c'] + coef * diff

def qm(population_density, profile):
    '''
    Calculate metabolic heat flux
    :param population_density:  (pd.Series) Residential population density (people per square metre) in each local area
    :param profile: (float) Mean metabolic activity per person in area (Wm-2)
    :return: Qm (pd.Series): Metabolic heat flux for each local area in Wm-2
    '''
    Qm = population_density*profile # W/m^2 
    return Qm

def qb(params, energy_use, temperature, profile, BP_temperature, attribs):
    '''
    Calculate building heat flux
    :param config: LQFParames object (controls whether or not to use custom temperature response)
    :param energy_use: (pd.Series) Total energy consumption in local areas (kwh per year)
    :param temperature: (float) Mean air temperature
    :param profile: (pd.Series indexed by area id) Diurnal scaling of air temperature for the current time of day (identified outside of this function). Should be ~1/24
    :param BP_temperature: (float) Balance point temperature  for temperature-based energy use scaling
    :param attribs (pd.DataFrame indexed to output area ID): Data frame, with columns "ecostatus" (socio economic classification)
            and "summer_cooling" (heat generated by summer cooling). Both should be numeric (1-4 and 0-1 respectively)
    :return: Qb: (pd.Series) Building heat flux in Wm-2 for each area
    '''

    if params.TResponse is None:
        factor = getTMF(temperature, BP_temperature, attribs) # User didn't set a T response function so use built-in version
    else:
        factor = customTResponse(temperature, params)

    Qb = factor * (energy_use * 1000.0 / 365.25) * profile # kwh per year converted to W per day
    return Qb

def qt(avg_speed, vehicle_count, areas, emission_factors, profile):
    '''
    Calcluate transport heat flux
    :param avg_speed: Mean vehicle speed [m/hour]
    :param vehicle_count: (dict) Total vehicle count in local area for cars, motorcycles and freight
    :param areas: (pd.Series): The area of each local area in square metres
    :param emission_factors: (list) Emissions factors for the three vehicle types
    :param profile: (float) Diurnal multiplication factor for this time of day (identified outside of the function)
    :return: Qt (pd.Series): Transport heat flux for each local area
    '''

    local_watts = (24.0/ 3600.0) * avg_speed*(vehicle_count['cars']*emission_factors[0] +
                                vehicle_count['motorcycles']*emission_factors[1] +
                                vehicle_count['freight']*emission_factors[2])/areas # W/hour/m2

    Qt = local_watts*profile  # Profile = proportion of daily total traffic on the road in this hour (~1/24)
    return Qt

def testIt():
    # Run integrated test
    from .DailyTemperature import DailyTemperature
    attribs = pd.Series({'summer_cooling':1,
                           'increasePerCDD':0.0010,
                           'increasePerHDD':0.00060,
                           'offset':0.8,
                           'ecostatus':2}).to_frame()
    # fix_print_with_import
    print(attribs)
    dr = pd.date_range(dt.strptime('2013-01-01 12:00', '%Y-%m-%d %H:%M'), dt.strptime('2013-01-30 12:00', '%Y-%m-%d %H:%M'), tz="UTC")

    te = DailyTemperature("Asia/Shanghai", use_uk_holidays=False, weekendDays= [], other_holidays=[])
    te.addTemperatureData('N:\QF_China\Beijing\dailyTemperature_2013_Beijing.csv')
    #a.addTemperatureData('N:\QF_Heraklion\LUCYConfig\dailyTemperature_2016_Heraklion.csv')
    for dt in dr:
        a = getTMF(te.getTemp(dt.to_datetime(), 3600)[0], 12, attribs)
        # fix_print_with_import
        print(a)

