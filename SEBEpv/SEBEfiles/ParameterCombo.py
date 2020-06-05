"""
required for SEBEpv

created by Michael Revesz - michael.revesz@ait.ac.at
2017-03
"""

from PyQt4.QtCore import QObject


def load_data(datapath):
    """ Load parameters from file. """
    keys = []  # keys
    para = []  # parameters
    with open(datapath, 'r') as f:
        for line in f:
            if line == '\n':
                pass
            elif line[0] != '#':
                l = line.split(' ')
                l[0] = l[0].split('_')
                l[0] = ' '.join(l[0])
                keys.append(l[0])
                linepara = []
                for val in l[1:]:
                    if val != '':
                        linepara.append(float(val))
                para.append(linepara)
    return keys, para


class ParametersCombo(QObject):
    def __init__(self, widget, keys, params):
        QObject.__init__(self, widget)
        self.widget = widget
        self.currentItem = None
        self.keys = keys
        self.paramdict = {}

        for i in range(len(self.keys)):
            self.paramdict[self.keys[i]] = params[i]
        # get populate combobox
        self.get_items()

    def changed_selection(self):
        """set current item in widget"""
        self.currentItem = self.widget.currentText()

    def get_current_item(self):
        return self.currentItem

    def set_selection_index(self, key):
        idx = self.widget.findText(key)
        self.widget.setCurrentIndex(idx)

    def get_items(self):
        """ Populate combobox with keys """
        self.widget.clear()
        for item in self.keys:
            self.widget.addItem(item)
        self.widget.setCurrentIndex(-1)

