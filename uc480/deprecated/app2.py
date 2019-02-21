import numpy as np
from matplotlib import pyplot as plt

from lantz.core import ureg
from lantz.qt.app import Backend, Frontend, InstrumentSlot, QtCore
from lantz.qt.app import BackendSlot
from lantz.qt.utils.qt import QtGui

Q = ureg.Quantity

class SpectraAnalyzer(Backend):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.enable = False
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500) # ms
        self.timer.timeout.connect(self.generate_test_image)
    
    def set_enable(self, value, timestamp=None):
        self.enable = value
        
        if value:
            self.timer.start()
            self.log_debug("Timer started")
        else:
            self.timer.stop()
            self.log_debug("Timer stopped")
    
    def generate_test_image(self):
        print('Here')


class SpectraAnalyzerUi(Frontend):
    
    gui = 'enable_box.ui'
    
    def connect_backend(self):
        super().connect_backend()
        
        self.widget.checkBox.stateChanged.connect(lambda new_value: self.backend.set_enable(new_value==2))


if __name__ == '__main__':
    
    from lantz.core.log import log_to_screen, DEBUG
    from lantz.qt import start_gui_app

    # log_to_socket(DEBUG)
    log_to_screen(DEBUG)

    spectra_be = SpectraAnalyzer()
    
    # Then we use the start_gui_app. Notice that we provide the class for the Ui, not an instance
    start_gui_app(spectra_be, SpectraAnalyzerUi)