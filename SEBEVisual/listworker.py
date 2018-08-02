from builtins import next
from builtins import str
from qgis.PyQt import QtCore
import traceback
from qgis.core import *


class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(Exception, str)
    progress = QtCore.pyqtSignal()

    def __init__(self, minx, maxy, sizex, sizey, point1, point2, xllcorner, ytlcorner, cellsize, dir_path, wall_file):
        QtCore.QObject.__init__(self)
        self.minx = minx
        self.maxy = maxy
        self.sizex = sizex
        self.sizey = sizey
        self.point1 = point1
        self.point2 = point2
        self.xllcorner = xllcorner
        self.ytlcorner = ytlcorner
        self.cellsize = cellsize
        self.dir_path = dir_path
        self.wall_file = wall_file
        self.killed = False

    def run(self):
        ret = None

        try:
            wall_array = []
            xstart = self.minx - self.xllcorner + 1
            ystart = self.ytlcorner - self.maxy + 1
            rectpoint = QgsPoint(self.point1.x() - self.xllcorner + 1, self.ytlcorner - self.point1.y() + 1)
            rectpoint2 = QgsPoint(self.point2.x() - self.xllcorner + 1, self.ytlcorner - self.point2.y() + 1)

            QgsMessageLog.logMessage('xstart: ' + str(xstart), level=QgsMessageLog.CRITICAL)
            QgsMessageLog.logMessage('ystart: ' + str(ystart), level=QgsMessageLog.CRITICAL)
            QgsMessageLog.logMessage('point1: ' + str(rectpoint), level=QgsMessageLog.CRITICAL)
            QgsMessageLog.logMessage('point2: ' + str(rectpoint2), level=QgsMessageLog.CRITICAL)
            #rectpoint = QgsPoint(xstart, yend)
            #rectpoint2 = QgsPoint(xend, ystart)
            rect = QgsRectangle(rectpoint, rectpoint2)

            with open(self.dir_path[0] + '/' + self.wall_file) as wallfile:
                next(wallfile)
                for line in wallfile:
                    if self.killed is True:
                        break
                    wall_list = []
                    string = line.split()
                    x = float(string[1])
                    y = float(string[0])
                    testpoint = QgsPoint(x, y)
                    testpoint2 = QgsPoint(x + self.cellsize - 0.00001, y + self.cellsize - 0.00001)
                    testrect = QgsRectangle(testpoint, testpoint2)
                    if testrect.intersects(rect):
                        for e in string:
                            if float(e) > 0:
                                wall_list.append(float(e))
                        wall_list[0] = y - ystart
                        wall_list[1] = x - xstart
                        wall_list[2:len(wall_list)] = reversed(wall_list[2:len(wall_list)])
                        wall_array.append(wall_list)
                    self.progress.emit()

            if self.killed is False:
                self.progress.emit()
                ret = wall_array
        except Exception as e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

