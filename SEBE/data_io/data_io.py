
from osgeo import gdal, gdal_array
from osgeo.gdalconst import GDT_Float64,GDT_Float32,GDT_UInt32,GDT_UInt16,GDT_Byte

import numpy
import hashlib
import os
import cPickle
from collections import namedtuple
import subprocess
import tempfile
from math import pi,sin

from Solweig_10_metdata import Solweig_10_metdata
from sunmapcreator_2014a import sunmapcreator_2014a

Location = namedtuple('Location', ['longitude', 'latitude', 'altitude'])


def read_dem_grid(filepath):
    gridFile=gdal.Open(filepath)
    grid=gridFile.GetRasterBand(1)
    geoTransform=gridFile.GetGeoTransform()
    gridArray=grid.ReadAsArray()
    if gridArray.dtype=='float64':
        gridArray = gridArray.astype(numpy.float32, copy=False)
    gridScale=None
    if geoTransform is not None:
        try:
            gridScale=abs(1.0/geoTransform[1])
        except:
            #we have no geoTransform info or scale is zero
            pass
    if gridScale is None:
        gridScale=1.0
    return (gridArray, gridScale, geoTransform)

def write_dem(dem_array,file_name,geotransform=None):
    driver=gdal.GetDriverByName('GTiff')
    #print "dem_max",numpy.max(dem_array)
    #print "dem_min",numpy.min(dem_array)
    data_file=driver.Create(file_name,dem_array.shape[1],dem_array.shape[0],1,GDT_Float32)
    if geotransform is not None:
        print "geotransform",geotransform
        data_file.SetGeoTransform(geotransform)
    data_file.GetRasterBand(1).WriteArray(dem_array)
    data_file=None


def parse_met_data(met_data,longitude,latitude,altitude,UTC,):
    location={'longitude':longitude,'latitude':latitude,'altitude':altitude}
    print "met data:", met_data
    met,met_header,time,altitude,azimuth,zen,jday,XM,XD=Solweig_10_metdata(met_data,location,UTC)
    return (met,time,altitude,azimuth,zen,jday,XM,XD)


def build_radmat(met,altitude,azimuth,jday,albedo,calc_month=False,onlyglobal=False):
    if onlyglobal:
        onlyglobal=1
    else:
        onlyglobal=0
    output={'energymonth':0,'energyyear':1,'suitmap':0}
    if calc_month:
        output['energymonth']=1

    radmatI,radmatD,radmatR=sunmapcreator_2014a(met,altitude,azimuth,onlyglobal,output,jday,albedo)
    return radmatI,radmatD,radmatR


def read_weather_data(met_data,longitude,latitude,altitude,UTC,albedo=0.15,use_cache=True):
    with open(met_data,'r') as wf:
        weather_hash=hashlib.md5(wf.read()).hexdigest()
    metdata_pickle='metdata_'+weather_hash+'.pkl'
    if use_cache and os.path.isfile(metdata_pickle):
        print "using cached met_data"
        with open(metdata_pickle,'rb') as mdp:
            radmatI,radmatD,radmatR=cPickle.load(mdp)
    else:
        print "parsing_met"
        met, time, altitude, azimuth, zen, jday, XM, XD = parse_met_data(met_data,longitude,latitude,altitude,UTC)
        print "building radmat"
        radmatI,radmatD,radmatR=build_radmat(met ,altitude,azimuth,jday,albedo,calc_month=False,onlyglobal=False)
        with open(metdata_pickle,'wb') as mdp:
            cPickle.dump((radmatI,radmatD,radmatR),mdp,protocol=cPickle.HIGHEST_PROTOCOL)

    return (radmatI,radmatD,radmatR)


def make_location(longitude,latitude,altitude):
    return Location(longitude,latitude,altitude)
