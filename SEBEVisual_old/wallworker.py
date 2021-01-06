from qgis.PyQt import QtCore
from qgis.PyQt.QtGui import *
import traceback
from qgis.core import *


class wallWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    #error = QtCore.pyqtSignal(Exception, basestring)
    error = QtCore.pyqtSignal(object)
    # progress = QtCore.pyqtSignal()

    def __init__(self, ulcorner, cellsize, select_size, select_ulcorner, dir_path, wall_file):
        QtCore.QObject.__init__(self)
        self.xulc, self.yulc = ulcorner
        self.gridx, self.gridy = cellsize
        self.select_sizex, self.select_sizey = select_size
        self.select_xulc, self.select_yulc = select_ulcorner
        # self.minx = minx
        # self.maxy = maxy
        # self.sizex = sizex
        # self.sizey = sizey
        # self.point1 = point1
        # self.point2 = point2
        # self.xllcorner = xllcorner
        # self.ytlcorner = ytlcorner
        # self.cellsize = cellsize
        self.dir_path = dir_path
        self.wall_file = wall_file
        self.killed = False

    def run(self):
        ret = None
        try:
            wall_array = []

            select_xlrc = self.select_xulc + self.select_sizex * self.gridx
            select_ylrc = self.select_yulc + self.select_sizey * self.gridy

            xstart = (self.select_xulc - self.xulc)/self.gridx
            ystart = (self.select_yulc - self.yulc)/self.gridy

            # print("xstart, ystart")
            # print("%.5f %.5f" % (xstart, ystart))

            # rectangle covering selected area:
            rectpoint1 = QgsPointXY(select_xlrc, select_ylrc)
            rectpoint2 = QgsPointXY(self.select_xulc, self.select_yulc)
            rect = QgsRectangle(rectpoint1, rectpoint2)

            with open(self.dir_path + self.wall_file) as wallfile:
                next(wallfile)      # skip first line (header)
                for line in wallfile:
                    if self.killed is True:
                        break
                    wall_list = []
                    wallstring = line.split()
                    row = float(wallstring[0])   # y
                    col = float(wallstring[1])   # x
                    wall_list.append(row)
                    wall_list.append(col)

                    # create test-rectangle for wall-coordinate:
                    self.xulc, self.yulc
                    testpoint1 = QgsPointXY(self.xulc + ((col - 1) * self.gridx),
                                          self.yulc + ((row - 1) * self.gridy))
                    testpoint2 = QgsPointXY(self.xulc + (col * self.gridx),
                                          self.yulc + (row * self.gridy))
                    testrect = QgsRectangle(testpoint1, testpoint2)
                    if rect.contains(testrect):   # append wall-segment only if within selected ground area
                        zero_count = 0   # to allow value 0, if non-zero follows later
                        for e in wallstring[2:]:
                            if float(e) != 0:
                                if zero_count > 0:
                                    for izero in range(zero_count):
                                        wall_list.append(0.0)
                                    zero_count = 0   # reset counter
                                else:
                                    pass
                                wall_list.append(float(e))
                            else:
                                zero_count += 1   # count a wall-element with value 0
                        wall_list[0] = row - ystart - 1   # -1 to convert from 1-indexed to 0-indexed system
                        wall_list[1] = col - xstart - 1
                        wall_array.append(wall_list)
                    else:
                        pass
                        # print("test rectangle for wall coordinate is not within scene")
                    # self.progress.emit()

            # QMessageBox.critical(None, "Error", "test window: \nIs it shown in main-version?")
            # QMessageBox.critical(None, "Error",
            #                      (("c=%f, xst=%f, xerr=%f\n" % (ppcol, ppxstart, ppxstarterror)) +
            #                       ("r=%f, yst=%f, yerr=%f\n" % (pprow, ppystart, ppystarterror))
            #                       )
            #                      )
            # input()
            # print("testpoint 1, 2; selectpoint 1, 2; ul_x, ul_y")
            # print(testpoint1,testpoint2, rectpoint1, rectpoint2, self.xulc, self.yulc)
            if self.killed is False:
                # self.progress.emit()
                ret = wall_array
        #except Exception as e:
        except Exception:
            # forward the exception upstream
            ret = 0
            errorstring = self.print_exception()
            #self.error.emit(e, traceback.format_exc())
            self.error.emit(errorstring)
            # forward the exception upstream
            #self.error.emit(e, traceback.format_exc())
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

