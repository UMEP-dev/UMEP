import traceback
from qgis.core import *
from PyQt4 import QtCore, QtGui, QtOpenGL

from OpenGL import GL
from OpenGL.GL import *
from OpenGL.GLU import *

import math
import numpy as np


class ModelWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal()

    def __init__(self, energy_array, asc_array, wall_array, cellsize, dynamic):
        QtCore.QObject.__init__(self)
        self.energy_array = energy_array
        self.asc_array = asc_array
        self.wall_array = wall_array
        self.cellsize = cellsize
        self.sizex = self.energy_array.shape[0]
        self.sizey = self.energy_array.shape[1]
        self.max_energy = np.amax(self.energy_array)
        self.minimum_energy = np.amin(self.energy_array)
        self.rangeofcolor = self.max_energy - self.minimum_energy
        self.dynamic = dynamic

        self.colorlimit = 0

        self.killed = False

    def run(self):
        ret = None

        try:
            genList = GL.glGenLists(1)
            GL.glNewList(genList, GL.GL_COMPILE)

            GL.glBegin(GL.GL_QUADS)

            for k in range(0, self.sizey):
                if self.killed is True:
                    break
                for l in range(0, self.sizex):
                    if self.killed is True:
                        break
                    z = self.asc_array[l][k]
                    e = self.energy_array[l][k]
                    self.roof(l, z, k, e)

            for i in range(0, len(self.wall_array)):
                if self.killed is True:
                    break
                wall_list = self.wall_array[i]
                y = wall_list[1]
                x = wall_list[0]
                zveg = self.asc_array[x][y]
                for j in range(2, len(wall_list)):
                    if self.killed is True:
                        break
                    e = wall_list[j]
                    zveg = zveg - self.cellsize
                    self.walls(x, zveg, y, e)

            GL.glEnd()
            GL.glEndList()

            if self.killed is False:
                self.progress.emit()
                ret = genList
        except Exception, e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def roof(self, x, y, z, e):
        if e < self.colorlimit:
            pass
        else:
            if self.dynamic:
                #self.qglColor(self.set_colordynamic(e))
                glColor4i(255, 0, 0, 255)
            else:
                self.qglColor(self.set_colorgroup(e))

            glVertex3f(x+self.cellsize, y+self.cellsize, z+0.0)
            glVertex3f(x+0.0, y+self.cellsize, z+0.0)
            glVertex3f(x+0.0, y+0.0, z+0.0)
            glVertex3f(x+self.cellsize, y+0, z+0.0)

            glVertex3f(x+0, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+0, y+0.0, z+-self.cellsize)
            glVertex3f(x+0, y+0.0, z+0.0)
            glVertex3f(x+0, y+self.cellsize, z+0)

            glVertex3f(x+0.0, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+0, z+-self.cellsize)
            glVertex3f(x+0.0, y+0, z+-self.cellsize)

            glVertex3f(x+self.cellsize, y+0, z+0.0)
            glVertex3f(x+self.cellsize, y+0, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+0.0)

            glVertex3f(x+self.cellsize, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+0.0, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+0.0, y+self.cellsize, z+0)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+0)

    def walls(self, x, y, z, e):
        if e < self.colorlimit:
            pass
        else:
            if self.dynamic:
                #self.qglColor(self.set_colordynamic(e))
                glColor4i(0, 0, 255, 255)
            else:
                self.qglColor(self.set_colorgroup(e))

            glVertex3f(x+self.cellsize, y+self.cellsize, z+0.0)
            glVertex3f(x+0.0, y+self.cellsize, z+0.0)
            glVertex3f(x+0.0, y+0.0, z+0.0)
            glVertex3f(x+self.cellsize, y+0, z+0.0)

            glVertex3f(x+0, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+0, y+0.0, z+-self.cellsize)
            glVertex3f(x+0, y+0.0, z+0.0)
            glVertex3f(x+0, y+self.cellsize, z+0)

            glVertex3f(x+0.0, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+0, z+-self.cellsize)
            glVertex3f(x+0.0, y+0, z+-self.cellsize)

            glVertex3f(x+self.cellsize, y+0, z+0.0)
            glVertex3f(x+self.cellsize, y+0, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+0.0)

            glVertex3f(x+self.cellsize, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+0.0, y+self.cellsize, z+-self.cellsize)
            glVertex3f(x+0.0, y+self.cellsize, z+0)
            glVertex3f(x+self.cellsize, y+self.cellsize, z+0)

    #sets color for voxels if dynamic
    def set_colordynamic(self, e):
        blue = (255 * (self.rangeofcolor - (e-self.minimum_energy)))/self.rangeofcolor
        red = math.floor((255 * (e-self.minimum_energy))/self.rangeofcolor)
        return QtGui.QColor(red, 0, blue, 255)

