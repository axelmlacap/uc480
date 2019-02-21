# -*- coding: utf-8 -*-
"""
Created on Sun Jan 27 13:50:41 2019

@author: Axel
"""


from functools import wraps

from lantz.core import ureg
from lantz.qt import Backend, Frontend, InstrumentSlot, QtCore
from lantz.qt.app import BackendSlot, FlockSlot
from lantz.qt.utils.qt import QtGui
from lantz.qt.blocks import ChartUi, VerticalUi

class Area:
    """
    Abstract class for a two-dimensional area
    """
    # Default values:
    _D_UNITS = ureg.dimensionless
    _D_XMIN = 0
    _D_XMAX = 0
    _D_YMIN = 0
    _D_YMAX = 0
    
    _D_CANVAS_XMIN = 0
    _D_CANVAS_XMAX = 0
    _D_CANVAS_YMIN = 0
    _D_CANVAS_YMAX = 0
    
    class Validators:
        """
        Container class for decorators (decorators cannot be defined as instance
        or static methods
        """
        
        @classmethod
        def value(self, func):
            """ 
            Decorator for validating Area objects setter values. Checks if
            value is a pint quantity with right units.
            """
            
            @wraps(func)
            def validator(self, value):
                units = self.units
                
                # Universal conversion to pint quantity
                try:
                    value = value.to(units)
                except AttributeError:
                    value = value * units
                
                if func.__name__ == 'origin':
                    # Origin dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                    except AttributeError:
                        raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                
                if func.__name__ == 'end':
                    # End dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                    except AttributeError:
                        raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                
                if func.__name__ == 'limits':
                    # Limits dimension validation
                    try:
                        if value.shape != (4,):
                            raise ValueError('Area limits value must be a four element numpy or pint array with structure [xmin, xmax, ymin, ymax]')
                    except AttributeError:
                            raise ValueError('Area limits value must be a four element numpy or pint array with structure [xmin, xmax, ymin, ymax]')
                        
                return func(self, value)
            
            return validator
        
        @classmethod
        def canvas(self, func):
            """ 
            Decorator for validating Area object limits. Assumes value validation
            already done.
            """
        
            @wraps(func)
            def validator(self, value):
                canvas = self.canvas
                
                # If no canvas is provided, do not validate
                if isinstance(canvas, type(None)):
                    pass
                
                elif func.__name__ == 'xmin':
                    # Validation of xmin
                    if value < canvas.xmin:
                        raise ValueError('Assigned xmin value is less than minimum allowed value of {}'.format(canvas.xmin))
                
                elif func.__name__ == 'xmax':
                    # Validation of xmax
                    if value > canvas.xmax:
                        raise ValueError('Assigned xmax value is greater than minimum allowed value of {}'.format(canvas.xmax))
                
                elif func.__name__ == 'ymin':
                    # Validation of ymin
                    if value < canvas.ymin:
                        raise ValueError('Assigned ymin value is less than minimum allowed value of {}'.format(canvas.ymin))
                
                elif func.__name__ == 'ymax':
                    # Validation of ymax
                    if value > canvas.ymax:
                        raise ValueError('Assigned ymax value is greater than minimum allowed value of {}'.format(canvas.ymax))
                
                elif func.__name__ == 'width':
                    # Validation of width
                    if value > canvas.width:
                        raise ValueError('Assigned width is larger than maximum width configured of {}'.format(canvas.width))
                
                elif func.__name__ == 'height':
                    # Validation of height
                    if value > canvas.height:
                        raise ValueError('Assigned height is larger than maximum width configured of {}'.format(canvas.height))
                
                elif func.__name__ == 'origin':
                    # Validation of height
                    if any((value[0] < canvas.xmin,
                            value[0] > canvas.xmax,
                            value[1] < canvas.ymin,
                            value[1] > canvas.ymax)):
                        raise ValueError('Assigned area origin at {} lies outside canvas limits {}'.format(value, canvas.limits))
                
                elif func.__name__ == 'end':
                    # Validation of height
                    if any((value[0] < canvas.xmin,
                            value[0] > canvas.xmax,
                            value[1] < canvas.ymin,
                            value[1] > canvas.ymax)):
                        raise ValueError('Assigned area end at {} lies outside canvas limits {}'.format(value, canvas.limits))
                
                return func(self, value)
            
            return validator
    
    def __init__(self, limits=None, canvas_limits=None, units=None):
        if isinstance(units, type(None)):
            self.units = self._D_UNITS
        else:
            self.units = units
        
        if isinstance(canvas_limits, type(None)):
            self.canvas = None
        else:
            self.canvas = Area(limits=canvas_limits)
        
        self._xmin = self._D_XMIN 
        self._xmax = self._D_XMAX
        self._ymin = self._D_YMIN
        self._ymax = self._D_YMAX
        
        self.limits = limits

    @property
    def xmin(self):
        return self._xmin
    
    @xmin.setter
    @Validators.value
    @Validators.canvas
    def xmin(self, value):
        self._xmin = value
        
        if value > self.xmax:
            self.xmax = value
    
    @property
    def xmax(self):
        return self._xmax
    
    @xmax.setter
    @Validators.value
    @Validators.canvas
    def xmax(self, value):
        self._xmax = value
    
        if value < self.xmin:
            self.xmin = value
    
    @property
    def ymin(self):
        return self._ymin
    
    @ymin.setter
    @Validators.value
    @Validators.canvas
    def ymin(self, value):
        self._ymax = value
        
        if value > self.ymax:
            self.ymax = value
    
    @property
    def ymax(self):
        return self._ymax
    
    @ymax.setter
    @Validators.value
    @Validators.canvas
    def ymax(self, value):
        self._ymax = value
        
        if value < self.ymin:
            self.ymin = value
    
    @property
    def origin(self):
        return [self.xmin, self.ymin]
    
    @origin.setter
    @Validators.value
    @Validators.canvas
    def origin(self, value):
        self.xmin = value[0]
        self.ymin = value[1]
    
    @property
    def end(self):
        return [self.xmax, self.ymax]
    
    @end.setter
    @Validators.value
    @Validators.canvas
    def end(self, value):
        self.xmax = value[0]
        self.ymax = value[1]
    
    @property
    def width(self):
        return self.xmax - self.xmin
    
    @width.setter
    @Validators.value
    @Validators.canvas
    def width(self, value):
        # Modify xmax if area is within canvas or no canvas is provided
        if isinstance(self.canvas, type(None)):
            self.xmax = self.xmin + value
        elif self.xmin + value < self.canvas.xmax:
            self.xmax = self.xmin + value
        # If not, modify both xmin and xmax
        else:
            self.xmax = self.canvas.xmax
            self.xmin = self.canvas.xmax - value
    
    @property
    def height(self):
        return self.ymax - self.ymin
    
    @height.setter
    @Validators.value
    @Validators.canvas
    def height(self, value):
        # Modify ymax if area is within canvas or no canvas is provided
        if isinstance(self.canvas, type(None)):
            self.ymax = self.ymin + value
        elif self.ymin + value < self.canvas.ymax:
            self.ymax = self.ymin + value
        # If not, modify both ymin and ymax
        else:
            self.ymax = self.canvas.ymax
            self.ymin = self.canvas.ymax - value
    
    @property
    def limits(self):
        return [self.xmin, self.xmax, self.ymin, self.ymax]
    
    @limits.setter
    @Validators.value
    @Validators.canvas
    def limits(self, value):
        self.xmin = value[0]
        self.xmax = value[1]
        self.ymin = value[2]
        self.ymax = value[3]
        
    
