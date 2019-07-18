# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 12:57:34 2019

@author: Fotonica
"""

from numpy import arange, zeros, full, ndarray, broadcast_to, isscalar, ceil

from enum import IntEnum, auto

from lantz.qt import QtCore

from warnings import warn

from types import FunctionType, BuiltinFunctionType

class BufferOverrun(Exception):
    """
        Excepción cuando ocurre un overrun del buffer.
    """
    pass

class BufferEnd(Exception):
    """
        Excepción cuando el buffer se llena.
    """
    pass

class BufferCore(QtCore.QObject):
    
    was_filled = QtCore.pyqtSignal()
    was_reset = QtCore.pyqtSignal()
    was_resized = QtCore.pyqtSignal()
    
    def __init__(self, length=1):
        super().__init__()
        
        self._length = 1
        self._index = 0
        self._count = 0
        
        self.length = length
    
    def __iter__(self):
        self._index = 0
        self._count = 0
        return self
    
    def __next__(self):
        self.count += 1
        self.index += 1
        return self.index
    
    def __call__(self):
        current_index = self._index
        self.__next__()
        
        return current_index
    
    @property
    def index(self):
        return self._index
    
    @index.setter
    def index(self, value):
        self._index = int(value % self.length)
        
        if self._index == 0 and self._count != 0:
            self.was_filled.emit()
    
    @property
    def count(self):
        return self._count
    
    @count.setter
    def count(self, value):
        self._count = int(value)
    
    @property
    def length(self):
        return self._length
    
    @length.setter
    def length(self, value):
        self._length = int(value)
        self.reset()
        
        self.was_resized.emit()
    
    def reset(self):
        self._index = 0
        self._count = 0
        
        self.was_reset.emit()
    
    @property
    def indices_new_first(self):
        return (self.index-1 - arange(self.length)) % self.length
    
    @property
    def indices_old_first(self):
        return (arange(self.length) - self.index) % self.length


class FIFOBuffer(QtCore.QObject):
    """
    Clase para buffer circular tipo "first-intput, first-output" (FIFO).
    
    Implementa un array de buffer que se accede de forma circular mediante
    índices de escritura y lectura SEPARADOS. El buffer puede contener
    cualquier tipo de datos que acepte un array de numpy, pero a la escritura y
    lectura sólo se accede de forma unidimensional mediante la primer
    dimensión.
    
    Parameters
    ----------
    length : int
        Largo del buffer (en cantidad de elementos). Por defecto, igual a 1.
    packet_length : int
        Los datos pueden segmentarse en paquetes de tamaño packet_length (en
        cantidad de muestras). Es transparente al funcionamiento del buffer y
        sirve únicamente para avisar al usuario que hay cierta cantidad de
        datos disponible. Por defecto, igual a 1.
    init_object
        Clase o instancia del objeto que se utilizará para construir el buffer.
        El buffer consistirá en un ndarray de numpy (cuyo largo está
        determinado por length) que contenga copias del init_object.
    overrun_policy : {'error', 'skip', 'silent_skip', 'none'} or callable
        Define cómo tratar los eventos de buffer overrun. Acepta un string
        indicando alguna de las configuraciones posibles o bien una función
        exterba personalizada. Dicha función debe tomar como único argumento la
        propia instancia de FIFOBuffer. Por defecto, toma el valor 'error'.
        Las configuraciones posibles son:
            'error': Suma el evento al contador interno y levanta una excepción
                     tipo BufferOverrun
            'skip': Suma el evento al contador interno y levana una advertencia
            'silent_skip': Suma el evento al contador interno
            'none': No realiza ninguna acción
            'custom': Configuración cuando a overrun_policy se le pasa un
                      método. Ejecuta el método personalizado pasando como
                      argumento la propia instancia de FIFOBuffer.
    end_policy : {'silent_skip', 'error', 'skip', 'none'} or callable
        Define cómo tratar los eventos donde el buffer se llena. Acepta los
        mismos valores que overrun_policy. En el caso de configuración 'error',
        levanta la excepción BufferEnded. Por defecto toma el valor 
        'silent_skip'.
    
    Raises
    ------
    BufferOverrun
        Cuando el índice de lectura intenta acceder sobre un espacio del buffer
        no escrito. Sólo si la configuración overrun_policy es tipo 'error'.
    BufferEnded
        Una vez que se escribe el último lugar disponible del buffer. Sólo si
        la configuración end_policy es tipo 'error'.
    
    Warns
    -----
    BufferOverrun
        Cuando el índice de lectura intenta acceder sobre un espacio del buffer
        no escrito. Sólo si la configuración overrun_policy es tipo 'skip'.
    BufferEnded
        Una vez que se escribe el último lugar disponible del buffer. Sólo si
        la configuración end_policy es tipo 'skip'.
    
    pyQt Signals
    ------------
    filled
        Cada vez que el índice de escritura llega al final del buffer.
    packet_filled
        Cada vez que hay un paquete nuevo para leer.
    ended
        Cuando se intenta leer pero no hay nuevos elementos escritos.
    overrun
        Cuando el índice de escritura intenta sobreescribir elementos no
        leídos.
    reinitialized
        Cuando se reinicia el buffer (los contadores se restablecen y el buffer
        se vacía).
    resized
        Cuando el largo 'length' del buffer se cambia.
    
    Notes
    -----
    Las funciones para lectura y escritura son los métodos 'read' y 'write'
    respectivamente. Ambos tienen un parámetro opcional 'step' (por defecto
    igual a 1) que permite leer (escribir) más de un valor (paquete).
    
    Los paquetes deben escribirse en arrays cuyo primer índice recorra los
    distintos elementos del paquete.
    
    La lectura de un único elemento puede hacerse mediante el método __call__()
    (sin argumentos). La escritura de un único elemento puede hacerse mediante
    el método __call__(value), donde el argumento 'value' acepta el valor a
    escribir.
    
    El valor length debe ser un múltiplo entero del valor packet_length. En
    caso de que length sea menor, se reemplaza igual a packet_length.
    
    Los métodos 'read' y 'write' implementan una serie de verificaciones
    iniciales (como, por ejemplo, que no se quiera leer un índice no escrito,
    lo cual sería un buffer overrun). Si alguna de estas verificaciones falla,
    aumentan un contador 'skip' ('_rskip' para escritura, '_wskip' para
    lectura) de modo que la operación se saltea. De esta forma la operación
    sólo se ejecuta cuando el contador correspondiente sea cero. El contador se
    restablece a cero cada vez que la operación se saltea.
    
    El método __getitem__(key) otorga acceso directo al array del buffer, de
    modo que la indexación no es tipo FIFO (por orden de escritura) sino
    absoluta.
    
    Los métodos 'newest_indices' y 'oldest_indices' devuelven una lista de
    índices de 0 hasta 'length' según el órden de escritura.
    
    La clase es iterable para su lectura (VERSIÓN EXPERIMENTAL, HAY QUE REVISAR
    EL CÓDIGO).
    
    """
    
    filled = QtCore.pyqtSignal()
    packet_filled = QtCore.pyqtSignal()
    ended = QtCore.pyqtSignal()
    overrun = QtCore.pyqtSignal()
    reinitialized = QtCore.pyqtSignal()
    resized = QtCore.pyqtSignal()
    
    class OverrunPolicies(IntEnum):
        ERROR = auto()
        SKIP = auto()
        SILENT_SKIP = auto()
        NONE = auto()
        CUSTOM = auto()
    
    class EndPolicies(IntEnum):
        ERROR = auto()
        SKIP = auto()
        SILENT_SKIP = auto()
        NONE = auto()
        CUSTOM = auto()
    
    def __init__(self,
                 length=1,
                 packet_length=None,
                 init_object=float,
                 overrun_policy="error",
                 end_policy="silent_skip"):
        super().__init__()
        
        self._length = 1
        self._packet_length = 1
        self.reinitialize(init_object=0)
        
        self.init_object = init_object
        self.length = length
        self.packet_length = packet_length
        
        self.overrun_policy = overrun_policy
        self.end_policy = end_policy
    
    def __iter__(self):
        return self
    
    def __next__(self):
        self._rnext()
        return self._ridx
    
    def __call__(self, value=None):
        if value is None:
            return self.read()
        else:
            self.write(value)
            return self._widx
    
    def __getitem__(self, key):
        self._data[key]
    
    @property
    def length(self):
        return self._length
    
    @length.setter
    def length(self, value):
        self._length = int(value)
        self._check_packet_length_compatibility()
        
        self.reinitialize()
        self.resized.emit()
    
    @property
    def packet_length(self):
        return self._packet_length
    
    @packet_length.setter
    def packet_length(self, value):
        if isinstance(value, type(None)):
            value = self.length
        
        self._packet_length = int(value)
        self._check_packet_length_compatibility()
    
    def _check_packet_length_compatibility(self):
        if self._length % self._packet_length != 0:
            if self._length < self._packet_length:
                self.length = self._packet_length
            elif self.length > self._packet_length:
                self.length = int(ceil(self._length/self._packet_length) * self._packet_length)
    
#    @property
#    def mode(self):
#        return self._mode.name.lower()
#    
#    @mode.setter
#    def mode(self, value):
#        if isinstance(value, str):
#            self._mode = self.Modes[value.upper()]
#        elif isinstance(value, type(self.Modes(1))):
#            self._mode = self.Modes(value)
#        else:
#            raise TypeError("Buffer mode must be a string with a valid mode. See 'Buffer.Modes'.")
#        
#        if self._mode == self.Modes.FIFO:
#            self._rorder = 1
#            self._worder = 1
#        elif self._mode == self.Modes.LIFO:
#            self._rorder = -1
#            self._worder = 1
    
    @property
    def overrun_policy(self):
        return self._overrun_policy.name.lower()
    
    @overrun_policy.setter
    def overrun_policy(self, value):
        if isinstance(value, str):
            self._overrun_policy = self.OverrunPolicies[value.upper()]
            self.handle_overrun = self.get_default_handle_overrun()
        elif isinstance(value, type(self.OverrunPolicies(1))):
            self._overrun_policy = self.OverrunPolicies(value)
            self.handle_overrun = self.get_default_handle_overrun()
        elif isinstance(value, (FunctionType, BuiltinFunctionType)):
            self._overrun_policy = self.OverrunPolicies.CUSTOM
            self.handle_overrun = value
        else:
            raise TypeError("Buffer overrun policy must be a string with a valid policy. See 'Buffer.OverrunPolicies'.")
    
    def get_default_handle_overrun(self):
        if self._overrun_policy == self.OverrunPolicies.ERROR:
            def handle(self):
                raise BufferOverrun()
            return handle
        
        elif self._overrun_policy == self.OverrunPolicies.SKIP:
            def handle(self):
                warn("Buffer overrun at {}".format(self))
                self._wskip += 1
            return handle
        
        elif self._overrun_policy == self.OverrunPolicies.SILENT_SKIP:
            def handle(self):
                self._wskip += 1
            return handle
        
        elif self._overrun_policy == self.OverrunPolicies.NONE:
            def handle(self):
                pass
            return handle
        
        else:
            raise ValueError("Invalid overrun policy '{}'".format(self._overrun_policy))
    
    @property
    def end_policy(self):
        return self._end_policy.name.lower()
    
    @end_policy.setter
    def end_policy(self, value):
        if isinstance(value, str):
            self._end_policy = self.EndPolicies[value.upper()]
            self.handle_end = self.get_default_handle_end()
        elif isinstance(value, type(self.EndPolicies(1))):
            self._end_policy = self.EndPolicies(value)
            self.handle_end = self.get_default_handle_end()
        elif isinstance(value, (FunctionType, BuiltinFunctionType)):
            self._end_policy = self.EndPolicies.CUSTOM
            self.handle_end = value
        else:
            raise TypeError("Buffer end policy must be a string with a valid policy. See 'Buffer.EndPolicies'.")
    
    def get_default_handle_end(self):
        if self._end_policy == self.EndPolicies.ERROR:
            def handle(self):
                raise BufferEnd()
            return handle
        
        elif self._end_policy == self.EndPolicies.SKIP:
            def handle(self):
                warn("Buffer end at {}".format(self))
                self._rskip += 1
            return handle
        
        elif self._end_policy == self.EndPolicies.SILENT_SKIP:
            def handle(self):
                self._rskip += 1
            return handle
        
        elif self._end_policy == self.EndPolicies.NONE:
            def handle(self):
                pass
            return handle
        
        else:
            raise ValueError("Invalid end policy '{}'".format(self._end_policy))
    
    @property
    def read_counter(self):
        return self._rctr
    
    @property
    def read_index(self):
        return self._ridx
    
    def _rnext(self, step=1):
        # Increment counter if there is no skip signal
        if self._rskip == 0:
            self._ridx = (self._ridx + step * self._rorder) % self._length
    
    def read(self, step=1):
        self._check_ended()
        
        # Read if there is no skip signal
        if self._rskip == 0:
            if step == 1:
                value = self._data[self._ridx]
            else:
                value = self._data[self.oldest_indices(step)]
                
            self._rctr += step * self._rorder
            self._rnext(step)
        else:
            self._rskip -= 1
            value = None
        
        return value
    
    @property
    def write_counter(self):
        return self._wctr
    
    @property
    def write_index(self):
        return self._widx
    
    def _wnext(self, step=1):
        # Increment counter if there is no skip signal
        if self._wskip == 0:
            self._widx = (self._widx + step  * self._worder) % self._length
    
    def write(self, value, step=1):
        self._check_overrun()
        
        # Write if there is no skip signal
        if self._wskip == 0:
            self._wnext(1)
            
            if step == 1:
                self._data[self._widx] = value
            else:
                # Check that step size does not exceeds buffer limits
                if step <= self._length - self._widx:
                    self._data[self._widx:self._widx+step] = value
                else:
                    first_chunk_size = self._length - self._widx
                    second_chunk_size = value.length - first_chunk_size
                    self._data[self._widx:] = value[0:first_chunk_size]
                    self._data[0:second_chunk_size] = value[first_chunk_size:]
            
            self._wnext(step-1)
            self._wctr += step * self._worder
            self._check_packet()
            self._check_filled()
        else:
            self._wskip = 0
    
    def newest_indices(self, num=None):
        if isinstance(num, type(None)):
            num = self.length
        
        return (self._widx - arange(num)) % self._length
    
    def oldest_indices(self, num=None):
        if isinstance(num, type(None)):
            num = self.length
        
        return (self._ridx + arange(num)) % self._length
    
    def _check_packet(self):
        if self._wctr != 0 and self._wctr % self._packet_length == 0:
            self.packet_filled.emit()
    
    def _check_filled(self):
        if self._widx == 0 and self._wctr != 0:
            self.filled.emit()
    
    def _check_ended(self):
        if self._rctr == self._wctr:
            self.ended.emit()
            self.handle_end(self)
    
    def _check_overrun(self):
        if (self._wctr - self._rctr) >= self._length:
            self.overrun.emit()
            self.handle_overrun(self)
    
    @property
    def init_object(self):
        return self._init_object
    
    @init_object.setter
    def init_object(self, value):
        if isinstance(value, type(None)):
            self.dtype = object
            self.inner_size = ()
            data_size = (self.length, ) + self.inner_size
            self._data = zeros(data_size, dtype=self.dtype)
        elif isinstance(value, type):
            self.dtype = value
            self.inner_size = ()
            data_size = (self.length, ) + self.inner_size
            self._data = zeros(data_size, dtype=self.dtype)
        elif isscalar(value):
            self.inner_size = ()
            data_size = (self.length, ) + self.inner_size
            self._data = full(data_size, fill_value=value, dtype=None)
            self.dtype = self._data.dtype
        elif isinstance(value, ndarray):
            self.inner_size = value.shape
            data_size = (self.length, ) + self.inner_size
            self._data = broadcast_to(value, data_size).copy()
            self.dtype = self._data.dtype
        else:
            raise TypeError("Value if 'init_object' must be either a type, a scalar or a numpy.ndarray.")
        
        self._init_object = self._data[0]
    
    @property
    def data(self):
        return self._data
    
    def reinitialize(self, init_object=None):
        if init_object is None:
            init_object = self._init_object
        
        self._rctr = 0
        self._wctr = 0
        self._rskip = 0
        self._wskip = 0
        self._ridx = 0
        self._widx = -1
        self._rorder = 1
        self._worder = 1
        
        self.init_object = init_object
        self.reinitialized.emit()
    
    def handle_buffer_overrun(self):
        warn("Buffer overrun at {}".format(self))



















