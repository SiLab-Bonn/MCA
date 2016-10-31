#
# ------------------------------------------------------------
# Copyright (c) All rights reserved 
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from basil.dut import Dut
import numpy as np
import time
import logging

np.set_printoptions(formatter={'int':hex})

dut = Dut('qmca.yaml')
dut.init()

dut['PWR0'].set_current_limit(100, unit='mA')
dut['PWR0'].set_voltage(1.8, unit='V')
dut['PWR0'].set_enable(True)

dut['fadc0_rx'].reset()
dut['fadc0_rx'].set_delay(10)
dut['fadc0_rx'].set_data_count(10)
dut['fadc0_rx'].set_single_data(True)
dut['fadc0_rx'].set_en_trigger(False)
    
dut['DATA_FIFO'].reset()

for i in range(10):
    pattern = 10 + i*100
    dut['FADC_CONF'].enable_pattern(pattern)  

    dut['fadc0_rx'].start()
    while not dut['fadc0_rx'].is_done():
        pass

    lost = dut['fadc0_rx'].get_count_lost()
    data = dut['DATA_FIFO'].get_data()   
    if data.tolist() != [pattern]*10 or lost !=0 :
        logging.error("Wrong or loot data :" + str(data))
    else:
        logging.info("OK Data:" + str(data) + " Lost: "+ str(lost) )

    
