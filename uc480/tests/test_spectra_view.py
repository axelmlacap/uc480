from uc480.core.app import SpectraAnalyzer as Backend
from uc480.core.app import SpectraViewerUi as Frontend

from lantz.core.log import log_to_screen, DEBUG
from lantz.qt import start_gui_app

log_to_screen(DEBUG)
backend = Backend(None)
start_gui_app(backend, Frontend)