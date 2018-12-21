from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
import os
import pickle
import re
from datetime import datetime as dt
from datetime import timedelta as timedelta
from distutils import dir_util
from shutil import copyfile
try:
    import pandas as pd
except:
    pass

from .DataManagement.spatialHelpers import feature_areas, loadShapeFile, shapefile_attributes
from .DataManagement.temporalHelpers import makeUTC
from pytz import timezone
from .Calcs3 import QF
from .DailyEnergyLoading import DailyEnergyLoading
from .DailyFactors import DailyFact
from .Disaggregate import disaggregate
from .EnergyProfiles import EnergyProfiles # For temporal energy use profiles
from .EnergyUseData import EnergyUseData   # For spatially disaggregated energy use data
from .FuelConsumption import FuelConsumption
from .GQFDataSources import DataSources
from .HumanActivityProfiles import HumanActivityProfiles
from .Params import Params
from .Partitions import Partitions
from .Population import Population
from .Transport import Transport
from .TransportProfiles import TransportProfiles


class Model(object):
    ''' Class that encapsulates a GreaterQF model instance'''
    def __init__(self):
        # Define the subfolders that should be present after each model run
        self.subFolders = {'render':'Images',
                           'config':'ConfigFiles',
                           'output':'ModelOutput',
                           'logs':'Logs',
                           'disagg':'DownscaledData'}

        # Set placeholders
        self.parameters = None          # GQF Parameters object
        self.ds = None                  # GQFDataSources object
        self.config = None              # GQF Config object
        self.resultsAvailable = False   # Flag to determine whether the model has run yet
        self.processedDataList = None   # Dict containing details of processed input data files

        # Path placeholders
        self.modelRoot = None           # Main model output directory
        self.processedInputData = None  # Folder containing already processed input data
        self.downscaledPath = None      # Folder where processed input data should ultimately be stored
        self.logPath = None             # Folder containing output logs
        self.modelOutputPath = None     # Folder containing model results
        self.configPath = None          # Folder containing copies of data sources and parameter files
        self.renderPath = None          # Folder containing rendered images from visualisation

        # Output file information
        # Filename format information so data can be retrieved
        self.reg = 'GQF[0-9]{4}[0-9]{2}[0-9]{2}_[0-9]{2}-[0-9]{2}\.csv'   # Regex
        self.dateStructure  = 'GQF%Y%m%d_%H-%M.csv'                               # Time format to use when saving output files
        self.fileList = None                                                      # List of model output files indexed by time
        self.outputAreas = None                                                   # Output area IDs

    def setParameters(self, file):
        ''' Set model parameters from GQF parameters file
         :param file: path to parameters file
        '''
        self.parameters = Params(file)

    def processInputData(self):
        '''
        Pre-process input data according to data sources file, and save disaggregated spatial files to a folderoutlay['EPSG']
        :param dataSourcesFile: str: Path to data sources file for use with GQFDataSources() object
        :param outputFolder: str: Folder at which to save processed input data for later use
        :return: Path to processed data
        '''
        if self.ds is None:
            raise Exception('Data sources file must be set  before processing input data')

        if self.parameters is None:
            raise Exception('Model parameters file must be set before processing input data')

        if self.downscaledPath is None:
            raise Exception('Model output folder needs to be set before processing input data')

        processedPath = disaggregate(qfDataSources=self.ds, outputFolder=self.downscaledPath, qfParams=self.parameters)
        return processedPath

    def setDataSources(self, file):
        '''
        Set data sources given data sources file (must be acceptable to QFDataSources object
        :param file: Path to data sources file
        '''
        self.ds = DataSources(file)

    def setOutputDir(self, path):
        '''
        Set directory that will contain model outputs and other supplementary artefacts, and create folder structure if needed
        :param path: str: Path to use
        '''

        self.modelRoot = path
        self.configPath = os.path.join(path, self.subFolders['config'])
        self.downscaledPath = os.path.join(path, self.subFolders['disagg'])
        self.modelOutputPath = os.path.join(path, self.subFolders['output'])
        self.renderPath = os.path.join(path, self.subFolders['render'])

        self.logPath = os.path.join(path, self.subFolders['logs'])
        # Set up folder structure if it doesn't exist
        for of in [self.configPath, self.downscaledPath, self.modelOutputPath, self.logPath, self.renderPath]:
            if not os.path.exists(of):
                os.makedirs(of)

    def setConfig(self, configObj):
        '''
        Set model configuration
        :param configObj: Populated Config object for greaterQF
        '''
        self.config = configObj

    def setPreProcessedInputFolder(self, path):
        '''
        Set the path containing pre-processed data created using processInputData() method
        Checks manifest for all files
        :param path: str: Path to folder containing model outputs
        :return: None
        '''
        if self.downscaledPath is None:
            raise Exception('Model output folder must be set before choosing a folder containing existing pre-processed input data (it gets copied there)')

        # Validate pre-processed inputs
        expectedManifest = os.path.join(path, 'MANIFEST')
        if os.path.exists(expectedManifest):
            with open(expectedManifest, 'rb') as manf:
                manif = pickle.load(manf)
                if type(manif) is not dict:
                    raise Exception(path + ' does not seem to be a valid store of processed input data (manifest file missing)')
                self.processedDataList = manif
                self.processedInputData = path
        else:
            raise Exception('The specified processed input data path ' + path + ' does not exist')

    def run(self):
        ''' Run model based on configuration, parameters and pre-processed input data'''

        # Are folders set up?
        # Is object configured?
        if self.config is None:
            raise Exception('self.setConfig must be used before model run')

        if self.ds is None:
            raise Exception('self.setDataSources must be used before model run')

        if self.parameters is None:
            raise Exception('self.setParameters must be used before model run')

        if self.processedDataList is None:
            raise Exception('No processed input data has been set')

        if self.modelOutputPath is None:
            raise Exception('The model output path has not been set')

        # If necessary, copy the pre-processed inputs to the /DownscaledData/ subdirectory of model output
        if self.processedInputData != self.downscaledPath:
            dir_util.copy_tree(src=self.processedInputData, dst=self.downscaledPath, update=True)

        # Copy data sources and parameters files to output folder for traceability
        # Exception should only arise if they are copying to themselves, in which case it's fine
        try:
            copyfile(self.parameters.inputFile, os.path.join(self.configPath, 'Parameters.nml'))
            copyfile(self.ds.inputFile, os.path.join(self.configPath, 'DataSources.nml'))
        except Exception:
            pass

        self.mostcalcs()
        self.loadModelResults(self.modelRoot)
        self.resultsAvailable = True

    def mostcalcs(self):
        '''
        Get total latent and/or sensible and/or wastewater heat fluxes for domestic & industrial
        Assuming spatial units are already consistent and in shapefiles of identical projection
        :param qfConfig:
        :param qfParams:
        :param qfDataSources:
        :param disaggregated:
        :param outputFolder:
        :param logFolder:
        :return:
        '''
        print('one')
        # Get partitioning and heat of combustion values
        partitions = Partitions(self.config, self.parameters)
        props = partitions.fluxProp  # Proportion of possible fluxes (latent, wastewater, sensible based on what user selected) to include in results
        startDates = self.config.dt_start
        endDates = self.config.dt_end
        # Set up UTC time bins @ 30 min intervals
        for i in range(0,len(startDates),1):
            bins = pd.date_range(pd.datetime.strptime(startDates[i].strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M') + timedelta(seconds=1800),
                                 pd.datetime.strptime(endDates[i].strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M'),
                                 tz='UTC',
                                 freq='30Min')
            if i == 0:
                timeBins = bins
            else:
                timeBins = timeBins.append(bins)
        print('two')
        # Make some aliases for the output layer for brevity
        outShp = self.ds.outputAreas_spat['shapefile']
        outFeatIds =  self.ds.outputAreas_spat['featureIds']
        outEpsg = self.ds.outputAreas_spat['epsgCode']
        print('three')
        # Populate temporal disaggregation objects
        # Building energy daily loadings (temporal disaggregation from Annual to daily)
        dailyE = DailyEnergyLoading(self.parameters.city, useUKholidays=self.parameters.useUKholidays)
        # Each component has 1..n data sources. Add each one, looping over them
        [dailyE.addLoadings(den['profileFile']) for den in self.ds.dailyEnergy]
        print('four')
        # Building energy diurnal cycles (temporal disaggregation from daily to half-hourly). These are provided in local time (London)
        diurnalE = EnergyProfiles(self.parameters.city, use_uk_holidays=self.parameters.useUKholidays, customHolidays=self.parameters.customHolidays)
        [diurnalE.addDomElec(de['profileFile']) for de in self.ds.diurnDomElec]
        [diurnalE.addDomGas(dg['profileFile']) for dg in self.ds.diurnDomGas]
        [diurnalE.addEconomy7(e7['profileFile']) for e7 in self.ds.diurnEco7]
        [diurnalE.addIndElec(ie['profileFile']) for ie in self.ds.diurnIndElec]
        [diurnalE.addIndGas(ig['profileFile']) for ig in self.ds.diurnIndGas]
        print('five')
        # Diurnal traffic patterns
        diurnalT = TransportProfiles(self.parameters.city, use_uk_holidays=self.parameters.useUKholidays, customHolidays=self.parameters.customHolidays)
        [diurnalT.addProfiles(tr['profileFile']) for tr in self.ds.diurnalTraffic]
        print('six')
        # Workday metabolism profile
        hap = HumanActivityProfiles(self.parameters.city, use_uk_holidays=self.parameters.useUKholidays, customHolidays=self.parameters.customHolidays)
        [hap.addProfiles(ha['profileFile']) for ha in self.ds.diurnMetab]
        pop = Population()
        pop.setOutputShapefile(outShp, outEpsg, outFeatIds)
        [pop.injectResPop(rp['file'], makeUTC(rp['startDate']), rp['attribute'], rp['EPSG']) for rp in self.processedDataList['resPop']]
        [pop.injectWorkPop(wp['file'], makeUTC(wp['startDate']), wp['attribute'], wp['EPSG']) for wp in self.processedDataList['workPop']]
        bldgEnergy = EnergyUseData()
        bldgEnergy.setOutputShapefile(outShp, outEpsg, outFeatIds)
        print('seven')
        [bldgEnergy.injectDomesticElec(rp['file'], makeUTC(rp['startDate']), rp['attribute'], rp['EPSG']) for rp in self.processedDataList['domElec']]
        [bldgEnergy.injectDomesticGas(rp['file'], makeUTC(rp['startDate']), rp['attribute'], rp['EPSG']) for rp in self.processedDataList['domGas']]
        [bldgEnergy.injectEconomy7Elec(rp['file'], makeUTC(rp['startDate']), rp['attribute'], rp['EPSG']) for rp in self.processedDataList['domEco7']]
        [bldgEnergy.injectIndustrialElec(rp['file'], makeUTC(rp['startDate']), rp['attribute'], rp['EPSG']) for rp in self.processedDataList['indElec']]
        [bldgEnergy.injectIndustrialGas(rp['file'], makeUTC(rp['startDate']), rp['attribute'], rp['EPSG']) for rp in self.processedDataList['indGas']]
        fc = FuelConsumption(self.ds.fuelConsumption[0]['profileFile'])
        trans = Transport(fc, self.parameters)
        trans.setOutputShapefile(outShp, outEpsg, outFeatIds)
        [trans.injectFuelConsumption(rp['file'], makeUTC(rp['startDate']), rp['EPSG']) for rp in self.processedDataList['transport']]
        ds = None
        # Get daily factors
        df = DailyFact(self.parameters.useUKholidays) # Use UK holidays
        print('eight')
        # Get area of each output feature, along with its identifier
        areas = (bldgEnergy.domGas.getOutputFeatureAreas())
        print('nine')
        for tb in timeBins:
            WH = QF(areas.index.tolist(), tb.to_pydatetime(), 1800, bldgEnergy, diurnalE, dailyE, pop, trans, diurnalT, hap, df,  props, self.parameters.heatOfCombustion)
            # Write out the full time step to a file
            WH.to_csv(os.path.join(self.modelOutputPath, tb.strftime(self.dateStructure)), index_label='featureId')
        print('ten')
        # Write log files to disk for traceability
        bldgEnergy.logger.writeFile(os.path.join(self.logPath, 'EnergyUseSpatial.txt'))
        pop.logger.writeFile(os.path.join(self.logPath, 'PopulationSpatial.txt'))
        trans.logger.writeFile(os.path.join(self.logPath, 'transportSpatial.txt'))
        hap.logger.writeFile(os.path.join(self.logPath, 'humanActivityProfiles.txt'))
        diurnalT.logger.writeFile(os.path.join(self.logPath, 'diurnalTransport.txt'))
        dailyE.logger.writeFile(os.path.join(self.logPath, 'dailyEnergy.txt'))

    def loadModelResults(self, path):
        '''
        Load a previous set of model results so the outputs/configuration can be revisited
        :param path: Path of model output folder (this contains the processed input data and parameters files needed)
        :return: Dict of model run parameters e.g. config file location (for user information)
        '''
        # Check model outputs are intact, and set if so
        if not os.path.exists(path):
            raise Exception('Model output directory ' + str(path) + ' not found')

        for sub in list(self.subFolders.values()):
            directory = os.path.join(path, sub)
            if not os.path.exists(directory):
                raise Exception('Chosen model output folder ' + str(path) + ' did not contain enough subfolders to be genuine')

        # If directory structure checks out, try populating the object
        self.setOutputDir(path)
        self.setPreProcessedInputFolder(os.path.join(path, self.subFolders['disagg']))

        # Don't populate the config or datasources fields: Only allow re-runs through an explicit method call

        # Scan folder for files matching the expected pattern
        files = os.listdir(self.modelOutputPath)
        tz = timezone('UTC')
        self.fileList={}
        for f in files:
            a = re.search(self.reg, f)
            if a is not None:
                self.fileList[tz.localize(dt.strptime(f, self.dateStructure))] = os.path.join(self.modelOutputPath, f)

        self.fileList = pd.Series(self.fileList)

        self.setDataSources(os.path.join(self.configPath, 'DataSources.nml'))
        self.setParameters(os.path.join(self.configPath,  'Parameters.nml'))
        # Extract the location names from the first file in the list
        # This assumes all files in the folder are for identical output areas
        firstFile = pd.read_csv(self.fileList[0], header=0, index_col=0)
        self.outputAreas = list(firstFile.index)
        self.resultsAvailable = True
        return {'outputPath':self.modelOutputPath,
                'processedInputData':self.processedInputData,
                'logPath':self.logPath,
                'paramsFile':os.path.join(self.configPath,  'Parameters.nml'),
                'dsFile':os.path.join(self.configPath, 'DataSources.nml')}

    def fetchResultsForLocation(self, id, startTime, endTime):
        '''
        Gets time series for feature ID between startTime and endTime for Total, Building, Metabolic and Transport QF
        :param id:
        :return:
        '''
        if id not in self.outputAreas:
            raise Exception('Requested ID ' + id + ' not among available output areas')

        if (type(startTime) is not dt) or (type(endTime) is not dt):
            raise ValueError('Requested start and end times must be of type datetime')

        # All model outputs are UTC
        tz = timezone('UTC')
        start = tz.localize(startTime)
        end = tz.localize(endTime)

        # See if there are any files to return
        relevant = self.fileList[(self.fileList.index >= start) & (self.fileList.index <= end)]
        if len(relevant) == 0:
            raise ValueError('Requested start and end times must be of type datetime')

        indices =  self.fileList.index[(self.fileList.index >= start) & (self.fileList.index <= end)]
        # Go through the files and build up time series of Total, building, transport and
        combined = pd.DataFrame(index=indices, columns=['AllTot', 'BldTot', 'TransTot', 'Metab', 'ElDmUnr', 'ElDmE7', 'ElId', 'GasDm', 'GasId', 'OthrId', 'Mcyc', 'Taxi', 'Car', 'Bus', 'LGV', 'Rigd', 'Art'])
        for i in indices:
            outs = pd.read_csv(self.fileList[i], header=0, index_col=0)
            combined['AllTot'].loc[i] = outs['AllTot'].loc[id]
            combined['BldTot'].loc[i] = outs['BldTot'].loc[id]
            combined['TransTot'].loc[i] = outs['TransTot'].loc[id]
            combined['Metab'].loc[i] = outs['Metab'].loc[id]
            combined['ElDmUnr'].loc[i] = outs['ElDmUnr'].loc[id]
            combined['ElDmE7'].loc[i] = outs['ElDmE7'].loc[id]
            combined['ElId'].loc[i] = outs['ElId'].loc[id]
            combined['GasDm'].loc[i] = outs['GasDm'].loc[id]
            combined['GasId'].loc[i] = outs['GasId'].loc[id]
            combined['OthrId'].loc[i] = outs['OthrId'].loc[id]
            combined['Mcyc'].loc[i] = outs['Mcyc'].loc[id]
            combined['Taxi'].loc[i] = outs['Taxi'].loc[id]
            combined['Car'].loc[i] = outs['Car'].loc[id]
            combined['Bus'].loc[i] = outs['Bus'].loc[id]
            combined['LGV'].loc[i] = outs['LGV'].loc[id]
            combined['Rigd'].loc[i] = outs['Rigd'].loc[id]
            combined['Art'].loc[i] = outs['Art'].loc[id]

        return combined

    def getOutputLayerInfo(self):
        '''
        Return the location and metadata of the output layer
        :return:
        '''
        # Just use one of the disaggregated layers, since these are using same feature mappings
        return self.processedDataList['domGas'][0]

    def getOutputAreaIDs(self):
        '''
        Return list of output areas
        :return: List of IDs
        '''
        return self.outputAreas

    def getTimeSteps(self):
        '''
        Return list of time steps
        :return:
        '''
        return list(self.fileList.index)

    def getFileList(self):
        '''
        Returns pandas time series of model output files
        :return:
        '''
        return self.fileList

    def getOutputAreas(self):
        ''' Return output areas in square metres, and their IDs (pandas series)'''
        a = loadShapeFile(self.ds.outputAreas_spat['shapefile'])
        s = pd.Series(feature_areas(a))
        a = None
        return s

    def getFeatureMapper(self):
        ''' Return a pandas series that allows the preferred feature ID to be looked up from the numeric feature ID'''
        a = loadShapeFile(self.ds.outputAreas_spat['shapefile'])
        if self.ds.outputAreas_spat['featureIds'] is None:
            featureMapper = pd.DataFrame(shapefile_attributes(a).index, index = shapefile_attributes(a).index)
        else:
            # Create mapping from real (numeric) feature ID to desired (string) feature ID
            featureMapper = shapefile_attributes(a)[self.ds.outputAreas_spat['featureIds']]
        a = None
        return featureMapper

    def getReverseFeatureMapper(self):
        ''' Return a pandas series that allows the numeric feature ID to be looked up from the perferred feature ID'''
        a = self.getFeatureMapper()
        b = pd.Series(data=a.index.astype('int'), index=a.values)
        return b