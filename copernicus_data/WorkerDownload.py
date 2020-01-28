from __future__ import absolute_import
import traceback
from qgis.PyQt.QtCore import QObject, pyqtSignal
try: 
    import supy as sp
except:
    pass


class DownloadDataWorker(QObject):
    # Worker to get netCDF data using a separate thread
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, str)

    def __init__(self, start_date, end_date, folderPath, lat, lon):
        QObject.__init__(self)
        self.killed = False
        self.start_date = start_date
        self.end_date = end_date
        self.folderPath = folderPath
        self.lat = lat
        self.lon = lon

    def kill(self):
        self.killed = True

    def run(self):
        try:
            sp.util.gen_forcing_era5(self.lat, self.lon, self.start_date, self.end_date, dir_save=self.folderPath)

            # sp.util.gen_forcing_era5(self.lat, self.lon, self.start_date, self.end_date, dir_save=self.folderPath[0])

            self.finished.emit()
        except Exception as e:
            self.error.emit(e, traceback.format_exc())
