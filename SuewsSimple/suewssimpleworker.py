from PyQt4 import QtCore
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import *
import traceback
import Suews_wrapper_v7

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, iface, plugin_dir, dlg):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.dlg = dlg

    def run(self):

        ret = 0

        try:
            wrapperresult = Suews_wrapper_v7.wrapper(self.plugin_dir)
            # self.progress.emit()

            if self.killed is False:
                # self.progress.emit()
                # ret = wrapperresult  ### THIS DOES NOT WORK
                ret = 1

        except Exception, e:
            ret = 0
            self.error.emit(e, traceback.format_exc())

        self.finished.emit(ret)

    def kill(self):
        self.killed = True
