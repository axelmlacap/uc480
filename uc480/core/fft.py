# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 13:01:25 2019

@author: Axel Lacapmesure
"""

from uc480.utilities import FFT

from lantz.qt.app import Backend, Frontend, QtCore
from lantz.core import ureg

import numpy as np

from pyqtgraph import PlotWidget

from time import monotonic


class FFTAnalyzer(Backend):
    
    new_data = QtCore.pyqtSignal(object, object)
    
    def __init__(self, spectra_analyzer_backend=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.enable = False
        self.initialized = False
        
        self.fft = FFT()
        self.spectra_analyzer_be = spectra_analyzer_backend
    
    def set_enable(self, value):
        self.enable = value
        self.log_debug("FFT enabled" if value else "FFT disabled")
    
    def link_spectra_analyzer(self):
        self.spectra_analyzer_be.new_data.connect(self.update_from_spectrum)
    
    def update_from_spectrum(self, spectrum):
        if self.enable:
            now = monotonic() * ureg.ms
            
            if not self.initialized:
                self.fft.update_x(spectrum.x)
                self.initialized = True
            
            self.fft.update_from_spectrum(spectrum)
            self.new_data.emit(self.fft, now)
    
    # Send/read signals' functions:
    def read_interpolation(self, value):
        self.fft.interpolation = value
    
    def read_update_x(self):
        self.fft.update_x(self.spectra_analyzer_be.spectrum.x)


class FFTAnalyzerUi(Frontend):
    
    backend: FFTAnalyzer
    
    gui = 'gui/fft.ui'
    
    interpolation_sg = QtCore.pyqtSignal(object)
    
    def setupUi(self):
        super().setupUi()
        
        # Connections
        self.widget.enable.stateChanged.connect(self.send_enable)
        self.widget.interp_combo.currentTextChanged.connect(self.send_interpolation)
    
    def connect_backend(self):
        super().connect_backend()
        
        # Outgoing signals
        self.interpolation_sg.connect(self.backend.read_interpolation)
        self.widget.update_x_btn.clicked.connect(self.backend.read_update_x)
        
        if not isinstance(self.backend.spectra_analyzer_be, type(None)):
            self.backend.link_spectra_analyzer()
    
    def send_enable(self, value):
        value = value==2
        self.backend.set_enable(value)
    
    def read_enable(self, value):
        self.widget.enable.setDown(value)
    
    def send_interpolation(self, value):
        value = value.lower()
        
        if value == "none":
            value = ""
        
        self.interpolation_sg.emit(value)


class FFTViewerUi(Frontend):
    
    backend: FFTAnalyzer
    
    gui = 'gui/image_viewer.ui'
    
    def setupUi(self):
        super().setupUi()
        
        self.widget = PlotWidget(parent=self)
        self.setCentralWidget(self.widget)
        
        self.plot_item = self.widget.getPlotItem()
        self.plot_item.setLabel('left', 'Intensity')
        self.plot_item.setLabel('bottom', 'Position')
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.enableAutoScale()
        
        self.plot_data_item = self.plot_item.plot(x=np.zeros((2,)), y=np.zeros((2,)))
    
    def connect_backend(self):
        super().connect_backend()
        
        self.backend.new_data.connect(self.refresh)
    
    def refresh(self, fft, timestamp=None):
        self.plot_data_item.setData(x=fft.x, y=fft.absolute)