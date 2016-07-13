# Clips/samples an input shapefile full of values to produe a new shapefile full of values
# As it's for GreaterQF translation, weighted means of areas within clipping area is calculated for
# all fields
# Assumes that the first field of a shapefile is a unique ID for the geometry
import os
import string
import numpy as np
from osgeo import ogr, osr
from main import * # TODO: hive this into something better
import json

if __name__=='__main__':

    inputData = 'c:/testOutput/greaterQF_0.shp' # Input shapefile to be clipped
    templateInput = 'C:/Users/pn910202/Desktop/polyGrid.shp'
    outputFile = 'clipped2.shp'
    newLayerName = 'greaterQF_sampled'
    inShp = loadShapeFile(inputData)

    inLayer = inShp.GetLayer()

    template = loadShapeFile(templateInput)
    templateLayer = template.GetLayer()

    outShp = initializeShapefile(outputFile)
    outLayer = outShp.CreateLayer(newLayerName,
                                  templateLayer.GetSpatialRef(),
                                  geom_type=templateLayer.GetGeomType())

    # Coordinate transform from input to output
    # Assume input is EPSG 27700 (British National Grid)
    inputSpatRef = osr.SpatialReference()
    inputSpatRef.ImportFromEPSG(27700)
    outputSpatRef = templateLayer.GetSpatialRef()
    coordTransform = osr.CoordinateTransformation(inputSpatRef, outputSpatRef)

    # Copy the list of fields (includes greaterQF output fields) from input layer to output layer
    cloneFields(outLayer, inLayer.GetLayerDefn())

    #  Transform input data polygons to output coordinate system
    # This is a copy so must be in the same order as the input polygons
    inGeoms = []
    for j in range(0, inLayer.GetFeatureCount()):
        ftr=inLayer.GetFeature(j)
        geor = ftr.GetGeometryRef().Clone()
        geor.Transform(coordTransform)
        inGeoms.append(geor)

    # Cycle over output polygons, doing spatial intersections to establish relation between polygons
    # Only needs doing once for a given input and output combo so store the results.
    # Can't copy OGR geometries as not python objects, so can't do functions :(

    areas = {} # Dictionary {outputPolygonIndex: {inputPolygonIndex:areaIntersected}}

    for i in range(0, templateLayer.GetFeatureCount()):
        outFtr = templateLayer.GetFeature(i)
        outGeo = outFtr.GetGeometryRef()
        # Get indices of input geometries that are at all intersected by outgeo
        # Get area of each intersection
        result = {} # Dictionary of input polygon indices:area intersected within outGeo
        for j in range(0, len(inGeoms)):
            inGeo = inGeoms[j]
            a = outGeo.Intersection(inGeo).Area()

            if a > 0:  # No point including areas with no area
                result[j]=a

        areas[i] = result

    with open('InputData/UrbanfluxesTo1kmMapping.json', 'w') as outfile:
        json.dump(areas, outfile)
