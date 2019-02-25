# -*- coding: utf-8 -*-
"""
Created on Thu Dec 13 10:32:43 2018

@author: Fotonica
"""

from matplotlib import pyplot as plt
import numpy as np
from scipy.interpolate import interp1d

from enum import Enum, IntEnum, IntFlag, Flag, unique, auto

from re import split, sub

import os, sys, errno

from datetime import datetime

from functools import wraps

from tkinter import filedialog
import tkinter as tk

from lantz.core import ureg
from lantz.qt import QtCore

def prop_to_int(prop):
    return int.from_bytes(prop.value, byteorder='big')

def file_dialog_save(title="Guardar archivo", initial_dir="/", filetypes=[("all files","*.*")]):
    tkroot = tk.Tk()
    
    path = filedialog.asksaveasfilename(title=title,
                                        initialdir=initial_dir,
                                        filetypes=filetypes)
    tkroot.lift()
    tkroot.withdraw()
    
    return path

def file_dialog_open(title="Abrir archivo", initial_dir="/", filetypes=[("all files","*.*")]):
    tkroot = tk.Tk()
    
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

class EnumMixin:
    
    @classmethod
    def to_plain_dict(cls):
        dictionary = {}
        for name, enum in cls.__members__.items():
            dictionary[name] = enum.value
        
        return dictionary

class TrueFalse(EnumMixin, IntEnum):
    TRUE = 1
    FALSE = 0

class Error(EnumMixin, IntEnum):
    IS_NO_SUCCESS = -1
    IS_SUCCESS = 0
    IS_INVALID_CAMERA_HANDLE = 1
    IS_INVALID_HANDLE = 1
    IS_IO_REQUEST_FAILED = 2
    IS_CANT_OPEN_DEVICE = 3
    IS_CANT_CLOSE_DEVICE = 4
    IS_CANT_SETUP_MEMORY = 5
    IS_NO_HWND_FOR_ERROR_REPORT = 6
    IS_ERROR_MESSAGE_NOT_CREATED = 7
    IS_ERROR_STRING_NOT_FOUND = 8
    IS_HOOK_NOT_CREATED = 9
    IS_TIMER_NOT_CREATED = 10
    IS_CANT_OPEN_REGISTRY = 11
    IS_CANT_READ_REGISTRY = 12
    IS_CANT_VALIDATE_BOARD = 13
    IS_CANT_GIVE_BOARD_ACCESS = 14
    IS_NO_IMAGE_MEM_ALLOCATED = 15
    IS_CANT_CLEANUP_MEMORY = 16
    IS_CANT_COMMUNICATE_WITH_DRIVER = 17
    IS_FUNCTION_NOT_SUPPORTED_YET = 18
    IS_OPERATING_SYSTEM_NOT_SUPPORTED = 19
    IS_INVALID_VIDEO_IN = 20
    IS_INVALID_IMG_SIZE = 21
    IS_INVALID_ADDRESS = 22
    IS_INVALID_VIDEO_MODE = 23
    IS_INVALID_AGC_MODE = 24
    IS_INVALID_GAMMA_MODE = 25
    IS_INVALID_SYNC_LEVEL = 26
    IS_INVALID_CBARS_MODE = 27
    IS_INVALID_COLOR_MODE = 28
    IS_INVALID_SCALE_FACTOR = 29
    IS_INVALID_IMAGE_SIZE = 30
    IS_INVALID_IMAGE_POS = 31
    IS_INVALID_CAPTURE_MODE = 32
    IS_INVALID_RISC_PROGRAM = 33
    IS_INVALID_BRIGHTNESS = 34
    IS_INVALID_CONTRAST = 35
    IS_INVALID_SATURATION_U = 36
    IS_INVALID_SATURATION_V = 37
    IS_INVALID_HUE = 38
    IS_INVALID_HOR_FILTER_STEP = 39
    IS_INVALID_VERT_FILTER_STEP = 40
    IS_INVALID_EEPROM_READ_ADDRESS = 41
    IS_INVALID_EEPROM_WRITE_ADDRESS = 42
    IS_INVALID_EEPROM_READ_LENGTH = 43
    IS_INVALID_EEPROM_WRITE_LENGTH = 44
    IS_INVALID_BOARD_INFO_POINTER = 45
    IS_INVALID_DISPLAY_MODE = 46
    IS_INVALID_ERR_REP_MODE = 47
    IS_INVALID_BITS_PIXEL = 48
    IS_INVALID_MEMORY_POINTER = 49
    IS_FILE_WRITE_OPEN_ERROR = 50
    IS_FILE_READ_OPEN_ERROR = 51
    IS_FILE_READ_INVALID_BMP_ID = 52
    IS_FILE_READ_INVALID_BMP_SIZE = 53
    IS_FILE_READ_INVALID_BIT_COUNT = 54
    IS_WRONG_KERNEL_VERSION = 55
    IS_RISC_INVALID_XLENGTH = 60
    IS_RISC_INVALID_YLENGTH = 61
    IS_RISC_EXCEED_IMG_SIZE = 62
    IS_DD_MAIN_FAILED = 70
    IS_DD_PRIMSURFACE_FAILED = 71
    IS_DD_SCRN_SIZE_NOT_SUPPORTED = 72
    IS_DD_CLIPPER_FAILED = 73
    IS_DD_CLIPPER_HWND_FAILED = 74
    IS_DD_CLIPPER_CONNECT_FAILED = 75
    IS_DD_BACKSURFACE_FAILED = 76
    IS_DD_BACKSURFACE_IN_SYSMEM = 77
    IS_DD_MDL_MALLOC_ERR = 78
    IS_DD_MDL_SIZE_ERR = 79
    IS_DD_CLIP_NO_CHANGE = 80
    IS_DD_PRIMMEM_NULL = 81
    IS_DD_BACKMEM_NULL = 82
    IS_DD_BACKOVLMEM_NULL = 83
    IS_DD_OVERLAYSURFACE_FAILED = 84
    IS_DD_OVERLAYSURFACE_IN_SYSMEM = 85
    IS_DD_OVERLAY_NOT_ALLOWED = 86
    IS_DD_OVERLAY_COLKEY_ERR = 87
    IS_DD_OVERLAY_NOT_ENABLED = 88
    IS_DD_GET_DC_ERROR = 89
    IS_DD_DDRAW_DLL_NOT_LOADED = 90
    IS_DD_THREAD_NOT_CREATED = 91
    IS_DD_CANT_GET_CAPS = 92
    IS_DD_NO_OVERLAYSURFACE = 93
    IS_DD_NO_OVERLAYSTRETCH = 94
    IS_DD_CANT_CREATE_OVERLAYSURFACE = 95
    IS_DD_CANT_UPDATE_OVERLAYSURFACE = 96
    IS_DD_INVALID_STRETCH = 97
    IS_EV_INVALID_EVENT_NUMBER = 100
    IS_INVALID_MODE = 101
    IS_CANT_FIND_FALCHOOK = 102
    IS_CANT_FIND_HOOK = 102
    IS_CANT_GET_HOOK_PROC_ADDR = 103
    IS_CANT_CHAIN_HOOK_PROC = 104
    IS_CANT_SETUP_WND_PROC = 105
    IS_HWND_NULL = 106
    IS_INVALID_UPDATE_MODE = 107
    IS_NO_ACTIVE_IMG_MEM = 108
    IS_CANT_INIT_EVENT = 109
    IS_FUNC_NOT_AVAIL_IN_OS = 110
    IS_CAMERA_NOT_CONNECTED = 111
    IS_SEQUENCE_LIST_EMPTY = 112
    IS_CANT_ADD_TO_SEQUENCE = 113
    IS_LOW_OF_SEQUENCE_RISC_MEM = 114
    IS_IMGMEM2FREE_USED_IN_SEQ = 115
    IS_IMGMEM_NOT_IN_SEQUENCE_LIST = 116
    IS_SEQUENCE_BUF_ALREADY_LOCKED = 117
    IS_INVALID_DEVICE_ID = 118
    IS_INVALID_BOARD_ID = 119
    IS_ALL_DEVICES_BUSY = 120
    IS_HOOK_BUSY = 121
    IS_TIMED_OUT = 122
    IS_NULL_POINTER = 123
    IS_WRONG_HOOK_VERSION = 124
    IS_INVALID_PARAMETER = 125
    IS_NOT_ALLOWED = 126
    IS_OUT_OF_MEMORY = 127
    IS_INVALID_WHILE_LIVE = 128
    IS_ACCESS_VIOLATION = 129
    IS_UNKNOWN_ROP_EFFECT = 130
    IS_INVALID_RENDER_MODE = 131
    IS_INVALID_THREAD_CONTEXT = 132
    IS_NO_HARDWARE_INSTALLED = 133
    IS_INVALID_WATCHDOG_TIME = 134
    IS_INVALID_WATCHDOG_MODE = 135
    IS_INVALID_PASSTHROUGH_IN = 136
    IS_ERROR_SETTING_PASSTHROUGH_IN = 137
    IS_FAILURE_ON_SETTING_WATCHDOG = 138
    IS_NO_USB20 = 139
    IS_CAPTURE_RUNNING = 140
    IS_MEMORY_BOARD_ACTIVATED = 141
    IS_MEMORY_BOARD_DEACTIVATED = 142
    IS_NO_MEMORY_BOARD_CONNECTED = 143
    IS_TOO_LESS_MEMORY = 144
    IS_IMAGE_NOT_PRESENT = 145
    IS_MEMORY_MODE_RUNNING = 146
    IS_MEMORYBOARD_DISABLED = 147
    IS_TRIGGER_ACTIVATED = 148
    IS_WRONG_KEY = 150
    IS_CRC_ERROR = 151
    IS_NOT_YET_RELEASED = 152
    IS_NOT_CALIBRATED = 153
    IS_WAITING_FOR_KERNEL = 154
    IS_NOT_SUPPORTED = 155
    IS_TRIGGER_NOT_ACTIVATED = 156
    IS_OPERATION_ABORTED = 157
    IS_BAD_STRUCTURE_SIZE = 158
    IS_INVALID_BUFFER_SIZE = 159
    IS_INVALID_PIXEL_CLOCK = 160
    IS_INVALID_EXPOSURE_TIME = 161
    IS_AUTO_EXPOSURE_RUNNING = 162
    IS_CANNOT_CREATE_BB_SURF = 163
    IS_CANNOT_CREATE_BB_MIX = 164
    IS_BB_OVLMEM_NULL = 165
    IS_CANNOT_CREATE_BB_OVL = 166
    IS_NOT_SUPP_IN_OVL_SURF_MODE = 167
    IS_INVALID_SURFACE = 168
    IS_SURFACE_LOST = 169
    IS_RELEASE_BB_OVL_DC = 170
    IS_BB_TIMER_NOT_CREATED = 171
    IS_BB_OVL_NOT_EN = 172
    IS_ONLY_IN_BB_MODE = 173
    IS_INVALID_COLOR_FORMAT = 174
    IS_INVALID_WB_BINNING_MODE = 175
    IS_INVALID_I2C_DEVICE_ADDRESS = 176
    IS_COULD_NOT_CONVERT = 177
    IS_TRANSFER_ERROR = 178
    IS_PARAMETER_SET_NOT_PRESENT = 179
    IS_INVALID_CAMERA_TYPE = 180
    IS_INVALID_HOST_IP_HIBYTE = 181
    IS_CM_NOT_SUPP_IN_CURR_DISPLAYMODE = 182
    IS_NO_IR_FILTER = 183
    IS_STARTER_FW_UPLOAD_NEEDED = 184
    IS_DR_LIBRARY_NOT_FOUND = 185
    IS_DR_DEVICE_OUT_OF_MEMORY = 186
    IS_DR_CANNOT_CREATE_SURFACE = 187
    IS_DR_CANNOT_CREATE_VERTEX_BUFFER = 188
    IS_DR_CANNOT_CREATE_TEXTURE = 189
    IS_DR_CANNOT_LOCK_OVERLAY_SURFACE = 190
    IS_DR_CANNOT_UNLOCK_OVERLAY_SURFACE = 191
    IS_DR_CANNOT_GET_OVERLAY_DC = 192
    IS_DR_CANNOT_RELEASE_OVERLAY_DC = 193
    IS_DR_DEVICE_CAPS_INSUFFICIENT = 194
    IS_INCOMPATIBLE_SETTING = 195
    IS_DR_NOT_ALLOWED_WHILE_DC_IS_ACTIVE = 196
    IS_DEVICE_ALREADY_PAIRED = 197
    IS_SUBNETMASK_MISMATCH = 198
    IS_SUBNET_MISMATCH = 199
    IS_INVALID_IP_CONFIGURATION = 200
    IS_DEVICE_NOT_COMPATIBLE = 201
    IS_NETWORK_FRAME_SIZE_INCOMPATIBLE = 202
    IS_NETWORK_CONFIGURATION_INVALID = 203
    IS_ERROR_CPU_IDLE_STATES_CONFIGURATION = 204
    IS_DEVICE_BUSY = 205
    IS_SENSOR_INITIALIZATION_FAILED = 206
    IS_IMAGE_BUFFER_NOT_DWORD_ALIGNED = 207

class SensorID(EnumMixin, IntEnum):
    IS_SENSOR_INVALID = 0x0000
    IS_SENSOR_UI141X_M = 0x0001
    IS_SENSOR_UI141X_C = 0x0002
    IS_SENSOR_UI144X_M = 0x0003
    IS_SENSOR_UI144X_C = 0x0004
    IS_SENSOR_UI154X_M = 0x0030
    IS_SENSOR_UI154X_C = 0x0031
    IS_SENSOR_UI145X_C = 0x0008
    IS_SENSOR_UI146X_C = 0x000a
    IS_SENSOR_UI148X_M = 0x000b
    IS_SENSOR_UI148X_C = 0x000c
    IS_SENSOR_UI121X_M = 0x0010
    IS_SENSOR_UI121X_C = 0x0011
    IS_SENSOR_UI122X_M = 0x0012
    IS_SENSOR_UI122X_C = 0x0013
    IS_SENSOR_UI164X_C = 0x0015
    IS_SENSOR_UI155X_C = 0x0017
    IS_SENSOR_UI1223_M = 0x0018
    IS_SENSOR_UI1223_C = 0x0019
    IS_SENSOR_UI149X_M = 0x003E
    IS_SENSOR_UI149X_C = 0x003F
    IS_SENSOR_UI1225_M = 0x0022
    IS_SENSOR_UI1225_C = 0x0023
    IS_SENSOR_UI1645_C = 0x0025
    IS_SENSOR_UI1555_C = 0x0027
    IS_SENSOR_UI1545_M = 0x0028
    IS_SENSOR_UI1545_C = 0x0029
    IS_SENSOR_UI1455_C = 0x002B
    IS_SENSOR_UI1465_C = 0x002D
    IS_SENSOR_UI1485_M = 0x002E
    IS_SENSOR_UI1485_C = 0x002F
    IS_SENSOR_UI1495_M = 0x0040
    IS_SENSOR_UI1495_C = 0x0041
    IS_SENSOR_UI112X_M = 0x004A
    IS_SENSOR_UI112X_C = 0x004B
    IS_SENSOR_UI1008_M = 0x004C
    IS_SENSOR_UI1008_C = 0x004D
    IS_SENSOR_UI1005_M = 0x020A
    IS_SENSOR_UI1005_C = 0x020B
    IS_SENSOR_UI1240_M = 0x0050
    IS_SENSOR_UI1240_C = 0x0051
    IS_SENSOR_UI1240_NIR = 0x0062
    IS_SENSOR_UI1240LE_M = 0x0054
    IS_SENSOR_UI1240LE_C = 0x0055
    IS_SENSOR_UI1240LE_NIR = 0x0064
    IS_SENSOR_UI1240ML_M = 0x0066
    IS_SENSOR_UI1240ML_C = 0x0067
    IS_SENSOR_UI1240ML_NIR = 0x0200
    IS_SENSOR_UI1243_M_SMI = 0x0078
    IS_SENSOR_UI1243_C_SMI = 0x0079
    IS_SENSOR_UI1543_M = 0x0032
    IS_SENSOR_UI1543_C = 0x0033
    IS_SENSOR_UI1544_M = 0x003A
    IS_SENSOR_UI1544_C = 0x003B
    IS_SENSOR_UI1543_M_WO = 0x003C
    IS_SENSOR_UI1543_C_WO = 0x003D
    IS_SENSOR_UI1453_C = 0x0035
    IS_SENSOR_UI1463_C = 0x0037
    IS_SENSOR_UI1483_M = 0x0038
    IS_SENSOR_UI1483_C = 0x0039
    IS_SENSOR_UI1493_M = 0x004E
    IS_SENSOR_UI1493_C = 0x004F
    IS_SENSOR_UI1463_M_WO = 0x0044
    IS_SENSOR_UI1463_C_WO = 0x0045
    IS_SENSOR_UI1553_C_WN = 0x0047
    IS_SENSOR_UI1483_M_WO = 0x0048
    IS_SENSOR_UI1483_C_WO = 0x0049
    IS_SENSOR_UI1580_M = 0x005A
    IS_SENSOR_UI1580_C = 0x005B
    IS_SENSOR_UI1580LE_M = 0x0060
    IS_SENSOR_UI1580LE_C = 0x0061
    IS_SENSOR_UI1360M = 0x0068
    IS_SENSOR_UI1360C = 0x0069
    IS_SENSOR_UI1360NIR = 0x0212
    IS_SENSOR_UI1370M = 0x006A
    IS_SENSOR_UI1370C = 0x006B
    IS_SENSOR_UI1370NIR = 0x0214
    IS_SENSOR_UI1250_M = 0x006C
    IS_SENSOR_UI1250_C = 0x006D
    IS_SENSOR_UI1250_NIR = 0x006E
    IS_SENSOR_UI1250LE_M = 0x0070
    IS_SENSOR_UI1250LE_C = 0x0071
    IS_SENSOR_UI1250LE_NIR = 0x0072
    IS_SENSOR_UI1250ML_M = 0x0074
    IS_SENSOR_UI1250ML_C = 0x0075
    IS_SENSOR_UI1250ML_NIR = 0x0202
    IS_SENSOR_XS = 0x020B
    IS_SENSOR_UI1493_M_AR = 0x0204
    IS_SENSOR_UI1493_C_AR = 0x0205
    IS_SENSOR_UI1060_M = 0x021A
    IS_SENSOR_UI1060_C = 0x021B
    IS_SENSOR_UI1013XC = 0x021D
    IS_SENSOR_UI1140M = 0x021E
    IS_SENSOR_UI1140C = 0x021F
    IS_SENSOR_UI1140NIR = 0x0220
    IS_SENSOR_UI1590M = 0x0222
    IS_SENSOR_UI1590C = 0x0223
    IS_SENSOR_UI1260_M = 0x0226
    IS_SENSOR_UI1260_C = 0x0227
    IS_SENSOR_UI1130_M = 0x022A
    IS_SENSOR_UI1130_C = 0x022B
    IS_SENSOR_UI1160_M = 0x022C
    IS_SENSOR_UI1160_C = 0x022D
    IS_SENSOR_UI1180_M = 0x022E
    IS_SENSOR_UI1180_C = 0x022F
    IS_SENSOR_UI1080_M = 0x0230
    IS_SENSOR_UI1080_C = 0x0231
    IS_SENSOR_UI1280_M = 0x0232
    IS_SENSOR_UI1280_C = 0x0233
    IS_SENSOR_UI1860_M = 0x0234
    IS_SENSOR_UI1860_C = 0x0235
    IS_SENSOR_UI1880_M = 0x0236
    IS_SENSOR_UI1880_C = 0x0237
    IS_SENSOR_UI1270_M = 0x0238
    IS_SENSOR_UI1270_C = 0x0239
    IS_SENSOR_UI1070_M = 0x023A
    IS_SENSOR_UI1070_C = 0x023B
    IS_SENSOR_UI1130LE_M = 0x023C
    IS_SENSOR_UI1130LE_C = 0x023D
    IS_SENSOR_UI1290_M = 0x023E
    IS_SENSOR_UI1290_C = 0x023F
    IS_SENSOR_UI1090_M = 0x0240
    IS_SENSOR_UI1090_C = 0x0241
    IS_SENSOR_UI1000_M = 0x0242
    IS_SENSOR_UI1000_C = 0x0243
    IS_SENSOR_UI1200_M = 0x0244
    IS_SENSOR_UI1200_C = 0x0245
    IS_SENSOR_UI223X_M = 0x0080
    IS_SENSOR_UI223X_C = 0x0081
    IS_SENSOR_UI241X_M = 0x0082
    IS_SENSOR_UI241X_C = 0x0083
    IS_SENSOR_UI234X_M = 0x0084
    IS_SENSOR_UI234X_C = 0x0085
    IS_SENSOR_UI221X_M = 0x0088
    IS_SENSOR_UI221X_C = 0x0089
    IS_SENSOR_UI231X_M = 0x0090
    IS_SENSOR_UI231X_C = 0x0091
    IS_SENSOR_UI222X_M = 0x0092
    IS_SENSOR_UI222X_C = 0x0093
    IS_SENSOR_UI224X_M = 0x0096
    IS_SENSOR_UI224X_C = 0x0097
    IS_SENSOR_UI225X_M = 0x0098
    IS_SENSOR_UI225X_C = 0x0099
    IS_SENSOR_UI214X_M = 0x009A
    IS_SENSOR_UI214X_C = 0x009B
    IS_SENSOR_UI228X_M = 0x009C
    IS_SENSOR_UI228X_C = 0x009D
    IS_SENSOR_UI223X_M_R3 = 0x0180
    IS_SENSOR_UI223X_C_R3 = 0x0181
    IS_SENSOR_UI241X_M_R2 = 0x0182
    IS_SENSOR_UI251X_M = 0x0182
    IS_SENSOR_UI241X_C_R2 = 0x0183
    IS_SENSOR_UI251X_C = 0x0183
    IS_SENSOR_UI234X_M_R3 = 0x0184
    IS_SENSOR_UI234X_C_R3 = 0x0185
    IS_SENSOR_UI221X_M_R3 = 0x0188
    IS_SENSOR_UI221X_C_R3 = 0x0189
    IS_SENSOR_UI222X_M_R3 = 0x0192
    IS_SENSOR_UI222X_C_R3 = 0x0193
    IS_SENSOR_UI224X_M_R3 = 0x0196
    IS_SENSOR_UI224X_C_R3 = 0x0197
    IS_SENSOR_UI225X_M_R3 = 0x0198
    IS_SENSOR_UI225X_C_R3 = 0x0199
    IS_SENSOR_UI2130_M = 0x019E
    IS_SENSOR_UI2130_C = 0x019F
    IS_SENSOR_PASSIVE_MULTICAST = 0x0F00

class SensorColorMode(EnumMixin, IntEnum):
    IS_COLORMODE_INVALID = 0
    IS_COLORMODE_MONOCHROME = 1
    IS_COLORMODE_BAYER = 2
    IS_COLORMODE_CBYCRY = 4
    IS_COLORMODE_JPEG = 8

class ImageColorMode(EnumMixin, IntEnum):
    IS_GET_COLOR_MODE = 0x8000
    IS_CM_FORMAT_PLANAR = 0x2000
    IS_CM_FORMAT_MASK = 0x2000
    IS_CM_ORDER_BGR = 0x0000
    IS_CM_ORDER_RGB = 0x0080
    IS_CM_ORDER_MASK = 0x0080
    IS_CM_PREFER_PACKED_SOURCE_FORMAT = 0x4000
    IS_CM_SENSOR_RAW8 = 11
    IS_CM_SENSOR_RAW10 = 33
    IS_CM_SENSOR_RAW12 = 27
    IS_CM_SENSOR_RAW16 = 29
    IS_CM_MONO8 = 6
    IS_CM_MONO10 = 34
    IS_CM_MONO12 = 26
    IS_CM_MONO16 = 28
    IS_CM_BGR5_PACKED = (3|IS_CM_ORDER_BGR)
    IS_CM_BGR565_PACKED = (2|IS_CM_ORDER_BGR)
    IS_CM_RGB8_PACKED = (1|IS_CM_ORDER_RGB)
    IS_CM_BGR8_PACKED = (1|IS_CM_ORDER_BGR)
    IS_CM_RGBA8_PACKED = (0|IS_CM_ORDER_RGB)
    IS_CM_BGRA8_PACKED = (0|IS_CM_ORDER_BGR)
    IS_CM_RGBY8_PACKED = (24|IS_CM_ORDER_RGB)
    IS_CM_BGRY8_PACKED = (24|IS_CM_ORDER_BGR)
    IS_CM_RGB10_PACKED = (25|IS_CM_ORDER_RGB)
    IS_CM_BGR10_PACKED = (25|IS_CM_ORDER_BGR)
    IS_CM_RGB10_UNPACKED = (35|IS_CM_ORDER_RGB)
    IS_CM_BGR10_UNPACKED = (35|IS_CM_ORDER_BGR)
    IS_CM_RGB12_UNPACKED = (30|IS_CM_ORDER_RGB)
    IS_CM_BGR12_UNPACKED = (30|IS_CM_ORDER_BGR)
    IS_CM_RGBA12_UNPACKED = (31|IS_CM_ORDER_RGB)
    IS_CM_BGRA12_UNPACKED = (31|IS_CM_ORDER_BGR)
    IS_CM_JPEG = 32
    IS_CM_UYVY_PACKED = 12
    IS_CM_UYVY_MONO_PACKED = 13
    IS_CM_UYVY_BAYER_PACKED = 14
    IS_CM_CBYCRY_PACKED = 23
    IS_CM_RGB8_PLANAR = (1|IS_CM_ORDER_RGB|IS_CM_FORMAT_PLANAR)
    IS_CM_ALL_POSSIBLE = 0xFFFF
    IS_CM_MODE_MASK = 0x007F

class DisplayMode(EnumMixin, IntEnum):
    IS_GET_DISPLAY_MODE = 0x8000
    IS_SET_DM_DIB = 1
    IS_SET_DM_DIRECT3D = 4
    IS_SET_DM_OPENGL = 8
    IS_SET_DM_MONO = 0x800
    IS_SET_DM_BAYER = 0x1000
    IS_SET_DM_YCBCR = 0x4000

class AOI(EnumMixin, IntEnum):
    IS_AOI_IMAGE_SET_AOI = 0x0001
    IS_AOI_IMAGE_GET_AOI = 0x0002
    IS_AOI_IMAGE_SET_POS = 0x0003
    IS_AOI_IMAGE_GET_POS = 0x0004
    IS_AOI_IMAGE_SET_SIZE = 0x0005
    IS_AOI_IMAGE_GET_SIZE = 0x0006
    IS_AOI_IMAGE_GET_POS_MIN = 0x0007
    IS_AOI_IMAGE_GET_SIZE_MIN = 0x0008
    IS_AOI_IMAGE_GET_POS_MAX = 0x0009
    IS_AOI_IMAGE_GET_SIZE_MAX = 0x0010
    IS_AOI_IMAGE_GET_POS_INC = 0x0011
    IS_AOI_IMAGE_GET_SIZE_INC = 0x0012
    IS_AOI_IMAGE_GET_POS_X_ABS = 0x0013
    IS_AOI_IMAGE_GET_POS_Y_ABS = 0x0014
    IS_AOI_IMAGE_GET_ORIGINAL_AOI = 0x0015
    IS_AOI_IMAGE_POS_ABSOLUTE = 0x10000000
    IS_AOI_IMAGE_SET_POS_FAST = 0x0020
    IS_AOI_IMAGE_GET_POS_FAST_SUPPORTED = 0x0021
    IS_AOI_AUTO_BRIGHTNESS_SET_AOI = 0x0030
    IS_AOI_AUTO_BRIGHTNESS_GET_AOI = 0x0031
    IS_AOI_AUTO_WHITEBALANCE_SET_AOI = 0x0032
    IS_AOI_AUTO_WHITEBALANCE_GET_AOI = 0x0033
    IS_AOI_MULTI_GET_SUPPORTED_MODES = 0x0100
    IS_AOI_MULTI_SET_AOI = 0x0200
    IS_AOI_MULTI_GET_AOI = 0x0400
    IS_AOI_MULTI_DISABLE_AOI = 0x0800
    IS_AOI_MULTI_MODE_X_Y_AXES = 0x0001
    IS_AOI_MULTI_MODE_Y_AXES = 0x0002
    IS_AOI_MULTI_MODE_GET_MAX_NUMBER = 0x0003
    IS_AOI_MULTI_MODE_GET_DEFAULT = 0x0004
    IS_AOI_MULTI_MODE_ONLY_VERIFY_AOIS = 0x0005
    IS_AOI_MULTI_MODE_GET_MINIMUM_SIZE = 0x0006
    IS_AOI_MULTI_MODE_GET_ENABLED = 0x0007
    IS_AOI_MULTI_STATUS_SETBYUSER = 0x00000001
    IS_AOI_MULTI_STATUS_COMPLEMENT = 0x00000002
    IS_AOI_MULTI_STATUS_VALID = 0x00000004
    IS_AOI_MULTI_STATUS_CONFLICT = 0x00000008
    IS_AOI_MULTI_STATUS_ERROR = 0x00000010
    IS_AOI_MULTI_STATUS_UNUSED = 0x00000020
    IS_AOI_SEQUENCE_GET_SUPPORTED = 0x0050
    IS_AOI_SEQUENCE_SET_PARAMS = 0x0051
    IS_AOI_SEQUENCE_GET_PARAMS = 0x0052
    IS_AOI_SEQUENCE_SET_ENABLE = 0x0053
    IS_AOI_SEQUENCE_GET_ENABLE = 0x0054
    IS_AOI_SEQUENCE_INDEX_AOI_1 = 0
    IS_AOI_SEQUENCE_INDEX_AOI_2 = 1
    IS_AOI_SEQUENCE_INDEX_AOI_3 = 2
    IS_AOI_SEQUENCE_INDEX_AOI_4 = 4

class Timeout(EnumMixin, IntEnum):
    IS_GET_LIVE = 0x8000
    IS_WAIT = 0x0001
    IS_DONT_WAIT = 0x0000

class Trigger(EnumMixin, IntEnum):
    IS_GET_EXTERNALTRIGGER = 0x8000
    IS_GET_TRIGGER_STATUS = 0x8001
    IS_GET_TRIGGER_MASK = 0x8002
    IS_GET_TRIGGER_INPUTS = 0x8003
    IS_GET_SUPPORTED_TRIGGER_MODE = 0x8004
    IS_GET_TRIGGER_COUNTER = 0x8000
    IS_SET_TRIGGER_MASK = 0x0100
    IS_SET_TRIGGER_CONTINUOUS = 0x1000
    IS_SET_TRIGGER_OFF = 0x0000
    IS_SET_TRIGGER_HI_LO = (IS_SET_TRIGGER_CONTINUOUS|0x0001)
    IS_SET_TRIGGER_LO_HI = (IS_SET_TRIGGER_CONTINUOUS|0x0002)
    IS_SET_TRIGGER_SOFTWARE = (IS_SET_TRIGGER_CONTINUOUS|0x0008)
    IS_SET_TRIGGER_HI_LO_SYNC = 0x0010
    IS_SET_TRIGGER_LO_HI_SYNC = 0x0020
    IS_SET_TRIGGER_PRE_HI_LO = (IS_SET_TRIGGER_CONTINUOUS|0x0040)
    IS_SET_TRIGGER_PRE_LO_HI = (IS_SET_TRIGGER_CONTINUOUS|0x0080)
    IS_GET_TRIGGER_DELAY = 0x8000
    IS_GET_MIN_TRIGGER_DELAY = 0x8001
    IS_GET_MAX_TRIGGER_DELAY = 0x8002
    IS_GET_TRIGGER_DELAY_GRANULARITY = 0x8003

class Exposure(EnumMixin, IntEnum):
    IS_EXPOSURE_CMD_GET_CAPS = 1
    IS_EXPOSURE_CMD_GET_EXPOSURE_DEFAULT = 2
    IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MIN = 3
    IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MAX = 4
    IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_INC = 5
    IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE = 6
    IS_EXPOSURE_CMD_GET_EXPOSURE = 7
    IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_MIN = 8
    IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_MAX = 9
    IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_INC = 10
    IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE = 11
    IS_EXPOSURE_CMD_SET_EXPOSURE = 12
    IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_MIN = 13
    IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_MAX = 14
    IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_INC = 15
    IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE = 16
    IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_ENABLE = 17
    IS_EXPOSURE_CMD_SET_LONG_EXPOSURE_ENABLE = 18
    IS_EXPOSURE_CMD_GET_DUAL_EXPOSURE_RATIO_DEFAULT = 19
    IS_EXPOSURE_CMD_GET_DUAL_EXPOSURE_RATIO_RANGE = 20
    IS_EXPOSURE_CMD_GET_DUAL_EXPOSURE_RATIO = 21
    IS_EXPOSURE_CMD_SET_DUAL_EXPOSURE_RATIO = 22

class PixelClock(EnumMixin, IntEnum):
    IS_PIXELCLOCK_CMD_GET_NUMBER = 1
    IS_PIXELCLOCK_CMD_GET_LIST = 2
    IS_PIXELCLOCK_CMD_GET_RANGE = 3
    IS_PIXELCLOCK_CMD_GET_DEFAULT = 4
    IS_PIXELCLOCK_CMD_GET = 5
    IS_PIXELCLOCK_CMD_SET = 6


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
        return (self.index-1 - np.arange(self.size)) % self.size
    
    @property
    def indices_old_first(self):
        return (np.arange(self.size) - self.index) % self.size


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
#        
#        first_idx = min(0, new_limits[0] - old_limits[0])
#        last_idx = new_limits[1] - old_limits[1]
#        first_value = min(max(old_limits[0], new_limits[0]), old_limits[1]-1)
#        last_value = max(min(old_limits[1]-1, new_limits[1]-1), old_limits[0])
#        first_idx = (self.x==first_value).nonzero()[0][0]
#        last_idx = (self.x==last_value).nonzero()[0][0] + 1
        slc = slice(int(first_idx), int(last_idx))
#        print(slc)
        
#        print(last_value, last_idx)
        
        # Are you expanding? Pad with zeros
        pad_size_left = min(max(0, int(old_limits[0]-new_limits[0])), new_limits[1]-new_limits[0])
        pad_size_right = min(max(0, int(new_limits[1]-old_limits[1])), new_limits[1]-new_limits[0])
        
        # Go through all spectrums and reshape
        for spectrum in [self.raw, self.dark, self.reference, self.processed]:
            if not isinstance(spectrum, type(None)):       
                zeros_left = np.zeros((spectrum.y.shape[0], pad_size_left))
                zeros_right = np.zeros((spectrum.y.shape[0], pad_size_right))
#                print(zeros_left.shape, spectrum.y[:, slc].shape, zeros_right.shape)
                
                spectrum._y = np.hstack((zeros_left, spectrum.y[:, slc], zeros_right))
                spectrum._x = calibrated_x
                
                
#                # Are you shrinking? Take slice
#                if new_limits[0] > old_limits[0] or new_limits[1] < old_limits[1]:
#                    indices = np.logical_and(self.x >= new_limits[0], self.x < new_limits[1])
#                    new_y = new_y[:, indices]
#                
#                # Are you extending? Pad with zeros
#                if new_limits[0] < old_limits[0]:
#                    pad_size_left = int(old_limits[0]-new_limits[0])
#                    zeros = np.zeros((self.raw._y.shape[0], pad_size_left))
#                    new_y = np.hstack((zeros, new_y))
#                if new_limits[1] > old_limits[1]:
#                    pad_size_right = int(new_limits[1]-old_limits[-1])
#                    zeros = np.zeros((self.raw._y.shape[0], pad_size_right))
#                    new_y = np.hstack((new_y, zeros))
        
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
        tkroot = tk.Tk()
        
        path = filedialog.asksaveasfilename(title=title,
                                            initialdir=initial_dir,
                                            filetypes=filetypes)
        tkroot.lift()
        tkroot.withdraw()
        
        return path
    
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








