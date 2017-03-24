from datetime import datetime

from PyQt4.QtCore import QSettings
from qgis.core import QgsDataSourceURI, QgsMapLayerRegistry, QgsMessageLog
from DataManagement.SpatialAttributesSampler import SpatialAttributesSampler
from DataManagement.spatialHelpers import *
from DataManagement.LookupLogger import LookupLogger
import sqlite3 as lite
from calendar import isleap
def addQuotes(x): return "'" + x + "'"

class RegionalParameters:
    # Translate spatially and temporally resolved country-specific parameters to model output polygons. Samples values
    # rather than downscaling them.
    # Parameters: Times of waking, sleeping and duration over which sleep/wake transition occurs; economic status rating; summer cooling
    # Provides a value for every output feature.
    # Parameters MUST have a set attribute names: t_sleep, t_wake, transition, ecostatus, smrcooling
    def __init__(self, logger=LookupLogger()):
        self.logger = logger
        self.worldAttributes = SpatialAttributesSampler(logger)
        self.dburi = None # Database URI
        self.dbschema = None # Database schema containing table(s) of interest
        self.dbtable = None # Database table containing world features
        self.databaseLocation = None # File containing sqlite database

        self.templateShapefile = None
        self.templateEpsgCode = None
        self.outputLayer = None  # actual qgsVectorLayer representing output layer
        self.countryAssignments = None  # Pandas series containing the country assigned to each ID used in the output layer

        # Store raw values from database
        self.attrs = None
        self.wdBuildingCycles = None
        self.weBuildingCycles = None
        self.wdTransportCycles = None
        self.weTransportCycles = None
        self.weekendDays = None
        self.fixedHolidays = None
        # Placeholders for populations. Note population is used to disaggregate national totals, which are per person.
        self.resPops = None # Residential populaton in buildings
        self.vehPop = None  # Effective population in vehicle emitting areas
        self.metabPop = None # Residential population in metabolism-friendly areas

        # set new QGIS project layers (created herein) to inherit the project EPSG code (initially) to avoid annoying popups
        s = QSettings()
        s.setValue("/Projections/defaultBehaviour", "useProject")

   # SETTERS
    def setWorldDatabase(self, database):
        '''Sets the world database
        :param database: Local database file (hard coded properties are used in this function)
        :return: Nothing (stores self.attributedOutputLayer, which contains assignments)
        '''

        if not os.path.exists(database):
            raise ValueError('LQF Database file ' + database + ' not found')
        self.databaseLocation = database
        self.dburi = QgsDataSourceURI()
        self.dburi.setDatabase(database)
        self.dbschema = ''
        self.dbtable = 'World'

    def setOutputShapefile(self, filename, epsgCode, id_field=None):
        '''
        Sets output areas for object and assigns country ID to each of them (takes a long time if many features)
        :param filename:  Shapefile filename
        :param epsgCode: EPSG code (int)
        :param id_field: Name of field/attribute containing unique feature IDs
        :return: Filename of shapefile with country assignments added
        '''
        self.worldAttributes.setOutputShapefile(filename, epsgCode, id_field)

        if self.dburi is None:
            raise ValueError('setWorldDatabase() must be called first')

        # Get output area's overall bounding box
        self.worldAttributes.outputLayer.selectAll()
        bbox = self.worldAttributes.outputLayer.boundingBoxOfSelected()
        # Get a layer that includes just the countries intersecting and containing the bbox of the output areas

        # Return the geometries of matching countries, converted to the same CRS as the output
        sql = "(select admin, geom, ST_Transform( geom , " + str(self.worldAttributes.templateEpsgCode) + " ) as transformed_geom FROM " + self.dbtable + ")"
        geom_column = 'transformed_geom'

        # The following statement converts the bbox of our output area to EPSG 4326, and finds countries that intersect this
        polygonText = "ST_Intersects(ST_Transform(SetSRID(GeomFromText('%s'), %s), 4326), geom)"% (bbox.asWktPolygon(), str(self.worldAttributes.templateEpsgCode))

        # E.g the following query selects greece
        #SELECT name FROM World WHERE ST_Intersects(ST_Transform(SetSrid(GeomFromText("POLYGON((309045.14839637035038322 3892853.22750130295753479, 345275.02064901700941846 3892853.22750130295753479, 345275.02064901700941846 3926290.0938413473777473, 309045.14839637035038322 3926290.0938413473777473, 309045.14839637035038322 3892853.22750130295753479))"), 32635), 4326), geom)
        self.dburi.setDataSource(self.dbschema, sql, geom_column, polygonText)
        vlayer = QgsVectorLayer(self.dburi.uri(), "Matched countries", 'spatialite')
        # Build list of country names
        vlayer.selectAll()
        countries = []
        for f in vlayer.getFeatures():
            countries.append(f['admin'])

        # Connect to SpatiaLite database
        con = None
        con = lite.connect(self.databaseLocation)
        self.extractPropertiesForCountries(con, countries)
        # Create a list of DOYs for each country and put into dataframe

        # Assign country name to output areas
        # Take a temporary local copy of the world map to prevent going back to the database every time a feature is looke dup
        fobj,tempLayerFile = tempfile.mkstemp('.shp')
        os.close(fobj)
        saveLayerToFile(vlayer, tempLayerFile, vlayer.crs())

        tl = loadShapeFile(tempLayerFile, 4326)
        self.attributedOutputLayer = self.worldAttributes.resampleLayer(tl, ['admin'], inputIdField='admin')
        tl = None
        vlayer = None
        try:
            os.remove(tempLayerFile)         # Delete temporary file
        except:
            pass

        # Assign this population as vehicle, residential and metabolisng population data frames
        # This can be overriden later to inject specific distributions for the population types
        df = shapefile_attributes(self.attributedOutputLayer)
        df.index = map(intOrString, df[self.worldAttributes.templateIdField])
        self.countryAssignments = df

        return self.attributedOutputLayer # This should be saved so it can be used with self.injectSampledLayer to save time later

    def injectMetabPopLayer(self, filename, epsgCode):
        '''
        Inject a population shapefile that shows the distribution of the metabolising population.
        The features must be identical to those in the output layer
        :param filename: Shapefile path
        :param epsgCode: EPSG of shapefile
        :return: Nothing. Assigns object properties
        '''
        lyr = openShapeFileInMemory(filename, epsgCode, 'temp layer')
        ser = shapefile_attributes(lyr)
        ser.index = map(intOrString, ser[self.worldAttributes.templateIdField])
        self.metabPop = ser['Pop']
        lyr = None

    def injectVehPopLayer(self, filename, epsgCode):
        '''
        Inject a population shapefile that shows the distribution of the vehicle population.
        The features must be identical to those in the output layer
        :param filename: Shapefile path
        :param epsgCode: EPSG of shapefile
        :return: Nothing. Assigns object properties
        '''
        lyr = openShapeFileInMemory(filename, epsgCode, 'temp layer')
        ser = shapefile_attributes(lyr)
        ser.index = map(intOrString, ser[self.worldAttributes.templateIdField])
        self.vehPop = ser['Pop']
        lyr = None

    def injectResPopLayer(self, filename, epsgCode):
        '''
        Inject a population shapefile that shows the distribution of the residential population.
        The features must be identical to those in the output layer
        :param filename: Shapefile path
        :param epsgCode: EPSG of shapefile
        :return: Nothing. Assigns object properties
        '''
        lyr = openShapeFileInMemory(filename, epsgCode, 'temp layer')
        ser = shapefile_attributes(lyr)
        ser.index = map(intOrString, ser[self.worldAttributes.templateIdField])
        self.resPops = ser['Pop']
        lyr = None

    def injectAttributedOutputLayer(self, filename, epsgCode, id_field=None):
        '''
        Sets output areas for object and assigns country ID to each of them (takes a long time if many features)
        :param database: Local database file (hard coded properties are used in this function)
        :return: Nothing (stores self.attributedOutputLayer, which contains assignments)
        '''
        self.worldAttributes.setOutputShapefile(filename, epsgCode, id_field)
        self.attributedOutputLayer = openShapeFileInMemory(filename, epsgCode, 'attributed output areas')
        if self.dburi is None:
            raise ValueError('setWorldDatabase() must be called first')

        # Unlike setOutputShapefile(), this already has the required country ID in the 'admin' field
        # so no need to do spatial indexing
        df = shapefile_attributes(self.attributedOutputLayer)
        if 'admin' not in df.columns:
            raise ValueError('A valid attributed output layer must have the field "admin" in it.')

        countries = df['admin'].dropna().unique()

        df = None
        # Connect to SpatiaLite database and populate object with country-specific attributes and holidays
        con = None
        con = lite.connect(self.databaseLocation)
        self.extractPropertiesForCountries(con, countries)
        ca = shapefile_attributes(self.attributedOutputLayer)
        ca.index = map(intOrString, ca[self.worldAttributes.templateIdField])
        self.countryAssignments = ca

    def extractPropertiesForCountries(self, con, countries):
        '''
        Pull all country-specific data from database and put into pandas dataframe with appropriate indexing.
        :param con: Database connection object (SQLIte)
        :param countries: list of countries for which to get data
        :return: Nothing. Populates object fields instead.
        '''
        # All years are taken here, and accounted for upon this objected being queried
        attrs = "SELECT * FROM attributes WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        self.attrs = pd.read_sql(attrs, con, index_col=['id', 'as_of_year'])

        # Weekend and weekday building diurnal cycles for each country
        wdBuildingCycles = "SELECT * FROM weekdayBuildingCycles WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        self.wdBuildingCycles = pd.read_sql(wdBuildingCycles, con, index_col=['id'])  # Column names are 1...24
        diffs = set(countries).difference(list(self.wdBuildingCycles.index))
        if len(diffs) > 0:
            raise Exception('The LQF database contains no weekday building cycles for: ' + str(diffs))

        weBuildingCycles = "SELECT * FROM weekendBuildingCycles WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        self.weBuildingCycles = pd.read_sql(weBuildingCycles, con, index_col=['id'])  # Column names are 1...24
        diffs = set(countries).difference(list(self.weBuildingCycles.index))
        if len(diffs) > 0:
            raise Exception('The LQF database contains no weekend building cycles for: ' + str(diffs))

        # Weekend and weekday transport diurnal cycles for each country
        wdTransportCycles = "SELECT * FROM weekdayTransportCycles WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        self.wdTransportCycles = pd.read_sql(wdTransportCycles, con, index_col=['id'])  # Column names are 1...24
        diffs = set(countries).difference(list(self.wdTransportCycles.index))
        if len(diffs) > 0:
            raise Exception('The LQF database contains no weekday transport cycles for: ' + str(diffs))

        weTransportCycles = "SELECT * FROM weekendTransportCycles WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        self.weTransportCycles = pd.read_sql(weTransportCycles, con, index_col=['id'])  # Column names are 1...24
        diffs = set(countries).difference(list(self.weTransportCycles.index))
        if len(diffs) > 0:
            raise Exception('The LQF database contains no weekend transport cycles for: ' + str(diffs))

        weekendDays = "SELECT * FROM weekendDays WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        self.weekendDays = pd.read_sql(weekendDays, con, index_col=['id'])  # Column names are Mon, Tue...
        diffs = set(countries).difference(list(self.weekendDays.index))
        if len(diffs) > 0:
            raise Exception('The LQF database contains no list of weekday/weekend days for: ' + str(diffs))

        # Get fixed holiday day of years (assuming not leap year)
        fixedHols = "SELECT * FROM fixedholidays WHERE id IN " + "(" + ','.join(map(addQuotes, countries)) + ")"
        fixedHols = pd.read_sql(fixedHols, con)
        self.fixedHolidays = {c: list(fixedHols['DOY'].loc[fixedHols['id'] == c]) for c in countries}

    ## GETTERS
    def getNationalAttributes(self, year):
        '''
        Retrieve national data for the specified year for the country(ies) intersected by the output layer.
        When the requested year is not available, the most recent match is used.
        If there is no most recent match, an exception is thrown
        :param year: Int: Year represented by data.
        :return: Dict of attributes: {country: {attrib: val}}.
        '''

        if type(year) is not int:
            raise ValueError('Year must be an integer year between 1000 and 3000')

        if (year < 1000) or (year > 3000):
            raise ValueError('Year must be an integer year between 1000 and 3000')

        # Retrieve national data for country and year
        countries = self.weTransportCycles.index.unique() # Purely for the primary key

        # Get most up-to-date data for this country in this period
        cols = ['population', 'kwh_year', 'wakeTime', 'sleepTime',  'transition',  'summer_cooling', 'ecostatus','cars', 'motorcycles', 'freight']
        arr = pd.DataFrame(index = countries, columns = cols)
        for c in countries:
            # Get scalars first
            arr[:].loc[c] = pd.Series({'population' : self.attrs['population'][c].dropna().asof(year),
                            'kwh_year' : self.attrs['kwh_year'][c].dropna().asof(year),
                            'wakeTime' : self.attrs['wake_hour'][c].dropna().asof(year),
                            'sleepTime' : self.attrs['sleep_hour'][c].dropna().asof(year),
                            'transition' : self.attrs['transition_time'][c].dropna().asof(year),
                            'summer_cooling' : self.attrs['summer_cooling'][c].dropna().asof(year),
                            'ecostatus' : self.attrs['ecostatus'][c].dropna().asof(year),
                            'cars' : self.attrs['cars'][c].dropna().asof(year),
                            'motorcycles' : self.attrs['motorcycles'][c].dropna().asof(year),
                            'freight' : self.attrs['freight'][c].dropna().asof(year)})

            if not pd.Series(arr[:].loc[c]).notnull().all():
                raise Exception('Cannot model ' + c + ' in year ' + str(year) + ' because there is not enough nation-level information up to this period')

        return arr

    def isWeekend(self, featureIds, date):
        '''
        Given a particular date and country, gives True or False to answer "Is it the weekend?"
        :param featureIds: list or pd.index of feature IDs
        :param date: datetime (UTC)
        :return: True (it's the weekend) or False (it's a weekday)
        '''
        # Get list of 1 or 0 with no index.
        days = self.countryAssignments.loc[featureIds].join(self.weekendDays[['Mon', 'Tue', 'Wed', 'Thu', 'Fri','Sat', 'Sun']], on='admin')[['Mon', 'Tue', 'Wed', 'Thu', 'Fri','Sat', 'Sun']]
        days.columns = range(0,7)
        return days[date.weekday()] > 0

    def getWeekendDaysByRegion(self):
        '''
        :return:  dict of {country: [int, int]} that shows which days of the week (0-6 = Monday-Sunday) are weekend days
        '''
        tempDays = self.weekendDays[['Mon', 'Tue', 'Wed', 'Thu', 'Fri','Sat', 'Sun']]
        tempDays.columns = range(7)
        return {idx: tempDays.columns[tempDays.loc[idx] > 0] for idx in tempDays.index}

    # def getCyclesForFeatureIDs(self, featureIds, weekend):
    #     '''
    #     Get the 24-hour diurnal cycle of energy use for the specified feature IDs
    #     :param featureIds: list or pd.index of feature IDs
    #     :param weekend: pd.Series of true or false describing if it is the weekend (true) or weekday (false) at each feature ID
    #     :return: pd.dataframe with 25 columns: Country name and hour of day. Each represents the preceding hour
    #     '''
    #
    #     # Get all weekday cycles
    #     vals = self.countryAssignments.loc[featureIds].join(self.weekendCycles, on='admin')
    #     # Overwrite with weekend versions if needed#
    #
    #     weekendIndices = weekend.index[weekend]
    #     vals[:].loc[weekendIndices] = self.countryAssignments.loc[weekendIndices].join(self.weekendCycles, on='admin')
    #     return vals

    def getTransportCycles(self, weekend):
        '''
        Get all transport diurnal cycles for the countries overlapped by the features in the output layer
        :param weekend: Return weekend cycle (True) or weekday (False)
        :return: pd.DataFrame with 24 columns (1 for each hour) indexed by country name
        '''
        if weekend:
            return self.weTransportCycles
        else:
            return self.wdTransportCycles

    def getBuildingCycles(self, weekend):
        '''
        Get all building diurnal cycles for the countries overlapped by the features in the output layer
        :param weekend: Return weekend cycle (True) or weekday (False)
        :return: pd.DataFrame with 24 columns (1 for each hour) indexed by country name
        '''
        if weekend:
            return self.weBuildingCycles
        else:
            return self.wdBuildingCycles

    def getOutputLayer(self):
        # Gets the output layer
        if self.worldAttributes.outputLayer is not None:
            return self.worldAttributes.outputLayer
        else:
            raise Exception('The output layer has not yet been set!')

    def getAttribsTable(self, featureId, requestYear):
        '''
        Get pandas data frame of attributes for each output feature on requested date
        :param featureId: Pandas series of feature Id(s) for which to return attributes (non-matching ones get NA)
        :param requestYear: DateTime object containing requested date
        :return: pandas data frame indexed by chosen unique identifier of each output area
        '''
        if type(featureId) is pd.Index:
            featureId = featureId.tolist()

        # Country assignments
        # This can be overriden later to inject specific distributions for the population types
        countryAssignments = shapefile_attributes(self.attributedOutputLayer)
        countryAssignments.index = map(intOrString, countryAssignments[self.worldAttributes.templateIdField])

        # Get national attributes for each country
        attrs = self.getNationalAttributes(requestYear)
        # Combine the populations
        allPops = pd.concat([countryAssignments['admin'], self.resPops, self.vehPop, self.metabPop], axis=1)
        allPops.columns = ['admin','resPop', 'vehPop', 'metabPop']
        # Join list of names to national attributes
        attrs = allPops[:].loc[featureId].join(attrs, on='admin')
        return attrs

    def getEnergyUse(self, featureId, requestYear):
        '''
        Return kwh per year used in each output area
        :param featureId:
        :param requestYear:
        :return:
        '''
        # Get national energy consumption associated to each output area
        # Multiply it by fraction of population in this output area
        data = self.getAttribsTable(featureId, requestYear)
        return data['kwh_year'] * data['resPop']/data['population'] # Disaggregate energy use by building borne population

    def getVehCount(self, featureId, requestYear):
        '''
        Return vehicle counts per year used in each output area
        :param featureId:
        :param requestYear:
        :return:
        '''
        data = self.getAttribsTable(featureId, requestYear)
        # Vehicle counts in DB are vehicles per 1,000 people, so this is calculated per populated area by counting the local pop in 1000s
        return (data[['cars', 'motorcycles', 'freight']].transpose() *  data['vehPop']/1000).transpose() # Disaggregate by vehicle "population"

    def getMetabPop(self, featureId, requestYear):
        '''
        Return population spread across "metabolism friendly" areas e.g. parks and streets as well as buildings
        :param featureId:
        :param requestYear:
        :return:
        '''
        data = self.getAttribsTable(featureId, requestYear)
        # Vehicle counts in DB are vehicles per 1,000 people, so this is calculated per populated area by counting the local pop in 1000s
        return data['metabPop']   # It's just the number of people in each feature ID

    def getFixedHolidays(self, startDate, endDate):
        '''
        Returns a list of fixed public holidays between the specified datetime objects
        :param startDate: datetime: First day to include in range
        :param endDate: datetime: Final day to include in range
        :return: dict: {countryName: [holidays]}: each entry in dict is list of datetime.date objects containing the holidays.
        '''
        if endDate < startDate:
            raise ValueError('End date is earlier than start date')

        def doyToLeapDatetime(x, year):
            return datetime.strptime(str(year)+str(x+1 if (x > 59) and isleap(year) else x), '%Y%j').date()
        output = {}
        for c in self.fixedHolidays.keys():
            output[c] = []
            for y in range(startDate.year, endDate.year+1):
                null = [output[c].append(doyToLeapDatetime(d, y)) for d in self.fixedHolidays[c]]

        return output

    def getDominantCountry(self):
        ''' Returns the dominant country: the one that intersects the largest number of output features. '''

        return self.countryAssignments['admin'].dropna().value_counts().sort_values(ascending=False).index[0]