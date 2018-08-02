from __future__ import absolute_import
from builtins import str
from builtins import map
from .spatialHelpers import *
from qgis.core import QgsField, QgsVectorLayer, QgsSpatialIndex, QgsMessageLog, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.PyQt.QtCore import QVariant

try:
    import pandas as pd
except:
    pass

from .SpatialTemporalResampler import SpatialTemporalResampler
def intorstring(x):
    try:
        return int(x)
    except:
        return str(x)

def floatorstring(x):
    try:
        return float(x)
    except:
        return str(x)

class SpatialAttributesSampler(SpatialTemporalResampler):
    # Class that takes a wide-area input polygon layer (QgsVectorLayer), such as countries in the world,
    # and maps its attributes to a different polygon layer based on where each polygon lands
    # (i.e. if 3 polygons land in england and england has colour='blue' or ID=43, they all get colour='blue' and ID=43)
    # *** No downscaling is performed *** : the attributes are just harvested. If an output polygon intersects multiple input polygons,
    # the input polygon with the largest intersected area is used.
    # Multiple input polygon layers can be used, each representing a different time period. Outputs are always in terms of the new (output)
    # polygon layer.

    def resampleLayer(self, inputLayer, fieldsToSample, weightby=None, inputIdField=None):
        ''' Samples the polygon properties named in <fieldsToSample> from <inputLayer> at self.outputLayer features
        :param inputLayer: qgsVectorLayer: Data to sample:
        :param fieldsToSample: list: List of fields that should be sampled:
        :param weightBy: Leave empty: Only here for compatibility.
        :param inputIdField: Field name of INPUT layer that contains unique identifiers for each entry
        :return: Copy of output layer with attributes sampled from
        '''

        if inputIdField is None:
            raise ValueError('Input layer ID attribute name MUST be specified')

        # Make sure the fields to sample are actually present in the file. Throw exception if not
        originalFields = get_field_names(inputLayer)
        missing = list(set(fieldsToSample).difference(originalFields))
        if len(missing) > 0:
            raise ValueError('The input shapefile is missing the following attributes: ' + str(missing))

        # Clone the output layer (populate this with [dis]aggregated data)
        newShapeFile = duplicateVectorLayer(self.outputLayer, targetEPSG=self.templateEpsgCode)

        # Keep track of which field name has which field index
        fieldIndices = {}
        newShapeFile.startEditing()
        existingFields = get_field_names(self.outputLayer)
        numFields = len(newShapeFile.dataProvider().fields())
        numFieldsAdded = 0

        for field in fieldsToSample:
            if field in existingFields: # If this field already exists in output layer, overwrite its values
                fieldIndices[field] = existingFields.index(field)
            else: # Field does not already exist in output layer -  Create a field of the same type in the new layer
                origField = inputLayer.dataProvider().fields()[originalFields.index(field)]
                newShapeFile.addAttribute(QgsField(field, origField.type()))
                newShapeFile.updateFields()
                fieldIndices[field] = numFields + numFieldsAdded
                numFieldsAdded += 1

        newShapeFile.commitChanges()
        newShapeFile.updateExtents()

        # Get read-across between so feature ID can be ascertained from name according to chosen ID field
        t = shapefile_attributes(newShapeFile)[self.templateIdField]
        readAcross = pd.Series(index=list(map(intorstring, t.values)), data=list(map(intorstring, t.index)))
        t = None

        # If the inputLayer and outputLayer spatial units are the same, then disaggregation does not need to happen.
        if sameFeatures(newShapeFile, self.outputLayer):
            newShapeFile.selectAll()
            o = shapefile_attributes(inputLayer)
            newShapeFile.selectAll()
            for outputFeat in newShapeFile.selectedFeatures():
                # Just copy the attribute(s) of interest
                for field in fieldsToSample:
                    # If an output area is influenced by multiple input areas, and a subset of these is invalid,
                    # assign them zero
                    newShapeFile.changeAttributeValue(outputFeat.id(), fieldIndices[field], floatorstring(o[field].loc[outputFeat.id()]))
        else:
            # Disaggregate to elicit the attribute(s) of interest
            # Get areas of input shapefile intersected by output shapefile, and proportions covered, and attribute vals
            intersectedAreas = intersecting_amounts_LUCY(fieldsToSample, inputLayer, newShapeFile, inputIdField, self.templateIdField)
            # Work out disaggregation factor baed on area intersected
            # Use "big" totals of weightings if the same attribute present in the input data file

            newShapeFile.setSelectedFeatures(list(readAcross[list(intersectedAreas.keys())]))
            selectedOutputFeatures = newShapeFile.selectedFeatures()
            newShapeFile.startEditing()
            # Apply disaggregation to features
            for outputFeat in selectedOutputFeatures:  # For each output feature
                # Select the relevant feature from the input layer
                # Take the input area with the largest intersected area if there is more than one to choose from
                rawData = intersectedAreas[outputFeat[self.templateIdField]]

                numEntries = len(list(rawData.keys()))
                if numEntries == 0:
                    continue
                elif numEntries == 1:
                    inputValues = list(rawData.values())[0]

                elif numEntries > 1:
                    area_info = pd.DataFrame(rawData).transpose()
                    if 'amountIntersected' not in area_info.columns:
                        continue
                    # inputValues = area_info.sort('amountIntersected', ascending=False).iloc[0].to_dict()
                    inputValues = area_info.sort_values('amountIntersected', ascending=False).iloc[0].to_dict()

                # Calculate area-weighted average to get a single value for each output area
                for field in fieldsToSample:
                    # If an output area is influenced by multiple input areas, and a subset of these is invalid,
                    # assign them zero
                    newShapeFile.changeAttributeValue(outputFeat.id(), fieldIndices[field], floatorstring(inputValues[field]))

        newShapeFile.commitChanges()
        newShapeFile.setSelectedFeatures([])  # De-select all features
        return newShapeFile
