# -*- coding: utf-8 -*-

#from uc480 import DEFAULTS_PATH
from uc480.config import CONFIG_DEFAULT
from uc480.utilities.aoi import AOI2D
from uc480.utilities import enums
from uc480.utilities.func import safe_call, safe_get, safe_set, prop_to_int

import numpy as np

from pyueye import ueye

from lantz.core import Driver, ureg
from lantz import Feat, Action

import ctypes

from yaml import safe_load, YAMLError, dump

from enum import EnumMeta


class Config:
    pass

def validate_handle(handle, none_return = None):
    
    if handle == None:
        if none_return == None:
            handle, _handle = None, None
        else:
            handle, _handle = validate_handle(none_return)
    elif isinstance(handle, int):
        handle = handle
        _handle = ueye.HIDS(handle)
    elif isinstance(handle, ueye.HIDS):
        handle = handle.value
        _handle = handle
    else:
        raise TypeError('Camera handle must be int type or pyueye.ueye.HIDS type.')
    
    return (handle, _handle)

def validate_timeout(value):
    if isinstance(value, type(enums.VideoCapture.IS_DONT_WAIT)):
        timeout = value.value
    if isinstance(value, str):
        try:
            timeout = enums.VideoCapture[value].value
        except KeyError:
            raise KeyError("Invalid wait timeout '{0:}'.".format(value))
    elif isinstance(value, int):
        if value in enums.VideoCapture.to_plain_dict().values():
            timeout = value
        elif value >= 4 and value <= 429496729:
            timeout = value
        else:
            raise ValueError('Wait timeout must be within 4 and 429496729 range (40 ms to approx. 1193 hs).')
    else:
        raise TypeError('Wait timeout must be int type within [4,429496729] range or a valid VideoCapture enum value.')
    
    return timeout

def validate_aoi(value, max_width, max_height):
    if not isinstance(max_width, int):
        TypeError('max_width must be int type.')
    
    if not isinstance(max_height, int):
        TypeError('max_width must be int type.')
    
    if value == None:
            value = [0, 0, max_width-1, max_height-1]
    elif isinstance(value, list):
        if len(value) != 4:
            raise ValueError('AOI value must be a list of four integers: [x, y, width, height].')
        elif any([not isinstance(x, int) for x in value]):
            raise TypeError('AOI elements must be int type.')
    else:
        raise TypeError('AOI value must be a list of four integers: [x, y, width, height].')
    
    if value[0] > max_width:
        raise ValueError('Specified AOI x position of {0:} px exceeds maximum width of {1:} px.'.format(value[0], max_width))
    if value[1] > max_height:
        raise ValueError('Specified AOI y position of {0:} px exceeds maximum height of {1:} px.'.format(value[1], max_height))
    if value[0]+value[2] > max_width:
        value[2] = max_width - value[0]
        raise Warning('AOI width exceeds maximum dimensions. AOI will be cropped to {0:} px width.'.format(value[2]))
    if value[1]+value[3] > max_height:
        value[3] = max_height - value[1]
        raise Warning('AOI height exceeds maximum dimensions. AOI will be cropped to {0:} px height.'.format(value[3]))
    
    return value


class CameraAOI(AOI2D):
    
    @classmethod
    def from_camera(cls, camera):
        max_width = int(camera.sensor_info.max_width)
        max_height = int(camera.sensor_info.max_height)
        
        return cls(camera, limits=[0,max_width,0,max_height], canvas_limits=[0,max_width,0,max_height], units=ureg.px)
    
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(condition="even", *args, **kwargs)
        
        if not isinstance(parent, type(None)):
            self.parent = parent
            self.handle = parent.handle
            self._handle = parent._handle
        else:
            self.parent = None
            self.handle = None
            self._handle = None
        self.units = ureg.px
        self.inverse_y = True
    
    def __getitem__(self, idx):
        if isinstance(idx, int):
            if idx == 0:
                return int(self.xmin.to(ureg.px).magnitude)
            elif idx == 1:
                return int(self.ymin.to(ureg.px).magnitude)
            elif idx == 2:
                return int(self.width.to(ureg.px).magnitude)
            elif idx == 3:
                return int(self.height.to(ureg.px).magnitude)
            else:
                raise IndexError('Index exceeds AOI elements [x, y, width, height].')
        else:
            raise IndexError('Index must be int type.')
    
    def __setitem__(self, idx, value):
        if isinstance(idx, int):
            if idx == 0:
                self.xmin = value
            elif idx == 1:
                self.ymin = value
            elif idx == 2:
                self.width = value
            elif idx == 3:
                self.height = value
            else:
                raise IndexError('Index exceeds AOI elements [x, y, width, height].')
        else:
            raise IndexError('Index must be int type.')
        
    def __call__(self, value = None):
        if value == None:
            return self.limits
        else:
            self.limits = value
    
    def write_to_camera(self):
        rect = ueye.IS_RECT()
        rect.s32X.value = int(self._xmin.to(ureg.px).magnitude)
        rect.s32Y.value = int(self._ymin.to(ureg.px).magnitude)
        rect.s32Width.value = int(self.width.to(ureg.px).magnitude)
        rect.s32Height.value = int(self.height.to(ureg.px).magnitude)
        
        self.parent.allocate_memory(width=rect.s32Width.value, height=rect.s32Height.value)
        self.parent.set_memory()
        
        safe_call(self,
                  ueye.is_AOI,
                  self._handle,
                  enums.AOI.IS_AOI_IMAGE_SET_AOI.value,
                  rect,
                  ueye.sizeof(rect))
        
    def sync_with_camera(self):
        rect = ueye.IS_RECT()
        safe_call(self,
                  ueye.is_AOI,
                  self._handle,
                  enums.AOI.IS_AOI_IMAGE_GET_AOI.value,
                  rect,
                  ueye.sizeof(rect))
        
        self._xmin = rect.s32X.value * ureg.px
        self._ymin = rect.s32Y.value * ureg.px
        self.width = rect.s32Width.value * ureg.px
        self.height = rect.s32Height.value * ureg.px


class CameraInfo(Driver):
    
    _CAMINFO_obj = None
    
    def __init__(self, handle, CAMINFO_obj = None, *args, **kwargs):
        super().__init__()
        
        self.handle, self._handle = validate_handle(handle)
        
        if CAMINFO_obj == None:
            self._CAMINFO_obj = self.get_camera_info(handle = handle)
        elif isinstance(CAMINFO_obj, ueye.CAMINFO):
            self._CAMINFO_obj = CAMINFO_obj
        else:
            raise TypeError('CAMINFO_obj must be pyueye.ueye.CAMINFO type.')
        
        if self.is_empty(self._CAMINFO_obj):
            self.log_warning('Camera info returned an empty CAMINFO object.')
    
    def get_camera_info(self, handle = None):
        
        _, handle = validate_handle(handle, none_return = self.handle)
        
        CAMINFO_obj = ueye.CAMINFO()
        safe_call(self, ueye.is_GetCameraInfo, handle, CAMINFO_obj)
        
        return CAMINFO_obj
    
    @Feat(units = None)
    def serial_number(self, read_once = True):
        if self._CAMINFO_obj is None:
            self._CAMINFO_obj = self.get_camera_info(handle = self._handle)
        
        return self._CAMINFO_obj.SerNo.decode('utf-8')
    
    @Feat(units = None)
    def manufacturer(self, read_once = True):
        if self._CAMINFO_obj is None:
            self._CAMINFO_obj = self.get_camera_info(handle = self._handle)
        
        return self._CAMINFO_obj.ID.decode('utf-8')
    
    @Feat(units = None)
    def usb_version(self, read_once = True):
        if self._CAMINFO_obj is None:
            self._CAMINFO_obj = self.get_camera_info(handle = self._handle)
        
        return self._CAMINFO_obj.Version.decode('utf-8')
    
    @Feat(units = None)
    def quality_check_date(self, read_once = True):
        if self._CAMINFO_obj is None:
            self._CAMINFO_obj = self.get_camera_info(handle = self._handle)
        
        return self._CAMINFO_obj.Date.decode('utf-8')
    
    @Feat(units = None)
    def camera_type(self, read_once = True):
        if self._CAMINFO_obj is None:
            self._CAMINFO_obj = self.get_camera_info(handle = self._handle)
        
        return self._CAMINFO_obj.Type.value
    
    def is_empty(self, CAMINFO_obj = None):
        
        if CAMINFO_obj == None:
            CAMINFO_obj = self._CAMINFO_obj
        
        if isinstance(CAMINFO_obj, ueye.CAMINFO):
            empty = ueye.CAMINFO()
            checks = []
            
            checks.append(CAMINFO_obj.SerNo.decode('utf-8') == empty.SerNo.decode('utf-8'))
            checks.append(CAMINFO_obj.ID.decode('utf-8') == empty.ID.decode('utf-8'))
            checks.append(CAMINFO_obj.Version.decode('utf-8') == empty.Version.decode('utf-8'))
            checks.append(CAMINFO_obj.Date.decode('utf-8') == empty.Date.decode('utf-8'))
            checks.append(CAMINFO_obj.Select.value == empty.Select.value)
            checks.append(CAMINFO_obj.Type.value == empty.Type.value)
            
            return all(checks)
        
        else:
            raise TypeError('CAMINFO_obj must be pyueye.ueye.CAMINFO type (if no argument was passed, check if CAMINFO_obj was instantiated).')


class SensorInfo(Driver):
    
    _SENSORINFO_obj = None
    
    def __init__(self, handle, SENSORINFO_obj = None, *args, **kwargs):
        super().__init__()
        
        self.handle, self._handle = validate_handle(handle)

        if SENSORINFO_obj == None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = handle)
        elif isinstance(SENSORINFO_obj, ueye.SENSORINFO):
            self._SENSORINFO_obj = SENSORINFO_obj
        else:
            raise TypeError('SENSORINFO_obj must be pyueye.ueye.SENSORINFO type.')
        
        if self.is_empty(self._SENSORINFO_obj):
            self.log_warning('Camera sensor info returned an empty SENSORINFO object.')
    
    def get_sensor_info(self, handle = None):
        
        _, handle = validate_handle(handle, none_return = self.handle)
        
        SENSORINFO_obj = ueye.SENSORINFO()
        safe_call(self, ueye.is_GetSensorInfo, handle, SENSORINFO_obj)
        
        return SENSORINFO_obj
    
    def is_empty(self, SENSORINFO_obj = None):
        
        if SENSORINFO_obj == None:
            SENSORINFO_obj = self._SENSORINFO_obj
        
        if isinstance(SENSORINFO_obj, ueye.SENSORINFO):
            empty = ueye.SENSORINFO()
            checks = []
            
            checks.append(SENSORINFO_obj.SensorID.value == empty.SensorID.value)
            checks.append(SENSORINFO_obj.nColorMode.value == empty.nColorMode.value)
            checks.append(SENSORINFO_obj.nMaxWidth.value == empty.nMaxWidth.value)
            checks.append(SENSORINFO_obj.nMaxHeight.value == empty.nMaxHeight.value)
            checks.append(SENSORINFO_obj.bMasterGain.value == empty.bMasterGain.value)
            checks.append(SENSORINFO_obj.bRGain.value == empty.bRGain.value)
            checks.append(SENSORINFO_obj.bGGain.value == empty.bGGain.value)
            checks.append(SENSORINFO_obj.bBGain.value == empty.bBGain.value)
            checks.append(SENSORINFO_obj.bGlobShutter.value == empty.bGlobShutter.value)
            checks.append(SENSORINFO_obj.wPixelSize.value == empty.wPixelSize.value)
            checks.append(SENSORINFO_obj.nUpperLeftBayerPixel.value == empty.nUpperLeftBayerPixel.value)
            
            return all(checks)
        
        else:
            raise TypeError('SENSORINFO_obj must be pyueye.ueye.SENSORINFO type (if no argument was passed, check if SENSORINFO_obj was instantiated).')
    
    @Feat(values = enums.SensorID.to_plain_dict(), read_once = True)
    def sensor_id(self, read_once=True):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.SensorID.value
        
    @Feat(units = None)
    def sensor_name(self, read_once = True):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.strSensorName.decode('utf-8')
    
    @Feat(values = enums.SensorColorMode.to_plain_dict(), read_once = True)
    def color_mode(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return prop_to_int(self._SENSORINFO_obj.nColorMode)
    
    @Feat(units = None, read_once = True)
    def max_width(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.nMaxWidth.value
    
    @Feat(units = None, read_once = True)
    def max_height(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.nMaxHeight.value
    
    @Feat(values = enums.TrueFalse.to_plain_dict(), read_once = True)
    def has_master_gain(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.bMasterGain.value
     
    @Feat(values = enums.TrueFalse.to_plain_dict(), read_once = True)
    def has_r_gain(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.bRGain.value
    
    @Feat(values = enums.TrueFalse.to_plain_dict(), read_once = True)
    def has_g_gain(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.bGGain.value
    
    @Feat(values = enums.TrueFalse.to_plain_dict(), read_once = True)
    def has_b_gain(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.bBGain.value
    
    @Feat(values = enums.TrueFalse.to_plain_dict(), read_once = True)
    def has_global_shutter(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.bGlobShutter.value
    
    @Feat(units = 'um', read_once=True)
    def pixel_size(self):
        if self._SENSORINFO_obj is None:
            self._SENSORINFO_obj = self.get_sensor_info(handle = self._handle)
        
        return self._SENSORINFO_obj.wPixelSize.value / 100


class DeviceInfo(Driver):
    
    _IS_DEVICE_INFO_obj = None
    
    def __init__(self, handle, IS_DEVICE_INFO_obj=None, *args, **kwargs):
        super().__init__()
        
        self.handle, self._handle = validate_handle(handle)
        
        if IS_DEVICE_INFO_obj == None:
            self._IS_DEVICE_INFO_obj = self.get_device_info(handle=handle)
        elif isinstance(IS_DEVICE_INFO_obj, ueye.IS_DEVICE_INFO):
            self._IS_DEVICE_INFO_obj = IS_DEVICE_INFO_obj
        else:
            raise TypeError('IS_DEVICE_INFO_obj must be pyueye.ueye.IS_DEVICE_INFO type.')
        
        if self.is_empty(self._IS_DEVICE_INFO_obj):
            self.log_warning('Device info returned an empty IS_DEVICE_INFO object.')
    
    def get_device_info(self, handle=None):
        _, handle = validate_handle(handle, none_return=self.handle)
        
        IS_DEVICE_INFO_obj = ueye.IS_DEVICE_INFO()
        
        print(handle, IS_DEVICE_INFO_obj)
        
        safe_call(self,
                  ueye.is_DeviceInfo,
                  handle,
                  ueye.IS_DEVICE_INFO_CMD_GET_DEVICE_INFO,
                  IS_DEVICE_INFO_obj,
                  ueye.sizeof(IS_DEVICE_INFO_obj))
        
        print(IS_DEVICE_INFO_obj)
        
        return IS_DEVICE_INFO_obj
    
    def update(self, handle=None):
        
        _, handle = validate_handle(handle, none_return=self.handle)
        
        self._IS_DEVICE_INFO_obj = self.get_device_info()
    
    @Feat(units=None)
    def firmware_version(self, read_once=True):
        if self._IS_DEVICE_INFO_obj is None:
            self._IS_DEVICE_INFO_obj = self.get_device_info(handle=self._handle)
        
        return self._IS_DEVICE_INFO_obj.infoDevHeartbeat.dwRuntimeFirmwareVersion.value
    
    @Feat(units=None)
    def temperature(self):
        if self._IS_DEVICE_INFO_obj is None:
            self._IS_DEVICE_INFO_obj = self.get_device_info(handle=self._handle)
        
        return self._IS_DEVICE_INFO_obj.infoDevHeartbeat.wTemperature.value
    
    @Feat(values=enums.Connectivity.to_plain_dict(), units=None)
    def link_speed(self, read_once=True):
        if self._IS_DEVICE_INFO_obj is None:
            self._IS_DEVICE_INFO_obj = self.get_device_info(handle=self._handle)
        
        return self._IS_DEVICE_INFO_obj.infoDevHeartbeat.wLinkSpeed_Mb.value
    
    @Feat(units=None)
    def device_id(self, read_once=True):
        if self._IS_DEVICE_INFO_obj is None:
            self._IS_DEVICE_INFO_obj = self.get_device_info(handle=self._handle)
        
        return self._IS_DEVICE_INFO_obj.infoDevControl.dwDeviceId.value
    
    def is_empty(self, IS_DEVICE_INFO_obj = None):
        
        if IS_DEVICE_INFO_obj == None:
            IS_DEVICE_INFO_obj = self._IS_DEVICE_INFO_obj
        
        if isinstance(IS_DEVICE_INFO_obj, ueye.IS_DEVICE_INFO):
            empty = ueye.IS_DEVICE_INFO()
            checks = []
            
            checks.append(IS_DEVICE_INFO_obj.infoDevHeartbeat.dwRuntimeFirmwareVersion.value == empty.infoDevHeartbeat.dwRuntimeFirmwareVersion.value)
            checks.append(IS_DEVICE_INFO_obj.infoDevHeartbeat.wTemperature.value == empty.infoDevHeartbeat.wTemperature.value)
            checks.append(IS_DEVICE_INFO_obj.infoDevHeartbeat.wLinkSpeed_Mb.value == empty.infoDevHeartbeat.wLinkSpeed_Mb.value)
            checks.append(IS_DEVICE_INFO_obj.infoDevControl.dwDeviceId.value == empty.infoDevControl.dwDeviceId.value)
            
            return all(checks)
        
        else:
            raise TypeError('CAMINFO_obj must be pyueye.ueye.CAMINFO type (if no argument was passed, check if CAMINFO_obj was instantiated).')


class Camera(Driver):
    
    def __init__(self, handle = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.handle, self._handle = validate_handle(handle)
        
        # Initializate camera and properties
        self.device_info = DeviceInfo(handle=self._handle)
        self.initiate()
        self.sensor_info = SensorInfo(handle=self._handle)
        self.camera_info = CameraInfo(handle=self._handle)
        
        # Initializate AOI
        sensor_limits = [0, self.sensor_info.max_width, 0, self.sensor_info.max_height]
        self.aoi = CameraAOI(parent=self, limits=sensor_limits, canvas_limits=sensor_limits, units=ureg.px)
        
        # Initial values needed
        self._mem_pointer = ueye.c_mem_p()
        self._mem_id = ueye.int()
        self._bits_per_pixel = 0
        self.reset_dark_base_pattern()
        
        # Load default configuration
        self.setup_from_file(config_path=CONFIG_DEFAULT)
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.close()
    
    @Action()
    def initiate(self):
        safe_call(self,
                  ueye.is_InitCamera,
                  self._handle,
                  None)
    
    @Action()
    def close(self):
        self.log_debug('Closing camera...')
        safe_call(self,
                  ueye.is_ExitCamera,
                  self._handle)
        self.log_debug('Camera closed.')
    
    # Image:
    @Feat()
    def bits_per_pixel(self):
        return self._bits_per_pixel
    
    @Feat()
    def bytes_per_pixel(self):
        return int(np.ceil(self._bits_per_pixel / 8))
    
    @Feat(units = 'bits')
    def bitdepth(self):
        sensor_color_mode = self.sensor_info.color_mode
        
        if sensor_color_mode == enums.SensorColorMode.IS_COLORMODE_BAYER:
            # setup the color depth to the current windows setting   
            bitdepth = ueye.INT()
            safe_call(self, ueye.is_GetColorDepth, self._handle, bitdepth, ueye.INT())
            return bitdepth.value
        
        elif sensor_color_mode == enums.SensorColorMode.IS_COLORMODE_CBYCRY:
            # for color camera models use RGB32 mode
            return 32
        
        elif sensor_color_mode == enums.SensorColorMode.IS_COLORMODE_MONOCHROME:
            # for monochrome camera models use Y8 mode
            return 8
        
        else:
            raise ValueError("Invalid sensor color mode '{0:}'".format(sensor_color_mode))
    
    @Feat(units = 'bytes')
    def bytedepth(self):
        return int(self.bitdepth/8)
    
    @Feat()
    def dtype(self):
        if self.dark_correction:
            return np.float64
        else:
            return self._dtype
    
    @Feat()
    def ctype(self):
        return self._ctype
    
    @Feat(values = enums.ImageColorMode.to_plain_dict(), units = None)
    def color_mode(self):
        return safe_get(self,
                        ueye.is_SetColorMode,
                        self._handle,
                        enums.ImageColorMode.IS_GET_COLOR_MODE.value)
    
    @color_mode.setter
    def color_mode(self, value):
        # Check if new value is the same as before
        if enums.ImageColorMode(value) == self.color_mode:
            return None
        
        # Stop video capture if running
        if self.get_capture_status():
            self.stop_video_capture()
            restart = True
        else:
            restart = False
        
        # Change color mode
        safe_set(self,
                 ueye.is_SetColorMode,
                 self._handle,
                 value)
        
        # Update pixel bit depth if changed
        if enums.BitsPerPixel[enums.ImageColorMode(value).name] != self._bits_per_pixel:
            self._bits_per_pixel = enums.BitsPerPixel[enums.ImageColorMode(value).name].value
            
            if self._bits_per_pixel > 32:
                self._dtype = np.dtype(np.uint64)
                self._ctype = ctypes.c_uint64
            elif self._bits_per_pixel > 16:
                self._dtype = np.dtype(np.uint32)
                self._ctype = ctypes.c_uint32
            elif self._bits_per_pixel > 8:
                self._dtype = np.dtype(np.uint16)
                self._ctype = ctypes.c_uint16
            else:
                self._dtype = np.dtype(np.uint8)
                self._ctype = ctypes.c_uint8
            
            # Reallocate memory
            self.allocate_memory()
            self.set_memory()
        
        # Restart video capture if it was running
        if restart:
            self.start_video_capture()
    
    @Action()
    def get_auto_color_mode(self):
        sensor_color_mode = self.sensor_info.color_mode
        
        if sensor_color_mode == enums.SensorColorMode.IS_COLORMODE_BAYER:
            # setup the color depth to the current windows setting   
            bitdepth = ueye.INT()
            color_mode = ueye.INT()
            safe_call(self,
                      ueye.is_GetColorDepth,
                      self._handle,
                      bitdepth,
                      color_mode)
        
        elif sensor_color_mode == enums.SensorColorMode.IS_COLORMODE_CBYCRY:
            # for color camera models use RGB32 mode
            color_mode = enums.ImageColorMode.IS_CM_BGRA8_PACKED
        
        elif sensor_color_mode == enums.SensorColorMode.IS_COLORMODE_MONOCHROME:
            # for monochrome camera models use Y8 mode
            color_mode = enums.ImageColorMode.IS_CM_MONO8
        
        else:
            raise ValueError("Invalid sensor color mode '{0:}'".format(sensor_color_mode))
        
        return color_mode
    
    @Action()
    def set_auto_color_mode(self):
        self.color_mode = self.get_auto_color_mode()
    
    @Action()
    def get_windows_color_settings(self):
        color_mode = ueye.c_int()
        bitdepth = ueye.c_int()
        
        safe_call(self,
                  ueye.is_GetColorDepth,
                  self._handle,
                  color_mode,
                  bitdepth)
        
        return enums.ImageColorMode(color_mode.value), bitdepth.value
    
    # Memory:
    """
    
    Faltan implementar LockSeqBuf, UnlockSeqBuf, AddToSequence.
    
    """
    
    @Action()
    def allocate_memory(self, width=None, height=None):
        """
        
        Falta implementar resolver el caso donde is_SetImageMem devuelve
        IS_SEQ_BUFFER_IS_LOCKED
        
        """
        if width == None:
            width = ueye.INT(self.aoi[2])
        elif isinstance(width, int):
            width = ueye.INT(width)
        else:
            raise TypeError('AOI width must be int type.')
            
        if height == None:
            height = ueye.INT(self.aoi[3])
        elif isinstance(height, int):
            height = ueye.INT(height)
        else:
            raise TypeError('AOI height must be int type.')
        
        bitdepth = ueye.INT(self.bits_per_pixel)
        
        safe_call(self,
                  ueye.is_AllocImageMem,
                  self._handle,
                  width,
                  height,
                  bitdepth,
                  self._mem_pointer,
                  self._mem_id)
    
    @Action()
    def set_memory(self, memory_pointer = None, memory_id = None):
        
        if memory_pointer == None:
            memory_pointer = self._mem_pointer
        elif isinstance(memory_pointer, ueye.c_mem_p):
            raise TypeError('memory_pointer type must be pyueye.ueye.c_mem_p type.')
        
        if memory_id == None:
            memory_id = self._mem_id
        elif isinstance(memory_id, ueye.INT):
            raise TypeError('image_memory_id type must be pyueye.ueye.INT type.')
        
        safe_call(self,
                  ueye.is_SetImageMem,
                  self._handle,
                  memory_pointer,
                  memory_id)
    
    @Action()
    def free_memory(self, memory_pointer = None, memory_id = None):
        
        if memory_pointer == None:
            memory_pointer = self._mem_pointer
        elif isinstance(memory_pointer, ueye.c_mem_p):
            raise TypeError('memory_pointer type must be pyueye.ueye.c_mem_p type.')
        
        if memory_id == None:
            memory_id = self._mem_id
        elif isinstance(memory_id, ueye.INT):
            raise TypeError('image_memory_id type must be pyueye.ueye.INT type.')
        
        safe_call(self,
                  ueye.is_FreeImageMem,
                  self._handle,
                  memory_pointer,
                  memory_id)
    
    @Feat(units=None)
    def memory_pitch(self):
        pitch = ueye.c_int()
        
        safe_call(self,
                  ueye.is_GetImageMemPitch,
                  self._handle,
                  pitch)
        
        return pitch.value
    
    #Configuration
    @Action()
    def get_supported_features(self):
        supported_features = ueye.c_int()
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.DeviceFeature.IS_DEVICE_FEATURE_CMD_GET_SUPPORTED_FEATURES.value,
                  supported_features,
                  ueye.sizeof(supported_features))
        
        return supported_features.value
    
    @Feat(values=enums.ShutterModes.to_plain_dict(), units=None)
    def shutter_mode(self):
        shutter_mode = ueye.c_int()
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.Shutter.IS_DEVICE_FEATURE_CMD_GET_SHUTTER_MODE.value,
                  shutter_mode,
                  ueye.sizeof(shutter_mode))
        
        return shutter_mode.value
    
    @shutter_mode.setter
    def shutter_mode(self, value):
        shutter_mode = ueye.c_int(value)
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.Shutter.IS_DEVICE_FEATURE_CMD_SET_SHUTTER_MODE.value,
                  shutter_mode,
                  ueye.sizeof(shutter_mode))
    
    @Action()
    def get_shutter_modes_list(self):
        supported_features = ueye.c_int()
        shutter_modes = []
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.DeviceFeature.IS_DEVICE_FEATURE_CMD_GET_SUPPORTED_FEATURES.value,
                  supported_features,
                  ueye.sizeof(supported_features))
        
        if supported_features & enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING.value:
            shutter_modes.append(enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING)
        if supported_features & enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL.value:
            shutter_modes.append(enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL)
        if supported_features & enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START.value:
            shutter_modes.append(enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START)
        if supported_features & enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL_ALTERNATIVE_TIMING.value:
            shutter_modes.append(enums.ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL_ALTERNATIVE_TIMING)
        
        return shutter_modes
    
    @Feat(values=enums.SensorBitDepths.to_plain_dict(), units=None)
    def sensor_bit_depth(self):
        bit_depth = ueye.c_int()
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.SensorBitDepth.IS_DEVICE_FEATURE_CMD_GET_SENSOR_BIT_DEPTH.value,
                  bit_depth,
                  ueye.sizeof(bit_depth))
        
        return bit_depth.value
    
    @sensor_bit_depth.setter
    def sensor_bit_depth(self, value):
        bit_depth = ueye.c_int(value)
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.SensorBitDepth.IS_DEVICE_FEATURE_CMD_SET_SENSOR_BIT_DEPTH.value,
                  bit_depth,
                  ueye.sizeof(bit_depth))
    
    @Action()
    def get_bit_depths_list(self):
        supported_bit_depths = ueye.c_int()
        bit_depths = []
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.BitDepth.IS_DEVICE_FEATURE_CMD_GET_SUPPORTED_SENSOR_BIT_DEPTHS.value,
                  supported_bit_depths,
                  ueye.sizeof(supported_bit_depths))
        
        if supported_bit_depths & enums.BitDepths.IS_SENSOR_BIT_DEPTH_8_BIT.value:
            bit_depths.append(enums.BitDepths.IS_SENSOR_BIT_DEPTH_8_BIT)
        if supported_bit_depths & enums.BitDepths.IS_SENSOR_BIT_DEPTH_10_BIT.value:
            bit_depths.append(enums.BitDepths.IS_SENSOR_BIT_DEPTH_10_BIT)
        if supported_bit_depths & enums.BitDepths.IS_SENSOR_BIT_DEPTH_12_BIT.value:
            bit_depths.append(enums.BitDepths.IS_SENSOR_BIT_DEPTH_12_BIT)
        
        return bit_depths
    
    @Action()
    def get_default_bit_depth(self):
        bit_depth = ueye.c_int()
        
        safe_call(self,
                  ueye.is_DeviceFeature,
                  self._handle,
                  enums.BitDepth.IS_DEVICE_FEATURE_CMD_GET_SENSOR_BIT_DEPTH_DEFAULT,
                  bit_depth,
                  ueye.sizeof(bit_depth))
        
        return bit_depth.value
    
    @Feat(units = 'MHz')
    def pixel_clock(self):
        pixel_clock = ueye.c_int()
        
        safe_get(self,
                 ueye.is_PixelClock,
                 self._handle,
                 enums.PixelClock.IS_PIXELCLOCK_CMD_GET,
                 pixel_clock,
                 ueye.sizeof(pixel_clock))
        
        return pixel_clock.value * ureg.MHz
    
    @pixel_clock.setter
    def pixel_clock(self, value):
        # Smart users will provide a Pint Quantity.
        try:
            value = value.to('MHz').magnitude
        except:
            pass
        
        pixel_clock = ueye.c_int(value)
        
        safe_set(self,
                 ueye.is_PixelClock,
                 self._handle,
                 enums.PixelClock.IS_PIXELCLOCK_CMD_SET,
                 pixel_clock,
                 ueye.sizeof(pixel_clock))
    
    @Action()
    def get_pixel_clock_range(self):
        c_array = (ctypes.c_uint * 3)()

        safe_call(self,
                  ueye.is_PixelClock,
                  self._handle,
                  enums.PixelClock.IS_PIXELCLOCK_CMD_GET_RANGE,
                  c_array,
                  ueye.sizeof(c_array))
        
        pixel_clock_min = c_array[0] * ureg.MHz
        pixel_clock_max = c_array[1] * ureg.MHz
        pixel_clock_inc = c_array[2] * ureg.MHz
        
        if pixel_clock_inc == 0 * ureg.MHz:
            self.log_warning("Camera allows only discrete pixel clock values. Use 'get_pixel_clock_list' to obtain a list of allowed pixel clock values.")
        
        return pixel_clock_min, pixel_clock_max, pixel_clock_inc
    
    @Action()
    def get_pixel_clock_list(self):
        pixel_clock_min, pixel_clock_max, pixel_clock_inc = self.get_pixel_clock_range()
        
        if pixel_clock_inc != 0 * ureg.MHz:
            pixel_clock_list = np.arange(pixel_clock_min.magnitude,
                                         pixel_clock_max.magnitude + pixel_clock_inc.magnitude,
                                         pixel_clock_inc.magnitude)
        else:
            n_items = ueye.c_uint()
            
            safe_call(self,
                      ueye.is_PixelClock,
                      self._handle,
                      enums.PixelClock.IS_PIXELCLOCK_CMD_GET_NUMBER,
                      n_items,
                      ueye.sizeof(n_items))
            
            c_array = (ctypes.c_uint * n_items.value)()
            
            safe_call(self,
                      ueye.is_PixelClock,
                      self._handle,
                      enums.PixelClock.IS_PIXELCLOCK_CMD_GET_LIST,
                      c_array,
                      ueye.sizeof(c_array))
            
            pixel_clock_list = np.ctypeslib.as_array(c_array, (n_items.value, ))
        
        return pixel_clock_list * ureg.MHz
    
    @Action()
    def get_default_pixel_clock(self):
        pixel_clock = ueye.c_int()
        
        safe_get(self,
                 ueye.is_PixelClock,
                 enums.PixelClock.IS_PIXELCLOCK_CMD_GET_DEFAULT,
                 pixel_clock,
                 ueye.sizeof(pixel_clock))
        
        return pixel_clock.value
    
    @Feat(units = 'Hz')
    def frame_rate(self):        
        value = ueye.c_double()
        
        safe_call(self,
                  ueye.is_SetFrameRate, # Alternativa: ueye.is_GetFramesPerSecond,
                  self._handle,
                  enums.Framerate.IS_GET_FRAMERATE,
                  value)
        
        return value.value
    
    @frame_rate.setter
    def frame_rate(self, value):
        fps = ueye.c_double(value)
        new_fps = ueye.c_double()
        
        safe_set(self,
                 ueye.is_SetFrameRate,
                 self._handle,
                 fps,
                 new_fps)
    
    @Action()
    def get_default_frame_rate(self):        
        default_fps = ueye.c_double()
        
        safe_get(self,
                 ueye.is_SetFrameRate,
                 self._handle,
                 ueye.IS_GET_DEFAULT_FRAMERATE,
                 default_fps)
        
        default_fps = default_fps.value * ureg.Hz
                
        return default_fps
    
    @Action()
    def get_frame_time_range(self):
        
        frame_time_min = ueye.c_double()
        frame_time_max = ueye.c_double()
        frame_time_inc = ueye.c_double()
        
        safe_call(self,
                  ueye.is_GetFrameTimeRange,
                  self._handle,
                  frame_time_min,
                  frame_time_max,
                  frame_time_inc)
        
        frame_time_min = frame_time_min.value * ureg.s
        frame_time_max = frame_time_max.value * ureg.s
        frame_time_inc = frame_time_inc.value * ureg.s

        return frame_time_min, frame_time_max, frame_time_inc
    
    @Action()
    def get_frame_rate_range(self):
        
        frame_time_min, frame_time_max, _ = self.get_frame_time_range()
        
        if frame_time_max != 0 * ureg.s:
            frame_rate_min = 1/frame_time_max
        else:
            frame_rate_min = 0 * 1/ureg.s
            
        if frame_time_min != 0 * ureg.s:
            frame_rate_max = 1/frame_time_min
        else:
            frame_rate_max = 0 * 1/ureg.s
        
        frame_rate_inc = 0 * 1/ureg.s

        return frame_rate_min, frame_rate_max, frame_rate_inc
    
    @Action()
    def get_frame_rate_list(self):        
        length_min, length_max, length_inc = self.get_frame_time_range()
        length_min = length_min.to('s').magnitude
        length_max = length_max.to('s').magnitude
        length_inc = length_inc.to('s').magnitude
        
        fps = np.sort(1/np.arange(length_min, length_max + length_inc, length_inc)) * ureg.Hz
        
        return fps
    
    @Feat(units = 'ms')
    def exposure(self):        
        exposure = ueye.c_double()
        
        safe_call(self,
                  ueye.is_Exposure,
                  self._handle,
                  enums.Exposure.IS_EXPOSURE_CMD_GET_EXPOSURE.value,
                  exposure,
                  8)
        
        return exposure.value
    
    @exposure.setter
    def exposure(self, value):
        exposure = ueye.c_double(value)
        
        safe_set(self,
                 ueye.is_Exposure,
                 self._handle,
                 enums.Exposure.IS_EXPOSURE_CMD_SET_EXPOSURE.value,
                 exposure,
                 ueye.sizeof(exposure))
            
    @Action()
    def get_exposure_range(self):        
        exposure_min = ueye.c_double()
        exposure_max = ueye.c_double()
        exposure_inc = ueye.c_double()
        
        safe_call(self,
                  ueye.is_Exposure,
                  self._handle,
                  enums.Exposure.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MIN.value,
                  exposure_min,
                  8)
        
        safe_call(self,
                  ueye.is_Exposure,
                  self._handle,
                  enums.Exposure.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MAX.value,
                  exposure_max,
                  8)
        
        safe_call(self,
                  ueye.is_Exposure,
                  self._handle,
                  enums.Exposure.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_INC.value,
                  exposure_inc,
                  8)
        
        exposure_min = exposure_min.value * ureg.ms
        exposure_max = exposure_max.value * ureg.ms
        exposure_inc = exposure_inc.value * ureg.ms
        
        return exposure_min, exposure_max, exposure_inc
    
    @Action()
    def get_exposure_list(self):        
        exposure_min, exposure_max, exposure_inc = self.get_exposure_range()
        exposure_min = exposure_min.to('ms').magnitude
        exposure_max = exposure_max.to('ms').magnitude
        exposure_inc = exposure_inc.to('ms').magnitude
        
        exposure_list = np.arange(exposure_min, exposure_max + exposure_inc, exposure_inc) * ureg.ms
        
        return exposure_list
    
    @Action()
    def get_default_exposure(self):        
        exposure_default = ueye.c_double()
        
        safe_call(self,
              ueye.is_Exposure,
              self._handle,
              enums.Exposure.IS_EXPOSURE_CMD_GET_EXPOSURE_DEFAULT.value,
              exposure_default,
              8)
        
        exposure_default = exposure_default.value * ureg.ms
        
        return exposure_default
    
    @Feat(values=enums.BlacklevelModes.to_plain_dict())
    def blacklevel_mode(self):
        blacklevel_mode = ueye.c_int()
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_GET_MODE.value,
                  blacklevel_mode,
                  ueye.sizeof(blacklevel_mode))
        
        return blacklevel_mode.value
    
    @blacklevel_mode.setter
    def blacklevel_mode(self, value):
        blacklevel_mode = ueye.c_int(value)
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_SET_MODE.value,
                  blacklevel_mode,
                  ueye.sizeof(blacklevel_mode))
    
    @Action()
    def get_default_blacklevel_mode(self):
        blacklevel_mode = ueye.c_int()
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_GET_MODE_DEFAULT.value,
                  blacklevel_mode,
                  ueye.sizeof(blacklevel_mode))
        
        return blacklevel_mode
    
    @Feat(units=None)
    def blacklevel_offset(self):
        blacklevel_offset = ueye.c_int()
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_GET_OFFSET,
                  blacklevel_offset,
                  ueye.sizeof(blacklevel_offset))
        
        return blacklevel_offset.value
    
    @blacklevel_offset.setter
    def blacklevel_offset(self, value):
        blacklevel_offset = ueye.c_int(value)
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_SET_OFFSET,
                  blacklevel_offset,
                  ueye.sizeof(blacklevel_offset))
    
    @Action()
    def get_default_blacklevel_offset(self):
        blacklevel_offset = ueye.c_int()
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_GET_OFFSET_DEFAULT,
                  blacklevel_offset,
                  ueye.sizeof(blacklevel_offset))
        
        return blacklevel_offset.value
    
    @Action()
    def get_blacklevel_offset_range(self):
        blacklevel_offset_range = ueye.IS_RANGE_S32()
        
        safe_call(self,
                  ueye.is_Blacklevel,
                  self._handle,
                  enums.Blacklevel.IS_BLACKLEVEL_CMD_GET_OFFSET_RANGE,
                  blacklevel_offset_range,
                  ueye.sizeof(blacklevel_offset_range))
        
        blacklevel_offset_min = blacklevel_offset_range.s32Min.value
        blacklevel_offset_max = blacklevel_offset_range.s32Max.value
        blacklevel_offset_inc = blacklevel_offset_range.s32Inc.value
        
        return blacklevel_offset_min, blacklevel_offset_max, blacklevel_offset_inc
    
    @Action()
    def get_blacklevel_offset_list(self):        
        blacklevel_offset_min, blacklevel_offset_max, blacklevel_offset_inc = self.get_blacklevel_offset_range()
        blacklevel_offset_list = np.arange(blacklevel_offset_min, blacklevel_offset_max + blacklevel_offset_inc, blacklevel_offset_inc)
        
        return blacklevel_offset_list
    
    
    # Acquisition:
    @Feat(values = enums.Trigger.to_plain_dict())
    def trigger(self):
        return safe_get(ueye.is_SetExternalTrigger,
                        self._handle,
                        enums.Trigger.IS_GET_EXTERNALTRIGGER.value)
    
    @trigger.setter
    def trigger(self, value):
        safe_set(ueye.is_SetExternalTrigger,
                 self._handle,
                 enums.Trigger[value].value)
    
    @Action()
    def get_capture_status(self):
        return safe_get(self,
                        ueye.is_CaptureVideo,
                        self._handle,
                        enums.VideoCapture.IS_GET_LIVE)
    
    @Action()
    def start_video_capture(self, timeout=enums.VideoCapture.IS_DONT_WAIT):
        timeout = validate_timeout(timeout)
        
        safe_call(self,
                  ueye.is_CaptureVideo,
                  self._handle,
                  timeout.value)
    
    @Action()
    def stop_video_capture(self, timeout=enums.VideoCapture.IS_FORCE_VIDEO_STOP):
        timeout = validate_timeout(timeout)
        if timeout == enums.VideoCapture.IS_DONT_WAIT:
            timeout = enums.VideoCapture.IS_FORCE_VIDEO_STOP
        
        safe_call(self,
                  ueye.is_StopLiveVideo,
                  self._handle,
                  timeout.value)
    
    @Feat(values = enums.DisplayMode.to_plain_dict())
    def display_mode(self):
        return safe_get(self,
                        ueye.is_SetDisplayMode,
                        self._handle,
                        enums.DisplayMode.IS_GET_DISPLAY_MODE.value)
    
    @display_mode.setter
    def display_mode(self, value):
        safe_call(self,
                  ueye.is_SetDisplayMode,
                  self._handle,
                  value)
    
##   DEPRECATED:
#    @Action()
#    def get_frame(self):
#        data = ueye.get_data(self._mem_pointer,
#                             self.aoi[2],
#                             self.aoi[3],
#                             self.bitdepth,
#                             self.aoi[2],
#                             copy=False)
#        
#        return np.reshape(data, (int(self.aoi.height.magnitude), int(self.aoi.width.magnitude)))    
    
    @Feat(values=enums.TrueFalse.to_plain_dict())
    def dark_correction(self):
        return self._dark_correction
    
    @dark_correction.setter
    def dark_correction(self, value):
        self._dark_correction = value
    
    @property
    def dark_offset_base_pattern(self, value):
        return self._dark_offset_base_pattern
    
    @dark_offset_base_pattern.setter
    def dark_offset_base_pattern(self, value):
        if isinstance(value, np.ndarray):
            self._dark_offset_base_pattern= value
            self._correct_dark_offset = True
        elif isinstance(value, type(None)):
            self._dark_offset_base_pattern = np.zeros((self.aoi.canvas.height.magnitude, self.aoi.canvas.width.magnitude))
            self._correct_dark_offset = False
        
        self.update_dark_pattern()
    
    @property
    def dark_slope_base_pattern(self):
        return self._dark_slope_pattern
    
    @dark_slope_base_pattern.setter
    def dark_slope_base_pattern(self, value):
        if isinstance(value, np.ndarray):
            self._dark_slope_base_pattern = value
            self._correct_dark_slope = True
        elif isinstance(value, type(None)):
            self._dark_slope_base_pattern = np.zeros((self.aoi.canvas.height.magnitude, self.aoi.canvas.width.magnitude))
            self._correct_dark_slope = False
        
        self.update_dark_pattern()
    
    @property
    def dark_base_pattern(self):
        return self._dark_base_pattern
    
    @property
    def dark_pattern(self):
        return self._dark_pattern
    
    @Action()
    def reset_dark_base_pattern(self):
        self._dark_offset_base_pattern = np.zeros((self.aoi.canvas.height.magnitude, self.aoi.canvas.width.magnitude))
        self._dark_slope_base_pattern = np.zeros((self.aoi.canvas.height.magnitude, self.aoi.canvas.width.magnitude))
        
        self.update_dark_pattern()
    
    @Action()
    def update_dark_pattern(self, limits=None, exposure=None):
        # Use 'private' limit values (with underscores, as _xmin, _xmax, ...)
        # because public values for vertical axis are inverted.
        if isinstance(limits, type(None)):
            limits = [self.aoi._xmin.magnitude, self.aoi._xmax.magnitude, self.aoi._ymin.magnitude, self.aoi._ymax.magnitude]
        elif isinstance(limits, ureg.Quantity):
            limits = limits.magnitude
        elif isinstance(limits, list):
            pass
        else:
            raise TypeError("Argument 'limits' must be a four element list or pint array with structure [xmin, xmax, ymin, ymax].")
        
        if isinstance(exposure, type(None)):
            exposure = self.exposure.magnitude
        else:
            try:
                exposure = exposure.to(self.exposure.units).magnitude
            except AttributeError:
                pass
        
        self._dark_base_pattern = self._dark_offset_base_pattern + exposure * self._dark_slope_base_pattern
        self._dark_pattern = self._dark_base_pattern[limits[2]:limits[3], limits[0]:limits[1]]
    
    def correct_dark(self, image):
        return image - self._dark_pattern
    
    @Feat(values=enums.TrueFalse.to_plain_dict())
    def gain_correction(self):
        return self._gain_correction
    
    @gain_correction.setter
    def gain_correction(self, value):
        if not isinstance(value, bool):
            raise TypeError("Gain correction value must be bool type.")
        
        self._gain_correction = value
    
    @property
    def gain_correction_base_pattern(self, value):
        return self._gain_correction_base_pattern
    
    @gain_correction_base_pattern.setter
    def gain_correction_base_pattern(self, value):
        if isinstance(value, np.ndarray):
            self._gain_correction_base_pattern= value
            self._correct_gain = True
        elif isinstance(value, type(None)):
            self._gain_correction_base_pattern = np.ones((self.aoi.canvas.height.magnitude, self.aoi.canvas.width.magnitude))
            self._correct_gain = False
        
        self.update_gain_correction_pattern()
    
    @property
    def gain_correction_pattern(self):
        return self._gain_correction_pattern
    
    @Action()
    def reset_gain_correction_base_pattern(self):
        self._gain_correction_base_pattern = np.ones((self.aoi.canvas.height.magnitude, self.aoi.canvas.width.magnitude))
        
        self.update_gain_correction_pattern()
    
    @Action()
    def update_gain_correction_pattern(self, limits=None, exposure=None):
        # Use 'private' limit values (with underscores, as _xmin, _xmax, ...)
        # because public values for vertical axis are inverted.
        if isinstance(limits, type(None)):
            limits = [self.aoi._xmin.magnitude, self.aoi._xmax.magnitude, self.aoi._ymin.magnitude, self.aoi._ymax.magnitude]
        elif isinstance(limits, ureg.Quantity):
            limits = limits.magnitude
        elif isinstance(limits, list):
            pass
        else:
            raise TypeError("Argument 'limits' must be a four element list or pint array with structure [xmin, xmax, ymin, ymax].")
        
        self._gain_correction_pattern = self._gain_correction_base_pattern[limits[2]:limits[3], limits[0]:limits[1]]
    
    def correct_gain(self, image):
        return np.multiply(image, self.gain_correction_pattern)
    
    @Action()
    def get_frame(self):
        mem_pointer = ctypes.cast(self._mem_pointer, ctypes.POINTER(self._ctype))
        data = np.ctypeslib.as_array(mem_pointer, (self.aoi[3], self.aoi[2]))
        
        if self._dark_correction and (self._correct_dark_offset or self._correct_dark_slope):
            data = self.correct_dark(data)
        
        return data
    
    
    # Miscellaneous
    @Action()
    def reset_to_default(self):
        safe_call(self,
                  ueye.is_ResetToDefault,
                  self._handle)
    
    @Action()
    def read_configuration_file(self, config_path=None):
        if config_path is None:
            config_path = CONFIG_DEFAULT
        
        with open(config_path, 'r') as file:
            try:
                yaml = safe_load(file)
                yaml = yaml["driver"]
            except YAMLError as exc:
                print(exc)
        
        return yaml
    
    @Action()
    def save_configuration_file(self, config_path=None):
        if config_path is None:
            config_path = CONFIG_DEFAULT
        
        driver = {"color_mode": self.color_mode.name,
                  "display_mode": self.display_mode.name,
                  "shutter_mode": self.shutter_mode.name,
                  
                  "pixel_clock": self.pixel_clock.magnitude,
                  "frame_rate": self.frame_rate.magnitude,
                  "exposure": self.exposure.magnitude,
                  "blacklevel_mode": self.blacklevel_mode.value,
                  "blacklevel_offset": self.blacklevel_offset}
        
        # Try update file values if file exists
        try:
            yaml = self.read_configuration_file(config_path)
            yaml["driver"] = driver
            
            with open(config_path, 'w') as file:
                dump(yaml, file, default_flow_style=False)
        
        # If not, write new file
        except FileNotFoundError:
            yaml = {"driver": driver}
            
            with open(config_path, 'w') as file:
                dump(yaml, file, default_flow_style=False)
    
    @Action()
    def setup_from_file(self, config_path=None):
        
        def validate_value(self, yaml, name, type_, units=None):
            if isinstance(type_, EnumMeta):
                value = type_[yaml[name]]
            elif isinstance(type_, type):
                if isinstance(yaml[name], str):
                    if yaml[name].lower() == 'min':
                        value, _, _ = self.__getattribute__('get_' + name + '_range')()
                    elif yaml[name].lower() == 'max':
                        _, value, _ = self.__getattribute__('get_' + name + '_range')()
                    elif yaml[name].lower() == 'default':
                        value = self.__getattribute__('get_default_' + name)()
                    if type_ == str:
                        value = type_(yaml[name])
                        if units is not None:
                            value = value * units
                else:
                    value = type_(yaml[name])
                    if units is not None:
                        value = value * units
            
            return value
        
        config = self.read_configuration_file(config_path)
        
        self.display_mode = validate_value(self, config, 'display_mode', enums.DisplayMode)
        self.color_mode = validate_value(self, config, 'color_mode', enums.ImageColorMode)
        self.shutter_mode = validate_value(self, config, 'shutter_mode', enums.ShutterModes)
        
        self.pixel_clock = validate_value(self, config, 'pixel_clock', int, self.pixel_clock.units)
        self.frame_rate = validate_value(self, config, 'frame_rate', float, self.frame_rate.units)
        self.exposure = validate_value(self, config, 'exposure', float, self.exposure.units)
        
        self.blacklevel_mode = validate_value(self, config, 'blacklevel_mode', enums.BlacklevelModes)
        self.blacklevel_offset = validate_value(self, config, 'blacklevel_offset', int)
        
        dark_offset_base_pattern_path = validate_value(self, config, 'dark_offset_base_pattern_path', str)
        if dark_offset_base_pattern_path.lower() == "none":
            self.dark_offset_base_pattern = None
        else:
            self.dark_offset_base_pattern = np.load(dark_offset_base_pattern_path)
        
        dark_slope_base_pattern_path = validate_value(self, config, 'dark_slope_base_pattern_path', str)
        if dark_slope_base_pattern_path.lower() == "none":
            self.dark_slope_base_pattern_path = None
        else:
            self.dark_slope_base_pattern = np.load(dark_slope_base_pattern_path)
        
        self.dark_correction = validate_value(self, config, 'dark_correction', bool)
        











