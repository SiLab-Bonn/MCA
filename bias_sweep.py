import qmca
import depletion_monitor
from basil.dut import Dut
import time
import progressbar


bias_device = 'Sourcemeter1'
nwell_device = 'Sourcemeter2'

duration = 60*30
max_events = 10000000

bias_steps = range(0, 81, 10)



my_qmca = qmca.qmca(channel=2,
                    threshold=6000,
                    sample_count=200,
                    sample_delay=50,
                    write_after_n_events=10000,
                    adc_differential_voltage=1.5)


dut = Dut('devices.yaml')
dut.init()

devices = {'bias':[dut[bias_device], 'keithley_2410'],
           'nwellring':[dut[nwell_device], 'keithley_2410']}

mon = depletion_monitor(devices)

pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=duration*len(bias_steps), poll=10, term_width=80).start()

start_time = time.time()
actual_time = start_time

for bias_potential in bias_steps:
    mon.deplete(bias_potential)
    my_qmca.start()
    while ((actual_time < (start_time + duration)) and (my_qmca.event_count < max_events)):
        pbar.update(actual_time - start_time)
        actual_time = time.time()
        time.sleep(1)
    
    my_qmca.stop()
    mon.ramp_down()
    
    
pbar.finish()
