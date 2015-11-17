#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, Timer
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue
from cocotb.clock import Clock

from basil.utils.BitLogic import BitLogic
import numpy as np

class MCAFileDriver(BusDriver):
   
    _signals = ['ADC_CLK', 'ADC_CH0', 'ADC_CH1', 'ADC_CH2', 'ADC_CH3']

    def __init__(self, entity, file_name):
        BusDriver.__init__(self, entity, "", entity.ADC_CLK)
        
        print file_name
        self.data = np.load(file_name)
    @cocotb.coroutine
    def run(self):
        i = 0;
        bv = BitLogic(len(self.bus.ADC_CH0))
        
        data_size = self.data.shape[1]
        while 1:
            yield RisingEdge(self.clock)
            bv[:] = int(self.data[0, i % data_size])
            self.bus.ADC_CH0 <= BinaryValue(bits = len(self.bus.ADC_CH0), value = str(bv))
            bv[:] = int(self.data[1, i % data_size])
            self.bus.ADC_CH1 <= BinaryValue(bits = len(self.bus.ADC_CH0), value = str(bv))
            bv[:] = int(self.data[2, i % data_size])
            self.bus.ADC_CH2 <= BinaryValue(bits = len(self.bus.ADC_CH0), value = str(bv))
            bv[:] = int(self.data[3, i % data_size])
            self.bus.ADC_CH3 <= BinaryValue(bits = len(self.bus.ADC_CH0), value = str(bv))
            
            i += 1

            