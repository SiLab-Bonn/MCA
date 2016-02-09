import qmca
import depletion_monitor
import plotter
from basil.dut import Dut
import time
import progressbar
import logging


bias_device = 'Sourcemeter1'
nwell_device = 'Sourcemeter2'

duration = 10#60*30
max_events = 10000000

devicename = 'DeviceA'
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

mon = depletion_monitor.depletion_monitor(devices)
plotter = plotter.qmca_plotter()
pbar = progressbar.ProgressBar(widgets=['',
                                        progressbar.Percentage(),
                                        ' ',
                                        progressbar.Bar(marker='*', left='|', right='|'),
                                        ' ',
                                        progressbar.AdaptiveETA()],
                               maxval=len(bias_steps)*duration,
                               poll=10,
                               term_width=80).start()
                               
                               
try:
    j = 0
    for bias_potential in bias_steps:
        out_filename = 'eventData_%s_bias=%sV' % (devicename, bias_potential)
        mon.deplete(bias_potential)
        
        start_time = time.time()
        actual_time = start_time
    
        logging.info('Now measuring %s at %i V bias potential' % (devicename, bias_potential))
        my_qmca.start(out_filename=out_filename)
        while (((actual_time - start_time) < duration) and (my_qmca.event_count < max_events)):
            actual_time = time.time()
            pbar.update(j)
            j += 1
            time.sleep(1)
        
        my_qmca.stop()
        
        plotter.clear_plot()
        plotter.plot_data_file(out_filename + '.h5', title=('%s - Bias = %iV' % (devicename, bias_potential)))
    
    pbar.finish()
except Exception as e:
    logging.error(e)
    mon.ramp_down()
