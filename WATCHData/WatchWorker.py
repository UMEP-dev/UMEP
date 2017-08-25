# Worker object for WATCH data refinement
from PyQt4.QtCore import QObject, pyqtSignal
from WFDEIDownloader.FTPdownload import *
import traceback
from WFDEIDownloader.WFDEI_Interpolator import *


class WatchWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    update = pyqtSignal(object)

    def __init__(self, rawdata, datestart, dateend, input_AH_path, output_path, lat, lon, hgt, UTC_offset_h, rainAmongN):
        '''Instantiate Watch Worker:
        - rawData: Data source (NetCDF file containing 3h extracted data)
        - required_variables: Variables to process
        - input_AH_path: Full path to LQF AH data in CSV format
        - lat and lon: WGS84 lat and lon position for which to extract
        - hgt: site height to which to downscale air temperature
        - UTC_offset_h: offset between LST and UTC in hour
        - rainAmongN: number of rainy sub-intervals in a 3-h section'''

        QObject.__init__(self)
        self.killed = False
        self.datestart = datestart
        self.dateend = dateend
        self.rawdata = rawdata # NetCDF file containing raw data
        self.input_AH_path = input_AH_path  # LQF outputs
        self.output_path = output_path # Place to save file
        self.lat = lat
        self.lon = lon
        self.hgt = hgt
        self.UTC_offset_h = UTC_offset_h
        self.rainAmongN = rainAmongN

    def kill(self):
        self.killed = True

    def run(self):
        if self.input_AH_path is None:  # opt_AH: if AH results will be incorporated into downsacled WATCH data
            # normal downscaling
            try:
                runExtraction(self.rawdata, self.output_path, self.datestart.year,
                              self.dateend.year, self.hgt,
                              self.UTC_offset_h, self.rainAmongN, self.update)
            except Exception, e:
                self.error.emit(e, traceback.format_exc())
        else:
            # incorporating AH results
            try:
                runExtraction_AH(self.rawdata, self.input_AH_path, self.output_path,
                                 self.datestart.year, self.dateend.year,
                                 self.hgt,
                                 self.UTC_offset_h, self.rainAmongN, self.update)
            except Exception, e:
                self.error.emit(e, traceback.format_exc())

        self.finished.emit(None)
