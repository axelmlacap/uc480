from uc480.core import Camera
from uc480.core import CameraControl, CameraSave, CameraSaveUi, CameraMain, CameraSaveMainUi
from uc480.utilities import enums

import numpy as np

#from lantz.qt.app import build_qapp

if __name__ == '__main__':

    from lantz.core.log import log_to_screen, log_to_socket, DEBUG, ERROR
    from lantz.qt import start_gui_app, wrap_driver_cls

#    log_to_socket(DEBUG)
    log_to_screen(ERROR)
    
    QCamera = wrap_driver_cls(Camera)

    with QCamera() as camera:
        control_be = CameraControl(camera=camera)
        camera_save_be = CameraSave(camera_control_be=control_be)
        
        app = CameraMain(control_be=control_be, camera_save_be=camera_save_be)
        start_gui_app(camera_save_be, CameraSaveUi)
