# -*- coding: utf-8 -*-
"""
Created on Thu Jun 27 18:57:08 2019

@author: Fotonica
"""

from uc480.utilities.save import SaveManager, PATH, DATA, StopConditions, Numerations

from numpy import save, ones
from lantz.qt import QtCore

class TestCaller(QtCore.QObject):
    trigger = QtCore.pyqtSignal(object)
    
    def __init__(self):
        super().__init__()

caller = TestCaller()

def callback(path, data):
    print("Writing to path: {} the following data:".format(path))
    print(data)
    
    save(path, data)

sm = SaveManager(callback=callback,
                 trigger=caller.trigger)

sm.stop_condition = StopConditions.COUNT
sm.limit = 12
sm.packet_length = 5
sm.append = Numerations.TIMESTAMP

init_object = 0
sm.buffer_init = init_object

sm.callback_args = (PATH(), DATA(), )

sm.set_path("save_test\\test.npy")

sm.start()
for idx in range(14):
    caller.trigger.emit(idx)
    













