from uc480.core.app import SpectraAnalyzer, SpectraAnalyzerUi

from lantz.core.log import log_to_screen, DEBUG
from lantz.qt import start_gui_app

log_to_screen(DEBUG)
spectra_be = SpectraAnalyzer(camera_control_backend=None)
start_gui_app(spectra_be, SpectraAnalyzerUi)