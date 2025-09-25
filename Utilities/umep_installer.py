import sys, subprocess, os
from pathlib import Path
import platform
from packaging import version

from qgis.core import Qgis, QgsMessageLog


# locate QGIS-python interpreter
def locate_py():

    # get Python version
    str_ver_qgis = sys.version.split(" ")[0]

    try:
        # non-Linux
        path_py = os.environ["PYTHONHOME"]
    except Exception:
        # Linux
        path_py = sys.executable

    # convert to Path for eaiser processing
    path_py = Path(path_py)

    # pre-defined paths for python executable
    if platform.system() == "Windows":
        candidates = [
            path_py
            / (
                "../../bin/pythonw.exe"
                if version.parse(str_ver_qgis) >= version.parse("3.9.1")
                else "pythonw.exe"
            ),
            path_py.with_name("pythonw.exe"),
        ]
    else:
        candidates = [
            path_py / "bin" / "python3",
            path_py / "bin" / "python",
            path_py.with_name("python3"),
            path_py.with_name("python"),
        ]

    for candidate_path in candidates:
        if candidate_path.exists():
            return candidate_path

    raise RuntimeError("UMEP cannot locate the Python interpreter used by QGIS!")


# check if supy is installed
def check_supy_version():
    try:
        path_pybin = locate_py()
        list_cmd = f"{str(path_pybin)} -m pip show supy".split()
        list_info = subprocess.check_output(list_cmd, encoding="UTF8").split("\n")
        str_ver = list_info[1].split(":")[1].strip()
        return str_ver
    except Exception:
        raise RuntimeError("UMEP cannot identify a supy installation!") from Exception


# install supy
def install_umep_python(ver=None):
    str_ver = f"=={ver}" if ver else ""
    # get Python version
    str_ver_qgis = sys.version.split(" ")[0]
    try:
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
        # --prefer-binary because https://github.com/jameskermode/f90wrap/issues/203
        list_cmd = f"{str(path_pybin)} -m pip install umep-reqs{str_ver} -U --user --prefer-binary {str_use_feature}".split()
        str_info = subprocess.check_output(
            list_cmd, stderr=subprocess.STDOUT, encoding="UTF8"
        )

        str_info = str_info.split("\n")[-2].strip()

        str_info = (
            str_info
            if "Successfully installed UMEP dependent Python packages" in str_info
            else f"UMEP dependent Python packages has already been installed!"
        )
        return str_info
    except subprocess.CalledProcessError as exc:
        QgsMessageLog.logMessage(f"Error running {exc.args}:\n{exc.stdout}", level=Qgis.Warning)
        raise


# uninstall supy
def uninstall_umep_python():

    try:
        path_pybin = locate_py()
        list_cmd = f"{str(path_pybin)} -m pip uninstall umep-reqs -y".split()
        list_info = subprocess.check_output(list_cmd, encoding="UTF8").split("\n")

        str_info = list_info[-2].strip()
        return str_info
    except Exception:
        raise RuntimeError(f"UMEP couldn't uninstall umep-reqs!") from Exception


# set up umep
def setup_umep_python(ver=None, debug=False):
    if debug:
        uninstall_umep_python()
        install_umep_python(ver)

    try:
        # check if supy and others have been installed
        import supy as sp
        sp.show_version()
        import numba
        import jaydebeapi

    except Exception:
        # install supy
        install_umep_python(ver)
