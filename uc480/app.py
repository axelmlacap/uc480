
import time

import numpy as np

from lantz.core import ureg
from lantz.qt import Backend, Frontend, InstrumentSlot, QtCore
from lantz.qt.utils.qt import QtGui
from lantz.qt.blocks import ChartUi, VerticalUi

from PyQt5 import QtWidgets

from driver import Camera


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
        # This method is executed after the backend is assigned to the frontend
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