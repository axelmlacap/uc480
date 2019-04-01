from uc480.core.app import SpectraAnalyzer, SpectraAnalyzerUi, SpectraSave, SpectraSaveUi, SpectraViewerUi, SpectraMainUi
from uc480.utilities import enums

from lantz.core import ureg
from lantz.qt.app import Backend, Frontend, InstrumentSlot, QtCore
from lantz.qt.app import BackendSlot

from lantz.core.log import log_to_screen, log_to_socket, DEBUG, ERROR
from lantz.qt import start_gui_app, wrap_driver_cls

#    log_to_socket(DEBUG)
log_to_screen(DEBUG)

spectra_be = SpectraAnalyzer(camera_control_backend=None)

# Then we use the start_gui_app. Notice that we provide the class for the Ui, not an instance
start_gui_app(spectra_be, SpectraAnalyzerUi)
