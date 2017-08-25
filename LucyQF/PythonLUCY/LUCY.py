import os
import re
from datetime import datetime as dt
from datetime import timedelta as timedelta
from shutil import copyfile
from distutils.dir_util import copy_tree
import traceback
import pickle
from pytz import timezone
try:
    import pandas as pd
    import numpy as np
    import netCDF4 as nc4
except:
    pass

from RegionalParameters import RegionalParameters
from LUCYDiurnalProfile import LUCYDiurnalProfile
from Disaggregate import disaggregate
from LUCYfunctions import qm, qb, qt, offset, increasePerHDD, increasePerCDD
from DailyTemperature import DailyTemperature
from LUCYDataSources import LUCYDataSources
from LUCYParams import LUCYParams
from MetabolismProfiles import MetabolismProfiles
from DataManagement.spatialHelpers import intOrString, loadShapeFile
from DataManagement.temporalHelpers import is_holiday
from PyQt4.QtCore import QObject, pyqtSignal


class LQFWorker(QObject):
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    def __init__(self, ds, params, outputFolder, UMEPgrid=None, UMEPcoverFractions=None, UMEPgridID=None):
        QObject.__init__(self)
        self.killed = False
        self.ds = ds
        self.params = params
        self.outputFolder = outputFolder
        self.UMEPgrid = UMEPgrid
        self.UMEPcoverFractions = UMEPcoverFractions
        self.UMEPgridID = UMEPgridID

    def kill(self):
        self.killed=True

    def run(self):
        try:
            outputFolder = disaggregate(self.ds, self.params, self.outputFolder, self.UMEPgrid, self.UMEPcoverFractions, self.UMEPgridID, self.update)
            self.finished.emit(outputFolder)
        except Exception,e:
            self.error.emit(e, traceback.format_exc())

class Model():
    ''' Class that encapsulates a GreaterQF model instance'''
    def __init__(self):
        # Define the subfolders that should be present after each model run
        self.subFolders = {'config':'ConfigFiles',
                           'output':'ModelOutput',
                           'logs':'Logs',
                           'disagg':'DownscaledData',
                           'render':'Images'}

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

        # Optional extra disaggregation data (comes from UMEP land cover fraction calculator)
        self.UMEPgrid = None            # Path to shapefile containing grid to which land cover fractions correspond
        self.UMEPcoverFractions = None  # Path to CSV file containing land cover fractions for this grid (UMEP output)
        self.UMEPgridID = None          # Name of field in shapefile that contains unique ID for each grid cell.

        # Output file information
        # Filename format information so data can be retrieved
        self.reg = 'LQF[0-9]{4}[0-9]{2}[0-9]{2}_[0-9]{2}-[0-9]{2}\.csv'   # Regex
        self.dateStructure  = 'LQF%Y%m%d_%H-%M.csv'                               # Time format to use when saving output files
        self.fileList = None                                                       # List of model output files indexed by time
        self.outputAreas = None                                                    # Output area IDs

    def setParameters(self, file):
        ''' Set model parameters from GQF parameters file
         :param file: path to parameters file
        '''
        self.parameters = LUCYParams(file)

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
        processedPath = disaggregate(ds=self.ds, params=self.parameters, outputFolder=self.downscaledPath, UMEPgrid=self.UMEPgrid, UMEPcoverFractions=self.UMEPcoverFractions, UMEPgridID=self.UMEPgridID)

        return processedPath

    def setDataSources(self, file):
        '''
        Set data sources given data sources file (must be acceptable to QFDataSources object
        :param file: Path to data sources file
        '''
        self.ds = LUCYDataSources(file)

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

        # Reset processed data list and processed input data folder too, as these get copied to output folder
        self.processedDataList = None
        self.processedInputData = None

    def setLandCoverData(self, file):
        self.UMEPcoverFractions = file

    def setLandCoverGrid(self, file):
        self.UMEPgrid = file

    def setLandCoverGridID(self, id):
        self.UMEPgridID = id

    def setConfig(self, configObj):
        '''
        Set model configuration
        :param configObj: Populated Config object for greaterQF
        '''
        self.config = configObj

    def setPreProcessedInputFolder(self, path):
        '''
        Set the path containing pre-processed data created using processInputData() method
        Copies pre-processed data to current model output folder so it can be kept track of later
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

            # If drawing pre-processed input data in, copy it to downscaledData folder for current model
            if path != self.downscaledPath:
                copy_tree(path, self.downscaledPath)
            self.processedInputData = self.downscaledPath
        else:
            raise Exception('The specified processed input data files ' + path + ' do not exist')

    def run(self):
        ''' Run model based on configuration, parameters and pre-processed input data'''
        # Are folders set up?
        # Is object configured?
        if self.config is None:
            raise Exception('Internal error: Model config was not set.')

        if self.ds is None:
            raise Exception('Data sources file must be specified before model run')

        if self.parameters is None:
            raise Exception('Parameters file must be set before model run')

        if self.processedDataList is None:
            raise Exception('No processed input data has been set')

        if self.modelOutputPath is None:
            raise Exception('The model output path has not been set')

        self.setupAndRun(self.config['startDates'], self.config['endDates'])

        # Copy data sources and parameters files to output folder for traceability
        # Exception should only arise if they are copying to themselves, in which case it's fine
        try:
            copyfile(self.parameters.inputFile, os.path.join(self.configPath, 'Parameters.nml'))
            copyfile(self.ds.inputFile, os.path.join(self.configPath, 'DataSources.nml'))
        except:
            pass

        self.loadModelResults(self.modelRoot)

    def setupAndRun(self, startDates, endDates):
        '''
        Get total latent and/or sensible and/or wastewater heat fluxes for domestic & industrial
        Assuming spatial units are already consistent and in shapefiles of identical projection
        :param qfConfig: Model configuration object
        :param qfParams: LUCYParams object
        :param qfDataSources: LUCYDataSources object
        :param disaggregated:
        :param outputFolder:
        :param logFolder:
        :return:
        '''
        # Set up time steps
        timeStepDuration = 3600 #Seconds
        startDates = np.sort(np.unique(startDates))
        endDates = np.sort(np.unique(endDates))
        try:
            cityTimezone = timezone(self.parameters.timezone)
        except:
            raise ValueError('The "timezone" entry in the LQF parameters file must be a valid time zone string')

        for i in range(0,len(startDates),1):
            bins = pd.date_range(pd.datetime.strptime(startDates[i].strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M') + timedelta(seconds=timeStepDuration),
                                 pd.datetime.strptime(endDates[i].strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M'),
                                 tz='UTC',
                                 freq='60Min')
            if i == 0:
                timeBins = bins
            else:
                timeBins = timeBins.append(bins)

        # Populate already-disaggregated energy, vehicle count and population data
        outFeatIds =  self.ds.outputAreas_spat['featureIds']
        regPar = RegionalParameters()
        regPar.setWorldDatabase(self.ds.database)
        # If the user went for extra disaggregation, use this. If not, don't
        if 'extra_disagg' in self.processedDataList.keys():
            # Create three copies of the regional parameters object, each using a different "population" to disaggregate buildings, vehicles and metabolism
            mt = self.processedDataList['extra_disagg']['metabolism'][0]
            tp = self.processedDataList['extra_disagg']['transport'][0]
            bd = self.processedDataList['extra_disagg']['building'][0]
            al = self.processedDataList['extra_disagg']['allocations']

            # Set as the output layer the version that was generated during disaggregation
            regPar.injectAttributedOutputLayer(os.path.join(self.downscaledPath, al['file']), al['EPSG'], al['featureIds']) # This contains country assignments already
            regPar.injectResPopLayer(os.path.join(self.downscaledPath, bd['file']), bd['EPSG']) # Assign a residential population
            regPar.injectVehPopLayer(os.path.join(self.downscaledPath, tp['file']), tp['EPSG']) # Assign transport "population"
            regPar.injectMetabPopLayer(os.path.join(self.downscaledPath, mt['file']), mt['EPSG']) # Assign metabolising population
        else:
            # Use same population density for vehicle, metabolism and building resident spatial distributions
            rp = self.processedDataList['resPop'][0]
            al = self.processedDataList['allocations']
            regPar.injectAttributedOutputLayer(os.path.join(self.downscaledPath, al['file']), al['EPSG'], outFeatIds)
            regPar.injectResPopLayer(os.path.join(self.downscaledPath, rp['file']), rp['EPSG'])
            regPar.injectVehPopLayer(os.path.join(self.downscaledPath, rp['file']), rp['EPSG'])
            regPar.injectMetabPopLayer(os.path.join(self.downscaledPath, rp['file']), rp['EPSG'])

        # Now that countries are assigned to output areas, get local information
        areas = (regPar.worldAttributes.getOutputFeatureAreas())
        dominantCountry = regPar.getDominantCountry() # The country that intersects the majority of output areas
        weekendDays = regPar.getWeekendDaysByRegion()
        fixedHolidays = regPar.getFixedHolidays(startDates[0], endDates[-1])

        #### Populate temporal input data with either database values, or local overrides if available
        # Daily temperature - values taken to represent whole study area
        # Provide empty list of weekend days and holidays because weekday/weekend differences are meaningless for T
        dailyT = DailyTemperature(self.parameters.timezone, weekendDays=[], use_uk_holidays=[], other_holidays=[])
        [dailyT.addTemperatureData(te) for te in self.ds.dailyTemp]
        # Sttch together fixed holidays from database and any user-defined holidays
        combinedHolidays = []
        combinedHolidays.extend(fixedHolidays[dominantCountry])
        combinedHolidays.extend(self.parameters.custom_holidays)
        # Traffic cycle
        if self.ds.diurnTraffic is not None: # Take existing 7-day cycle from file. This applies to whole study area.
            # Weekend days are drawn from the first study area in the list of those intersected
            # Add fixed holidays in dominant country to any already added
            trafficProfile = LUCYDiurnalProfile(self.parameters.timezone,
                                                weekendDays=weekendDays[dominantCountry],
                                                use_uk_holidays=self.parameters.use_uk_hols,
                                                other_holidays=combinedHolidays)
            [trafficProfile.addProfile(tr) for tr in self.ds.diurnTraffic]
        else:
            # Build a weekly cycle for each country involved in the modelling run, accounting for when weekends occur
            # Energy cycles are used for transport as the database no data for transport.
            weekendTraffic = regPar.getTransportCycles(True)
            weekdayTraffic = regPar.getTransportCycles(False)
            trafficProfile = {}             # Create a dict of objects, one for each country. NOTE: this assumes the whole study area lies in the same time zone
            for country in weekdayTraffic.index:
                trafficProfile[country] = LUCYDiurnalProfile(self.parameters.timezone,
                                                             weekendDays=list(weekendDays[country]),
                                                             use_uk_holidays=self.parameters.use_uk_hols,
                                                             other_holidays=combinedHolidays)
                # Generate 7-day cycle from reference data, with weekends in the right places given local country
                cycle = pd.concat([weekdayTraffic.loc[country]]*7)
                cycle.index = range(0, len(cycle))
                for wdd in weekendDays[country]:
                    cycle[range(wdd*24, (1+wdd)*24)] = weekendTraffic.loc[country].values # Overwrite the weekend days with weekend values
                trafficProfile[country].addWeeklyCycle(cityTimezone.localize(dt(2015,01,01)), cityTimezone.localize(dt(2015,12,31)), cycle) # 2015 is arbitrary; will work for all years.

        # Building cycle: Same approach as for Traffic cycle
        if self.ds.diurnEnergy is not None:
            bldgProfile = LUCYDiurnalProfile(self.parameters.timezone,
                                             weekendDays=weekendDays[dominantCountry],
                                             use_uk_holidays=self.parameters.use_uk_hols,
                                             other_holidays=combinedHolidays)
            [bldgProfile.addProfile(bl) for bl in self.ds.diurnEnergy]
        else:
            weekendBldg = regPar.getBuildingCycles(True)
            weekdayBldg = regPar.getBuildingCycles(False)
            bldgProfile = {}
            for country in weekendBldg.index:
                bldgProfile[country] = LUCYDiurnalProfile(self.parameters.timezone,
                                                          weekendDays=list(weekendDays[country]),
                                                          use_uk_holidays=self.parameters.use_uk_hols,
                                                          other_holidays=combinedHolidays)
                cycle = pd.concat([weekdayBldg.loc[country]]*7)
                cycle.index = range(0, len(cycle))
                for wdd in weekendDays[country]:
                    cycle[range(wdd*24, (1+wdd)*24)] = weekendBldg.loc[country].values # Overwrite the weekend days with weekend values
                bldgProfile[country].addWeeklyCycle(cityTimezone.localize(dt(2015,01,01)), cityTimezone.localize(dt(2015,12,31)), cycle) # 2015 is arbitrary; will work for all years.

        # This version of the model doesn't allow a custom metabolic cycle.
        metabCycles = MetabolismProfiles(self.parameters.timezone,workLevel=175, sleepLevel=75)

        # List of dates to run
        dates = np.unique(timeBins.date)
        columns = ['nation_id']
        def to_datestring(x): return (x + timedelta(hours=24)).strftime('%Y-%m-%d')
        columns.extend(map(to_datestring, dates))

        # Data that will be stored to summarise the run so it can be loaded in SUEWS
        national_attribs_used = [] # Store the unique national attributes used in the model
        temperatures = []
        # Also store local_population_density, which is for metabolism and is multiplied by the metab_cycle

        prevYear = -1000
        for d in dates:
            # The list of dates contains the final time bin at UTC midnight the next day. Don't execute the whole day
            if sum(timeBins.date == d) == 1:
                continue

            # Lookups that apply to the whole day (look up at noon to avoid edge effects)
            d_notimezone = dt.combine(d, dt.min.time()) + timedelta(hours=12)
            d_lookup = timezone('UTC').localize(d_notimezone)
            d_lookup_temperature = timezone(self.parameters.timezone).localize(d_notimezone) # Daily temperature data is at local time and once per day, so look up using local time
            if d_lookup.year > prevYear:
                # Only refresh attributes list if a new year has begun (attributes are done per year)
                attribs = regPar.getAttribsTable(areas.index, d_lookup.year)
                # Extend attribs table using heating/cooling parameters
                validStatus = attribs['ecostatus'].dropna().astype('int')
                attribs['increasePerCDD'] = np.nan
                attribs['increasePerHDD'] = np.nan
                attribs['offset'] = np.nan
                attribs['increasePerCDD'].loc[validStatus.index] =  pd.Series(increasePerCDD())[validStatus].values
                attribs['increasePerHDD'].loc[validStatus.index] =  pd.Series(increasePerHDD())[validStatus].values
                attribs['offset'].loc[validStatus.index] =  pd.Series(offset())[validStatus].values

                energyUse = regPar.getEnergyUse(areas.index, d_lookup.year)
                vehicleCountData = regPar.getVehCount(areas.index, d_lookup.year)
                metabPopulationDensity = attribs['metabPop']/areas # People per square metre

            temperatures.append(dailyT.getTemp(d_lookup_temperature, timeStepDuration)[0]) # Mean daily temperature
            # Get national values from attributes table, compress to unique sets of national values only, then
            # generate summary and assign each model output area to a set of unique values. Keep track of changes over time.
            unique_attribs = attribs.drop(['metabPop', 'vehPop', 'resPop'], axis=1).drop_duplicates().dropna()

            matched = False
            # If a combination of attributes hasn't been seen before, add it to a stack
            for idx in unique_attribs.index:
                dictified = unique_attribs.loc[idx].to_dict()
                for attr in national_attribs_used:
                    # If this combination of attributes hasn't been seen before, add it to the list of national attributes
                    # that were used, along with the date on which it was used
                    if dictified == attr:
                        matched = True

                if not matched:
                    national_attribs_used.append(dictified)

            attrib_indexes = pd.Series(index=attribs.index)
            for idx in range(len(national_attribs_used)):
                # Which of the area attributes match this unique row?
                matches = pd.Series(index=attribs.index)
                matches[:] = True
                for c in attribs.drop(['resPop', 'vehPop', 'metabPop'], axis=1).columns: # Local populations dropped as they are OA specific
                    matches = matches & (attribs[c] == national_attribs_used[idx][c])
                    attrib_indexes[matches] = intOrString(idx)

            # Get all unique diurnal cycles for this date; determine which model output area(s) each one applies to; append
            # to list covering all time. IF unique cycle seen before, add this date to the list of dates to which this cycle applies
            diurnal_times = pd.date_range(d, freq='H', periods=25, tz='UTC')[1:25]

            # Execute model calculations for each UTC hour and produce output files
            for t in range(0,24):
                ts_dt = diurnal_times[t].to_datetime()
                # Get offset between UTC and the modelled time zone
                localLookupTimeBin = cityTimezone.localize(ts_dt.replace(tzinfo=None))
                tzOffset = ts_dt - localLookupTimeBin

                # Is this time step a holiday in local time?
                # Subtract 1 second from the time bin end in local time to avoid any midnight effect when the time step
                # resides in the previous day
                holiday = is_holiday((ts_dt + tzOffset - timedelta(seconds=1)).date(), self.parameters.use_uk_hols, combinedHolidays)
                # Daily temperature elicited in local time. This means first and last time steps of the year may overrun/underrun available
                # temperature data and trigger a lookup
                temperatureNow = dailyT.getTemp(ts_dt, timeStepDuration)[0]

                #### Metabolic flux ###
                # Use country-specific parameters
                metabLevels = {unique_attribs['admin'].loc[i]:metabCycles.getWattPerson(timeBinEnd=ts_dt,
                                                                                        timeBinDuration=timeStepDuration,
                                                                                        medianAsleep=attribs['sleepTime'].loc[i],
                                                                                        medianAwake=attribs['wakeTime'].loc[i],
                                                                                        transitionDuration=attribs['transition'].loc[i]) for i in unique_attribs.index}
                metabolismNow = pd.Series(index=attribs.index)
                for idx in unique_attribs['admin']:
                    metabolismNow.loc[attribs['admin'] == idx] = metabLevels[idx]

                Qm_result = qm(metabPopulationDensity, metabolismNow)

                ### Building flux ###
                if type(bldgProfile) is dict: # Country-specific profile(s) used
                    bldgMultiplier = pd.Series(index=attribs.index)
                    for idx in unique_attribs['admin']:
                        bldgMultiplier.loc[attribs['admin'] == idx] = bldgProfile[idx].getValueAtTime(ts_dt, 3600)[0]
                else: # Same profile used everywhere
                    bldgMultiplier = bldgProfile.getValueAtTime(ts_dt, 3600)[0]

                Qb_result = qb(self.parameters, energyUse, temperatureNow, bldgMultiplier, self.parameters.BP_temp, attribs)/areas # Wm-2

                ### Transport flux ###
                if type(trafficProfile) is dict: # Country-specific profile(s) used
                    traffMultiplier = pd.Series(index=attribs.index)
                    for idx in unique_attribs['admin']:
                        traffMultiplier.loc[attribs['admin'] == idx] = trafficProfile[idx].getValueAtTime(ts_dt, 3600)[0]
                else: # Same profile used everywhere
                    traffMultiplier = trafficProfile.getValueAtTime(ts_dt, 3600)[0]

                # Apply reductions to vehicle count on public holidays and weekends
                reductionFactor = 1
                if holiday:  # Holidays apply to everywhere in study area
                    reductionFactor = self.parameters.QV_multfactor
                else:       # Check if country-specific weekend is occurring
                    # If not public holiday, see if it's the weekend anywhere and apply reduction here
                    # Weekend behaviour starts in local time so can be mid-way through a UTC day.
                    # Check if it's the weekend for a time step one second before the end of the time step. Avoids midnight confusing things.
                    weekendLocations = vehicleCountData[regPar.isWeekend(vehicleCountData.index, ts_dt+tzOffset-timedelta(seconds=1))].index
                    reductionFactor = pd.Series(index=vehicleCountData.index, data=1)
                    if len(weekendLocations) > 0:
                        reductionFactor.loc[weekendLocations] = self.parameters.QV_multfactor

                vc = (vehicleCountData.transpose() * reductionFactor).transpose() # Apply multiplication, which may be location-specific
                Qt_result = qt(self.parameters.avg_speed, vc, areas, self.parameters.emission_factors, traffMultiplier)

                ### Overall QF ###
                Qf_result = Qm_result + Qb_result + Qt_result
                # Output a file for each time step
                combined = pd.concat([Qf_result, Qm_result, Qb_result, Qt_result], axis=1)
                # Re-insert in any original output areas that were omitted because there was no population data
                combined.columns = ['Qf', 'Qm', 'Qb', 'Qt']
                outFile = os.path.join(self.modelOutputPath, diurnal_times[t].strftime(self.dateStructure))
                combined.to_csv(outFile, float_format='%.3f') # Produce all outputs to 3 decimal places

        # Generate NetCDF files for SUEWS input if user has requested this
        if self.config['makeNetCDF']:
            self.makeSUEWSnetcdfFiles(national_attribs_used, attrib_indexes, dates, temperatures)

        # Dump logs
        #regPar.logger.writeFile(os.path.join(self.logPath, 'popLog.txt'))
        #metabProfile.logger.writeFile(os.path.join(self.logPath, 'metabProfileLog.txt'))
        #bldgProfile.logger.writeFile(os.path.join(self.logPath, 'bldgProfileLog.txt'))
        dailyT.logger.writeFile(os.path.join(self.logPath, 'DailyTempLog.txt'))
        regPar.logger.writeFile(os.path.join(self.logPath, 'NationalParameters.txt'))

    def makeSUEWSnetcdfFiles(self, national_attribs_used, attrib_indexes, dates, temperatures):
        '''
        Generate NetCDF3 classic files that summarise the results of the LQF run for use in SUEWS
        Includes enough data for SUEWS to recalculate heating/cooling effects
        :param modelOutputPath: Model output path - where the .csv files are. These are converted.
        :param national_attribs_used: List of each unique combination of attributes (including heating & cooling coefficients) used
        :param attrib_indexes: pd.Series of output area IDs and the index of national attribute set used
        :param dates: Dates covered by the model run. May not be contiguous
        :param temperatures: List or series of daily temperatures (same T assumed for whole study area)
        '''

        self.loadModelResults(self.modelRoot)
        startTime = dates[0]

        if 'extra_disagg' in self.processedDataList.keys():
            gridIdFieldName = self.processedDataList['extra_disagg']['output_areas']['featureIds']
            outLayer = loadShapeFile(self.processedDataList['extra_disagg']['output_areas']['file'], self.processedDataList['extra_disagg']['output_areas']['EPSG'])
        else:
            gridIdFieldName = self.ds.outputAreas_spat['featureIds']
            outLayer = loadShapeFile(self.ds.outputAreas_spat['shapefile'], self.ds.outputAreas_spat['epsgCode'])

        # Is it a grid?
        gridIds, is_grid, mappings, outputAreas, output_x, output_y = self.isRegularGrid(gridIdFieldName, outLayer)

        # Produce hourly outputs split across multiple netCDF files
        expectedSize = outputAreas * len(self.fileList) * 4 * 3 # Output size in bytes

        #maxSize = 2000000000 * 0.95 # 0.95 gives a bit of space
        maxSize = 500000000 # bytes
        numFilesNeeded = int(expectedSize) / int(maxSize) + 1 if expectedSize%maxSize != 0 else 0
        timesPerFile = len(self.fileList) / numFilesNeeded
        metaFile = os.path.join(self.modelOutputPath, 'LQF_META.nc')  # NetCDF file containing metadata

        for i in range(numFilesNeeded):
            firstPoint = i * timesPerFile # First entry of this file
            finalPoint = (i+1) * timesPerFile - 1 # Final entry of this file
            if i == numFilesNeeded-1:
                # Make sure the correct number of entries is used
                finalPoint = len(self.fileList) - 1
            numPoints = finalPoint - firstPoint
            timesToUse = list(self.fileList.index)[firstPoint:(1+finalPoint)]
            outFile = os.path.join(self.modelOutputPath, 'LQF_SUEWS_' + str(i) + '.nc')
            dataset = nc4.Dataset(outFile, 'w', format='NETCDF3_CLASSIC')
            dataset.createDimension('time', numPoints+1)
            # Time variable
            times = dataset.createVariable('time', np.int32, ('time',))
            times.units = 'hours since ' + startTime.strftime('%Y-%m-%d %H:%M:%S')
            times.calendar = 'gregorian'
            def toHoursSinceStart(x): return (int(x.strftime('%j'))-1)*24 + x.hour
            times[:] = np.array(map(toHoursSinceStart, timesToUse))

            if is_grid:
                dataset.createDimension('south_north', len(output_y))
                northing = dataset.createVariable('south_north', np.float32, ('south_north',))
                dataset.createDimension('west_east', len(output_x))
                easting = dataset.createVariable('west_east', np.float32, ('west_east',))

                easting.units = 'metres_east'
                easting[:] = output_x
                northing.units = 'metres_north'
                northing[:] = output_y

                total_qf = dataset.createVariable('total_qf', 'f4', ('time', 'south_north', 'west_east'), least_significant_digit=3)
                building_qf = dataset.createVariable('building_qf', 'f4', ('time', 'south_north', 'west_east'), least_significant_digit=3)

                # Sort the grid IDs into an order that allows data to be transformed quickly from series to grid
                # [y_pos, x_pos]
                correctIdOrder = map(intOrString, list(pd.DataFrame(mappings).transpose().sort([1,0]).index))
                # Set up data arrays
                for t in range(len(timesToUse)):
                    # Read output file and add it to netCDF. Re-order each on the fly and reshape to matrix
                    qfData = pd.DataFrame.from_csv(self.fileList[timesToUse[t]])
                    total_qf[t, :, :] = np.array(qfData['Qf'].loc[correctIdOrder]).reshape([len(output_x), len(output_y)])
                    building_qf[t, :, :] = np.array(qfData['Qb'].loc[correctIdOrder]).reshape([len(output_x), len(output_y)])
                    qfData = None
            else:
                # Index everything by grid ID in 1 dimension
                dataset.createDimension('grid_id', outputAreas)
                grid_id = dataset.createVariable('grid_id', np.int16, ('grid_id'))
                grid_id[:] = np.array(gridIds)
                total_qf = dataset.createVariable('total_qf', 'f4', ('time','grid_id'), least_significant_digit=3)
                building_qf = dataset.createVariable('building_qf', 'f4',  ('time','grid_id'), least_significant_digit=3)
                for t in range(len(timesToUse)):
                    # Read output file and add it to netCDF. Re-order each on the fly and reshape to matrix
                    qfData = pd.DataFrame.from_csv(self.fileList[timesToUse[t]])
                    total_qf[t,:] = np.array(qfData['Qf'])
                    building_qf[t, :] = np.array(qfData['Qb'])
                    qfData = None

            dataset.close()

        # Create grid cell metadata netcdf file: the relation between grid position and heating/cooling parameter(s) to use
        dataset = nc4.Dataset(metaFile, 'w', format='NETCDF3_CLASSIC')
        dataset.createDimension('time', len(temperatures))
        # Time variable
        times = dataset.createVariable('time', np.int16, ('time',))
        times.units = 'days since ' + dates[0].strftime('%Y-%m-%d %H:%M:%S')
        times.calendar = 'gregorian'
        times[:] = range(len(temperatures))
        temps = dataset.createVariable('temperature', np.float32, ('time',))
        temps[:] = list(temperatures)

        # Add coefficients for building energy calculation
        dataset.createDimension('regional_id', len(national_attribs_used))
        regionId = dataset.createVariable('regional_id', np.int16, ('regional_id',))
        regionId.units = 'N/A'
        regionId[:] = range(len(national_attribs_used))
        increasePerCDD = dataset.createVariable('increasePerCDD', np.float32, ('regional_id',))
        increasePerCDD[:] = [x['increasePerCDD'] for x in national_attribs_used]
        increasePerHDD = dataset.createVariable('increasePerHDD', np.float32, ('regional_id',))
        increasePerHDD[:] = [x['increasePerHDD'] for x in national_attribs_used]
        summerCooling =  dataset.createVariable('summer_cooling', np.int16, ('regional_id',))
        summerCooling[:] = [x['summer_cooling'] for x in national_attribs_used]

        if is_grid:
            dataset.createDimension('south_north', len(output_y))
            northing = dataset.createVariable('south_north', np.float32, ('south_north',))
            dataset.createDimension('west_east', len(output_x))
            easting = dataset.createVariable('west_east', np.float32, ('west_east',))
            easting.units = 'metres_east'
            easting[:] = output_x
            northing.units = 'metres_north'
            northing[:] = output_y
            grid_id = dataset.createVariable('grid_id', np.int16, ('south_north', 'west_east'))
            grid_id[:,:] = np.array(correctIdOrder).reshape([len(output_x), len(output_y)])
            attrib_id = dataset.createVariable('attrib_id', np.int16, ('south_north', 'west_east',))
            attrib_id[:,:] =  np.array(attrib_indexes[correctIdOrder]).reshape([len(output_x), len(output_y)])
        else:
            dataset.createDimension('grid_id', outputAreas)
            grid_id = dataset.createVariable('grid_id', np.int16, ('grid_id'))
            grid_id[:] = np.array(gridIds)
            attrib_id = dataset.createVariable('attrib_id', np.int16, ('grid_id',))
            attrib_id[:] =  np.array(attrib_indexes[gridIds])
        dataset.close()

    def isRegularGrid(self, gridIdFieldName, outLayer):
        '''
        Determine whether the given shapefile outLayer is a regular grid or not, and determine the grid parameters if so
        :param gridIdFieldName:
        :param outLayer:
        :return:
        '''
        # Determine whether it's a regular grid
        # Make list of lower y and x coordinates of each box
        ymins = []
        xmins = []
        gridIds = []
        numFeatures = 0
        for f in outLayer.getFeatures():
            numFeatures += 1
            bbox = f.geometry().boundingBox()
            ymins.append(bbox.yMinimum())
            xmins.append(bbox.xMinimum())
            gridIds.append(f[gridIdFieldName])

        # It's a grid if the heights and widths vary by less than 1 percent
        ymins = np.array(ymins)
        xmins = np.array(xmins)
        unique_y = np.unique(ymins)
        unique_x = np.unique(xmins)
        x_spacings = np.diff(unique_x)
        y_spacings = np.diff(unique_y)
        mean_x_spacing = x_spacings.mean()
        mean_y_spacing = y_spacings.mean()
        if (y_spacings.std() / mean_y_spacing < 0.01) and (x_spacings.std() / mean_x_spacing < 0.01):

            # Create mappings between grid id and position in the actual grid
            tolerance = 0.01  # How much are the grid centres allowed to wobble from their expected values?
            tol_x = mean_x_spacing * tolerance  # Tolerance
            tol_y = mean_y_spacing * tolerance

            # Round the coordinates of each cell to a precision that can contain the tolerance.
            # This is mostly to ensure floating point errors don't creep in
            if tol_x < 1:
                x_dps = int(-1 * np.log10(tol_x) + 1)  # Add one to be sure
                y_dps = int(-1 * np.log10(tol_y) + 1)  # Add one to be sure
            else:
                # Just round everything to the nearest integer
                x_dps = 0
                y_dps = 0

                # Set up the grid co-ordinates
            output_x = np.round(unique_x[0] + x_spacings[0] * (np.arange(len(unique_x)) + 0.5), x_dps)
            output_y = np.round(unique_y[0]+ y_spacings[0] * (np.arange(len(unique_y)) + 0.5), y_dps)
            # Round the coordinates of the actual features to be comparable
            xmins = np.round(xmins + x_spacings[0] * 0.5, x_dps)
            ymins = np.round(ymins + y_spacings[0] * 0.5, y_dps)
            mappings = {}
            outputAreas = len(output_x) * len(output_y)
            for i in range(0, len(gridIds)):
                mappings[gridIds[i]] = [np.where(output_x == np.round(xmins[i], x_dps))[0][0], np.where(output_y == np.round(ymins[i], y_dps))[0][0]]
            is_grid = True

        else:
            is_grid = False
            mappings = None
            output_x = None
            output_y = None
            outputAreas = numFeatures

        return gridIds, is_grid, mappings, outputAreas, output_x, output_y

    def loadModelResults(self, path):
        '''
        Load a previous set of model results so the outputs/configuration can be revisited
        :param path: Path of model output folder (this contains the processed input data and parameters files needed)
        :return: Dict of model run parameters e.g. config file location (for user information)
        '''
        # Check model outputs are intact, and set if so
        if not os.path.exists(path):
            raise Exception('Model output directory ' + str(path) + ' not found')

        for sub in self.subFolders.values():
            directory = os.path.join(path, sub)
            if not os.path.exists(directory):
                raise Exception('Chosen model output folder ' + str(path) + ' did not contain enough subfolders to be genuine')

        # If directory structure checks out, try populating the object
        self.setOutputDir(path)
        self.setPreProcessedInputFolder(os.path.join(path, self.subFolders['disagg']))
        self.setDataSources(os.path.join(self.configPath, 'DataSources.nml'))
        self.setParameters(os.path.join(self.configPath, 'Parameters.nml'))
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

        # Extract the location names from the first file in the list
        # This assumes all files in the folder are for identical output areas
        firstFile = pd.read_csv(self.fileList[0], header=0, index_col=0)
        self.outputAreas = list(firstFile.index)
        self.resultsAvailable = True

        return {'outputPath':self.modelOutputPath,
                'processedInputData':self.processedInputData,
                'logPath':self.logPath,
                'paramsFile':os.path.join(self.configPath, 'Parameters.nml'),
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
        combined = pd.DataFrame(index=indices, columns=['Qf', 'Qb', 'Qt', 'Qm'])
        for i in indices:
            outs = pd.read_csv(self.fileList[i], header=0, index_col=0)
            combined['Qf'].loc[i] = outs['Qf'].loc[id]
            combined['Qb'].loc[i] = outs['Qb'].loc[id]
            combined['Qt'].loc[i] = outs['Qt'].loc[id]
            combined['Qm'].loc[i] = outs['Qm'].loc[id]

        return combined

    def getOutputLayerInfo(self):
        '''
        Return the location and metadata of the output layer
        :return:
        '''
        # Just use one of the disaggregated layers, since these are using same feature mappings
        if 'extra_disagg' in self.processedDataList.keys():
            return self.processedDataList['extra_disagg']['output_areas']
        else:
            return self.processedDataList['resPop'][0]

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