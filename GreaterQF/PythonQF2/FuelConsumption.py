try:
    import pandas as pd
except:
    pass
import os
from string import lower
class FuelConsumption():
    def __init__(self, filename):
        ''' Class to read in fuel consumption file with prescribed format in g/km,
         and do lookups for different dates, road types and vehicle types, returning data in kg/km
        :param filename: str: filename of fuel consumption CSV file (which must be in approved format)'''
        self.data = None # Multi-indexed data frame that will hold the data
        self.vehicleTypes = ['car', 'taxi', 'bus', 'lgv', 'artic','rigid', 'motorcycle']
        self.fuelTypes = ['diesel', 'petrol']
        self.roadTypes = ['motorway', 'rural_single', 'rural_dual', 'urban']
        self.dealWithFile(filename)

    def dealWithFile(self, filename):
        '''
        reads and validates fuel consumption file [g/km], converts to kg/km producing a series of pandas data frames for different periods if all is well
        :param filename: Path to CSV file containing consumption data
        :return: Null
        '''
        if not os.path.exists(filename):
            raise ValueError('Fuel consumption file ' + filename + ' does not exist')

        # Create multi-indexed data frame
        def todate(x): return pd.datetime.strptime(x, '%Y-%m-%d')
        try:
            self.data = pd.read_csv(filename, header=1, delimiter=',', index_col=[0,1,2], parse_dates=True)
        except Exception:
            raise ValueError('Error reading the fuel consumption file')

        # Validate the entries
        # Index level 0 is date, level 1 is fuel, level 2 is vehicle type
        roadsPresent = list(pd.unique(self.data.keys()))

        missingRoads = list(set(self.roadTypes).difference(map(lower, roadsPresent)))
        if len(missingRoads) > 0:
            raise ValueError('Not all of the required road types were found in ' + filename + '. Expected: ' + str(self.roadTypes) + ' but got ' + str(roadsPresent))

        fuelsPresent = list(pd.unique(self.data.index.levels[1]))
        missingFuels = list(set(self.fuelTypes).difference(map(lower, fuelsPresent)))
        if len(missingFuels) > 0:
            raise ValueError('Not all of the required fuel types were found in ' + filename + '. Expected: ' + str(self.fuelTypes) + ' but got ' + str(fuelsPresent))

        vehiclesPresent = list(pd.unique(self.data.index.levels[2]))
        missingVehicles = list(set(self.vehicleTypes).difference(map(lower, vehiclesPresent)))
        if len(missingVehicles) > 0:
            raise ValueError('Not all of the required vehicle types were found in ' + filename + '. Expected: ' + str(self.vehicleTypes) + ' but got ' + str(missingVehicles))

        # Map lexical matches to expected indices to avoid case sensitivites
        self.roadMatch = {expected: roadsPresent[map(lower, roadsPresent).index(expected)] for expected in self.roadTypes}
        self.fuelMatch = {expected: fuelsPresent[map(lower, fuelsPresent).index(expected)] for expected in self.fuelTypes}
        self.vehicleMatch = {expected: vehiclesPresent[map(lower, vehiclesPresent).index(expected)] for expected in self.vehicleTypes}

    def getFuelConsumption(self, date, vehicle, road, fuel):
        '''
        Retrieve fuel consumption [kg/km] for a given date, vehicle and road type
        :param date: datetime: date for which to retrieve a value
        :param vehicle: vehicle type
        :param road: string: road type (motorway, ruradual, rural_single or urban)
        :param fuel:string: fuel type (diesel or petrol)
        :return: float or None: Fuel consumption value
        '''

        # Validate request input
        if vehicle not in self.vehicleTypes:
            raise ValueError('Invalid vehicle type selected')

        if fuel not in self.fuelTypes:
            raise ValueError('Invalid fuel selected')

        if road not in self.roadTypes:
            raise ValueError('Invalid road type selected')

        # What is earliest date in inventory? If the date provided is before the first date in the inventory, use the first date
        # in the inventory
        firstTime = self.data.index.levels[0][0]
        if date < firstTime:
            date = firstTime
        timePick = self.data.index.levels[0].asof(date)

        tidx = self.data.index.levels[0].asof(timePick)
        return self.data.loc[tidx].loc[self.fuelMatch[fuel]].loc[self.vehicleMatch[vehicle]][self.roadMatch[road]]/1000.0 # Convert to kg/km

