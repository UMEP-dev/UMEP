# -*- coding: utf-8 -*-
# __author__ = 'xlinfr'

from qgis.PyQt.QtWidgets import QMessageBox
from .supy_installer import setup_supy
# we can specify a version if needed
try: 
    import supy as sp
except:
    if QMessageBox.question(None, "Supy and related dependencies not installed on this system", "Do you want UMEP to automatically install? ", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
        try:
            setup_supy(ver=None)
            QMessageBox.information(None, "SuPy successfully installed",
                                    "Restart QGIS before you continue.")
        except Exception as e:
            QMessageBox.information(None, "An error occurred",
                                    "SuPy not installed. report any errors to https://bitbucket.org/fredrik_ucg/umep/issues")
    else:
        QMessageBox.information(None,
                                "Information", "SuPy not installed. Some UMEP tool will not be functioning proparly.")
# setup_supy(ver='2020.1.23')
