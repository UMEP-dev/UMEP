''' Calculates the sensible, latent, wastewater parts of each source and sector.
Calculations consider the gross and net heat combustion for each fuel used. 
'''
import csv
import numpy as np 

def getQFComponents():
    # List and return the components of anthropogenic heat flux
    # Same order as GreaterQF output array
    # TODO: Hard-link these together using pandas arrays or named lists
    components = {}
    components[0] = "Dm El Unre"
    components[1] = "Dm El Eco7"
    components[2] = "Id El"
    components[3] = "Dm gas"
    components[4] = "Id gas"
    components[5] = "Id Other"
    components[6] = "Sum Dm Bld"
    components[7] = "Sum Id Bld"
    components[8] = "Sum Bld"
    components[9] = "Motorcyc"
    components[10] = "Taxis"
    components[11] = "Cars"
    components[12] = "Buses"
    components[13] = "LGVs"
    components[14] = "HGV Rigid"
    components[15] = "HGV artic"
    components[16] = "Sum tspt"
    components[17] = "Metabolism"
    components[18] = "Everything"
    return components

def sum_fluxes(conf, params):
    reader = csv.reader(open(conf.input_data_dir + "Index5_HeatCombustion.csv", "rt"),
                        delimiter=',')
    x = list(reader)[1:]
    Index5 = np.array(x)
    SensLatFrac = np.array(Index5[5:12, 1:3].astype('float'))  # Ratios of vehicles using petrol/diesel

    HeatCom = np.array(Index5[:4, 1:3].astype('float'))  # Gross and net heat of combustion (TableII)
    NGN, NGG = HeatCom[0]  # natural gas net, gross
    PFN, PFG = HeatCom[1]  # petrol net, gross
    DFN, DFG = HeatCom[2]  # diesel net, gross
    CON, COG = HeatCom[3]  # crude oil net, gross
    petrol = PFN / PFG  # Petrol net/gross
    diesel = DFN / DFG  # Diesel ent/gross

    # for Sensible Heat part
    # Parts: [0]Domestic Unrestricted elec [1]Domestic Economy 7 elec/
    # [2]Industrial elec [3]Domestic gas [4]Industrial gas [5]Other fuels/
    # [6]Motorcycles [7]Taxis [8]Cars [9]Buses [10]LGV [11]HGV-Rig [12]HGV-Art
    # [13]Metabolism

    # Petrol and disel latent flux
    petlat = 1 - (PFN / PFG)
    dilat = 1 - (DFN / DFG)

    # Partition latent, wastewater, sensible fluxes
    LatPart = np.zeros(14)  # Latent
    WastWPart = np.zeros(14)  # Wastewater
    SensPart = np.zeros(14)  # Sensible
    WholePart = np.zeros([14, 3])  # Grand total
    for i in range(0, 15):  # For each heat source
        # Latent
        if i in range(0, 3):  # Electricity
            LatPart[i] = 0  # print str(LatPart[i]) + " leccy"
        if i in range(3, 5):  # Gas
            LatPart[i] = (NGG - NGN) / NGG  # print str(LatPart[i]) + " Gas"
        if i == 5:  # Other fuels
            LatPart[i] = (COG - CON) / COG  # print str(LatPart[i]) + " Other"
        if i in range(6, 13):  # Transport
            LatPart[i] = petlat * SensLatFrac[i - 6, 0] + dilat * SensLatFrac[
                i - 6, 1]  # print str(LatPart[i]) + " transport"
        if i == 13:  # metabolism
            LatPart[i] = params.metabolicLatentHeatFract  # print str(LatPart[i]) + " metabolism"

        # Wastewater
        if i in range(0, 2):  # unrest, ec7
            WastWPart[i] = params.waterHeatFract['domestic']['elec'] * params.heaterEffic['elec']  # print str(WastWPart[i]) + " unrest,ec7"
        if i == 2:  # industrial elec
            WastWPart[i] = params.waterHeatFract['industrial']['elec'] * params.heaterEffic['elec']  # print str(WastWPart[i]) + " ind "
        if i == 3:  # dom gas
            WastWPart[i] = params.waterHeatFract['domestic']['gas'] * params.heaterEffic['gas']  # print str(WastWPart[i]) + " gas dom"
        if i == 4:  # ind gas
            WastWPart[i] = params.waterHeatFract['industrial']['gas'] * params.heaterEffic['gas']  # print str(WastWPart[i]) + " gas ind"
        if i == 5:  # other fuels
            WastWPart[i] = params.waterHeatFract['industrial']['other'] * params.heaterEffic['gas']  # print str(WastWPart[i]) + " other fuels"

        # Sensible
        if i in range(0, 6):  # building energy
            SensPart[i] = 1 - LatPart[i] - WastWPart[i]  # print str(SensPart[i]) + " gas and leccy"
        if i in range(6, 13):  # transport
            SensPart[i] = petrol * SensLatFrac[i - 6, 0] + diesel * SensLatFrac[
                i - 6, 1]  # print str(SensPart[i]) + " transport"
        if i == 13:  # metabolism
            SensPart[i] = params.metabolicSensibleHeatFract  # print str(SensPart[i]) + " metabolism"

        # Total
        if i < 14:
            if conf.latent_qf == 1 or conf.all_qf == 1:
                WholePart[i, 0] = LatPart[i]
            if conf.wastewater_qf == 1 or conf.all_qf == 1:
                WholePart[i, 1] = WastWPart[i]
            if conf.sensible_qf == 1 or conf.all_qf == 1:
                WholePart[i, 2] = SensPart[i]

    return {'SensPart':SensPart, 'WholePart':WholePart, 'LatPart':LatPart, 'WastWPart':WastWPart}

