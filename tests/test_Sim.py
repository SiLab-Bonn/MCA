#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import unittest

from basil.dut import Dut
from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean

import yaml
import os
import sys
sys.path.append(os.path.dirname(os.getcwd()))


class TestSim(unittest.TestCase):
    def setUp(self):
        
        cocotb_compile_and_run(
            [os.getcwd() + '/mca_tb.v', '/cadence/xilinx/14.7/ISE_DS/ISE/verilog/src/glbl.v'], 
            sim_bus='basil.utils.sim.SiLibUsbBusDriver',
            include_dirs = ('/cadence/xilinx/14.7/ISE_DS/ISE/verilog/src/unisims',),
            extra = 'export SIMULATION_MODULES='+yaml.dump({'MCAFileDriver' : {}})
            )
                
        cnfg = {}
        with open('../qmca.yaml', 'r') as f:
            cnfg = yaml.load(f)
            
        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        
        # this should be based on some search
        cnfg['transfer_layer'].remove(cnfg['transfer_layer'][1])
        cnfg['hw_drivers'].remove(cnfg['hw_drivers'][1])
        cnfg['hw_drivers'].remove(cnfg['hw_drivers'][0])
        
        cnfg['registers'].remove(cnfg['registers'][5])
        cnfg['registers'].remove(cnfg['registers'][4])
        cnfg['registers'].remove(cnfg['registers'][3])
        cnfg['registers'].remove(cnfg['registers'][2])
        cnfg['registers'].remove(cnfg['registers'][1])
        cnfg['registers'].remove(cnfg['registers'][0])
        
        self.chip = Dut(cnfg)
        self.chip.init()

    def test(self):
        self.assertEqual(True,False)
        
    def tearDown(self):
        self.chip.close()  # let it close connection and stop simulator
        cocotb_compile_clean()

if __name__ == '__main__':
    unittest.main()