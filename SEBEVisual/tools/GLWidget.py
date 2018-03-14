import math
import os.path
import numpy as np
from modelworker import ModelWorker
from PyQt4 import QtCore, QtGui, QtOpenGL
from PyQt4.QtCore import QThread
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL import GL
from qgis.core import *


g_nearPlane = 1.
g_farPlane = 1000.
zoom = 65.
viewdistance = 200
horizonview = 0
verticalview = 0
startgroup1 = "300"
startgroup2 = "600"
startgroup3 = "600"
startgroup4 = "900"
startgroup5 = "1200"
limit = "0"
dynamic = True
hideveg = True
hideground = True

databasepath = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'Database'))


class GLWidget(QtOpenGL.QGLWidget):

    # Sets up attributes used by model
    def __init__(self, energy_array, asc_array, wall_array, cellsize, dlg, parent=None):
        super(GLWidget, self).__init__(parent)
        global horizonview, verticalview
        self.object = 0
        self.veg = 0
        self.ground = 0

        self.thread = None
        self.worker = None

        self.visDlg = dlg
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.group1value = float(startgroup1)
        self.group2value = float(startgroup2)
        self.group3value = float(startgroup3)
        self.group4value = float(startgroup4)
        self.group5value = float(startgroup5)
        self.colorlimit = float(limit)
        self.energy_array = energy_array
        self.asc_array = asc_array
        self.wall_array = wall_array
        self.cellsize = cellsize
        self.sizex = self.energy_array.shape[1]
        self.sizey = self.energy_array.shape[0]
        self.max_energy = np.amax(self.energy_array)
        self.minimum_energy = np.amin(self.energy_array)
        self.rangeofcolor = self.max_energy - self.minimum_energy
        self.starty = self.sizey/2
        self.startx = self.sizex/2
        self.startz = np.average(asc_array)
        self.lastPos = QtCore.QPoint()

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(400, 400)

    def setXRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.updateGL()

    def setYRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.yRot:
            self.yRot = angle
            self.updateGL()

    def setZRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.updateGL()

    #def reset_view(self):
    #    global viewdistance, horizonview
    #    viewdistance = 100
    #    horizonview = 0
    #   self.updateGL()

    def update_Object(self):
        self.object = self.makeObject()
        self.updateGL()

    #Initializing the model, runs once
    def initializeGL(self):
        self.qglClearColor(QtGui.QColor(240,240,240,255))
        self.object = self.makeObject()

        #self.startModWorker()
        #self.veg = self.makeVegetation()
        #self.ground = self.makeGround()
        #
        GL.glShadeModel(GL.GL_FLAT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_CULL_FACE)

        self.visDlg.label.hide()

    #Paints the window, runs for rotation etc
    def paintGL(self):
        global hideveg, hideground
        QgsMessageLog.logMessage('horizview: ' + str(horizonview), level=QgsMessageLog.CRITICAL)
        QgsMessageLog.logMessage('vertview: ' + str(verticalview), level=QgsMessageLog.CRITICAL)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glLoadIdentity()
        gluLookAt(0, self.startz, -viewdistance, horizonview, verticalview, 0, 0, 1, 0)

        GL.glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        GL.glRotated(self.yRot / 16.0, 0.0, 1.0, 0.0)
        GL.glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)

        GL.glCallList(self.object)
        if not hideveg:
            GL.glCallList(self.veg)

        if not hideground:
            GL.glCallList(self.ground)

    def resizeGL(self, width, height):
        side = min(width, height)
        if side < 0:
            return

        GL.glViewport((width - side) // 2, (height - side) // 2, side, side)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        gluPerspective(zoom, float(width)/float(height), g_nearPlane, g_farPlane)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    def wheelEvent(self, event):

        dz = event.delta()/6
        global viewdistance
        viewdistance -= dz
        self.updateGL()

    # Create camera movements
    def mouseMoveEvent(self, event):
        global zoom
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()

        if event.buttons() & QtCore.Qt.LeftButton:
            self.setXRotation(self.xRot + 8 * dy)
            self.setYRotation(self.yRot + 8 * dx)
        elif event.buttons() & QtCore.Qt.RightButton:
            global viewdistance, horizonview, verticalview
            #viewdistance -= dy
            verticalview -= dy
            horizonview -= dx
            self.updateGL()

        self.lastPos = event.pos()

    def startModWorker(self):
        worker = ModelWorker(self.energy_array, self.asc_array, self.wall_array, self.cellsize, dynamic)

        #self.visDlg.pushButtonVisualize.setText('Cancel')
        self.visDlg.pushButtonVisualize.clicked.disconnect()
        self.visDlg.pushButtonVisualize.clicked.connect(self.kill_worker)
        #self.visDlg.pushButton.setEnabled(False)

        # start the worker in a new thread
        thread = QThread(self.visDlg)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerError(self, e, exception_string):
        strerror = "Worker thread raised an exception: " + str(e)
        QgsMessageLog.logMessage(strerror.format(exception_string), level=QgsMessageLog.CRITICAL)

    def progress_update(self):
        pass

    def kill_worker(self, worker):
        self.visDlg.label.hide()
        self.worker.kill()

    def workerFinished(self, ret):
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        if ret is not None:
            self.object = ret
            GL.glShadeModel(GL.GL_FLAT)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_CULL_FACE)

        self.visDlg.pushButtonVisualize.setText('Visualize')
        self.visDlg.pushButtonVisualize.clicked.disconnect()
        #self.visDlg.pushButtonVisualize.clicked.connect(visualize)
        self.visDlg.pushButton.setEnabled(True)
        self.visDlg.label.hide()

    #Creates a display list for roofs and walls
    def makeObject(self):

        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)

        GL.glBegin(GL.GL_QUADS)

        for y in xrange(0, self.sizey):
            for x in xrange(0, self.sizex):
                z = self.asc_array[y][x]
                e = self.energy_array[y][x]
                self.roof(x - self.startx, z, y - self.starty, e)

        for i in xrange(0, len(self.wall_array)):
            wall_list = self.wall_array[i]
            y = int(wall_list[0])
            x = int(wall_list[1])
            zveg = self.asc_array[y][x]
            flipwall = np.flip(wall_list, 0)
            for j in xrange(0, len(wall_list) - 2):
            # for j in xrange(2, len(wall_list)):
                # e = wall_list[j]
                e = flipwall[j]
                # zveg = zveg - self.cellsize
                zveg = zveg + self.cellsize
                self.walls(x - self.startx, zveg, y - self.starty, e)

        GL.glEnd()
        GL.glEndList()
        return genList

    #Create display lists for vegetation
    # def makeVegetation(self):
    #
    #     con = None
    #
    #     con = lite.connect(databasepath + '/sun.db')
    #
    #     genListveg = GL.glGenLists(1)
    #     GL.glNewList(genListveg, GL.GL_COMPILE)
    #
    #     GL.glBegin(GL.GL_QUADS)
    #
    #     with con:
    #         cur = con.cursor()
    #         cur.execute("SELECT * FROM Modelvegetation")
    #
    #         while True:
    #             row = cur.fetchone()
    #
    #             if row == None:
    #                 break
    #             x = row[1]-self.startx
    #             y = row[2]-self.startz
    #             z = row[0]-self.starty
    #
    #             self.vegetation(x,y,z)
    #
    #     GL.glEnd()
    #     GL.glEndList()
    #     con.close()
    #     return genListveg

    #Create display lists for ground
    # def makeGround(self):
    #
    #     con = None
    #
    #     con = lite.connect(databasepath + '/sun.db')
    #
    #     genListground = GL.glGenLists(1)
    #     GL.glNewList(genListground, GL.GL_COMPILE)
    #
    #     GL.glBegin(GL.GL_QUADS)
    #
    #     with con:
    #         cur = con.cursor()
    #         cur.execute("SELECT * FROM Modelsurf")
    #
    #         while True:
    #             row = cur.fetchone()
    #
    #             if row == None:
    #                 break
    #             x = row[1]-self.startx
    #             y = row[2]-self.startz
    #             z = row[0]-self.starty
    #
    #             self.surface(x, y, z)
    #
    #     GL.glEnd()
    #     GL.glEndList()
    #     con.close()
    #     return genListground

    #Voxels for roofs
    def roof(self, x, y, z, e):
        if e < self.colorlimit:
            pass
        else:
            if dynamic:
                self.qglColor(self.set_colordynamic(e))
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
            if dynamic:
                self.qglColor(self.set_colordynamic(e))
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

    #Voxels for walls
    # def wall(self, x, y, z, e):
    #     if e < self.colorlimit:
    #         pass
    #     else:
    #         if dynamic:
    #             self.qglColor(self.set_colordynamic(e))
    #         else:
    #             self.qglColor(self.set_colorgroup(e))
    #
    #         glVertex3f(x+0.5,y+1,z+0.0);
    #         glVertex3f(x+0.0,y+1.0,z+0.0);
    #         glVertex3f(x+0.0,y+0.0,z+0.0);
    #         glVertex3f(x+0.5,y+0,z+0.0);
    #
    #         glVertex3f(x+0,y+1,z+0);
    #         glVertex3f(x+0,y+1.0,z+-0.5);
    #         glVertex3f(x+0,y+0.0,z+-0.5);
    #         glVertex3f(x+0,y+0.0,z+0.0);
    #
    #         glVertex3f(x+0.0,y+1.0,z+-0.5);
    #         glVertex3f(x+0.5,y+1,z+-0.5);
    #         glVertex3f(x+0.5,y+0,z+-0.5);
    #         glVertex3f(x+0.0,y+0,z+-0.5);
    #
    #         glVertex3f(x+0.5,y+0,z+0.0);
    #         glVertex3f(x+0.5,y+0,z+-0.5);
    #         glVertex3f(x+0.5,y+1,z+-0.5);
    #         glVertex3f(x+0.5,y+1,z+0.0);
    #
    #         glVertex3f(x+0.5,y+1,z+-0.5)
    #         glVertex3f(x+0.0,y+1,z+-0.5)
    #         glVertex3f(x+0.0,y+1,z+0)
    #         glVertex3f(x+0.5,y+1,z+0)

    #Voxels for ground
    # def surface(self, x, y, z):
    #     self.qglColor(QtGui.QColor(139,139,139,255))
    #
    #     glVertex3f(x+0.5,y+1,z+0.0)
    #     glVertex3f(x+0.0,y+1.0,z+0.0)
    #     glVertex3f(x+0.0,y+0.0,z+0.0)
    #     glVertex3f(x+0.5,y+0,z+0.0)
    #
    #     glVertex3f(x+0,y+1.0,z+-0.5)
    #     glVertex3f(x+0,y+0.0,z+-0.5)
    #     glVertex3f(x+0,y+0.0,z+0.0)
    #     glVertex3f(x+0,y+1,z+0)
    #
    #     glVertex3f(x+0.0,y+1.0,z+-0.5)
    #     glVertex3f(x+0.5,y+1,z+-0.5)
    #     glVertex3f(x+0.5,y+0,z+-0.5)
    #     glVertex3f(x+0.0,y+0,z+-0.5)
    #
    #     glVertex3f(x+0.5,y+0,z+0.0)
    #     glVertex3f(x+0.5,y+0,z+-0.5)
    #     glVertex3f(x+0.5,y+1,z+-0.5)
    #     glVertex3f(x+0.5,y+1,z+0.0)
    #
    #     glVertex3f(x+0.5,y+1,z+-0.5)
    #     glVertex3f(x+0.0,y+1,z+-0.5)
    #     glVertex3f(x+0.0,y+1,z+0)
    #     glVertex3f(x+0.5,y+1,z+0)

    # Voxels for vegetation
    def vegetation(self, x, y, z):
        self.qglColor(QtGui.QColor(0,255,0,255))

        glVertex3f(x+0.5,y+1,z+0.0)
        glVertex3f(x+0.0,y+1.0,z+0.0)
        glVertex3f(x+0.0,y+0.0,z+0.0)
        glVertex3f(x+0.5,y+0,z+0.0)

        glVertex3f(x+0,y+1.0,z+-0.5)
        glVertex3f(x+0,y+0.0,z+-0.5)
        glVertex3f(x+0,y+0.0,z+0.0)
        glVertex3f(x+0,y+1,z+0)

        glVertex3f(x+0.0,y+1.0,z+-0.5)
        glVertex3f(x+0.5,y+1,z+-0.5)
        glVertex3f(x+0.5,y+0,z+-0.5)
        glVertex3f(x+0.0,y+0,z+-0.5)

        glVertex3f(x+0.5,y+0,z+0.0)
        glVertex3f(x+0.5,y+0,z+-0.5)
        glVertex3f(x+0.5,y+1,z+-0.5)
        glVertex3f(x+0.5,y+1,z+0.0)

        glVertex3f(x+0.5,y+1,z+-0.5)
        glVertex3f(x+0.0,y+1,z+-0.5)
        glVertex3f(x+0.0,y+1,z+0)
        glVertex3f(x+0.5,y+1,z+0)

    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    # Sets color for voxels if grouped
    def set_colorgroup(self, e):
        if e < self.group1value:
            return QtGui.QColor(43,131,186,255)
        elif e < self.group2value:
            return QtGui.QColor(171,221,164,255)
        elif e < self.group3value:
            return QtGui.QColor(255,255,191,255)
        elif e < self.group4value:
            return QtGui.QColor(253,174,97,255)
        elif e > self.group4value:
            return QtGui.QColor(215,25,28,255)

    # sets color for voxels if dynamic
    def set_colordynamic(self, e):
        green = (255 * (self.rangeofcolor - (e-self.minimum_energy)))/self.rangeofcolor
        red = math.floor((255 * (e-self.minimum_energy))/self.rangeofcolor)
        return QtGui.QColor(red, 0, green, 255)
