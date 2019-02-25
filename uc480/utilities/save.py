# -*- coding: utf-8 -*-
"""
Created on Thu Dec 13 10:32:43 2018

@author: Fotonica
"""

from .func import file_dialog_open

from lantz.qt import QtCore
from lantz.core import ureg

import os, sys, errno

from enum import Enum

from datetime import datetime

class SaveManager(QtCore.QObject):
    
    saved = QtCore.pyqtSignal(object, object, object)
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    
    stop_condition_set = QtCore.pyqtSignal(object)
    limit_set = QtCore.pyqtSignal(object)
    append_set = QtCore.pyqtSignal(object)
    base_path_set = QtCore.pyqtSignal(object)
    callback_args_set = QtCore.pyqtSignal(object)
    callback_kwargs_set = QtCore.pyqtSignal(object)
    
    class _stop_conditions(Enum):
        COUNT = 'count'
        TIME = 'time'
    
    _numerations = ['none', 'count', 'timestamp']
    
    def __init__(self, callback, signal, stop_condition='count', limit=1, append=['timestamp'], default_ext=".txt", *args, **kwargs):
        super().__init__()
        
        self._default_ext = ""
        self._base_path = None
        self._folder = None
        self._base_name = None
        self._extension = None
        self._stop_condition = self._stop_conditions.COUNT
        self._limit = 1
        self._save_every = 1
        self._append = []
        self._callback_args = ()
        self._callback_kwargs = {}
        
        self.signal = signal
        self.callback = callback
        self.callback_args = args
        self.callback_kwargs = kwargs
        
        self.stop_condition = self._stop_conditions(stop_condition)
        self.limit = limit
        self.save_every = 1
        self.count = 0
        self.signal_emissions = 0
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
            value = self._stop_conditions(value.lower())
        elif isinstance(value, type(self._stop_conditions.COUNT)):
            pass
        else:
            raise TypeError("Value type must be either string or stop_conditions enum.")
        
        if value != self._stop_condition:
            self._stop_condition = value
            self.limit = 1
            self.append = self.append
            
            self.stop_condition_set.emit(self.stop_condition)
    
    @property
    def limit(self):
        return self._limit
    
    @limit.setter
    def limit(self, value):
        if self._stop_condition == self._stop_conditions.COUNT:
            self._limit = int(value) if value >= 0 else 0
        elif self._stop_condition == self._stop_conditions.TIME:
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
    def append(self):
        return self._append
    
    @append.setter
    def append(self, value):
        if isinstance(value, type(None)):
            value = []
        elif isinstance(value, bool):
            if value == False:
                value = []
            else:
                raise TypeError("Append value must be a list of strings with valid options")
        elif isinstance(value, str):
            value = [value.lower()]
        elif not isinstance(value, list):
            raise TypeError("Append value must be a list of strings with valid options")
        
        # Validate:
        for x in value:
            if x not in self._numerations:
                raise ValueError("Invalid append value '{}'")
        
        # No numeration is allowed only for single file operation
        if not value:
            if self._stop_condition == self._stop_conditions.TIME:
                value = ["timestamp"]
            if self._stop_condition == self._stop_conditions.COUNT and self.limit > 1:
                value = ["timestamp"]
        
        self._append = value
        self.append_set.emit(self._append)
    
    @property
    def path(self):
        path = os.path.join(self._folder, self._base_name)
        
        if "timestamp" in self.append:
            path += "_" + self.get_timestamp()
        if "count" in self.append:
            path += "_" + str(self.count)
        
        path += self._extension
        
        return path
    
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
        elif not self.is_pathname_valid(value):
            raise ValueError("Invalid file path")
        else:
            value = value.replace("/","\\")
            
            self._base_path = value
            self._folder, self._base_name, self._extension, _ = self.split_path(value)
            
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
    def callback_args(self):
        return self._callback_args
    
    @callback_args.setter
    def callback_args(self, value):
        self._callback_args = value
        
        self.callback_args_set.emit(value)
    
    @property
    def callback_kwargs(self):
        return self._callback_kwargs
    
    @callback_kwargs.setter
    def callback_kwargs(self, value):
        self._callback_kwargs = value
        
        self.callback_kwargs_set.emit(value)
    
    def save(self):
        self.callback(self.path, *self.callback_args, **self.callback_kwargs)
        
        self.saved.emit(self.path, self.count, self.run_time)
        self.update_run_time()
        self.count += 1
    
    def start(self):
        if not self._base_path:
            self.set_path()
        
        self.enabled = True
        self.signal.connect(self.run)
        self.started.emit()
        
        self.count = 0
        self.start_time = datetime.now()
        self.stop_time = None
    
    def stop(self):
        self.enabled = False
        self.signal.disconnect(self.run)
        self.stopped.emit()
        
        self.stop_time = datetime.now()
    
    @QtCore.pyqtSlot()
    def run(self, *args, **kwargs):
        if self.enabled:
            self.signal_emissions += 1
            self.update_run_time()
            
            if self.signal_emissions % self.save_every == 0:
                self.save()
            
            # Check for stop conditions
            if self._stop_condition == self._stop_conditions.COUNT:
                if self.count >= self.limit:
                    self.stop()
            elif self._stop_condition == self._stop_conditions.TIME:
                if self.run_time >= self.limit:
                    self.stop()
    
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
    def file_dialog_save(title="Guardar archivo", initial_dir="/", filetypes=[("Text files","*.txt")]):
        
        return file_dialog_open(title=title, initial_dir=initial_dir, filetypes=filetypes)
    
    @staticmethod
    def split_path(path):
        from os.path import split, splitext
        
        folder, full_name = split(path)
        name, extension = splitext(full_name)
        
        return folder, name, extension, full_name
    
    @staticmethod
    def is_pathname_valid(pathname: str) -> bool:
        '''
        `True` if the passed pathname is a valid pathname for the current OS;
        `False` otherwise.
        '''
        
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








