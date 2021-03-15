# -*- coding: utf-8 -*-
# __author__ = 'xlinfr'

from qgis.PyQt.QtWidgets import QMessageBox
from .supy_installer import setup_supy
from qgis.core import Qgis, QgsMessageLog
# we can specify a version if needed
try: 
    import supy as sp
    from supy import __version__ as ver_supy
    QgsMessageLog.logMessage("UMEP - SuPy Version installed: " + ver_supy, level=Qgis.Info)
except:
    if QMessageBox.question(None, "Supy and related dependencies not installed", 
              "Do you want UMEP to automatically install? \r\n"
              "QGIS will be non-responsive for a couple of minutes.", 
               QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
        try:
            setup_supy(ver=None)
            QMessageBox.information(None, "Packages successfully installed",
                                    "We recommend that you restart QGIS before you continue.")
        except Exception as e:
            QMessageBox.information(None, "An error occurred",
                                    "Packages not installed. report any errors to https://github.com/UMEP-dev/UMEP/issues")
    else:
        QMessageBox.information(None,
                                "Information", "Packages not installed. Some UMEP tools will not be fully operational.")
# setup_supy(ver='2020.1.23')
