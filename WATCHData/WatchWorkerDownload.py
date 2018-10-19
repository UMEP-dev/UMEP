from __future__ import absolute_import
# Worker object for WATCH data refinement
from qgis.PyQt.QtCore import QObject, pyqtSignal
import traceback
from ..Utilities.ncWMSConnector import NCWMS_Connector


class DownloadDataWorker(QObject):
    # Worker to get netCDF data using a separate thread
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, str)

    def __init__(self, hw_start, hw_end, watch_vars, ll_lat, ll_lon, ur_lat, ur_lon):
        QObject.__init__(self)
        self.hw_start = hw_start
        self.hw_end = hw_end
        self.watch_vars = watch_vars
        self.ll_lat = ll_lat
        self.ll_lon = ll_lon
        self.ur_lat = ur_lat
        self.ur_lon = ur_lon
        self.downloader = NCWMS_Connector()

    def kill(self):
        self.downloader.kill()

    def run(self):
        try:
            output = self.webToTimeseries(self.hw_start, self.hw_end, self.watch_vars, self.ll_lat, self.ll_lon,
                                          self.ur_lat, self.ur_lon, self.update)
            self.finished.emit(output)
        except Exception as e:
            self.error.emit(e, traceback.format_exc())

    def webToTimeseries(self, hw_start, hw_end, watch_vars, ll_lat, ll_lon, ur_lat, ur_lon, update=None):
        """
        Take WCS raster layer and save to local geoTiff
        :param baseURL: Server URL up to the /wcs? part where the query string begins (not including the question mark)
        :param layer_name: The coverage name on the WCS server
        :param output_file: File to save as (GeoTIFF)
        :param bbox: dict with WGS84 coordinates {xmin: float <lower left longitude>, xmax:float, ymin:float <upper right latitude>, ymax:float}
        :param resolution: dict {x:float, y:float} containing the resolution to use
        :param srs: string e.g. EPSG:4326: The layer CRS string
        :return: Path to output file
        """
        self.downloader.get_data(start_date=hw_start,  # Connector will take the first moment of this date
                                 end_date=hw_end,  # Connector will take the final second of this date
                                 variables=watch_vars,  # Get all variables
                                 lowerleft_lat=ll_lat,
                                 lowerleft_lon=ll_lon,
                                 upperright_lat=ur_lat,
                                 upperright_lon=ur_lon,
                                 update=update)
        temp_netcdf = self.downloader.average_data(None, 'mean')
        return temp_netcdf