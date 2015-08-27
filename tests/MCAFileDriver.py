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
import random
import numpy as np

class MCAFileDriver(BusDriver):
   
    _signals = ['ADC_CLK', 'ADC_CH0', 'ADC_CH1', 'ADC_CH2', 'ADC_CH3']

    def __init__(self, entity, seed=1, start=0, hit_prob=0, trig_prob=0, stop = 8000 ):
        BusDriver.__init__(self, entity, "", entity.ADC_CLK)

    @cocotb.coroutine
    def run(self):
        val = 0;
        
        while 1:
            yield RisingEdge(self.clock)
            self.bus.ADC_CH0 <= BinaryValue(bits = len(self.bus.ADC_CH0), value= val % 2^14)
            self.bus.ADC_CH1 <= BinaryValue(bits = len(self.bus.ADC_CH0), value= (val + 1024) % 2^14)
            self.bus.ADC_CH2 <= BinaryValue(bits = len(self.bus.ADC_CH0), value= (val + 2 * 1048) % 2^14 )
            self.bus.ADC_CH3 <= BinaryValue(bits = len(self.bus.ADC_CH0), value= (val + 3 * 1024) % 2^14 )
            
            val += 1
            
            