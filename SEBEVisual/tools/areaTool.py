'''
Created on 10 apr 2014

@author: nke
'''
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsPointXY, QgsGeometry
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand


class AreaTool(QgsMapToolEmitPoint):

    areaComplete = pyqtSignal(QgsPointXY, QgsPointXY)
    areaStart = None
    areaEnd = None
    areaRubberband1 = None
    areaRubberband2 = None
    areaRubberband3 = None
    areaRubberband4 = None


    def __init__(self, canvas):
        
        #Create a reference to the map canvas
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)

    def canvasMoveEvent(self, event):
        if self.areaStart:
            point = self.toMapCoordinates(event.pos())
            if self.areaRubberband1:
                 self.areaRubberband1.reset()
                 self.areaRubberband2.reset()
                 self.areaRubberband3.reset()
                 self.areaRubberband4.reset()
            else: 
                self.areaRubberband1 = QgsRubberBand(self.canvas, False)
                self.areaRubberband1.setColor(QColor(Qt.red))
                self.areaRubberband2 = QgsRubberBand(self.canvas, False)
                self.areaRubberband2.setColor(QColor(Qt.red))
                self.areaRubberband3 = QgsRubberBand(self.canvas, False)
                self.areaRubberband3.setColor(QColor(Qt.red))
                self.areaRubberband4 = QgsRubberBand(self.canvas, False)
                self.areaRubberband4.setColor(QColor(Qt.red))
            if self.areaEnd is None:
                point1 = QgsPointXY(point.x(), self.areaStart.y())
                point2 = QgsPointXY(self.areaStart.x(), point.y())
                points1 = [self.areaStart, point1]
                points2 = [self.areaStart, point2]
                points3 = [point1, point]
                points4 = [point2, point]
                self.areaRubberband1.setToGeometry(QgsGeometry.fromPolylineXY(points1), None) # was fromPolyline before. Might need a QgsPoint object
                self.areaRubberband2.setToGeometry(QgsGeometry.fromPolylineXY(points2), None)
                self.areaRubberband3.setToGeometry(QgsGeometry.fromPolylineXY(points3), None)
                self.areaRubberband4.setToGeometry(QgsGeometry.fromPolylineXY(points4), None)
            else:
                point1 = QgsPointXY(self.areaEnd.x(), self.areaStart.y())
                point2 = QgsPointXY(self.areaStart.x(), self.areaEnd.y())
                points1 = [self.areaStart, point1]
                points2 = [self.areaStart, point2]
                points3 = [point1, self.areaEnd]
                points4 = [point2, self.areaEnd]
                self.areaRubberband1.setToGeometry(QgsGeometry.fromPolylineXY(points1), None)
                self.areaRubberband2.setToGeometry(QgsGeometry.fromPolylineXY(points2), None)
                self.areaRubberband3.setToGeometry(QgsGeometry.fromPolylineXY(points3), None)
                self.areaRubberband4.setToGeometry(QgsGeometry.fromPolylineXY(points4), None)
    
    def canvasPressEvent(self, e):
        if self.areaStart is None:
            self.areaStart = self.toMapCoordinates(e.pos())
        else:
            self.areaEnd = self.toMapCoordinates(e.pos())
            
            self.areaComplete.emit(self.areaStart, self.areaEnd)
            
            self.areaRubberband1.reset()
            self.areaRubberband2.reset()
            self.areaRubberband3.reset()
            self.areaRubberband4.reset()

            self.areaStart = None
            self.areaEnd = None

