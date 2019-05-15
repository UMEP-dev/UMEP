# Helper methods to do spatial and shapefile-related manipulations
# amg 23/06/2016
import string
import os
try:
    import numpy as np
    import pandas as pd
except:
    pass
from qgis.core import QgsVectorFileWriter, QgsVectorLayer, QgsRasterLayer, QgsGeometry, QgsRaster, QgsRectangle, QgsPoint, QgsField, QgsFeature, QgsSpatialIndex, QgsMessageLog, NULL, QgsCoordinateReferenceSystem, QgsCoordinateTransform
# from qgis.core import QgsMapLayerRegistry, QgsSymbol, QgsGraduatedSymbolRenderer, QgsRendererRange, QgsFeatureRequest, QgsExpression, QgsDistanceArea
from qgis.core import QgsSymbol, QgsGraduatedSymbolRenderer, QgsRendererRange, QgsFeatureRequest, QgsExpression, QgsDistanceArea, QgsCoordinateTransformContext, QgsVectorLayerUtils, QgsProcessingFeedback
from qgis.analysis import QgsZonalStatistics
import processing  # qgis processing framework
# from qgis.PyQt.QtCore import QVariant, QPyNullVariant
from qgis.PyQt.QtCore import QVariant
import tempfile
# from .string_func import   lower
#
# qgs = QgsApplication(sys.argv, False)
# qgs.setPrefixPath(r"C:\Program Files (x86)\QGIS 2.18\apps\qgis-ltr", True)
# qgs.initQgis()


def reprojectVectorLayer_threadSafe(filename, targetEpsgCode):
    ''' Does the same thing as reprojectVectorLayer but in a thread safe way'''
    orig_layer = loadShapeFile(filename)
    orig_crs = orig_layer.crs()
    dest = os.path.join(tempfile.mkdtemp() + 'reprojected.shp')
    target_crs = QgsCoordinateReferenceSystem()
    target_crs.createFromUserInput('EPSG:%d' % int(targetEpsgCode))

    new_layer = QgsVectorLayer(
        "Polygon?crs=EPSG:" + str(targetEpsgCode), "temp", "memory")
    crs_transform = QgsCoordinateTransform(orig_crs, target_crs)
    out_feat = QgsFeature()

    # Copy fields
    fields = orig_layer.fields()
    new_layer.startEditing()
    new_layer.dataProvider().addAttributes(fields)
    new_layer.updateFields()
    new_layer.updateExtents()

    orig_layer.selectAll()
    for f in orig_layer.getFeatures():
        geom = f.geometry()
        geom.transform(crs_transform)
        out_feat.setGeometry(geom)
        out_feat.setAttributes(f.attributes())
        new_layer.addFeatures([out_feat])
    new_layer.updateExtents()
    new_layer.commitChanges()
    error_code, error_msg = QgsVectorFileWriter.writeAsVectorFormat(
        new_layer, dest, "CP1250", target_crs, "ESRI Shapefile")
    new_layer = None
    orig_layer = None
    out_feat = None
    crs_transform = None

    return dest


def reprojectVectorLayer(filename, targetEpsgCode):
    ''' Reprojects a shapefile to a new EPSG code using QGIS built-in algorithm
    :param filename: str: filename of shapefile to reproject
    :param targetEpsgCode: int: EPSG code of the new shapefile
    :return str: filename of reprojected shapefile (in a temporary directory)'''
    if type(filename) is not str:
        raise ValueError('Filename must be a string')

    dest = os.path.join(tempfile.mkdtemp() + 'reprojected.shp')
    # processing.runalg('qgis:reprojectlayer', filename, "EPSG:" + str(targetEpsgCode), dest)
    try:
        processing.run(
            'qgis:reprojectlayer',
            {
                'INPUT': filename,
                'TARGET_CRS': "EPSG:" + str(targetEpsgCode),
                'OUTPUT': dest,
            }
        )
    except:
        processing.run(
            'native:reprojectlayer',
            {
                'INPUT': filename,
                'TARGET_CRS': "EPSG:" + str(targetEpsgCode),
                'OUTPUT': dest,
            }
        )

    # WORKAROUND FOR QGIS BUG: qgis:reprojectvectorlayer mishandles attributes so that QLongLong data types are
    # treated as int. This means large values have an integer overrun in the reprojected layer

    # This workaround operates by opening both files and copying the attributes from the original layer into the new one
    orig_layer = loadShapeFile(filename)
    reproj_layer = loadShapeFile(dest, targetEPSG=targetEpsgCode)

    reproj_layer.startEditing()
    orig_fieldNames = {a.name(): i for i, a in enumerate(
        orig_layer.dataProvider().fields())}
    reproj_fieldNames = {a.name(): i for i, a in enumerate(
        reproj_layer.dataProvider().fields())}
    # Copy features
    for orig_feat in orig_layer.getFeatures():
        orig_id = orig_feat.id()
        for fieldName in list(orig_fieldNames.keys()):
            try:
                new_val = float(orig_feat[orig_fieldNames[fieldName]])
                reproj_layer.changeAttributeValue(
                    orig_id, reproj_fieldNames[fieldName], new_val)
            except Exception:
                continue
    reproj_layer.commitChanges()
    orig_feat = None
    reproj_layer = None
    orig_layer = None
    # END OF WORKAROUND
    return dest


def calculate_fuel_use(inputLayer, inputIdField,
                       completeInputs,
                       modelParams, age, fuelCon, roadTypeLookup,
                       modelledTypesAADTprovided, completeInputAADTprovided,
                       vAADTFields, roadTypeField, totalAADTField=None,):
    '''
    Calculate total fuel use (petrol and diesel separately) for each modelled vehicle type in each given road segment.
    :param inputLayer: QgsVectorLayer: Map of road segments that may or may not have  AADT by vehicle type or overall
    :param inputIdField: str: Name of input layer field containing unique identifiers for each road segment
    :param roadTypeField: str: the field of inputLayer that contains the road classification
    :param totalAADTField: str: field of inputLayer that contains the total AADT value (or None if not available)
    :param completeInputs: list of str: The most comprehensive list of AADT fields we are likely to get
    :param modelParams: Params() object: GreaterQF parameters
    :param age: numeric: assumed age of each vehicle so the fuel efficiency can be looed up
    :param fuelCon: FuelConsumption: Fuel consumption object
    :param roadTypeLookup: dict: links the road type names used in inputLayer to those used in model {inputLayerVersion:ourVersion}
    :param modelledTypesAADTprovided: bool: AADT in inputLayer is broken down exactly into modelledTypes
    :param completeInputAADTprovided: bool: AADT in inputLayer is broken down exactly into completeInputs
    :return: dict of {fuelUse: pandas.DataFrame of fuel use [KILOGRAMS] for each modelled vehicle type, petrol and diesel, for each feature ID,
                      names: dict of {fueltype: {vehicleType: column name in dataframe}}
    '''

    # Make sure any lengths are calculated independently of CRS
    in_a = QgsDistanceArea()
    in_a.setEllipsoid('WGS84')
    # in_a.setEllipsoidalMode(True)
    in_a.setSourceCrs(inputLayer.crs(), QgsCoordinateTransformContext())

    # Add new attributes to inputLayer into which results will go
    totalAADTAvailable = False
    if totalAADTField is not None:
        totalAADTAvailable = True

    # Make new attribute names to hold consumption attributes
    # Make a dict that links the modelled vehicle names to new field names
    dieselFields = {'motorcycle': '_FC_Dmcyc', 'artic': '_FC_Dart', 'rigid': '_FC_Drig',
                    'taxi': '_FC_Dtaxi', 'car': '_FC_Dcar', 'bus': '_FC_Dbus', 'lgv': '_FC_Dlgv'}
    petrolFields = {'motorcycle': '_FC_Pmcyc', 'artic': '_FC_Part', 'rigid': '_FC_Prig',
                    'taxi': '_FC_Ptaxi', 'car': '_FC_Pcar', 'bus': '_FC_Pbus', 'lgv': '_FC_Plgv'}

    # Get overall list of new attrib names
    consumption_attributes = list(dieselFields.values())
    consumption_attributes.extend(list(petrolFields.values()))
    fieldMap = {'diesel': dieselFields, 'petrol': petrolFields}
    modelledTypes = list(petrolFields.keys())

    # Read-across from our road classes to EuroClass road classes (used in the FuelConsumption object)
    roadAcross = {'motorway': 'motorway', 'primary_road': 'urban',
                  'secondary_road': 'urban', 'other': 'urban'}

    # Get all feature IDs
    allIds = []
    for feat in inputLayer.getFeatures():
        allIds.append(intOrString(feat[inputIdField]))
    # Results holder: a value for every combination of fuel & vehicle type for each feature ID
    newValues = pd.DataFrame(index=allIds, columns=consumption_attributes)

    # Get features for each road type
    # Unique road types that are present in shapefile
    # roadTypes = list(set(inputLayer.getValues(roadTypeField)[0]))
    roadTypes = list(
        set(QgsVectorLayerUtils.getValues(inputLayer, roadTypeField)[0]))

    for roadType in roadTypes:  # For each road type in the file
        # If we don't explicitly consider this road type as motorway, A road or B road, just consider it "other"
        if roadType not in list(roadTypeLookup.keys()):
            roadTypeOfficial = 'other'
        else:
            roadTypeOfficial = roadTypeLookup[roadType]
        inputLayer.selectAll()
        expressionText = "\"" + roadTypeField + "\" = '" + roadType + "'"
        # Select all features with this road type, then do calculations
        thisRoad = QgsFeatureRequest().setFilterExpression(expressionText)

        # Feature IDs for roads of this type
        fids = []  # Feature IDs within shapefile
        ids = []  # Feature IDs using desired naming scheme
        lkm = []
        # # convert multilinestring to linestring for later use
        # lyr_linstring = processing.runAndLoadResults(
        #     'qgis:convertgeometrytype',
        #     {
        #         'INPUT': inputLayer,
        #         'TYPE': 2, # line string
        #         'OUTPUT': 'memory:',
        #     },
        #     feedback=QgsProcessingFeedback().reportError('invalid features encountered in `qgis:convertgeometrytype` processing')
        # )
        # lyr_linstring = loadShapeFile(lyr_linstring['OUTPUT'])
        # for f in lyr_linstring.getFeatures(thisRoad):
        #     fids.append(f.id())
        #     ids.append(intOrString(f[inputIdField]))
        #     # Length of segment in km
        #     lkm.append(in_a.measureLine(f.geometry().asMultiPolyline()[0])/1000.0)

        for f in inputLayer.getFeatures(thisRoad):
            fids.append(f.id())
            ids.append(intOrString(f[inputIdField]))
            # Length of segment in km
            lkm.append(in_a.measureLine(f.geometry().asMultiPolyline()[0])/1000.0)

        inputLayer.selectByIds(fids)
        #ids = np.array(ids)
        lkm = pd.Series(index=ids, data=lkm)

        # Road type in terms of fuel consumption object
        rType_cons = roadAcross[roadTypeOfficial]
        if (not modelledTypesAADTprovided) and (not completeInputAADTprovided):
            # AADT is not broken down by vehicle type. Need to estimate AADT per vehicle type
            # Make new AADT fields with standard names
            vAADTFields = {type: type for type in modelledTypes}

            if not totalAADTAvailable:
                # Scenario 1: There is no AADT data available whatsoever.
                # Calculate this segment's AADT both from the parameters file, based solely on road type
                aadtData = pd.DataFrame(np.repeat(modelParams.roadAADTs[roadTypeOfficial], len(ids))[:, np.newaxis] *
                                        np.array(
                    modelParams.vehicleFractions[roadType]),
                    columns=modelledTypes, index=ids)
            else:
                # Scenario 2: Only total AADT is available for each segment.
                # Break this down into vehicle types using vehicle fractions in parameters file for each segment
                totalAadtData = np.array(QgsVectorLayerUtils.getDoubleValues(inputLayer,
                    totalAADTField, selectedOnly=True)[0])
                aadtData = pd.DataFrame(totalAadtData[:, np.newaxis] *
                                        np.array(
                    modelParams.vehicleFractions[roadTypeOfficial]),
                    columns=modelledTypes, index=ids)

            # Now we effectively have AADT for every modelled type, so set the flag (reduces code duplication)
            # TODO: If AADT counts are available for some road segments but not others, calculate a mean and apply this
            # Begin calculating fuel use

        alreadyCalculated = []
        if completeInputAADTprovided:

            # Scenario 4: Vehicle-specific AADT data is available in the shapefile, and breaks cars and LGVs down by fuel type
            # Car and LVG diesel and petrol AADTs available separately when complete data given
            aadtData = pd.DataFrame(columns=completeInputs, index=ids)
            for key in completeInputs:
                aadtData[key] = np.array(
                    QgsVectorLayerUtils.getDoubleValues(
                    inputLayer, vAADTFields[key], selectedOnly=True)[0])  # Populate and translate names at the same time
                # aadtData[key] = np.array(QgsVectorLayerUtils.getDoubleValues(inputLayer,vAADTFields[key], selectedOnly=True)[0])  # Populate and translate names at the same time

            # Make use of the extra detail available to us
            newValues[fieldMap['diesel']['car']].loc[ids] = aadtData['diesel_car'] * \
                lkm * \
                fuelCon.getFuelConsumption(age, 'car', rType_cons, 'diesel')
            newValues[fieldMap['petrol']['car']].loc[ids] = aadtData['petrol_car'] * \
                lkm * \
                fuelCon.getFuelConsumption(age, 'car', rType_cons, 'petrol')
            newValues[fieldMap['diesel']['lgv']].loc[ids] = aadtData['diesel_lgv'] * \
                lkm * \
                fuelCon.getFuelConsumption(age, 'lgv', rType_cons, 'diesel')
            newValues[fieldMap['petrol']['lgv']].loc[ids] = aadtData['petrol_lgv'] * \
                lkm * \
                fuelCon.getFuelConsumption(age, 'lgv', rType_cons, 'petrol')

            # Complete input data includes coaches, which will be lumped in with buses
            newValues[fieldMap['petrol']['bus']].loc[ids] = aadtData['coach'] * \
                modelParams.fuelFractions['bus']['petrol'] * lkm * \
                fuelCon.getFuelConsumption(age, 'bus', rType_cons, 'petrol')
            newValues[fieldMap['diesel']['bus']].loc[ids] = aadtData['coach'] * \
                modelParams.fuelFractions['bus']['diesel'] * lkm * \
                fuelCon.getFuelConsumption(age, 'bus', rType_cons, 'diesel')
            alreadyCalculated = ['car', 'lgv', 'bus']
        else:
            # Scenario 3: Vehicle-specific AADT data available in the shapefile, but with no fuel type specifics
            aadtData = pd.DataFrame(columns=modelledTypes, index=ids)
            for key in modelledTypes:
                aadtData[key] = np.array(QgsVectorLayerUtils.getDoubleValues(inputLayer,
                    vAADTFields[key], selectedOnly=True)[0])
            # Populate car, bus and LGV differently to above
            for fuelType in list(fieldMap.keys()):
                newValues[fieldMap[fuelType]['car']].loc[ids] = aadtData['total_car'] *\
                    modelParams.fuelFractions['car'][fuelType] *\
                    lkm *\
                    fuelCon.getFuelConsumption(
                        age, 'car', rType_cons, fuelType)

                newValues[fieldMap[fuelType]['lgv']].loc[ids] = aadtData['total_lgv'] *\
                    modelParams.fuelFractions['lgv'][fuelType] * \
                    lkm *\
                    fuelCon.getFuelConsumption(
                        age, 'lgv', rType_cons, fuelType)

            # Setting coach contribution to buses as zero lets us use "+=" in a few moments' time.
            newValues['_FC_Pbus'].loc[ids] = 0
            newValues['_FC_Dbus'].loc[ids] = 0
            alreadyCalculated = ['car', 'lgv', 'bus']

        # The remaining vehicle types all get calculated in the same way so loop over fieldMap to save on code...
        for fuelType in list(fieldMap.keys()):
            for vehType in list(fieldMap[fuelType].keys()):
                if vehType not in alreadyCalculated:
                    newValues[fieldMap[fuelType][vehType]].loc[ids] = aadtData[vehType] * \
                        modelParams.fuelFractions[vehType][fuelType] * \
                        lkm * \
                        fuelCon.getFuelConsumption(
                            age, vehType, rType_cons, fuelType)
            # Special case for bus, because coaches may already have added a contribution
            newValues[fieldMap[fuelType]['bus']].loc[ids] += aadtData['bus'] *\
                modelParams.fuelFractions['bus'][fuelType] *\
                lkm *\
                fuelCon.getFuelConsumption(age, 'bus', rType_cons, fuelType)

        inputLayer.selectByIds([])  # Deselect features ready for next loop
        # End of loop over road types
    return {'fuelUse': newValues, 'names': fieldMap}


def intersecting_amounts(fieldsToSample, inputIndex, inputLayer, new_layer, inputLayerIdField, newLayerIdField):
    ''' calculate the length/area of each input feature intersecting each output area. Also returns requested attributes of the input feature
    :param fieldsToSample: List of input shapefile fields from which to draw values
    :param inputIndex: QgsSpatialIndex of input features
    :param inputLayer: QgsVectorLayer containing the input features
    :param new_layer: QgsVectorLayer to use as output (contain polygons to intersect input features)
    :param inputLayerIdField: str name of ID field of input layer
    :param newLayerIdField: str name of ID field of output layer (names are needed for cross-referencing)
    :return Dictionary of outputAreaId:{inputFeatureId: amountIntersected}'''

    intersectedAmounts = {}

    # Ensure areas are all square metres (if SRS=WGS84 then doing geometry.area() gives square degrees)
    # when comparing across different layers. Comparing areas within the same layer don't need this
    in_a = QgsDistanceArea()
    in_a.setEllipsoid('WGS84')
    # in_a.setEllipsoidalMode(True)
    in_a.setSourceCrs(inputLayer.crs(), QgsCoordinateTransformContext())

    out_a = QgsDistanceArea()
    out_a.setEllipsoid('WGS84')
    # out_a.setEllipsoidalMode(True)
    out_a.setSourceCrs(new_layer.crs(), QgsCoordinateTransformContext())

    # Get bounding box around combined output features
    # If there are fewer than 10 input features, work out if any of them totally subsume the entire output layer
    # This is a bit hacky but is really intended for the case in which we disaggregate from national -> regional

    inputLayer.selectAll()
    subsumed = None
    if inputLayer.selectedFeatureCount() < 10:
        new_layer.selectAll()
        bbox = QgsGeometry().fromRect(new_layer.boundingBoxOfSelected())
        subsumed = {feat[inputLayerIdField]: feat.geometry().intersection(
            bbox).area()/bbox.area() for feat in inputLayer.getFeatures()}

    # # convert multilinestring to linestring for later conversion
    # lyr_linstring = processing.runAndLoadResults(
    #     'qgis:convertgeometrytype',
    #     {
    #         'INPUT': inputLayer,
    #         'TYPE': 2,  # line string
    #         'OUTPUT': 'memory:',
    #     }
    # )
    # lyr_linstring = loadShapeFile(lyr_linstring['OUTPUT'])


    # Calculate the area or length of all input features (to avoid doing it repetitively later)
    # What type of input features are we dealing with? Support line or polygon
    for inFeat in inputLayer.getFeatures():
        if inFeat.geometry().type() == 1:
            inType = 'Line'
            inputAmounts = {feat[inputLayerIdField]: in_a.measureLine(
                feat.geometry().asMultiPolyline()[0]) for feat in inputLayer.getFeatures()}
        elif inFeat.geometry().type() == 2:
            inType = 'Polygon'
            inputAmounts = {feat[inputLayerIdField]: in_a.measureArea(
                feat.geometry()) for feat in inputLayer.getFeatures()}
        else:
            raise ValueError(
                'Input shapefile must contain either polygons or lines')
        break  # Just look at the first feature and assume the rest are of the same type

    # # convert multilinestring to linestring for later use
    # if inType == 'Line':
    #     lyr_linstring = processing.runAndLoadResults(
    #         'qgis:convertgeometrytype',
    #         {
    #             'INPUT': inputLayer,
    #             'TYPE': 2,  # line string
    #             'OUTPUT': 'memory:',
    #         },
    #         feedback=QgsProcessingFeedback().reportError('invalid features encountered in `qgis:convertgeometrytype` processing')
    #     )
    #     lyr_linstring = loadShapeFile(lyr_linstring['OUTPUT'])
    #     inputLayer_use = lyr_linstring
    # else:
    #     inputLayer_use = inputLayer

    for outputFeat in new_layer.getFeatures():  # For each output feature
        outGeo = outputFeat.geometry()
        outType = outGeo.type()
        if outType != 2:
            raise ValueError('Output features must all be polygons')
        # IDs of input data features intersected by the output area polygon
        matching = inputIndex.intersects(outputFeat.geometry().boundingBox())
        matchingInputAmounts = {}
        inputLayer.selectByIds(matching)
        # inputLayer_use.selectByIds(matching)
        # Input features that intersect the bounding box of the output feature
        selected = inputLayer.selectedFeatures()
        # selected = inputLayer_use.selectedFeatures()

        for featureMatched in selected:
            # Time-saver: If everything is subsumed by the input, skip the following calculations
            # To account for rounding error
            if subsumed is not None and subsumed[featureMatched[inputLayerIdField]] > 0.999999999:
                amountIntersected = out_a.measureArea(outGeo)
            else:
                # Calculate the amount intersected (metres for lines, square metres for polygons)
                if inType == 'Line':
                    amountIntersected = outGeo.intersection(
                        featureMatched.geometry()).length()
                    # amountIntersected = out_a.measureLine(
                    #     outGeo.intersection(featureMatched.geometry()).asPolyline())
                if inType == 'Polygon':
                    amountIntersected = out_a.measureArea(
                        outGeo.intersection(featureMatched.geometry()))

            if amountIntersected < 0.1:
                continue  # Ignore any intersections smaller than 0.1m2 or 0.1m

            matchingInputAmounts[featureMatched[inputLayerIdField]] = {'amountIntersected': amountIntersected,
                                                                       'originalAmount': inputAmounts[featureMatched[inputLayerIdField]]}
            # Get the requested feature attributes too
            for field in fieldsToSample:
                matchingInputAmounts[featureMatched[inputLayerIdField]
                                     ][field] = featureMatched[field]

        intersectedAmounts[outputFeat[newLayerIdField]] = matchingInputAmounts

    return intersectedAmounts


def intersecting_amounts_LUCY(fieldsToSample, inputLayer, new_layer, inputLayerIdField, newLayerIdField):
    ''' Identical to intersecting_amounts but does spatial indexing differently to get around big extents making it crash'''
    intersectedAmounts = {}

    # Ensure areas are all square metres (if SRS=WGS84 then doing geometry.area() gives square degrees)
    # when comparing across different layers. Comparing areas within the same layer don't need this
    in_a = QgsDistanceArea()
    in_a.setEllipsoid('WGS84')
    # in_a.setEllipsoidalMode(True)
    in_a.setSourceCrs(inputLayer.crs(), QgsCoordinateTransformContext())

    out_a = QgsDistanceArea()
    out_a.setEllipsoid('WGS84')
    # out_a.setEllipsoidalMode(True)
    out_a.setSourceCrs(new_layer.crs(), QgsCoordinateTransformContext())

    # Get bounding box around combined output features
    # If there are fewer than 10 input features, work out if any of them totally subsume the entire output layer
    # This is a bit hacky but is really intended for the case in which we disaggregate from national -> regional
    inputLayer.selectAll()
    subsumed = None
    if inputLayer.selectedFeatureCount() < 10:
        new_layer.selectAll()
        bbox = QgsGeometry().fromRect(new_layer.boundingBoxOfSelected())
        subsumed = {feat[inputLayerIdField]: feat.geometry().intersection(
            bbox).area()/bbox.area() for feat in inputLayer.getFeatures()}  # Area ratio

    # # convert multilinestring to linestring for later use
    # lyr_linstring = processing.runAndLoadResults(
    #     'qgis:convertgeometrytype',
    #     {
    #         'INPUT': inputLayer,
    #         'TYPE': 2,  # line string
    #         'OUTPUT': 'memory:',
    #     },
    #     feedback=QgsProcessingFeedback().reportError('invalid features encountered in `qgis:convertgeometrytype` processing')
    # )
    # lyr_linstring = loadShapeFile(lyr_linstring['OUTPUT'])
    # Calculate the area or length of all input features (to avoid doing it repetitively later)
    # What type of input features are we dealing with? Support line or polygon
    for inFeat in inputLayer.getFeatures():
    # for inFeat in lyr_linstring.getFeatures():
        if inFeat.geometry().type() == 1:
            inType = 'Line'
            inputAmounts = {feat[inputLayerIdField]: in_a.measureLine(
                feat.geometry().asMultiPolyline()[0]) for feat in inputLayer.getFeatures()}
        elif inFeat.geometry().type() == 2:
            inType = 'Polygon'
            inputAmounts = {feat[inputLayerIdField]: in_a.measureArea(
                feat.geometry()) for feat in inputLayer.getFeatures()}
        else:
            raise ValueError(
                'Input shapefile must contain either polygons or lines')
        break  # Just look at the first feature and assume the rest are of the same type

    a = QgsSpatialIndex()
    for outputFeat in new_layer.getFeatures():  # For each output feature
        outGeo = outputFeat.geometry()
        outType = outGeo.type()
        if outType != 2:
            raise ValueError('Output features must all be polygons')

        # Generate spatial index of this specific feature and see which input features overlay them
        # This is a workaround as putting the whole world in a spatial index caused QGIS to crash hard

        a.addFeature(outputFeat)
        matchingInputIds = []
        for inFeat in inputLayer.getFeatures():
            # IDs of input data features intersected by the output area polygon
            matching = a.intersects(inFeat.geometry().boundingBox())
            if len(matching) == 1:
                matchingInputIds.append(inFeat.id())

        a.deleteFeature(outputFeat)

        inputLayer.selectByIds(matchingInputIds)

        # convert multilinestring to linestring for later use
        lyr_linstring = processing.runAndLoadResults(
            'qgis:convertgeometrytype',
            {
                'INPUT': inputLayer,
                'TYPE': 2,  # line string
                'OUTPUT': 'memory:',
            },
            feedback=QgsProcessingFeedback().reportError('invalid features encountered in `qgis:convertgeometrytype` processing')
        )
        lyr_linstring = loadShapeFile(lyr_linstring['OUTPUT'])

        # Input features that intersect the bounding box of the output feature
        selected = lyr_linstring.selectedFeatures()
        # selected = inputLayer.selectedFeatures()
        matchingInputAmounts = {}

        for featureMatched in selected:
            # Time-saver: If everything is subsumed by the input, skip the following calculations
            # To account for rounding error
            if subsumed is not None and subsumed[featureMatched[inputLayerIdField]] > 0.999999999:
                amountIntersected = out_a.measureArea(outGeo)
            else:
                # Calculate the amount intersected (metres for lines, square metres for polygons)
                if inType == 'Line':
                    amountIntersected = out_a.measureLine(
                        outGeo.intersection(featureMatched.geometry()).asPolyline())
                if inType == 'Polygon':
                    amountIntersected = out_a.measureArea(
                        outGeo.intersection(featureMatched.geometry()))

            if amountIntersected < 0.1:
                continue  # Ignore any intersections smaller than 0.1m2 or 0.1m

            matchingInputAmounts[featureMatched[inputLayerIdField]] = {'amountIntersected': amountIntersected,
                                                                       'originalAmount': inputAmounts[featureMatched[inputLayerIdField]]}
            # Get the requested feature attributes too
            for field in fieldsToSample:
                matchingInputAmounts[featureMatched[inputLayerIdField]
                                     ][field] = featureMatched[field]

        intersectedAmounts[outputFeat[newLayerIdField]] = matchingInputAmounts
    return intersectedAmounts


def get_field_names(layer):
    # Reutrn a list of field names for the layer provided
    return [a.name() for i, a in enumerate(layer.dataProvider().fields())]


def get_field_index(layer, fieldname):
    # Return the field index for a given field name (or None if it doesn't exist)
    idx = None
    names = get_field_names(layer)
    if fieldname in names:
        return names.index(fieldname)


def disaggregate_weightings(intersectedAmounts, output_layer, weightingAttributes, total_weightings, outputLayerIdField):
    ''' Disaggregate the values obtained by intersecting_amounts and return factors by which to multiply the original feature attribute
    to get the amount in the new feature
    :param intersectedAmounts: Dict intersectedAreas (from intersecting_amounts()): {inputAreaId: {'amountIntersected', 'originalArea'} }
    :param output_layer: The QgsVectorLayer() object into which to place downscaled values
    :param weightingAttributes: List of attribute(s) of output_layer that contains weightings (these get normalised) for disaggregation.
            if absent then intersected area used
    :param total_weightings: Dict {attribute:{inputAreaId: totalWeighting}}: The sum of individual weightings in each input_area. If absent then
            the sum of the weights of output areas within each input area is used.
    :param outputLayerIdField: str: name of field containing unique IDs in output_layer
    :return dict of {output_id: {attributeName: {input_id : new_amount}}}

    If output area straddles multiple input areas, the weight in the input area is mutliplied by the proportion of the output area
    intersected by the input area'''

    # Calculate feature areas in square metres, because intersecting_amount are stated in square metres
    out_a = QgsDistanceArea()
    out_a.setEllipsoid('WGS84')
    # out_a.setEllipsoidalMode(True)
    out_a.setSourceCrs(output_layer.crs(), QgsCoordinateTransformContext())

    # Check the requested weightingAttribute exists in the output layer. If not, make some noise
    if weightingAttributes is None:
        weightingAttributes = ['_AREA_']  # Reserved word
    else:
        if type(weightingAttributes) is not list:
            weightingAttributes = [weightingAttributes]
        if '_AREA_' in weightingAttributes:
            raise ValueError(
                'The attribute _AREA_ is not allowed to be used as it is a reserved word')

    for wa in weightingAttributes:
        # Check each attribute (except _AREA_) is in the output shapefile
        if wa != '_AREA_':
            if output_layer.dataProvider().fieldNameIndex(wa) == -1:
                raise ValueError('Weighting attribute:' +
                                 str(wa) + ' not in the output shapefile.')

    weighting_attrib = {wa: {} for wa in weightingAttributes}

    # Get the total area and weighting attribute of each output feature
    for feat in output_layer.getFeatures():
        geoArea = out_a.measureArea(feat.geometry())
        for wa in weightingAttributes:
            if wa == '_AREA_':
                weighting_attrib[wa][feat[outputLayerIdField]] = {
                    'area': geoArea, 'weight': geoArea}  # Just use area
            else:
                weighting_attrib[wa][feat[outputLayerIdField]] = {
                    'area': geoArea, 'weight': feat[wa]}

    # turn the input dictionary inside out to get all the output features touching a given input feature
    input_features = {}

    for out_id in list(intersectedAmounts.keys()):
        for in_id in list(intersectedAmounts[out_id].keys()):
            if in_id not in list(input_features.keys()):
                input_features[in_id] = {}
            # Each entry contains the area intersected, size and values of the input feature
            # Append the weighting attributes to the input data dict
            intersectedAmounts[out_id][in_id]['weight_attrib'] = {}
            for wa in weightingAttributes:
                intersectedAmounts[out_id][in_id]['weight_attrib'][wa] = weighting_attrib[wa][out_id]['weight']
            intersectedAmounts[out_id][in_id]['output_feature_area'] = weighting_attrib[wa][out_id]['area']
            # Create lookup from input feature to its constituent output area(s)
            input_features[in_id][out_id] = intersectedAmounts[out_id][in_id]

    intersectedAmounts = None  # Done with this dict

    # If not all of the output feature is within the input feature, scale the weighting attribute by the
    # % of the output area falling inside the input feature

    # Produce new dictionary of outputFeature_id: inputFeature_id: factor
    # Multiply the input feature attribute value by the factor to get the disaggregated value
    # A weighting for each weighting attrib
    disagg_weightings = {wa: {} for wa in weightingAttributes}

    totals_already_available = True
    if len(list(total_weightings.keys())) == 0:
        totals_already_available = False
        total_weightings = {wa: {} for wa in weightingAttributes}

    elif len(list(total_weightings.keys())) != len(weightingAttributes):
        raise ValueError(
            'Total weightings are not present for all weighting attributes')

    # Keep track of the number of output features (reflects partial overlaps) intersecting each input feature
    num_outfeats = {}
    if not totals_already_available:
        # Use overlapping area in lieu of a total being available:
        # Track proportion of each input area that's been covered by output areas overall. Used for a correction factor that stops
        # everything in a partially-covered input area leaping into the output areas that cover it.
        inputAreaCovered = {}

    for in_id in list(input_features.keys()):
        num_outfeats[in_id] = 0.0
        if not totals_already_available:
            # Keep a running total of the weightings falling within input feature for normalisation
            for wa in weightingAttributes:
                total_weightings[wa][in_id] = 0.0
            # Add up what proportion of input area has been covered
            inputAreaCovered[in_id] = 0.0

        for out_id in list(input_features[in_id].keys()):
            # If not all of the output area intersects the input area, don't use all of the output area's weighting
            # Use proportion_of_output_area_intersected * weighting as the weighting. This prevents an output area from "stealing"
            # all of the disaggregated value when only a sliver intersects the input area
            fraction_intersected = input_features[in_id][out_id]['amountIntersected'] / \
                input_features[in_id][out_id]['output_feature_area']
            num_outfeats[in_id] += fraction_intersected
            if not totals_already_available:
                inputAreaCovered[in_id] += input_features[in_id][out_id]['amountIntersected'] / \
                    input_features[in_id][out_id]['originalAmount']

            for wa in weightingAttributes:
                # If none of the output areas in this input area, just allocate empty entries
                if out_id not in list(disagg_weightings[wa].keys()):
                    # Dict contains contribution from each input ID intersecting this out_id
                    disagg_weightings[wa][out_id] = {}

            for wa in weightingAttributes:
                try:
                    weight = float(
                        input_features[in_id][out_id]['weight_attrib'][wa])
                except Exception:  # Non-numeric weight encountered. Nothing from out_id will contribute to in_id
                    continue

                disagg_weightings[wa][out_id][in_id] = weight * \
                    fraction_intersected
                if not totals_already_available:
                    total_weightings[wa][in_id] += disagg_weightings[wa][out_id][in_id]

    # Go back round and normalise disagg_weightings by total weighting within each input feature
    # This conserves the total amount to be disaggregated in each input feature unless totals were obtained separately,
    #    in which case the totals are rightly used to downscale the "big" value.
    # If we find the total is zero over the whole input area, then spread everything evenly across inside that area
    #   to prevent throwing away the quantity to be disaggregated
    for in_id in list(input_features.keys()):
        for out_id in list(input_features[in_id].keys()):
            for wa in weightingAttributes:
                # Only use those values that are available (may have been skipped above)
                try:
                    # If a zero weighting found, spread evenly over input area
                    if total_weightings[wa][in_id] == 0.0:
                        disagg_weightings[wa][out_id][in_id] = 1 / \
                            float(num_outfeats[in_id])
                    else:                                # Non-zero weightings found: respect local variations
                        disagg_weightings[wa][out_id][in_id] /= float(
                            total_weightings[wa][in_id])

                    # Apply correction factor if needed
                    if not totals_already_available:
                        disagg_weightings[wa][out_id][in_id] *= inputAreaCovered[in_id]
                except:
                    pass
    total_weightings = {}  # Done with this. No point it hanging around taking up memory
    return disagg_weightings
#
# def spatialAverageField(mappings, fieldNum, inLayer):
#     # Take input features (each has a set of fields) and does a spatial average of the features within inLayer falling inside
#     # each feature within outLayer. Results are weighted by the area intersected
#     # fieldNum is the thing that is averaged
#     # mappings: dictionary of dictionaries: {output feature index: {input feature index:area intersected}}
#     #           Relates output areas to input areas (this takes a long time to do)
#     # Returns dict {outFeatureIndex:value}
#     featureVals = {}
#     for m in mappings.keys():
#         if len(mappings[m]) == 0: featureVals[m] = None
#         m=int(m)
#         weighting = np.divide(mappings[m].values(), sum(mappings[m].values()))
#         invals = [inLayer.GetFeature(int(featNum)).GetFieldAsDouble(fieldNum) for featNum in mappings[m].keys()]
#         result = np.sum(np.multiply(invals, weighting))
#         featureVals[m] = result
#
#     return featureVals


def feature_areas(layer):
   # Return dict of feature areas {feature_id:area m^2}
    out_a = QgsDistanceArea()  # Ensure metres are the unit rather than degrees
    out_a.setEllipsoid('WGS84')
    # out_a.setEllipsoidalMode(True)
    out_a.setSourceCrs(layer.crs(), QgsCoordinateTransformContext())

    areas = {}
    for feat in layer.getFeatures():
        areas[feat.id()] = out_a.measureArea(feat.geometry())
    return areas


def multiply_shapefile_attribute(layer, attribute, factor):
    ''' Multiply the named attribute by the given float() factor
        Return updated layer (if layer is ogr, then it will be altered on disk)'''
    feats = layer.getFeatures()
    # Work out which entry in the field list is the one of interest
    fieldNames = {a.name(): i for i, a in enumerate(
        layer.dataProvider().fields())}
    fieldIndex = fieldNames[attribute]
    layer.startEditing()
    for feat in feats:
        # Only update the number if it converts to a float
        try:
            new_val = float(feat[attribute]) * float(factor)
            layer.changeAttributeValue(feat.id(), fieldIndex, new_val)
        except Exception:
            continue

    layer.commitChanges()
    return layer


def convert_to_spatial_density(layer, attribute):
    ''' Normalise the named attribute by the area of its parent feature
        Return updated layer (if layer is ogr, then it will be altered on disk)'''
    out_a = QgsDistanceArea()  # Ensure metres are the unit rather than degrees
    out_a.setEllipsoid('WGS84')
    # out_a.setEllipsoidalMode(True)
    out_a.setSourceCrs(layer.crs(), QgsCoordinateTransformContext()())

    feats = layer.getFeatures()
    # Work out which entry in the field list is the one of interest
    fieldNames = {a.name(): i for i, a in enumerate(
        layer.dataProvider().fields())}
    fieldIndex = fieldNames[attribute]
    layer.startEditing()
    for feat in feats:
        # Only update the number if it converts to a float
        try:
            new_val = float(feat[attribute]) / \
                float(out_a.measureArea(feat.geometry()))
            layer.changeAttributeValue(feat.id(), fieldIndex, new_val)
        except Exception:
            continue

    layer.commitChanges()
    return layer


# def convert_nulls_to_zeroes(layer, attribute):
#     ''' Convert nulls in shapefile attributes to zeroes'''
#     feats = layer.getFeatures()
#     # Work out which entry in the field list is the one of interest
#     fieldNames = {a.name():i for i,a in enumerate(layer.dataProvider().fields())}
#     fieldIndex = fieldNames[attribute]
#     layer.startEditing()
#     for feat in feats:
#         # Only update the number if it converts to a float
#         try:
#             new_val = float(feat[attribute])
#         except Exception:
#             new_val = 0.0
#
#     layer.changeAttributeValue(feat.id(), fieldIndex, new_val)
#     layer.commitChanges()
#     return layer

def shapefile_attributes(layer):
    # Return a pandas Data Frame of shapefile attributes indexed by feature ID
    # Input: a QgsVectorLayer
    # Replaces anything non-numeric with its string representation

    table = {}
    for feat in layer.getFeatures():
        vals = []
        attrs = feat.attributes()
        for a in attrs:
            try:
                vals.append(float(a))
            except Exception:
                if str(a) is 'NULL':
                    vals.append(np.nan)
                else:
                    # vals.append(str(a))
                    vals.append(a)

                # try:
                    # vals.append(str(a))
                # except Exception:
                #     QPyNullVariant is deprecated
                    # always cast to NaN
                    # vals.append(np.nan)
                    # if a is NULL:
                    #     print(a)
                    #     vals.append(np.nan)
                    # else:
                    #     vals.append(a)
                # print('not a good value', type(a))
                # if type(a) is QPyNullVariant:
                # if a is None:
                #     vals.append(np.nan)
                # else:
                #     vals.append(a)

        table[feat.id()] = vals

    table = pd.DataFrame().from_dict(table)
    table = table.transpose()
    table.columns = [field.name() for field in layer.dataProvider().fields()]

    return table


def sameFeatures(layer1, layer2):
    '''
    Determines whether two QgsVectorLayers contain the same features (ignoring different attributes)
    :param layer1: QgsVectorLayer 1
    :param layer2: QgsVectorLayer 2
    :return: True if they match, False if they don't
    '''
    extentsMatch = layer1.extent() == layer2.extent()
    crsMatch = layer1.crs() == layer2.crs()
    expectedFeatureIds = layer2.allFeatureIds()
    featureIdsMatch = len(set(layer1.allFeatureIds()).intersection(
        expectedFeatureIds)) == len(expectedFeatureIds)
    # Do all the features have the same geometry?
    geometryMatch = True
    for id in expectedFeatureIds:
        layer1.selectByIds([id])
        infeat = layer1.selectedFeatures()[0]
        layer2.selectByIds([id])
        outfeat = layer2.selectedFeatures()[0]
        if infeat.geometry() != outfeat.geometry():
            geometryMatch = False
    if extentsMatch & featureIdsMatch & crsMatch & geometryMatch:
        return True
    else:
        return False


def findPrimaryKeyField(primaryKeyName, layerDefinition):
    # Identify which numeric field in a LayerDefinition is the primary key
    # Inputs: primaryKeyName: name of the primary key; layerDefiniton: layer definition object containing fields

    primaryKeyIndex = None
    for i in range(layerDefinition.GetFieldCount()):
        fDef = layerDefinition.GetFieldDefn(i)
        if fDef.GetNameRef() == primaryKeyName:
            primaryKeyIndex = i

    return primaryKeyIndex


def geometryOverlap(newGeo, origGeos):
    # Takes a "big" geometry and returns the area of each "small" geometry with which it intersects
    # origGeos with no overlap are omitted to save memory
    # Inputs: newGeo = "big" geometry (singleton)
    #         origGe = "small" geometries (list)
    # Value: Dict of intersected geometries indexed by origGeo ogr objects

    result = {}
    for og in origGeos:
        inter = newGeo.Intersection(origGeos)
        if inter.Area() > 0:
            result[origGeos] = newGeo.Intersection(origGeos)

    return result


def mapGeometries(newGeos, origGeos):
    # Spatially joins origGeos to newGeos, showing the area of each origGeos corresponding to newGeos
    overlaps = {}
    for ng in newGeos:
        overlaps[ng] = geometryOverlap(ng, origGeos)

    # Get areas intersecting each newGeos
    areas = {}
    for ov in list(overlaps.keys()):
        areas[ov] = []
        for int in ov:  # For each intersection
            areas[ov].append(ov.Area())

    return areas


def loadShapeFile(filename, targetEPSG=None):
    # Opens a shapefile. Note that any changes to this shapefile will be written straight to disk
    layer = QgsVectorLayer(filename, 'Shapefile', 'ogr')
    # layer = QgsVectorLayer(path=filename, baseName='shpfile', providerLib='ogr')

    # print(layer)
    # print(layer.crs().authid())
    # print layer.dataProvider().crs().authid().split(':')[1]
    # print('data provider', layer.dataProvider())

    # print layer.dataProvider().crs().authid().split(':')[1]
    if not layer:
        raise Exception('Shapefile %s not valid') % (filename,)
    if targetEPSG is None:
        try:
            targetEPSG = '32631'
        except Exception:
            raise ValueError(
                'Could not determine a CRS for shapefile %s' % (filename,))
    crs = layer.crs()
    crs.createFromId(int(targetEPSG))
    layer.setCrs(crs)
    return layer


def openShapeFileInMemory(filename, targetEPSG=None, label="Layer"):
    '''
    Returns a duplicate of the input QgsVectorLayer, stored in memory
    :param filename: Filename of shapefile
    :param targetEPSG: EPSG code (numeric) of shapefile
    :param label: Label to use in QGIS
    :return: QgsVectorLayer
    '''
    # Returns a duplicate of the input qgsVectorLayer, in memory
    # Optionally labels the name of the layer
    a = loadShapeFile(filename)
    b = duplicateVectorLayer(a, targetEPSG=targetEPSG, label=label)
    a = None
    return b


def saveLayerToFile(layer, filename, targetCRS=None, label=None):
    '''saves a QgsVectorLayer that may be in memory to a disk,  Overwrites it if it already exists
    :param layer:  QgsVectorLayer to save
    :param filename:  File name to save as
    :param targetCRS: CRS of layer to write (as with layer.getCRS())
    :param label: Label of layer
    :return: None
    '''

    if os.path.exists(filename):
        deleted = QgsVectorFileWriter.deleteShapeFile(filename)
        if not deleted:
            raise IOError('Failed to delete existing vector file ' + str(filename) +
                          '. The file may be in use. Please close it and try again.')

    error_code, error_msg = QgsVectorFileWriter.writeAsVectorFormat(
        layer, filename, "CP1250", targetCRS, "ESRI Shapefile")

    if error_code != QgsVectorFileWriter.NoError:
        print(error)
        raise IOError('Failed to write vector file ' + str(filename))


def addNewField(inLayer, fieldNames, initialValue=None):
    ''' Adds a Double field (attribute) to a QgsVectorLayer and also gives it an initial value (optional)
        returns the updated layer'''

    if type(fieldNames) is not list:
        fieldNames = [fieldNames]
    inLayer.startEditing()
    for field in fieldNames:
        inLayer.addAttribute(QgsField(field, QVariant.Double))
        inLayer.updateFields()
    inLayer.commitChanges()
    inLayer.updateFields()
    inLayer.updateExtents()

    # Populate with initial values
    for fieldName in fieldNames:
        # Find index of this field
        fieldNameList = {a.name(): i for i, a in enumerate(
            inLayer.dataProvider().fields())}
        fieldIndex = fieldNameList[fieldName]

        # Now propagate the initial value through all the features
        if initialValue is not None:
            inLayer.startEditing()
            for feat in inLayer.getFeatures():
                inLayer.changeAttributeValue(
                    feat.id(), fieldIndex, float(initialValue))
            inLayer.commitChanges()

    inLayer.updateExtents()

    return inLayer


def duplicateVectorLayer(inLayer, targetEPSG=None, label=None):
    # Creates duplicate of a shapefile (single vector layer) in memory, given the filename of the original shapefile
    # Shapefile is assigned CRS using targetEPSG (integer): the EPSG code (optional)

    if label is None:
        label = 'Duplicated Layer'
    # If no target EPSG specified, try inheriting that from the input layer. If nothing there, try 27700
    if targetEPSG is None:
        try:
            targetEPSG = inLayer.dataProvider().crs().authid().split(':')[1]
        except Exception:
            raise Exception('Cannot identify the EPSG code for shapefile:' +
                            str(inLayer.dataProvider().dataSourceUri().uri()))

    # Try very hard to set the CRS of the input layer so there are no annoying popups
    inLayer.startEditing()
    crs = inLayer.crs()
    crs.createFromId(int(targetEPSG))
    inLayer.setCrs(crs)
    inLayer.updateExtents()
    inLayer.commitChanges()

    # # Create output layer in memory
    # newLayer = QgsVectorLayer("Polygon?crs=EPSG:" +
    #                           str(targetEPSG), label, "memory")
    # pr = newLayer.dataProvider()
    # if pr is None:
    #     raise Exception('No provider')

    # fields = inLayer.fields()

    # newLayer.startEditing()
    # pr.addAttributes(fields)
    # newLayer.updateFields()
    # newLayer.updateExtents()

    # # Copy features
    # for feat in inLayer.getFeatures():
    #     a = QgsFeature()
    #     a.setGeometry(feat.geometry())
    #     a.setFields(newLayer.fields())
    #     a.setAttributes(feat.attributes())
    #     pr.addFeatures([a])  # Update layer

    # newLayer.updateExtents()
    # newLayer.commitChanges()

    # TS added new method for duplicate a layer for QGIS3
    inLayer.selectAll()
    newLayer = processing.run(
        "native:saveselectedfeatures",
        {
            'INPUT': inLayer,
            'OUTPUT': 'memory:',
        }
    )['OUTPUT']
    newLayer.setCrs(crs)
    # newLayer.setLabel(label)
    return newLayer


def colourRanges(displayLayer, attribute, opacity, range_minima, range_maxima, colours):
    # from qgis.core import QgsMapLayerRegistry, QgsSymbol, QgsGraduatedSymbolRenderer, QgsRendererRange
    from qgis.core import QgsSymbol, QgsGraduatedSymbolRenderer, QgsRendererRange
    from qgis.PyQt.QtGui import QColor

    # Colour vector layer according to the value of attribute <<attribute>>, with ranges set out by <<range_minima>> (list), <<range_maxima>> (list)
    # using <<colours>>
    # Map is added to QGIS interface with <<opacity>> (double: 0 to 1)
    rangeList = []
    transparent = QColor(QColor(0, 0, 0, 0))
    for i in range(0, len(range_minima)):
        symbol = QgsSymbol.defaultSymbol(displayLayer.geometryType())
        symbol.setColor(QColor(colours[i]))
        symbol.setOpacity(opacity)  # setAlpha is now setOpacity
        # symbol.symbolLayer(0).setOutlineColor(transparent)

        valueRange = QgsRendererRange(range_minima[i], range_maxima[i], symbol,
                                      str(range_minima[i]) + ' - ' + str(range_maxima[i]))
        rangeList.append(valueRange)

    renderer = QgsGraduatedSymbolRenderer('', rangeList)
    renderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
    renderer.setClassAttribute(attribute)
    displayLayer.setRenderer(renderer)  # setRendererV2 before


def populateShapefileFromTemplate(dataMatrix, primaryKey, templateShapeFile,
                                  templateEpsgCode=None, title=None):
    '''
    Produce a map of greaterQF outputs based on a template shape file (QGIS ONLY)
    Inputs:
      dataMatrix:Pandas array with indexes equal to feature IDs and columns with headings for shapefile attributes
      primaryKey: shapefile field that contains feature ID
      templateShapeFile: Filename of shapefile or QgsVectorLayer from which to produce outputs
      templateEpsgCode: EPSG code of shapefile
    Outputs:
      newLayer: A QGIS layer containing all greaterQF components for each feature. Stored in memory.
      :param templateEpsgCode:
    '''

    if type(templateShapeFile) in [str, str]:
        # Open existing layer and try to set its CRS
        layer = openShapeFileInMemory(
            templateShapeFile, templateEpsgCode, label=title)

        if not layer:
            raise Exception(
                'Shapefile ' + str(templateShapeFile) + ' not valid')

    elif type(templateShapeFile) is QgsVectorLayer:
        # Just use if already a QgsVectorLayer
        layer = templateShapeFile
    else:
        raise ValueError(
            'Input layer should be a string path to a shapefile or a QgsVectorLayer')

    if templateEpsgCode is None:
        try:
            templateEpsgCode = int(
                layer.dataProvider().crs().authid().split(':')[1])
        except Exception:
            raise ValueError(
                'Could not ascertain EPSG code from output layer. One must be specified explicitly.')

    # Deal with fields/attributes
    attribs = list(dataMatrix.columns)

    fields = []
    for cmpt in attribs:
        fi = QgsField(cmpt, QVariant.Double)
        fi.setTypeName('double')  # Assume all the data are double
        fields.append(fi)

    idField = QgsField(primaryKey, QVariant.String)
    idField.setTypeName('QString')
    layer.startEditing()
    layer.dataProvider().addAttributes([idField])
    layer.dataProvider().addAttributes(fields)
    layer.updateFields()
    # Copy over features and set attributes
    layer.startEditing()
    for feat in layer.getFeatures():
        # Get area ID and Match this area ID to the model result
        featId = feat[primaryKey]
        try:
            areaId = int(featId)
        except Exception:
            areaId = str(featId)

        for fld in attribs:
            idx = layer.dataProvider().fieldNameIndex(fld)
            nulls = dataMatrix[fld].isnull()
            nulls = nulls.index[nulls]
            try:
                if areaId not in nulls:
                    layer.changeAttributeValue(
                        feat.id(), idx, float(dataMatrix[fld][areaId]))
            except:
                pass  # Allow a mismatch between input and output layer feature IDs
    layer.commitChanges()
    layer.updateExtents()

    return layer


def intOrString(x):
    # Return int or string representation of x if int is not possible
    try:
        return int(x)
    except:
        return str(x)
