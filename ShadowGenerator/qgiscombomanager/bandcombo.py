#-----------------------------------------------------------
#
# QGIS Combo Manager is a python module to easily manage a combo
# box with a layer list and eventually relate it with one or
# several combos with list of corresponding fields.
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------


from PyQt4.QtCore import pyqtSignal, QObject

from layercombo import RasterLayerCombo


class BandCombo(QObject):
    bandChanged = pyqtSignal()

    def __init__(self, widget, rasterLayerCombo, initBand=None):
        QObject.__init__(self, widget)
        if not isinstance(rasterLayerCombo, RasterLayerCombo):
            raise NameError("You must provide a VectorLayerCombo.")
        self.widget = widget
        self.layerCombo = rasterLayerCombo
        self.initBand = initBand
        self.layerCombo.layerChanged.connect(self.__layerChanged)
        self.widget.currentIndexChanged.connect(self.currentIndexChanged)
        self.layer = None
        self.__layerChanged()

    def currentIndexChanged(self, i):
        self.bandChanged.emit()

    def __layerChanged(self):
        if hasattr(self.initBand, '__call__'):
            initBand = self.initBand()
        else:
            initBand = self.initBand
        self.widget.clear()
        self.layer = self.layerCombo.getLayer()
        if self.layer is None:
            return
        for b in range(self.layer.bandCount()):
            bandName = self.layer.bandName(b)
            self.widget.addItem(bandName)
            if b == initBand:
                self.widget.setCurrentIndex(b)

    def getBand(self):
        return self.widget.currentIndex()+1
