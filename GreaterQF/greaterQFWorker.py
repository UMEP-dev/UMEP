from PyQt4.QtCore import QObject, pyqtSignal
from qgis.core import QgsMessageLog

# Initialize Qt resources from file resources.py
# Import the code for the dialog
import pickle
import tempfile
# System
import os.path
import traceback

# GreaterQF functions
from PythonQF.spatialHelpers import *
from PythonQF.Config import Config
from PythonQF.Params import Params
from PythonQF.Calcs3 import *

# Worker object for greaterQF execution
class GreaterQFWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    progress = pyqtSignal(float)

    # Execute GreaterQF in a separate thread
    def __init__(self, startDate, endDate, componentOptions, outputArea):
        QObject.__init__(self)
        self.killed = False
        self.startDate = startDate.toPyDate().strftime('%Y-%m-%d')
        self.endDate = endDate.toPyDate().strftime('%Y-%m-%d')
        self.doLatent = componentOptions['latent']
        self.doSensible = componentOptions['sensible']
        self.doWastewater = componentOptions['wastewater']
        self.outputArea = outputArea
        self.doAll = self.doLatent & self.doWastewater & self.doSensible

    def kill(self):
        self.killed = True

    def run(self):
        # Start the GreaterQF worker
        outs = None

        try:
            # Execute GreaterQf
            config = Config()
            dir = os.path.dirname(__file__)

            config.loadFromNamelist(os.path.join(dir, 'PythonQF/V32_Input.nml'))  # Model config

            configParams = {'spatial_domain': self.outputArea, 'start_date': self.startDate, 'end_date': self.endDate, \
                            'all_qf': self.doAll, 'sensible_qf': self.doSensible, 'latent_qf': self.doLatent, 'wastewater_qf': self.doWastewater,
                            'input_data_dir': os.path.join(dir, 'PythonQF/InputData/')}
            config.loadFromDictionary(configParams)

            params = Params(os.path.join(dir, 'PythonQF/parameters.nml'))  # Model params (not the same as input data)
            outs = mostcalcs(config, params)

            if type(outs['Data']) is type(None):
                raise ValueError('No output generated: {}'.format(type(outs)))

            # Convert to simpler data format
            outs['Data'] = outs['Data'].astype(np.float16)
            # Placeholder for loopy execution
            self.progress.emit(80)
            with open(os.path.join(tempfile.gettempdir(), 'greaterQF.pickled'), 'w+') as outFile:
                pickle.dump(outs, outFile)

        except Exception, e:
            self.error.emit(e, traceback.format_exc())

        self.finished.emit(outs)


