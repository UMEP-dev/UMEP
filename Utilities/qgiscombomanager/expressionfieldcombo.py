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


from PyQt4.QtGui import QDialog
from qgis.gui import QgsExpressionBuilderDialog
from fieldcombo import FieldCombo


class ExpressionFieldCombo(FieldCombo):

    def __init__(self, widget, expressionWidget, vectorLayerCombo, initField="", options={}):
        FieldCombo.__init__(self, widget, vectorLayerCombo, initField, options)
        expressionWidget.clicked.connect(self.editExpression)
        self.windowTitle = "Expression based label"

    def editExpression(self):
        expr = ""
        if self.widget.currentIndex() >= self.nFields:
            expr = self.widget.currentText()

        self.exprDlg = QgsExpressionBuilderDialog(self.layer, expr)
        self.exprDlg.setWindowTitle(self.windowTitle)

        if self.exprDlg.exec_() == QDialog.Accepted:
            expression = self.exprDlg.expressionText()
            self.addExpression(expression)

    def getExpression(self):
        if self.widget.currentIndex() < 0:
            return None,None
        if self.widget.currentIndex() <= self.nFields-1:
            return self.getFieldName(), False
        else:
            return self.widget.currentText(), True

    def setExpression(self, expr):
        if self.setField(expr) != -1:
            return
        self.addExpression(expr)

    def addExpression(self, expr):
        # Only add the expression if the user has entered some text.
        if expr != "":
            self.widget.addItem(expr)
            self.widget.setCurrentIndex(self.widget.count() - 1)



