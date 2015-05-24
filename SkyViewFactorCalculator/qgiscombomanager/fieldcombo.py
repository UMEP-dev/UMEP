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


from PyQt4.QtCore import Qt, QObject, pyqtSignal
from qgis.core import QgsVectorLayer

from layercombo import VectorLayerCombo

from optiondictionary import OptionDictionary

AvailableOptions = {"fieldType": None}


class FieldCombo(QObject):
    fieldChanged = pyqtSignal()

    def __init__(self, widget, vectorLayerCombo, initField="", options={}):
        QObject.__init__(self, widget)
        if not isinstance(vectorLayerCombo, VectorLayerCombo):
            raise NameError("You must provide a VectorLayerCombo.")
        self.options = OptionDictionary(AvailableOptions, options)
        self.widget = widget
        self.layerCombo = vectorLayerCombo
        self.initField = initField
        self.layerCombo.layerChanged.connect(self.__layerChanged)
        self.widget.currentIndexChanged.connect(self.currentIndexChanged)
        self.layer = None
        self.nFields = 0
        self.__layerChanged()

    def currentIndexChanged(self, i):
        self.fieldChanged.emit()

    def __layerChanged(self):
        if type(self.layer) == QgsVectorLayer:
            self.layer.attributeAdded.disconnect(self.__layerChanged)
            self.layer.attributeDeleted.disconnect(self.__layerChanged)
        if hasattr(self.initField, '__call__'):
            initField = self.initField()
        else:
            initField = self.initField
        self.widget.clear()
        self.nFields = 0
        self.layer = self.layerCombo.getLayer()
        if self.layer is None:
            return
        self.nFields = self.layer.pendingFields().count()
        self.layer.layerDeleted.connect(self.__layerDeleted)
        self.layer.attributeAdded.connect(self.__layerChanged)
        self.layer.attributeDeleted.connect(self.__layerChanged)
        i = -1
        for idx, field in enumerate(self.layer.pendingFields()):
            i += 1
            fieldAlias = self.layer.attributeDisplayName(idx)
            fieldName = field.name()
            self.widget.addItem(fieldAlias, fieldName)
            if not self.__isFieldValid(idx):
                j = self.widget.model().index(i, 0)
                self.widget.model().setData(j, 0, Qt.UserRole-1)
                continue
            if fieldName == initField:
                self.widget.setCurrentIndex(i)

    def __layerDeleted(self):
        self.layer = None

    def __isFieldValid(self, idx):
        if self.options.fieldType is None:
            return True
        #return self.layer.dataProvider().fields()[idx].type() == self.options.fieldType
        return self.layer.pendingFields()[idx].type() == self.options.fieldType

    def isValid(self):
        idx = self.getFieldIndex()
        if idx == -1:
            return False
        return self.__isFieldValid(idx)

    def getFieldAlias(self):
        i = self.widget.currentIndex()
        if i < 0 or i > self.nFields-1:
            return ""
        return self.widget.currentText()

    def getFieldName(self):
        i = self.widget.currentIndex()
        if i < 0 or i > self.nFields-1:
            return ""
        return self.widget.itemData(i)

    def getFieldIndex(self):
        i = self.widget.currentIndex()
        if i < 0 or i > self.nFields-1:
            return None
        return self.layer.fieldNameIndex(self.getFieldName())

    def setField(self, fieldName):
        idx = self.widget.findData(fieldName, Qt.UserRole)
        if idx != -1:
            self.widget.setCurrentIndex(idx)
        return idx
