import sys
import math
import os.path
import sqlite3 as lite

from PyQt4 import QtCore, QtGui, QtOpenGL

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL import GL


#-----------
# VARIABLES
#-----------



g_nearPlane = 1.
g_farPlane = 1000.
zoom = 65.
viewdistance = 100
horizonview = 0
startgroup1 = "200"
startgroup2 = "400"
startgroup3 = "600"
startgroup4 = "800"
limit = "0"
dynamic = True
hideveg = False
hideground = False






databasepath = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'Database'))

class Window(QtGui.QWidget):

    #Creates Gui elements for the 3D-model
    def __init__(self):
        super(Window, self).__init__()

        self.glWidget = GLWidget()
      
        #Color group

        self.groupBox1 = QtGui.QGroupBox("Colouring")
        self.groupBox1.setMaximumSize(150, 70)
        
        self.radioButton1 = QtGui.QRadioButton("Dynamic/Ranged")

        self.radioButton2 = QtGui.QRadioButton("Grouped")

        self.radioButton1.setChecked(1)
        
        self.group1Layout = QtGui.QVBoxLayout()

        self.group1Layout.addWidget(self.radioButton1)
        self.group1Layout.addWidget(self.radioButton2)
        
        self.groupBox1.setLayout(self.group1Layout)
        
        #Grouped options
        
        self.groupBox2 = QtGui.QGroupBox("Grouped options")
        self.groupBox2.setMaximumSize(150, 250)
        self.groupBox2.setDisabled(True)
        
        self.pushButton = QtGui.QPushButton("Update")
        #self.pushButton.clicked.connect(self.glWidget.reset_view)
        self.pushButton.clicked.connect(self.glWidget.update_Object)
        
        #self.label = QtGui.QLabel(str(self.glWidget.group1value))
        
        self.label1 = QtGui.QLabel("Blue <")
        self.label2 = QtGui.QLabel("> Green <")
        self.label3 = QtGui.QLabel("> Yellow <")
        self.label4 = QtGui.QLabel("> Orange <")
        self.label5 = QtGui.QLabel("> Red")
        self.group1line = QtGui.QLineEdit(startgroup1)
        self.group1line.textChanged.connect(self.set_group1)
        self.group2line = QtGui.QLineEdit(startgroup2)
        self.group2line.textChanged.connect(self.set_group2)
        self.group3line = QtGui.QLineEdit(startgroup3)
        self.group3line.textChanged.connect(self.set_group3)
        self.group4line = QtGui.QLineEdit(startgroup4)
        self.group4line.textChanged.connect(self.set_group4)

        self.group2Layout = QtGui.QVBoxLayout()
        
        self.group2Layout.addWidget(self.label1)
        self.group2Layout.addWidget(self.group1line)
        self.group2Layout.addWidget(self.label2)
        self.group2Layout.addWidget(self.group2line)
        self.group2Layout.addWidget(self.label3)
        self.group2Layout.addWidget(self.group3line)
        self.group2Layout.addWidget(self.label4)
        self.group2Layout.addWidget(self.group4line)
        self.group2Layout.addWidget(self.label5)
        self.group2Layout.addWidget(self.pushButton)
        
        self.groupBox2.setLayout(self.group2Layout)
       
        #limit group
        
        self.groupBox3 = QtGui.QGroupBox("Limit")
        self.groupBox3.setMaximumSize(150, 100)
        
        self.label6 = QtGui.QLabel("Hide areas with kwh under:")
        self.limitLine = QtGui.QLineEdit(limit)
        self.limitLine.textChanged.connect(self.set_limit)

        self.pushButton2 = QtGui.QPushButton("Update")
        self.pushButton2.clicked.connect(self.glWidget.update_Object)
        
        self.group3Layout = QtGui.QVBoxLayout()
        
        self.group3Layout.addWidget(self.label6)
        self.group3Layout.addWidget(self.limitLine)
        self.group3Layout.addWidget(self.pushButton2)
        
        self.groupBox3.setLayout(self.group3Layout)
        self.groupBox4 = QtGui.QGroupBox("Hide/Show")
        self.groupBox4.setMaximumSize(150, 90)
        
        self.checkbox = QtGui.QCheckBox("Hide vegetation")
        self.checkbox.stateChanged.connect(self.hide_veg)
        self.checkbox2 = QtGui.QCheckBox("Hide ground")
        self.checkbox2.stateChanged.connect(self.hide_ground)
        
        self.group4Layout = QtGui.QVBoxLayout()
        
        self.group4Layout.addWidget(self.checkbox)
        self.group4Layout.addWidget(self.checkbox2)
        
        self.groupBox4.setLayout(self.group4Layout)
        
        #Signals
        
        self.radioButton1.toggled.connect(self.set_dynamic)
        self.radioButton2.toggled.connect(self.set_grouped)
        
        #Add UI-components to main window
        
        mainLayout = QtGui.QHBoxLayout()
        mainLayout.stretch(1)
        modelLayout = QtGui.QHBoxLayout()
        modelLayout.stretch(1)
        self.toolsLayout = QtGui.QVBoxLayout()
        self.toolsLayout.stretch(1)
        self.toolsLayout.addStrut(10)

        modelLayout.addWidget(self.glWidget)
        
        self.toolsLayout.addWidget(self.groupBox1)
        self.toolsLayout.addWidget(self.groupBox2)
        self.toolsLayout.addWidget(self.groupBox3)
        self.toolsLayout.addWidget(self.groupBox4)

        mainLayout.addLayout(modelLayout)
        mainLayout.addLayout(self.toolsLayout)

        self.setLayout(mainLayout)

        self.setWindowTitle("3d Model")
    
    def set_dynamic(self):
        global dynamic
        dynamic = True
        self.groupBox2.setDisabled(True)
        self.glWidget.update_Object()
        
    def set_grouped(self):
        global dynamic
        dynamic = False
        self.groupBox2.setEnabled(True)
        self.glWidget.update_Object()

    def set_group1(self):
        try:
            self.glWidget.group1value = float(self.group1line.text())
        except:
            pass
        
    def set_group2(self):
        try:
            self.glWidget.group2value = float(self.group2line.text())
        except:
            pass
        
    def set_group3(self):
        try:
            self.glWidget.group3value = float(self.group3line.text())
        except:
            pass
        
    def set_group4(self):
        try:
            self.glWidget.group4value = float(self.group4line.text())
        except:
            pass
        
    def set_limit(self):
        try:
            self.glWidget.colorlimit = float(self.limitLine.text())
        except:
            pass

    def hide_veg(self):
        global hideveg
        if self.checkbox.isChecked():
            hideveg = True
            self.glWidget.updateGL()
        else:
            hideveg = False
            self.glWidget.updateGL()
  
    def hide_ground(self):
        global hideground
        if self.checkbox2.isChecked():
            hideground = True
            self.glWidget.updateGL()
        else:
            hideground = False
            self.glWidget.updateGL()

#Creates the OpenGL window for 3D-model
class GLWidget(QtOpenGL.QGLWidget):

    #Sets up attributes used by model
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)

        self.object = 0
        self.veg = 0
        self.ground = 0
        
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.group1value = float(startgroup1)
        self.group2value = float(startgroup2)
        self.group3value = float(startgroup3)
        self.group4value = float(startgroup4)
        self.colorlimit = float(limit)
        
        con = None
        con = lite.connect(databasepath + '/sun.db')
    
        with con:
            cur = con.cursor()
            cur.execute("SELECT Avg(y), Avg(x), Avg(z) FROM Modelroof")
            row = cur.fetchone()
            self.starty = row[0]
            self.startx = row[1]
            self.startz = row[2]
            
            cur.execute("SELECT Min(Energy) From Modelroof")
            row = cur.fetchone()
            self.minEnergy = row[0]
            
            cur.execute("SELECT Max(Energy) From Modelroof")
            row = cur.fetchone()
            self.maxEnergy = row[0]
                
            cur.execute("SELECT Min(Energy) From Modelwalls")
            row = cur.fetchone()
            if row[0] < self.minEnergy:
                self.minEnergy = row[0]
            
            cur.execute("SELECT Max(Energy) From Modelwalls")
            row = cur.fetchone()
            if row[0] > self.maxEnergy:  
                self.maxEnergy = row[0]
                
            self.rangeofcolor = self.maxEnergy - self.minEnergy
                  
        con.close()
        
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
        self.veg = self.makeVegetation()
        self.ground = self.makeGround()
        GL.glShadeModel(GL.GL_FLAT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_CULL_FACE)
    
    #Paints the window, runs for rotation etc
    def paintGL(self):
        global hideveg, hideground
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glLoadIdentity()
        gluLookAt(0, 0, -viewdistance, horizonview, 0, 0, 0, 1, 0)
    
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

    #Create camera movements
    def mouseMoveEvent(self, event):
        global zoom
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()

        if event.buttons() & QtCore.Qt.LeftButton:
            self.setXRotation(self.xRot + 8 * dy)
            self.setYRotation(self.yRot + 8 * dx)
        elif event.buttons() & QtCore.Qt.RightButton:
            global viewdistance, horizonview
            viewdistance -= dy
            horizonview -= dx
            self.updateGL()

        self.lastPos = event.pos()
    
    #Creates a display list for roofs and walls
    def makeObject(self):
        
        con = lite.connect(databasepath + '/sun.db')
        
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)

        GL.glBegin(GL.GL_QUADS)
        
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM Modelroof")
        
            while True:
                row = cur.fetchone()
        
                if row == None:
                    break
                x = row[1]-self.startx
                y = row[2]-self.startz
                z = row[0]-self.starty
                e = row[3]
                
                self.roof(x,y,z,e)
            
            cur.execute("SELECT * FROM Modelwalls")
        
            while True:
      
                row = cur.fetchone()
        
                if row == None:
                    break
                x = row[1]-self.startx
                y = row[2]-self.startz
                z = row[0]-self.starty
                e = row[3]
                
                self.wall(x,y,z,e)

        #self.surface(0, 0, 0)

        #self.wall(0, 0, 0)
        
        GL.glEnd()
        GL.glEndList()
        con.close()
        return genList
    
    #Create display lists for vegetation
    def makeVegetation(self):
        
        con = None
        
        con = lite.connect(databasepath + '/sun.db')
        
        genListveg = GL.glGenLists(1)
        GL.glNewList(genListveg, GL.GL_COMPILE)

        GL.glBegin(GL.GL_QUADS)
        
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM Modelvegetation")
        
            while True:
                row = cur.fetchone()
        
                if row == None:
                    break
                x = row[1]-self.startx
                y = row[2]-self.startz
                z = row[0]-self.starty

                self.vegetation(x,y,z)
        
        GL.glEnd()
        GL.glEndList()
        con.close()
        return genListveg
    
    #Create display lists for ground
    def makeGround(self):
        
        con = None
        
        con = lite.connect(databasepath + '/sun.db')
        
        genListground = GL.glGenLists(1)
        GL.glNewList(genListground, GL.GL_COMPILE)

        GL.glBegin(GL.GL_QUADS)
        
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM Modelsurf")
        
            while True:
                row = cur.fetchone()
        
                if row == None:
                    break
                x = row[1]-self.startx
                y = row[2]-self.startz
                z = row[0]-self.starty
                
                self.surface(x,y,z)
        
        GL.glEnd()
        GL.glEndList()
        con.close()
        return genListground
    
    #Voxels for roofs
    def roof(self, x, y, z, e):
        if e < self.colorlimit:
            pass
        else:
            if dynamic:
                self.qglColor(self.set_colordynamic(e))
            else:
                self.qglColor(self.set_colorgroup(e))

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

    #Voxels for walls
    def wall(self, x, y, z, e):
        if e < self.colorlimit:
            pass
        else:
            if dynamic:
                self.qglColor(self.set_colordynamic(e))
            else:
                self.qglColor(self.set_colorgroup(e))
                                   
            glVertex3f(x+0.5,y+1,z+0.0);       
            glVertex3f(x+0.0,y+1.0,z+0.0);      
            glVertex3f(x+0.0,y+0.0,z+0.0);        
            glVertex3f(x+0.5,y+0,z+0.0);      
 
            glVertex3f(x+0,y+1,z+0);       
            glVertex3f(x+0,y+1.0,z+-0.5);       
            glVertex3f(x+0,y+0.0,z+-0.5);      
            glVertex3f(x+0,y+0.0,z+0.0);       

            glVertex3f(x+0.0,y+1.0,z+-0.5);        
            glVertex3f(x+0.5,y+1,z+-0.5);     
            glVertex3f(x+0.5,y+0,z+-0.5);        
            glVertex3f(x+0.0,y+0,z+-0.5);              
                        
            glVertex3f(x+0.5,y+0,z+0.0);
            glVertex3f(x+0.5,y+0,z+-0.5);   
            glVertex3f(x+0.5,y+1,z+-0.5);
            glVertex3f(x+0.5,y+1,z+0.0);
        
            glVertex3f(x+0.5,y+1,z+-0.5)      
            glVertex3f(x+0.0,y+1,z+-0.5)       
            glVertex3f(x+0.0,y+1,z+0)       
            glVertex3f(x+0.5,y+1,z+0) 
     
    #Voxels for ground   
    def surface(self, x, y, z):
        self.qglColor(QtGui.QColor(139,139,139,255))

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
     
    #Voxels for vegetation    
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
    
    #Sets color for voxels if grouped 
    def set_colorgroup(self, e):
        if e < self.group1value:
            return QtGui.QColor(0,0,255,255)
        elif e < self.group2value:
            return QtGui.QColor(0,255,0,255)
        elif e < self.group3value:
            return QtGui.QColor(255,255,0,255)
        elif e < self.group4value:
            return QtGui.QColor(255,165,0,255)
        elif e > self.group4value:
            return QtGui.QColor(255,0,0,255)
   
    #sets color for voxels if dynamic
    def set_colordynamic(self,e):
        blue = (255 * (self.rangeofcolor - (e-self.minEnergy)))/self.rangeofcolor
        red = math.floor((255 * (e-self.minEnergy))/self.rangeofcolor)
        return QtGui.QColor(red,0,blue,255)

if __name__ == '__main__':
    #def main(self):
    app = QtGui.QApplication()
    window = Window()
    window.show()
    app.exec_()

