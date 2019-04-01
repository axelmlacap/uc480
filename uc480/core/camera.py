# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 13:01:25 2019

@author: Axel Lacapmesure
"""

from .driver import Camera
from uc480.utilities import file_dialog_save
from uc480.utilities.save import SaveManager, PATH, TRIGGER_RETURN, INSTANCE_ATTRIBUTE

from lantz.qt.app import Backend, Frontend, InstrumentSlot, QtCore
from lantz.core import ureg

import numpy as np

from scipy.misc import imsave

from re import split

from enum import Enum

from time import monotonic

from pyqtgraph import ImageView

class CameraControl(Backend):
    
    camera: Camera = InstrumentSlot
    
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    new_data = QtCore.pyqtSignal(object, object)
    
    aoi_changed = QtCore.pyqtSignal(object)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._averages = 1
        
        try:
            current_frame_interval = 1/self.camera.frame_rate
        except ZeroDivisionError:
            current_frame_interval = 0 * ureg.ms
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(current_frame_interval.to('ms').magnitude)
        self.timer.timeout.connect(self.acquire)
    
    @property
    def averages(self):
        return self._averages
    
    @averages.setter
    def averages(self, value):
        value = int(value)
        
        if value < 1:
            raise ValueError("Number of frames to average {} is less than minimum value of 1.".format(value))
        
        print('Averages set to {}'.format(value))
        
        if self.timer.isActive():
            self.timer.stop()
            reinitialize = True
        else:
            reinitialize = False
        
        self._averages = value
        
        if reinitialize:
            self.timer.start()
        
    def acquire(self):
        now = monotonic() * ureg.ms
        
        if self.averages > 1:
            image = self.camera.get_frame() / self.averages
            
            for idx in range(self.averages-1):
                image += self.camera.get_frame() / self.averages
        else:
            image = self.camera.get_frame()
        
        self.new_data.emit(image, now)
    
    def start_stop(self, value):
        if value:
            self.timer.start()
            self.started.emit()
            self.log_debug('Camera viewer started')
        else:
            self.timer.stop()
            self.stopped.emit()
            self.log_debug('Camera viewer stopped')
    
    def set_pixel_clock(self, value):
        self.camera.pixel_clock = value
        
        return self.camera.pixel_clock
    
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


class CameraControlUi(Frontend):
    
    backend: CameraControl
    
    gui = 'gui/camera_control.ui'
    
    pixel_clock_units = ureg.MHz
    frame_rate_units = ureg.Hz
    exposure_units = ureg.ms
    
    pixel_clock_changed = QtCore.pyqtSignal()
    frame_rate_changed = QtCore.pyqtSignal()
    exposure_changed = QtCore.pyqtSignal()
    
    def setupUi(self):
        super().setupUi()
        
        self.pixel_clock_list = np.array([]) * self.pixel_clock_units
        self.frame_rate_list = np.array([]) * self.frame_rate_units
        self.exposure_list = np.array([]) * self.exposure_units
    
    def connect_backend(self):
        super().connect_backend()
        
        self.refresh_pixel_clock_list()
        self.refresh_frame_rate_list()
        self.refresh_exposure_list()
        
        self.widget.run_checkbox.stateChanged.connect(lambda new_value: self.backend.start_stop(new_value == 2))
        
        self.widget.exp_slider.valueChanged.connect(self.new_exposure_by_slider)
        self.widget.exp_text.editingFinished.connect(self.new_exposure_by_text)
        self.widget.fps_slider.valueChanged.connect(self.new_frame_rate_by_slider)
        self.widget.fps_text.editingFinished.connect(self.new_frame_rate_by_text)
        self.widget.clk_combo.currentIndexChanged.connect(self.new_pixel_clock)
        
        self.pixel_clock_changed.connect(self.refresh_frame_rate_list)
        self.pixel_clock_changed.connect(self.refresh_exposure_list)
        self.frame_rate_changed.connect(self.refresh_exposure_list)
        self.exposure_changed.connect(self.refresh_frame_rate_list)
        
        self.widget.aoi_set.clicked.connect(self.new_aoi)
        self.widget.aoi_reset.clicked.connect(self.backend.reset_aoi)
        self.widget.aoi_sync.clicked.connect(self.backend.get_aoi)
        self.backend.aoi_changed.connect(self.read_aoi)
    
    def refresh_pixel_clock_list(self):
        self.pixel_clock_list = self.backend.get_pixel_clock_list()
        
        for idx in range(self.widget.clk_combo.count()):
            self.widget.clk_combo.removeItem(0)
        
        for value in self.pixel_clock_list:
            self.widget.clk_combo.addItem("{:~}".format(value), value)
        
        current_pixel_clock = self.backend.camera.pixel_clock
        current_index = np.argwhere(self.pixel_clock_list==current_pixel_clock).flatten()[0]
        self.widget.clk_combo.setCurrentIndex(current_index)
    
    def refresh_frame_rate_list(self):
        self.frame_rate_list = self.backend.get_frame_rate_list()
        
        current_frame_rate = self.backend.camera.frame_rate
        current_index = np.argmin(np.abs(self.frame_rate_list - current_frame_rate))
        
        self.widget.fps_text.setText("{:0.4g}".format(current_frame_rate.to(self.frame_rate_units).magnitude))
        self.widget.fps_slider.setMinimum(0)
        self.widget.fps_slider.setMaximum(len(self.frame_rate_list) - 1)
        self.widget.fps_slider.setValue(current_index)

    def refresh_exposure_list(self):
        self.exposure_list = self.backend.get_exposure_list()
        
        current_exposure = self.backend.camera.exposure
        current_index = np.argmin(np.abs(self.exposure_list-current_exposure))
        
        self.widget.exp_text.setText("{:0.4g}".format(current_exposure.to(self.exposure_units).magnitude))
        self.widget.exp_slider.setMinimum(0)
        self.widget.exp_slider.setMaximum(len(self.exposure_list) - 1)
        self.widget.exp_slider.setValue(current_index)
    
    def new_pixel_clock(self, new_combo_index):
        new_pixel_clock = self.pixel_clock_list[new_combo_index]
        self.backend.set_pixel_clock(new_pixel_clock)
        
        self.pixel_clock_changed.emit()
    
    def new_frame_rate_by_slider(self, new_slider_value):
        new_frame_rate = self.frame_rate_list[new_slider_value]
        self.backend.set_frame_rate(new_frame_rate)
        self.widget.fps_text.setText("{:0.4g}".format(new_frame_rate.to(self.frame_rate_units).magnitude))
        
        self.frame_rate_changed.emit()
    
    def new_frame_rate_by_text(self):
        new_value = float(self.widget.fps_text.text()) * self.frame_rate_units
        
        # Find nearest allowed frame rate and sets it
        new_index = np.argmin(np.abs(self.frame_rate_list - new_value))
        new_frame_rate = self.frame_rate_list[new_index]
        new_frame_rate = self.backend.set_frame_rate(new_frame_rate)
        self.widget.fps_text.setText("{:0.4g}".format(new_frame_rate.to(self.frame_rate_units).magnitude))
        self.widget.fps_slider.setValue(new_index)
        
        self.frame_rate_changed.emit()
    
    def new_exposure_by_slider(self, new_slider_value):
        new_exposure = self.exposure_list[new_slider_value]
        new_exposure = self.backend.set_exposure(new_exposure)
        self.widget.exp_text.setText("{:0.4g}".format(new_exposure.to(self.exposure_units).magnitude))
        
        self.exposure_changed.emit()
    
    def new_exposure_by_text(self):
        new_value = float(self.widget.exp_text.text()) * self.exposure_units
        
        # Find nearest allowed frame rate and sets it
        new_index = np.argmin(np.abs(self.exposure_list - new_value))
        new_exposure = self.exposure_list[new_index]
        new_exposure = self.backend.set_exposure(new_exposure)
        self.widget.exp_text.setText("{:0.4g}".format(new_exposure.to(self.exposure_units).magnitude))
        self.widget.exp_slider.setValue(new_index)
        
        self.exposure_changed.emit()
    
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


class CameraSave(SaveManager, Backend):
    
    class _modes(Enum):
        DATA = 'data'
        IMAGE = 'image'
    
    class _formats(Enum):
        INTEGER = "%0.1i"
        FLOAT = "%.12e"
    
    DELIMITER = "\t"
    
    def __init__(self, camera_control_be: CameraControl, mode="data"):
        
        self.camera_control_be = camera_control_be
        self.mode = mode
        
        super().__init__(self.save_frame,
                         self.camera_control_be.new_data,
                         stop_condition='count',
                         limit=1,
                         append='timestamp',
                         path=PATH(),
                         data=TRIGGER_RETURN(0),
                         mode=INSTANCE_ATTRIBUTE("mode"))
    
    @property
    def mode(self):
        return self._mode
    
    @mode.setter
    def mode(self, value):
        if isinstance(value, str):
            value = self._modes(value)
        elif isinstance(value, type(self._modes.DATA)):
            value = self._modes[value.name]
        else:
            raise TypeError("Camera save mode must be either a string with a valid mode name or a valid mode enum object.")
        
        self._mode = value
    
    def save_frame(self, path, data, mode):
        if mode == self._modes.DATA:
            if np.issubdtype(data.dtype, np.integer):
                fmt = self._formats.INTEGER.value
            elif np.issubdtype(data.dtype, np.float):
                fmt = self._formats.FLOAT.value
            
            np.savetxt(path, data, fmt=fmt, delimiter=self.DELIMITER)
        
        elif mode == self._modes.IMAGE:
            imsave(path, data)

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
        self.widget.mode_combo.setCurrentText(self.backend._modes.DATA.value.capitalize())
    
    def configure_backend(self):
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
            value = "count"
        elif self.widget.time_radio.isChecked():
            value = "time"
        self.backend.stop_condition = value
    
    def read_stop_condition(self, value):
        if value == 'count':
            self.widget.count_text.setEnabled(True)
            self.widget.time_text.setDisabled(True)
        elif value == 'time':
            self.widget.count_text.setDisabled(True)
            self.widget.time_text.setEnabled(True)
    
    def send_limit(self):
        if self.widget.count_radio.isChecked():
            value = int(self.widget.count_text.text())
            self.backend.limit = value
        elif self.widget.time_radio.isChecked():
            value = ureg.Quantity(self.widget.time_text.text())
            self.backend.limit = value
    
    def read_limit(self, value):
        if self.backend.stop_condition == "count":
            self.widget.count_text.setText(str(value))
        elif self.backend.stop_condition == "time":
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
        
        self.backend.append = value
    
    def read_append(self, value):
        if "count" in value:
            self.widget.count.setChecked(True)
        else:
            self.widget.count.setChecked(False)
        
        if "timestamp" in value:
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
    
    def read_mode(self, value):
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
    
    def read_saved(self, path, count, time):
        if self.widget.count_radio.isChecked():
            text = "Saved file {} of {}.".format(count, self.backend.limit)
        elif self.widget.time_radio.isChecked():
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
        self.widget.getView().invertY(True) # Positions axis origin at top-left corner
        self.widget.getView().setBackgroundColor(color=(20,20,20))
        
        self.img = self.widget.getImageItem()
        self.img.setOpts(axisOrder='row-major') # Pixels follow row-column order as y-x
    
    def connect_backend(self):
        super().connect_backend()
        
        self.backend.new_data.connect(self.refresh)
    
    def refresh(self, data, timestamp=None):
        self.img.setImage(data,
                          autoLevels = False,
                          levels = (0,255))