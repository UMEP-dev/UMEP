# Wrapper that kicks off the model run and can translate outputs to polygons from shapefile template
import Calcs3
import os
import string
import numpy as np
from osgeo import ogr, osr

from spatialHelpers import *
from AllParts import getQFComponents
from Config import Config
from Params import Params

if __name__ == "__main__":
    config = Config()
    config.loadFromNamelist('V32_Input.nml') # Model config
    params = Params('parameters.nml') # Model params (not the same as input data)
    outs = Calcs3.mostcalcs(config, params)
    print outs

    # if __name__=='__main__':
    # Match spatialdomain to a shapefile, and specify the ID column so that outputs can be linked to areas
    # Paths relative to main.py
    shapefiles = {}
    shapefiles['LAData'] = {'file': 'statistical-gis-boundaries-london/ESRI/London_Borough_Excluding_MHW.shp',
                            'primaryKey': 'GSS_CODE'}
    shapefiles['Gridkm2Data'] = {'file': 'Shapefile_Grid1000x1000/Grid1000x1000m2.shp', 'primaryKey': 'Gr1000Code'}
    shapefiles['Grid200Data'] = {'file': 'Shapefile_Grid200x200/Grid200x200m2.shp', 'primaryKey': 'Gr200Code'}

    # Some need working out
    shapefiles['GORData'] = ''
    shapefiles['MLSOAData'] = ''
    shapefiles['LLSOAData'] = ''
    shapefiles['OAData'] = ''

    components = getQFComponents()

    # TODO: Convert outs to pandas so labels automatic
    for i in range(0, outs['Data'].shape[2]):
        try:
            to_shapefile(shapefiles[outs['SpatialDomain']]['file'],  '1greaterQF_' + str(i) + '.shp',   outs['Data'][:, :, i], components, outs['ID'], shapefiles[outs['SpatialDomain']]['primaryKey'])  # TODO: Loop over each time bin
        except Exception, e:
            print str(e)
