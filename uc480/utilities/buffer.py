# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 12:57:34 2019

@author: Fotonica
"""

from numpy import arange

from lantz.qt import QtCore


class BufferCore(QtCore.QObject):
    
    was_filled = QtCore.pyqtSignal()
    was_reset = QtCore.pyqtSignal()
    was_resized = QtCore.pyqtSignal()
    
    def __init__(self, size=1):
        super().__init__()
        
        self._size = 1
        self._index = 0
        self._count = 0
        
        self.size = size
    
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
        self._index = int(value % self.size)
        
        if self._index == 0 and self._count != 0:
            self.was_filled.emit()
    
    @property
    def count(self):
        return self._count
    
    @count.setter
    def count(self, value):
        self._count = int(value)
    
    @property
    def size(self):
        return self._size
    
    @size.setter
    def size(self, value):
        self._size = int(value)
        self.reset()
        
        self.was_resized.emit()
    
    def reset(self):
        self._index = 0
        self._count = 0
        
        self.was_reset.emit()
    
    @property
    def indices_new_first(self):
        return (self.index-1 - arange(self.size)) % self.size
    
    @property
    def indices_old_first(self):
        return (arange(self.size) - self.index) % self.size