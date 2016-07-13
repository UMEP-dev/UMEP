import numpy as np
import datetime as dt
from datetime import date as dtd

import copy
from collections import OrderedDict
from TimeProfiles import WhatSeason, WhatYear, DayOfWeek, DateDiff, WeekSatSun, DailyFact, generateHolidays
import read_data_files as rdf
reload(rdf)
from AllParts import sum_fluxes

def get_area_data(qfConfig):
    # Load energy data from area-resolved file based on output area selected
    # INputs: qfConfig. Config object with params and config options
    if qfConfig.spatial_domain == 'SubOA200Data':  # Special case
        y = rdf.SubOAAreaDataReader(qfConfig.spatial_domai, qfConfig.input_data_dirn)
    else:
        y = rdf.AreaDataReader(qfConfig.spatial_domain, qfConfig.input_data_dir)
    y.AData()
    y.RData()
    y.DData()
    y.EData()
    y.Code()
    return y

def mostcalcs(qfConfig, qfParams):
    # Produce list of holidays for use by DayOfWeek()
    holidayDays = []
    holidays = generateHolidays(qfConfig.dt_start.year, qfConfig.dt_end.year)
    holidayDays = [dtd.toordinal(h) for h in holidays] # Gets used when determining effective day of week

    # Get area-resolved energy use data, given Config() object and Params() objects
    y = get_area_data(qfConfig)
    Area=y.Area
    Residents=y.Residents
    Daytime=y.Daytime
    Energy=y.Energy
    Code=y.IDCode

    # take length of hours in day, create array thats hours x 18 WattHour
    days = 7  # Days per week
    months = 4  # Weeks per month
    WattHour = np.zeros((18, 24 * 2))  # 2* hours per day
    WattDay = np.zeros((18, days))
    WattMonth = np.zeros((18, months))

    # Get total latent and/or sensible and/or wastewater heat fluxes for domestic & industrial
    lsw = sum_fluxes(qfConfig, qfParams)
    LSWfluxTotal = lsw['WholePart'] # Total

    NewElDom=np.zeros(len(Area))
    NewElInd=np.zeros(len(Area))
    NewGasDom=np.zeros(len(Area))
    NewGasInd=np.zeros(len(Area))

    OrdDate = dt.date.toordinal(qfConfig.dataStartDate)
    refday = dt.date.toordinal(qfConfig.dt_start)-OrdDate #refday is number of days from 1/1/2005, used to find correct row in EnergyDaily

    # Work out which season we're in (to start with)
    current=copy.copy(qfConfig.dt_start)
    season= WhatSeason(current)
    energyData = rdf.load(qfConfig.input_data_dir)
    EH= energyData['EnergyHourly'][:,season:season+3]  #selects the correct season from Energy Hourly
    EDF=energyData['EnergyDaily'][:,:]

    Traffic=energyData['HHourTrafficIndex'][:,:]
    DaytInd=energyData['DaytInd']
    WattPerson=energyData['WattPerson']

    d= DateDiff(qfConfig.dt_start, qfConfig.dt_end)

    hours = 24
    WattHour = np.empty((len(Area), 19, hours*2))  #at later point do something with mods to find total hours in time period
    #WattHour[domains, energy parts, half-hour timesteps]
    WattDay = np.empty((len(Area),19,d))
    WattHourDays=OrderedDict()
    WattArea=np.empty((len(Area), 19, d*hours*2))

    # Cycle around time and spatial bins, weighting fluxes by seasonal and spatial energy use
    for dd in range(0, d):
        j= DayOfWeek(current, holidayDays)
        k= WeekSatSun(current, holidayDays)
        DailyFactors = DailyFact(current, holidayDays)
        year= WhatYear(current)
        season= WhatSeason(current)

        # Change of season since yesterday
        if WhatSeason(current-dt.timedelta(days=1))!= WhatSeason(current):
            EH=rdf.EnergyHourly[:,season:season+3] # CHANGED to rdf FROM EHD - BUT A GUESS BY ANDY
        WattHour = np.zeros((len(Area), 19, hours*2)) 

        for A in range(len(Area)):
            Rho=Energy[A, 0+year]/(Energy[A,8+year]+0.00001)  #Domestic Unrestricted elec/Industrial elec
            Sum=Energy[A,0+year]+Energy[A, 8+year] #Domestic Unrestricted elec + Industrial elec
            NewElDom[A]=DailyFactors*Rho*Sum/(1+DailyFactors*Rho)
            NewElInd[A]=Sum/(1+DailyFactors*Rho)

            Rho=Energy[A,12+year]/(Energy[A,16+year]+0.000001) #Domestic gas/Industrial gas
            Sum=Energy[A,12+year]+Energy[A,16+year] #Domestic gas+Industrial gas
            NewGasDom[A]=DailyFactors*Rho*Sum/(1+DailyFactors*Rho)
            NewGasInd[A]=Sum/(1+DailyFactors*Rho)

            for hh in range(0,48):  #hh= half-hour timesteps
                kk=(k*48+hh)-1  #for weekday, Saturday Sunday of half-hour timesteps
                jj=(j*48+hh) #for a week of half hour timesteps

                WattHour[A,0,hh]=sum(LSWfluxTotal[0,:])*EH[kk,0]*EDF[refday,0]*NewElDom[A]    #El dom unrestr
                WattHour[A,1,hh]=sum(LSWfluxTotal[1,:])*EH[kk,1]*EDF[refday,0]*Energy[A,4+year]     #El domestic economy 7
                WattHour[A,2,hh]=sum(LSWfluxTotal[2,:])*EH[kk,2]*EDF[refday,0]*NewElInd[A]   #El industrial
                WattHour[A,3,hh]=sum(LSWfluxTotal[3,:])*EH[kk,0]*EDF[refday,1]*NewGasDom[A]     #Gas domestic
                WattHour[A,4,hh]=sum(LSWfluxTotal[4,:])*EH[kk,2]*EDF[refday,1]*NewGasInd[A]   #Gas industrial
                WattHour[A,5,hh]=sum(LSWfluxTotal[5,:])*EH[kk,2]*EDF[refday,1]*Energy[A,20+year]     #Other industrial
                WattHour[A,6,hh]=WattHour[A,0,hh]+WattHour[A,1,hh]+WattHour[A,3,hh]   #total buildings domestic
                WattHour[A,7,hh]=WattHour[A,2,hh]+WattHour[A,4,hh]+WattHour[A,5,hh]   #total buildings industrial
                WattHour[A,8,hh]=WattHour[A,6,hh]+WattHour[A,7,hh]                  #total buildings

                WattHour[A,9,hh]=sum(LSWfluxTotal[6,:])*Energy[A,24+year]*Traffic[jj,0]   #motorcycles
                WattHour[A,10,hh]=sum(LSWfluxTotal[7,:])*Energy[A,28+year]*Traffic[jj,1]   #taxi
                WattHour[A,11,hh]=sum(LSWfluxTotal[8,:])*Energy[A,32+year]*Traffic[jj,2]   #cars
                WattHour[A,12,hh]=sum(LSWfluxTotal[9,:])*Energy[A,36+year]*Traffic[jj,3]   #bus
                WattHour[A,13,hh]=sum(LSWfluxTotal[10,:])*Energy[A,40+year]*Traffic[jj,4]   #lgv
                WattHour[A,14,hh]=sum(LSWfluxTotal[11,:])*Energy[A,44+year]*Traffic[jj,5]   #rigid
                WattHour[A,15,hh]=sum(LSWfluxTotal[12,:])*Energy[A,48+year]*Traffic[jj,6]   #artic
                WattHour[A,16,hh]=0
                for i in range(9,16):
                    WattHour[A,16,hh]+=WattHour[A,i,hh]

                WattHour[A,17,hh]=sum(LSWfluxTotal[13,:]*(((1-DaytInd[kk])*Residents[A]+\
                DaytInd[kk]*Daytime[A])*WattPerson[hh])/(Area[A]+0.000001))  #metabolism
                WattHour[A,18,hh]=WattHour[A,8,hh]+WattHour[A,16,hh]+WattHour[A,17,hh]

            #IF HALF-HOURLY IS SELECTED>>> (for when GUI is sorted out)
                WattArea[A,:,48*dd+hh]=WattHour[A,:,hh]

            #If DAILY AVERAGE IS SELECTED>>> (for when GUI is sorted out)   
            for p in range(19):
                WattDay[A,p,dd]=sum(WattHour[A,p,:]/48.0)
        #WattHourDays[str(current)]=WattHour
        #WattArea[A,]=WattHour[A,:,:])
        #WattArea[A]= np.asarray(WattArea[A])
        refday+=1
        current+=dt.timedelta(days=1)

    WattDay=np.around(WattDay, decimals=3)

    # SubOA input file is kWh rather than Wh, so apply conversion
    if qfConfig.spatial_domain=='SubOA':
        TotArea=sum(Area)
        WattArea*=(1000/365/24/TotArea)
        #np.around(WattHour, 3)
    # Return everything needed to build a shapefile of the output
    return {'ID':Code, 'Data':WattArea, 'SpatialDomain':qfConfig.spatial_domain}



