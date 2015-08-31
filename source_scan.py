import qmca
from basil.dut import Dut
import logging
import time
import progressbar

duration = 10


dut = Dut('devices.yaml')
dut.init()
logging.info('Found TTI: ' + dut['TTi'].get_name())
logging.info('Found Sourcemeter: ' + dut['Sourcemeter'].get_name())


bias_voltage = 30
current_limit = 0.000105
my_qmca = qmca.qmca(channel=1, threshold=2500)

pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=duration, poll=10, term_width=80).start()

#Powercycle TTI
dut['TTi'].off()
dut['TTi'].on()
time.sleep(1)

#Ramp up bias voltage
dut['Sourcemeter'].off()
dut['Sourcemeter'].set_voltage(0)
dut['Sourcemeter'].set_current_limit(current_limit)
dut['Sourcemeter'].on()
for v in range(0,bias_voltage):
    dut['Sourcemeter'].set_voltage(v)
    time.sleep(0.5)



my_qmca.start()
start_time = time.time()
actual_time = start_time

while (actual_time < (start_time + duration)):
    pbar.update(actual_time - start_time)
    actual_time = time.time()
    time.sleep(1)

my_qmca.stop()
pbar.finish()

#Ramp down bias voltage
for v in range(bias_voltage,0, -1):
    dut['Sourcemeter'].set_voltage(v)
    time.sleep(0.5)
    
dut['Sourcemeter'].off()