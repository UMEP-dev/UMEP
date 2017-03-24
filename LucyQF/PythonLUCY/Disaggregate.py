from PyQt4.QtCore import QObject, pyqtSignal
import traceback
import os
import pickle
from DataManagement.spatialHelpers import saveLayerToFile, loadShapeFile, populateShapefileFromTemplate, openShapeFileInMemory, reprojectVectorLayer_threadSafe
from DataManagement.temporalHelpers import makeUTC
try:
    import pandas as pd
except:
    pass
from Population import Population
from ExtraDisaggregate import ExtraDisaggregate, performDisaggregation, performSampling
from RegionalParameters import RegionalParameters

class DisaggregateWorker(QObject):
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    def __init__(self, ds, params, outputFolder, UMEPgrid=None, UMEPcoverFractions=None, UMEPgridID=None):
        QObject.__init__(self)
        self.killed = False
        self.ds = ds
        self.params = params
        self.outputFolder = outputFolder
        self.UMEPgrid = UMEPgrid
        self.UMEPcoverFractions = UMEPcoverFractions
        self.UMEPgridID = UMEPgridID

    def kill(self):
        self.killed=True

    def run(self):
        try:
            outputFolder = disaggregate(self.ds, self.params, self.outputFolder, self.UMEPgrid, self.UMEPcoverFractions, self.UMEPgridID, self.update)
            self.finished.emit(outputFolder)
        except Exception,e:
            self.error.emit(e, traceback.format_exc())

def floatOrNone(x):
    # Return float representation or, failing that, None
    try:
        return float(x)
    except:
        return None

def disaggregate(ds, params, outputFolder, UMEPgrid=None, UMEPcoverFractions=None, UMEPgridID=None, update=None):
    '''
    Function that performs all spatial disaggregation of GreaterQF inputs, and writes to output files.
    Returns dict of information that amounts to a new data sources file
    :param ds:  Data sources object (contains locations and metadata regarding shapefiles)
    :param params:  Params object (contains params related to disaggregation)
    :param outputFolder: string path to folder in which to store disaggregated shapefiles
    :param UMEPgrid (optional): str: Path to shapefile containing UMEP grid (for second-stage disaggregation)
    :param UMEPcoverFractions (optional): pd.DataFrame: Pandas dataframe containing cover fractions corresponding to UMEPgrid
    :param UMEPgridID (optional): str: Field of UMEPgrid that contains unique identifiers (must be same as index in UMEPcoverFractions)
    :return: dict of {dataName:{shapefileName, startDate, field(s)ToUse}
    '''
    returnDict = {}
    returnDict['resPop'] = [] # Residential population in terms of output layer. Allow a list for future expansion (we don't use it)
    returnDict['allocations'] = None # Allocations of each output layer feature to a region/country from the database

    outShp = ds.outputAreas_spat['shapefile']
    outFeatIds =  ds.outputAreas_spat['featureIds']
    outEpsg = ds.outputAreas_spat['epsgCode']

    # Disaggregate residential population to output features
    pop = Population()

    pop.setOutputShapefile(outShp, outEpsg, outFeatIds)
    rp = ds.resPop_spat[0]
        # Take a look at the residential population data and see if there are any people in it.
    testPop = loadShapeFile(rp['shapefile'], rp['epsgCode'])
    vals = pd.Series(map(floatOrNone, testPop.getValues('Pop')[0]))
    if sum(vals.dropna()) == 0:
        raise Exception('The input population file has zero population')
    testPop = None
    if rp['shapefile'] == outShp:
        # If same residential population and output shapefiles, just inject the res pop
        pop.injectResPop(rp['shapefile'], makeUTC(rp['startDate']), rp['attribToUse'], rp['epsgCode'])
    else:
        # If not the same, spatially disaggregate based on overlapping fractions
        pop.setResPop(rp['shapefile'], makeUTC(rp['startDate']), rp['attribToUse'], rp['featureIds'], None, rp['epsgCode'])

    filename = 'resPop_starting' + rp['startDate'].strftime('%Y-%m-%d') + '.shp'
    (lyr, attrib) = pop.getResPopLayer(makeUTC(rp['startDate']))
    scaledPopFile = os.path.join(outputFolder, filename)
    saveLayerToFile(lyr, scaledPopFile, pop.getOutputLayer().crs(), 'Res pop scaled')
    # Test the disaggregated shapefile to make sure it contains people
    vals = pd.Series(map(floatOrNone, lyr.getValues('Pop')[0]))
    if sum(vals.dropna()) == 0:
        raise Exception('The output shapefile did not overlap any of the population data, so the model cannot run')
    returnDict['resPop'].append({'file':filename, 'EPSG':rp['epsgCode'], 'startDate':rp['startDate'], 'attribute':attrib, 'featureIds':outFeatIds})

    update.emit(10)
    # Assign country ID to each of the disaggregated population features and allow national attributes to be looked up by feature ID
    atts = RegionalParameters()
    atts.setWorldDatabase(ds.database)
    allocatedLayer = atts.setOutputShapefile(outShp, outEpsg, outFeatIds)
    alloc_filename = 'area_allocations.shp'
    allocationFile = os.path.join(outputFolder, alloc_filename)
    saveLayerToFile(allocatedLayer, allocationFile, allocatedLayer.crs(), 'Regional allocations')
    allocatedLayer = None
    atts = None
    update.emit(20)
    returnDict['allocations'] = {'file':alloc_filename, 'EPSG':outEpsg, 'startDate':rp['startDate'], 'attribute':None, 'featureIds':outFeatIds}
    # If land cover information available, do extra disaggregation of the above population
    if (UMEPcoverFractions is not None) and (UMEPgrid is not None) and (UMEPgridID is not None):
        # Get weightings for building, transport and metabolism related distributions
        returnDict['extra_disagg'] = {}
        # Get EPSG of UMEP grid
        ug = openShapeFileInMemory(UMEPgrid)
        UMEPEPSG = ug.dataProvider().crs().authid().split(':')[1]
        ug = None
        # Disaggregate the initially-disaggregated data produced above
        returnDict['extra_disagg']['output_areas'] = {'file':UMEPgrid, 'EPSG':UMEPEPSG, 'featureIds':UMEPgridID}
        returnDict['extra_disagg']['metabolism'] = []
        returnDict['extra_disagg']['building'] = []
        returnDict['extra_disagg']['transport'] = []
        returnDict['extra_disagg']['allocations'] = None

        # Get intersecting weightings

        (intersectedAmounts, weightings) = ExtraDisaggregate(ds.outputAreas_spat['shapefile'], UMEPcoverFractions, UMEPgrid, params.landCoverWeights, ds.outputAreas_spat['featureIds'], UMEPgridID)
        update.emit(40)
        # Residential population
        rp = returnDict['resPop'][0]
        # High-res locations of metabolising population

        popLayer = loadShapeFile(reprojectVectorLayer_threadSafe(os.path.join(outputFolder, rp['file']), UMEPEPSG))
        # Distribute population for metabolism
        metabData = performDisaggregation(layerToDisaggregate=popLayer, idField=rp['featureIds'], fieldsToDisaggregate=[rp['attribute']], weightingType='metabolism', weightings=weightings)
        metabLayer = populateShapefileFromTemplate(dataMatrix=metabData, primaryKey=UMEPgridID, templateShapeFile=UMEPgrid, templateEpsgCode=UMEPEPSG)
        filename = '_EXTRA_DISAGG_metabPopulation_starting' + rp['startDate'].strftime('%Y-%m-%d') + '.shp'
        saveLayerToFile(metabLayer, os.path.join(outputFolder, filename), metabLayer.crs(), 'Metabolic population loadings')
        returnDict['extra_disagg']['metabolism'].append({'file':filename, 'EPSG':UMEPEPSG, 'startDate':rp['startDate'], 'attribute':rp['attribute'], 'featureIds':UMEPgridID})
        metabLayer = None
        update.emit(60)
        # Assign country ID to each of the disaggregated population features and allow national attributes to be looked up by feature ID
        atts2 = RegionalParameters()
        atts2.setWorldDatabase(ds.database)
        allocatedLayer = atts2.setOutputShapefile(UMEPgrid, UMEPEPSG, UMEPgridID)
        allocationFile = '_EXTRA_DISAGG_area_allocations.shp'
        saveLayerToFile(allocatedLayer, os.path.join(outputFolder, allocationFile), allocatedLayer.crs(), 'Regional allocations')
        returnDict['extra_disagg']['allocations'] = {'file':allocationFile, 'EPSG':UMEPEPSG, 'featureIds':UMEPgridID}
        allocatedLayer = None
        # Since the same input and output grids are being used every time, don't do this using SpatialTemporalResampler. Instead, make use of the face we only have to do intersected_areas once.
        update.emit(70)
        # Distribute population amongst buildings for building energy calculation
        bldgData = performDisaggregation(layerToDisaggregate=popLayer, idField=rp['featureIds'], fieldsToDisaggregate=[rp['attribute']], weightingType='building', weightings=weightings)
        bldgLayer = populateShapefileFromTemplate(dataMatrix=bldgData, primaryKey=UMEPgridID, templateShapeFile=UMEPgrid, templateEpsgCode=UMEPEPSG)
        filename = '_EXTRA_DISAGG_bldgEnergy_starting' + rp['startDate'].strftime('%Y-%m-%d') + '.shp'
        saveLayerToFile(bldgLayer, os.path.join(outputFolder, filename), bldgLayer.crs(), 'Building energy')
        returnDict['extra_disagg']['building'].append({'file':filename, 'EPSG':UMEPEPSG, 'startDate':rp['startDate'], 'attribute':rp['attribute'], 'featureIds':outFeatIds})
        bldgLayer = None
        update.emit(80)
        # Distribute population onto paved areas for vehicle calculation; vehicles will follow them there.
        transData = performDisaggregation(layerToDisaggregate=popLayer, idField=rp['featureIds'], fieldsToDisaggregate=rp['attribute'], weightingType='transport', weightings=weightings)
        transLayer = populateShapefileFromTemplate(dataMatrix=transData, primaryKey=UMEPgridID, templateShapeFile=UMEPgrid, templateEpsgCode=UMEPEPSG)
        filename  = '_EXTRA_DISAGG_vehcles_starting' + rp['startDate'].strftime('%Y-%m-%d') + '.shp'
        saveLayerToFile(transLayer, os.path.join(outputFolder,filename), transLayer.crs(), 'Vehicle count')
        returnDict['extra_disagg']['transport'].append({'file':filename, 'EPSG':UMEPEPSG, 'startDate':rp['startDate'], 'attribute':rp['attribute'], 'featureIds':outFeatIds})
        transLayer = None
        popLayer = None
        atts2 = None
        update.emit(90)
    # Pickle the dictionary as a manifest file
    with open(os.path.join(outputFolder, 'MANIFEST'), 'wb') as outpickle:
        pickle.dump(returnDict, outpickle)

    # Destroy the objects to eliminate any refernces to OGR or memory objects
    popLayer = None
    atts = None
    lyr = None
    update.emit(100)
    return outputFolder
