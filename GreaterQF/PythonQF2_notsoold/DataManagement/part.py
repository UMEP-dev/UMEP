import pandas as pd
import os

def setOutputShapefile(self, shapefile, epsgCode, id_field):
    ''' Output polygons that will be produced. If inputs are different polygons, result will be area-weighted mean of intersected input polygon(s)
            shapefile: str OR QgsVectorLayer: The shapefile to use
            epsgCode: numeric EPSG code of shapefile coord system. This is needed to prevent popups asking the same
            id_field: The field of the shapefile that acts as a unique identifier for each feature.'''

    self.templateIdField = id_field
    self.templateEpsgCode = int(epsgCode)

    if id_field is None:
        raise ValueError('Shapefile ID field cannot be empty')

    if type(shapefile) is str:
        if not os.path.exists(shapefile):
            raise ValueError('Shapefile: ' + shapefile + ' does not exist')
            # Try and load a copy of the shapefile into memory. Allow explosion if fails.

        self.outputLayer = openShapeFileInMemory(shapefile, targetEPSG=self.templateEpsgCode, label='Template layer')

    if type(shapefile) is QgsVectorLayer:
        self.outputLayer = shapefile

    print('output layer', self.outputLayer)
    # Ensure the ID field exists
    fields = get_field_names(self.outputLayer)
    if id_field not in fields:
        raise ValueError('ID Field ' + str(id_field) + ' not present in output shapefile')

    # Refer to features by an ID in the shapefile attributes rather than (numeric) feature ID, if desired
    self.templateIdField = id_field
    # Create mapping from real (numeric) feature ID to desired (string) feature ID
    a = shapefile_attributes(self.outputLayer)[id_field]
    self.featureMapper = pd.Series(index=a.index, data=list(map(intOrString, a.values)))

    # record what was used to label features
    if self.logger is not None:
        self.logger.addEvent('Disagg', None, None, None,
                             'Labelling features using ' + id_field + ' for ' + str(shapefile))

    # Record area of each polygon and label as the user desires
    self.areas = pd.Series(feature_areas(self.outputLayer))
    self.areas.index = self.featureMapper[self.areas.index]

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

def loadShapeFile(filename, targetEPSG=None):
    # Opens a shapefile. Note that any changes to this shapefile will be written straight to disk
    layer = QgsVectorLayer(filename, 'Shapefile', 'ogr')
    # layer = QgsVectorLayer(path=filename, baseName='shpfile', providerLib='ogr')

    print(layer)
    print(layer.crs().authid())
    # print layer.dataProvider().crs().authid().split(':')[1]
    print('data provider', layer.dataProvider())

    # print layer.dataProvider().crs().authid().split(':')[1]
    if not layer:
        raise Exception('Shapefile %s not valid')%(filename,)
    if targetEPSG is None:
        try:
            targetEPSG = '32631'
        except Exception:
            raise ValueError('Could not determine a CRS for shapefile %s'%(filename,))
    crs = layer.crs()
    crs.createFromId(int(targetEPSG))
    layer.setCrs(crs)
    return layer

def shapefile_attributes(layer):
    # Return a pandas Data Frame of shapefile attributes indexed by feature ID
    # Input: a QgsVectorLayer
    # Replaces anything non-numperic with its string representation

    table = {}
    for feat in layer.getFeatures():
        vals = []
        attrs = feat.attributes()
        for a in attrs:
            try:
                vals.append(float(a))
            except Exception:
                if type(a) is QPyNullVariant:
                    vals.append(np.nan)
                else:
                    vals.append(a)

        table[feat.id()] = vals

    table = pd.DataFrame().from_dict(table)
    table = table.transpose()
    table.columns = [field.name() for field in layer.dataProvider().fields()]

    return table

def duplicateVectorLayer(inLayer, targetEPSG=None, label=None):
    # Creates duplicate of a shapefile (single vector layer) in memory, given the filename of the original shapefile
    # Shapefile is assigned CRS using targetEPSG (integer): the EPSG code (optional)

    if label is None:
        label='Duplicated Layer'
    # If no target EPSG specified, try inheriting that from the input layer. If nothing there, try 27700
    if targetEPSG is None:
        try:
            targetEPSG = inLayer.dataProvider().crs().authid().split(':')[1]
        except Exception:
            raise Exception('Cannot identify the EPSG code for shapefile:' + str(inLayer.dataProvider().dataSourceUri().uri()))


    # Try very hard to set the CRS of the input layer so there are no annoying popups
    inLayer.startEditing()
    crs = inLayer.crs()
    crs.createFromId(int(targetEPSG))
    inLayer.setCrs(crs)
    inLayer.updateExtents()
    inLayer.commitChanges()

    # Create output layer in memory
    newLayer = QgsVectorLayer("Polygon?crs=EPSG:" + str(targetEPSG), label, "memory")
    pr = newLayer.dataProvider()
    if pr is None:
        raise Exception('No provider')

    fields = inLayer.fields()

    newLayer.startEditing()
    pr.addAttributes(fields)
    newLayer.updateFields()
    newLayer.updateExtents()

    # Copy features
    for feat in inLayer.getFeatures():
        a = QgsFeature()
        a.setGeometry(feat.geometry())
        a.setFields(newLayer.fields())
        a.setAttributes(feat.attributes())
        pr.addFeatures([a])  # Update layer


    newLayer.updateExtents()
    newLayer.commitChanges()
    return newLayer

def get_field_names(layer):
    # Reutrn a list of field names for the layer provided
    return [a.name() for i, a in enumerate(layer.dataProvider().fields())]



self.outputLayer = openShapeFileInMemory(shapefile, targetEPSG=self.templateEpsgCode, label='Template layer')

if type(shapefile) is QgsVectorLayer:
    self.outputLayer = shapefile