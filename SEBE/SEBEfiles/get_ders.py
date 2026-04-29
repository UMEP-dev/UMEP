from __future__ import division
from __future__ import print_function

try:
    from osgeo import gdal, gdal_array
    from osgeo.gdalconst import GDT_Float64,GDT_Float32,GDT_UInt32,GDT_UInt16,GDT_Byte
except:
    use_gdal=False
else:
    use_gdal=True

import numpy
import subprocess, os
import tempfile
from math import pi, sin
from ..data_io.data_io import read_dem_grid

GDALDEM=r"gdaldem"

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
    # fix_print_with_import
    print(temp_filename)
    return temp_filename

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
    asp=asp*-1 # convert asp to increase going counterclockwise

    #Converting to 0 - 2*pi
    asp=asp+(asp<0)*(pi*2)
    return grad,asp

if use_gdal:
    read_dem_grid=read_dem_grid
else:
    read_dem_grid=read_tiffile


if use_gdal:
    get_slope_aspect=get_slope_aspect_gdal
else:
    get_slope_aspect=get_ders