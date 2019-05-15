from datetime import timedelta as timedelta
try:
    import pandas as pd
except:
    pass


def QF(areaCodes, timeStepEnd, timeStepDuration, annualEnergyUse, diurnalProfiles, dailyEnergy, pop, trans, diurnalTrans,
       workingProfiles, dailyFactor, prop, hoc):
    '''
    Calculate all energy fluxes for the specified time step and spatial area ID
    :param areaCodes: The feature ID of the spatial area (as appears in energyUse.getEnergyTable())
    :param timeStepEnd: datetime() featuring the end of the time step
    :param timeStepDuration: int() number of seconds covered by the model time step
    :param annualEnergyUse: EnergyUseData object populated with data
    :param diurnalProfiles: EnergyProfile object populated with data
    :param pop: PopulationData object
    :param trans: Transport object
    :param diurnalTrans: TransportProfiles object
    :param area: Areas of the output features
    :param workingProfiles: HumanActivityProfiles object
    :param dailyFactor
    :param prop: Proportions of fluxes to include (dict of {sector or road fuel: {fuel or number}})
    :param hoc: Heat of combustion [J/km] {petrol: float, diesel: float}
    :return: Building energy QF components for this time step
    '''
    dailyFactor = dailyFactor.getFact(timeStepEnd - timedelta(
        seconds=timeStepDuration))  # Get daily factors at start of time bin to ensure correct day
    de = annualEnergyUse.getDomesticElecValue(areaCodes, timeStepEnd)
    ie = annualEnergyUse.getIndustrialElecValue(areaCodes, timeStepEnd)
    dg = annualEnergyUse.getDomesticGasValue(areaCodes, timeStepEnd)
    ig = (annualEnergyUse.getIndustrialGasValue(areaCodes, timeStepEnd))

    ElecRho = de / (ie + 0.00001)
    ElecSum = de + ie
    NewElDom = dailyFactor * ElecRho * ElecSum / (1.0 + dailyFactor * ElecRho)
    NewElInd = ElecSum / (1.0 + dailyFactor * ElecRho)

    GasRho = dg / (ig + 0.00001)
    GasSum = dg + ig

    NewGasDom = dailyFactor * GasRho * GasSum / (1.0 + dailyFactor * GasRho)

    NewGasInd = GasSum / (1.0 + dailyFactor * GasRho)

    columns = ['ElDmUnr',
               'ElDmE7',
               'ElId',
               'GasDm',
               'GasId',
               'OthrId',
               'BldTotDm',
               'BldTotId',
               'BldTot',
               'Mcyc',
               'Taxi',
               'Car',
               'Bus',
               'LGV',
               'Rigd',
               'Art',
               'TransTot',
               'Metab',
               'AllTot']
    # at later point do something with mods to find total hours in time period
    WattHour = pd.DataFrame(columns=columns, index=areaCodes)

    WattHour[columns[0]][areaCodes] = prop['domestic']['elec'] * \
        diurnalProfiles.getDomElec(timeStepEnd, timeStepDuration)[0] * \
        dailyEnergy.getElec(timeStepEnd, timeStepDuration)[0] * \
        NewElDom  # El dom unrestr
    WattHour[columns[1]][areaCodes] = prop['domestic']['eco7'] * \
        diurnalProfiles.getEconomy7(timeStepEnd, timeStepDuration)[0] * \
        dailyEnergy.getElec(timeStepEnd, timeStepDuration)[0] * \
        annualEnergyUse.getEconomy7ElecValue(areaCodes, timeStepEnd)

    WattHour[columns[2]][areaCodes] = prop['industrial']['elec'] * \
        diurnalProfiles.getIndElec(timeStepEnd, timeStepDuration)[0] * \
        dailyEnergy.getElec(timeStepEnd, timeStepDuration)[0] * \
        NewElInd  # El industrial

    WattHour[columns[3]][areaCodes] = prop['domestic']['gas'] * \
        diurnalProfiles.getDomGas(timeStepEnd, timeStepDuration)[0] * \
        dailyEnergy.getGas(timeStepEnd, timeStepDuration)[0] * \
        NewGasDom  # Gas domestic

    WattHour[columns[4]][areaCodes] = prop['industrial']['gas'] * \
        diurnalProfiles.getIndGas(timeStepEnd, timeStepDuration)[0] * \
        dailyEnergy.getGas(timeStepEnd, timeStepDuration)[0] * \
        NewGasInd  # Gas industrial

    WattHour[columns[5]][areaCodes] = prop['industrial']['crude_oil'] * \
        diurnalProfiles.getIndGas(timeStepEnd, timeStepDuration)[0] * \
        dailyEnergy.getGas(timeStepEnd, timeStepDuration)[0] * \
        annualEnergyUse.getIndustrialOtherValue(
            areaCodes, timeStepEnd)  # Assume same behaviour as gas

    WattHour[columns[6]][areaCodes] = WattHour[columns[0]][areaCodes] + \
        WattHour[columns[1]][areaCodes] + \
        WattHour[columns[3]][areaCodes]  # total buildings domestic

    WattHour[columns[7]][areaCodes] = WattHour[columns[2]][areaCodes] + \
        WattHour[columns[4]][areaCodes] + \
        WattHour[columns[5]][areaCodes]  # total buildings industrial

    WattHour[columns[8]][areaCodes] = WattHour[columns[6]][areaCodes] + \
        WattHour[columns[7]][areaCodes]  # total buildings

    # TRANSPORT: Take fuel consumption density [kg/m2] for petrol and diesel, convert to heat
    # Heat of combustion shorthand
    dslHoc = hoc['diesel']['gross']
    petHoc = hoc['petrol']['gross']

    # Scaling factor shorthand(determines whether latent and/or sensible heat should be included)
    # Factor of 86400 to convert from J/m2/day to J/m2/s (W/m2)
    dslSc = prop['diesel']
    petSc = prop['petrol']
    WattHour[columns[9]][areaCodes] = (petHoc * trans.getMotorcycle(areaCodes, 'petrol', timeStepEnd) * petSc +
                                       dslHoc * trans.getMotorcycle(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getMotorcycle(timeStepEnd, timeStepDuration)[
        0]/86400.0  # motorcycles

    WattHour[columns[10]][areaCodes] = (petHoc * trans.getTaxi(areaCodes, 'petrol', timeStepEnd) * petSc +
                                        dslHoc * trans.getTaxi(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getTaxi(timeStepEnd, timeStepDuration)[0]/86400.0  # Taxis

    WattHour[columns[11]][areaCodes] = (petHoc * trans.getCar(areaCodes, 'petrol', timeStepEnd) * petSc +
                                        dslHoc * trans.getCar(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getCar(timeStepEnd, timeStepDuration)[0]/86400.0  # Cars

    WattHour[columns[12]][areaCodes] = (petHoc * trans.getBus(areaCodes, 'petrol', timeStepEnd) * petSc +
                                        dslHoc * trans.getBus(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getBus(timeStepEnd, timeStepDuration)[0]/86400.0  # Bus

    WattHour[columns[13]][areaCodes] = (petHoc * trans.getLGV(areaCodes, 'petrol', timeStepEnd) * petSc +
                                        dslHoc * trans.getLGV(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getLGV(timeStepEnd, timeStepDuration)[0]/86400.0  # LGVs

    WattHour[columns[14]][areaCodes] = (petHoc * trans.getRigid(areaCodes, 'petrol', timeStepEnd) * petSc +
                                        dslHoc * trans.getRigid(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getRigid(timeStepEnd, timeStepDuration)[
        0]/86400.0  # Rigid HGVs

    WattHour[columns[15]][areaCodes] = (petHoc * trans.getArtic(areaCodes, 'petrol', timeStepEnd) * petSc +
                                        dslHoc * trans.getArtic(areaCodes, 'diesel', timeStepEnd) * dslSc) * \
        diurnalTrans.getArtic(timeStepEnd, timeStepDuration)[
        0]/86400.0  # Articulated HGVs

    WattHour[columns[16]] = WattHour[columns[9:16]].sum(
        axis=1)  # Calculate grand total across transport

    # METABOLISM
    # Home:Work balance of people.  1=Workday population, 0= Residential Population
    activeFraction = workingProfiles.getFraction(
        timeStepEnd, timeStepDuration)[0]
    a = prop['metab'] * workingProfiles.getWattPerson(timeStepEnd, timeStepDuration)[0] *\
        ((1-activeFraction)*pop.getResPopValue(areaCodes, timeStepEnd) +
         activeFraction*pop.getWorkPopValue(areaCodes, timeStepEnd))

    WattHour[columns[17]] = a
    WattHour[columns[18]][areaCodes] = WattHour[columns[8]][areaCodes] + \
        WattHour[columns[16]][areaCodes] + WattHour[columns[17]][areaCodes]
    return WattHour.astype('float16')
