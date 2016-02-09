import qmca
import time
import progressbar

duration = 60*30
max_events = 1000000

my_qmca = qmca.qmca(channel=2,
                    threshold=6000,
                    sample_count=200,
                    sample_delay=50,
                    write_after_n_events=10000,
                    adc_differential_voltage=1.5)

pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=duration, poll=10, term_width=80).start()

start_time = time.time()
actual_time = start_time

my_qmca.start()
while ((actual_time < (start_time + duration)) and (my_qmca.event_count <= max_events)):
    pbar.update(actual_time - start_time)
    actual_time = time.time()
    time.sleep(1)

my_qmca.stop()
pbar.finish()
