import logging
try:
    import OpenGL.GL as gl
    from OpenGL.GLU import gluPerspective, gluLookAt, gluOrtho2D
except:
    pass
from qgis.PyQt import QtWidgets
from qgis.PyQt import QtGui
from qgis.PyQt import QtCore
try:
    from PyQt5.QtOpenGL import *
except:
    pass
import numpy as np  # only for testing with test data arrays
from matplotlib import cm     # used to get "viridis"-colormap


class VisWidget(QGLWidget):
    def __init__(self, energy_array, dsm_array, wall_array, cellsizex, cellsizey, dlg, parent=None):
        super(VisWidget, self).__init__(parent)

        self.dlg = dlg
        self.finished_draw = False     # signal if objects are drawn to GL (bool)

        # Objects to be drawn:
        self.object = None
        self.compass = None

        self.lastPos = QtCore.QPoint()

        # data arrays, dimensions:
        self.energy_array = energy_array
        self.dsm_array = dsm_array
        self.wall_array = np.array(wall_array)
        self.cellsizex = cellsizex
        self.cellsizey = -cellsizey   # *(-1) - in y direction index increases inverse to geo-coordinates
        self.sizex = self.energy_array.shape[1]
        self.sizey = self.energy_array.shape[0]
        self.starty = self.sizey/2
        self.startx = self.sizex/2
        self.startz = np.nanmin(dsm_array)

        # View, projection, screen variables:
        self.minviewdist = 10
        self.maxviewdist = 5000
        self.viewdistance = max(self.sizex, self.sizey)*3
        self.viewshiftx = 0
        self.viewshifty = 0
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.g_nearPlane = 1.
        self.g_farPlane = 1000.
        self.viewangle = 65.
        self.width = None
        self.height = None
        self.side = None

        # coloring:
        self.dynamic = True
        self.colorlimit = float(0)  # be aware: nan values for dsm or roof energy is set to -9999
        self.min_energy, self.max_energy = 0, 0
        self.calc_minmax_energy()
        self.range_energy = 0
        self.calc_energyrange()

        # Define color map:
        self.rangesteps = 75      # number of color bins for color mapping
        # colors = [(0, 0, .5),
        #           (0, 0, 1),
        #           (0, 1, 1),
        #           (0, 1, 0),
        #           (1, 1, 0),
        #           (1, 0, 0),
        #           (.5, 0, 0)]
        # self.cm = LinearSegmentedColormap.from_list('colormap', colors, N=self.rangesteps)
        self.cm = cm.get_cmap('viridis', self.rangesteps)

    def reinitiate(self, energy_array, dsm_array, wall_array, cellsizex, cellsizey):
        """ Load new scene without resetting the complete widget. Keep view settings. """

        # data arrays, dimensions:
        self.energy_array = energy_array
        self.dsm_array = dsm_array
        self.wall_array = np.array(wall_array)
        self.cellsizex = cellsizex
        self.cellsizey = -cellsizey

        # coloring:
        self.dynamic = True
        self.colorlimit = float(0)  # be aware: nan values for dsm or roof energy is set to -9999
        self.min_energy, self.max_energy = 0, 0
        self.calc_minmax_energy()
        self.range_energy = 0
        self.calc_energyrange()

        # Objects to be drawn:
        self.object = self.createObject()
        self.compass = self.createCompass()

    def initializeGL(self):
        gl.glClearColor(1., 1., 1., 1.)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glShadeModel(gl.GL_FLAT)
        gl.glEnable(gl.GL_DEPTH_TEST)   # required, otherwise transparent.
        # gl.glEnable(gl.GL_CULL_FACE)  # DON'T use this!!

        self.object = self.createObject()
        self.compass = self.createCompass()

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        # Draw scene:
        gl.glViewport((self.width - self.side) // 2, (self.height - self.side) // 2, self.side, self.side)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gluLookAt(self.viewshiftx, self.viewshifty*np.cos(np.radians(self.xRot)),
                  self.viewdistance-self.viewshifty*np.sin(np.radians(self.xRot)),
                  self.viewshiftx, self.viewshifty*np.cos(np.radians(self.xRot)),
                  -self.viewshifty*np.sin(np.radians(self.xRot)),
                  0, 1, 0)

        gl.glRotated(-self.xRot, 1.0, 0.0, 0.0)
        gl.glRotated(self.yRot, 0.0, 1.0, 0.0)
        gl.glRotated(self.zRot, 0.0, 0.0, 1.0)

        gl.glCallList(self.object)

        # Draw compass:
        gl.glViewport((self.width + self.side) // 2 - 80, (self.height + self.side) // 2 - 80, 80, 80)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gluLookAt(0, 0, 27, 0, 0, 0, 0, 1, 0)

        gl.glRotated(-self.xRot, 1.0, 0.0, 0.0)
        gl.glRotated(self.yRot, 0.0, 1.0, 0.0)
        gl.glRotated(self.zRot, 0.0, 0.0, 1.0)

        gl.glCallList(self.compass)
        self.setFont(QtGui.QFont("Arial", 10))
        self.qglColor(QtGui.QColor(0, 0, 0))
        self.renderText(0, 3.3, 0, 'N')
        self.renderText(3.3, 0, 0, 'E')

    def resizeGL(self, width, height):
        # set the portion of Widget used for drawing:
        self.width = width
        self.height = height
        self.side = min(self.width, self.height)
        if self.side < 0:
            return

        # pass size to main application:
        self.dlg.update_windowsize(self.width, self.height)

        # viewport for scene:
        gl.glViewport((self.width - self.side) // 2, (self.height - self.side) // 2, self.side, self.side)
        # set the perspective of view:
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gluPerspective(self.viewangle, 1., self.g_nearPlane, self.g_farPlane)

        # viewport for compass:
        gl.glViewport((self.width + self.side) // 2 - 80, (self.height + self.side) // 2 - 80, 80, 80)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gluPerspective(20, 1., 15, -15)

    def minimumSizeHint(self):
        return QtCore.QSize(10, 10)

    def sizeHint(self):
        return QtCore.QSize(500, 500)

    def setXRotation(self, angle):
        angle = self.normalize_pihalf(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.updateGL()

    def setZRotation(self, angle):
        angle = self.normalize_twopi(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.updateGL()

    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    # Zoom
    def wheelEvent(self, event):
        dz = (event.angleDelta().y() / 8) // 1.5
        if ((self.viewdistance - dz) < self.minviewdist) & (dz > 0):
            pass
        elif ((self.viewdistance - dz) > self.maxviewdist) & (dz < 0):
            pass
        else:
            self.viewdistance -= dz
            self.updateGL()
            self.dlg.txt_update_zoom(self.viewdistance)

    # Create camera movements
    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()
        if event.buttons() & QtCore.Qt.LeftButton:
            self.setXRotation(self.xRot - dy // 5)  # tilt of scene: similar to a zenith angle
            self.setZRotation(self.zRot + dx)   # rotation around z axis of scene
        elif event.buttons() & QtCore.Qt.RightButton:
            self.viewshifty += dy#/10
            self.viewshiftx -= dx#/10
            self.updateGL()
        self.lastPos = event.pos()

    def mouseReleaseEvent(self,event):
        # Mouse Right Button Release Event
        if event.button() == QtCore.Qt.RightButton:
            self.dlg.txt_update_xshf(self.viewshiftx)
            self.dlg.txt_update_yshf(self.viewshifty)
        elif event.button() == QtCore.Qt.LeftButton:
            self.dlg.txt_update_zeni(self.xRot)
            self.dlg.txt_update_azim(self.zRot)
        else:
            pass

    def createObject(self):
        """Create the object: 3D scene to be plotted"""
        self.finished_draw = False
        gllist = gl.glGenLists(1)

        gl.glNewList(gllist, gl.GL_COMPILE)
        gl.glBegin(gl.GL_QUADS)

        for y in range(0, self.sizey):
            for x in range(0, self.sizex):
                z = self.dsm_array[y][x]
                e = self.energy_array[y][x]
                self.roof((x - self.startx) * self.cellsizex,
                          (self.starty - y) * self.cellsizey,
                          z - self.cellsizex - self.startz, e)   # z - cellsize, then top == z when drawn

        for i in range(0, len(self.wall_array)):
            wall_list = self.wall_array[i]
            wallheight = len(wall_list) - 2     # -2 because 2 points are coordinates
            y = int(wall_list[0])
            x = int(wall_list[1])
            z = self.dsm_array[y][x]

            x = (x - self.startx) * self.cellsizex
            y = (self.starty - y) * self.cellsizey

            delta = (np.floor(z / self.cellsizex) * self.cellsizex) - z   # diff: incremented wheight and true wheight
            z = z + delta - self.startz
            for j in range(0, wallheight):
                e = wall_list[j + 2]
                zw = z + self.cellsizex * j
                self.walls(x, y, zw, e)
        gl.glEnd()
        gl.glEndList()
        self.finished_draw = True

        return gllist

    def createCompass(self):
        """Create the object: compass"""
        gllist = gl.glGenLists(1)
        gl.glNewList(gllist, gl.GL_COMPILE)

        ORG = [0, 0, 0]
        XP = [3, 0, 0]
        YP = [0, 3, 0]
        ZP = [0, 0, 3]

        gl.glLineWidth(2.0)
        gl.glBegin(gl.GL_LINES)
        gl.glColor3f(1, 0, 0) # X axis is red.
        gl.glVertex3fv(ORG)
        gl.glVertex3fv(XP)
        gl.glColor3f(0, 1, 0) # Y axis is green.
        gl.glVertex3fv(ORG)
        gl.glVertex3fv(YP)
        gl.glColor3f(0, 0, 1) # z axis is blue.
        gl.glVertex3fv(ORG)
        gl.glVertex3fv(ZP)
        gl.glEnd()

        gl.glEndList()
        return gllist

    # Voxels for roofs
    def roof(self, x, y, z, e):
        if np.isnan(e):
            pass
        else:
            if self.dynamic:
                self.qglColor(self.set_colordynamic(e))
            else:
                self.qglColor(self.set_colorgroup(e))

            # left:
            gl.glVertex3f(x+0, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+0, y+0.0, z+self.cellsizex)
            gl.glVertex3f(x+0, y+0.0, z+0.0)
            gl.glVertex3f(x+0, y+self.cellsizey, z+0)
            # top:
            gl.glVertex3f(x+0.0, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+self.cellsizex, y+0, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+0, z+self.cellsizex)
            # right:
            gl.glVertex3f(x+self.cellsizex, y+0, z+0.0)
            gl.glVertex3f(x+self.cellsizex, y+0, z+self.cellsizex)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+0.0)
            # back:
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+self.cellsizey, z+0)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+0)
            # front:
            gl.glVertex3f(x+0.0, y+0.0, z+0.0)
            gl.glVertex3f(x+self.cellsizex, y+0, z+0.0)
            gl.glVertex3f(x+self.cellsizex, y+0.0, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+0.0, z+self.cellsizex)

    # Voxels for walls
    def walls(self, x, y, z, e):
        if np.isnan(e):
            pass
        else:
            if self.dynamic:
                self.qglColor(self.set_colordynamic(e))
            else:
                self.qglColor(self.set_colorgroup(e))

            # left:
            gl.glVertex3f(x+0, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+0, y+0.0, z+self.cellsizex)
            gl.glVertex3f(x+0, y+0.0, z+0.0)
            gl.glVertex3f(x+0, y+self.cellsizey, z+0)
            # right:
            gl.glVertex3f(x+self.cellsizex, y+0, z+0.0)
            gl.glVertex3f(x+self.cellsizex, y+0, z+self.cellsizex)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+0.0)
            # back:
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+self.cellsizey, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+self.cellsizey, z+0)
            gl.glVertex3f(x+self.cellsizex, y+self.cellsizey, z+0)
            # front:
            gl.glVertex3f(x+0.0, y+0.0, z+0.0)
            gl.glVertex3f(x+self.cellsizex, y+0, z+0.0)
            gl.glVertex3f(x+self.cellsizex, y+0.0, z+self.cellsizex)
            gl.glVertex3f(x+0.0, y+0.0, z+self.cellsizex)

    # Sets color for voxels if grouped
    def set_colorgroup(self, e):
        if e < self.group1value:
            return QtGui.QColor(43, 131, 186, 255)
        elif e < self.group2value:
            return QtGui.QColor(171, 221, 164, 255)
        elif e < self.group3value:
            return QtGui.QColor(255, 255, 191, 255)
        elif e < self.group4value:
            return QtGui.QColor(253, 174, 97, 255)
        elif e > self.group4value:
            return QtGui.QColor(215, 25, 28, 255)

    def set_colordynamic(self, v):
        r, g, b, _ = self.cm((v - self.min_energy) / (self.range_energy))
        return QtGui.QColor(QtGui.QColor.fromRgbF(r, g, b, 1.))

    def calc_minmax_energy(self):
        """Calculate the minimum and maximum energy."""
        np.place(self.energy_array, self.energy_array < self.colorlimit, np.nan)
        wallminimum = []
        wallmaximum = []

        for i in self.wall_array:
            try:
                wallminimum.append(min(i[2:]))
            except Exception as e:
                errmsg = "wallminimum.append(min(i[2:]))\nWall coordinates: " + str(i[0]) + ", " + str(i[1])
                logging.warning("%s\n%s\n%s" % (type(e).__name__, str(e), errmsg))
            try:
                wallmaximum.append(max(i[2:]))
            except Exception as e:
                errmsg = "wallmaximum.append(max(i[2:]))\nWall coordinates: " + str(i[0]) + ", " + str(i[1])
                logging.warning("%s\n%s\n%s" % (type(e).__name__, str(e), errmsg))
        try:
            emin = min(np.nanmin(self.energy_array), min(wallminimum))
        except Exception as e:
            errmsg = "emin = min(np.nanmin(self.energy_array), min(wallminimum))"
            logging.warning("%s\n%s\n%s\nSetting emin to 0." % (type(e).__name__, str(e), errmsg))
            emin = 0.
        try:
            emax = max(np.nanmax(self.energy_array), max(wallmaximum))
        except Exception as e:
            errmsg = "emax = max(np.nanmax(self.energy_array), max(wallmaximum))"
            logging.warning("%s\n%s\n%s\nSetting emax to emin+1." % (type(e).__name__, str(e), errmsg))
            emax = emin + 1.

        self.min_energy, self.max_energy = emin, emax

    def calc_energyrange(self):
        self.range_energy = (self.max_energy - self.min_energy)

    def normalize_twopi(self, angle):
        while angle < 0:
            angle += 360
        while angle > 360:
            angle -= 360
        return angle

    def normalize_pihalf(self, angle):
        while angle > 90:
            angle = 90
        while angle < 0:
            angle = 0
        return angle

    def get_viewdist(self):
        return self.viewdistance

    def set_viewdist(self, value):
        self.viewdistance = value

    def get_xshift(self):
        return self.viewshiftx

    def set_xshift(self, value):
        self.viewshiftx = value

    def get_yshift(self):
        return self.viewshifty

    def set_yshift(self, value):
        self.viewshifty = value

    def get_xrot(self):
        return self.xRot

    def set_xrot(self, value):
        self.xRot = value

    def get_yrot(self):
        return self.yRot

    def set_yrot(self, value):
        self.yRot = value

    def get_zrot(self):
        return self.zRot

    def set_zrot(self, value):
        self.zRot = value

    def get_min_energy(self):
        return self.min_energy

    def set_min_energy(self, value):
        self.min_energy = value

    def get_max_energy(self):
        return self.max_energy

    def set_max_energy(self, value):
        self.max_energy = value

    def get_finished_draw(self):
        return self.finished_draw


if __name__ == '__main__':

    energy = np.array([[1 ,1 ,1 ,1 ,1 ,0 ,0],
                       [1 ,3 ,3 ,3 ,1 ,0 ,0],
                       [1 ,3 ,3 ,3 ,3 ,1 ,0],
                       [1 ,3 ,3 ,3 ,3 ,3 ,1],
                       [1 ,1 ,1 ,1 ,1 ,1 ,1]])
    dsm = np.array([[1, 1, 1, 1, 2, 2, 2],
                    [1, 8, 8, 8, 1, 2, 2],
                    [1, 8, 8, 8, 8, 1, 2],
                    [1, 8, 8, 8, 8, 8, 1],
                    [1, 1, 1, 1, 1, 1, 1]])

    walls = np.array([[1, 1, 8, 8, 8, 7, 7, 6, 5, 4],
                      [1, 2, 4, 4, 4, 4, 4, 3, 3, 3],
                      [1, 3, 4, 4, 4, 4, 4, 3, 3, 3],
                      [2, 1, 8, 8, 8, 7, 7, 6, 5, 4],
                      [2, 4, 4, 4, 4, 4, 4, 3, 3, 3],
                      [3, 1, 8, 8, 8, 7, 7, 6, 5, 4],
                      [3, 2, 8, 8, 8, 7, 7, 6, 5, 4],
                      [3, 3, 8, 8, 8, 7, 7, 6, 5, 4],
                      [3, 4, 8, 8, 8, 7, 7, 6, 5, 4],
                      [3, 5, 8, 8, 8, 7, 7, 6, 5, 4]])

    app = QtGui.QApplication(["Draw a Scene using PyQt OpenGL"])
    widget = VisWidget(energy, dsm, walls, 1., 1. , "dlg")
    widget.show()
    app.exec_()