from driver import Camera
from app import CameraViewer, CameraViewerUi
import utilities as utils

from lantz.qt.app import build_qapp

if __name__ == '__main__':

    from lantz.core import ureg

    from lantz.core.log import log_to_screen, log_to_socket, DEBUG

    from lantz.qt import start_gui_app, wrap_driver_cls

    # log_to_socket(DEBUG)
    log_to_screen(DEBUG)

    # Create a Qt aware version of instrument.
    QCamera = wrap_driver_cls(Camera)

    with QCamera() as camera:
        
        camera.display_mode = utils.DisplayMode.IS_SET_DM_DIB
        
        camera.allocate_memory()
        camera.set_memory()
        camera.set_auto_color_mode()
        
        camera.capture_video(utils.Timeout.IS_DONT_WAIT)
        
        # We then create the backend and provide the driver we have just created
        # This will be bound to the corresponding instrument slot
        app = CameraViewer(interval=0, camera=camera)
        
        # Then we use the start_gui_app. Notice that we provide the class for the Ui, not an instance
        start_gui_app(app, CameraViewerUi)
