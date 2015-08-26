from basil.dut import Dut
import numpy as np
import time
import zmq
import progressbar
import csv
import tables as tb

#np.set_printoptions(formatter={'int':hex})

def send_data(data, name='qMCA'):
    '''Sends the data of every read out via ZeroMQ to a specified socket
    '''
    try:
        data_meta_data = dict(
            name=name,
            dtype=str(data.dtype),
            shape=data.shape,
            thr = threshold
        )
        socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
        socket.send(data, flags=zmq.NOBLOCK)  # PyZMQ supports sending numpy arrays without copying any data
    except zmq.Again:
        pass

def record_data():
    # Read data from SRAM
    single_data = dut['DATA_FIFO'].get_data()
    #print single_data
    selection = np.where(single_data & 0x10000000 == 0x10000000)[0]
    event_data = np.bitwise_and(single_data, 0x00003fff).astype(np.uint32)
    event_data = np.split(event_data, selection)
    return event_data   

def set_threshold_and_channel(threshold, channel):
    dut['TH']['TH'] = int(threshold)
    dut['TH']['SEL_ADC_CH'] = channel
    dut['TH'].write()
    return

def set_adc(scount, delay):
    dut['fadc0_rx'].set_data_count(scount)
    dut['fadc0_rx'].set_single_data(True)
    dut['fadc0_rx'].set_delay(delay)
    dut['fadc0_rx'].set_en_trigger(True)
    return

    
if __name__ == '__main__':
    # Initialize BASIL DUT
    dut = Dut('qmca.yaml')
    dut.init()
    
    print "Found Sourcemeter: ", dut['Sourcemeter'].get_name()
    # Set up internal power supply    
    dut['PWR0'].set_current_limit(100, unit='mA')
    dut['PWR0'].set_voltage(1.8, unit='V')
    dut['PWR0'].set_enable(True)
    
    dut['PWR1'].set_current_limit(100, unit='mA')
    dut['PWR1'].set_voltage(1.8, unit='V')
    dut['PWR1'].set_enable(True)
    
    dut['PWR2'].set_current_limit(100, unit='mA')
    dut['PWR2'].set_voltage(1.8, unit='V')
    dut['PWR2'].set_enable(True)
    
    dut['PWR3'].set_current_limit(100, unit='mA')
    dut['PWR3'].set_voltage(1.8, unit='V')
    dut['PWR3'].set_enable(True)
    
    # Set dynamic range of differential ADC
    dut['VSRC3'].set_voltage(1.9, unit='V')
    
    # Settings
    scount = 200                        # Number of samples per event
    delay = 50                          # Number of samples before trigger
    threshold = 2000                    # Default discriminator threshold to define event
    duration = 60*20                    # Duration of the measurement in seconds
    filename = 'event_data.h5'          # h5 file name for data
    socket_addr='tcp://127.0.0.1:5678'  # address to send the data to
    
    # Clear FIFO and data-array
    dut['DATA_FIFO'].get_data()
    
    # Setup ZeroMQ socket    
    socket = zmq.Context().socket(zmq.PUSH)  # push data non blocking
    socket.bind(socket_addr)
    
    # Set ADC settings
    set_threshold_and_channel(threshold, 3) # Choose channel here
    set_adc(scount, delay)
    
    start_time = time.time()
    event_count = 0
    # Pull the FIFO data, split at events, and send/store every event data
    print("Now recording data for %d seconds..." % (duration))
    with tb.open_file(filename, 'w') as output_file:
        output_array = output_file.createEArray(output_file.root, name='event_data', atom=tb.UIntAtom(), shape=(0, 200), title='The raw data of the ADC', filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False))  # expectedrows = ???
        pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=duration, poll=10, term_width=80).start()
        while ((time.time() - start_time) < duration):
            pbar.update(time.time() - start_time)
            events_data = record_data()
            for event_data in events_data:
                if event_data.shape[0] == 200:
                    send_data(event_data)
                    output_array.append(event_data.reshape(1, 200))  # whatever...
                    event_count += 1
                    if (event_count % 1000 == 0):
                        output_array.flush()
        output_array.flush()
        pbar.finish()
    
    print("Done! Recorded %1i events." % event_count)
    print "Shutting down Sourcemeter..."    
    dut['Sourcemeter'].off()
    print "Done."
    
    