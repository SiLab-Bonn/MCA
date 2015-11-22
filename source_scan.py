import qmca
from basil.dut import Dut
import time
import progressbar

duration = 60*60
max_events = 1000000
bias_voltage = 30
current_limit = 0.000105
my_qmca = qmca.qmca(channel=1,
                    threshold=3000,
                    sample_count=200,
                    sample_delay=50,
                    write_after_n_events=1000000,
                    adc_differential_voltage=1.5)

pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=duration, poll=10, term_width=80).start()

start_time = time.time()
actual_time = start_time

my_qmca.start()

# print 'event_count is %d' % my_qmca.event_count

while ((actual_time < (start_time + duration)) and (my_qmca.event_count <= max_events)):
# while True:
#     print 'event_count is %d' % my_qmca.event_count
    pbar.update(actual_time - start_time)
    actual_time = time.time()
    time.sleep(1)

my_qmca.stop()
pbar.finish()

#Ramp down bias voltage
# for v in range(bias_voltage,0, -1):
#     dut['Sourcemeter'].set_voltage(v)
#     time.sleep(0.5)
#     
# dut['Sourcemeter'].off()