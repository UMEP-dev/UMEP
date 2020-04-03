'''
Created on 10 apr 2014

@author: nke
'''
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *

# class AreaTool(QgsMapToolEmitPoint):
# class AreaTool(QgsMapTool):
#     def __init__(self, canvas):
#         self.canvas = canvas
#         QgsMapToolEmitPoint.__init__(self, self.canvas)
#         self.rubberBand = QgsRubberBand(self.canvas, True)
#         self.rubberBand.setColor(Qt.red)
#         self.rubberBand.setWidth(1)
#         self.reset()

#     def reset(self):
#         self.startPoint = self.endPoint = None
#         self.isEmittingPoint = False
#         self.rubberBand.reset(True)

#     def canvasPressEvent(self, e):
#         self.startPoint = self.toMapCoordinates(e.pos())
#         self.endPoint = self.startPoint
#         self.isEmittingPoint = True
#         self.showRect(self.startPoint, self.endPoint)

#     def canvasReleaseEvent(self, e):
#         self.isEmittingPoint = False
#         r = self.rectangle()
#         if r is not None:
#           print("Rectangle:", r.xMinimum(),
#                 r.yMinimum(), r.xMaximum(), r.yMaximum()
#                 )

#     def canvasMoveEvent(self, e):
#         if not self.isEmittingPoint:
#           return

#         self.endPoint = self.toMapCoordinates(e.pos())
#         self.showRect(self.startPoint, self.endPoint)

#     def showRect(self, startPoint, endPoint):
#         self.rubberBand.reset(Qgis.Polygon)
#         if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
#           return

#         point1 = QgsPoint(startPoint.x(), startPoint.y())
#         point2 = QgsPoint(startPoint.x(), endPoint.y())
#         point3 = QgsPoint(endPoint.x(), endPoint.y())
#         point4 = QgsPoint(endPoint.x(), startPoint.y())

#         self.rubberBand.addPoint(point1, False)
#         self.rubberBand.addPoint(point2, False)
#         self.rubberBand.addPoint(point3, False)
#         self.rubberBand.addPoint(point4, True)    # true to update canvas
#         self.rubberBand.show()

#     def rectangle(self):
#         if self.startPoint is None or self.endPoint is None:
#           return None
#         elif (self.startPoint.x() == self.endPoint.x() or \
#               self.startPoint.y() == self.endPoint.y()):
#           return None

#           return QgsRectangle(self.startPoint, self.endPoint)

#     def deactivate(self):
#         QgsMapTool.deactivate(self)
#         self.deactivated.emit()


class AreaTool(QgsMapToolEmitPoint):
    '''
    classdocs
    '''
    areaComplete = pyqtSignal(QgsPoint, QgsPoint)
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
                point1 = QgsPoint(point.x(), self.areaStart.y())
                point2 = QgsPoint(self.areaStart.x(), point.y())
                points1 = [self.areaStart, point1]
                points2 = [self.areaStart, point2]
                points3 = [point1, point]
                points4 = [point2, point]
                self.areaRubberband1.setToGeometry(QgsGeometry.fromPolyline(points1), None)
                self.areaRubberband2.setToGeometry(QgsGeometry.fromPolyline(points2), None)
                self.areaRubberband3.setToGeometry(QgsGeometry.fromPolyline(points3), None)
                self.areaRubberband4.setToGeometry(QgsGeometry.fromPolyline(points4), None)
            else:
                point1 = QgsPoint(self.areaEnd.x(), self.areaStart.y())
                point2 = QgsPoint(self.areaStart.x(), self.areaEnd.y())
                points1 = [self.areaStart, point1]
                points2 = [self.areaStart, point2]
                points3 = [point1, self.areaEnd]
                points4 = [point2, self.areaEnd]
                self.areaRubberband1.setToGeometry(QgsGeometry.fromPolyline(points1), None)
                self.areaRubberband2.setToGeometry(QgsGeometry.fromPolyline(points2), None)
                self.areaRubberband3.setToGeometry(QgsGeometry.fromPolyline(points3), None)
                self.areaRubberband4.setToGeometry(QgsGeometry.fromPolyline(points4), None)
    
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

