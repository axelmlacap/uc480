# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 12:50:11 2019

@author: Axel Lacapmesure
"""

from .enums import Error

from tkinter import filedialog, Tk

from lantz.qt.utils.qt import QtGui

def get_layout0(vertical):

    layout = QtGui.QVBoxLayout() if vertical else QtGui.QHBoxLayout()

    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)

    return layout

def prop_to_int(prop):
    return int.from_bytes(prop.value, byteorder='big')

def file_dialog_save(title="Guardar archivo", initial_dir="/", filetypes=[("all files","*.*")]):
    tkroot = Tk()
    
    path = filedialog.asksaveasfilename(title=title,
                                        initialdir=initial_dir,
                                        filetypes=filetypes)
    tkroot.lift()
    tkroot.withdraw()
    
    return path

def file_dialog_open(title="Abrir archivo", initial_dir="/", filetypes=[("all files","*.*")]):
    tkroot = Tk()
    
    path = filedialog.askopenfilename(title=title,
                                      initialdir=initial_dir,
                                      filetypes=filetypes)
    tkroot.lift()
    tkroot.withdraw()
    
    return path

def safe_call(parent, fun, *args, **kwargs):
    
    """
    DOESN'T SUPPORT RETURNS. REPLACED BY safe_get OR safe_set
    
    Safe call for uEye functions. Handles error validation.
    Check if return of uEye method is SUCCESS. If not, raises or prints to
    log an error.
    """
    
    ret = fun(*args, **kwargs)
    
    if ret != Error.IS_SUCCESS:
        try:
            parent.log_error("Error while calling {0:}: error code {1:} '{2:}'".format(fun.__name__, ret, Error(ret).name))
        except AttributeError:
            raise RuntimeError("Error while calling {0:}: error code {1:} '{2:}'".format(fun.__name__, ret, Error(ret).name))

def safe_set(parent, fun, *args, **kwargs):
    
    """
    Safe call for uEye setters. Handles error validation.
    Check if return of uEye method is SUCCESS. If not, raises or prints to
    log an error.
    """
    
    ret = fun(*args, **kwargs)
    
    if ret != Error.IS_SUCCESS:
        try:
            parent.log_error("Error while calling {0:}: error code {1:} '{2:}'".format(fun.__name__, ret, Error(ret).name))
        except AttributeError:
            raise RuntimeError("Error while calling {0:}: error code {1:} '{2:}'".format(fun.__name__, ret, Error(ret).name))

def safe_get(parent, fun, *args, **kwargs):
    
    """
    Safe call for uEye getters. Handles error validation.
    Check if return of uEye method is SUCCESS. If not, raises or prints to
    log an error.
    """
    
    ret = fun(*args, **kwargs)
    
    if ret == Error.IS_NO_SUCCESS:
        try:
            parent.log_error("Error while calling {0:}: error code {1:} '{2:}'".format(fun.__name__, ret, Error(ret).name))
            return ret
        except AttributeError:
            raise RuntimeError("Error while calling {0:}: error code {1:} '{2:}'".format(fun.__name__, ret, Error(ret).name))
    else:
        return ret
