'''Creates classes that read the correct data file based on the input spatial
resolution. Classes include functions that extract the data for area, number of 
residents, daytime population, energy fraction and area code for each zone
within a domain.  
'''
import csv
import numpy as np
import datetime as dt
import string as st
import os
def getareacodes(conf):
    '''Extracts an array (length containing the area codes
    for all zones within chosen spatial domain.
    '''
    areaname = conf.SpatialDomain
    if areaname == 'SubOA200Data':
        y = SubOAAreaDataReader(areaname)
    else:
        y = AreaDataReader(areaname)

    y.Code()
    Code = y.IDCode

    return Code

class AreaDataReader:
    """Converts area data csv file to a numpy array, with functions
    calculating separate values for; Area: AData(); Residents: RData(); 
    Daytime: DDAta() and Energy: EData (in Wm-2). Takes file name as 
    only argument as follows:
    GORData: Greater London - 1 zone
    LAData: Local Auhority - 33 zones
    MLSOAData: middle level super output areas - 983 zones
    Gridkm2Data: km2 grid - 1730 zones
    LLSOAData: lower level super output areas - 4765 zones
    OAData: output areas - 24140 zones
    Grid200Data: 200m x 200m grid - 40632 zones
    For SubOA200Data, use class SubOAAreaDataReader instead. 
    """
    def __init__(self, areaname, inputDataPath):
        # areaname: the area name as it is called in the file (no.csv or leading folder)
        # inputDataPath: The folder in which the input data resides
        area_file = os.path.join(inputDataPath, areaname + '.csv')
       # print(area_file)    ######### TESTING ONLY
        reader=csv.reader(open(area_file,"rU"),delimiter=';')
        x=list(reader)[1:]
        self.array=np.array(x)
        self.Area=None
        self.Residents=None
        self.Daytime=None
        self.Energy=None
        self.IDCode=None
    def AData(self):    #area of each domain
        self.Area=self.array[:,1].astype('float')
    def RData(self):    #number of residents within each domain
        self.Residents=self.array[:,2].astype('float')
    def DData(self):    #daytime population
        self.Daytime=self.array[:,3].astype('float')
    def EData(self):    #energy value of domain
        self.Energy=self.array[:,4:-1].astype('float')
    def Code(self):     #area code
        # If code seems to be a comma separated list, just take the first part (this is the ID). It's the case for 1km grid but not boroughs
        self.IDCode=np.array([x.split(',')[0] for x in self.array[:,0].astype(str)])

        
class SubOAAreaDataReader:
    """Converts area data csv file to a numpy array, with functions
    calculating separate values for; Area: AData(); Residents: RData(); 
    Daytime: DDAta() and Energy: EData (in Wm-2).
    SubOAData: sub output area - 147315 domains
    """
    def __init__(self, areaname, dataDir):
        area_file = os.path.join(dataDir, 'SubOA200Data.csv')
       # print(area_file)   ######### TESTING ONLY
        reader=csv.reader(open(area_file,"rU"),delimiter=';')
        x=list(reader)[1:]
        self.array=np.array(x)
        self.Area=None
        self.Residents=None
        self.Daytime=None
        self.Energy=None
        self.Code=None
    def AData(self):
        self.Area=self.array[:,7].astype('float')
    def RData(self):
        self.Residents=self.array[:,8].astype('float')
    def DData(self):
        self.Daytime=self.array[:,9].astype('float')
    def EData(self):
        self.Energy=self.array[:,10:-1].astype('float')
    def Code(self):
        self.Code=self.array[:,0].astype(str)


def load(input_data_dir):
    # Read transportation, metabolism, daily and hourly energy use data
    # Return dict of datasets

    reader = csv.reader(open(os.path.join(input_data_dir, "Index1_Transportation.csv"), "rt"), delimiter=';')
    x = list(reader)[1:]
    HHourTrafficIndex = np.array(x).astype('float')
    reader = csv.reader(open(os.path.join(input_data_dir, "Index2_EnergyHourly.csv"), "rt"), delimiter=';')
    x = list(reader)[1:]
    nparray = np.array(x).astype('float')
    EnergyHourly = nparray[:, :-1]
    reader = csv.reader(open(os.path.join(input_data_dir, "Index3_EnergyDaily.csv"), "rt"), delimiter=';')
    x = list(reader)[1:]
    EnergDailyFractFile = np.array(x).astype('float')
    EnergyDaily = EnergDailyFractFile[:, :]

    Index4 = np.recfromcsv(os.path.join(input_data_dir, "Index4_Metabolism.csv"), delimiter=';')
    WattPerson = Index4.wperson
    DaytInd = Index4.daytindworksatsun
    return {'Index4':Index4, 'WattPerson':WattPerson, 'DaytInd':DaytInd, 'EnergyHourly':EnergyHourly, 'EnergyDaily':EnergyDaily, 'HHourTrafficIndex':HHourTrafficIndex}

