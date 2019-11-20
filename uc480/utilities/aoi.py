# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 12:53:28 2019

@author: Axel Lacapmesure
"""

from lantz.core import ureg
from lantz.qt import QtCore

from enum import Enum, auto

from functools import wraps

import numpy as np


class AOI2D(QtCore.QObject):
    """
    Abstract class for a two-dimensional area of interest
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
    
    class _CONDITIONS(Enum):
        ANY = auto()
        EVEN = auto()
        ODD = auto()
    
    limits_changed = QtCore.pyqtSignal(object)
    
    class Validators:
        """
        Container class for decorators used for input validation (decorators
        cannot be defined as instance or static methods, so we define them
        within this class)
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
                name = func.__name__
                
                if name in ['inverse_x', 'inverse_y']:
                    # Conversion to bool:
                    value = bool(value)
                elif name == "condition":
                    pass
                else:
                    # Universal conversion to pint quantity
                    try:
                        value = value.to(units)
                    except AttributeError:
                        value = value * units                    
                
                if name == 'origin':
                    # Origin dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                    except AttributeError:
                        raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                
                if name == 'end':
                    # End dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                    except AttributeError:
                        raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                
                if name == 'limits':
                    # Limits dimension validation
                    try:
                        if value.shape != (4,):
                            raise ValueError('Area limits value must be a four element numpy or pint array with structure [xmin, xmax, ymin, ymax]')
                    except AttributeError:
                            raise ValueError('Area limits value must be a four element numpy or pint array with structure [xmin, xmax, ymin, ymax]')
                
                if name == "condition":
                    # Restrictins validation
                    if isinstance(value, type(None)):
                        value = self._CONDITIONS.ANY
                    elif isinstance(value, str):
                        value = self._CONDITIONS[value.upper()]
                    elif isinstance(value, int):
                        value = self._CONDITIONS(value)
                    elif isinstance(value, type(self._CONDITIONS.ANY)):
                        pass
                    else:
                        raise TypeError("Restriction value must be either a string, a integer or a enum element indicating a valid restriction")
                
                # If value equals already set, do nothing
                if name in ['inverse_x', 'inverse_y', 'xmin', 'xmax', 'ymin', 'ymax']:
                    if value==self.__getattribute__(name):
                        return None
                
                # If value falls beyond the opposed limit, redefine it
                if name in ['xmin','xmax','ymin','ymax']:
                    axis = name[0] # x or y
                    side = name[1:] # min or max
                    conj_side = 'min' if side=='max' else 'max'
                    
                    if side=='min' and value>self.__getattribute__(axis+conj_side):
                        self.__setattr__(axis+conj_side, value)
                    elif side=='max' and value<self.__getattribute__(axis+conj_side):
                        self.__setattr__(axis+conj_side, value)
                
                return func(self, value)
            
            return validator
        
        @classmethod
        def dimensions(self, func):
            """
            Decorator for validating Area objects setter input dimensions.
            """
            
            @wraps(func)
            def validator(self, value):
                name = func.__name__
                
                if name == 'origin':
                    # Origin dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                    except AttributeError:
                        raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                
                if name == 'end':
                    # End dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                    except AttributeError:
                        raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                
                if name == 'limits':
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
    
    class Modificators:
        """
        Container class for decorators used for function modificators
        (decorators cannot be defined as instance or static methods, so we
        define them within this class)
        """
        
#        @classmethod
#        def emit_limits_changed(self, func):
#            """
#            Emits a limits_changed singal after function call. 
#            """
#            
#            @wraps(func)
#            def modificator(self, value):
#                func(self, value)
#                self.limits_changed.emit(self.limits)
#            
#            return modificator
        
        @classmethod
        def inverse_axis(self, func):
            """
            
            """
            
            @wraps(func)
            def modificator(self, value):
                
                name = func.__name__
                
                if name in ['xmin','xmax','ymin','ymax'] and not isinstance(self.canvas, type(None)):
                    axis = name[0]
                    side = name[1:]
                    conj_side = 'min' if side=='max' else 'max'
                    
                    if self.__getattribute__('inverse_'+axis):
                        def alt_func(self, value):
                            value = self.canvas.__getattribute__(axis+'max') - value
                            self.__setattr__('_' + axis + conj_side, value)
                        return alt_func(self, value)
                    
                return func(self, value)
            
            return modificator
        
        @classmethod
        def inverse_axis_getter(self, func):
            """
            
            """
            
            @wraps(func)
            def modificator(self):
                
                name = func.__name__
                axis = name[0]
                side = name[1:]
                conj_side = 'min' if side=='max' else 'max'
                
                if name in ['xmin','xmax','ymin','ymax'] and not isinstance(self.canvas, type(None)):
                    axis = name[0]
                    
                    if self.__getattribute__('inverse_'+axis):
                        return self.canvas.__getattribute__(axis+'max') - self.__getattribute__('_'+axis+conj_side)
                    
                return func(self)
            
            return modificator
        
        @classmethod
        def impose_condition(self, func):
            """
            
            """
            
            @wraps(func)
            def modificator(self, value):
                
                name = func.__name__
                modify = False # Booelan indicating if conditions for modificator to generate an alterate function are satisfied
                
                if name in ['xmin','xmax','ymin','ymax'] and self.condition != self._CONDITIONS.ANY:
                    axis = name[0]
                    side = name[1:]
                    conj_side = 'min' if side=='max' else 'max'
                    
                    plain_value = value.to(self.units).magnitude
                    conj_value = self.__getattribute__(axis+conj_side).to(self.units).magnitude
                    
                    if self.condition == self._CONDITIONS.EVEN and np.abs(plain_value-conj_value)%2 != 0:
                        modify = True
                    
                    if self.condition == self._CONDITIONS.ODD and np.abs(plain_value-conj_value)%2 != 1:
                        modify = True
                    
                    if modify:
                        def alt_func(self, value, axis):
                            func(self, value)
                            if axis == "x":
                                self.width = self.width + 1*self.units
                            if axis == "y":
                                self.height = self.height + 1*self.units
                        
                        return alt_func(self, value, axis)
                
                return func(self, value)
            
            return modificator
        
    def __init__(self, limits=None, canvas_limits=None, units=None, inverse_x=False, inverse_y=False, condition=None):
        super().__init__()
        
        self.canvas = None
        self._units = self._D_UNITS
        self._xmin = self._D_XMIN * self._D_UNITS
        self._xmax = self._D_XMAX * self._D_UNITS
        self._ymin = self._D_YMIN * self._D_UNITS
        self._ymax = self._D_YMAX * self._D_UNITS
        self._inverse_x = False
        self._inverse_y = False
        self._condition = self._CONDITIONS.ANY
        
        if isinstance(units, type(None)):
            self.units = self._D_UNITS
        else:
            self.units = units
        
        if isinstance(canvas_limits, type(None)):
            self.canvas = None
        else:
            self.canvas = self.__class__(limits=canvas_limits, units=self.units)
        
        self.inverse_x = inverse_x
        self.inverse_y = inverse_y
        
        if isinstance(limits, type(None)):
            if isinstance(self.canvas, type(None)):
                # If no canvas is provided, use default limits
                pass
            else:
                # If a canvas is provided, set maximum limits
                self.limits = self.canvas.limits
        else:
            self.limits = limits
        
        self.condition = condition
    
    @property
    def inverse_x(self):
        return self._inverse_x
    
    @inverse_x.setter
    @Validators.value
    def inverse_x(self, value):
        self._inverse_x = value
        self.limits = self.limits
    
    @property
    def inverse_y(self):
        return self._inverse_y
    
    @inverse_y.setter
    @Validators.value
    def inverse_y(self, value):
        self._inverse_y = value
        self.limits = self.limits
    
    @property
    def condition(self):
        return self._condition
    
    @condition.setter
    @Validators.value
    def condition(self, value):
        self._condition = value
    
    @property
    @Modificators.inverse_axis_getter
    def xmin(self):
        return self._xmin
    
    @xmin.setter
    @Validators.value
    @Modificators.impose_condition
    @Modificators.inverse_axis
    @Validators.canvas
    def xmin(self, value):
        self._xmin = value
        self.limits_changed.emit(self.limits)
    
    @property
    @Modificators.inverse_axis_getter
    def xmax(self):
        return self._xmax
    
    @xmax.setter
    @Validators.value
    @Modificators.impose_condition
    @Modificators.inverse_axis
    @Validators.canvas
    def xmax(self, value):
        self._xmax = value
        self.limits_changed.emit(self.limits)
    
    @property
    @Modificators.inverse_axis_getter
    def ymin(self):
        return self._ymin
    
    @ymin.setter
    @Validators.value
    @Modificators.impose_condition
    @Modificators.inverse_axis
    @Validators.canvas
    def ymin(self, value):
        self._ymax = value
        self.limits_changed.emit(self.limits)
    
    @property
    @Modificators.inverse_axis_getter
    def ymax(self):
        return self._ymax
    
    @ymax.setter
    @Validators.value
    @Modificators.impose_condition
    @Modificators.inverse_axis
    @Validators.canvas
    def ymax(self, value):
        self._ymax = value
        self.limits_changed.emit(self.limits)
    
    @property
    def origin(self):
        return [self.xmin.magnitude, self.ymin.magnitude] * self.units
    
    @origin.setter
    @Validators.value
    @Validators.dimensions
    @Validators.canvas
    def origin(self, value):
        self.xmin = value[0]
        self.ymin = value[1]
    
    @property
    def end(self):
        return [self.xmax.magnitude, self.ymax.magnitude] * self.units
    
    @end.setter
    @Validators.value
    @Validators.dimensions
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
    def shape(self):
        return (self.height, self.width)
    
    @property
    def limits(self):
        return [self.xmin.magnitude, self.xmax.magnitude, self.ymin.magnitude, self.ymax.magnitude] * self.units
    
    @limits.setter
    @Validators.value
    @Validators.dimensions
    @Validators.canvas
    def limits(self, value):
        self.xmin = value[0]
        self.xmax = value[1]
        self.ymin = value[2]
        self.ymax = value[3]
    
    @property
    def xgrid(self):
        return self._xgrid
    
    @property
    def x_pitch(self):
        return self._x_pitch
    
    @x_pitch.setter
    @Validators.value
    def x_pitch(self, value):
        self._x_pitch = value
        self.update_xgrid()
    
    @property
    def x_offset(self):
        return self._x_offset
    
    @x_offset.setter
    @Validators.value
    def x_offset(self, value):
        self._x_offset = value
        self.update_xgrid()
    
    @property
    def ygrid(self):
        return self._ygrid
    
    @property
    def y_pitch(self):
        return self._y_pitch
    
    @y_pitch.setter
    @Validators.value
    def y_pitch(self, value):
        self._y_pitch = value
        self.update_ygrid()
    
    @property
    def y_offset(self):
        return self._y_offset
    
    @y_offset.setter
    @Validators.value
    def y_offset(self, value):
        self._y_offset = value
        self.update_ygrid()
    
    @property
    def units(self):
        return self._units
    
    @units.setter
    def units(self, value):
        xmin = self._xmin.to(self.units).magnitude
        xmax = self._xmax.to(self.units).magnitude
        ymin = self._ymin.to(self.units).magnitude
        ymax = self._ymax.to(self.units).magnitude
        
        if isinstance(value, type(None)):
            self._units = ureg.dimensionless
        else:
            self._units = value
        
        self._xmin = xmin * self._units
        self._xmax = xmax * self._units
        self._ymin = ymin * self._units
        self._ymax = ymax * self._units
        
        if not isinstance(self.canvas, type(None)):
            self.canvas.units = self._units
    
    def set_canvas(self, canvas_limits):
        if isinstance(canvas_limits, type(None)):
            self.canvas = None
        else:
            self.canvas = self.__class__(limits=canvas_limits, units=self.units)
            self.crop_to(self.canvas)
    
    def update_xgrid(self):
        self._x_grid = (np.arange(self.xmin.to(self.units).magnitude, self.xmax.to(self.units).magnitude, self.x_pitch.to(self.units).magnitude) + self.x_offset.to(self.units)) * self.units
    
    def update_ygrid(self):
        self._y_grid = (np.arange(self.ymin.to(self.units).magnitude, self.ymax.to(self.units).magnitude, self.y_pitch.to(self.units).magnitude) + self.y_offset.to(self.units)) * self.units
    
    def reset_limits(self):
        if isinstance(self.canvas, type(None)):
            self.limits = [self._D_XMIN, self._D_XMAX, self._D_YMIN, self._D_YMAX]
        else:
            self.limits = self.canvas.limits
    
    def crop_to(self, crop_area):
        if not isinstance(crop_area, self.__class__):
            crop_area = self.__class__(limits=crop_area, units=self.units)
        
        if self.xmin < crop_area.xmin:
            self.xmin = crop_area.xmin
        if self.xmax > crop_area.xmax:
            self.xmax = crop_area.ymax
        if self.ymin < crop_area.ymin:
            self.ymin = crop_area.ymin
        if self.ymax > crop_area.ymax:
            self.ymax = crop_area.ymax