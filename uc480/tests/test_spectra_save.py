from uc480.core.app import CameraSave as Backend
from uc480.core.app import CameraSaveUi as Frontend

from lantz.core.log import log_to_screen, DEBUG
from lantz.qt import start_gui_app

log_to_screen(DEBUG)
backend = Backend(None)
start_gui_app(backend, Frontend)