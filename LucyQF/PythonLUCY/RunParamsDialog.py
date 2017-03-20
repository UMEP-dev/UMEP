from PyQt4 import QtGui, uic
from PyQt4.QtGui import QListWidgetItem, QDialog
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplicationm
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
import os
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'RunParamsDialog.ui'))
from matplotlib import pyplot
from datetime import datetime as dt


class RunParamsDialog(QDialog, FORM_CLASS):
    def __init__(self, runParams, parent=None):
        self.state = None

        """Constructor."""
        super(RunParamsDialog, self).__init__(parent)
        self.cmdContinue.clicked.connect(self.doApprove)
        self.cmdCancel.clicked.connect(self.doReject)

        self.lblFirstDate.setText(runParams['firstDate'])
        self.lblFinalDate.setText(runParams['finalDate'])
        if 'diurnalBuildings' in runParams.keys():
            self.lblBldgDiurnal.setText('File at: ' + runParams['diurnalBuildings'][-30:])
        if 'diurnalTraffic' in runParams.keys():
            self.lblBldgDiurnal.setText('File at: ' + runParams['diurnalTraffic'][-30:])


    @staticmethod
    def getUserApproval(parent = None):
        dialog = RunParamsDialog(parent)
        result = dialog.exec_()
        date = dialog.dateTime()
        return (date.date(), date.time(), result == QDialog.Accepted)

