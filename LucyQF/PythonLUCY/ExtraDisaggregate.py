# Performs supplementary spatial disaggregation of GQF outputs.
# Identifies relationships between two layers: A set of gridded land cover fractions and the QGF output grid
# Saves dict that summarises this relationship so that disaggregation can occur
import os
try:
    import pandas as pd
except:
    pass

from DataManagement.spatialHelpers import openShapeFileInMemory, populateShapefileFromTemplate, disaggregate_weightings, intersecting_amounts, reprojectVectorLayer, feature_areas, shapefile_attributes, intOrString, reprojectVectorLayer_threadSafe
from qgis.core import QgsSpatialIndex

def ExtraDisaggregate(modelOutAreas, landCoverData, landCoverGrid, landCoverWeights, modelOutputIdField, gridIdField):
    '''
    :param modelOutAreas: Path to shapefile corresponding to model output areas
    :param landCoverGrid:  str: Path to shapefile containing polygon grid (from UMEP)
    :param landCoverData:  str: Path to land cover data file (CSV) corresponding to landCoverGrid (from UMEP)
    :param landCoverWeights: Dict of weightings summing contribution from
    ["paved", "buildings", "evergreentrees", "decidioustrees", "grass", "baresoil", "water"] (cols)
    to ['building', 'transport', 'metabolism'] (rows)
    :param idField: Field of the shapefile to use as unique identifier (must be present)
    :returns weightings: dict {component (building/transport/metabolism: {outputId : {inputId: weight}}}
    '''

    if not os.path.exists(landCoverGrid):
        raise IOError('Specified land cover grid: ' + str(landCoverGrid) + ' does not exist')

    if not os.path.exists(landCoverData):
        raise IOError('Specified land cover data file: ' + str(landCoverData) + ' does not exist')

    # Headings: Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water
    coverages = pd.read_csv(landCoverData, delim_whitespace=True, index_col=0, header=0)

    # Calculate weightings to use for building, transport and metabolic components
    # based on values in text file and their importance in Parameters object
    weightings = pd.DataFrame(index=coverages.index, columns=['building', 'transport', 'metabolism'])
    weightings[:][:] = 0.0

    for f in coverages.columns:
        weightings['building'] += coverages[f] * landCoverWeights[f.lower()]['building']
        weightings['transport'] += coverages[f] * landCoverWeights[f.lower()]['transport']
        weightings['metabolism'] += coverages[f] * landCoverWeights[f.lower()]['metabolism']
    outputLayer = populateShapefileFromTemplate(weightings, gridIdField, landCoverGrid)
    # Get areas of input shapefile intersected by output shapefile, and proportions covered, and attribute vals

    # Reproject output layer so both in same CRS
    outputEpsg = int(outputLayer.dataProvider().crs().authid().split(':')[1])
    modelOutAreas = reprojectVectorLayer_threadSafe(modelOutAreas, outputEpsg)
    modelLayer = openShapeFileInMemory(modelOutAreas)
    # Create spatial index: assume input layer has more features than output
    inputIndex = QgsSpatialIndex()

    # Determine which input features intersect the bounding box of the output feature,
    # then do a real intersection.
    # Spatial index
    for feat in modelLayer.getFeatures():
        inputIndex.insertFeature(feat)
    intersectedAmounts = intersecting_amounts([], inputIndex, modelLayer, outputLayer, modelOutputIdField, gridIdField)
    weights = disaggregate_weightings(intersectedAmounts, outputLayer, ['building', 'transport', 'metabolism'], {}, gridIdField)
    outputLayer = None
    modelLayer = None
    inputIndex = None
    modelOutAreas = None

    return (intersectedAmounts, weights)


def performDisaggregation(layerToDisaggregate, idField, fieldsToDisaggregate, weightingType, weightings):
    '''
    Perform re-distribution of shapefile values based either metabolism, transport or building presence
    :param layerToDisaggregate:  QgsVectorLayer to disaggregate.
    :param idField:  Str: Field name of layerToDisaggregate contining unique IDs
    :param fieldsToDisaggregate:  list of Str: Field name(s) of layerToDisaggregate contining numeric data to disaggregate
    :param weightingType: Weighting to use for disaggregation: ['transport', 'metabolism', 'building']
    :return: Disaggregated layer
    '''

    if type(fieldsToDisaggregate) is not list:
        fieldsToDisaggregate = [fieldsToDisaggregate]

    validTypes = ['metabolism', 'transport', 'building']
    # Select successfully identified output areas
    if weightingType not in validTypes:
        raise ValueError('Invalid type selected. Must be one of ' + str(validTypes))

    # get area of each feature, using names rather than feature IDs
    # Build data frame of what to actually disaggregate
    areas = pd.Series(feature_areas(layerToDisaggregate))
    atts = shapefile_attributes(layerToDisaggregate)
    areaNames = atts[idField]
    areas.index = map(intOrString, areaNames[areas.index])
    atts.index =  map(intOrString, areaNames[atts.index])
    atts = atts[fieldsToDisaggregate] # Data frame of row:input_id, col:parameter and data = quantity to disagg

    # Apply disaggregation to features
    result = pd.DataFrame(index=weightings[weightingType].keys(), columns=atts.columns)
    for oa in weightings[weightingType].keys():
        vals = pd.Series(weightings[weightingType][oa]) # Series of input_id:weighting
        result.loc[oa] = atts.loc[vals.index].transpose().multiply(vals).transpose().sum() # Produces a data frame of the weighted contribution from each input ID, then does col sums

    return result

def performSampling(layerToSample, idField, fieldsToSample, intersectedAmounts):
    '''
    Perform sampling (not disaggregation) of shapefile values based either metabolism, transport or building presence
    :param layerToSample:  QgsVectorLayer to disaggregate.
    :param idField:  Str: Field name of layerToDisaggregate contining unique IDs
    :param fieldsToSample:  list of Str: Field name(s) of layerToDisaggregate contining numeric data to sample
    :param intersectedAmounts: Dict of intersected amounts from intersecting_amounts
    :return: Resampled layer
    '''
    if type(fieldsToSample) is not list:
        fieldsToSample = [fieldsToSample]

    # Build data frame of what to actually sample
    atts = shapefile_attributes(layerToSample)
    areaNames = atts[idField]
    atts.index =  map(intOrString, areaNames[atts.index])
    atts = atts[fieldsToSample] # Data frame of row:input_id, col:parameter and data = quantity to disagg

    # Sample from features
    result = pd.DataFrame(index=intersectedAmounts.keys(), columns=fieldsToSample)
    for oa in intersectedAmounts.keys():
        rawData =intersectedAmounts[oa]
        numEntries = len(rawData.keys())

        if numEntries == 0:
            continue
        elif numEntries == 1:
            inputId = rawData.keys()[0]
        elif numEntries > 1:
            area_info = pd.DataFrame(rawData).transpose()
            # Take attribute from input area that most intersects the output area
            if 'amountIntersected' not in area_info.columns:
                continue
            inputId = area_info.sort('amountIntersected', ascending=False).index[0]
        for field in fieldsToSample:
            result[field].loc[oa] = atts[field].loc[inputId] # Produces a data frame of the weighted contribution from each input ID, then does col sums

    return result
