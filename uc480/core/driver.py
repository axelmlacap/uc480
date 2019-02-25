# -*- coding: utf-8 -*-

from uc480.utilities.aoi import AOI2D
from uc480.utilities import enums
from uc480.utilities.func import safe_call, safe_get, safe_set, prop_to_int

import numpy as np

from pyueye import ueye

from lantz.core import Driver, ureg
from lantz import Feat, Action

import ctypes

#---------------------------------------------------------------------------------------------------------------------------------------

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
    if isinstance(value, str):
        try:
            timeout = enums.Timeout[value].value
        except KeyError:
            raise KeyError("Invalid wait timeout '{0:}'.".format(value))
    elif isinstance(value, int):
        if value in enums.Timeout.to_plain_dict().values():
            timeout = value
        elif value >= 4 and value <= 429496729:
            timeout = value
        else:
            raise ValueError('Wait timeout must be within 4 and 429496729 range (40 ms to approx. 1193 hs).')
    else:
        raise TypeError('Wait timeout must be int type within [4,429496729] range or a valid timeout mode (as string or integer).')
    
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
        
        print([rect.s32X.value, rect.s32Y.value, rect.s32Width.value, rect.s32Height.value])
        print(ueye.sizeof(rect))
        
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


class Camera(Driver):
    
    def __init__(self, handle = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.handle, self._handle = validate_handle(handle)
        
        self.initiate()
        self.sensor_info = SensorInfo(handle=self._handle)
        self.camera_info = CameraInfo(handle=self._handle)
        
        sensor_limits = [0, self.sensor_info.max_width, 0, self.sensor_info.max_height]
        self.aoi = CameraAOI(parent=self, limits=sensor_limits, canvas_limits=sensor_limits, units=ureg.px)
        
        self._mem_pointer = ueye.c_mem_p()
        self._mem_id = ueye.int()
    
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
    @Feat(units = 'bits')
    def bitdepth(self):
    
        sensor_color_mode = self.sensor_info.color_mode
        
        if enums.SensorColorMode[sensor_color_mode] == enums.SensorColorMode.IS_COLORMODE_BAYER:
            # setup the color depth to the current windows setting   
            bitdepth = ueye.INT()
            safe_call(self, ueye.is_GetColorDepth, self._handle, bitdepth, ueye.INT())
            return bitdepth.value
        
        elif enums.SensorColorMode[sensor_color_mode] == enums.SensorColorMode.IS_COLORMODE_CBYCRY:
            # for color camera models use RGB32 mode
            return 32
        
        elif enums.SensorColorMode[sensor_color_mode] == enums.SensorColorMode.IS_COLORMODE_MONOCHROME:
            # for monochrome camera models use Y8 mode
            return 8
        
        else:
            raise ValueError("Invalid sensor color mode '{0:}'".format(sensor_color_mode))
    
    @Feat(units = 'bytes')
    def bytedepth(self):
        return int(self.bitdepth/8)
    
    @Feat(values = enums.ImageColorMode.to_plain_dict(), units = None)
    def color_mode(self):
        return safe_get(self,
                        ueye.is_SetColorMode,
                        self._handle,
                        enums.ImageColorMode.IS_GET_COLOR_MODE.value)
    
    @color_mode.setter
    def color_mode(self, value):
        safe_set(self,
                 ueye.is_SetColorMode,
                 self._handle,
                 value)
    
    @Action()
    def get_auto_color_mode(self):
        
        sensor_color_mode = self.sensor_info.color_mode
        
        if enums.SensorColorMode[sensor_color_mode] == enums.SensorColorMode.IS_COLORMODE_BAYER:
            # setup the color depth to the current windows setting   
            bitdepth = ueye.INT()
            color_mode = ueye.INT()
            safe_call(self,
                      ueye.is_GetColorDepth,
                      self._handle,
                      bitdepth,
                      color_mode)
        
        elif enums.SensorColorMode[sensor_color_mode] == enums.SensorColorMode.IS_COLORMODE_CBYCRY:
            # for color camera models use RGB32 mode
            color_mode = enums.ImageColorMode.IS_CM_BGRA8_PACKED.value
        
        elif enums.SensorColorMode[sensor_color_mode] == enums.SensorColorMode.IS_COLORMODE_MONOCHROME:
            # for monochrome camera models use Y8 mode
            color_mode = enums.ImageColorMode.IS_CM_MONO8.value
        
        else:
            raise ValueError("Invalid sensor color mode '{0:}'".format(sensor_color_mode))
        
        return enums.ImageColorMode(color_mode).name
    
    @Action()
    def set_auto_color_mode(self):
        self.color_mode = self.get_auto_color_mode()
    
    # Memory:
    """
    
    Faltan implementar LockSeqBuf, UnlockSeqBuf, AddToSequence.
    
    """
    
    @Action()
    def allocate_memory(self, width = None, height = None):
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
    
        print(self)
        bitdepth = ueye.INT(self.bitdepth)
        
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
    
    #Configuration
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
            self.log_warning("Camera allows only discrete pixel clock values. Use 'get_allowed_pixel_clock' to obtain a list of allowed pixel clock values.")
        
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
                      ueye.sizeof(n_items))
            
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
        
        return pixel_clock.value * ureg.MHz
    
    
    @Feat(units = 'Hz')
    def frame_rate(self):        
        new_fps = ueye.c_double()
        
        safe_get(self,
                 ueye.is_GetFramesPerSecond, # Alternativa: ueye.is_SetFrameRate,
                 self._handle,
                 # Al usar la alternativa, agreagar aquí el parámetro: ueye.IS_GET_FRAMERATE,
                 new_fps)
        
        new_fps = new_fps.value * ureg.Hz
                
        return new_fps
    
    @frame_rate.setter
    def frame_rate(self, value):        
        # Smart users will provide a Pint Quantity.
        try:
            value = value.to('Hz').magnitude
        except:
            pass
                
        fps = ueye.c_double(value)
        new_fps = ueye.c_double()
        
        safe_set(self,
                 ueye.is_SetFrameRate,
                 self._handle,
                 fps,
                 new_fps)
        
        new_fps = new_fps.value * ureg.Hz
                
        return new_fps
    
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
        # Smart users will provide a Pint Quantity.
        try:
            value = value.to('ms').magnitude
        except:
            pass
                
        exposure = ueye.c_double(value)
        
        safe_set(self,
                 ueye.is_Exposure,
                 self._handle,
                 enums.Exposure.IS_EXPOSURE_CMD_SET_EXPOSURE.value,
                 exposure,
                 8)
            
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
    def capture_video(self, timeout):
        timeout = validate_timeout(timeout)
        safe_call(self,
                  ueye.is_CaptureVideo,
                  self._handle,
                  timeout)
    
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
    
    @Action()
    def get_frame(self):
        data = ueye.get_data(self._mem_pointer,
                             self.aoi[2],
                             self.aoi[3],
                             self.bitdepth,
                             self.aoi[2],
                             copy=False)
        
        return np.reshape(data, (int(self.aoi.height.magnitude), int(self.aoi.width.magnitude)))

    # Miscellaneous
    @Action()
    def reset_to_default(self):
        safe_call(self, ueye.is_ResetToDefault, self._handle)