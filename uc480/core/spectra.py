# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 13:01:25 2019

@author: Axel Lacapmesure
"""

from uc480.utilities.save import SaveManager, PATH, DATA
from uc480.utilities import AOI2D, Spectrum, file_dialog_save

from lantz.core import ureg
from lantz.qt.app import Backend, Frontend, QtCore

import numpy as np

from re import split

from time import monotonic

from pyqtgraph import PlotWidget


class SpectraAnalyzer(Backend):
    # XCAL_POL = [-2.07418056e-06, -6.01516616e-02, 8.39719080e+02]
    XCAL_POL = [1.0, 0.0]
    YCAL_POL = [1.0, 0.0]

    new_data = QtCore.pyqtSignal(object, object)

    plot_dark_set = QtCore.pyqtSignal(object)
    plot_reference_set = QtCore.pyqtSignal(object)
    aoi_set = QtCore.pyqtSignal(object)
    aoi_from_camera_set = QtCore.pyqtSignal(object)

    def __init__(self, camera_control_backend=None, test=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.enable = False
        self.test = test

        self.spectrum = Spectrum()
        self.wavelength_axis = 'horizontal'

        self.aoi = AOI2D(units=ureg.px)
        self.aoi_from_camera = False
        self.aoi.limits_changed.connect(self.reshape_spectrum_limits)

        self.x_units = "nm"
        self.y_units = "arb"
        self.enable_x_calibration(True)
        self.enable_y_calibration(False)
        self.set_x_calibration(self.XCAL_POL)
        self.set_y_calibration(self.YCAL_POL)

        self.camera_control_be = camera_control_backend

        if test:
            self.set_aoi_from_camera(False)
            self.aoi.set_canvas([0, 1280, 0, 1024])
            self.aoi.reset_limits()

            self.timer = QtCore.QTimer()
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.generate_test_image)

    def set_enable(self, value):
        self.enable = value

        if value:
            self.log_debug("Spectra analyzer enabled")
            if self.test:
                self.timer.start()
        else:
            self.log_debug("Spectra analyzer disabled")
            if self.test:
                self.timer.stop()

    def set_mode(self, value):
        self.spectrum.mode = value
        self.log_debug("Spectrum analyzer mode set to '{}'".format(self.spectrum.mode))

    def set_axis(self, value):
        if not isinstance(value, str):
            raise TypeError("Wavelength axis value must be string type")

        value = value.lower()

        if value not in ["horizontal", "vertical"]:
            raise ValueError("Wavelength axis value must be 'horizontal' or 'vertical'")

        self.wavelength_axis = value
        self.reshape_spectrum_limits(self.aoi.limits)
        self.log_debug("Spectrum analyzer wavelength axis set to {}".format(value))

    def set_normalize(self, value):
        self.spectrum.normalize = value
        self.log_debug("Spectra normalization set to {}".format(value))

    def set_subtract_dark(self, value):
        self.spectrum.subtract_dark = value
        self.log_debug("Spectra dark subtraction set to {}".format(value))

    def set_averages(self, value):
        self.spectrum.averages = value

    def set_boxcar(self, value):
        raise NotImplementedError("Boxcar filtering not yet available.")

    def set_dark(self):
        self.spectrum.dark = self.spectrum._RawSpectrum(self.spectrum.processed.x, self.spectrum.processed.y)
        self.log_debug("Dark spectrum set")

    def reset_dark(self):
        self.spectrum.dark = None
        self.log_debug("Dark spectrum reset")

    def set_plot_dark(self, value):
        self.plot_dark_set.emit(value)

    def set_reference(self):
        self.spectrum.reference = self.spectrum._RawSpectrum(self.spectrum.processed.x, self.spectrum.processed.y)
        self.log_debug('Reference spectrum set')

    def reset_reference(self):
        self.spectrum.reference = None
        self.log_debug('Reference spectrum reset')

    def set_plot_reference(self, value):
        self.plot_reference_set.emit(value)

    def set_aoi(self, value):
        self.aoi.limits = value
        self.update_data(new_x=self.get_wavelength_vector())
        self.log_debug("Spectra AOI limits set to {}".format(value))
        self.aoi_set.emit(value)

    def reset_aoi(self):
        self.aoi.reset_limits()
        self.update_data(new_x=self.get_wavelength_vector())
        self.log_debug("Spectra AOI limits set to {}".format(self.aoi.limits))
        self.aoi_set.emit(self.aoi.limits)

    def set_aoi_from_camera(self, value):
        self.aoi_from_camera = value
        self.log_debug("Get spectra AOI limits from camera {}".format('enabled' if value else 'disabled'))
        self.aoi_from_camera_set.emit(value)

    def enable_x_calibration(self, value):
        self.spectrum.calibrate_x = value
        self.spectrum.set_x_units(self.x_units if value else self.spectrum._RawSpectrum.D_X_UNITS)
        self.log_debug("Spectra x calibration turned {}".format('on' if value else 'off'))

    def set_x_calibration(self, value):
        self.spectrum.xcal = value

        if self.spectrum.calibrate_x:
            self.spectrum.x = self.get_wavelength_vector()
        self.log_debug("Spectra x calibration polynomial set to: {}".format(value))

    def reset_x_calibration(self):
        self.spectrum.xcal = [1.0, 0.0]

        if self.spectrum.calibrate_x:
            self.spectrum.x = self.get_wavelength_vector()
        self.log_debug("Spectra x calibration reset")

    def enable_y_calibration(self, value):
        self.spectrum.calibrate_y = value
        self.spectrum.set_y_units(self.y_units if value else self.spectrum._RawSpectrum.D_Y_UNITS)
        self.log_debug("Spectra y calibration turned {}".format('on' if value else 'off'))

    def set_y_calibration(self, value):
        self.spectrum.ycal = value

        if self.spectrum.calibrate_y:
            self.spectrum.process()
        self.log_debug("Spectra y calibration polynomial set to: {}".format(value))

    def reset_y_calibration(self):
        self.spectrum.ycal = [1.0, 0.0]

        if self.spectrum.calibrate_y:
            self.spectrum.process()
        self.log_debug("Spectra y calibration reset")

    #    def calibrate_x(self, x):
    #        return np.polyval(self.xcal_pol, x)
    #
    #    def calibrate_y(self, y):
    #        return np.polyval(self.ycal_pol, y)

    def get_wavelength_vector(self):
        return self.spectrum.wavelength

    def reshape_spectrum_limits(self, new_limits):
        if self.wavelength_axis == 'horizontal':
            new_limits = new_limits[0:2].to('px').magnitude
        elif self.wavelength_axis == 'vertical':
            new_limits = new_limits[2:4].to('px').magnitude

        self.spectrum.reshape_x(new_limits=new_limits)

    def link_camera(self):
        max_width = self.camera_control_be.camera.sensor_info.max_width
        max_height = self.camera_control_be.camera.sensor_info.max_height

        self.aoi.set_canvas([0, max_width, 0, max_height])
        self.aoi.reset_limits()
        self.set_aoi_from_camera(True)

        self.camera_control_be.new_data.connect(self.from_image)

    def from_image(self, image, timestamp=None):
        if self.enable:
            now = monotonic() * ureg.ms

            mean_axis = 0 if self.wavelength_axis == 'horizontal' else 1
            y = np.mean(image, axis=mean_axis)

            self.spectrum.y = y
            self.new_data.emit(self.spectrum.processed, now)

    def generate_test_image(self):
        width = self.aoi.canvas.width.magnitude
        height = self.aoi.canvas.height.magnitude

        image = np.zeros((height, width))
        X, Y = np.meshgrid(np.arange(width), np.arange(height))

        center = np.array([width / 2 + np.random.randn(1) * width / 20, height / 2 + np.random.randn(1) * height / 20])
        std = np.array([10 * width + np.random.randn(1) * width / 5, 2 * height + np.random.randn(1) * height / 5])

        image = np.exp(-(X - center[0]) ** 2 / (2 * std[0])) * np.exp(-(Y - center[1]) ** 2 / (2 * std[1]))

        self.log_debug("A simulated frame was created")
        self.from_image(image)


class SpectraAnalyzerUi(Frontend):
    backend: SpectraAnalyzer

    gui = 'gui/spectra_analyzer.ui'

    overload_true_bckg_color = "(255, 50, 50, 255)"  # rgba format, as string
    overload_true_font_color = "(255, 255, 255, 255)"  # rgba format, as string
    overload_false_bckg_color = "(255, 50, 50, 0)"  # rgba format, as string
    overload_false_font_color = "(170, 170, 170, 255)"  # rgba format, as string

    def setupUi(self):
        super().setupUi()

        # Connections
        self.widget.enable.stateChanged.connect(self.send_enable)

        self.widget.mode_combo.currentTextChanged.connect(self.send_mode)
        self.widget.axis_horizontal.toggled.connect(lambda x: self.send_axis('horizontal'))
        self.widget.axis_vertical.toggled.connect(lambda x: self.send_axis('vertical'))
        self.widget.normalize.stateChanged.connect(self.send_normalize)
        self.widget.dark_subtract.stateChanged.connect(self.send_subtract_dark)
        self.widget.avg_text.editingFinished.connect(self.send_average)
        self.widget.box_text.editingFinished.connect(self.send_boxcar)

        self.widget.dark_set.clicked.connect(self.send_set_dark)
        self.widget.dark_reset.clicked.connect(self.send_reset_dark)
        self.widget.ref_set.clicked.connect(self.send_set_reference)
        self.widget.ref_reset.clicked.connect(self.send_reset_reference)
        self.widget.dark_plot.stateChanged.connect(self.send_plot_dark)
        self.widget.ref_plot.stateChanged.connect(self.send_plot_reference)

        self.widget.save_button.clicked.connect(self.save_spectrum)

    #        self.widget.xcal_set.clicked.connect(self.send_x_calibration)
    #        self.widget.xcal_enable.stateChanged.connect(self.send_enable_x_calibration)
    #        self.widget.xcal_reset.clicked.connect(self.send_reset_x_calibration)
    #        self.widget.ycal_set.clicked.connect(self.send_y_calibration)
    #        self.widget.ycal_enable.stateChanged.connect(self.send_enable_y_calibration)
    #        self.widget.ycal_reset.clicked.connect(self.send_reset_y_calibration)

    def connect_backend(self):
        super().connect_backend()

        # Default values
        for idx in range(self.widget.mode_combo.count()):
            self.widget.mode_combo.removeItem(0)
        for mode in self.backend.spectrum.modes:
            self.widget.mode_combo.addItem(mode.capitalize())
        self.widget.mode_combo.setCurrentText(self.backend.spectrum._modes.INTENSITY.value.capitalize())

        # Incoming signals
        self.backend.aoi_set.connect(self.read_aoi)
        #        self.backend.aoi_from_camera_set.connect(self.read_aoi_from_camera)

        # Outgoing signals
        if not isinstance(self.backend.camera_control_be, type(None)):
            self.backend.link_camera()

    #        else:
    #            self.backend.set_enable(True)

    def send_enable(self, value):
        value = value == 2
        self.backend.set_enable(value)

    def read_enable(self, value):
        self.widget.enable.setDown(value)

    def send_mode(self, value):
        value = value.lower()
        self.backend.set_mode(value)

    def read_mode(self, value):
        self.widget.mode_combo.setCurrentText(value.capitalize())

    def send_axis(self, value):
        self.backend.set_axis(value)

    def read_axis(self, value, timestamp):
        if value == "horizontal":
            self.widget.axis_horizontal.setDown(True)  # Use setDown to avoid sending toggle signals
        elif value == "vertical":
            self.widget.axis_vertical.setDown(True)

    def send_normalize(self, value):
        value = value == 2
        self.backend.set_normalize(value)

    def read_normalize(self, value):
        self.widget.normalize.setChecked(value)

    def send_subtract_dark(self, value):
        value = value == 2
        self.backend.set_subtract_dark(value)

    def read_subtract_dark(self, value):
        self.widget.dark_subtract.setChecked(value)

    def send_average(self):
        value = self.widget.avg_text.text()
        if value != "":
            value = int(value)
            self.backend.set_averages(value)

    def read_average(self, value):
        self.widget.avg_text.setPlainText(str(value))

    def send_boxcar(self, value):
        raise NotImplementedError("Boxcar filtering not yet available.")

    def read_boxcar(self, value):
        raise NotImplementedError("Boxcar filtering not yet available.")

    def send_set_dark(self):
        self.backend.set_dark()

    def send_reset_dark(self):
        self.backend.reset_dark()

    def send_set_reference(self):
        self.backend.set_reference()

    def send_reset_reference(self):
        self.backend.reset_reference()

    def send_plot_dark(self, value):
        value = value == 2
        self.backend.set_plot_dark(value)

    def read_plot_dark(self, value):
        self.widget.dark_plot.setChecked(value)

    def send_plot_reference(self, value):
        value = value == 2
        self.backend.set_plot_reference(value)

    def read_plot_reference(self, value, timestamp):
        self.widget.ref_plot.setChecked(value)

    def send_aoi(self, value):
        aoi_limits = [float(lim) for lim in split("\[|,|\]", value) if lim != ""]
        self.backend.set_aoi(aoi_limits)

    def read_aoi(self, value):
        if self.widget.aoi_from_camera.checked:
            self.widget.aoi_text.setPlainText(str(value).replace(" ", ""))

    def send_aoi_from_camera(self, value):
        self.backend.set_aoi_from_camera(value)
        self.widget.aoi_text.setDisabled(value)

    #    def read_aoi_from_camera(self, value):
    #        if value:
    #            self.widget.aoi_text.setDisabled(True)
    #        else:
    #            self.widget.aoi_text.setEnabled(True)

    #    def send_x_calibration(self):
    #        offset = float(self.widget.xcal_offset_text.text)
    #        slope = float(self.widget.xcal_slope_text.text)
    #        self.backend.set_x_calibration(offset, slope)

    #    def read_x_calibration(self, offset, slope):
    #        self.widget.xcal_offset_text.setPlainText(str(offset))
    #        self.widget.xcal_slope_text.setPlaiText(str(slope))

    def send_enable_x_calibration(self, value):
        value = value == 2
        self.backend.enable_x_calibration.emit(self, value)

    def read_enable_x_calibration(self, value):
        self.widget.xcal_enable.setChecked(value)

    def send_reset_x_calibration(self):
        self.backend.reset_x_calibration()

    #    def send_y_calibration(self):
    #        offset = float(self.widget.ycal_offset_text.text)
    #        slope = float(self.widget.ycal_slope_text.text)
    #        self.backend.set_y_calibration(offset, slope)

    #    def read_y_calibration(self, offset, slope, timestamp):
    #        self.widget.ycal_offset_text.setPlainText(str(offset))
    #        self.widget.ycal_slope_text.setPlaiText(str(slope))

    def send_enable_y_calibration(self, value):
        self.backend.enable_y_calibration(value)

    def read_enable_y_calibration(self, value):
        self.widget.ycal_enable.setChecked(value)

    def send_reset_y_calibration(self):
        self.backend.reset_y_calibration()

    def save_spectrum(self):
        path = file_dialog_save("Guardar espectro", filetypes=[('Archivos de texto', '*.txt')])
        self.backend.spectrum.save(path,
                                   processed=self.widget.save_processed.isChecked(),
                                   raw=self.widget.save_raw.isChecked(),
                                   dark=self.widget.save_dark.isChecked(),
                                   reference=self.widget.save_ref.isChecked())


class SpectraViewerUi(Frontend):
    backend: SpectraAnalyzer

    gui = 'gui/image_viewer.ui'

    def setupUi(self):
        super().setupUi()

        self.widget = PlotWidget(parent=self)
        self.setCentralWidget(self.widget)

        self.plot_item = self.widget.getPlotItem()
        self.plot_item.setLabel('left', 'Intensity')
        self.plot_item.setLabel('bottom', 'Wavelength')
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.enableAutoRange()

        self.plot_data_item = self.plot_item.plot(x=np.zeros((2,)), y=np.zeros((2,)))

    def connect_backend(self):
        super().connect_backend()

        self.backend.new_data.connect(self.refresh)

    def refresh(self, spectrum, timestamp=None):
        self.plot_data_item.setData(x=spectrum.x, y=spectrum.y.flatten())


class SpectraSave(SaveManager, Backend):

    def __init__(self, spectra_analyzer_be: SpectraAnalyzer):

        self.spectra_analyzer_be = spectra_analyzer_be

        if spectra_analyzer_be is None:
            callback = None
            trigger = None
        else:
            callback = self.save_spectrum
            trigger = spectra_analyzer_be.spectrum.buffer_filled

        super().__init__(callback,
                         trigger,
                         index_of_data=0,
                         stop_condition='count',
                         limit=1,
                         append='timestamp',
                         buffer_init=Spectrum,
                         path=PATH(),
                         spectrum=DATA(),
                         processed=True,
                         raw=False,
                         dark=False,
                         reference=False)

    @staticmethod
    def save_spectrum(path: str, spectrum: Spectrum, *args, **kwargs):
        spectrum.save(path=path, *args, **kwargs)


class SpectraSaveUi(Frontend):
    backend: SpectraSave

    gui = 'gui/spectra_save.ui'

    def setupUi(self):
        super().setupUi()

        # Connections
        self.widget.enable.clicked.connect(self.send_enable)

        self.widget.count_radio.toggled.connect(self.refresh_stop_condition)
        self.widget.time_radio.toggled.connect(self.refresh_stop_condition)
        self.widget.count_text.editingFinished.connect(self.refresh_append)
        self.widget.time_text.editingFinished.connect(self.refresh_append)

        self.widget.count.toggled.connect(self.refresh_append)
        self.widget.timestamp.toggled.connect(self.refresh_append)

        #        self.widget.processed.toggled.connect(self.send_includes)
        #        self.widget.raw.toggled.connect(self.send_includes)
        #        self.widget.dark.toggled.connect(self.send_includes)
        #        self.widget.reference.toggled.connect(self.send_includes)

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
        self.backend.callback_kwargs_set.connect(self.read_includes)

    def configure_backend(self):
        self.send_stop_condition()
        self.send_limit()
        #        self.backend.save_every = self.backend.spectra_analyzer_be.spectrum.averages
        self.send_append()
        self.send_includes()
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
            self.backend.packet_length = value
        elif self.widget.time_radio.isChecked():
            value = ureg.Quantity(self.widget.time_text.text())
            estimated_frames = (value * self.backend.spectra_analyzer_be.camera_control_be.get_frame_rate()).magnitude \
                               // self.spectra_analyzer_be.spectrum.raw.buffer.length

            self.backend.limit = value
            self.backend.packet_length = int(2 * estimated_frames)

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
            if (self.widget.count_radio.isChecked() and int(
                    self.widget.count_text.text()) > 1) or self.widget.time_radio.isChecked():
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

    def send_includes(self):
        self.backend.callback_kwargs['processed'] = self.widget.processed.isChecked()
        self.backend.callback_kwargs['raw'] = self.widget.raw.isChecked()
        self.backend.callback_kwargs['dark'] = self.widget.dark.isChecked()
        self.backend.callback_kwargs['reference'] = self.widget.reference.isChecked()

    def read_includes(self, value):
        self.widget.processed.setChecked(value['processed'])
        self.widget.raw.setChecked(value['raw'])
        self.widget.dark.setChecked(value['dark'])
        self.widget.reference.setChecked(value['reference'])

    def file_dialog_save(self, title="Guardar archivo", initial_dir="/", filetypes=[("Text files", "*.txt")]):
        path = file_dialog_save(title=title, initial_dir=initial_dir, filetypes=filetypes)

        self.widget.path_text.setPlainText(path)

    def send_path(self):
        if not self.widget.path_text.toPlainText():
            self.file_dialog_save()

        self.backend.path = self.widget.path_text.toPlainText()

    def read_path(self, value):
        self.widget.path_text.setPlainText(value)

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
