from future import standard_library
standard_library.install_aliases()
from builtins import str
from qgis.PyQt.QtCore import QObject, pyqtSignal
import urllib.parse
import requests
import defusedxml.ElementTree as etree
import traceback

class GetMetaWorker(QObject):
    # Worker to get WMS metadata for a layer to keep the process from slowing down the interace thread
    finished = pyqtSignal(object)
    update = pyqtSignal(object)
    error = pyqtSignal(Exception, str)
    def __init__(self, baseURL, layerName):
        QObject.__init__(self)
        self.baseURL = baseURL
        self.layerName = layerName

    def kill(self):
        self.killed=True

    def run(self):
        try:
            output = getWMSInfo(self.baseURL, self.layerName, self.update)
            self.finished.emit(output)
        except Exception as e:
            self.error.emit(e, traceback.format_exc())


def getWMSInfo(baseURL, layer_name, update):
    '''
    Get WMS information that contains things like an abstract for the named layer

    :param baseURL:
    :param layer_name:
    :return:
    '''
    update.emit({'Abstract':'Loading abstract for layer...'})
    caps = baseURL + '/wms?service=WMS&version=1.1.1&request=GetCapabilities'
    ## Check if URL is valid
    parsed_url = urllib.parse.urlparse(caps)
    if parsed_url.scheme not in ('http', 'https'):
        raise Exception('Invalid URL: ' + caps)
            
    safe_url = parsed_url.geturl()

    response = requests.get(safe_url, timeout=15)
    data = response.content
    root = etree.fromstring(data)
    layer = root.find('Capability/Layer')
    if layer is None:
        return None # There must be a problem with this data source if there's no offering
    # Get actual layers within this layer and locate the
    a = layer.findall('Layer')
    for l in a:
        layName = l.find('Name').text
        if str(layName) == layer_name:
            # Extract and return the information
            if l.find('Abstract') is not None:
                return {'Abstract':l.find('Abstract').text}