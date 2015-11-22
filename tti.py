from basil.dut import Dut
import time


dut = Dut('tti.yaml')
dut.init()


print 'TTi = ', dut['TTi'].get_name()

dut['TTi'].off()
time.sleep(1)
dut['TTi'].on()