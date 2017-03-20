import os
import re
from pytz import timezone
from datetime import datetime as dt
try:
    import numpy as np
    import pandas as pd
    import netCDF4 as nc4
except:
    pass

def dict_to_namelist(input_dict, outputfile):
    '''
    Convert a dict to a namelist. This is a very basic treatment and only supports nesting that's one-deep
    It also doesn't try to conform to specs - it's just what works with SUEWS
    Supports string, int, float and lists of these as values in the namelist

    :param input_dict: input dict {'group_name': {group_item: value(s)}}
    :param outputfile: string for output nml file
    :return: None
    '''
    # Always surround strings with double quotes
    def encapsulate(x): return "\"" + x + "\""

    def convert_list_item(x):
        if type(x) is str:
            return encapsulate(x)
        else:
            return str(x)

    # Will write to the file in parts to make things easier to manage


    string_build = ''
    for k in input_dict.keys():
        string_build += "&" + k + "\n"
        t = type(input_dict[k])
        val = None
        if t is list:
            # Convert list to comma separated list
            val = map(convert_list_item, input_dict[k])
            val = ",".join(val)
            string_build += '  ' + k + ' = ' + val + "\n"
        elif (t is int) or (t is float):
            # Convert to string
            val = str(input_dict[k])
            string_build += '  ' + k + ' = ' + val + "\n"
        elif (t is str) or (t is unicode):
            # Take it literally
            val = encapsulate(input_dict[k])
            string_build += '  ' + k + ' = ' + val + "\n"
        elif (t is dict):
            # Allow one-deep recursion so groups can exist
            for kk in input_dict[k].keys():
                t2 = type(input_dict[k][kk])
                if t2 is list:
                    # Convert list to comma separated list
                    val = map(convert_list_item, input_dict[k][kk])
                    val = ",".join(val)
                elif (t2 is int) or (t2 is float):
                    # Convert to string
                    val = str(input_dict[k][kk])
                elif (t2 is str) or (t2 is unicode):
                    # Take it literally
                    val = encapsulate(input_dict[k][kk])
                else:
                    pass
                if val is not None:
                    string_build += '  ' + kk + ' = ' + val + "\n"
        else:
            pass

        string_build += "/" + "\n\n"
    with open(outputfile, 'w') as a:
        a.write(string_build)

def results_to_ncdf(results_path):
    '''
    Convert set of LUCY CSV files to a single netCDF file
    TODO: Add extra parameters for temperature scaling
    :param results_path:
    :return: path to netcdf file
    '''


    # Number of time stamps for LUCY = numFiles * 24
        # Filename format information so data can be retrieved
    reg = 'LUCY[0-9]{4}[0-9]{2}[0-9]{2}_[0-9]{2}-[0-9]{2}\.csv'   # Regex
    dateStructure  = 'LUCY%Y%m%d_%H-%M.csv'                               # Time format to use when saving output files
    files = os.listdir(results_path)
    tz = timezone('UTC')
    fileList={}
    for f in files:
        a = re.search(reg, f)
        if a is not None:
            fileList[tz.localize(dt.strptime(f, dateStructure))] = os.path.join(results_path, f)

    # Extract the location names from the first file in the list
    # This assumes all files in the folder are for identical output areas


    # Create N netcdf3 classic files to contain the full output
    # each file contains total Qf and the building component
    # These must not exceed 2GB per file, and are split into different time ranges to ensure this does not occur

    fileList = pd.Series(fileList)
    firstFile = pd.read_csv(fileList[0], header=0, index_col=0)
    outputAreas = list(firstFile.index)
    outputAreas = range(0, 10000)

    # Assume each QF value is 4 bytes
    # Each file contains 3 columns: Total QF (32float), Building QF(32float), index (int) for combination of heating/cooling parameters
    #
    output_x = range(300) # West-east coordinates
    output_y = range(300) # south-north coordinates

    expectedSize = len(outputAreas) * len(fileList) * 4 * 3
    maxSize = 2000000000 * 0.95 # 0.95 gives a bit of space
    numFilesNeeded = int(expectedSize) / int(maxSize) + 1 if expectedSize%maxSize != 0 else 0
    timesPerFile = len(fileList) / numFilesNeeded
    for i in range(numFilesNeeded):
        firstPoint = i * timesPerFile # First entry of this file
        finalPoint = (i+1) * timesPerFile - 1 # Final entry of this file
        if i == numFilesNeeded-1:
            # Make sure the correct number of entries is used
            finalPoint = len(fileList) - 1
        numPoints = finalPoint - firstPoint
        dataset = nc4.Dataset('c:/testoutput/test_ncdf3.nc', 'w', format='NETCDF3_CLASSIC')
        dataset.createDimension('time', numPoints) # Unlimited
        dataset.createDimension('west_east', len(output_x))
        dataset.createDimension('south_north', len(output_y))

        # Total QF on each day as a yuge matrix
        total_qf = dataset.createVariable('total_qf', 'f4', ('time','west_east', 'south_north'), least_significant_digit=3)
        # Populate with random numbers for now
        total_qf[:,:,:] = np.random.uniform(size=(numPoints, len(output_x), len(output_y))) # TEST VALUES
        # The building component before any artificial heating/cooling applied
        building_qf = dataset.createVariable('building_qf', 'f4', ('time','west_east', 'south_north'), least_significant_digit=3)
        building_qf[:,:,:] = (np.random.uniform(size=(numPoints, len(output_x), len(output_y))) * 100) # TEST VALUES
        # Heating/cooling classification (integer)
        heat_cool_id = dataset.createVariable('heat_cool_id', 'u1', ('west_east', 'south_north'))
        (np.random.uniform(size=(30,))*100).astype('int')
        heat_cool_id[:,:] =  (np.random.uniform(size=(len(output_x), len(output_y))) * 100).astype('int') # TEST VALUES
        # Heating degree days in the city (positive = HDD, negative = CDD)
        deg_days = dataset.createVariable('deg_days', 'u1', ('time'))
        deg_days[:] =  np.random.uniform(size=(numPoints,))*100  # TEST VALUES
        dataset.close()

def testIt():
    d = {'a': {'first': [1,2,3], 'second':'howdy'}, 'b':{'entry':['a', 'b', 'c']}}
    dict_to_namelist(d, 'c:/testoutput/testit.nml')

if __name__ == "__main__":
    results_to_ncdf('C:/TestOutput/baselbigenergy/ModelOutput')

    #d = {'temperature': [10.9, 11.7, 11.6, 13.1, 11.8, 7.5], 'traffic_cycles_0': {'dates': ['2015-01-01', '2015-01-03', '2015-01-04', '2015-01-06'], 'values': [0.016666667616666703, 0.012500000462500018, 0.012500000462500018, 0.016666667616666703, 0.025000000925000036, 0.033333331233333256, 0.041666668541666736, 0.050000001850000073, 0.054166669004166758, 0.058333335158333409, 0.062500002312500094, 0.066666669466666773, 0.066666669466666773, 0.066666669466666773, 0.066666669466666773, 0.066666669466666773, 0.058333332158333299, 0.054166669004166758, 0.04583333469583338, 0.037500001387500051, 0.029166668079166722, 0.020833333770833351, 0.02083330077083213, 0.016666667616666703]}, 'metab_cycles_0': {'dates': ['2015-01-01', '2015-01-02', '2015-01-03', '2015-01-04', '2015-01-05', '2015-01-06'], 'values': [75.0, 75.0, 75.0, 75.0, 99.583333333333343, 149.58333333333331, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 175.0, 150.41666666666669, 100.41666666666667, 75.0, 75.0], 'nation_id': 1285}, 'attribs_1285': {'attribs': [1.0, 1.0], 'dates': ['2015-01-01', '2015-01-02', '2015-01-03', '2015-01-04', '2015-01-05', '2015-01-06']}, 'traffic_cycles_1': {'dates': ['2015-01-02', '2015-01-05'], 'values': [0.0041666669999999998, 0.0083333330000000001, 0.020833332999999999, 0.033333333, 0.041666666999999998, 0.054166667000000002, 0.070833332999999998, 0.0625, 0.058333333000000001, 0.054166667000000002, 0.054166667000000002, 0.058333333000000001, 0.058333333000000001, 0.0625, 0.066666666999999999, 0.074999999999999997, 0.058333333000000001, 0.041666666999999998, 0.033333333, 0.029166667, 0.025000000000000001, 0.016666667, 0.0083333330000000001, 0.0041666669999999998]}, 'building_cycles_2': {'dates': ['2015-01-03'], 'values': [0.7260769800907596, 0.67676829208459599, 0.64813539008101695, 0.64891440908111431, 0.68655371808581922, 0.75545710409443212, 0.87917795010989719, 0.99351082912418887, 1.0638927601329866, 1.0970407901371302, 1.124839029140605, 1.124624402140578, 1.089695759136212, 1.0611343991326418, 1.0932251891366531, 1.2104356671513046, 1.3353250411669155, 1.3541725181692714, 1.3229879331653736, 1.2360796821545099, 1.1232015011404002, 1.0228830041278605, 0.92587136111573398, 0.79999629009999962]}, 'building_cycles_0': {'dates': ['2015-01-01', '2015-01-04', '2015-01-06'], 'values': [0.76523140099999998, 0.71310583000000005, 0.68076645499999999, 0.67350781599999998, 0.69818718999999996, 0.737477779, 0.80599933700000004, 0.89358122799999995, 1.0089252799999999, 1.1021859890000001, 1.132390469, 1.104841797, 1.038574688, 1.012435046, 1.056200373, 1.1742856290000001, 1.3123876510000001, 1.359269923, 1.35530756, 1.3052912640000001, 1.1938327179999999, 1.076533103, 0.96101825900000004, 0.83866321499999996]}, 'building_cycles_1': {'dates': ['2015-01-02', '2015-01-05'], 'values': [0.66107412702754464, 0.62026317302584422, 0.59972261802498839, 0.60775612202532303, 0.67472425702811345, 0.824136387034339, 0.94080447203920003, 1.0320372450430013, 1.0796747160449862, 1.1168879510465368, 1.1521026130480041, 1.1604542030483522, 1.1245147680468548, 1.1033758040459738, 1.1196316300466511, 1.2164374550506847, 1.3213508590550562, 1.3426859040559451, 1.3393786740558074, 1.2559223210523298, 1.1328794300472032, 1.005910566041913, 0.84231380403509637, 0.72596090003024827]}}
    #dict_to_namelist(d, 'c:/testoutput/testit.nml')
