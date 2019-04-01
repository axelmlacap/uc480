from uc480.core.app import SpectraAnalyzer, SpectraSave
from uc480.core.app import SpectraAnalyzerUi, SpectraSaveUi, SpectraViewerUi
from uc480.utilities.func import get_layout0

from lantz.qt.app import Backend, Frontend, BackendSlot
from lantz.core.log import log_to_screen, DEBUG
from lantz.qt import start_gui_app

class Main(Backend):
    spectra_analyzer_be: SpectraAnalyzer = BackendSlot
    spectra_save_be: SpectraSave = BackendSlot

class MainUi(Frontend):
    backend: Main
    
    gui = '../core/gui/main.ui'
    
    # leftbar
    spectra_analyzer_ui = SpectraAnalyzerUi.using('spectra_analyzer_be')
    spectra_save_ui = SpectraSaveUi.using('spectra_save_be')
    
    # central
    spectra_viewer_ui = SpectraViewerUi.using('spectra_analyzer_be')
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.spectra_analyzer_ui)
        layout.addWidget(self.spectra_save_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_spectrum_page = layout = get_layout0(vertical=False)
        layout.addWidget(self.spectra_viewer_ui)
        self.spectrum_page.setLayout(layout)


log_to_screen(DEBUG)
spectra_analyzer_be = SpectraAnalyzer(None)
spectra_save_be = SpectraSave(None)

main_be = Main(spectra_analyzer_be=spectra_analyzer_be, spectra_save_be=spectra_save_be)

start_gui_app(main_be, MainUi)







