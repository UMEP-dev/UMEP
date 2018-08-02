from future import standard_library
standard_library.install_aliases()
from builtins import str
from qgis.PyQt.QtCore import QObject, pyqtSignal
import urllib.request, urllib.parse, urllib.error
import os
import xml.etree.ElementTree as etree
from qgis.core import QgsRasterLayer, QgsRasterPipe, QgsRasterFileWriter
import tempfile
import traceback

class DownloadDataWorker(QObject):
    # Worker to get raster data saved to a file in a thread
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, str)
    def __init__(self, baseURL, layerName, outputFile, bbox, resolution, srs):
        QObject.__init__(self)
        self.baseURL = baseURL
        self.layerName = layerName
        self.outputFile = outputFile
        self.bbox = bbox
        self.resolution = resolution
        self.srs = srs

    def kill(self):
        self.killed=True

    def run(self):
        try:
            output = webToRaster(self.baseURL, self.layerName, self.outputFile, self.bbox, self.resolution, self.srs, self.update)
            self.finished.emit({'filename':output, 'srs':self.srs, 'progress':100})
        except Exception as e:
            self.error.emit(e, traceback.format_exc())

def webToRaster(baseURL, layer_name, output_file, bbox, resolution, srs, update):
    '''
    Take WCS raster layer and save to local geoTiff
    :param baseURL: Server URL up to the /wcs? part where the query string begins (not including the question mark)
    :param layer_name: The coverage name on the WCS server
    :param output_file: File to save as (GeoTIFF)
    :param bbox: dict with WGS84 coordinates {xmin: float <lower left longitude>, xmax:float, ymin:float <upper right latitude>, ymax:float}
    :param resolution: dict {x:float, y:float} containing the resolution to use
    :param srs: string e.g. EPSG:4326: The layer CRS string
    :return: Path to output file
    '''

    # Example URL http://51.140.49.104:8080/geoserver/wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&coverage=public:GRUMP_PopulationDensity_2010_UNadj&identifier=public:GRUMP_PopulationDensity_2010_UNadj&bbox=-1,50,1,52&FORMAT=image/tiff&CRS=EPSG:4326&WIDTH=500&HEIGHT=500&interpolatioMethod=bilinear
    # Example URL http://51.140.49.104:8080/geoserver/wcs?SERVICE=WCS&VERSION=1.1.1&REQUEST=getcoverage&coverage=public:GRUMP_PopulationDensity_2010_UNadj&identifier=public:GRUMP_PopulationDensity_2010_UNadj&boundingbox=-1,51,-0.8,51.2,EPSG:4326&format=image/tiff&CRS=EPSG:4326&WIDTH=500&HEIGHT=500
    #http://geobrain.laits.gmu.edu/cgi-bin/wcs-all?service=wcs&version=1.1.0&request=getcoverage&identifier=SMOKE:%22/Volumes/RAIDL1/WCS-ALL-DATA/SMOKE/G13.201010221315.all.aod_conc.NAM3.grd%22:EATM&format=image/netcdf&boundingbox=-175,-0.15,-54.85,79.95,epsg:4326
    #layer_name = 'public:GRUMP_PopulationDensity_2010_UNadj' # Layer name on server
    #bbox = "-1,50,1,52" # Region to extract (EPSG 4326) xmin, ymin, xmax, ymax
    # Dimensions of what we WANT (not what's on server). Server will resample.

    #baseURL = "http://51.140.49.104:8080/geoserver/wcs"
    bboxString = "%f,%f,%f,%f"%(bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax'])
    #bigURL = baseURL + '/wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&coverage=%s&identifier=%s&bbox=%s&FORMAT=image/tiff&CRS=EPSG:4326&WIDTH=%d&HEIGHT=%d'%(layer_name, layer_name, bboxString, width, height)
    bigURL = baseURL + '/wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&coverage=%s&identifier=%s&bbox=%s&FORMAT=image/geotiff&CRS=%s&RESX=%f&RESY=%f'%(layer_name, layer_name, bboxString, srs, resolution['x'], resolution['y'])
    # Save data to temporary file

    try:
        dataOut = tempfile.mktemp('.tif')
    except Exception as e:
        raise Exception('Problem creating temporary file to store raster data: '+  str(e))
    # TODO: Work out if the response is an XML error
    update.emit({'progress':10, 'message':'Downloading file...'})

    urllib.request.urlretrieve(bigURL, dataOut)

    # Load data as QgsRasterLayer and then re-save it, ensuring it has the correct projection info
    a = QgsRasterLayer(dataOut, "temporary raster layer")
    # Double-confirm projection info (sometimes WCS has it in the meta but not the file)
    crs = a.crs()
    crs.createFromId(int(srs.split(':')[1]))
    a.setCrs(crs)
    update.emit({'progress':90, 'message':'Saving file...'})
    writer = QgsRasterFileWriter(output_file)

    pipe = QgsRasterPipe()
    width, height = a.width(), a.height()
    extent = a.extent()
    provider=a.dataProvider()
    pipe.set(provider.clone())
    writer.writeRaster(pipe, width, height, extent, a.crs())
    a = None
    pipe = None
    provider = None
    # Delete temp file
    os.remove(dataOut)
    return output_file
