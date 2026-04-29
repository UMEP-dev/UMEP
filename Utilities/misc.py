__author__ = 'xlinfr'

import numpy as np
from osgeo import gdal
from osgeo.gdalconst import *
from pandas import read_csv, to_datetime


# Slope and aspect used in SEBE and Wall aspect
def get_ders(dsm, scale):
    # dem,_,_=read_dem_grid(dem_file)
    dx = 1/scale
    # dx=0.5
    fy, fx = np.gradient(dsm, dx, dx)
    asp, grad = cart2pol(fy, fx, 'rad')
    slope = np.arctan(grad)
    asp = asp * -1
    asp = asp + (asp < 0) * (np.pi * 2)
    return slope, asp


def cart2pol(x, y, units='deg'):
    radius = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    if units in ['deg', 'degs']:
        theta = theta * 180 / np.pi
    return theta, radius


def saveraster(gdal_data, filename, raster):
    rows = gdal_data.RasterYSize
    cols = gdal_data.RasterXSize

    outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
    outBand = outDs.GetRasterBand(1)

    # write the data
    outBand.WriteArray(raster, 0, 0)
    # flush data to disk, set the NoData value and calculate stats
    outBand.FlushCache()
    outBand.SetNoDataValue(-9999)

    # georeference the image and set the projection
    outDs.SetGeoTransform(gdal_data.GetGeoTransform())
    outDs.SetProjection(gdal_data.GetProjection())


def get_resolution_from_umep_forcing(met_path):

    forcing = read_csv(met_path, sep=r"\s+")
    forcing['Datetime'] = to_datetime(forcing[['iy', 'id', 'it', 'imin']].astype(str).agg('-'.join, axis=1), format='%Y-%j-%H-%M')
    # # Set the datetime column as the index
    forcing.set_index('Datetime', inplace=True)

    time1 = list(forcing.iloc[[1]].index)
    time2 = list(forcing.iloc[[2]].index)
    inputresolution = int((time2[0]-time1[0]).total_seconds())

    return inputresolution