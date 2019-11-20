# -*- coding: utf-8 -*-
"""
Created on Thu Dec 13 10:32:43 2018

@author: Fotonica
"""

from .func import file_dialog_save
from .buffer import FIFOBuffer

from lantz.qt import QtCore
from lantz.core import ureg

import numpy as np

import os
import sys
import errno
from pathlib import Path

from enum import Enum, IntEnum, IntFlag, auto

from datetime import datetime


class PATH:
    pass


class DATA:
    pass


class TRIGGER_RETURN:
    def __init__(self, index):
        self.index = index


class INSTANCE_ATTRIBUTE:
    def __init__(self, name):
        self.name = name


class StopConditions(IntFlag):
    COUNT = auto()
    TIME = auto()


class Numerations(IntFlag):
    COUNT = auto()
    TIMESTAMP = auto()


class CallbackModes(IntFlag):
    SERIAL = auto()
    PARALLEL = auto()


class SaveManager(QtCore.QObject):
    """
    Clase para implementar guardado de datos automatizado a partir de signals y slots de Qt.

    Acepta un signal `trigger` que se emite cada vez que hay una muestra disponible. La muestra se almacena en un buffer
    tipo FIFO hasta llenar un paquete de tamaño configurable, momento en el cual se llama a la función `callback` que
    guarda los datos de cada muestra individualmente.

    Parameters
    ----------
    callback : Callable
        Función que guarda los datos de cada muestra. En su firma debe incluir parámetros que acepten la ruta del
        archivo y los datos a guardar de cada muestra (en los argumentos `callback_args` y `callback_kwargs` se
        especifica el orden en el cual se introducen dichos parámetros).
    trigger : PyQt5.signal
        Señal de PyQt5 que indica que una muestra está disponible. En alguno de los returns de cada emisión de la señal
        debe incluirse los datos de la muestra.
    index_of_data : int, opcional
        Índice que indica la posición de los datos de la muestra entre los returns de la emisión del trigger (por
        defecto: 0).
    stop_condition : Union[str, int, StopConditions], opcional
        Criterio de parada determinado por la enumeración StopConditions (por defecto: StopConditions.COUNT, que
        significa la terminación del proceso de guardado una vez que se alcanza un límite de muestras).
    limit : float, opcional
        Valor de límite para determinar el criterio de parada. Si `stop_condition = StopConditions.COUNT`, `limit`
        indica la cantidad de muestras totales a guardar. Si `stop_condition = StopConditions.TIME`, `limit` indica la
        cantidad de tiempo en segundos a registrar (por defecto: 1).
    packet_length : float, opcional
        Las muestras se guardarán de a grupos (paquetes) de tamaño `packet_length`. Este valor se utiliza para definir
        el tamaño del buffer: si `callback_mode = CallbackModes.SERIAL`, el buffer tiene el mismo tamaño que los
        paquetes; si `callback_mode = CallbackModes.PARALLEL`, el tamaño del buffer incluye un determinado overhead dado
        por el valor de `BUFFER_OVERHEAD_IN_PACKETS` (por defecto: 1).
    append : Union[str, int, Numerations], opcional
        Especifica si anexa un sufijo al nombre de archivo (previo a la extensión). Útil para evitar sobrescrituras. Los
        posibles sufijos están determinados por la enumeración Numerations (por defecto: Numerations.TIMESTAMP).
    default_ext: str, opcional
        Extensión del formato de archivos en el cual se guardará la muestra. No está implementado, pero en las clases
        hijas puede servir para completar el nombre de archivo si este no incluye una extensión.
    buffer_init, opcional
        Ejemplo de contenedor de los datos de una única muestra. Permite configurar el buffer como un arreglo de estos
        contenedores. Debe ser compatible con el tipo de datos que devuelve la señal de `trigger` (por defecto: object,
        lo cual significa que puede aceptar cualquier tipo de datos).
    callback_mode : Union[str, int, CallbackModes], opcional
        Establece si el guardado se ejecuta de forma secuencial respecto a la adquisición de datos (lo cual implica una
        pausa en la adquisición de datos) o en paralelo (para una adquisición continua). Actualmente no implementado, lo
        cual significa una escritura en serie.

    Arguments
    =========

    stop_condition
    stop_flag
    limit
    packet_length
    save_every
    single_file
    buffer
    buffer_init
    path
    append
    default_ext
    index_of_data
    callback_args
    callback_kwargs
    callback_mode
    """
    added = QtCore.pyqtSignal(object, object)
    saved = QtCore.pyqtSignal(object, object, object)
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    
    stop_condition_set = QtCore.pyqtSignal(object)
    limit_set = QtCore.pyqtSignal(object)
    append_set = QtCore.pyqtSignal(object)
    base_path_set = QtCore.pyqtSignal(object)
    callback_args_set = QtCore.pyqtSignal(object)
    callback_kwargs_set = QtCore.pyqtSignal(object)
    
    BUFFER_OVERHEAD_IN_PACKETS = 5
    
    def __init__(self,
                 callback,
                 trigger,
                 index_of_data=0,
                 stop_condition=StopConditions.COUNT,
                 limit=1,
                 packet_length=1,
                 append=Numerations.TIMESTAMP,
                 default_ext=".txt",
                 buffer_init=object,
                 single_file=True,
                 callback_mode=CallbackModes.SERIAL,
                 *args, **kwargs):
        super().__init__()

        self._stop_condition = StopConditions.COUNT
        self._limit = 1
        self._packet_length = 1
        self._save_every = 1
        self._single_file = None
        self._buffer_init = None
        self._buffer = FIFOBuffer(init_object=self._buffer_init)
        self._base_path = None
        self._folder = None
        self._base_name = None
        self._extension = None
        self._default_ext = ""
        self._append = Numerations(0)
        self._callback_args = ()
        self._callback_kwargs = {}
        self._callback_mode = CallbackModes.SERIAL

        self.buffer_init = buffer_init
        
        self.trigger = trigger
        self.index_of_data = index_of_data
        self.callback = callback
        self.callback_args = args
        self.callback_kwargs = kwargs
        
        self.stop_condition = stop_condition
        self.limit = limit
        self.packet_length = packet_length
        self.single_file = single_file
        self.save_every = 1
        self.count = 0
        self.trigger_count = 0
        self.append = append
        self.default_ext = default_ext
        
        self.enabled = False
        self.start_time = None
        self.stop_time = None
        self.run_time = None
    
    @property
    def stop_condition(self):
        return self._stop_condition.value
    
    @stop_condition.setter
    def stop_condition(self, value):
        if isinstance(value, str):
            value = StopConditions[value.upper()]
        elif isinstance(value, int):
            value = StopConditions(value)
        elif isinstance(value, StopConditions):
            pass
        else:
            raise TypeError("Value type must be either a StopConditions enum value, a string or an integer.")
        
        # Change _stop_condition if value differs from previous value
        if value != self._stop_condition:
            self._stop_condition = value
            self.limit = 1
            # Refresh append to avoid lack of numeration and file overwriting
            self.append = self.append
            
            self.stop_condition_set.emit(self.stop_condition)
    
    @property
    def append(self):
        return self._append
    
    @append.setter
    def append(self, value):
        if isinstance(value, type(None)):
            value = Numerations(0)
        elif isinstance(value, bool):
            if value == False:
                value = Numerations(0)
            else:
                raise TypeError("Append value must be either a Numerations enum value, a string with a valid numeration name, an integer or a list with any of the above types.")
        elif isinstance(value, str):
            value = Numerations[value.upper()]
        elif isinstance(value, int):
            value = Numerations(value)
        elif isinstance(value, Numerations):
            pass
        elif isinstance(value, list):
            append = Numerations(0)
            for v in value:
                if isinstance(v, type(None)):
                    append |= Numerations(0)
                elif isinstance(v, str):
                    append |= Numerations[v.upper()]
                elif isinstance(v, int):
                    append |= Numerations(v)
                elif isinstance(v, Numerations):
                    append |= v
                else:
                    raise TypeError("Append value must be either a Numerations enum value, a string with a valid numeration name, an integer or a list with any of the above types.")
            value = append
        else:
            raise TypeError("Append value must be either a Numerations enum value, a string with a valid numeration name, an integer or a list with any of the above types.")
        
        # To avoid file overwrite, lack of numeration is allowed only for single file operation
        if not value:
            if self._stop_condition == StopConditions.TIME:
                value = Numerations.TIMESTAMP
            if self._stop_condition == StopConditions.COUNT and self.limit > 1:
                value = Numerations.TIMESTAMP
        
        self._append = value
        self.append_set.emit(self._append)
    
    @property
    def path(self):
        name = self._base_name
        
        if self.append & Numerations.TIMESTAMP:
            name += "_" + self.get_timestamp()
        if self.append & Numerations.COUNT:
            name += "_" + str(self.count)

        name += self._extension
        path = Path(self._folder) / name
        
        return str(path)
    
    @path.setter
    def path(self, value):
        if not value:
            self._base_path = None
            self._folder = None
            self._base_name = None
            self._extension = None
            
            self.base_path_set.emit(self._base_path)
        elif not isinstance(value, str):
            raise TypeError("File path must be a string with a valid path.")
        # elif not self.is_pathname_valid(value):
        #     raise ValueError("Invalid file path")
        else:
            value = Path(value).resolve()

            # if not value.is_file():
            #     raise ValueError("File path does not point to a file.")
            
            self._base_path = str(value)
            self._folder = value.parent
            self._base_name = value.stem
            self._extension = value.suffix
            
            if not self._extension:
                self._extension = self._default_ext
            
            self.base_path_set.emit(self._base_path)
    
    def set_path(self, path=None):
        if not path:
            path = self.file_dialog_save()
        
        self.path = path
    
    @property
    def default_ext(self):
        return self._default_ext
    
    @default_ext.setter
    def default_ext(self, value):
        if isinstance(value, type(None)):
            value = ""
        elif not isinstance(value, str):
            raise TypeError("Default extension must be string type.")
        
        if value[0] != ".":
            value = "." + value
        
        self._default_ext = value
    
    @property
    def index_of_data(self):
        return self._index_of_data
    
    @index_of_data.setter
    def index_of_data(self, value):
        if not isinstance(value, int):
            raise TypeError("Index of data must be int type")
        
        self._index_of_data = value
    
    @property
    def callback_args(self):
        return self._callback_args
    
    @callback_args.setter
    def callback_args(self, value):
        if not isinstance(value, tuple):
            value = tuple([value])
        self._callback_args = tuple(value)
        
        self.callback_args_set.emit(value)
    
    @property
    def callback_kwargs(self):
        return self._callback_kwargs
    
    @callback_kwargs.setter
    def callback_kwargs(self, value):
        self._callback_kwargs = value
        
        self.callback_kwargs_set.emit(value)
    
    @property
    def callback_mode(self):
        return self._callback_mode
    
    @callback_mode.setter
    def callback_mode(self, value):
        if isinstance(value, CallbackModes):
            pass
        elif isinstance(value, str):
            value = CallbackModes[value]
        elif isinstance(value, int):
            value = CallbackModes(value)
        
        if value == CallbackModes.PARALLEL:
            raise NotImplementedError("Parallel callback mode in SaveManager is not yet implemented. Use serial mode instead.")
        
        self._callback_mode = value

    def insert_callback_args(self, data):
        callback_args = list(self.callback_args)

        for index, arg in enumerate(callback_args):
            if isinstance(arg, PATH):
                callback_args[index] = self.path
            if isinstance(arg, DATA):
                callback_args[index] = data
            #            elif isinstance(arg, TRIGGER_RETURN):
            #                callback_args[index] = trigger_returns[arg.index]
            elif isinstance(arg, INSTANCE_ATTRIBUTE):
                callback_args[index] = self.__getattribute__(arg.name)

        return tuple(callback_args)

    def insert_callback_kwargs(self, data):
        callback_kwargs = dict(self.callback_kwargs)

        for index, (key, value) in enumerate(callback_kwargs.items()):
            if isinstance(value, PATH):
                callback_kwargs[key] = self.path
            if isinstance(value, DATA):
                callback_kwargs[key] = data
            #            elif isinstance(value, TRIGGER_RETURN):
            #                callback_kwargs[key] = trigger_returns[value.index]
            elif isinstance(value, INSTANCE_ATTRIBUTE):
                callback_kwargs[key] = self.__getattribute__(value.name)

        return callback_kwargs

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, value):
        if self._stop_condition == StopConditions.COUNT:
            self._limit = int(value) if value >= 0 else 0
        elif self._stop_condition == StopConditions.TIME:
            try:
                self._limit = value.to('s')
            except AttributeError:
                self._limit = float(value) * ureg.s

        self.limit_set.emit(self._limit)

    @property
    def save_every(self):
        return self._save_every

    @save_every.setter
    def save_every(self, value):
        value = int(value)
        value = max(value, 1)

        self._save_every = value

    @property
    def single_file(self):
        return self._single_file

    @single_file.setter
    def single_file(self, value):
        self._single_file = bool(value)

    @property
    def packet_length(self):
        return self._packet_length
    
    @packet_length.setter
    def packet_length(self, value):
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise TypeError("Packet length must be int type.")
        
        self._packet_length = value
        
        # Update buffer lengths
        if self._callback_mode == CallbackModes.SERIAL:
            self._buffer.packet_length = value
            self._buffer.length = value
            self._buffer.init_object = self.buffer_init
        elif self._callback_mode == CallbackModes.PARALLEL:
            self._buffer.packet_length = value
            self._buffer.length = value * self.BUFFER_OVERHEAD_IN_PACKETS
            self._buffer.init_object = self.buffer_init

    @property
    def stop_flag(self):
        count_flag = self._stop_condition == StopConditions.COUNT and self.buffer.write_counter >= self.limit
        time_flag = self._stop_condition == StopConditions.TIME and self.run_time >= self.limit

        return (count_flag or time_flag)

    @property
    def buffer(self):
        return self._buffer

    @property
    def buffer_init(self):
        return self._buffer_init

    @buffer_init.setter
    def buffer_init(self, value):
        self._buffer_init = value
        self._buffer.init_object = value

    def add_to_buffer(self, *trigger_returns):
        self.buffer(trigger_returns[self.index_of_data])

    def start(self):
        if not self._base_path:
            self.set_path()
        
        self.count = 0
        self.start_time = datetime.now()
        self.stop_time = None
        self.enabled = True
        
        self.buffer.packet_filled.connect(self.save)
        self.trigger.connect(self.run)
        self.started.emit()
    
    def stop(self):
        self.enabled = False
        self.trigger.disconnect(self.run)
        self.buffer.packet_filled.disconnect(self.save)
        self.stopped.emit()
        
        self.stop_time = datetime.now()
    
    def run(self, *trigger_returns):
        if self.enabled:
            self.trigger_count += 1
            self.update_run_time()
            
            if self.trigger_count % self.save_every == 0:
                self.buffer(trigger_returns[self.index_of_data])
                self.added.emit(self.buffer.write_counter, self.run_time)
            
            # Check for stop condition
            if self.stop_flag:
                self.stop()
                
                # Save remaining data
                remaining_length = self.buffer.write_counter - self.buffer.read_counter
                self.save(remaining_length)

    def save(self, data_length=None):
        if isinstance(data_length, type(None)):
            data_length = self._packet_length
        
        if data_length != 0:
            data_array = self.buffer.read(data_length)

            if self.single_file and isinstance(data_array, np.ndarray):
                for data in data_array:
                    callback_args = self.insert_callback_args(data)
                    callback_kwargs = self.insert_callback_kwargs(data)
                    self.callback(*callback_args, **callback_kwargs)

                    self.saved.emit(self.path, self.count, self.run_time)
                    self.count += 1
                    self.update_run_time()
            else:
                callback_args = self.insert_callback_args(data_array)
                callback_kwargs = self.insert_callback_kwargs(data_array)
                self.callback(*callback_args, **callback_kwargs)

                self.saved.emit(self.path, self.count, self.run_time)
                self.count += 1
                self.update_run_time()

        self.count = 0
    
    def update_run_time(self):
        if self.start_time:
            self.run_time = (datetime.now() - self.start_time).total_seconds() * ureg.s
        else:
            self.run_time = None
    
    @staticmethod
    def get_timestamp():
        now = datetime.now()
        milis = now.microsecond // 1000
        return now.strftime('%Y%m%d_%H%M%S.') + str(milis)
    
    @staticmethod
    def file_dialog_save(title="Guardar archivo", initial_dir="/", filetypes=[("Text files", "*.txt")]):
        
        return file_dialog_save(title=title, initial_dir=initial_dir, filetypes=filetypes)
    
    @staticmethod
    def split_path(path):
        from os.path import split, splitext
        
        folder, full_name = split(path)
        name, extension = splitext(full_name)
        
        return folder, name, extension, full_name
    
    @staticmethod
    def is_pathname_valid(pathname: str) -> bool:
        """
        `True` if the passed pathname is a valid pathname for the current OS;
        `False` otherwise.
        """
        
        ERROR_INVALID_NAME = 123
        
        # If this pathname is either not a string or is but is empty, this pathname
        # is invalid.
        try:
            if not isinstance(pathname, str) or not pathname:
                return False
    
            # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
            # if any. Since Windows prohibits path components from containing `:`
            # characters, failing to strip this `:`-suffixed prefix would
            # erroneously invalidate all valid absolute Windows pathnames.
            _, pathname = os.path.splitdrive(pathname)
    
            # Directory guaranteed to exist. If the current OS is Windows, this is
            # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
            # environment variable); else, the typical root directory.
            root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
                if sys.platform == 'win32' else os.path.sep
            assert os.path.isdir(root_dirname)   # ...Murphy and her ironclad Law
    
            # Append a path separator to this directory if needed.
            root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep
    
            # Test whether each path component split from this pathname is valid or
            # not, ignoring non-existent and non-readable path components.
            for pathname_part in pathname.split(os.path.sep):
                try:
                    os.lstat(root_dirname + pathname_part)
                # If an OS-specific exception is raised, its error code
                # indicates whether this pathname is valid or not. Unless this
                # is the case, this exception implies an ignorable kernel or
                # filesystem complaint (e.g., path not found or inaccessible).
                #
                # Only the following exceptions indicate invalid pathnames:
                #
                # * Instances of the Windows-specific "WindowsError" class
                #   defining the "winerror" attribute whose value is
                #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
                #   fine-grained and hence useful than the generic "errno"
                #   attribute. When a too-long pathname is passed, for example,
                #   "errno" is "ENOENT" (i.e., no such file or directory) rather
                #   than "ENAMETOOLONG" (i.e., file name too long).
                # * Instances of the cross-platform "OSError" class defining the
                #   generic "errno" attribute whose value is either:
                #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
                #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
                except OSError as exc:
                    if hasattr(exc, 'winerror'):
                        if exc.winerror == ERROR_INVALID_NAME:
                            return False
                    elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                        return False
        # If a "TypeError" exception was raised, it almost certainly has the
        # error message "embedded NUL character" indicating an invalid pathname.
        except TypeError:
            return False
        # If no exception was raised, all path components and hence this
        # pathname itself are valid. (Praise be to the curmudgeonly python.)
        else:
            return True
        # If any other exception was raised, this is an unrelated fatal issue
        # (e.g., a bug). Permit this exception to unwind the call stack.








