from spatialHelpers import *
from qgis.core import QgsField, QgsVectorLayer, QgsSpatialIndex, QgsMessageLog, QgsCoordinateReferenceSystem, QgsCoordinateTransform
import processing

from PyQt4.QtCore import QVariant, QSettings
try:
    import pandas as pd
    import numpy as np
except:
    pass

import os
from datetime import datetime as dt
import tempfile
from LookupLogger import LookupLogger


class SpatialTemporalResampler:
    # Class that takes spatial data (QgsVectorLayers), associates them with a time and
    # allows them to be spatially resampled to output polygons based on attribute values
    # Also supports a single value for all space via same interface
    # Data can be queried in a tabular way via Pandas data frames

    def __init__(self, logger=LookupLogger()):
        '''
        :param logger: LookupLogger object (optional) to record the results of disaggregations and lookups
        '''
        self.logger = logger
        # Set up output shapefile fields
        self.templateShapefile = None
        self.templateEpsgCode = None
        self.templateIdField = None
        self.featureMapper = None # Mapping from desired feature id : actual feature ID (dict) for referencing use
        self.outputLayer = None  # actual qgsVectorLayer
        # "raw" data fields
        self.dataLayers = None  # pd.Series of resampled QgsVectorLayer objects, or single numbers, indexed by time. Wm-2
        self.attributeTables = None # pd.Series of data frames that each contain a copy of the relevant dataLayer's data. Improves performance when looking up values.
        self.attribute = None  # pd.series of strings, indexed by time, that indicate which QgsVectorLayer field to use for the variable of interest
        self.areas = None # Area of each polygon to save having to do it on the fly each time

    def setOutputShapefile(self, shapefile, epsgCode, id_field):
        ''' Output polygons that will be produced. If inputs are different polygons, result will be area-weighted mean of intersected input polygon(s)
                shapefile: str OR QgsVectorLayer: The shapefile to use
                epsgCode: numeric EPSG code of shapefile coord system. This is needed to prevent popups asking the same
                id_field: The field of the shapefile that acts as a unique identifier for each feature.'''

        self.templateIdField = id_field
        self.templateEpsgCode = int(epsgCode)

        if type(shapefile) in [str, unicode]:
            if not os.path.exists(shapefile):
                raise ValueError('Shapefile: ' + shapefile + ' does not exist')
                    # Try and load a copy of the shapefile into memory. Allow explosion if fails.

            self.outputLayer = openShapeFileInMemory(shapefile, targetEPSG=self.templateEpsgCode, label='Template layer')

        if type(shapefile) is QgsVectorLayer:
            self.outputLayer = shapefile

        # Ensure the ID field exists
        fields = get_field_names(self.outputLayer)
        if id_field not in fields:
            raise ValueError('There is no ID field called "' + str(id_field) + '" in the output shapefile. Please check that the data sources file is correct.')

        # Refer to features by an ID in the shapefile attributes rather than (numeric) feature ID, if desired
        self.templateIdField = id_field
        # Create mapping from real (numeric) feature ID to desired (string) feature ID
        a = shapefile_attributes(self.outputLayer)[id_field]

        self.featureMapper = pd.Series(index = a.index, data = map(intOrString, a.values))
        # record what was used to label features
        if self.logger is not None:
            self.logger.addEvent('Disagg', None, None, None, 'Labelling features using ' + id_field + ' for ' + str(shapefile))

        # Record area of each polygon and label as the user desires
        self.areas = pd.Series(feature_areas(self.outputLayer))
        self.areas.index = self.featureMapper[self.areas.index]

    def getOutputShapefile(self):
        return self.outputLayer

    def getOutputFeatureIds(self):
        return shapefile_attributes(self.outputLayer).keys()

    def dealWithSingleValue(self, value, startTime, attributeToUse):
        ''' Create a QgsVectorLayer based on self.outputLayer with field attributeToUse the same value all the way through '''

        if type(startTime) is not type(dt.now()):
            raise ValueError('Start time must be a DateTime object')

        if startTime.tzinfo is None:
            raise ValueError('Start time must have a time zone attached')

        try:
            value = float(value)
        except:
            raise ValueError('Value must be float() or convertible to a float()')
        #self.logger.addEvent('Disagg', None, None, None, 'Single value given for layer: Assigning this value to all features')

        # Create a layer with all entries set to the chosen vanlue
        nl = duplicateVectorLayer(self.outputLayer, targetEPSG=self.templateEpsgCode)
        nl = addNewField(nl, attributeToUse, initialValue=value)
        self.updateLayers([attributeToUse], nl, startTime)
        return nl

    def dealWithVectorLayer(self, shapefileInput, epsgCode, startTime, attributeToUse, weight_by, inputIdField):
        ''' Loads, resamples and populates object with an input vector layer for use when needed
        :param shapefileInput:  Filename of shapefile to be (dis)aggregated
        :param epsgCode: EPSG code of vector layer
        :param startTime: datetime() object: the date of the period represented by this shapefile's data. Time ignored.
        :param attributeToUse: the field(s)/attribute(s) of the shapefile containing the quantity of interest (this gets disaggregated)
        :param inputIdField: the field/attribute of the input shapefile containing a unique identifier for each feature.
        :param weight_by:  Field/attribute of the INPUT *AND* OUTPUT shapefile by which to weight disaggregated values.
                                     If field present in input shapefile, it is assumed to be the aggregated total. If not present,
                                     total is aggregated from the output shapefile, with consideration to intersected areas given.
                                     If no field specified, then intersected area used.
        :return: QgsVectorLayer that was added'''

        if self.outputLayer is None:
            raise Exception('Output shapefile must be set before adding any input vector layers')

        if type(startTime) is not type(dt.now()):
            raise ValueError('Start time must be a DateTime object')

        if startTime.tzinfo is None:
            raise ValueError('Start time must have a timezone attached')

        if type(shapefileInput) not in [str, QgsVectorLayer]:
            raise ValueError('Shapefile input (' + str(shapefileInput) + ') is not a string or QgsVectorLayer')

        if inputIdField is None:
            raise ValueError('ID field for input shapefile must be specified')

        # If shapefileInput is a QgsVectorLayer, then assume it is already in correct EPSG
        if type(shapefileInput) is str:
            if not os.path.exists(shapefileInput):
                raise ValueError('Shapefile  (' + str(shapefileInput) + ') does not exist')

            # If the input layer isn't the same projection as the output layer, then produce a copy that's the right projection and use that instead
            reprojected = False
            if int(epsgCode) != self.templateEpsgCode:
                dest = reprojectVectorLayer_threadSafe(shapefileInput, self.templateEpsgCode) # This creates a temp file
                shapefileInput = dest
                reprojected = True

            # Load the layer
            try:
                vectorLayer = openShapeFileInMemory(shapefileInput, targetEPSG=self.templateEpsgCode)
            except Exception, e:
                raise ValueError('Could not load shapefile at ' + shapefileInput)

            if reprojected:
                try:
                    os.remove(dest) # Delete the temp file
                except:
                    pass

        else:
            vectorLayer = shapefileInput

        # Resample layer
        if type(attributeToUse) is not list:
            attributeToUse = [attributeToUse]

        resampled = self.resampleLayer(vectorLayer, attributeToUse, weight_by, inputIdField)

        self.updateLayers(attributeToUse, resampled, startTime)
        vectorLayer = None # we are done with this
        return resampled

    def injectInput(self, shapefileInput, epsgCode, attributeToUse, startTime):
        ''' Inject a shapefile previously created by this object back in so no disaggregation has to happen
        :param shapefileInput:  Filename of shapefile to be (dis)aggregated
        :param epsgCode: EPSG code of vector layer
        :param startTime: datetime() object: the date of the period represented by this shapefile's data. Time ignored.
        :param attributeToUse: the field(s)/attribute(s) of the shapefile containing the quantity of interest
        :return: QgsVectorLayer that was added'''

        if self.outputLayer is None:
            raise Exception('Output shapefile must be set before adding any input vector layers')

        if type(startTime) is not type(dt.now()):
            raise ValueError('Start time must be a DateTime object')

        if startTime.tzinfo is None:
            raise ValueError('Start time must have a timezone attached')

        if type(shapefileInput) not in [str, unicode]:
            raise ValueError('Shapefile input (' + str(shapefileInput) + ') is not a string filename')

        if not os.path.exists(shapefileInput):
            raise ValueError('Shapefile  (' + str(shapefileInput) + ') does not exist')

        # Load the layer straight from disk as we won't be making any modifications to it
        try:
            vectorLayer = loadShapeFile(shapefileInput)
        except Exception, e:
            raise ValueError('Could not load shapefile at ' + shapefileInput)

        if type(attributeToUse) is not list:
            attributeToUse = [attributeToUse]
        self.updateLayers(attributeToUse, vectorLayer, startTime)
        return vectorLayer

    def updateLayers(self, attributeToUse, layer, startTime):
        # Places the vector layer and its attributes into pandas series
        # Extract attributes table so it doesn't have to be done later
        satts = shapefile_attributes(layer)
        # Make sure table is indexed by what the user wanted
        # Ensure that the objective ID field is used rather than feature ID, as the latter tends to shift by 1 sometimes

        # ID field should be the same for both input layer and the one being considered, as both have been disaggregated
        # using the output layer

        satts.index = map(intOrString, satts[self.templateIdField].loc[satts.index.tolist()])

        # Replace any QNullVariants with pd.nan
        if self.dataLayers is None:
            # Instantiate new time series of vector layers, make a copy of attributes table and record which attribute(s) are of interest
            self.dataLayers = pd.Series([layer], index=[startTime])
            self.attributeTables = pd.Series([satts.copy()], index=[startTime])
            self.attribute = pd.Series([attributeToUse], index=[startTime])
        else:
            # Append to existing time series, and ensure time series still chronological
            self.dataLayers[startTime] = layer
            self.dataLayers = self.dataLayers.sort_index()
            # Extract attributes table
            self.attributeTables[startTime] = satts.copy()
            self.attributeTables = self.attributeTables.sort_index()
            # Record attribute(s) of interest
            self.attribute[startTime] = attributeToUse
            self.attribute = self.attribute.sort_index()


    #def getValueForFeatureId(self, attribute, featureId, layer):
    #    # Returns the value of the specified <<attribute>> (string) for a QgsVectorLayer <<layer>>
    #    # for featureId in that layer. Any wrongness causes an exception
    #    return shapefile_attributes(layer[attribute].loc[featureId])

    def getTableForDate(self, requestDate):
        ''' Return pandas data frame of values for each feature ID as of the requested datetime '''

        if type(requestDate) is not type(dt.now()):
            raise ValueError('Request date must be DateTime object')

        if requestDate.tzinfo is None:
            raise ValueError('Request datetime must have a timezone attached')

        layer_idx = self.attributeTables.index[0] if self.attributeTables.index.asof(requestDate) is np.nan else self.attributeTables.index.asof(requestDate)
        var_idx = self.attribute.index[0] if self.attribute.index.asof(requestDate) is np.nan else self.attribute.index.asof(requestDate)

        tbl = self.attributeTables[layer_idx]
        attrib = self.attribute[var_idx]

        # self.logger.addEvent('LayerLookup', requestDate.date(), layer_idx.date(), attrib,
        #                      'Looked up ' + str(attrib) + ' in vector layer attributes for ' + requestDate.strftime('%Y-%m-%d') + '. Gave data for ' + str(layer_idx.strftime('%Y-%m-%d')))
        # toc = dt.now()
        # print 'Time taken for spatial lookup:' + str((toc-tic).microseconds/1000) + ' sec'
        # Just return the field(s) of interest
        return tbl[attrib]

    def getLayerForDate(self, requestDate):
        ''' Return resampled layer or value for a given date, and the attribute of interest (tuple) '''
        if type(requestDate) is not type(dt.now()):
            raise ValueError('Request date must be DateTime object')

        if requestDate.tzinfo is None:
            raise ValueError('Request datetime must have a timezone attached')

        layer_idx = self.dataLayers.index[0] if self.dataLayers.index.asof(requestDate) is np.nan else self.dataLayers.index.asof(requestDate)
        var_idx = self.attribute.index[0] if self.attribute.index.asof(requestDate) is np.nan else self.attribute.index.asof(requestDate)

        layer = self.dataLayers[layer_idx]
        attrib = self.attribute[var_idx]
        if (len(attrib)==1) and (type(attrib) is list): # More than one attrib can be returned, but return singleton if it's a list of 1
            attrib = attrib[0]

        # Record which shapefile was provided for this date
        #self.logger.addEvent('LayerLookup', requestDate.date(), layer_idx.date(), 'Not sure of param', 'Looked up shapefile for requestdate and returned one for actualDate')

        if type(layer) is not type(QgsVectorLayer()):
            # This is a single value. Return a layer populated with it
            newLayer = duplicateVectorLayer(self.outputLayer, targetEPSG=self.templateEpsgCode)
            # Add a field and pre-populate it with the same value always
            newLayer = addNewField(newLayer, attrib, initialValue=layer)
            return (newLayer, attrib)
        else:
            # Return the existing resampled layer
            return (layer, attrib)

    def getOutputFeatureAreas(self):
        # Returns a pandas array of output feature areas in m2
        areas = pd.Series(feature_areas(self.outputLayer))
        areas.index = self.featureMapper[areas.index]
        return areas

    def getAreas(self):
        # Return the area of each feature in square metres
        return self.areas

    def resampleLayer(self, inputLayer, fieldsToSample, weight_by, inputIdField):
        ''' Disaggregates the polygon properties named in <fieldsToSample> from <inputLayer> at self.outputLayer features
        :param qgsVectorLayer with data to disaggregate:
        :param List of fields that should be downscaled spatially:
        :param Attribute of the OUTPUT shapefile by which to weight the resampled values that fall in the same input feature.
        *** value extracted from each inputLayer polygon will be multiplied by the fraction of that polygon intersected
        :param inputIdField: Field name of INPUT layer that contains unique identifiers for each entry
        :return: resampled layer
        '''
        # Make sure the fields to sample are actually present in the file. Throw exception if not
        extantFields = get_field_names(inputLayer)
        missing = list(set(fieldsToSample).difference(extantFields))
        if len(missing) > 0:
            raise ValueError('The input shapefile %s is missing the following attributes:  %s'%(str(inputLayer.dataProvider().dataSourceUri().uri()), str(fieldsToSample)))

        # Create spatial index: assume input layer has more features than output
        inputIndex = QgsSpatialIndex()

        # Determine which input features intersect the bounding box of the output feature,
        # then do a real intersection.
        for feat in inputLayer.getFeatures():
            inputIndex.insertFeature(feat)

        # If the inputLayer and outputLayer spatial units are the same, then disaggregation does not need to happen.
        if sameFeatures(inputLayer, self.outputLayer):
            return inputLayer

        # record what was used to label features
        #if self.logger is not None:
        #    self.logger.addEvent('Disagg', None, None, None, 'Resampling fields ' + str(fieldsToSample) + ', weighting by ' + str(weight_by))

        # Clone the output layer (populate this with [dis]aggregated data)
        newShapeFile = duplicateVectorLayer(self.outputLayer, targetEPSG=self.templateEpsgCode)
        # Keep track of which field name has which field index

        fieldIndices = {}
        newShapeFile.startEditing()
        existingFields = get_field_names(self.outputLayer)
        numFields = len(newShapeFile.dataProvider().fields())
        numFieldsAdded = 0

        for field in fieldsToSample:
            if field in existingFields:
                fieldIndices[field] = existingFields.index(field)
            else:
                newShapeFile.addAttribute(QgsField(field, QVariant.Double))
                newShapeFile.updateFields()
                fieldIndices[field] = numFields + numFieldsAdded
                numFieldsAdded += 1

        newShapeFile.commitChanges()
        newShapeFile.updateExtents()

        # Get read-across between so feature ID can be ascertained from name according to chosen ID field
        t = shapefile_attributes(newShapeFile)[self.templateIdField]
        def intorstring(x):
            try:
                return int(x)
            except:
                return str(x)

        readAcross = pd.Series(index=map(intorstring, t.values), data=map(intorstring, t.index))
        t = None

        # Get areas of input shapefile intersected by output shapefile, and proportions covered, and attribute vals
        intersectedAreas = intersecting_amounts(fieldsToSample, inputIndex, inputLayer, newShapeFile, inputIdField, self.templateIdField)

        # Work out disaggregation factor baed on area intersected
        # Use "big" totals of weightings if the same attribute present in the input data file
        total_weightings = {} # Assume no "big" totals are available
        #if type(weight_by) not in [str, unicode]:
        #    raise ValueError('Weighting attribute name not a string or unicode variable')

        if weight_by in get_field_names(inputLayer):
            atts = shapefile_attributes(inputLayer)[weight_by]
            total_weightings = {weight_by:{idx:atts[idx] for idx in atts.index}}
            self.logger.addEvent('Disagg', None, None, None, 'Found attribute ' + str(weight_by) + ' in shapefile to be disaggregated. '
                                                                                                   'Assuming this is the sum of '+ str(weight_by) + ' in the output features')
        else:
            # It's not in the input file: Record what happened in the log
            if weight_by is not None:
                self.logger.addEvent('Disagg', None, None, None, 'Total of Weighting Attribute ' + str(weight_by) + ' not found in original shapefile, so calculating it from the output areas')
            else:
                self.logger.addEvent('Disagg', None, None, None, 'No weighting attribute specified so disaggregated weighting by intersected feature area only')

        if weight_by is None:
            disagg = disaggregate_weightings(intersectedAreas, newShapeFile, weight_by, total_weightings, self.templateIdField)['_AREA_']
        else:
            disagg = disaggregate_weightings(intersectedAreas, newShapeFile, weight_by, total_weightings, self.templateIdField)[weight_by]

        # Select successfully identified output areas

        newShapeFile.setSelectedFeatures(list(readAcross[disagg.keys()]))

        selectedOutputFeatures = newShapeFile.selectedFeatures()
        newShapeFile.startEditing()
        # Apply disaggregation to features
        for outputFeat in selectedOutputFeatures:  # For each output feature
            # Select the relevant features from the input layer
            area_weightings = {inputAreaId: disagg[outputFeat[self.templateIdField]][inputAreaId] for inputAreaId in disagg[outputFeat[self.templateIdField]].keys()}
            # Calculate area-weighted average to get a single value for each output area
            for field in fieldsToSample:
                # The values to disaggregate in all regions touching this output feature
                input_values = {inputAreaId: intersectedAreas[outputFeat[self.templateIdField]][inputAreaId][field] for inputAreaId in intersectedAreas[outputFeat[self.templateIdField]].keys()}
                # If an output area is influenced by multiple input areas, and a subset of these is invalid,
                # assign them zero
                for i in input_values.keys():
                    try:
                        input_values[i] = float(input_values[i])
                    except:
                        input_values[i] = 0
                # Combine values in all input regions touching this output feature. If disagg_weightings missed one out it's because no intersection or NULL data.
                # Any value intersecting an output area with NULL weighting will be excluded
                outputAreasToUse = set(input_values.keys()).intersection(area_weightings.keys())
                weighted_average = np.sum(np.array([input_values[in_id] * float(area_weightings[in_id]) for in_id in list(outputAreasToUse)]))

                newShapeFile.changeAttributeValue(outputFeat.id(), fieldIndices[field], float(weighted_average))

        newShapeFile.commitChanges()
        newShapeFile.setSelectedFeatures([])  # De-select all features
        return newShapeFile

    def addInput(self, input, startTime, attributeToUse, inputFieldId, weight_by=None, epsgCode=None):
        ''' Add a layer of data for a specific time. Must be QgsVectorLayer OR a float (represents all space), indexed by unique area ID.
            Unique area IDs must correspond to features in the spatial layer
            Parameters:
                # input: The QgsVectorLayer or float() object
                # epsgCode: Numeric EPSG code of layer (can be None)
                # startTime: The start of the period represented by this data (datetime() object)
                # attributeToUse: The attribute(s) (field(s)) to use as input data. Other fields will be ignored
                # inputFieldId: The attribute(s) (field(s)) that contains unique identifiers for each input field
                # weight_by: Attribute of the OUTPUT shapefile by which to weight the resampled values. '''
        if type(startTime) is not type(dt.now()):
            raise ValueError('Start time must be a DateTime object')

        if startTime.tzinfo is None:
            raise ValueError('Start time must have a timezone attached')

        if type(attributeToUse) is not list:
            attributeToUse = [attributeToUse]

        if type(input) is float:  # Assume a single value for all space
            return self.dealWithSingleValue(input, startTime, 'SINGLEVAL')

        if type(input) in ([unicode, str]):  # Assume a filename
            if epsgCode is None:
                raise ValueError('EPSG code must be provided if a shapefile is input')
            return self.dealWithVectorLayer(input, epsgCode, startTime, attributeToUse, weight_by, inputFieldId)

        if type(input) is QgsVectorLayer:
            return self.dealWithVectorLayer(input, epsgCode, startTime, attributeToUse, weight_by, inputFieldId)

        raise ValueError('Error setting input layer for ' + str(startTime) + ': input was neither string nor float')