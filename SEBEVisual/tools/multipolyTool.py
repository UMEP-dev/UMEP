'''
Created on 10 apr 2014

@author: nke
'''
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *


class MultiPolyTool(QgsMapTool):
    polyComplete = pyqtSignal(QgsFeature)
    rubberband1 = None
    rubberband2 = None
    rubberbandList = []
    pointList = []
    latestPoint = None
    Done = False
    poly = QgsFeature()

    # Create a reference to the map canvas
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapTool.__init__(self, self.canvas)
        
    def canvasMoveEvent(self, event):
        if self.Done:
            pass
        elif len(self.pointList) > 0:
            point = self.toMapCoordinates(event.pos())
            if self.rubberband1 != None:
                self.rubberband1.reset()
                self.rubberband2.reset()
            
            self.rubberband1 = QgsRubberBand(self.canvas, False)
            self.rubberband1.setColor(QColor(Qt.red))
            self.rubberband2= QgsRubberBand(self.canvas, False)
            self.rubberband2.setColor(QColor(Qt.red))

            points1 = [self.latestPoint, point]
            points2 = [point, self.pointList[0]]
            
            self.rubberband1.setToGeometry(QgsGeometry.fromPolyline(points1),None)
            self.rubberband2.setToGeometry(QgsGeometry.fromPolyline(points2),None)

    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if len(self.pointList) == 0:
                self.latestPoint = self.toMapCoordinates(e.pos())
                self.pointList.append(self.toMapCoordinates(e.pos()))
            else: 
                rubberband = QgsRubberBand(self.canvas, False)
                rubberband.setColor(QColor(Qt.red))
                newPoint = self.toMapCoordinates(e.pos())
                points = [QgsPoint(self.latestPoint.x(),self.latestPoint.y()),QgsPoint(newPoint.x(),newPoint.y())]
                self.pointList.append(QgsPoint(newPoint.x(),newPoint.y()))
                rubberband.setToGeometry(QgsGeometry.fromPolyline(points), None)
                self.rubberbandList.append(rubberband)
                self.latestPoint = newPoint
        elif e.button() == Qt.RightButton:
            self.Done = True
            self.poly.setGeometry(QgsGeometry.fromPolygon([self.pointList]))
            self.polyComplete.emit(self.poly)
            
            for rubberband in self.rubberbandList:
                rubberband.reset()
            self.rubberband1.reset()
            self.rubberband2.reset()    
            self.rubberbandList = []
            self.pointList = []
            self.latestPoint = None
            self.Done = False