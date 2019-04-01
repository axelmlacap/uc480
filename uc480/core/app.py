# -*- coding: utf-8 -*-

from .camera import CameraControl, CameraSave, CameraControlUi, CameraSaveUi, ImageViewerUi
from .spectra import SpectraAnalyzer, SpectraSave, SpectraAnalyzerUi, SpectraSaveUi, SpectraViewerUi
from .fft import FFTAnalyzer, FFTAnalyzerUi, FFTViewerUi

from uc480.utilities import get_layout0

from lantz.qt.app import Backend, Frontend, BackendSlot

#class Header(Frontend):
#    gui = 'gui/title.ui'
#
#class ExpandableWidget(Backend):
#    backend = BackendSlot
#
#class ExpandableWidgetUi(Frontend):
#    gui = 'gui/emptybox.ui'
#    
#    def __init__(self, main_widget, name=None, enable_callback=None, expanded=False):
#        super().__init__()
#        
#        if not name:
#            name = main_widget.__class__.__name__
#        
#        self.header = Header.using_parent_backend()
#        self.main = main_widget.using_parent_backend()
#        
#        self.name = name
#        self.enable_callback = enable_callback
#        self.expanded = bool(expanded)    
#    
#    def setupUi(self):
#        super().setupUi()
#        
#        layout = get_layout0(vertical=True)
#        layout.add_widget(self.header)
#        layout.add_widget(self.frontend)


class Main(Backend):
    control_be: CameraControl = BackendSlot
    camera_save_be: CameraSave = BackendSlot
    spectra_be: SpectraAnalyzer = BackendSlot
    save_be: SpectraSave = BackendSlot
    fft_be: FFTAnalyzer = BackendSlot


class MainUi(Frontend):
    backend: Main
    
    gui = 'gui/main.ui'
    
    # leftbar
    control_ui: CameraControlUi = CameraControlUi.using('control_be')
    camera_save_ui: CameraSaveUi = CameraSaveUi.using('camera_save_be')
    spectra_ui: SpectraAnalyzerUi = SpectraAnalyzerUi.using('spectra_be')
    save_ui: SpectraSaveUi = SpectraSaveUi.using('save_be')
    fft_ui: FFTAnalyzerUi = FFTAnalyzerUi.using('fft_be')
    
    # central
    viewer_ui: ImageViewerUi = ImageViewerUi.using('control_be')
    spectra_viewer_ui: SpectraViewerUi = SpectraViewerUi.using('spectra_be')
    fft_viewer_ui: FFTViewerUi = FFTViewerUi.using('fft_be')
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.control_ui)
        layout.addWidget(self.camera_save_ui)
        layout.addWidget(self.spectra_ui)
        layout.addWidget(self.save_ui)
        layout.addWidget(self.fft_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_image_page = layout = get_layout0(vertical=False)
        layout.addWidget(self.viewer_ui)
        self.image_page.setLayout(layout)
        
        # Central, page 2
        self.l_spectrum_page = layout = get_layout0(vertical=False)
        layout.addWidget(self.spectra_viewer_ui)
        self.spectrum_page.setLayout(layout)
        
        # Central, page 3
        self.l_spectrum_page = layout = get_layout0(vertical=False)
        layout.addWidget(self.fft_viewer_ui)
        self.fft_page.setLayout(layout)


class CameraMainUi(Frontend):
    backend: Main
    
    gui = 'gui/main.ui'
    
    # leftbar
    control_ui: CameraControlUi = CameraControlUi.using('control_be')
    
    # central
    viewer_ui: ImageViewerUi = ImageViewerUi.using('control_be')
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.control_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_image_page = layout =  get_layout0(vertical=False)
        layout.addWidget(self.viewer_ui)
        self.image_page.setLayout(layout)


class SpectraMainUi(Frontend):
    backend: SpectraAnalyzer
    
    gui = 'gui/main.ui'
    
    # leftbar
    spectra_ui: SpectraAnalyzerUi = SpectraAnalyzerUi.using('spectra_be')    
    # central
    spectra_view_ui: SpectraViewerUi = SpectraViewerUi.using('spectra_be')
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.spectra_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_image_page = layout =  get_layout0(vertical=False)
        layout.addWidget(self.spectra_view_ui)
        self.image_page.setLayout(layout)