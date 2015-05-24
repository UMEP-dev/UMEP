#-----------------------------------------------------------
#
# QGIS combo Manager is a python module to easily manage a combo
# box with a composer list and eventually relate it with one or
# several combos with list of corresponding fields.
#
# copyright    : (C) 2013 Denis Rouzaud
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

from PyQt4.QtCore import Qt


class ComposerCombo():
    def __init__(self, iface, widget, initComposer=""):
        self.widget = widget
        if hasattr(initComposer, '__call__'):
            self.initComposer = lambda: initComposer()
        else:
            self.initComposer = initComposer
        self.iface = iface

        # connect signal for composer and populate combobox
        iface.composerAdded.connect(self.__listComposer)
        iface.composerRemoved.connect(self.__listComposer)
        self.__listComposer()

    def getComposer(self):
        i = self.widget.currentIndex()
        if i == -1:
            return None
        return self.widget.itemData(i)

    def setComposer(self, composer):
        if composer is None:
            idx = -1
        else:
            if type(composer) == str:
                idx = self.widget.findText(composer)
            else:
                idx = self.widget.findData(composer, Qt.UserRole)
        self.widget.setCurrentIndex(idx)

    def __listComposer(self, composer=None):
        self.widget.clear()
        for composer in self.iface.activeComposers():
            title = composer.composerWindow().windowTitle()
            self.widget.addItem(title, composer)
            if title == self.initComposer:
                self.widget.setCurrentIndex(self.widget.count())


