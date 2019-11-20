from uc480.core import Camera, CameraControl, CameraControlUi
from uc480.utilities import enums

from lantz.core import ureg
from lantz.qt.app import Backend, Frontend, InstrumentSlot, QtCore
from lantz.qt.app import BackendSlot

from lantz.core.log import log_to_screen, log_to_socket, DEBUG, ERROR
from lantz.qt import start_gui_app, wrap_driver_cls

from pyueye import ueye

#    log_to_socket(DEBUG)
log_to_screen(DEBUG)

QCamera = wrap_driver_cls(Camera)

with QCamera() as camera:
    control_be = CameraControl(camera=camera)
    start_gui_app(control_be, CameraControlUi)
