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
from .umep_installer import locate_py, setup_umep_python
from qgis.core import Qgis, QgsMessageLog


#test
import subprocess
from packaging import version
ver = "3.1"
str_ver = f"=={ver}" if ver else ""
# get Python version
str_ver_qgis = sys.version.split(" ")[0]
path_pybin = locate_py()
# update pip to use new features
list_cmd0 = f"{str(path_pybin)} -m pip install pip -U --user".split()
str_info0 = subprocess.check_output(
    list_cmd0, stderr=subprocess.STDOUT, encoding="UTF8"
)

# add netCDF4 TODO: Should later be replaced with xarrays
# list_cmd0 = f"{str(path_pybin)} -m pip install netCDF4 -U --user".split()
# str_info0 = subprocess.check_output(
#     list_cmd0, stderr=subprocess.STDOUT, encoding="UTF8"
# )

# install supy and dependencies
str_use_feature = (
    "--use-feature=2020-resolver"
    if version.parse(str_ver_qgis) <= version.parse("3.9.1")
    else ""
)
# select correct supy version via extras (QGIS 3 vs 4)
qgis_major = int(Qgis.QGIS_VERSION.split('.')[0])
qgis_extra = f"[qgis{qgis_major}]"
# --prefer-binary because https://github.com/jameskermode/f90wrap/issues/203
list_cmd = f"{str(path_pybin)} -m pip install umep-reqs{qgis_extra}{str_ver} -U --user --prefer-binary {str_use_feature}".split()
QgsMessageLog.logMessage(str(list_cmd), level=Qgis.Info)

try:
    # temprorary disable in preparation of QGIS4                                            
    # import supy as sp  
    # import numba
    # import jaydebeapi
    # import rioxarray
    # import yaml
    # import pydantic
    #import timezonefinder
    from supy import __version__ as ver_supy
    QgsMessageLog.logMessage("UMEP - SuPy Version installed: " + ver_supy, level=Qgis.MessageLevel.Info)

except:
    if QMessageBox.question(None, "UMEP for Processing Python dependencies not installed",
              "Do you automatically want install missing python modules? \r\n"
              "QGIS will be non-responsive for a couple of minutes.",
               QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Ok:
        try:
            path_pybin = locate_py()
        except Exception:
            QMessageBox.information(
                None,
                "Could not determine location of QGIS Python binary",
                "Please report at https://github.com/UMEP-dev/UMEP-processing/issues",
            )
        try:
            setup_umep_python(ver='3.1')
            QMessageBox.information(None, "Packages successfully installed",
                                    "To make all parts of the plugin work it is recommended to restart your QGIS-session.")
        except Exception as e:
            QgsMessageLog.logMessage(traceback.format_exc(), level=Qgis.MessageLevel.Warning)
            QMessageBox.information(None, "An error occurred",
                                    "UMEP couldn't install Python packages!\n"
                                    "See 'General' tab in 'Log Messages' panel for details.\n"
                                    "Report any errors to https://github.com/UMEP-dev/UMEP-processing/issues")
    else:
        QMessageBox.information(None,
                                "Information", "Packages not installed. Some UMEP tools will not be fully operational.")


