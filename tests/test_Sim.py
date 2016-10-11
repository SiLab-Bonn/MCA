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
import numpy as np
from tempfile import NamedTemporaryFile
import random
import time
import sys
qmca_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #../
sys.path.append( qmca_dir ) 

import qmca

np.set_printoptions(formatter={'int':hex})


class TestSim(unittest.TestCase):
    def generate_data(self):
        '''
        Generates events for simulation
        '''
        data = [[], [], [], []]
        outfile = NamedTemporaryFile(delete=False)
        
        self.sample_count = 400 # Total length of event
        self.sample_delay = 30  # Number of samples before rising edge / threshold crossing
        baseline = random.randint(500,1000)
        
        for c in range(4):
            for i in range(self.sample_count):
                if i < self.sample_delay:
                    val = baseline
                elif i < 70:
                    val = data[c][-1] + 275
                elif i < 180:
                    val = data[c][-1] - 100
                else:
                    val = baseline
                data[c].append(val)
                
            for i in range(len(data[c])):
                noise = random.randint(-500,500) 
                data[c][i] = data[c][i] + noise
                
        npdata = np.asarray(data)
        np.save(outfile, npdata)
        outfile.close()
        return outfile.name
            
    def setUp(self):
        self.file_name = self.generate_data()

        
        cocotb_compile_and_run(
            [qmca_dir + '/tests/mca_tb.v'], 
            sim_bus='basil.utils.sim.SiLibUsbBusDriver',
            include_dirs = (qmca_dir,),
            extra = 'export SIMULATION_MODULES='+yaml.dump({'MCAFileDriver' : {'file_name': str(self.file_name)}})
            )
                
        with open(qmca_dir + '/qmca.yaml', 'r') as f:
            cnfg = yaml.load(f)
            
        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        cnfg['hw_drivers'][0]['init']['no_calibration'] = True
        
        # this should be based on some search
        #cnfg['transfer_layer'].remove(cnfg['transfer_layer'][1])
        #cnfg['hw_drivers'].remove(cnfg['hw_drivers'][1])
        #cnfg['hw_drivers'].remove(cnfg['hw_drivers'][0])
        
        #cnfg['registers'].remove(cnfg['registers'][5])
        #cnfg['registers'].remove(cnfg['registers'][4])
        #cnfg['registers'].remove(cnfg['registers'][3])
        #cnfg['registers'].remove(cnfg['registers'][2])
        #cnfg['registers'].remove(cnfg['registers'][1])
        #cnfg['registers'].remove(cnfg['registers'][0])
        
        self.ch = 0 # Channel to use
        self.ev = 0 # Event to use
        self.th = 2500  # Threshold
        
        self.my_qmca = qmca.qmca(config=cnfg, channel=self.ch, sample_count=self.sample_count, sample_delay=self.sample_delay, threshold=self.th)

    def test(self):
        # Wait a while
        for _ in range(100):
            self.my_qmca.dut['DATA_FIFO'].get_size()
        
        # Record some events
        event_data = self.my_qmca._record_data()
        
        # Load the simulated event...
        start_data = np.load(self.file_name)
        # ... and shift it according to set threshold
        for i in range(start_data.shape[1]):
            if start_data[self.ch][i] >= self.th:
                break
        dly = i - self.sample_delay
        start_data_dly = start_data[self.ch][dly:]
        
        # Compare simulated and recorded events
        comp = (event_data[self.ev][:-dly] == start_data_dly)
        self.assertTrue(comp.all())
        
    def tearDown(self):
        self.my_qmca.dut.close()
        time.sleep(5)
        cocotb_compile_clean()

if __name__ == '__main__':
    unittest.main()