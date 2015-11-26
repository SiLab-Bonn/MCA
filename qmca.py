#
# ------------------------------------------------------------
# Copyright (c) All rights reserved 
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import threading
from basil.dut import Dut
import numpy as np
import zmq
import tables as tb
import logging

np.set_printoptions(formatter={'int':hex})

class qmca(object):    
    '''Sets up qMCA setup. Reads data via USB from qMCA setup and sends it via ZeroMQ to Online Monitor.
    8000 Hz of waveforms with 200 samples can be read out'''    
    
    def __init__(self, config='qmca.yaml', sample_count=200, sample_delay=50, threshold=2000, channel=0, adc_differential_voltage=1.9, socket_addr='tcp://127.0.0.1:5678', write_after_n_events = 100000):
        '''
        Parameters
        ----------
        sample_count : int
            Length of event in ADC samples
        sample_delay : int
            Number of ADC samples to add to event before detected peak
        threshold : int [0:2**14]
            ADC threshold
        channel : int [0:3]
            qMCA channel number
        outfile_name : string
            Filename of the raw data output file
        socket_addr : string
            Socket address of Online Monitor
        '''
        
        self.event_count = 0
        self.count_lost = 0
        self.main_thread = None
        self.exit = threading.Event()
        self.write_after_n_events = write_after_n_events
        self.sample_count = sample_count
        self.sample_delay = sample_delay
        
        # Setup ZeroMQ socket    
        self.socket = zmq.Context().socket(zmq.PUSH)
        self.socket.bind(socket_addr)
        
        # Setup Dut
        self.dut = Dut(config)
        self.dut.init()
        
        self.dut['PWR0'].set_current_limit(100, unit='mA')
        self.dut['PWR0'].set_voltage(1.8, unit='V')
        self.dut['PWR0'].set_enable(True)
        
        self.dut['PWR1'].set_current_limit(100, unit='mA')
        self.dut['PWR1'].set_voltage(1.8, unit='V')
        self.dut['PWR1'].set_enable(True)
        
        self.dut['PWR2'].set_current_limit(100, unit='mA')
        self.dut['PWR2'].set_voltage(1.8, unit='V')
        self.dut['PWR2'].set_enable(True)
        
        self.dut['PWR3'].set_current_limit(100, unit='mA')
        self.dut['PWR3'].set_voltage(1.8, unit='V')
        self.dut['PWR3'].set_enable(True)
        
        # Reset ADC and SRAM
        self.dut['fadc0_rx'].reset()
        self.dut['DATA_FIFO'].reset()
        
        self.adc_differential_voltage = adc_differential_voltage
        self.set_adc_differential_voltage(adc_differential_voltage)
        self.set_adc_eventsize(self.sample_count, self.sample_delay)
        self.set_threshold(threshold)
        self.select_channel(channel)

    
    def start(self, out_filename='event_data'):
        self.out_filename = out_filename + '.h5'
        
        logging.info('Starting main loop in new thread.')
        self.main_thread = threading.Thread(target=self._main_loop)
        self.main_thread.start()
    
    def stop(self):
        self.exit.set()
        if self.main_thread:
            self.main_thread.join(timeout=1)
            self.main_thread = None
            logging.info('Measurement stopped. Recorded %i events.' % self.event_count)
        else:
            logging.info('No measurement was running.')

    def reset_dut(self):
        self.dut['fadc0_rx'].reset()
        self.dut['DATA_FIFO'].reset()
        
        self.set_adc_differential_voltage(self.adc_differential_voltage)
        self.set_adc_eventsize(self.sample_count, self.sample_delay)
        
        self.event_count = 0
        self.count_lost = 0
        self.main_thread = None

    def set_threshold(self, threshold):
        self.dut['TH']['TH'] = int(threshold)
        self.dut['TH'].write()
        self.threshold = threshold
    
    def select_channel(self, channel):
        self.dut['TH']['SEL_ADC_CH'] = channel
        self.dut['TH'].write()
        self.channel = channel
        
    def set_adc_differential_voltage(self, value):
        self.adc_differential_voltage = value
        self.dut['VSRC3'].set_voltage(value, unit='V')
        
    def set_adc_eventsize(self, sample_count, sample_delay):
        self.dut['fadc0_rx'].set_delay(sample_delay)
        self.dut['fadc0_rx'].set_data_count(sample_count)
        self.dut['fadc0_rx'].set_single_data(True)
        self.dut['fadc0_rx'].set_en_trigger(True)
        
        self.sample_count = sample_count
        self.sample_delay = sample_delay
    
    def _send_data(self, data, name='qMCA'):
        try:
            data_meta_data = dict(
                name=name,
                dtype=str(data.dtype),
                shape=data.shape,
                thr = self.threshold,
                ch = self.channel
            )
            self.socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
            self.socket.send(data, flags=zmq.NOBLOCK)                           # PyZMQ supports sending numpy arrays without copying any data
        except zmq.Again:
            pass

    def _record_data(self):
        '''
            Reads raw event data from SRAM and splits data stream into events
            ----------
            Returns:
                event_data : np.ndarray
                    Numpy array of single event numpy arrays 
        '''
        
        self.count_lost = self.dut['fadc0_rx'].get_count_lost()
#         print 'count_lost is %d' % self.count_lost
#         print 'event_count is %d' % self.event_count
        if self.count_lost > 0:
            logging.error('SRAM FIFO overflow number %d. Skip data.', self.count_lost)
            self.dut['fadc0_rx'].reset()
            self.set_adc_eventsize(self.sample_count, self.sample_delay)
            #return
        
        single_data = self.dut['DATA_FIFO'].get_data()                          # Read raw data from SRAM
        
        try:
            if single_data.shape[0] > 200:
                selection = np.where(single_data & 0x10000000 == 0x10000000)[0]         # Make mask from new-event-bit
                event_data = np.bitwise_and(single_data, 0x00003fff).astype(np.uint32)  # Remove new-event-bit from data       
                event_data = np.split(event_data, selection)                            # Split data into events by means of mask
                event_data = event_data[1:-1]                                           # Remove first and last event in case of chopping
                event_data = np.vstack(event_data)                                      # Stack events together
            else:
                event_data = np.asarray([np.bitwise_and(single_data, 0x00003fff).astype(np.uint32)])

            if event_data.shape[1] == self.sample_count:
                return event_data
        except ValueError as e:
            logging.error('_record_data() experienced a ValueError: ' + str(e))
            return


    def _main_loop(self):
        logging.info('Beginning measurement. Please open Online Monitor.')
        last_mod_value = 0
        with tb.open_file(self.out_filename, 'w') as self.output_file:
            output_array = self.output_file.createEArray(self.output_file.root, name='event_data', atom=tb.UIntAtom(), shape=(0, self.sample_count), title='The raw events from the ADC', filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False))
            while not self.exit.wait(0.01):
                events_data = self._record_data()
                
                if np.any(events_data):
                    self._send_data(events_data)
                    try:
                        output_array.append(events_data)
                    except ValueError:
                        print events_data, events_data.shape
                    self.event_count += events_data.shape[0]
                    if (self.event_count % self.write_after_n_events < last_mod_value):
                        logging.info('Recorded %d events. Write data to disk.', self.write_after_n_events)
                        output_array.flush()
                    last_mod_value = self.event_count % self.write_after_n_events
            
            output_array.flush()