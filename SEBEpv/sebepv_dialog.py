# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SEBEpv
                                 A QGIS plugin
 Derived from SEBE:
 Calculated solar energy on roofs, walls and ground
                             -------------------
        begin                : 2015-09-17
        copyright            : (C) 2015 by Fredrik Lindberg - Dag Wästberg
        email                : fredrikl@gvc.gu.se
        git sha              : $Format:%H$

 New SEBEpv:
 Calculate Photovoltaic power on walls and roofs
                              -------------------
        begin                : 2016-11-17
        copyright            : (C) 2016 by Michael Revesz
        email                : michael.revesz@ait.ac.at
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

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sebepv_dialog_base.ui'))


class SEBEDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SEBEDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
