from builtins import str
from builtins import range
from builtins import object
from datetime import datetime as dt
from datetime import timedelta as td
import tempfile
import shutil
try:
    import pandas as pd
    import numpy as np
    import netCDF4 as nc4
    from requests.auth import HTTPBasicAuth, HTTPDigestAuth
    import requests
except:
    pass

from collections import OrderedDict
import os
class InvalidRelativeBbox(ValueError):
    pass
class InvalidTimeWindow(ValueError):
    pass

class NCWMS_Connector(object):

    def __init__(self):
        self.vars = ['Tair',
                                 'Wind',
                                 'LWdown',
                                 'PSurf',
                                 'Qair',
                                 'Rainf',
                                 'Snowf',
                                 'SWdown']

        self.start_date = dt(1979,0o1,0o1,00,00,00) # The first data point available in the dataset on the server
        self.end_date = dt(2015,12,31,21,00,00) # The final data point available in the dataset on the server
        self.time_res = 3600 * 3 # Time resolution of data in seconds
        self.request_length = 200 # Number of days of data to request at a time from server (helps manage load on server and produce a progress bar)
        self.request_params = {} # Holds a dict of request parameters
        self.results = OrderedDict() # Stores a list of downloaded netCDF files for different time subsets, with start datetime as key
        self.killed = False # Aborts execution if needed

    def kill(self):
        self.killed = True

    def check_bbox(self,lower_left_lat, lower_left_lon, upper_right_lat, upper_right_lon):
        '''
        Check WGS84 bounding box is valid
        :param lower_left_lat:
        :param lower_left_lon:
        :param upper_right_lat:
        :param upper_right_lon:
        :return: True or exception
        '''

        if lower_left_lat > upper_right_lat:
            raise InvalidRelativeBbox('Lower left latitude of bounding box cannot be greater than upper right latitude')

        if lower_left_lon > upper_right_lon:
            raise InvalidRelativeBbox('Lower left longitude of bounding box cannot be greater than upper right longitude')

        return True

    def check_times(self,start_date, end_date):
        '''
        Check requested start and end dates are valid
        :param start_date:
        :param end_date:
        :return:
        '''
        if type(start_date) is not dt:
            raise TypeError('Start time is of type %s, but must be datetime.datetime' % (type(start_date),))
        if type(end_date) is not dt:
            raise TypeError('End time is of type %s, but must be datetime.datetime' % (type(start_date),))

        if start_date > end_date:
            raise InvalidTimeWindow('Requested end date (%s) must be greater than or equal to start date (%s)' % (end_date.strftime('%Y-%m-%d %H:%M:%S'), start_date.strftime('%Y-%m-%d %H:%M:%S')))

        # Check this is allowed given scope of data
        if (start_date < self.start_date) or (start_date > self.end_date):
            raise InvalidTimeWindow('Requested start date (%s) must be between %s and %s'%(end_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                                         self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                                         self.end_date.strftime('%Y-%m-%d %H:%M:%S')))

        if (end_date > self.end_date) or ( end_date < self.start_date):
            raise InvalidTimeWindow('Requested end date (%s) must be between %s and %s'%(end_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                                         self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                                         self.end_date.strftime('%Y-%m-%d %H:%M:%S')))
        return True

    def check_vars(self, var_list):
        '''
        Ensure requested variable names are valid
        :param var_list:
        :return:
        '''

        for v in var_list:
            if v not in self.vars:
                raise ValueError('Variable %s is not one of those available in data'%(v, ))

        return True

    def get_data(self, start_date, end_date, variables, lowerleft_lat, lowerleft_lon, upperright_lat, upperright_lon, update=None):
        '''
        Retrieve data from ncWMS
        :param start_date:  datetime.datetime: Earliest requested date
        :param end_date:    datetime.datetime: Latest requested date
        :param variables:   List of variables to retrieve
        :param lowerleft_lat:  Latitude (WGS84) degrees N, lower left of bounding box
        :param lowerleft_lon:   Longitude (WGS84) degrees E, lower left of bounding box
        :param upperright_lat:  Latitude (WGS84) degrees N, upper right of bounding box
        :param upperright_lon:   Longitude (WGS84) degrees E, upper right of bounding box
        :param update:  A QT progressBar object (optional)
        :return:
        '''

        # Validate input params
        self.check_bbox(lower_left_lat = lowerleft_lat, lower_left_lon = lowerleft_lon, upper_right_lat=upperright_lat, upper_right_lon=upperright_lon)
        self.check_vars(variables)
        self.check_times(start_date, end_date)

        self.request_params = {'vars':variables, 'start_date':start_date, 'end_date':end_date, 'bbox': [lowerleft_lat, lowerleft_lon, upperright_lat, upperright_lon]}
        start_dates = pd.date_range(start_date, end_date, freq='%dD'%(self.request_length,)).to_datetime()

        # Create queue of retrievals, and safeguard against over-running dataset end date
        for s in range(0, len(start_dates)):
            if self.killed:
                break

            if s == len(start_dates)-1:
                end_date_candidate = end_date + td(seconds = 3600 * 24 -1)
                final_date = True
            else:
                end_date_candidate = start_dates[s+1]- td(seconds=self.time_res)
                final_date = False

            if end_date_candidate > self.end_date:
                final_date = True
                end_date_candidate = self.end_date

            self.results[start_dates[s]] = self.retrieve(start_dates[s], end_date_candidate) # Get data from start date to next start date minus time resolution
            if update is not None:
                update.emit({'progress':100*float(s)/float(len(start_dates)), 'message':' (%s to %s)'%(start_dates[s].strftime('%Y-%m-%d'), end_date_candidate.strftime('%Y-%m-%d'))})

            if final_date:
                break
        self.convert_to_nc3()
        update.emit({'progress':100, 'message':' Cleaning up...'})

    def convert_to_nc3(self):
        '''
        Process dict of downloaded netCDF files into a single averaged time series (also netCDF)
        :return:
        '''

        # Convert each file to netcdf4_classic so it can be used with MFDataset
        for file_date in list(self.results.keys()):
            tmp = tempfile.mktemp(suffix='.nc')
            new_data = nc4.Dataset(tmp, 'w', clobber=True,  format='NETCDF3_CLASSIC')
            extant = nc4.Dataset(self.results[file_date])

            # from https://gist.github.com/guziy/8543562
            for dname, the_dim in extant.dimensions.items():
                new_data.createDimension(dname, len(the_dim) if not the_dim.isunlimited() else None)

            # Copy variables from first file
            for v_name, varin in extant.variables.items():
                if varin.datatype == 'int64':
                    dtype = 'f' # Use a float instead of a long integer because netcdf3 classic doesn't allow
                else:
                    dtype = varin.datatype

                outVar = new_data.createVariable(v_name, dtype, varin.dimensions)
                # Copy variable attributes
                outVar.setncatts({k: varin.getncattr(k) for k in varin.ncattrs()})
                outVar[:] = varin[:]

            new_data.close()
            extant.close()
            os.remove(self.results[file_date]) # Delete original NC file
            self.results[file_date] = tmp # Update dict with newer one


    def resample_by_method(self, resampled, method):
        '''
        Use a specific method to calculate aggregate statistics on a resampled pandas dataframe
        :param resampled: output of ps.series.resample()
        :param method: String naming method to use
        :return:
        '''
        if method == 'mean':
            return resampled.mean()
        if method == 'median':
            return resampled.median()
        if method == 'sum':
            return resampled.sum()
        if method == 'min':
            return resampled.min()
        if method == 'max':
            return resampled.max()

        raise ValueError('Resampling statistic %s not recognised.'%(method,))

    def average_data(self, period, method):
        '''
        Produces a NetCDF file with temporally averaged data for all variables, preserving the spatial aspects
        :param period: Desired averaging period in seconds, or None to do no averaging
        :param method: How the mean should be found, either 'mean', 'sum', 'median', 'min' or 'max'
        :return:
        '''

        combined_data = nc4.MFDataset(list(self.results.values()), aggdim='time')
        # Create new netCDF file that'll contain averaged/combined data and delete the individual files
        # from https://gist.github.com/guziy/8543562

        # Go round the variables and average them
        tmp = tempfile.mktemp(suffix='.nc')
        new_data = nc4.Dataset(tmp, 'w', clobber=True,  format='NETCDF3_CLASSIC')
        times = combined_data.variables['time']
        time_bins = nc4.num2date(times[:], units=times.units)

        # Workaround: The server currently has a slightly wobble in time bins, which we know to be precise
        # re-do them. The first one tends to be correct, and drift sets in later.
        time_bins = pd.date_range(time_bins[0],  periods=len(time_bins), freq=str(self.time_res)+'s')
        dim = combined_data.variables[self.vars[0]][:].shape # Assume all requested variables have the same shape

        if period is None:
            new_time_bins = time_bins
        else:
            new_time_bins = self.resample_by_method(pd.Series(index=time_bins, data=0).resample('%ds'%(period,), label='right'), method).index
        new_dim = [len(new_time_bins), dim[1], dim[2]]

        # Duplicate all non-time dimensions from original file, and add new time dimension
        for dname, the_dim in combined_data.dimensions.items():
            if dname == 'time':
                t = new_data.createDimension(dname, len(new_time_bins))
            else:
                new_data.createDimension(dname, len(the_dim) if not the_dim.isunlimited() else None)

        # Copy variables from first file
        for v_name, varin in combined_data.variables.items():
            outVar = new_data.createVariable(v_name, varin.dtype, varin.dimensions)
            try:
                if v_name == 'time':
                    outVar.units = varin.units.replace('seconds', 'hours') # Replace seconds with hours (if seconds) to save data
                else:
                    outVar.units = varin.units
            except:
                pass
            try:
                outVar.setncatts({k: varin.getncattr(k) for k in varin.ncattrs()})
            except:
                pass

            # Perform time-averaging and add data to new file
            # TODO: Support user-defined choice of averaging method
            if v_name in self.vars:
                # TODO: Make this efficient
                for i in range(0, combined_data.variables[v_name][:].shape[1]):
                    for j in range(0, combined_data.variables[v_name][:].shape[2]):
                        p = pd.Series(index=time_bins, data=combined_data.variables[v_name][:,i,j])
                        if period is None:
                            rs = p
                        else:
                            rs =  self.resample_by_method(p.resample('%ds'%(period,), label='right'), method)
                        if (i == 0) and (j == 0):
                            new_array = np.zeros(new_dim)
                        new_array[:,i,j] = rs.values
                outVar[:] = new_array
            else:
                if v_name == 'time':
                    # Populate with new time bins
                    timestamps = nc4.date2num(list(new_time_bins), varin.units.replace('seconds', 'hours')) # Replace seconds with hours to save data
                    outVar[:] = timestamps
                if v_name in ['lat', 'lon']:
                    outVar[:] = combined_data.variables[v_name][:]

        new_data.close()
        combined_data.close()
        [os.remove(v) for v in list(self.results.values())] # Remove individual files as no longer needed
        return tmp # Return path to combined file

    def retrieve(self, start_period, end_period):
        '''
        Performs retrieval of NetCDF file from server in chunks defined by start_period and end_period
        :return:
        '''
        baseURL = 'http://data.urban-climate.net:8080/umep/download'
        parms = {'BBOX':'%f,%f,%f,%f'%(float(self.request_params['bbox'][1]), float(self.request_params['bbox'][0]), float(self.request_params['bbox'][3]), float(self.request_params['bbox'][2])),
                 'DATASET': 'watch',
                 'VARIABLES':','.join(self.request_params['vars']),
                 'TIME':'%s/%s'%(start_period.strftime('%Y-%m-%dT%H:%M:%S'),end_period.strftime('%Y-%m-%dT%H:%M:%S'))}

        try:
            dataOut = tempfile.mktemp('.nc')
        except Exception as e:
            os.remove(dataOut)
            raise Exception('Problem creating temporary file to store raster data: '+  str(e))
        # TODO: Work out if the response is an XML error

        resp = requests.get(baseURL, params=parms, auth=HTTPDigestAuth("umep-user", "pUEmw5BbVdzfu3dz"), stream=True)
        if resp.status_code != 200:
            raise Exception('Error connecting to server. Got HTTP response code %d'%(resp.status_code,))
        with open(dataOut, 'wb') as out:
            shutil.copyfileobj(resp.raw, out)
        del resp
        return dataOut
