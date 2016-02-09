import datetime
import logging
import time
import sys
import csv
import matplotlib.pyplot as plt


class depletion_monitor():
    def __init__(self, devices, nwellring_current_limit=0.001, minimum_delay=0.1):
        self.devices = devices
        self.minimum_delay = minimum_delay
        
        logging.info('Depletion monitor started!')
        logging.info('bias_device is ', str(self.devices['bias'][0].get_name().rstrip()))
        logging.info('nwellring_device is ', str(self.devices['nwellring'][0].get_name().rstrip()))
        
        filestr = 'depletion_' + datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H:%M:%S')
        logfile =  filestr + '.log'
        self.datafile = filestr + '.csv'
        logging.basicConfig(filename=logfile, filemode='wb', level=logging.INFO, format="%(asctime)s - %(name)s - [%(levelname)-8s] (%(threadName)-10s) %(message)s")
        
        logging.info('Reset devices.')
        self.ramp_down()
        self.devices['nwellring'][0].set_current_limit(nwellring_current_limit)
        self.devices['bias'][0].set_current_limit(0.105)
        
    
    def get_current_reading(self, device):
        if device[1] == 'keithley_2410':
            return float(device[0].get_current().split(',')[1])
        
    def get_voltage_reading(self, device):
        if device[1] == 'keithley_2410':
            return float(device[0].get_voltage().split(',')[0])
    
    def ramp_down(self):
        logging.info('Ramping down all voltages...')
        done = {}
        for key in self.devices.keys():
            done[key] = False
            
        while True:
            for key in self.devices.keys():
                value = int(self.get_voltage_reading(self.devices[key]))
                if value != 0:
                    step = -1 if (value > 0) else 1
                    self.devices[key][0].set_voltage(value + step)
                else:
                    done[key] = True
            time.sleep(0.5)
            if all([dev for dev in done.itervalues()]):
                break
    
    def deplete(self, bias_voltage, polarity=1):
        self.bias_voltage = bias_voltage
        self.polarity = polarity
        
        try:        
            logging.info('Ramping up voltage')
            self.devices['bias'][0].on()
            self.devices['nwellring'][0].on()
            for v in range(0, polarity * (bias_voltage + 1), polarity):
                time.sleep(0.5)
                self.devices['bias'][0].set_voltage(v)
                self.devices['nwellring'][0].set_voltage(v)
        
        except Exception as e:
            logging.error(sys.exc_info()[0] + ': ' + e)
            logging.error('An error occurred! Ramping down Voltage!')
            self.ramp_down()
                
    def monitor_current(self, waittime=10, record_nwellcurrent=False):
        logging.info('Now monitoring current. Data file is ' + self.datafile)
        try:
            start = time.time()
            
            with open(self.datafile, 'wb') as outfile:
                dat = csv.writer(outfile ,quoting=csv.QUOTE_NONNUMERIC)
                if record_nwellcurrent:
                    dat.writerow(['Absolute time', 'Relative time [s]', 'Nwell current [A]', 'Current [A]'])
                else:
                    dat.writerow(['Absolute time', 'Relative time [s]', 'Current [A]'])
                
            data = []
            
            fig, axarr = plt.subplots(nrows=2, sharex=True)
            fig.canvas.set_window_title('Bias Current Monitor')
            plt.grid()
            plt.xlabel('Time [s]')
            plt.ylabel('Current [A]')
            
            plt.ion()
            plt.show()
            
            loop = 0
            while True:
                loop += 1
                event = []
                event.append(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'))
                event.append(time.time() - start)
                
                event.append(self.get_current_reading(self.devices['nwellring']))
                event.append(self.get_current_reading(self.devices['bias']))
                
                print event
                data.append(event)
                
                with open(self.datafile, 'a') as outfile:
                    dat = csv.writer(outfile ,quoting=csv.QUOTE_NONNUMERIC)
                    if record_nwellcurrent:
                        dat.writerow([event[0], event[1], event[2], event[3]])
                    else:
                        dat.writerow([event[0], event[1], event[3]])
                
                if loop > 2:
                    x,y1,y2 = [], [], []
                    for ev in data:
                        x.append(ev[1])
                        y1.append(ev[2])
                        y2.append(ev[3])
                          
                    
                    plt.cla()
                    fig.canvas.set_window_title('Bias Current Monitor')
                    axarr[0].set_title('Diode Current')
                    axarr[1].set_title('NWell Current')
                    axarr[0].xaxis.grid(True,'major')
                    axarr[0].yaxis.grid(True,'major')
                    axarr[1].xaxis.grid(True,'major')
                    axarr[1].yaxis.grid(True,'major')
                    axarr[1].set_xlabel('Time [s]')
                    axarr[0].set_ylabel('Current [A]')
                    axarr[1].set_ylabel('Current [A]')
                    
                    axarr[0].plot(x, y1, 'r-')
                    axarr[1].plot(x, y2, 'b-')
                    plt.pause(0.1)
                
                time.sleep(waittime)
            
        except Exception as e:
            logging.error(sys.exc_info()[0] + ': ' + e)
            logging.error('An error occurred! Ramping down Voltage!')
            self.ramp_down()
                
        except KeyboardInterrupt:
            logging.info('Interrupt detected! Ramping down voltage...')
            self.ramp_down()
            logging.info('Done. Shutting down.')

            
if __name__ == '__main__':
    import argparse
    from basil.dut import Dut
    
    parser = argparse.ArgumentParser(description='LF Diodes Depletion Monitor')
    parser.add_argument('-y', '--yaml', help='Sourcemeter YAML file', required=False, default='devices.yaml')
    parser.add_argument('-b', '--biasdev', help='Bias device name in YAML file', required=False, default='Sourcemeter2')
    parser.add_argument('-n', '--nwelldev', help='NWell ring device name in YAML file', required=False, default='Sourcemeter1')
    parser.add_argument('-v', '--voltage', help='Bias voltage', required=True)
    parser.add_argument('-r', '--recnwellcurrent', help='Record also the current to the NWellRing?', required=False, default='False')
    args = parser.parse_args()
    
    dut = Dut(args.yaml)
    dut.init()
    
    devices = {'bias':[dut[args.biasdev], 'keithley_2410'],
               'nwellring':[dut[args.nwelldev], 'keithley_2410']}
    
    mon = depletion_monitor(devices)
    
    mon.deplete(bias_voltage=int(args.voltage))
    mon.monitor_current(record_nwellcurrent=bool(args.recnwellcurrent))