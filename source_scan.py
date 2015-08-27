import qmca
from basil.dut import Dut
import logging
import time
import progressbar

duration = 5000

dut = Dut('devices.yaml')
dut.init()
logging.info('Found Sourcemeter: ' + dut['Sourcemeter'].get_name())

my_qmca = qmca.qmca()

pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=duration, poll=10, term_width=80).start()

my_qmca.start()
start_time = time.time()
actual_time = start_time

while (actual_time < (start_time + duration)):
    pbar.update(actual_time - start_time)
    actual_time = time.time()
    time.sleep(1)

my_qmca.stop()
pbar.finish()