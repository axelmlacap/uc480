from uc480.core import Camera
from uc480.core import CameraControl, CameraSave, SpectraAnalyzer, SpectraSave, FFTAnalyzer, Main, MainUi

#from lantz.qt.app import build_qapp

if __name__ == '__main__':

    from lantz.core.log import log_to_screen, log_to_socket, DEBUG, ERROR, INFO
    from lantz.qt import start_gui_app, wrap_driver_cls

#    log_to_socket(DEBUG)
    log_to_screen(ERROR)
    
    QCamera = wrap_driver_cls(Camera)

    with QCamera() as camera:
        control_be = CameraControl(camera=camera)
        camera_save_be = CameraSave(camera_control_be=control_be)
        spectra_be = SpectraAnalyzer(camera_control_backend=control_be)
        save_be = SpectraSave(spectra_analyzer_be=spectra_be)
        fft_be = FFTAnalyzer(spectra_analyzer_backend=spectra_be)
        
        app = Main(control_be=control_be, camera_save_be=camera_save_be, spectra_be=spectra_be, save_be=save_be, fft_be=fft_be)
        start_gui_app(app, MainUi)
