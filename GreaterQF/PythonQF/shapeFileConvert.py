# Takes the JSON mappings between shapefiles that were done by shapefileClip.py
# and does the spatial averaging

import os
import string
import numpy as np
from osgeo import ogr, osr
from spatialHelpers import *
import json

if __name__=='__main__':

    inputData = 'c:/testOutput/greaterQF_0.shp' # Input shapefile to be clipped
    templateInput = 'C:/Users/pn910202/Desktop/polyGrid.shp'
    outputFile = '3Aclipped2.shp'
    newLayerName = 'greaterQF_sampled'

    inShp = loadShapeFile(inputData)
    inLayer = inShp.GetLayer()

    template = loadShapeFile(templateInput)
    templateLayer = template.GetLayer()
    templateLayerDef = templateLayer.GetLayerDefn()

    outShp = initializeShapefile(outputFile)
    outLayer = outShp.CreateLayer(newLayerName,
                                  templateLayer.GetSpatialRef(),
                                  geom_type=templateLayer.GetGeomType())
    outLayerDef = outLayer.GetLayerDefn()

    # Coordinate transform from input to output
    # Assume input is EPSG 27700 (British National Grid)
    inputSpatRef = osr.SpatialReference()
    inputSpatRef.ImportFromEPSG(27700)
    outputSpatRef = templateLayer.GetSpatialRef()
    coordTransform = osr.CoordinateTransformation(inputSpatRef, outputSpatRef)

    # Copy the list of fields (includes greaterQF output fields) from input layer to output layer
    initialFieldCount = cloneFields(outLayer, inLayer.GetLayerDefn())
    # We know the QF output should be [somestuff, somestuff, QF compt1, QF compt2...]
    componentLabels = getQFComponents()

    with open('mappings.json', 'r') as infile:
        mapping = json.load(infile)
        # Ensure keys are ints rather than strings
        mapping2 = {int(k):mapping[k] for k in mapping.keys()}

    averaged = {}

    for i in range(initialFieldCount-len(componentLabels)+1, len(componentLabels)+1):
        averaged[i] = spatialAverageField(mapping2, i, inLayer) # Key matches field index in shapefile

    # Build shapefile features

    for m in range(0, templateLayer.GetFeatureCount()):
        orig_feature = templateLayer.GetFeature(m)
        out_feature = ogr.Feature(outLayer.GetLayerDefn())
        out_feature.SetGeometry(orig_feature.GetGeometryRef().Clone())

        for j in range(initialFieldCount-len(componentLabels)+1, len(componentLabels)+1):
            # Set fields
            print outLayerDef.GetFieldDefn(j).GetNameRef()
            out_feature.SetField(outLayerDef.GetFieldDefn(j).GetNameRef(),
                                 averaged[j][m])

        outLayer.CreateFeature(out_feature) # Copy existing feature

    outShp.Destroy()