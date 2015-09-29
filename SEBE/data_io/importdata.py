# -*- coding: utf-8 -*-

"""
## -*- texinfo -*-
## @deftypefn  {Function File} {@var{A} =} importdata (@var{fileName})
## @deftypefnx {Function File} {@var{A} =} importdata (@var{fileName}, @var{delimiter})
## @deftypefnx {Function File} {@var{A} =} importdata (@var{fileName}, @var{delimiter},  @var{headerRows})
## @deftypefnx {Function File} {[@var{A}, @var{delimiter}] =} importdata (...)
## @deftypefnx {Function File} {[@var{A}, @var{delimiter}, @var{headerRows}] =} importdata (...)
## Importing data from file.
##
## Importing the contents of file @var{fileName} into workspace.
##
## Input parameters:
## @table @input
## @item @var{fileName}
## The file name for the file to import.
##
## @item @var{delimiter}
## The character separating columns of data. Use @code{\t} for tab. (Only valid for ascii files)
##
## @item @var{headerRows}
## Number of header rows before the data begins. (Only valid for ascii files)
## @end table
##
## Different file types are supported:
## @itemize
## @item Ascii table
##
## Importing ascii table using the specified number of header rows and the specified delimiter.
##
## @item Image file
##
## @item Matlab file
##
## @item Wav file
##
## @end table
##
## @seealso{textscan, dlmread, csvread, load}
## @end deftypefn
"""

import os
from PIL import Image
import numpy as np

def importdata(*args):
    nargin = len(args)

    # Default values
    fileName = ''
    delimiter = ''
    headerRows = -1
    output = dict()

    # Check input arguments
    if nargin < 1:
        print_usage()

    fileName = args[0]
    if not isinstance(fileName, str):
        raise TypeError("importdata: File name needs to be a string.")
    if '-pastespecial' in fileName:
        raise ValueError('importdata: Option ''-pastespecial'' not implemented.')

    if nargin > 1:
        delimiter = args[1]
        # Check that the delimiter really is a string
        if not isinstance(delimiter, str):
            raise TypeError('importdata: Delimiter needs to be a character.')
        if len(delimiter) > 1 and not delimiter is '\t':
            raise ValueError('importdata: Delimiter cannot be longer than 1 character.')
        if delimiter is '\\':
            delimiter = '\\\\'    # if delimiter is "\" change to "\\"

    if nargin > 2:
        headerRows = args[2]
        if not isinstance(headerRows, int) or headerRows < 0:
            raise TypeError('importdata: Number of header rows needs to be an integer number >= 0.')

    if nargin > 3:
        raise ValueError('importdata: Too many input arguments.')

    #########################

    # Check file format
    # Get the extension from the file name.
    dir = os.path.dirname(fileName)
    name, ext = os.path.basename(fileName).split(".")
    ext = ext.lower()   # Make sure file extension is in lower case.

    if ext in ['.au', '.snd']:
        raise ValueError('importdata: Not implemented for file format ' + ext + '.')
    elif ext is '.avi':
        raise ValueError('importdata: Not implemented for file format ' + ext + '.')
    elif ext in ['.bmp', '.cur', '.gif', '.hdf', '.ico', '.jpe', '.jpeg', '.jpg', '.pbm', '.pcx', '.pgm', '.png', '.pnm', '.ppm', '.ras', '.tif', '.tiff', '.xwd']:
        delimiter  = None
        headerRows = 0
        img = Image.open(fileName)
        output['cdata'] = np.array(img)
        output['colormap'] = img.mode    # TODO: check if this method is euaivalent
        output['alpha'] = img.split()[-1]
    elif ext is '.mat':
        import scipy.io as sio
        delimiter  = None
        headerRows = 0
        output = sio.loadmat(fileName)
    elif ext is '.wk1':
        raise ValueError('importdata: Not implemented for file format ' + ext + '.')
    elif ext in ['.xls', '.xlsx']:
        raise ValueError('importdata: Not implemented for file format ' + ext + '.')
    elif ext in ['.wav', '.wave']:
        #delimiter  = None
        #headerRows = 0
        #[output.data, output.fs] = wavread(fileName)
        raise ValueError('importdata: Not implemented for file format ' + ext + '.')
    else:
        # Assume the file is in ascii format.
        output, delimiter, headerRows = importdata_ascii(fileName, delimiter, headerRows)
        #raise ValueError('importdata: Not implemented for file format: ASCII')

    # If there are any empty elements in the output dict, then remove them
    if isinstance(output, dict) and len(output) == 1:
        for key, val in output.copy().iteritems():    # copy() for py3 compatibility or use items()
            if not val:
                del output[key]

    # If only one element is left, replace the dict with the element, i.e. output = output['onlyFieldLeft']
    # Update the list of fields
    fields = output.keys()
    if len(fields) == 1:
        output = output[fields[0]]

    return output, delimiter, headerRows

def print_usage():
    """
    Prints the how-to document
    :return: None
    """
    print "Needs to be written"
    return

def importdata_ascii(fileName, delimiter, headerRows):
    output = dict()
    output['data'] = np.array([])
    output['textdata'] = list()
    #output['rowheaders'] = int
    #output['colheaders'] = int

    # Read file into string and count the number of header rows
    with open(fileName, 'rb') as txt:
        fileContentRows = txt.readlines()

    # removing \r\n or \n character from each lines
    fileContentRows = [line.rstrip('\r\n') for line in fileContentRows]

    if not delimiter:
        raise ValueError('importdata: Guessing delimiter is not implemented yet, you have to specify it.')

    if headerRows < 0:
        headerRows = 0
        for line in fileContentRows:
            if delimiter in line:
                headerRows += 1
            else:
                # Data part has begun and therefore no more header rows can be found
                break
    # Put the header rows in output.textdata.
    if headerRows > 0:
        # output['textdata'] = fileContentRows[0:headerRows]    # TODO check this line later
        for i, el in enumerate(fileContentRows[0:headerRows]):
            output['textdata'].append(unicode(el))    # struct in ML is converted to dict in py

    # If space is the delimiter, then remove spaces in the beginning of each data row.
    if delimiter is ' ':
        # strtrim does not only remove the leading spaces but also the tailing spaces, but that doesn't really matter.
        fileContentRows = fileContentRows[:headerRows] + [line.strip() for line in fileContentRows[headerRows:]]

    # Remove empty data rows. Go through them backwards so that you wont get out of bounds.
    # from last element to index=header in reverse
    fileContentRows = fileContentRows[:headerRows] + [line for line in fileContentRows[headerRows:] if not len(line) < 1]
                                                                        # if not line:   # more pythonic, needs testing
    # Count the number of data columns.
    # If there are different number of columns, use the greatest value.
    dataColumns = 0
    for line in fileContentRows:
        num_elements = len([el for el in line.split(delimiter) if el])    # if element is not empty
        dataColumns = max(dataColumns, num_elements)

    print "headerRows py:", headerRows
    # Go through the data and put it in either output.data or output.textdata depending on if it is numeric or not.
    output['data'] = np.empty((len(fileContentRows)-headerRows, dataColumns)) * np.nan
    for i, line in enumerate(fileContentRows[headerRows:]):
        # Only use the row if it contains anything other than white-space characters.
        if line.replace(" ", ""):
            rowData = line.split(delimiter)
            for j, el in enumerate(rowData):
                try:
                    output['data'][i, j] = float(el)
                except ValueError:
                    output['textdata'].append(unicode(el))    # using tuple (i,j) as key to dict textdata

    # Check wether rowheaders or colheaders should be used
    if headerRows == dataColumns and max(j for i, j in output['textdata']) == 1:    # getting the col size, assuming
                                                                                    # the dict is equivalent of struct in Matlab
        output['rowheaders'] = output['textdata']
    #elif max(j for i, j in output['textdata']) == 1 == dataColumns:    # TODO fix this
    #    output['colheaders'] = output['textdata']

    # making changes to data to fit the Matlab function
    headerRows = float(headerRows)
    return output, delimiter, headerRows