from __future__ import absolute_import
import traceback
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QObject, pyqtSignal
import logging
import sys
from pathlib import Path

try: 
    import supy as sp
except:
    pass


class Worker(QtCore.QObject):
    # Worker to get netCDF data using a separate thread
    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(object)
    # progress = QtCore.pyqtSignal()
    # finished = pyqtSignal(object)
    # update = pyqtSignal(object)
    # error = pyqtSignal(Exception, str)

    def __init__(self, lat, lon, start_date, end_date, folderPath):
        QtCore.QObject.__init__(self)
        self.killed = False

        self.start_date = start_date
        self.end_date = end_date
        self.folderPath = folderPath
        self.lat = lat
        self.lon = lon

    def run(self):
        try:
            # sp.util.gen_forcing_era5(self.lat, self.lon, self.start_date, self.end_date, dir_save=self.folderPath)
            # print(self.folderPath)

            logger_sp = logging.getLogger('SuPy')
            logger_sp.disabled = True
            
            sp.util.gen_forcing_era5(self.lat, self.lon, self.start_date, self.end_date, dir_save=Path(self.folderPath))
            ret = 1
        except Exception:
            ret = 0
            errorstring = self.print_exception()
            self.error.emit(errorstring)
        
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

