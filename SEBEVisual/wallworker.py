import traceback
from qgis.PyQt import QtCore


class WallWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, ulcorner, cellsize, select_size, select_ulcorner, dir_path, wall_file):
        QtCore.QObject.__init__(self)
        self.xulc, self.yulc = ulcorner
        self.gridx, self.gridy = cellsize
        self.select_sizex, self.select_sizey = select_size
        self.select_xulc, self.select_yulc = select_ulcorner
        self.dir_path = dir_path
        self.wall_file = wall_file
        self.killed = False

    def run(self):
        ret = None
        try:
            wall_array = []
            xstart = int(round((self.select_xulc - self.xulc)/self.gridx))  # upper-left corner
            ystart = int(round((self.select_yulc - self.yulc)/self.gridy))

            xend = xstart + self.select_sizex  # lower-right corner
            yend = ystart + self.select_sizey

            with open(self.dir_path + self.wall_file) as wallfile:
                next(wallfile)      # skip first line (header)
                for line in wallfile:
                    if self.killed is True:
                        break
                    wall_list = []
                    wallstring = line.split()
                    row = int(wallstring[0])   # y
                    col = int(wallstring[1])   # x

                    # Append wall-segment only if within selected ground area:
                    if (ystart <= (row - 1) < yend and
                            xstart <= (col - 1) < xend):
                        # -1 to convert from 1-indexed to 0-indexed system
                        wall_list.append(row - ystart - 1)
                        wall_list.append(col - xstart - 1)
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
                        wall_array.append(wall_list)
                    else:
                        pass
                    self.progress.emit()
            if self.killed is False:
                self.progress.emit()
                ret = wall_array
        except Exception as e:
            # forward the exception upstream
            ret = None
            errorstring = self.print_exception()
            self.error.emit(errorstring)
        finally:
            self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def print_exception(self):
        return traceback.format_exc()
