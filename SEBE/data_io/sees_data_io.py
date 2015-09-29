try:
    from osgeo import gdal, gdal_array
    from osgeo.gdalconst import GDT_Float64,GDT_Float32,GDT_UInt32,GDT_UInt16,GDT_Byte
except:
    use_gdal=False
else:
    use_gdal=True

print "using GDAL", use_gdal

import numpy
import hashlib
import os
import cPickle
from collections import namedtuple
import subprocess
import tempfile
from math import pi,sin

Location = namedtuple('Location', ['longitude', 'latitude', 'altitude'])

#GDALDEM=r"C:\Program Files\GDAL\gdaldem.exe"
#GDALDEM=r"C:\OSGeo4W64\bin\gdaldem.exe"
GDALDEM=r"gdaldem"

def read_dem_grid_gdal(filepath):
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
    return (gridArray,gridScale,geoTransform)


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

def parse_met_data(octave,met_data,longitude,latitude,altitude,UTC,):
    location={'longitude':longitude,'latitude':latitude,'altitude':altitude}
    met,met_header,time,altitude,azimuth,zen,jday,XM,XD=octave.Solweig_10_metdata(met_data,location,UTC)
    return (met,time,altitude,azimuth,zen,jday,XM,XD)

def build_radmat(octave,met,altitude,azimuth,jday,albedo,calc_month=False,onlyglobal=False):
    if onlyglobal:
        onlyglobal=1
    else:
        onlyglobal=0
    output={'energymonth':0,'energyyear':1,'suitmap':0}
    if calc_month:
        output['energymonth']=1

    radmatI,radmatD,radmatR=octave.sunmapcreator_2014a(met,altitude,azimuth,onlyglobal,output,jday,albedo);
    return radmatI,radmatD,radmatR

def read_weather_data(octave,met_data,longitude,latitude,altitude,UTC,albedo=0.15,use_cache=True):
    with open(met_data,'r') as wf:
        weather_hash=hashlib.md5(wf.read()).hexdigest()
    metdata_pickle='metdata_'+weather_hash+'.pkl'
    if use_cache and os.path.isfile(metdata_pickle):
        print "using cached met_data"
        with open(metdata_pickle,'rb') as mdp:
            radmatI,radmatD,radmatR=cPickle.load(mdp)
    else:
        print "parsing_met"
        met, time, altitude, azimuth, zen, jday, XM, XD = parse_met_data(octave,met_data,longitude,latitude,altitude,UTC)
        print "building radmat"
        radmatI,radmatD,radmatR=build_radmat(octave, met ,altitude,azimuth,jday,albedo,calc_month=False,onlyglobal=False)
        with open(metdata_pickle,'wb') as mdp:
            cPickle.dump((radmatI,radmatD,radmatR),mdp,protocol=cPickle.HIGHEST_PROTOCOL)

    return (radmatI,radmatD,radmatR)


def get_temp_file(suffix=""):
    fd,temp_filename=tempfile.mkstemp(suffix=suffix)
    try:
        os.close(fd)
    except:
        pass
    try:
        os.remove(temp_filename)
    except:
        pass
    print temp_filename
    return  temp_filename


def get_slope_aspect_gdal(dem_file):
    temp_slope=get_temp_file(".tif")
    temp_aspect=get_temp_file(".tif")
    slope_proc=subprocess.Popen([GDALDEM,"slope",dem_file,temp_slope,"-compute_edges","-alg","ZevenbergenThorne"])
    aspect_proc=subprocess.Popen([GDALDEM,"aspect",dem_file,temp_aspect,"-zero_for_flat","-compute_edges","-alg","ZevenbergenThorne"])
    slope_proc.wait()
    aspect_proc.wait()
    slope_array,_,_=read_dem_grid(temp_slope)
    slope_array=numpy.deg2rad(slope_array)
    aspect_array,_,_=read_dem_grid(temp_aspect)
    aspect_array=numpy.deg2rad(aspect_array)
    os.unlink(temp_slope)
    os.unlink(temp_aspect)
    return slope_array,aspect_array

def cart2pol(x, y, units='deg'):
    """Convert from cartesian to polar coordinates
     **usage**:
         theta, radius = cart2pol(x, y, units='deg')
     units refers to the units (rad or deg) for theta that should be returned"""
    radius = numpy.sqrt(x**2 + y**2)
    theta = numpy.arctan2(y, x)
    if units in ['deg', 'degs']:
        theta = theta * 180 / numpy.pi
    return theta, radius
def get_ders(dem_file):
    dem,_,_=read_dem_grid(dem_file)
    dx=0.5
    #print "ders dx",dx
    fy, fx = numpy.gradient(dem, dx, dx)
    asp,grad=cart2pol(fy,fx,'rad')
    grad=numpy.arctan(grad) #steepest slope
    asp=asp*-1; # convert asp to increase going counterclockwise

    #Converting to 0 - 2*pi
    asp=asp+(asp<0)*(pi*2)
    return grad,asp



def make_location(longitude,latitude,altitude):
    return Location(longitude,latitude,altitude)

if use_gdal:
    read_dem_grid=read_dem_grid_gdal
else:
    read_dem_grid=read_tiffile

if use_gdal:
    get_slope_aspect=get_slope_aspect_gdal
else:
    get_slope_aspect=get_ders