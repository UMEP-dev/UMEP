from .spatialHelpers import *
from qgis.core import QgsField
import processing

from qgis.PyQt.QtCore import QVariant, QSettings
try:
    import pandas as pd
    import numpy as np
except:
    pass
import os
from datetime import datetime as dt
import tempfile
from .LookupLogger import LookupLogger
from .SpatialTemporalResampler import SpatialTemporalResampler

class SpatialTemporalResampler_LUCY(SpatialTemporalResampler):
    # Class that takes spatial data (QgsVectorLayers), associates them with a time and
    # allows them to be spatially resampled to output polygons based on attribute values
    # This just overrides resampleLayer() so that spatial indexes are used in a way that supports worldwide shapefiles

    def resampleLayer(self, inputLayer, fieldsToSample, weight_by, inputIdField):
        ''' Disaggregates the polygon properties named in <fieldsToSample> from <inputLayer> at self.outputLayer features
        :param qgsVectorLayer with data to disaggregate:
        :param List of fields that should be downscaled spatially:
        :param Attribute of the OUTPUT shapefile by which to weight the resampled values that fall in the same input feature.
        *** value extracted from each inputLayer polygon will be multiplied by the fraction of that polygon intersected
        :param inputIdField: Field name of INPUT layer that contains unique identifiers for each entry
        :return: resampled layer
        '''

        # If the inputLayer and outputLayer spatial units are the same, then disaggregation does not need to happen.
        if sameFeatures(inputLayer, self.outputLayer):
            return inputLayer

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

        readAcross = pd.Series(index=list(map(intorstring, t.values)), data=list(map(intorstring, t.index)))
        t = None

        # Get areas of input shapefile intersected by output shapefile, and proportions covered, and attribute vals
        intersectedAreas = intersecting_amounts_LUCY(fieldsToSample, inputLayer, newShapeFile, inputIdField, self.templateIdField)
        # Work out disaggregation factor baed on area intersected
        # Use "big" totals of weightings if the same attribute present in the input data file
        total_weightings = {} # Assume no "big" totals are available
        print('WB:' + str(weight_by))
        if weight_by in get_field_names(inputLayer):
            atts = shapefile_attributes(inputLayer)
            total_weightings = {weight_by:{intOrString(atts[inputIdField].loc[idx]):atts[weight_by].loc[idx] for idx in atts.index}}
            self.logger.addEvent('Disagg', None, None, None, 'Found attribute ' + str(weight_by) + ' in shapefile to be disaggregated. '
                                                                                                   'Assuming this is the sum of '+ str(weight_by) + ' in the output features')
        else:
            if weight_by is not None:
                self.logger.addEvent('Disagg', None, None, None, 'Total of Weighting Attribute ' + str(weight_by) + ' not found in original shapefile, so calculating it from the output areas')
            else:
                # Couldn't find the weighting attribute in the output layer
                self.logger.addEvent('Disagg', None, None, None, 'No weighting attribute specified so disaggregated weighting by intersected feature area only')

        if weight_by is None:
            disagg = disaggregate_weightings(intersectedAreas, newShapeFile, weight_by, total_weightings, self.templateIdField)['_AREA_']
        else:
            disagg = disaggregate_weightings(intersectedAreas, newShapeFile, weight_by, total_weightings, self.templateIdField)[weight_by]

        # Select successfully identified output areas
        newShapeFile.selectByIds(list(readAcross[list(disagg.keys())]))

        selectedOutputFeatures = newShapeFile.selectedFeatures()
        newShapeFile.startEditing()
        # Apply disaggregation to features
        for outputFeat in selectedOutputFeatures:  # For each output feature
            # Select the relevant features from the input layer
            area_weightings = {inputAreaId: disagg[outputFeat[self.templateIdField]][inputAreaId] for inputAreaId in list(disagg[outputFeat[self.templateIdField]].keys())}
            # Calculate area-weighted average to get a single value for each output area
            for field in fieldsToSample:
                input_values = {inputAreaId: intersectedAreas[outputFeat[self.templateIdField]][inputAreaId][field] for inputAreaId in list(intersectedAreas[outputFeat[self.templateIdField]].keys())}
                # If an output area is influenced by multiple input areas, and a subset of these is invalid,
                # assign them zero
                for i in list(input_values.keys()):
                    try:
                        input_values[i] = float(input_values[i])
                    except:
                        input_values[i] = 0

                outputAreasToUse = set(input_values.keys()).intersection(list(area_weightings.keys()))
                weighted_average = np.sum(np.array([input_values[in_id] * float(area_weightings[in_id]) for in_id in list(outputAreasToUse)]))
                newShapeFile.changeAttributeValue(outputFeat.id(), fieldIndices[field], float(weighted_average))

        newShapeFile.commitChanges()
        newShapeFile.selectByIds([])  # De-select all features
        return newShapeFile
