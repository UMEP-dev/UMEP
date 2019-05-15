from qgis.PyQt import QtCore
import linecache
from ..suewsmodel import Suews_wrapper_v2019a
import sys


class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, iface, model_dir, dlg):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.iface = iface
        self.model_dir = model_dir
        self.dlg = dlg

    def run(self):

        ret = None

        try:
            df_output_suews_rsmp = Suews_wrapper_v2019a.wrapper(self.model_dir)

            if self.killed is False:
                ret = df_output_suews_rsmp

        except Exception:
            # self.error.emit(traceback.format_exc())
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
