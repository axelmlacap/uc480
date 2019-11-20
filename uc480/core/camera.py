# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 13:01:25 2019

@author: Axel Lacapmesure
"""

from .driver import Camera
from uc480.config import CONFIG_DEFAULT
from uc480.utilities import file_dialog_save
from uc480.utilities.save import SaveManager, PATH, DATA, TRIGGER_RETURN, INSTANCE_ATTRIBUTE, Numerations, StopConditions
from uc480.utilities.enums import ImageColorMode, ShutterModes, BlacklevelModes, EnumMixin

from lantz.qt.app import Backend, Frontend, InstrumentSlot, QtCore
from lantz.core import ureg

import numpy as np

from imageio import imwrite

from re import split

from enum import Enum, EnumMeta

from time import monotonic

from pyqtgraph import ImageView

from yaml import safe_load, YAMLError, dump

class CameraControl(Backend):
    
    camera: Camera = InstrumentSlot
    
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    new_data = QtCore.pyqtSignal(object)
    view = QtCore.pyqtSignal(object)
    
    aoi_changed = QtCore.pyqtSignal(object)
    
    class _outputs(Enum):
        FRAME = 'frame'
        DARK_PATTERN = 'dark_pattern'
        DARK_BASE_PATTERN = 'dark_base_pattern'
    
    ShutterModeNames = {ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING: "Rolling shutter",
                        ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL: "Global shutter",
                        ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START: "Rolling shutter, global start",
                        ShutterModes.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL_ALTERNATIVE_TIMING: "Global shutter, alt. timing"}
    
    BlacklevelModes = {False: BlacklevelModes.IS_AUTO_BLACKLEVEL_OFF,
                       True: BlacklevelModes.IS_AUTO_BLACKLEVEL_ON}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._last_frame = None
        self._averages = 1
        
        try:
            current_frame_interval = 1/self.camera.frame_rate
        except ZeroDivisionError:
            current_frame_interval = 0 * ureg.ms
        
        self.output = self._outputs.FRAME
        self.timer = QtCore.QTimer()
        self.timer.setInterval(current_frame_interval.to('ms').magnitude)
        self.timer.timeout.connect(self.acquire)
    
    @property
    def last_frame(self):
        return self._last_frame
    
    @property
    def output(self):
        return self._output
    
    @output.setter
    def output(self, value):
        if isinstance(value, str):
            value = self._outputs(value)
        elif isinstance(value, type(self._outputs.FRAME)):
            value = self._outputs[value.name]
        else:
            raise TypeError("Camera backend output stream must be either a string with a valid output name or a valid output enum object.")
        
        self._output = value
    
    def send_output(self, value, output_channel):
        if self.output == output_channel:
            self.new_data.emit(value)
    
    @property
    def averages(self):
        return self._averages
    
    @averages.setter
    def averages(self, value):
        value = int(value)
        
        if value < 1:
            raise ValueError("Number of frames to average {} is less than minimum value of 1.".format(value))
        
        if self.timer.isActive():
            self.timer.stop()
            reinitialize = True
        else:
            reinitialize = False
        
        self._averages = value
        
        if reinitialize:
            self.timer.start()
        
    def acquire(self):
        try:
            if self.averages > 1:
                image = self.camera.get_frame() / self.averages
                
                for idx in range(self.averages-1):
                    image += self.camera.get_frame() / self.averages
            else:
                image = self.camera.get_frame()
            
            self._last_frame = image
            self.send_output(image, self._outputs.FRAME)
        
        except KeyboardInterrupt:
            self.start_stop(False)
    
    def start_stop(self, value):
        if value:
            self.camera.start_video_capture()
            self.timer.start()
            self.started.emit()
            self.log_debug('Camera viewer started')
        else:
            self.camera.stop_video_capture()
            self.timer.stop()
            self.stopped.emit()
            self.log_debug('Camera viewer stopped')
    
    def set_pixel_clock(self, value):
        self.camera.pixel_clock = value
        
        return self.camera.pixel_clock
    
    def get_frame_rate(self):
        return self.camera.frame_rate
    
    def set_frame_rate(self, value):
        self.camera.frame_rate = value
        current_frame_rate = self.camera.frame_rate
        interval = int((1/current_frame_rate).to('ms').magnitude)
        
        self.timer.setInterval(interval)
        
        return current_frame_rate
    
    def set_exposure(self, value):
        self.camera.exposure = value
        
        return self.camera.exposure
    
    def get_pixel_clock_list(self):
        return self.camera.get_pixel_clock_list()
    
    def get_frame_rate_list(self):
        return self.camera.get_frame_rate_list()
    
    def get_exposure_list(self):
        return self.camera.get_exposure_list()
    
    def set_aoi(self, limits):
        self.camera.aoi.limits = limits
        self.camera.aoi.write_to_camera()
        
        self.aoi_changed.emit(self.camera.aoi.limits)
    
    def reset_aoi(self):
        self.camera.aoi.reset_limits()
        self.camera.aoi.write_to_camera()
        
        self.aoi_changed.emit(self.camera.aoi.limits)
    
    def get_aoi(self):
        self.camera.aoi.sync_with_camera()
        
        self.aoi_changed.emit(self.camera.aoi.limits)
        return self.camera.aoi.limits
    
    def get_bit_depth(self):
        bits_per_pixel = self.camera.bits_per_pixel
        
        if bits_per_pixel == 8:
            bit_depth = 8
        else:
            bit_depth = 10
        
        return bit_depth
    
    def set_bit_depth(self, value):
        if value == 8:
            color_mode = ImageColorMode.IS_CM_MONO8
        elif value == 10:
            color_mode = ImageColorMode.IS_CM_MONO10
        else:
            raise ValueError("Invalid bit depth value")
        
        self.camera.color_mode = color_mode
    
    def get_shutter_mode(self):
        return self.camera.shutter_mode
    
    def set_shutter_mode(self, value):
        self.camera.shutter_mode = value
        
        return self.camera.shutter_mode
    
    def get_shutter_modes_list(self):
        return self.camera.get_shutter_modes_list()
    
    def get_dtype(self):
        return self.camera.dtype
    
    def get_blacklevel_mode(self):
        return self.camera.blacklevel_mode
    
    def set_blacklevel_mode(self, value):
        self.camera.blacklevel_mode = value
        
        return self.camera.blacklevel_mode
    
    def get_blacklevel_offset(self):
        return self.camera.blacklevel_offset
    
    def set_blacklevel_offset(self, value):
        self.camera.blacklevel_offset = value
        
        return self.camera.blacklevel_offset
    
    def get_blacklevel_offset_list(self):
        return self.camera.get_blacklevel_offset_list()
    
    def set_dark_correction(self, value):
        self.camera.dark_correction = value
    
    def get_dark_correction(self):
        return self.camera.dark_correction
    
    def get_dark_pattern(self):
        self.send_output(self.camera.dark_pattern, self._outputs.DARK_PATTERN)
        
        return self.camera.dark_pattern
    
    def get_dark_base_pattern(self):
        self.send_output(self.camera.dark_base_pattern, self._outputs.DARK_BASE_PATTERN)
        
        return self.camera.dark_base_pattern
    
    def reset_dark_pattern(self):
        self.camera.reset_dark_pattern()
        
        self.send_output(self.camera.dark_pattern, self._outputs.DARK_PATTERN)
        self.send_output(self.camera.dark_base_pattern, self._outputs.DARK_BASE_PATTERN)
    
    def update_dark_pattern(self):
        self.camera.update_dark_pattern()
        
        self.send_output(self.camera.dark_pattern, self._outputs.DARK_PATTERN)
        self.send_output(self.camera.dark_base_pattern, self._outputs.DARK_BASE_PATTERN)


class CameraControlUi(Frontend):
    
    backend: CameraControl
    
    gui = 'gui/camera_control.ui'
    
    pixel_clock_units = ureg.MHz
    frame_rate_units = ureg.Hz
    exposure_units = ureg.ms
    
    pixel_clock_sg = QtCore.pyqtSignal()
    frame_rate_sg = QtCore.pyqtSignal()
    exposure_sg = QtCore.pyqtSignal()
    bit_depth_sg = QtCore.pyqtSignal()
    shutter_mode_sg = QtCore.pyqtSignal()
    blacklevel_mode_sg = QtCore.pyqtSignal()
    blacklevel_offset_sg = QtCore.pyqtSignal()
    dark_correction_sg = QtCore.pyqtSignal()
    dark_reset_sg = QtCore.pyqtSignal()
    
    def setupUi(self):
        super().setupUi()
        
        self.pixel_clock_list = np.array([]) * self.pixel_clock_units
        self.frame_rate_list = np.array([]) * self.frame_rate_units
        self.exposure_list = np.array([]) * self.exposure_units
        self.shutter_modes_list = []
        self.blacklevel_offset_list = np.array([])
    
    def connect_backend(self):
        super().connect_backend()
        
        # Default values
        self.read_bit_depth()
        self.refresh_pixel_clock_list()
        self.refresh_frame_rate_list()
        self.refresh_exposure_list()
        self.refresh_shutter_modes_list()
        self.refresh_blacklevel_offset_list()
        self.read_blacklevel_mode()
        self.read_dark_correction()
        
        # Widget connections
        self.widget.run_checkbox.stateChanged.connect(lambda new_value: self.backend.start_stop(new_value == 2))
        self.widget.view_checkbox.toggled.connect(self.send_view)
        
        self.widget.bitdepth_buttongroup.buttonClicked.connect(self.send_bit_depth)
        self.widget.exp_slider.valueChanged.connect(self.new_exposure_by_slider)
        self.widget.exp_text.editingFinished.connect(self.new_exposure_by_text)
        self.widget.fps_slider.valueChanged.connect(self.new_frame_rate_by_slider)
        self.widget.fps_text.editingFinished.connect(self.new_frame_rate_by_text)
        self.widget.clk_combo.currentIndexChanged.connect(self.new_pixel_clock)
        self.widget.shutter_combo.currentIndexChanged.connect(self.send_shutter_mode)
        self.widget.blmode_checkbox.clicked.connect(self.send_blacklevel_mode)
        self.widget.bloffset_slider.valueChanged.connect(self.send_blacklevel_offset_by_slider)
        self.widget.bloffset_text.editingFinished.connect(self.send_blacklevel_offset_by_text)
        self.widget.dark_checkbox.clicked.connect(self.send_dark_correction)
        self.widget.dark_reset.clicked.connect(self.send_dark_reset)
        self.widget.dark_view.clicked.connect(self.view_dark)
        
        # Signal connections
        self.bit_depth_sg.connect(self.refresh_pixel_clock_list)
        self.bit_depth_sg.connect(self.refresh_frame_rate_list)
        self.bit_depth_sg.connect(self.refresh_exposure_list)
        
        self.pixel_clock_sg.connect(self.refresh_frame_rate_list)
        self.shutter_mode_sg.connect(self.refresh_frame_rate_list)
        self.shutter_mode_sg.connect(self.refresh_blacklevel_offset_list)
        self.frame_rate_sg.connect(self.refresh_exposure_list)
        self.blacklevel_mode_sg.connect(self.refresh_blacklevel_offset_list)
        
        self.widget.aoi_set.clicked.connect(self.new_aoi)
        self.widget.aoi_reset.clicked.connect(self.backend.reset_aoi)
        self.backend.aoi_changed.connect(self.read_aoi)
        
        self.exposure_sg.connect(self.backend.update_dark_pattern)
    
    def closeEvent(self, event):
        self.backend.timer.stop()
        event.accept()
    
    def send_view(self):
        if self.widget.view_checkbox.isChecked():
            self.backend.view.emit(True)
        else:
            self.backend.view.emit(False)
    
    def new_pixel_clock(self, new_combo_index):
        new_pixel_clock = self.pixel_clock_list[new_combo_index]
        self.backend.set_pixel_clock(new_pixel_clock)
        
        self.pixel_clock_sg.emit()
    
    def refresh_pixel_clock_list(self):
        self.pixel_clock_list = self.backend.get_pixel_clock_list()
        
        # Disconnect signal to prevent index changes during item deletion to
        # fire new signals
        try:
            self.widget.clk_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass
        
        # Update values
        for idx in range(self.widget.clk_combo.count()):
            self.widget.clk_combo.removeItem(0)
        
        for value in self.pixel_clock_list:
            self.widget.clk_combo.addItem("{:~}".format(value), value)
        
        # Reconnect signal
        self.widget.clk_combo.currentIndexChanged.connect(self.new_pixel_clock)
        
        current_pixel_clock = self.backend.camera.pixel_clock
        current_index = np.argwhere(self.pixel_clock_list==current_pixel_clock).flatten()[0]
        self.widget.clk_combo.setCurrentIndex(current_index)
    
    def new_frame_rate_by_slider(self, new_slider_value):
        new_frame_rate = self.frame_rate_list[new_slider_value]
        self.backend.set_frame_rate(new_frame_rate)
        self.widget.fps_text.setText("{:0.4g}".format(new_frame_rate.to(self.frame_rate_units).magnitude))
        
        self.frame_rate_sg.emit()
    
    def new_frame_rate_by_text(self):
        new_value = float(self.widget.fps_text.text()) * self.frame_rate_units
        
        # Find nearest allowed frame rate and sets it
        new_index = np.argmin(np.abs(self.frame_rate_list - new_value))
        new_frame_rate = self.frame_rate_list[new_index]
        new_frame_rate = self.backend.set_frame_rate(new_frame_rate)
        self.widget.fps_text.setText("{:0.4g}".format(new_frame_rate.to(self.frame_rate_units).magnitude))
        self.widget.fps_slider.setValue(new_index)
        
        self.frame_rate_sg.emit()
    
    def refresh_frame_rate_list(self):
        self.frame_rate_list = self.backend.get_frame_rate_list()
        
        current_frame_rate = self.backend.camera.frame_rate
        current_index = np.argmin(np.abs(self.frame_rate_list - current_frame_rate))
        
        self.widget.fps_text.setText("{:0.4g}".format(current_frame_rate.to(self.frame_rate_units).magnitude))
        self.widget.fps_slider.setMinimum(0)
        self.widget.fps_slider.setMaximum(len(self.frame_rate_list) - 1)
        self.widget.fps_slider.setValue(current_index)
    
    def new_exposure_by_slider(self, new_slider_value):
        new_exposure = self.exposure_list[new_slider_value]
        new_exposure = self.backend.set_exposure(new_exposure)
        self.widget.exp_text.setText("{:0.4g}".format(new_exposure.to(self.exposure_units).magnitude))
        
        self.exposure_sg.emit()
    
    def new_exposure_by_text(self):
        new_value = float(self.widget.exp_text.text()) * self.exposure_units
        
        # Find nearest allowed frame rate and sets it
        new_index = np.argmin(np.abs(self.exposure_list - new_value))
        new_exposure = self.exposure_list[new_index]
        new_exposure = self.backend.set_exposure(new_exposure)
        self.widget.exp_text.setText("{:0.4g}".format(new_exposure.to(self.exposure_units).magnitude))
        self.widget.exp_slider.setValue(new_index)
        
        self.exposure_sg.emit()
    
    def refresh_exposure_list(self):
        self.exposure_list = self.backend.get_exposure_list()
        
        current_exposure = self.backend.camera.exposure
        current_index = np.argmin(np.abs(self.exposure_list-current_exposure))
        
        self.widget.exp_text.setText("{:0.4g}".format(current_exposure.to(self.exposure_units).magnitude))
        self.widget.exp_slider.setMinimum(0)
        self.widget.exp_slider.setMaximum(len(self.exposure_list) - 1)
        self.widget.exp_slider.setValue(current_index)
    
    def read_bit_depth(self, value=None):
        if value == None:
            value = self.backend.get_bit_depth()
        
        if value == 8:
            self.widget.bit8_radio.setChecked(True)
            self.widget.bit10_radio.setChecked(False)
        elif value == 10:
            self.widget.bit8_radio.setChecked(False)
            self.widget.bit10_radio.setChecked(True)
        else:
            self.log_error("Invalid bit depth value '{}'.".format(value))
    
    def send_bit_depth(self, button=None):
        if self.widget.bit8_radio.isChecked():
            bit_depth = 8
        elif self.widget.bit10_radio.isChecked():
            bit_depth = 10
        
        if self.backend.get_bit_depth() != bit_depth:
            self.backend.set_bit_depth(bit_depth)
            self.bit_depth_sg.emit()
    
    def send_shutter_mode(self, new_combo_index):
        new_shutter_mode = self.shutter_modes_list[new_combo_index]
        self.backend.set_shutter_mode(new_shutter_mode)
        
        self.shutter_mode_sg.emit()
    
    def read_shutter_mode(self, new_shutter_mode=None):
        if new_shutter_mode == None:
            new_shutter_mode = self.backend.get_shutter_mode()
        
        new_combo_index = self.shutter_modes_list.index(new_shutter_mode)
        
        self.widget.shutter_combo.setCurrentIndex(new_combo_index)
    
    def refresh_shutter_modes_list(self):
        self.shutter_modes_list = self.backend.get_shutter_modes_list()
        
        for idx in range(self.widget.shutter_combo.count()):
            self.widget.shutter_combo.removeItem(0)
        
        for value in self.shutter_modes_list:
            self.widget.shutter_combo.addItem("{}".format(self.backend.ShutterModeNames[value]), value.value)
        
        current_shutter_mode = self.backend.get_shutter_mode()
        self.read_shutter_mode(current_shutter_mode)
    
    def send_blacklevel_mode(self):
        mode = self.backend.BlacklevelModes[self.widget.blmode_checkbox.isChecked()]
        self.backend.set_blacklevel_mode(mode)
        
        self.blacklevel_mode_sg.emit()
    
    def read_blacklevel_mode(self, value=None):
        if value == None:
            value = self.backend.get_blacklevel_mode()
        
        if value == BlacklevelModes.IS_AUTO_BLACKLEVEL_OFF:
            mode = False
        elif value == BlacklevelModes.IS_AUTO_BLACKLEVEL_ON:
            mode = True
        else:
            raise ValueError("Cannot undesrtand blacklevel mode value '{}'.".format(value))
        
        self.widget.blmode_checkbox.setChecked(mode)
    
    def send_blacklevel_offset_by_slider(self, new_slider_value):
        new_offset = self.blacklevel_offset_list[new_slider_value]
        new_offset = self.backend.set_blacklevel_offset(new_offset)
        self.widget.bloffset_text.setText("{:0.4g}".format(new_offset))
        
        self.blacklevel_offset_sg.emit()
    
    def send_blacklevel_offset_by_text(self):
        new_value = float(self.widget.bloffset_text.text())
        
        # Find nearest allowed frame rate and sets it
        new_index = np.argmin(np.abs(self.blacklevel_offset_list - new_value))
        new_offset = self.blacklevel_offset_list[new_index]
        new_offset = self.backend.set_blacklevel_offset(new_offset)
        self.widget.bloffset_text.setText("{:0.4g}".format(new_offset))
        self.widget.bloffset_slider.setValue(new_index)
        
        self.blacklevel_offset_sg.emit()
    
    def read_blacklevel_offset(self, value=None):
        if value == None:
            value = self.backend.get_blacklevel_offset()
        
        new_index = np.argmin(np.abs(self.blacklevel_offset_list - value))
        self.widget.bloffset_text.setText("{:0.4g}".format(value))
        self.widget.bloffset_slider.setValue(new_index)
    
    def refresh_blacklevel_offset_list(self):
        self.blacklevel_offset_list = self.backend.get_blacklevel_offset_list()
        
        current_offset = self.backend.camera.blacklevel_offset
        self.widget.bloffset_text.setText("{:0.4g}".format(current_offset))
        self.widget.bloffset_slider.setMinimum(0)
        self.widget.bloffset_slider.setMaximum(len(self.blacklevel_offset_list) - 1)
        
        self.read_blacklevel_offset(current_offset)
        self.read_blacklevel_mode()
    
    def new_aoi(self, checked=False):
        aoi_text = self.widget.aoi_text.text()
        aoi_limits = [float(lim) for lim in split("\[|,|\]", aoi_text) if lim != ""]
        self.backend.set_aoi(aoi_limits)
    
    def read_aoi(self, value):
        value = [int(x) for x in value.to(ureg.px).magnitude]
        value = str(value).replace(' ','')
        
        self.widget.aoi_text.setText(value)
        self.refresh_exposure_list()
        self.refresh_frame_rate_list()
    
    def read_dark_correction(self, value=None):
        if isinstance(value, type(None)):
            value = self.backend.get_dark_correction()
        
        self.widget.dark_checkbox.setChecked(value)
    
    def send_dark_correction(self):
        self.backend.set_dark_correction(self.widget.dark_checkbox.isChecked())
        
        self.dark_correction_sg.emit()
    
    def send_dark_reset(self):
        self.backend.reset_dark_pattern(None)
        
        self.dark_reset_sg.emit()
    
    def view_dark(self):
        if self.widget.dark_view.isChecked():
            self.backend.output = self.backend._outputs.DARK_PATTERN
            self.backend.get_dark_pattern()
        else:
            self.backend.output = self.backend._outputs.FRAME


class CameraSave(SaveManager, Backend):
    
    class _modes(Enum):
        NPY = 'numpy binary'
        TIFF = 'tiff'
        IMAGE = "image"
        TXT = 'plain text'
    
    class _formats(Enum):
        INTEGER = "%0.1i"
        FLOAT = "%.12e"
    
    DELIMITER = "\t"
    
    def __init__(self, camera_control_be: CameraControl, mode="numpy binary"):
        
        self.camera_control_be = camera_control_be
        self.mode = mode
        
        super().__init__(self.callback,
                         self.camera_control_be.new_data,
                         stop_condition=StopConditions.COUNT,
                         limit=1,
                         packet_length=1,
                         append='timestamp',
                         single_file=False)
        
        self.callback_args = (PATH(), DATA())
    
    @property
    def mode(self):
        return self._mode
    
    @mode.setter
    def mode(self, value):
        if isinstance(value, str):
            value = self._modes(value)
        elif isinstance(value, type(self._modes)):
            value = self._modes[value.name]
        else:
            raise TypeError("Camera save mode must be either a string with a valid mode name or a valid mode enum object.")
        
        self._mode = value
        
        if value == self._modes.TXT:
            self.callback = self.save_txt
        elif value == self._modes.NPY:
            self.callback = self.save_npy
        elif value == self._modes.TIFF:
            self.callback = self.save_tiff
        elif value == self._modes.IMAGE:
            self.callback = self.save_image
    
    def initialize_buffer(self):
        if isinstance(self.camera_control_be.last_frame, type(None)):
            dtype = self.camera_control_be.get_dtype()
            aoi = self.camera_control_be.get_aoi()
            width = (aoi[1]-aoi[2]).magnitude
            height = (aoi[4]-aoi[3]).magnitude
            
            init_object = np.zeros((height, width), dtype=dtype)
        else:
            init_object = self.camera_control_be.last_frame
        
        self.buffer.init_object = init_object
    
    def save_txt(self, path, data):
        if np.issubdtype(data.dtype, np.integer):
            fmt = self._formats.INTEGER.value
        elif np.issubdtype(data.dtype, np.floating):
            fmt = self._formats.FLOAT.value

        np.savetxt(path, data, fmt=fmt, delimiter=self.DELIMITER)
    
    def save_npy(self, path, data):
        np.save(path, data)
        
    def save_image(self, path, data):
        imwrite(path, data)
    
    def save_tiff(self, path, data):
        raise NotImplementedError("Cannot save in TIFF format.")


class CameraSaveUi(Frontend):
    backend: CameraSave
    
    gui = 'gui/camera_save.ui'
    
    def setupUi(self):
        super().setupUi()
        
        # Connections
        self.widget.title_label.setText("Camera save")
        self.widget.enable.clicked.connect(self.send_enable)
        
        self.widget.count_radio.toggled.connect(self.refresh_stop_condition)
        self.widget.time_radio.toggled.connect(self.refresh_stop_condition)
        self.widget.count_text.editingFinished.connect(self.refresh_append)
        self.widget.time_text.editingFinished.connect(self.refresh_append)
      
        self.widget.count.toggled.connect(self.refresh_append)
        self.widget.timestamp.toggled.connect(self.refresh_append)
        
        self.widget.save_to.clicked.connect(self.file_dialog_save)
    
    def connect_backend(self):
        super().connect_backend()
        
        self.backend.added.connect(self.read_added)
        self.backend.saved.connect(self.read_saved)
        self.backend.started.connect(self.read_started)
        self.backend.stopped.connect(self.read_stopped)
        
        self.backend.stop_condition_set.connect(self.read_stop_condition)
        self.backend.limit_set.connect(self.read_limit)
        self.backend.append_set.connect(self.read_append)
        self.backend.base_path_set.connect(self.read_path)
        
        self.read_callback(self.backend.callback)
        self.read_trigger(self.backend.trigger)
        
        for mode in self.backend._modes:
            self.widget.mode_combo.addItem(mode.value.capitalize())
        self.read_mode()
    
    def configure_backend(self):
        self.send_mode()
        self.backend.initialize_buffer()
        self.send_stop_condition()
        self.send_limit()
        self.send_append()
        self.send_save_every()
        self.send_path()
    
    def send_enable(self):
        if self.widget.enable.isChecked():
            self.configure_backend()
            self.backend.start()
        else:
            self.backend.stop()
    
    def refresh_stop_condition(self):
        if self.widget.count_radio.isChecked():
            self.widget.count_text.setEnabled(True)
            self.widget.time_text.setDisabled(True)
        elif self.widget.time_radio.isChecked():
            self.widget.count_text.setDisabled(True)
            self.widget.time_text.setEnabled(True)
    
    def send_stop_condition(self):
        if self.widget.count_radio.isChecked():
            value = StopConditions.COUNT
        elif self.widget.time_radio.isChecked():
            value = StopConditions.TIME
        self.backend.stop_condition = value
    
    def read_stop_condition(self, value):
        if value == StopConditions.COUNT:
            self.widget.count_text.setEnabled(True)
            self.widget.time_text.setDisabled(True)
        elif value == StopConditions.TIME:
            self.widget.count_text.setDisabled(True)
            self.widget.time_text.setEnabled(True)
    
    def send_limit(self):
        if self.widget.count_radio.isChecked():
            value = int(self.widget.count_text.text())
            self.backend.limit = value
            self.backend.packet_length = value
        elif self.widget.time_radio.isChecked():
            value = ureg.Quantity(self.widget.time_text.text())
            estimated_frames = (value * self.backend.camera_control_be.get_frame_rate()).magnitude
            
            self.backend.limit = value
            self.backend.packet_length = int(2*estimated_frames)
    
    def read_limit(self, value):
        if self.backend.stop_condition == StopConditions.COUNT:
            self.widget.count_text.setText(str(value))
        elif self.backend.stop_condition == StopConditions.TIME:
            # noinspection PyStringFormat
            self.widget.time_text.setText("{:~}".format(value))
    
    def refresh_append(self):
        value = []
        
        if self.widget.count.isChecked():
            value.append('count')
        if self.widget.timestamp.isChecked():
            value.append('timestamp')
        
        if not value:
            if (self.widget.count_radio.isChecked() and int(self.widget.count_text.text()) > 1) or self.widget.time_radio.isChecked():
                if self.widget.count.isChecked():
                    self.widget.count.setChecked(True)
                elif self.widget.timestamp.isChecked():
                    self.widget.timestamp.setChecked(True)
    
    def send_append(self):
        value = []
        
        if self.widget.count.isChecked():
            value.append('count')
        if self.widget.timestamp.isChecked():
            value.append('timestamp')
        if not self.widget.timestamp.isChecked() and not self.widget.count.isChecked():
            value.append('none')
        
        self.backend.append = value
    
    def read_append(self, value):
        if Numerations.COUNT & value:
            self.widget.count.setChecked(True)
        else:
            self.widget.count.setChecked(False)
        
        if Numerations.TIMESTAMP & value:
            self.widget.timestamp.setChecked(True)
        else:
            self.widget.timestamp.setChecked(False)
    
    def send_save_every(self):
        value = int(self.widget.save_every_text.text())
        self.backend.save_every = value
    
    def read_save_every(self, value):
        self.widget.save_every_text.setText(str(value))
    
    def send_mode(self):
        value = self.widget.mode_combo.currentText().lower()
        self.backend.mode = value
    
    def read_mode(self, value=None):
        if isinstance(value, type(None)):
            value = self.backend.mode.value
        
        self.widget.mode_combo.setCurrentText(value.capitalize())
    
    def file_dialog_save(self, title="Guardar archivo", initial_dir="/", filetypes=[("Text files","*.txt")]):
        path = file_dialog_save(title=title, initial_dir=initial_dir, filetypes=filetypes)
        
        self.widget.path_text.setPlainText(path)
    
    def send_path(self):
        if not self.widget.path_text.toPlainText():
            self.file_dialog_save()
        
        self.backend.path = self.widget.path_text.toPlainText()
    
    def read_path(self, value):
        self.widget.path_text.setPlainText(value)
    
    def read_callback(self, value):
        try:
            self.widget.callback.setText("Callback: {}".format(value.__name__))
        except AttributeError:
            self.widget.callback.setText("Callback: {}".format(value))
    
    def read_trigger(self, value):
        try:
            self.widget.trigger.setText("Trigger: {}".format(value.__name__))
        except AttributeError:
            self.widget.trigger.setText("Trigger: {}".format(value))
    
    def read_added(self, count, time):
        if self.widget.count_radio.isChecked():
            text = "Acquired frame {} of {}.".format(count, self.backend.limit)
        elif self.widget.time_radio.isChecked():
            # noinspection PyStringFormat,PyStringFormat
            text = "Acquired frame at {:~} of total {:~}.".format(time, self.backend.limit)
        
        self.widget.monitor.setText(text)
    
    def read_saved(self, path, count, time):
        if self.widget.count_radio.isChecked():
            text = "Saved file {} of {}.".format(count, self.backend.limit)
        elif self.widget.time_radio.isChecked():
            # noinspection PyStringFormat,PyStringFormat
            text = "Saved file at {:~} of total {:~}.".format(time, self.backend.limit)
        
        self.widget.monitor.setText(text)
    
    def read_started(self):
        self.widget.monitor.setText("Started.")
    
    def read_stopped(self):
        self.widget.enable.setCheckState(0)
        self.widget.monitor.setText("Waiting for start.")
    

class ImageViewerUi(Frontend):
    
    backend: CameraControl
    
    gui = 'gui/image_viewer.ui'
    
    def setupUi(self):
        super().setupUi()
        
        self.widget = ImageView(parent=self)
        self.setCentralWidget(self.widget)
        
        self.widget.getView().setAspectLocked(True) # Fixed aspect ratio
        self.widget.getView().invertY(False) # Positions axis origin at top-left corner
        self.widget.getView().setBackgroundColor(color=(20,20,20))
        
        self.img = self.widget.getImageItem()
        self.img.setOpts(axisOrder='row-major') # Pixels follow row-column order as y-x
    
    def connect_backend(self):
        super().connect_backend()
        
        self.backend.view.connect(self.read_enable)
    
    def read_enable(self, value):
        if value:
            self.backend.new_data.connect(self.refresh)
        else:
            self.backend.new_data.disconnect(self.refresh)
    
    def refresh(self, data, timestamp=None):
        bit_depth = self.backend.get_bit_depth()
        if bit_depth == 8:
            levels = (0,255)
        elif bit_depth == 10:
            levels = (0,1023)
        else:
            raise ValueError("Bit depth value {} is not supported.".format(bit_depth))
        self.img.setImage(data,
                          autoLevels = False,
                          levels = levels)