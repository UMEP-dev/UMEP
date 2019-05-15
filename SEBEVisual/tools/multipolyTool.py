'''
Created on 10 apr 2014

@author: nke
'''
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY
from qgis.gui import QgsMapTool, QgsRubberBand


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
            
            self.rubberband1.setToGeometry(QgsGeometry.fromPolylineXY(points1),None)
            self.rubberband2.setToGeometry(QgsGeometry.fromPolylineXY(points2),None)

    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if len(self.pointList) == 0:
                self.latestPoint = self.toMapCoordinates(e.pos())
                self.pointList.append(self.toMapCoordinates(e.pos()))
            else: 
                rubberband = QgsRubberBand(self.canvas, False)
                rubberband.setColor(QColor(Qt.red))
                newPoint = self.toMapCoordinates(e.pos())
                points = [QgsPointXY(self.latestPoint.x(),self.latestPoint.y()),QgsPointXY(newPoint.x(),newPoint.y())]
                self.pointList.append(QgsPointXY(newPoint.x(),newPoint.y()))
                rubberband.setToGeometry(QgsGeometry.fromPolylineXY(points), None)
                self.rubberbandList.append(rubberband)
                self.latestPoint = newPoint
        elif e.button() == Qt.RightButton:
            self.Done = True
            self.poly.setGeometry(QgsGeometry.fromPolygonXY([self.pointList]))  # was fromPolygon() before
            self.polyComplete.emit(self.poly)

            for rubberband in self.rubberbandList:
                rubberband.reset()
            self.rubberband1.reset()
            self.rubberband2.reset()    
            self.rubberbandList = []
            self.pointList = []
            self.latestPoint = None
            self.Done = False