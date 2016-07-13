# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SUEWSPrepareDialog
                                 A QGIS plugin
 This pluin prepares input data to SUEWS v2015a
                             -------------------
        begin                : 2015-10-25
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import pyqtSignal, QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QImage, QLabel, QPixmap, QLineEdit, QFormLayout, QIntValidator, \
    QGroupBox, QGridLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QFileDialog, QFont

from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import os

# import xlrd

import urllib2

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'template_widget.ui'))


class TemplateWidget(QtGui.QWidget, FORM_CLASS):

    edit_mode_signal = pyqtSignal()
    cancel_edits_signal = pyqtSignal()
    checkbox_signal = pyqtSignal()
    make_edits_signal = pyqtSignal(object, object, object, object)

    def __init__(self, sheet, outputfile, title, code=None, default_combo=None, sitelist_pos=None, parent=None):
        """Constructor."""
        super(TemplateWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.sheet = sheet
        self.outputfile = outputfile
        self.title = title
        self.code = code
        self.default_combo = default_combo
        self.setupUi(self)
        self.sitelist_pos = sitelist_pos
        self.lineedit_list = None

    def setup_widget(self):
        font = QFont()
        font.setBold(True)
        self.groupBox2.setFont(font)
        self.groupBox2.setTitle(self.title)
        self.lineedit_list = self.setup_dynamically()
        self.setup_combo()
        self.setup_values()
        self.comboBox.currentIndexChanged.connect(lambda: self.setup_values())
        self.setup_signals()

    def setup_combo(self):
        if self.comboBox.count() > 0:
            self.comboBox.clear()
        for row in range(3, self.sheet.nrows):
            val = self.sheet.cell_value(row, 0)
            if int(val) == -9:
                break
            else:
                if self.code is None:
                    self.comboBox.addItem(str(int(val)))
                else:
                    if self.code == int(self.sheet.cell_value(row, self.sheet.ncols-1)):
                        self.comboBox.addItem(str(int(val)))
                    else:
                        pass
        if self.default_combo is not None:
            index = self.comboBox.findText(str(self.default_combo))
            self.comboBox.setCurrentIndex(index)

    def setup_values(self):
        try:
            code = self.comboBox.currentText()
            code = int(code)
            for row in range(3, self.sheet.nrows):
                #self.setup_image(row)
                val = self.sheet.cell_value(row, 0)
                val = int(val)
                if val == code:
                    values = self.sheet.row_values(row, 1)
                    for x in range(0, len(values)):
                        if values[x] == "!":
                            explanation = ""
                            for y in range(len(values)-4, 0, -1):
                                if values[y] == "!":
                                    break
                                else:
                                    explanation += str(self.sheet.cell_value(1, y+1))
                                    explanation += ": "
                                    explanation += str(values[y])
                                    explanation += "\n"
                            self.exp_label.setText(explanation)
                            break
                        lineEdit = self.lineedit_list[x]
                        lineEdit.setText(str(values[x]))
                    break
        except ValueError as e:
            QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
            pass

    def setup_signals(self):
        self.editButton.clicked.connect(self.edit_mode)
        self.cancelButton.clicked.connect(self.cancel_edits)
        self.changeButton.clicked.connect(self.make_edits)
        self.checkBox.stateChanged.connect(self.checkbox_changed)

    def checkbox_changed(self):
        if self.checkBox.isChecked():
            self.comboBox.setEnabled(False)
            self.comboBox_uniquecodes.setEnabled(True)
            self.checkbox_signal.emit()
        else:
            self.comboBox.setEnabled(True)
            self.comboBox_uniquecodes.setEnabled(False)
            self.comboBox_uniquecodes.clear()

    def edit_mode(self):
        self.edit_mode_signal.emit()

        for x in range(0, len(self.lineedit_list)):
            self.lineedit_list[x].setEnabled(1)
        self.editButton.setEnabled(0)
        self.changeButton.setEnabled(1)
        self.cancelButton.setEnabled(1)

    def cancel_edits(self):
        self.cancel_edits_signal.emit()

        for x in range(0, len(self.lineedit_list)):
            self.lineedit_list[x].setEnabled(0)
        self.editButton.setEnabled(1)
        self.changeButton.setEnabled(0)
        self.cancelButton.setEnabled(0)

    def make_edits(self):
        self.make_edits_signal.emit(self.outputfile, self.sheet, self.lineedit_list, self.code)

        for x in range(0, len(self.lineedit_list)):
            self.lineedit_list[x].setEnabled(0)
        self.editButton.setEnabled(1)
        self.changeButton.setEnabled(0)
        self.cancelButton.setEnabled(0)

    def setup_dynamically(self):
        font = QFont()
        font.setBold(False)
        lineEdit_list = []
        Layout = QGridLayout()
        row = 0
        col = 0
        values = self.sheet.row_values(3, 1)
        for x in range(1, len(values)):
            if values[x-1] == "!":
                break
            else:
                cell = self.sheet.cell_value(1, x)
                tool_tip = self.sheet.cell_value(2, x)
                Layout2 = QVBoxLayout()
                label = QLabel(str(cell))
                label.setFont(font)
                lineedit = QLineEdit()
                lineedit.setFont(font)
                lineedit.setToolTip(str(tool_tip))
                lineedit.setEnabled(0)
                Layout2.addWidget(label)
                Layout2.addWidget(lineedit)
                vert_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Maximum)
                Layout2.addItem(vert_spacer)
                Layout.addLayout(Layout2, row, col)
                lineEdit_list.append(lineedit)
                if x > 0:
                    if x % 5 == 0:
                        row += 1
                        col = 0
                        vert_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Maximum)
                        Layout.addItem(vert_spacer)
                    else:
                        col += 1
        self.groupBox2.setLayout(Layout)
        return lineEdit_list

    def setup_image(self, row):
        values = self.sheet.row_values(row, 0)
        url = values[len(values)-3]
        if url == '':
            self.Image.clear()
        else:
            req = urllib2.Request(str(url))
            try:
                resp = urllib2.urlopen(req)
            except urllib2.HTTPError as e:
                if e.code == 404:
                    QgsMessageLog.logMessage("Image URL encountered a 404 problem", level=QgsMessageLog.CRITICAL)
                    self.Image.clear()
                else:
                    QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
                    self.Image.clear()
            except urllib2.URLError as e:
                QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=QgsMessageLog.CRITICAL)
                self.Image.clear()
            else:
                data = resp.read()
                #data = urllib.urlopen(str(url)).read()

                image = QImage()
                image.loadFromData(data)

                self.Image.setPixmap(QPixmap(image).scaledToWidth(139))

    def get_checkstate(self):
        return self.checkBox.isChecked()

    def get_combo_text(self):
        return self.comboBox.currentText()

    def get_lineedit_list(self):
        return self.lineedit_list

    def get_sitelistpos(self):
        return int(self.sitelist_pos)

    def get_title(self):
        return self.title




