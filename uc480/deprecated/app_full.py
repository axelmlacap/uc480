
import time

import numpy as np

from enum import Enum

from functools import wraps

from lantz.core import ureg
from lantz.qt.app import Backend, Frontend, InstrumentSlot, QtCore
from lantz.qt.app import BackendSlot
from lantz.qt.utils.qt import QtGui
#from lantz.qt.blocks import ChartUi, VerticalUi

from PyQt5 import QtWidgets

from pyqtgraph import ImageView, PlotWidget

from driver import Camera

from re import split, sub


Q = ureg.Quantity

def get_layout0(vertical):

    layout = QtGui.QVBoxLayout() if vertical else QtGui.QHBoxLayout()

    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)

    return layout


class CameraControl(Backend):
    
    camera: Camera = InstrumentSlot
    
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    new_data = QtCore.pyqtSignal(object, object)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        try:
            current_frame_interval = 1/self.camera.frame_rate
        except ZeroDivisionError:
            current_frame_interval = 0 * ureg.ms
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(current_frame_interval.to('ms').magnitude)
        self.timer.timeout.connect(self.read_image)
    
    def read_image(self):
        now = time.monotonic() * ureg.ms
        image = self.camera.get_frame()
        self.new_data.emit(now, image)
    
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


class CameraControlUi(Frontend):
    
    backend: CameraControl
    
    gui = 'camera_control.ui'
    
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
        
        self.widget.exp_slider.valueChanged.connect(self.new_exposure_by_slider)
        self.widget.exp_text.editingFinished.connect(self.new_exposure_by_text)
        
        self.widget.fps_slider.valueChanged.connect(self.new_frame_rate_by_slider)
        self.widget.fps_text.editingFinished.connect(self.new_frame_rate_by_text)
        
        self.widget.clk_combo.currentIndexChanged.connect(self.new_pixel_clock)
        self.widget.run_checkbox.stateChanged.connect(lambda new_value: self.backend.start_stop(new_value == 2))
        
        self.pixel_clock_changed.connect(self.refresh_frame_rate_list)
        self.pixel_clock_changed.connect(self.refresh_exposure_list)
        self.frame_rate_changed.connect(self.refresh_exposure_list)
        self.exposure_changed.connect(self.refresh_frame_rate_list)
    
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


class ImageViewerUi(Frontend):
    
    backend: CameraControl
    
    gui = 'image_viewer.ui'
    
    def setupUi(self):
        super().setupUi()
        
        self.widget = ImageView(parent=self)
        self.setCentralWidget(self.widget)
        
        self.widget.getView().setAspectLocked(True) # Fixed aspect ratio
        self.widget.getView().invertY(True) # Positions axis origin at top-left corner
        
        self.img = self.widget.getImageItem()
        self.img.setOpts(axisOrder='row-major') # Pixels follow row-column order as y-x
    
    def connect_backend(self):
        super().connect_backend()
        
        self.backend.new_data.connect(self.refresh)
    
    def refresh(self, time, data):
        self.img.setImage(data,
                          autoLevels = False,
                          levels = (0,255))


class SpectraAnalyzer(Backend):
    
    new_data = QtCore.pyqtSignal(object, object)
    overload = QtCore.pyqtSignal()
    
    enable_set = QtCore.pyqtSignal(object, object)
    mode = QtCore.pyqtSignal(object, object)
    axis = QtCore.pyqtSignal(object, object)
    normalize = QtCore.pyqtSignal(object, object)
    substract_dark = QtCore.pyqtSignal(object, object)
    averages = QtCore.pyqtSignal(object, object)
    boxcar = QtCore.pyqtSignal(object, object)
    aoi_set = QtCore.pyqtSignal(object, object)
    aoi_from_camera = QtCore.pyqtSignal(object, object)
    
    x_calibration_set = QtCore.pyqtSignal(object, object, object)
    x_calibration_toggled = QtCore.pyqtSignal(object, object)
    
    y_calibration_set = QtCore.pyqtSignal(object, object, object)
    y_calibration_toggled = QtCore.pyqtSignal(object, object)
    
    dark_set = QtCore.pyqtSignal(object)
    reference_set = QtCore.pyqtSignal(object)
    plot_dark = QtCore.pyqtSignal(object, object)
    plot_reference = QtCore.pyqtSignal(object, object)
    
    def __init__(self, camera_control_backend=None, test=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.enable = False
        self.test = test
        
        self.spectrum = Spectrum()
        self.wavelength_axis = 'horizontal'
        
        self.aoi = AOI2D(units=ureg.px)
        self.aoi.from_camera = False
        self.aoi.limits_changed.connect(self.reshape_spectrum_limits)
        
        self.calibrate_x_toggle = True
        self.calibrate_y_toggle = True
        self.x_offset = self.y_offset = 0
        self.x_slope = self.y_slope = 1
        
        self.camera_control_be = camera_control_backend
        
        if test:
            self.set_aoi_from_camera(False)
            self.aoi.set_canvas([0, 1280, 0, 1024])
            self.aoi.reset_limits()
            
            self.timer = QtCore.QTimer()
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.generate_test_image)
    
    def set_enable(self, value, timestamp=None):
        now = time.monotonic() * ureg.ms
        
        self.enable = value
        
        if value:
            self.log_debug("Spectra analyzer enabled")
            if self.test:
                self.log_debug("Timer started")
                self.timer.start()
        else:
            self.log_debug("Spectra analyzer disabled")
            if self.test:
                self.log_debug("Timer stopped")
                self.timer.stop()
        
        self.enable_set.emit(value, now)
    
#    def set_mode(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.spectrum.mode = value
#        self.mode.emit(value, now)
#    
#    def set_axis(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        if not isinstance(value, str):
#            raise TypeError("Wavelength axis value must be string type")
#        
#        value = value.lower()
#        
#        if value not in ["horizontal", "vertical"]:
#            raise ValueError("Wavelength axis value must be 'horizontal' or 'vertical'")
#        
#        self.wavelength_axis = value
#        self.axis.emit(value, now)
#    
#    def set_normalize(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.spectrum.normalize = value
#        self.normalize.emit(value, now)
#    
#    def set_substract_dark(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.spectrum.substract_dark = value
#        self.substract_dark.emit(value, now)
#    
#    def set_averages(self, value, timestamp=None):
#        raise NotImplementedError("Spectra averaging not yet available.")
#    
#    def set_boxcar(self, value, timestamp=None):
#        raise NotImplementedError("Boxcar filtering not yet available.")
#    
#    def set_dark(self, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.spectrum.dark = self.spectrum.processed
#        self.dark_set.emit(now)
#    
#    def set_plot_dark(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.plot_dark.emit(value, now)
#    
#    def set_reference(self, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.spectrum.reference = self.spectrum.processed
#        self.reference_set.emit(now)
#    
#    def set_plot_reference(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.plot_reference.emit(value, now)
#    
    def set_aoi(self, value, timestamp=None):
        now = time.monotonic() * ureg.ms
        
        self.aoi.limits = value
        self.update_data(new_x=self.get_wavelength_vector())
        self.aoi_set.emit(value, now)
#    
    def set_aoi_from_camera(self, value, timestamp=None):
        now = time.monotonic() * ureg.ms
        
        self.aoi.from_camera = value
        self.aoi_from_camera.emit(value, now)
#    
#    def enable_x_calibration(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.calibrate_x_toggle = value
#        self.x_calibration_toggled.emit(value, now)
#    
#    def set_x_calibration(self, slope, offset, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.x_offset = offset
#        self.x_slope = slope
#        self.spectrum.update_data(new_x=self.get_wavelength_vector(), new_y=self.spectrum.raw.y)
#        
#        self.x_calibration_set.emit(offset, slope, now)
#    
#    def reset_x_calibration(self, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.x_offset = 0
#        self.x_slope = 1
#        self.spectrum.update_data(new_x=self.get_wavelength_vector())
#        
#        self.x_calibration_set(self.x_offset, self.x_slope, now)
#    
#    def enable_y_calibration(self, value, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.calibrate_y_toggle = value
#        self.y_calibration_toggled.emit(value, now)
#    
#    def set_y_calibration(self, slope, offset, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.y_offset = offset
#        self.y_slope = slope
#        
#        self.y_calibration_set(offset, slope, now)
#    
#    def reset_y_calibration(self, timestamp=None):
#        now = time.monotonic() * ureg.ms
#        
#        self.y_offset = 0
#        self.y_slope = 1
#        
#        self.y_calibration_set(self.y_offset, self.y_slope, now)
#    
    def calibrate_x(self, x):
        return self.x_offset + x * self.x_slope 
    
    def calibrate_y(self, y):
        return self.y_offset + y * self.y_slope
    
    def get_wavelength_vector(self):
        return self.calibrate_x(np.arange(self.aoi.xmin.magnitude, self.aoi.xmax.magnitude))
    
    def reshape_spectrum_limits(self, new_limits):        
        if self.wavelength_axis=='horizontal':
            new_limits = new_limits[0:2].to('px').magnitude
        elif self.wavelength_axis=='vertical':
            new_limits = new_limits[2:4].to('px').magnitude
        
        if self.calibrate_x_toggle:
            new_limits = self.calibrate_x(new_limits)
        
        self.spectrum.reshape_x(new_limits=new_limits)
    
    def link_camera(self):        
        max_width = self.camera_control_be.camera.sensor_info.max_width
        max_height = self.camera_control_be.camera.sensor_info.max_height
        
        self.aoi.set_canvas([0, max_width, 0, max_height])
        self.reset_aoi()
        self.set_aoi_from_camera(True)
    
    def from_image(self, image):
        now = time.monotonic() * ureg.ms
        
        mean_axis = 0 if self.wavelength_axis=='horizontal' else 1
        y = self.calibrate_y(np.mean(image, axis=mean_axis))
        
        if self.normalize:
            y = y/np.max(y)
        
        self.spectrum.update_data(new_y=y)
        self.new_data.emit(self.spectrum.processed, now)
    
    def from_camera(self, call_time, image):
        if self.enable:
            self.from_image(image)
    
    def generate_test_image(self):
        self.log_debug("A simulated frame was created")
        
        width = self.aoi.canvas.width.magnitude
        height = self.aoi.canvas.height.magnitude
        
        image = np.zeros((height, width))
        X, Y = np.meshgrid(np.arange(width), np.arange(height))
        
        center = np.array([width/2 + np.random.randn(1) * width/20, height/2 + np.random.randn(1) * height/20])
        std = np.array([10*width + np.random.randn(1) * width/5, 2*height + np.random.randn(1) * height/5])
        
        image = np.exp(-(X-center[0])**2/(2*std[0])) * np.exp(-(Y-center[1])**2/(2*std[1]))
        
        self.from_image(image)
        


class SpectraAnalyzerUi(Frontend):
    
    backend: SpectraAnalyzer
    
    gui = 'spectra_analyzer.ui'
    
    enable_set = QtCore.pyqtSignal(object, object)
    mode = QtCore.pyqtSignal(object, object)
    axis = QtCore.pyqtSignal(object, object)
    normalize = QtCore.pyqtSignal(object, object)
    substract_dark = QtCore.pyqtSignal(object, object)
    averages = QtCore.pyqtSignal(object, object)
    boxcar = QtCore.pyqtSignal(object, object)
    aoi = QtCore.pyqtSignal(object, object)
    aoi_from_camera = QtCore.pyqtSignal(object, object)
    
    set_x_calibration = QtCore.pyqtSignal(object, object, object)
    enable_x_calibration = QtCore.pyqtSignal(object, object)
    set_y_calibration = QtCore.pyqtSignal(object, object, object)
    enable_y_calibration = QtCore.pyqtSignal(object, object)
    
    set_dark = QtCore.pyqtSignal(object)
    set_reference = QtCore.pyqtSignal(object)
    plot_dark = QtCore.pyqtSignal(object, object)
    plot_reference = QtCore.pyqtSignal(object, object)
    
    overload = QtCore.pyqtSignal(object)
    overload_true_bckg_color = "(255, 50, 50, 255)" # rgba format, as string
    overload_true_font_color = "(255, 255, 255, 255)" # rgba format, as string
    overload_false_bckg_color = "(255, 50, 50, 0)" # rgba format, as string
    overload_false_font_color = "(170, 170, 170, 255)" # rgba format, as string
    
    def setupUi(self):
        super().setupUi()
        
        # Connections
#        self.widget.enable.toggled.connect(self.send_enable)
        
#        self.widget.mode_combo.currentTextChanged.connect(self.send_mode)
#        self.widget.axis_horizontal.toggled.connect(lambda x: self.send_axis(value='horizontal'))
#        self.widget.axis_vertical.toggled.connect(lambda x: self.send_axis('vertical'))
#        self.widget.normalize.toggled.connect(self.send_normalize)
#        self.widget.dark_substract.toggled.connect(self.send_substract_dark)
#        self.widget.avg_text.textEdited.connect(self.send_average)
#        self.widget.box_text.textEdited.connect(self.send_boxcar)
#        
#        self.widget.dark_set.clicked.connect(self.send_set_dark)
#        self.widget.ref_set.clicked.connect(self.send_set_reference)
#        self.widget.dark_plot.toggled.connect(self.send_plot_dark)
#        self.widget.ref_plot.toggled.connect(self.send_plot_reference)
#        
#        self.widget.aoi_from_camera.toggled.connect(self.send_aoi_from_camera)
#        self.widget.aoi_text.textEdited.connect(self.send_aoi)
#        
#        self.widget.xcal_set.clicked.connect(self.send_x_calibration)
#        self.widget.xcal_enable.toggled.connect(self.send_enable_x_calibration)
#        self.widget.xcal_reset.clicked.connect(self.send_reset_x_calibration)
#        self.widget.ycal_set.clicked.connect(self.send_y_calibration)
#        self.widget.ycal_enable.toggled.connect(self.send_enable_y_calibration)
#        self.widget.ycal_reset.clicked.connect(self.send_reset_y_calibration)
#        
#        self.widget.aoi_from_camera.toggled.connect(self.send_aoi_from_camera)
    
    def connect_backend(self):
        super().connect_backend()
        
        # Default values
        for idx in range(self.widget.mode_combo.count()):
            self.widget.mode_combo.removeItem(0)
        for mode in self.backend.spectrum.modes:
            self.widget.mode_combo.addItem(mode.capitalize())
        self.widget.mode_combo.setCurrentText(self.backend.spectrum.mode.capitalize())
        
        # Incoming signals
#        self.backend.enable_set.connect(self.read_enable)
#        self.backend.mode.connect(self.read_mode)
#        self.backend.axis.connect(self.read_axis)
#        self.backend.normalize.connect(self.read_normalize)
#        self.backend.substract_dark.connect(self.read_substract_dark)
#        self.backend.averages.connect(self.read_average)
#        self.backend.boxcar.connect(self.read_boxcar)
        self.backend.aoi_set.connect(self.read_aoi)
        self.backend.aoi_from_camera.connect(self.read_aoi_from_camera)
#        
#        self.backend.x_calibration_set.connect(self.read_x_calibration)
#        self.backend.x_calibration_toggled.connect(self.read_enable_x_calibration)
#        self.backend.y_calibration_set.connect(self.read_y_calibration)
#        self.backend.y_calibration_toggled.connect(self.read_enable_y_calibration)
#        
#        self.backend.plot_dark.connect(self.read_plot_dark)
#        self.backend.plot_reference.connect(self.read_plot_reference)
        
        # Outgoing signals
        self.widget.enable.toggled.connect(self.backend.set_enable)
#        self.enable_set.connect(self.backend.set_enable)
#        self.mode.connect(self.backend.set_mode)
#        self.axis.connect(self.backend.set_axis)
#        self.normalize.connect(self.backend.set_normalize)
#        self.substract_dark.connect(self.backend.set_substract_dark)
#        self.averages.connect(self.backend.set_averages)
#        self.boxcar.connect(self.backend.set_boxcar)
#        self.aoi.connect(self.backend.set_aoi)
#        self.aoi_from_camera.connect(self.backend.set_aoi_from_camera)
#        
#        self.set_x_calibration.connect(self.backend.set_x_calibration)
#        self.enable_x_calibration.connect(self.backend.enable_x_calibration)
#        self.set_y_calibration.connect(self.backend.set_y_calibration)
#        self.enable_y_calibration.connect(self.backend.enable_y_calibration)
#        
#        self.set_dark.connect(self.backend.set_dark)
#        self.set_reference.connect(self.backend.set_reference)
#        self.plot_dark.connect(self.backend.set_plot_dark)
#        self.plot_reference.connect(self.backend.set_plot_reference)
        
        if not isinstance(self.backend.camera_control_be, type(None)):
            self.backend.link_camera()
#        else:
#            self.backend.set_enable(True)
    
    def send_enable(self, value):
        now = time.monotonic() * ureg.ms
        
        self.enable_set.emit(value, now)
    
    def read_enable(self, value, timestamp=None):
        self.widget.enable.setDown(value)
    
#    def send_mode(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        value = value.lower()
#        self.mode.emit(value, now)
#    
#    def read_mode(self, value, timestamp):
#        self.widget.mode_combo.setCurrentText(value.capitalize())
#    
#    def send_axis(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.axis.emit(value, now)
#    
#    def read_axis(self, value, timestamp):        
#        if value == "horizontal":
#            self.widget.axis_horizontal.setDown(True) # Use setDown to avoid sending toggle signals
#        elif value == "vertical":
#            self.widget.axis_vertical.setDown(True)
#    
#    def send_normalize(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.normalize.emit(value, now)
#    
#    def read_normalize(self, value, timestamp):
#        self.widget.normalize.setDown(value)
#    
#    def send_substract_dark(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.substract_dark.emit(value, now)
#    
#    def read_substract_dark(self, value, timestamp):
#        self.widget.dark_substract.setDown(value)
#    
#    def send_average(self, value):
#        raise NotImplementedError("Spectra averaging not yet available.")
#    
#    def read_average(self, value, timestamp):
#        raise NotImplementedError("Spectra averaging not yet available.")
#    
#    def send_boxcar(self, value):
#        raise NotImplementedError("Boxcar filtering not yet available.")
#    
#    def read_boxcar(self, value, timestamp):
#        raise NotImplementedError("Boxcar filtering not yet available.")
#    
#    def send_set_dark(self):
#        now = time.monotonic() * ureg.ms
#        
#        self.set_dark.emit(now)
#    
#    def send_set_reference(self):
#        now = time.monotonic() * ureg.ms
#        
#        self.set_reference.emit(now)
#    
#    def send_plot_dark(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.plot_dark.emit(value, now)
#    
#    def read_plot_dark(self, value, timestamp):
#        self.widget.dark_plot.setDown(value)
#    
#    def send_plot_reference(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.plot_reference.emit(value, now)
#    
#    def read_plot_reference(self, value, timestamp):
#        self.widget.ref_plot.setDown(value)
#    
    def send_aoi(self, value):
        now = time.monotonic() * ureg.ms
        
        aoi_limits = [float(lim) for lim in split("\[|,|\]",value) if lim != ""]
        self.aoi.emit(self, aoi_limits, now)
    
    def read_aoi(self, value, timestamp):
        if self.widget.aoi_toggle.checked:
            self.widget.aoi_text.setPlainText(str(value).replace(" ",""))
    
    def send_aoi_from_camera(self, value):
        now = time.monotonic() * ureg.ms
        
        self.aoi_from_camera.emit(value, now)
    
    def read_aoi_from_camera(self, value, timestamp=None):
        if value:
            self.widget.aoi_text.setDisabled(True)
        else:
            self.widget.aoi_text.setEnabled(True)
#    
#    def send_x_calibration(self):
#        now = time.monotonic() * ureg.ms
#        
#        offset = float(self.widget.xcal_offset_text.text)
#        slope = float(self.widget.xcal_slope_text.text)
#        self.send_x_calibration.emit(self, offset, slope, now)
#    
#    def read_x_calibration(self, offset, slope, timestamp):
#        self.widget.xcal_offset_text.setPlainText(str(offset))
#        self.widget.xcal_slope_text.setPlaiText(str(slope))
#    
#    def send_enable_x_calibration(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.enable_x_calibration.emit(self, value, now)
#    
#    def read_enable_x_calibration(self, value, timestamp):
#        self.widget.xcal_enable.setChecked(value)
#    
#    def send_reset_x_calibration(self):
#        now = time.monotonic() * ureg.ms
#        
#        self.reset_x_calibration.emit(self, now)
#    
#    def send_y_calibration(self):
#        now = time.monotonic() * ureg.ms
#        
#        offset = float(self.widget.ycal_offset_text.text)
#        slope = float(self.widget.ycal_slope_text.text)
#        self.send_y_calibration.emit(self, offset, slope, now)
#    
#    def read_y_calibration(self, offset, slope, timestamp):
#        self.widget.ycal_offset_text.setPlainText(str(offset))
#        self.widget.ycal_slope_text.setPlaiText(str(slope))
#    
#    def send_enable_y_calibration(self, value):
#        now = time.monotonic() * ureg.ms
#        
#        self.enable_y_calibration.emit(self, value, now)
#    
#    def read_enable_y_calibration(self, value, timestamp):
#        self.widget.ycal_enable.setChecked(value)
#    
#    def send_reset_y_calibration(self):
#        now = time.monotonic() * ureg.ms
#        
#        self.reset_y_calibration.emit(self, now)
#    
#    def read_monitor(self, process_time, frame_interval, overload):
#        text = "Process time: {:~}" + "\r\n" + "Frame interval: {:~}".format(process_time, frame_interval)
#        self.widget.mon_text.setPlainText(text)
#        
#        if overload:
#            new_font_color = self.overload_true_font_color
#            new_background_color = self.overload_true_background_color
#        else:
#            new_font_color = self.overload_false_font_color
#            new_background_color = self.overload_false_background_color
#        
#        stylesheet = self.widget.overload.styleSheet
#        stylesheet = sub("color: rgba(.*)", "color: rgba{}".format(new_font_color), stylesheet)
#        stylesheet = sub("background-color: rgba(.*)", "background-color: rgba{}".format(new_background_color), stylesheet)
#        self.widget.overload.setStyleSheet(stylesheet)


class SpectraViewerUi(Frontend):
    
    backend: SpectraAnalyzer
    
    gui = 'image_viewer.ui'
    
    def setupUi(self):
        super().setupUi()
        
        self.widget = PlotWidget(parent=self)
        self.setCentralWidget(self.widget)
        
        self.plot_item = self.widget.getPlotItem()
        self.plot_item.setLabel('left', 'Intensity')
        self.plot_item.setLabel('bottom', 'Wavelength')
#        self.plot_item.show_grid(x=True, y=True, alpha=0.3)
        self.plot_item.enableAutoScale()
        
        self.plot_data_item = self.plot_item.plot(x=np.zeros((2,)), y=np.zeros((2,)))
    
    def connect_backend(self):
        super().connect_backend()
        
        self.backend.new_data.connect(self.refresh)
    
    def refresh(self, spectrum, timestamp=None):
        self.plot_data_item.setData(x=spectrum.x, y=spectrum.y)


#%% Main UI classes

class Main(Backend):
    control_be: CameraControl = BackendSlot
    spectra_be: SpectraAnalyzer = BackendSlot


class MainUi(Frontend):
    backend: Main
    
    gui = 'main.ui'
    
    # leftbar
    control_ui: CameraControlUi = CameraControlUi.using('control_be')
    spectra_ui: SpectraAnalyzerUi = SpectraAnalyzerUi.using('spectra_be')
    
    # central
    viewer_ui: ImageViewerUi = ImageViewerUi.using('control_be')
    spectra_view_ui: SpectraViewerUi = SpectraViewerUi.using('spectra_be')
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.control_ui)
        layout.addWidget(self.spectra_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_image_page = layout =  get_layout0(vertical=False)
        layout.addWidget(self.viewer_ui)
        self.image_page.setLayout(layout)
        
        # Central, page 2
        self.l_spectrum_page = layout =  get_layout0(vertical=False)
        layout.addWidget(self.spectra_ui)
        self.spectrum_page.setLayout(layout)


class CameraMainUi(Frontend):
    backend: Main
    
    gui = 'main.ui'
    
    # leftbar
    control_ui: CameraControlUi = CameraControlUi.using('control_be')
    
    # central
    viewer_ui: ImageViewerUi = ImageViewerUi.using('control_be')
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.control_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_image_page = layout =  get_layout0(vertical=False)
        layout.addWidget(self.viewer_ui)
        self.image_page.setLayout(layout)


class SpectraMainUi(Frontend):
    backend: SpectraAnalyzer
    
    gui = 'main.ui'
    
    # leftbar
    spectra_ui: SpectraAnalyzerUi = SpectraAnalyzerUi.using_parent_backend()    
    # central
    spectra_view_ui: SpectraViewerUi = SpectraViewerUi.using_parent_backend()
    
    def setupUi(self):
        super().setupUi()
        
        # Leftbar
        self.l_leftbar = layout = get_layout0(vertical=True)
        layout.addWidget(self.spectra_ui)
        layout.addStretch()
        self.leftbar.setLayout(layout)
        
        # Central, page 1
        self.l_image_page = layout =  get_layout0(vertical=False)
        layout.addWidget(self.spectra_view_ui)
        self.image_page.setLayout(layout)


#%% Auxiliar classes

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
    
    limits_changed = QtCore.pyqtSignal(object)
    
    class Validators:
        """
        Container class for decorators (decorators cannot be defined as
        instance or static methods
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
                
                # Universal conversion to pint quantity
                try:
                    value = value.to(units)
                except AttributeError:
                    value = value * units
                
                if func.__name__ == 'origin':
                    # Origin dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                    except AttributeError:
                        raise ValueError('Area origin value must be a two element numpy or pint array with structure [xmin, ymin]')
                
                if func.__name__ == 'end':
                    # End dimension validation
                    try:
                        if value.shape != (2,):
                            raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                    except AttributeError:
                        raise ValueError('Area end value must be a two element numpy or pint array with structure [xmax, ymax]')
                
                if func.__name__ == 'limits':
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
    
    def __init__(self, limits=None, canvas_limits=None, units=None):
        super().__init__()
        
        self.canvas = None
        self._units = self._D_UNITS
        self._xmin = self._D_XMIN * self._D_UNITS
        self._xmax = self._D_XMAX * self._D_UNITS
        self._ymin = self._D_YMIN * self._D_UNITS
        self._ymax = self._D_YMAX * self._D_UNITS
        
        if isinstance(units, type(None)):
            self.units = self._D_UNITS
        else:
            self.units = units
        
        if isinstance(canvas_limits, type(None)):
            self.canvas = None
        else:
            self.canvas = self.__class__(limits=canvas_limits, units=self.units)
        
        if isinstance(limits, type(None)):
            if isinstance(self.canvas, type(None)):
                # If no canvas is provided, use default limits
                pass
            else:
                # If a canvas is provided, set maximum limits
                self.limits = self.canvas.limits
        else:
            self.limits = limits
    
    @property
    def xmin(self):
        return self._xmin
    
    @xmin.setter
    @Validators.value
    @Validators.canvas
    def xmin(self, value):
        if self._xmin != value:
            self._xmin = value
            
            if value > self.xmax:
                self.xmax = value
            
            self.limits_changed.emit(self.limits)
    
    @property
    def xmax(self):
        return self._xmax
    
    @xmax.setter
    @Validators.value
    @Validators.canvas
    def xmax(self, value):
        if self._xmax != value:
            self._xmax = value
        
            if value < self.xmin:
                self.xmin = value
            
            self.limits_changed.emit(self.limits)
    
    @property
    def ymin(self):
        return self._ymin
    
    @ymin.setter
    @Validators.value
    @Validators.canvas
    def ymin(self, value):
        if self.ymin != value:
            self._ymax = value
            
            if value > self.ymax:
                self.ymax = value
            
            self.limits_changed.emit(self.limits)
    
    @property
    def ymax(self):
        return self._ymax
    
    @ymax.setter
    @Validators.value
    @Validators.canvas
    def ymax(self, value):
        if self._ymax != value:
            self._ymax = value
            
            if value < self.ymin:
                self.ymin = value
            
            self.limits_changed.emit(self.limits)
    
    @property
    def origin(self):
        return [self.xmin.magnitude, self.ymin.magnitude] * self.units
    
    @origin.setter
    @Validators.value
    @Validators.canvas
    def origin(self, value):
        self.xmin = value[0]
        self.ymin = value[1]
    
    @property
    def end(self):
        return [self.xmax.magnitude, self.ymax.magnitude] * self.units
    
    @end.setter
    @Validators.value
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
    
    wavelegth_changed = QtCore.pyqtSignal(object)
    
    class _RawSpectrum:
        
        def __init__(self, x=None, y=None):
            self._x = np.array([0, 1], dtype=float)
            self._y = np.array([0, 1], dtype=float)
            
            self.update_data(x, y)
        
        @property
        def x(self):
            return self._x
        
        @x.setter
        def x(self, value):
            value = np.array(value, dtype=float)
            
            self.reshape_x(new_x=value)
        
        @property
        def y(self):
            return self._y
        
        @y.setter
        def y(self, value):
            value = np.array(value, dtype=float)
            
            if value.shape != self._y.shape:
                raise ValueError("Spectrum x and y data sizes must match. Use 'update_data' to change data to a new size.")
            
            self._y = value
        
        def update_data(self, new_x=None, new_y=None):
            new_x = np.array(new_x, dtype=float)
            new_y = np.array(new_y, dtype=float)
            
            if new_x.ndim == 0 and new_y.ndim == 0:
                pass
            elif new_x.ndim == 1 and new_y.ndim == 1:
                if new_x.shape != new_y.shape:
                    raise ValueError("Spectrum x and y data sizes must match.")
                else:
                    self._x = new_x
                    self._y = new_y
            elif new_x.ndim == 1:
                if new_x.shape != self._y.shape:
                    self.reshape_x(new_x=new_x)
                else:
                    self._x = new_x
            elif new_y.ndim == 1:
                if new_y.shape != self._x.shape:
                    raise ValueError("Spectrum x and y data sizes must match.")
                else:
                    self._y = new_y
            else:
                raise ValueError("Spectrum data must be 1D array-like type.")
            
        def reshape_x(self, new_x=None, new_limits=None):
            old_pitch = self.x[1]-self.x[0]
            old_limits = [self.x[0], self.x[-1]+old_pitch]
            
            if isinstance(new_x, type(None)) and isinstance(new_limits, type(None)):
                return None
            elif not isinstance(new_x, type(None)):
                new_pitch = new_x[1]-new_x[0]
                new_limits = [new_x[0], new_x[-1]+new_pitch]
                if old_pitch!=new_pitch:
                    raise ValueError('Wavelength pitch change is not allowed at resize. Provide new x and y data with update_data.')
            
            # If limits changed...
            if any(np.not_equal(old_limits, new_limits)):
                # Create new_x if not provided
                if isinstance(new_x, type(None)):
                    new_x = np.arange(new_limits[0], new_limits[1], old_pitch)
                
                new_y = self.y
                # Are you shrinking? Take slice
                if new_limits[0]>old_limits[0]:
                    new_y = new_y[self.x>=new_limits[0]]
                if new_limits[1]<old_limits[1]:
                    new_y = new_y[self.x<new_limits[1]]
                
                # Are you extending? Pad with zeros
                if new_limits[0]<old_limits[0]:
                    zeros = np.zeros((int((old_limits[0]-new_limits[0])/old_pitch), ))
                    new_y = np.append(zeros, new_y)
                if new_limits[1]>old_limits[1]:
                    zeros = np.zeros((int((new_limits[1]-old_limits[-1])/old_pitch), ))
                    new_y = np.append(new_y, zeros)
                
                # Finally update both x and y data
                self.update_data(new_x, new_y)
        
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
    
    def __init__(self, wavelength=None, intensity=None, mode='intensity', reference=None, dark=None, normalize=False, substract_dark=False):
        super().__init__()
        
        self.mode = mode
        self.substract_dark = substract_dark
        self.normalize = normalize
        
        self.raw = self._RawSpectrum(x=wavelength, y=intensity)
        self.reference = reference
        self.dark = dark
        
        self.processed = None
        self.process()
    
    @property
    def wavelength(self):
        return self._wavelength
    
    @wavelength.setter
    def wavelength(self, value):
        self.raw.update_data(new_x=value)
        self._wavelength = self.raw.x
                
        if not isinstance(self.dark, type(None)):
            self.dark.update_data(new_x=value)
        if not isinstance(self.reference, type(None)):
            self.reference.update_data(new_x=value)
    
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
    
    def update_data(self, new_x=None, new_y=None):
        new_x = np.array(new_x, dtype=float)
        new_y = np.array(new_y, dtype=float)
        
        if new_x.ndim == 0 and new_y.ndim == 0:
            pass
        elif new_x.ndim == 1 and new_y.ndim == 1:
            if new_x.shape != new_y.shape:
                raise ValueError("Spectrum x and y data sizes must match.")
            else:
                self.wavelength = new_x
                self.raw.update_data(new_y=new_y)
                self.process()
        elif new_x.ndim == 1:
            # Validations are within _RawSpectra
            self.wavelength = new_x
        elif new_y.ndim == 1:
             # Validations are within _RawSpectra
            self.raw.update_data(new_y=new_y)
            self.process()
        else:
            raise ValueError("Spectrum data must be 1D array-like type.")
    
    def reshape_x(self, *args, **kwargs):
        self.raw.reshape_x(*args, **kwargs)
        if not isinstance(self.dark, type(None)):
            self.dark.resize_x(*args, **kwargs)
        if not isinstance(self.reference, type(None)):
            self.reference.resize_x(*args, **kwargs)
    
    def process(self):
        processed = self.raw
        
        if self.substract_dark:
            processed = self.substract_dark(self.raw, self.dark)
        
        if self.mode == self._modes.INTENSITY:
            pass
        elif self.mode == self._modes.TRANSMISSION:
            processed = self.compute_transmission(processed, self.reference)
        elif self.mode == self._modes.ABSORBANCE:
            processed = self.compute_absorbance(processed, self.reference_spectrum)
        
        if self.normalize:
            processed = self.normalized(processed)
        
        self.processed = processed
            
    @classmethod
    def normalize(cls, raw):
        return cls._RawSpectrum(raw.x, raw.y/np.max(raw.y))
    
    @classmethod
    def substract_dark(cls, raw, dark):
        if raw.x != dark.x:
            raise ValueError('Cannot substract dark spectrum. Wavelengths from raw and dark spectra do not match.')
        
        return cls._RawSpectrum(raw.x, raw.y-dark.y)
    
    @classmethod
    def compute_transmission(cls, raw, ref):
        if raw.x != ref.x:
            raise ValueError('Cannot substract dark spectrum. Wavelengths from raw and dark spectra do not match.')
         
        return cls._RawSpectrum(raw.x, np.divide(raw.y, ref.y))
    
    @classmethod
    def compute_absorbance(cls, raw, ref):
        if raw.x != ref.x:
            raise ValueError('Cannot substract dark spectrum. Wavelengths from raw and dark spectra do not match.')
        
        return cls._RawSpectrum(raw.x, np.log10(np.divide(ref.y, raw.y)))






#%% Old classes

class RawCameraViewer(Backend):

    # Here we define that this backend requires an instrument assigned to
    # a variable named board.
    # This line could be just board = InstrumentSlot
    # By adding the TemperatureSensor after the semicolon
    # allows PyCharm and other IDE to provide autocompletion
    camera: Camera = InstrumentSlot

    # We create a Signal that will be emitted every time the timer ticks
    new_data = QtCore.pyqtSignal(object, object)

    # We also create signals every time the Timer is started or stopped.
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()

    def __init__(self, interval, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If the user is smart, she will provide a Pint Quantity.
        try:
            interval = interval.to('ms').magnitude
        except:
            pass
        
        # This timer will run periodically and call update temperature.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(interval) # ms
        self.timer.timeout.connect(self.read_image)

    def read_image(self):
        self.log_debug('Reading image from camera')

        now = time.monotonic() * ureg.ms
        image = self.camera.get_frame()
        self.new_data.emit(now, image)
        
        self.log_debug('Image readed at {}'.format(now))

    def start_stop(self, value):
        if value:
            self.timer.start()
            self.started.emit()
            self.log_debug('Camera viewer started')
        else:
            self.timer.stop()
            self.stopped.emit()
            self.log_debug('Camera viewer stopped')


class RawCameraViewerUi(Frontend):

    # This line is completely unnecesary to run the program
    # (backend is already defined in the Frontend parent class)
    # But adding it allows PyCharm and other IDE to provide autocompletion
    backend: RawCameraViewer

    # Instead of drawing the gui programatically, we use QtDesigner and just load it.
    # The resulting gui will be inside an attribute named widget
    gui = 'image_viewer.ui'
    
    def setupUi(self):
        import pyqtgraph as pg
        pg.setConfigOptions(antialias=True)
        
#        self.img = pg.ImageItem()
#        self.img.setOpts(axisOrder='row-major')
        
#        self.image_widget = pg.GraphicsLayoutWidget()
#        self.view = self.image_widget.addViewBox()
#        self.view.setAspectLocked(True)
#        self.view.invertY(True)
#        self.view.addItem(self.img)
#        
#        layout = QtGui.QVBoxLayout()
#        layout.addWidget(self.image_widget)
#        self.widget.imageWidget.setLayout(layout)
        self.widget.runCheckBox = QtWidgets.QCheckBox(text = "Run")
        
        self.widget.imageWidget = pg.ImageView(parent=self.widget)
        self.widget.imageWidget.getView().setAspectLocked(True)
        self.widget.imageWidget.getView().invertY(True)
        
        self.img = self.widget.imageWidget.getImageItem()
        self.img.setOpts(axisOrder='row-major')
        
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.widget.imageWidget)
        layout.addWidget(self.widget.runCheckBox)
        self.widget.setLayout(layout)

    def connect_backend(self):
        # This method is executed after the backend is assigned to the frontend
        super().connect_backend()
        
        self.backend.new_data.connect(self.refresh)
        self.widget.runCheckBox.stateChanged.connect(lambda new_value: self.backend.start_stop(new_value == 2))

    def refresh(self, time, data):
        self.img.setImage(data,
                          autoLevels = False,
                          levels = (0,255))

class CameraViewerUi(Frontend):
    
    control_ui = CameraControlUi.using_parent_backend()
    
    gui = 'image_viewer.ui'
    
    def setupUi(self):
        import pyqtgraph as pg
        pg.setConfigOptions(antialias=True)
                
        self.widget.imageWidget = pg.ImageView(parent=self.widget)
        self.widget.imageWidget.getView().setAspectLocked(True) # Fixed aspect ratio
        self.widget.imageWidget.getView().invertY(True) # Positions axis origin at top-left corner
        
        self.img = self.widget.imageWidget.getImageItem()
        self.img.setOpts(axisOrder='row-major') # Pixels follow row-column order as y-x
        
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.widget.imageWidget)
        layout.addWidget(self.control_ui.widget)
        self.widget.setLayout(layout)

    def connect_backend(self):
        # This method is executed after the backend is assigned to the frontend
        super().connect_backend()
        
        self.backend.new_data.connect(self.refresh)
        
    def refresh(self, time, data):
        self.img.setImage(data,
                          autoLevels = False,
                          levels = (0,255))