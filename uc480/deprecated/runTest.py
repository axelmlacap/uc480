from app import SpectraAnalyzer, SpectraMainUi, Main, MainUi

from lantz.qt.app import build_qapp



if __name__ == '__main__':

    from lantz.core import ureg

    from lantz.core.log import log_to_screen, log_to_socket, DEBUG

    from lantz.qt import start_gui_app, wrap_driver_cls
    
    from time import sleep

    # log_to_socket(DEBUG)
    log_to_screen(DEBUG)

    spectra_be = SpectraAnalyzer(test=True)
    main = Main(spectra_be=spectra_be)
    
    # Then we use the start_gui_app. Notice that we provide the class for the Ui, not an instance
    start_gui_app(main, SpectraMainUi)