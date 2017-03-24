# Worker object for WATCH data extraction
from PyQt4.QtCore import QObject, pyqtSignal
from WFDEIDownloader.FTPdownload import *
import traceback
from WFDEIDownloader.WFDEI_Interpolator import *


class WatchWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)

    def __init__(self, rawdata, required_variables, datestart, dateend, input_path, input_AH_path, output_path, lat, lon, hgt, UTC_offset_h, rainAmongN, textObject=None):
        '''Instantiate Watch Worker:
        - rawData: Data source (compressed file location)
        - required_variables: Variables to download and extract
        - datestart and dateend: start and end date for extraction and download
        - input_path: Full path to WFDEI data within rawdata
        - input_AH_path: Full path to LQF AH data in CSV format
        - output_path: Full path to extracted file
        - lat and lon: WGS84 lat and lon position for which to extract
        - hgt: site height to correct downsacled air temperature
        - UTC_offset_h: offset between LST and UTC in hour
        - rainAmongN: number of rainy sub-intervals in a 3-h section
        - textObject: Qlabel to narrate what's going on. Needs only a .setText method'''

        QObject.__init__(self)
        self.killed = False
        self.datestart = datestart
        self.dateend = dateend
        self.rawdata = rawdata
        self.required_variables = required_variables
        self.input_path = input_path
        self.input_AH_path = input_AH_path
        self.output_path = output_path
        self.lat = lat
        self.lon = lon
        self.hgt = hgt
        self.UTC_offset_h = UTC_offset_h
        self.rainAmongN = rainAmongN
        self.textObject = textObject

    def kill(self):
        self.killed = True

    def run(self):
        if self.textObject is not None:
            self.textObject.setText('Downloading data from server...')

        try:
            runDownload(self.rawdata, self.required_variables, self.datestart.strftime(
                '%Y%m'), self.dateend.strftime('%Y%m'), self.textObject)
        except Exception, e:
            self.error.emit(e, traceback.format_exc())

        if not self.input_AH_path:  # opt_AH: if AH results will be incorporated into downsacled WATCH data
            # normal downscaling
            try:
                runExtraction(self.input_path, self.output_path, self.datestart.year,
                              self.dateend.year, self.lat, self.lon, self.hgt,
                              self.UTC_offset_h, self.rainAmongN, self.textObject)
            except Exception, e:
                self.error.emit(e, traceback.format_exc())
        else:
            # incorporating AH results
            try:
                runExtraction_AH(self.input_path, self.input_AH_path, self.output_path,
                                 self.datestart.year, self.dateend.year,
                                 self.lat, self.lon, self.hgt,
                                 self.UTC_offset_h, self.rainAmongN, self.textObject)
            except Exception, e:
                self.error.emit(e, traceback.format_exc())

        self.finished.emit(None)
