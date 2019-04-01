# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 12:55:59 2019

@author: Axel Lacapmesure
"""

from lantz.core import ureg
from lantz.qt import QtCore

from matplotlib import pyplot as plt

import numpy as np

from scipy.interpolate import interp1d

from enum import Enum


class FFT(QtCore.QObject):
    
    D_X_UNITS = "dimensionless"
    D_Y_UNITS = "dimensionless"
    
    class _interpolations(Enum):
        NONE = ''
        LINEAR = 'linear'
        NEAREST = 'nearest'
        ZERO = 'zero'
        SLINEAR = 'slinear'
        QUADRATIC = 'quadratic'
        CUBIC = 'cubic'
        PREVIOUS = 'previous'
        NEXT = 'next'
    
    interpolations = set(item.value for item in _interpolations)
    
    x_changed = QtCore.pyqtSignal(object)

    def __init__(self, x=None, y=None, x_units=None, y_units=None, buffer_size=1, interpolation='cubic'):
        super().__init__()
        
        self._x = np.zeros((0, ), dtype=float)
        self._y = np.zeros((0, ), dtype=float)
        self._interpolate = self._interpolations.CUBIC
        self._flip = False
        
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)
        
        # If None are passed, initialize with default values
        if x.ndim == 0:
            x = self._x
        if y.ndim == 0:
            y = self._y
        
        # Validate sizes
        if x.ndim != 0 and y.ndim != 0:
            if y.ndim == 1 and x.size != y.size:
                raise ValueError("FFT x and y data sizes must match.")
        
        self.x = x
        self.y = y
        
        self.x_units = x_units if x_units else self.D_X_UNITS
        self.y_units = y_units if y_units else self.D_Y_UNITS
        self.interpolation = interpolation
    
    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, value):
        value = np.array(value, dtype=float)
        
        if value.ndim == 0:
            return None
        if value.ndim == 1:
            self._x = value
            
            if value.size != self.y.size:
                self._y = np.zeros((value.size, ), dtype=float)
        elif value.ndim > 1:
            raise ValueError("FFT x data must be 1D array-like type.")
    
    @property
    def y(self):
        return self._y
    
    @y.setter
    def y(self, value):
        value = np.array(value, dtype=float)
        
        if value.ndim == 0:
            return None
        elif value.ndim == 1:
            pass
        elif value.ndim > 1:
            raise ValueError("FFT y value must be a one dimensional array.")
        
        if value.size != self._x.size:
            raise ValueError("FFT x and y data sizes must match.")
        
        self._y = value
    
    @property
    def x_units(self):
        return self._x_units
    
    @x_units.setter
    def x_units(self, value):
        if isinstance(value, type(None)):
            self._x_units = ureg.dimensionless
        if isinstance(value, ureg.Unit):
            self._x_units = value
        elif isinstance(value, str):
            self._x_units = ureg(value).units
        else:
            raise TypeError("Units must be either a string or a valid pint unit.")
    
    @property
    def y_units(self):
        return self._y_units
    
    @y_units.setter
    def y_units(self, value):
        if isinstance(value, type(None)):
            self._y_units = ureg.dimensionless
        if isinstance(value, ureg.Unit):
            self._y_units = value
        elif isinstance(value, str):
            self._y_units = ureg(value).units
        else:
            raise TypeError("Units must be either a string or a valid pint unit.")
    
    @property
    def interpolation(self):
        return self._interpolation.value
    
    @interpolation.setter
    def interpolation(self, value):
        if isinstance(value, str):
            self._interpolation = self._interpolations(value.lower())
        elif isinstance(value, type(self._interpolations.NONE)):
            self._interpolation = self._interpolations(value.value)
        else:
            raise TypeError("FFT interpolation value must be a valid string or a interpolation enum element.")
    
    @property
    def flip(self):
        return self._flip
    
    @flip.setter
    def flip(self, value):
        self._flip = bool(value)
    
    @property
    def wavenumber(self):
        return self._wavenumber
    
    @property
    def raw_wavenumber(self):
        return self._raw_wavenumber
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    @property
    def absolute(self):
        return np.abs(self.y.flatten())
    
    @property
    def power(self):
        return np.abs(self.y.flatten())**2
    
    def plot(self):
        plt.figure()
        plt.plot(self.x, self.y)
        plt.grid()
        plt.xlabel("Position [{}]".format(self.x_units))
        plt.ylabel("Intensity [{}]".format(self.y_units))
    
#    def update_data(self, new_x=None, new_y=None):
#        new_x = np.array(new_x, dtype=float)
#        new_y = np.array(new_y, dtype=float)
#        
#        if new_x.ndim == 0 and new_y.ndim == 0:
#            return None
#        elif new_x.ndim == 1 and new_y.ndim == 1:
#            if new_x.shape != new_y.shape:
#                raise ValueError("Spectrum x and y data sizes must match.")
#            else:
#                self.x = new_x
#                self.process()
#        elif new_x.ndim == 1:
#            # Validations are within _RawSpectra
#            self.x = new_x
#        elif new_y.ndim == 1:
#             # Validations are within _RawSpectra
#            self.raw.y = new_y
#            self.process()
#        else:
#            raise ValueError("Spectrum data must be 1D array-like type.")
    
    def update_x(self, wavelength=None, wavenumber=None):
        raw_wavenumber = wavenumber
        
        if isinstance(wavelength, type(None)) and isinstance(raw_wavenumber, type(None)):
            return None
        elif not isinstance(wavelength, type(None)) and isinstance(raw_wavenumber, type(None)):
            raw_wavenumber = 2*np.pi/wavelength
            if raw_wavenumber[1]-raw_wavenumber[0] >= 0:
                self.flip = False
            else:
                raw_wavenumber = np.flip(raw_wavenumber)
                self.flip = True
        
        if self.interpolation:
            min_k = raw_wavenumber[0]
            max_k = raw_wavenumber[-1]
            n = raw_wavenumber.size
            
            wavenumber = np.linspace(min_k, max_k, n)
        else:
            wavenumber = raw_wavenumber
        
        self._raw_wavenumber = raw_wavenumber
        self._wavenumber = wavenumber
        self._sample_rate = np.mean(np.diff(wavenumber))
        self.x = np.fft.rfftfreq(self.wavenumber.size, 1./self.sample_rate)
    
    def update_from_spectrum(self, spectrum):
        y = spectrum.y.flatten()
        
        if self.flip:
            y = np.flip(y)
        
        if self.interpolation:
            y = interp1d(x=self.raw_wavenumber, y=y, kind=self.interpolation)(self.wavenumber)
        
        self.y = np.fft.rfft(y)
    
#    def save(self, path, processed=True, raw=False, dark=False, reference=False, decimals=10):
#        NL = '\n' # Newline character
#        SEP = '\t' # Delimiter/separator character
#        fmt = '%.'+str(decimals)+'g'
##        print("Called spectrum.save. Saving: processed {} raw {} dark {} reference {}".format(processed, raw, dark, reference))
#        
#        header = 'Date: {}'.format(datetime.now()) + NL
#        header += 'Mode: {}'.format(self.mode) + NL
#        header += 'Normalization: {}'.format(self.normalize) + NL
#        header += 'Dark subtraction: {}'.format(self.subtract_dark) + NL
#        header += 'Buffer size: {}'.format(self.raw.buffer.size) + NL
#        header += NL
#        header += 'Wavelength [{}]'.format(self.raw.x_units)
#        
#        output = self.processed.x
#        
#        if processed and not isinstance(self.processed, type(None)):
#            output = np.vstack((output, self.processed.y))
#            header += SEP + 'Processed'
#        if dark and not isinstance(self.dark, type(None)):
#            output = np.vstack((output, self.dark.y))
#            header += SEP + 'Dark'
#        if reference and not isinstance(self.reference, type(None)):
#            output = np.vstack((output, self.reference.y))
#            header += SEP + 'Reference'
#        if raw and not isinstance(self.raw, type(None)):
#            output = np.vstack((output, self.raw.y))
#            header += SEP + 'Raw'
#        
#        output = output.transpose()
#        
#        np.savetxt(path, output, fmt=fmt, delimiter=SEP, newline=NL, header=header)
#    
#    @classmethod
#    def from_file(cls, path=None):
#        NL = '\n' # Newline character
#        SEP = '\t' # Delimiter/separator character
#        
#        if not path:
#            path = file_dialog_open()
#        
#        # First read header
#        header = []
#        
#        with open(path, 'r') as file:
#            # Seart for header start flag:
#            while True:
#                line = file.readline()
#                if line[0] != "#":
#                    break
#                else:
#                    header.append(line.replace("# ",""))
#        
#        # Parse properties
#        props = {}
#        for line in header[0:-1]:
#            try:
#                key, value = tuple(split(": ", line))
#                key = key.lower().replace(" ","_")
#                
#                if key == "date":
#                    pass
#                elif key == "mode":
#                    pass
#                elif key == "normalization":
#                    value = value == "True"
#                elif key == "dark_subtraction":
#                    value = value == "True"
#                elif key == "buffer_size":
#                    value = int(value)
#                
#                props[key] = value
#            except ValueError:
#                pass
#        
#        # Get column names
#        names = split(SEP, header[-1])
#        for index in range(len(names)):
#            names[index] = sub(NL+"|| \[.*\]", "", names[index].lower())
#        
#        # Import data and initialize return
#        data = np.loadtxt(fname=path, dtype=float, comments="#", delimiter=SEP)
##        raw_buffer_size = data.shape[1] - len(names) + 1
#        
#        spectrum = cls()
#        
#        if "wavelength" in names:
#            wavelength = data[:, names.index("wavelength")].flatten()
#        else:
#            wavelength = None
#        if "processed" in names:
#            spectrum.processed = spectrum._RawSpectrum(wavelength, data[:, names.index("processed")].flatten())
#        if "dark" in names:
#            dark = data[:, names.index("dark").flatten()]
#            spectrum.dark = spectrum._RawSpectrum(wavelength, dark)
#        if "reference" in names:
#            spectrum.reference = spectrum._RawSpectrum(wavelength, data[:, names.index("reference")].flatten())
#        if "raw" in names:
#            slc = slice(names.index("raw"), names.index("raw") + props["buffer_size"])
#            spectrum.raw = spectrum._RawSpectrum(wavelength, data[:, slc].transpose(), buffer_size=props["buffer_size"])
#
#        return spectrum