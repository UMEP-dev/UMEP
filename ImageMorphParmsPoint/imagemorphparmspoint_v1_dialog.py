# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageMorphParmsPointDialog
                                 A QGIS plugin
 This plugin calculates Morphometric parameters fro a high resolution DSM around a point of interest
                             -------------------
        begin                : 2015-01-12
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg GU
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

import os
import webbrowser

from PyQt4 import QtGui, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'imagemorphparmspoint_v1_dialog_base.ui'))


class ImageMorphParmsPointDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ImageMorphParmsPointDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

