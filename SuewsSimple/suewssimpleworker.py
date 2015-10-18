from PyQt4 import QtCore
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import *
import traceback
from ..suewsmodel import Suews_wrapper_v11


class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, iface, model_dir, dlg):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.iface = iface
        self.model_dir = model_dir
        self.dlg = dlg

    def run(self):

        ret = 1

        try:
            Suews_wrapper_v11.wrapper(self.model_dir)

            if self.killed is False:
                ret = 1

        except Exception, e:
            ret = 0
            self.error.emit(e, traceback.format_exc())

        self.finished.emit(ret)

    def kill(self):
        self.killed = True
