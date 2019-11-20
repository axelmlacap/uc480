from uc480.core import Camera
from uc480.core import CameraControl, CameraSave, SpectraAnalyzer, SpectraSave, FFTAnalyzer, Main, MainUi
from uc480.utilities import enums

from pyueye import ueye

import numpy as np

from lantz.core.log import log_to_screen, log_to_socket, DEBUG, ERROR
from lantz.qt import start_gui_app, wrap_driver_cls

log_to_screen(DEBUG)

QCamera = wrap_driver_cls(Camera)

camera = QCamera()
