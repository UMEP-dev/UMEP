__author__ = 'xlinfr'
import numpy as np
from osgeo import gdal
import sys
plugin_dir = 'C:/Users/xlinfr/.qgis2/python/plugins/UMEP/LandCoverFractionPoint'
sys.path.append(plugin_dir)
# from Utilities.imageMorphometricParms_v1 import *
from Utilities.landCoverFractions_v1 import *



# dataset2 = gdal.Open(plugin_dir + '/data/clipdem.tif')
# dem = dataset2.ReadAsArray().astype(np.float)
dataset = gdal.Open(plugin_dir + '/data/clipdsm.tif')
dsm = dataset.ReadAsArray().astype(np.float)
# a = np.loadtxt(suews_5min, skiprows=1)
scale = 1.0
degree = 5.0
dlg = []

# immorphresult = imagemorphparam_v1(dsm, dem, scale, 1, degree, dlg, 0)
landcoverresult = landcover_v1(dsm, 1, degree, dlg, 1)

