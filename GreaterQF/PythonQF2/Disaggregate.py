import os
import pickle
from DataManagement.spatialHelpers import saveLayerToFile, loadShapeFile, shapefile_attributes, populateShapefileFromTemplate
from DataManagement.temporalHelpers import makeUTC
from EnergyUseData import EnergyUseData
from FuelConsumption import FuelConsumption
from Population import Population
from Transport import Transport

def disaggregate(qfDataSources, qfParams, outputFolder):
    '''
    Function that performs all spatial disaggregation of GreaterQF inputs, and writes to output files.
    Returns dict of information that amounts to a new data sources file
    :param qfDataSources: GreaterQF Data sources object (contains locations and metadata regarding sharefiles)
    :param qfParams: GreaterQF config object (contains assumptions where these are needed)
    :param outputFolder: string path to folder in which to store disaggregated shapefiles
    :return: dict of {dataName:{shapefileName, startDate, field(s)ToUse}
    '''
    returnDict = {}
    outShp = qfDataSources.outputAreas_spat['shapefile']
    outFeatIds =  qfDataSources.outputAreas_spat['featureIds']
    outEpsg = qfDataSources.outputAreas_spat['epsgCode']

    pop = Population()
    pop.setOutputShapefile(outShp, outEpsg, outFeatIds)

    # Population data (may be the same as that used for disaggregation, but still needs specifying explicitly)
    # These get used to disaggregate energy, so population must be completely populated first

    # Raw residential population data: disaggregate and save
    returnDict['resPop'] = []
    returnDict['workPop'] = []
    returnDict['indElec'] = []
    returnDict['indGas'] = []
    returnDict['domElec'] = []
    returnDict['domGas'] = []
    returnDict['domEco7'] = []
    returnDict['transport'] = []

    for rp in qfDataSources.resPop_spat:
        pop.setResPop(rp['shapefile'],
                      startTime=makeUTC(rp['startDate']),
                      attributeToUse=rp['attribToUse'],
                      inputFieldId=rp['featureIds'],
                      weight_by=None,
                      epsgCode=rp['epsgCode'])
        outFile = os.path.join(outputFolder, 'resPop_starting' + rp['startDate'].strftime('%Y-%m-%d') + '.shp')
        (ds, attrib) = pop.getResPopLayer(makeUTC(rp['startDate']))
        saveLayerToFile(ds, outFile, pop.getOutputLayer().crs(), 'Res pop scaled')
        returnDict['resPop'].append({'file':outFile, 'EPSG':rp['epsgCode'], 'startDate':rp['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    # Raw residential population data: disaggregate and save
    for wp in qfDataSources.workPop_spat:
        pop.setWorkPop(wp['shapefile'],
                       startTime=makeUTC(wp['startDate']),
                       attributeToUse=wp['attribToUse'],
                       inputFieldId=wp['featureIds'],
                       weight_by=None,
                       epsgCode=wp['epsgCode'])

        outFile = os.path.join(outputFolder, 'WorkPop_starting' + wp['startDate'].strftime('%Y-%m-%d') + '.shp')
        (ds, attrib) = pop.getWorkPopLayer(makeUTC(wp['startDate']))
        saveLayerToFile(ds, outFile, pop.getOutputLayer().crs(), 'Work pop scaled')
        returnDict['workPop'].append({'file':outFile, 'EPSG':wp['epsgCode'], 'startDate':wp['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    # Set up building energy use data: total energy use for each area.
    bldgEnergy = EnergyUseData()
    # Industrial electricity, downscaled by workplace population
    for ie in qfDataSources.indElec_spat:
        (workpop, workpopattrib) = pop.getWorkPopLayer(makeUTC(ie['startDate']))     # Note: Population data is used for the output features. This means that population changing over time has to be incorporated
        bldgEnergy.setOutputShapefile(workpop, workpop.dataProvider().crs().authid().split(':')[1], outFeatIds)
        bldgEnergy.setIndustrialElec(ie['shapefile'],
                                     startTime=makeUTC(ie['startDate']),
                                     attributeToUse=ie['attribToUse'],
                                     inputFieldId=ie['featureIds'],
                                     weight_by=workpopattrib,
                                     epsgCode=ie['epsgCode'])
        (ds, attrib) = bldgEnergy.getIndustrialElecLayer(makeUTC(ie['startDate']))
        outFile = os.path.join(outputFolder, 'IndElec_starting' + ie['startDate'].strftime('%Y-%m-%d') + '.shp')
        saveLayerToFile(ds, outFile, bldgEnergy.getOutputLayer().crs(), 'ind elec gas downscaled')
        returnDict['indElec'].append({'file':outFile, 'EPSG':ie['epsgCode'], 'startDate':ie['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    # Industrial gas
    for ig in qfDataSources.indGas_spat:
        (output, workpopattrib) = pop.getWorkPopLayer(makeUTC(ig['startDate']))     # Disaggregate by workplace pop
        bldgEnergy.setOutputShapefile(output, output.dataProvider().crs().authid().split(':')[1], outFeatIds)
        bldgEnergy.setIndustrialGas(ig['shapefile'],
                                    startTime=makeUTC(ig['startDate']),
                                    attributeToUse=ig['attribToUse'],
                                    inputFieldId=ig['featureIds'],
                                    weight_by=workpopattrib,
                                    epsgCode=ig['epsgCode'])
        outFile = os.path.join(outputFolder, 'IndGas_starting' + ig['startDate'].strftime('%Y-%m-%d') + '.shp')
        (ds, attrib) = bldgEnergy.getIndustrialGasLayer(makeUTC(ie['startDate']))
        saveLayerToFile(ds, outFile, bldgEnergy.getOutputLayer().crs(), 'ind gas downscaled')
        returnDict['indGas'].append({'file':outFile, 'EPSG':ig['epsgCode'], 'startDate':ig['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    # Domestic gas
    for dg in qfDataSources.domGas_spat:
        (output, respopattrib) = pop.getResPopLayer(makeUTC(dg['startDate']))     # Disaggregate by residential pop
        bldgEnergy.setOutputShapefile(output, output.dataProvider().crs().authid().split(':')[1], outFeatIds)
        bldgEnergy.setDomesticGas(dg['shapefile'],
                                  startTime=makeUTC(dg['startDate']),
                                  attributeToUse=dg['attribToUse'],
                                  inputFieldId=dg['featureIds'],
                                  weight_by=respopattrib,
                                  epsgCode=dg['epsgCode'])
        outFile = os.path.join(outputFolder, 'DomGas_starting' + dg['startDate'].strftime('%Y-%m-%d') + '.shp')
        (ds, attrib) = bldgEnergy.getDomesticGasLayer(makeUTC(ie['startDate']))
        saveLayerToFile(ds, outFile, bldgEnergy.getOutputLayer().crs(), 'dom gas downscaled')
        returnDict['domGas'].append({'file':outFile, 'EPSG':dg['epsgCode'], 'startDate':dg['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    # Domestic elec
    for de in qfDataSources.domElec_spat:
        (output, respopattrib) = pop.getResPopLayer(makeUTC(dg['startDate']))     # Disaggregate by residential pop
        if type(respopattrib) is list:
            respopattrib = respopattrib[0]
        bldgEnergy.setOutputShapefile(output, output.dataProvider().crs().authid().split(':')[1], outFeatIds)
        bldgEnergy.setDomesticElec(de['shapefile'],
                                   startTime=makeUTC(de['startDate']),
                                   attributeToUse=de['attribToUse'],
                                   inputFieldId=de['featureIds'],
                                   weight_by=respopattrib,
                                   epsgCode=de['epsgCode'])
        outFile = os.path.join(outputFolder, 'DomElec_starting' + de['startDate'].strftime('%Y-%m-%d') + '.shp')
        (ds, attrib) = bldgEnergy.getDomesticElecLayer(makeUTC(ie['startDate']))
        saveLayerToFile(ds, outFile, bldgEnergy.getOutputLayer().crs(), 'dom elec downscaled')
        returnDict['domElec'].append({'file':outFile, 'EPSG':de['epsgCode'], 'startDate':de['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

# Domestic elec economy 7
    for e7 in qfDataSources.eco7_spat:
        (output, respopattrib) = pop.getResPopLayer(makeUTC(e7['startDate']))     # Disaggregate by residential pop
        if type(respopattrib) is list:
            respopattrib = respopattrib[0]
        bldgEnergy.setOutputShapefile(output, output.dataProvider().crs().authid().split(':')[1], outFeatIds)
        bldgEnergy.setEconomy7Elec(e7['shapefile'],
                                   startTime=makeUTC(e7['startDate']),
                                   attributeToUse=e7['attribToUse'],
                                   inputFieldId=e7['featureIds'],
                                   weight_by=respopattrib,
                                   epsgCode=e7['epsgCode'])
        outFile = os.path.join(outputFolder, 'Eco7_starting' + e7['startDate'].strftime('%Y-%m-%d') + '.shp')
        (ds, attrib) = bldgEnergy.getEconomy7ElecLayer(makeUTC(ie['startDate']))

        saveLayerToFile(ds, outFile, bldgEnergy.getOutputLayer().crs(), 'Economy 7 downscaled')
        returnDict['domEco7'].append({'file':outFile, 'EPSG':e7['epsgCode'], 'startDate':e7['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    # Set up transport fuel consumption in each output area
    fc = FuelConsumption(qfDataSources.fuelConsumption[0]['profileFile'])
    t = Transport(fc, qfParams)
    t.setOutputShapefile(outShp, outEpsg, outFeatIds)
    for tr in qfDataSources.transport_spat:
        sf = t.addTransportData(shapefile=tr['shapefile'],
                       startTime=makeUTC(tr['startDate']),
                       epsgCode=tr['epsgCode'],
                       roadTypeField=tr['class_field'],
                       roadTypeNames=tr['road_types'],
                       speedConversionFactor=tr['speed_multiplier'],
                       inputIdField=tr['featureIds'],
                       totalAADTField=tr['AADT_total'],
                       vAADTFields=tr['AADT_fields'],
                       speedDataField=tr['speed_field'])
        outFile = os.path.join(outputFolder, 'DailyFuelUse_starting' + tr['startDate'].strftime('%Y-%m-%d') + '.shp')
        saveLayerToFile(sf, outFile, bldgEnergy.getOutputLayer().crs(), 'Fuel use daily')
        returnDict['transport'].append({'file':outFile, 'EPSG':tr['epsgCode'], 'startDate':tr['startDate'], 'featureIds':outFeatIds})

    # Pickle the dictionary as a manifest file
    with open(os.path.join(outputFolder, 'MANIFEST'), 'wb') as outpickle:
        pickle.dump(returnDict, outpickle)

    # Return the output folder containing all this stuff
    return outputFolder
