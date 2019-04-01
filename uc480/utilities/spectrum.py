# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 12:55:59 2019

@author: Axel Lacapmesure
"""

from .func import file_dialog_open

from .buffer import BufferCore

from lantz.qt import QtCore

from matplotlib import pyplot as plt

import numpy as np

from scipy.interpolate import interp1d

from enum import Enum

from datetime import datetime

from re import split, sub


class Spectrum(QtCore.QObject):
    
    wavelength_changed = QtCore.pyqtSignal(object)
    
    class _RawSpectrum(QtCore.QObject):
        
        D_X_UNITS = "px"
        D_Y_UNITS = "arb"
        
        def __init__(self, x=None, y=None, x_units=None, y_units=None, buffer_size=1):
            super().__init__()
            
            self.buffer = BufferCore(size=buffer_size)            
            
            x = np.array(x, dtype=float)
            y = np.array(y, dtype=float)
            
            # If None are passed, initialize with default values
            if x.ndim == 0:
                x = np.array([0, 1], dtype=float)
            if y.ndim == 0:
                y = np.zeros((self.buffer.size, x.size), dtype=float)
            
            # If 1D y value passed, reshape to 2D with wavelength in axis 1
            if y.ndim == 1:
                y = y.reshape((1, y.size))
            
            # Validate sizes
            if x.ndim != 0 and y.ndim != 0:
                if y.ndim == 1 and x.size != y.size:
                    raise ValueError("Spectrum x and y data sizes must match.")
                elif y.ndim == 2 and x.size != y.shape[1]:
                    raise ValueError("Spectrum x and y data sizes must match.")
            
            self._x = x
            self._y = np.zeros((self.buffer.size, y.shape[1]))
            self.y = y
            self.x_units = x_units if x_units else self.D_X_UNITS
            self.y_units = y_units if y_units else self.D_Y_UNITS
        
        def __getitem__(self, value):
            # Get indices ordered from first to last, then slice as indicated by value and reorder to mantain old-first order
            indices = np.flip(self.buffer.indices_new_first[value])
            
            x = self.x
            y = self.y[indices, :]
            
            spectrum = self.__class__(x=x, y=y, buffer_size=indices.size)
            spectrum.buffer.index = 0
            spectrum.buffer.count = self.buffer.count
            
            return spectrum
        
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
                
                if value.size != self.y.shape[1]:
                    self._y = np.zeros((self.buffer.size, value.size), dtype=float)
            elif value.ndim > 1:
                raise ValueError("Spectrum x data must be 1D array-like type.")
        
        @property
        def y(self):
            return self._y
        
        @y.setter
        def y(self, value):
            value = np.array(value, dtype=float)
            
            if value.ndim == 0:
                return None
            elif value.ndim == 1:
                value = value.reshape((1, value.size))
            elif value.ndim > 2:
                raise ValueError("Spectrum y value must be a one or two dimensional array.")
            
            if value.shape[1] != self._x.size:
                raise ValueError("Spectrum x and y data sizes must match.")
            
            for idx in range(value.shape[0]):
                self._y[self.buffer(), :] = value[idx, :]
        
        def average(self):
            x = self.x
            y = np.mean(self.y, axis=0)
            
            return self.__class__(x, y)
        
        def resize_buffer(self, new_size):
            old_size = self.buffer.size
            
            if new_size == old_size:
                return None
            
            # If shrinking, retain the latest elements from buffer
            if new_size < old_size:
                indices = np.flip(self.buffer.indices_new_first[0:new_size])
                self._y = self.y[indices, :]
                
                self.buffer.size = new_size
                self.buffer.index = new_size
                self.buffer.count = new_size
            
            # If expanding, pad with zeros
            if new_size > old_size:
                # First, reorder
                indices = self.buffer.indices_old_first
                old_block = self.y[indices, :]
                
                # Now, pad with zeros
                new_block = np.zeros((new_size-old_size, self.y.shape[1]))
                self._y = np.vstack((old_block, new_block))
                
                new_count = min(self.buffer.count, old_size)
                self.buffer.size = new_size
                self.buffer.index = new_count
                self.buffer.count = new_count
        
        def plot(self):
            plt.figure()
            plt.plot(self.x, self.y.flatten())
            plt.grid()
            plt.xlabel("Wavelength [{}]".format(self.x_units))
            plt.ylabel("Intensity [{}]".format(self.y_units))
        
        @classmethod
        def from_spectrum(cls, spectrum_object, spectrum_type='raw'):
            if spectrum_type=='raw':
                return cls(spectrum_object.raw.x, spectrum_object.raw.y)
            elif spectrum_type=='process':
                return cls(spectrum_object.process.x, spectrum_object.process.y)
            elif spectrum_type=='dark':
                return cls(spectrum_object.dark.x, spectrum_object.dark.y)
            elif spectrum_type=='reference':
                return cls(spectrum_object.reference.x, spectrum_object.reference.y)
    
    class _modes(Enum):
        INTENSITY = 'intensity'
        TRANSMISSION = 'transmission'
        ABSORBANCE = 'absorbance'
    
    modes = set(item.value for item in _modes)
    
    def __init__(self, x=None, y=None, mode='intensity', reference=None, dark=None, normalize=False, subtract_dark=False, averages=1):
        super().__init__()
        
        self._x = np.array([0, 1])
        self.raw = self._RawSpectrum()
        self.dark = self._RawSpectrum()
        self.reference = self._RawSpectrum()
        self.processed = self._RawSpectrum()
        
        self.mode = mode
        self.subtract_dark = subtract_dark
        self.normalize = normalize
        self.average = False
        self.averages = averages
        
        self.calibrate_x = True
        self.xcal = [1.0, 0.0]
        self.x_units = "nm"
        self.calibrate_y = False
        self.ycal = [1.0, 0.0]
        self.y_units = "arb"
        
        self.x = x
        self.y = y
        self.reference = reference
        self.dark = dark
        
        self.process()
    
    @property
    def averages(self):
        return self.raw.buffer.size
    
    @averages.setter
    def averages(self, value):
        value = int(value)
        
        if value < 0:
            raise ValueError('Number of spectra to average must be at least 1.')
        
        if value == 0:
            value = 1
        
        if not isinstance(self.raw, type(None)):
            if value != self.raw.buffer.size:
                self.raw.resize_buffer(value)
                self.average = value > 1
    
    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, value):
        value = np.array(value, dtype=float)
        
        if value.ndim == 0:
            return None
        if value.ndim == 1:
            if value.size != self._x.size:
                self.reshape_x(new_x=value)
            else:
                self._x = value
                
                if not isinstance(self.raw, type(None)):
                    self.raw.x = self.wavelength
                if not isinstance(self.dark, type(None)):
                    self.dark.x = self.wavelength
                if not isinstance(self.reference, type(None)):
                    self.reference.x = self.wavelength
                if not isinstance(self.processed, type(None)):
                    self.processed.x = self.wavelength
        elif value.ndim > 1:
            raise ValueError("Spectrum x data must be 1D array-like type.")
    
    @property
    def y(self):
        return self.raw._y
    
    @y.setter
    def y(self, value):
        self.raw.y = value
        self.process()
    
    @property
    def wavelength(self):
        if isinstance(self._x, type(None)):
            return None
        else:
            if self.calibrate_x:
                return self.x_calibration(self.xcal, self._x)
            else:
                return self._x
    
    @property
    def mode(self):
        return self._mode.value
    
    @mode.setter
    def mode(self, value):
        if isinstance(value, str):
            self._mode = self._modes(value.lower())
        elif isinstance(value, type(self._modes.INTENSITY)):
            self._mode = self._modes(value.value)
        else:
            raise TypeError("Spectrum mode value must be a valid string or a mode enum element.")
    
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
    
    def reshape_x(self, new_x=None, new_limits=None):
        old_limits = [self.x[0], self.x[-1]+1]
        
        # If nothing is passed, do nothing
        if isinstance(new_limits, type(None)) and isinstance(new_x, type(None)):
            return None
        
        # If x value passed, get new_limits
        elif not isinstance(new_x, type(None)):
            new_limits = [min(new_x), max(new_x)+1]
        
        # If new_x is not provided, generate it
        if isinstance(new_x, type(None)):
            new_x = np.arange(new_limits[0], new_limits[1])
        
        # If limits did not change, do nothing
        if all(np.equal(old_limits, new_limits)):
            return None
        
        if self.calibrate_x:
            calibrated_x = self.x_calibration(self.xcal, new_x)
        else:
            calibrated_x = new_x
        
        # Are you shrinking? Take a slice
        if new_limits[0] <= old_limits[0]:
            first_idx = 0
        elif new_limits[0] < old_limits[1]:
            first_idx = new_limits[0] - old_limits[0]
        else:
            first_idx = self.x.size
        
        if new_limits[1] >= old_limits[1]:
            last_idx = self.x.size
        elif new_limits[1] > old_limits[0]:
            last_idx = new_limits[1] - old_limits[1]
        else:
            last_idx = 0

        slc = slice(int(first_idx), int(last_idx))
        
        # Are you expanding? Pad with zeros
        pad_size_left = min(max(0, int(old_limits[0]-new_limits[0])), new_limits[1]-new_limits[0])
        pad_size_right = min(max(0, int(new_limits[1]-old_limits[1])), new_limits[1]-new_limits[0])
        
        # Go through all spectrums and reshape
        for spectrum in [self.raw, self.dark, self.reference, self.processed]:
            if not isinstance(spectrum, type(None)):       
                zeros_left = np.zeros((spectrum.y.shape[0], pad_size_left))
                zeros_right = np.zeros((spectrum.y.shape[0], pad_size_right))
                
                spectrum._y = np.hstack((zeros_left, spectrum.y[:, slc], zeros_right))
                spectrum._x = calibrated_x
        
        self._x = new_x
    
    def process(self):
        processed = self.raw
        reference = self.reference
        
        if self.average:
            processed = processed.average()
        else:
            processed = processed[0]
        
        if self.subtract_dark:
            processed = self.dark_subtraction(processed, self.dark)
        
        if self._mode == self._modes.INTENSITY:
            pass
        else:
            if self.subtract_dark:
                reference = self.dark_subtraction(reference, self.dark)
            if self._mode == self._modes.TRANSMISSION:
                processed = self.compute_transmission(processed, reference)
            elif self._mode == self._modes.ABSORBANCE:
                processed = self.compute_absorbance(processed, reference)
        
        if self.calibrate_y:
            processed = self.y_calibration(self.ycal, processed)
        if self.normalize:
            processed = self.normalization(processed)
        
        self.processed = processed
    
    def set_x_units(self, new_units):
        if not isinstance(self.raw, type(None)):
            self.raw.x_units = new_units
        if not isinstance(self.dark, type(None)):
            self.dark.x_units = new_units
        if not isinstance(self.reference, type(None)):
            self.reference.x_units = new_units
        if not isinstance(self.processed, type(None)):
            self.processed.x_units = new_units
    
    def set_y_units(self, new_units):
        if not isinstance(self.raw, type(None)):
            self.raw.y_units = new_units
        if not isinstance(self.dark, type(None)):
            self.dark.y_units = new_units
        if not isinstance(self.reference, type(None)):
            self.reference.y_units = new_units
        if not isinstance(self.processed, type(None)):
            self.processed.y_units = new_units
    
    @staticmethod
    def to_wavenumber(wavelength, y, interpolate=False):
        wavenumber = np.flip(2*np.pi/wavelength)
        y = np.flip(y)
        
        if interpolate:
            interpolation = interp1d(wavenumber, y, kind=interpolate, copy=True)
            
            min_k = wavenumber[0]
            max_k = wavenumber[-1]
            n = wavenumber.size
            
            wavenumber = np.linspace(min_k, max_k, n)
            y = interpolation(wavenumber)
        
        return wavenumber, y
    
    def x_calibration(self, pol, value):
        return np.polyval(pol, value)
    
    def y_calibration(self, pol, value):
        if isinstance(value, self._RawSpectrum):
            value.y = np.polyval(pol, value.y)
            return value
        else:
            return np.polyval(pol, value)
    
    @classmethod
    def normalization(cls, raw):
        return cls._RawSpectrum(raw.x, raw.y/np.max(raw.y))
    
    @classmethod
    def dark_subtraction(cls, raw, dark):
        if isinstance(raw, type(None)):
            return None
        elif isinstance(dark, type(None)):
            return raw
        else:
            if any(np.not_equal(raw.x, dark.x)):
                raise ValueError('Cannot subtract dark spectrum. Wavelengths from raw and dark spectra do not match.')
            
            return cls._RawSpectrum(raw.x, np.subtract(raw.y, dark.y))
    
    @classmethod
    def compute_transmission(cls, raw, ref):
        if isinstance(raw, type(None)):
            return None
        elif isinstance(ref, type(None)):
            return raw
        else:
            if any(np.not_equal(raw.x, ref.x)):
                raise ValueError('Cannot compute transmission. Wavelengths from raw and reference spectra do not match.')
            
            return cls._RawSpectrum(raw.x, np.divide(raw.y, ref.y))
    
    @classmethod
    def compute_absorbance(cls, raw, ref):
        if isinstance(raw, type(None)):
            return None
        elif isinstance(ref, type(None)):
            return raw
        else:
            if any(np.not_equal(raw.x, ref.x)):
                raise ValueError('Cannot compute absorption. Wavelengths from raw and reference spectra do not match.')
            
            return cls._RawSpectrum(raw.x, np.log10(np.divide(ref.y, raw.y)))
    
    def save(self, path, processed=True, raw=False, dark=False, reference=False, decimals=10):
        NL = '\n' # Newline character
        SEP = '\t' # Delimiter/separator character
        fmt = '%.'+str(decimals)+'g'
#        print("Called spectrum.save. Saving: processed {} raw {} dark {} reference {}".format(processed, raw, dark, reference))
        
        header = 'Date: {}'.format(datetime.now()) + NL
        header += 'Mode: {}'.format(self.mode) + NL
        header += 'Normalization: {}'.format(self.normalize) + NL
        header += 'Dark subtraction: {}'.format(self.subtract_dark) + NL
        header += 'Buffer size: {}'.format(self.raw.buffer.size) + NL
        header += NL
        header += 'Wavelength [{}]'.format(self.raw.x_units)
        
        output = self.processed.x
        
        if processed and not isinstance(self.processed, type(None)):
            output = np.vstack((output, self.processed.y))
            header += SEP + 'Processed'
        if dark and not isinstance(self.dark, type(None)):
            output = np.vstack((output, self.dark.y))
            header += SEP + 'Dark'
        if reference and not isinstance(self.reference, type(None)):
            output = np.vstack((output, self.reference.y))
            header += SEP + 'Reference'
        if raw and not isinstance(self.raw, type(None)):
            output = np.vstack((output, self.raw.y))
            header += SEP + 'Raw'
        
        output = output.transpose()
        
        np.savetxt(path, output, fmt=fmt, delimiter=SEP, newline=NL, header=header)
    
    @classmethod
    def from_file(cls, path=None):
        NL = '\n' # Newline character
        SEP = '\t' # Delimiter/separator character
        
        if not path:
            path = file_dialog_open()
        
        # First read header
        header = []
        
        with open(path, 'r') as file:
            # Seart for header start flag:
            while True:
                line = file.readline()
                if line[0] != "#":
                    break
                else:
                    header.append(line.replace("# ",""))
        
        # Parse properties
        props = {}
        for line in header[0:-1]:
            try:
                key, value = tuple(split(": ", line))
                key = key.lower().replace(" ","_")
                
                if key == "date":
                    pass
                elif key == "mode":
                    pass
                elif key == "normalization":
                    value = value == "True"
                elif key == "dark_subtraction":
                    value = value == "True"
                elif key == "buffer_size":
                    value = int(value)
                
                props[key] = value
            except ValueError:
                pass
        
        # Get column names
        names = split(SEP, header[-1])
        for index in range(len(names)):
            names[index] = sub(NL+"|| \[.*\]", "", names[index].lower())
        
        # Import data and initialize return
        data = np.loadtxt(fname=path, dtype=float, comments="#", delimiter=SEP)
#        raw_buffer_size = data.shape[1] - len(names) + 1
        
        spectrum = cls()
        
        if "wavelength" in names:
            wavelength = data[:, names.index("wavelength")].flatten()
        else:
            wavelength = None
        if "processed" in names:
            spectrum.processed = spectrum._RawSpectrum(wavelength, data[:, names.index("processed")].flatten())
        if "dark" in names:
            dark = data[:, names.index("dark").flatten()]
            spectrum.dark = spectrum._RawSpectrum(wavelength, dark)
        if "reference" in names:
            spectrum.reference = spectrum._RawSpectrum(wavelength, data[:, names.index("reference")].flatten())
        if "raw" in names:
            slc = slice(names.index("raw"), names.index("raw") + props["buffer_size"])
            spectrum.raw = spectrum._RawSpectrum(wavelength, data[:, slc].transpose(), buffer_size=props["buffer_size"])

        return spectrum