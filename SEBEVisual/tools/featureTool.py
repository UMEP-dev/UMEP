'''
Created on 10 apr 2014

@author: nke
'''
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *




class FeatureTool(QgsMapToolEmitPoint):
    '''
    classdocs
    '''
    Feature = []
    selectedFeature = pyqtSignal()
    



    def __init__(self, canvas):
        
        #Create a reference to the map canvas
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
    

    
    def canvasPressEvent(self, e):
        currentLayer = self.canvas.currentLayer()
        point = self.toMapCoordinates(e.pos())
        pntGeom = QgsGeometry.fromPoint(point)
        pntbuf = pntGeom.buffer((self.canvas.mapUnitsPerPixel() * 2),0)
        rect = pntbuf.boundingBox()
        cLayer = self.canvas.currentLayer()
        selectList = None
        if cLayer:
               selectList = cLayer.select(rect,True) 
               if cLayer.selectedFeatureCount() is not 0:
                   self.selectedFeature.emit()
               
              # while provider.nextFeature(feat):
                    #   if feat.geometry().intersects(pntGeom):
                         #      selectList.append(feat.id())
                               
                               

              # cLayer.setSelectedFeatures(selectList)
                
        #point2 = QgsPoint(point.x(), point.y())
        #rect = QgsRectangle(point, point2)
        #self.Feature = QgsFeature()
        #provider = currentLayer.dataProvider()
        #currentLayer.select(rect, True)
        #self.Feature = currentLayer.selectedFeatures()
        #self.selectedFeature.emit(self.Feature)
        
        
        
        
