# -*- coding: utf-8 -*-
# __author__ = 'xlinfr'
import traceback

# The .egg packages shipped with QGIS sometimes appear before the user site dir
# in sys.path. To make sure package versions we install with "--user" take precedence,
# prepend the user site dir to sys.path before importing other packages.
# This works around https://github.com/qgis/QGIS/issues/55258
import site
import sys
sys.path.insert(0, site.getusersitepackages())

from qgis.PyQt.QtWidgets import QMessageBox
from .supy_installer import locate_py, setup_supy
from qgis.core import Qgis, QgsMessageLog
# we can specify a version if needed
try: 
    import supy as sp
    from supy import __version__ as ver_supy
    QgsMessageLog.logMessage("UMEP - SuPy Version installed: " + ver_supy, level=Qgis.Info)
except:
    if QMessageBox.question(None, "UMEP dependencies not installed",
              "Do you automatically want install missing python modules? \r\n"
              "QGIS will be non-responsive for a couple of minutes.",
               QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
        try:
            path_pybin = locate_py()
        except Exception:
            QMessageBox.information(
                None,
                "Could not determine location of QGIS Python binary",
                "Please report at https://github.com/UMEP-dev/UMEP-processing/issues",
            )

        try:
            setup_supy(ver=None)
            QMessageBox.information(None, "Packages successfully installed",
                                    "To make all parts of the plugin work it is recommended to restart your QGIS-session.")
        except Exception as e:
            QgsMessageLog.logMessage(traceback.format_exc(), level=Qgis.Warning)
            QMessageBox.information(None, "An error occurred",
                                    "UMEP couldn't install Python packages!\n"
                                    "See 'General' tab in 'Log Messages' panel for details.\n"
                                    "Report any errors to https://github.com/UMEP-dev/UMEP-processing/issues")
    else:
        QMessageBox.information(None,
                                "Information", "Packages not installed. Some UMEP tools will not be fully operational.")



#    if QMessageBox.question(None, "Supy and related dependencies not installed", 
#              "Do you want UMEP to automatically install missing python modules? \r\n"
#              "QGIS will be non-responsive for a couple of minutes.", 
#               QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
#        setup_supy(ver=None)
#        try:
#            setup_supy(ver=None)
#            QMessageBox.information(None, "Packages successfully installed", 
#                                    "To make all parts of the plugin work it is recommended to restart your QGIS-session.")
#        except Exception as e:
#            QMessageBox.information(None, "An error occurred",
#                                    "Packages not installed. report any errors to https://github.com/UMEP-dev/UMEP/issues")
#    else:
#        QMessageBox.information(None,
#                                "Information", "Packages not installed. Some UMEP tools will not be fully operational.")
# setup_supy(ver='2020.1.23')
