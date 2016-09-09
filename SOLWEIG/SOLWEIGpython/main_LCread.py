__author__ = 'xolofr'

import numpy as np
import gdal
from matplotlib import pylab as plt
from qgis.core import QgsVectorLayer, QgsApplication, QgsFeature, QgsVectorFileWriter
# import subprocess
# import os
# from gdalconst import *
# import time


folderpath_LCtif = 'C:/Users/xolofr/Documents/URBANFLUXES/Heraklion/Heraklion_qgis_project/surface_percentages/'
folderpath_grid = 'C:/Users/xolofr/Documents/URBANFLUXES/Heraklion/Heraklion_qgis_project/'

agriculture = gdal.Open(folderpath_LCtif + 'agriculture.tif')
baresoil = gdal.Open(folderpath_LCtif + 'bare_soil.tif')
lowveg = gdal.Open(folderpath_LCtif + 'low_veg.tif')
highveg = gdal.Open(folderpath_LCtif + 'high_veg_forest.tif')
industrial = gdal.Open(folderpath_LCtif + 'industrial.tif')
urban = gdal.Open(folderpath_LCtif + 'urban.tif')
water = gdal.Open(folderpath_LCtif + 'water.tif')

vlayer = QgsVectorLayer(folderpath_grid + 'UF_HERAKLION_GRID_polygon_DTM.shp', "polygon", "ogr")         # ladda vektorlager
prov = vlayer.dataProvider()
idx = vlayer.fieldNameIndex('UF_HER_ID')
index = 0

for f in vlayer.getFeatures():  # looping through each grid polygon

    attributes = f.attributes()
    geometry = f.geometry()
    feature = QgsFeature()
    feature.setAttributes(attributes)
    feature.setGeometry(geometry)
    gnumber = f.id()
    index = index + 1
    print gnumber



LC_water = water.ReadAsArray().astype(np.float)
numformat = '%9.6f'
np.savetxt('tzdLC.txt', LC_water, fmt=numformat, delimiter=' ', comments='')

fig = plt.figure()
