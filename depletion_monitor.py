import datetime
import logging
import time
import sys
import csv
import matplotlib.pyplot as plt


class depletion_monitor():
    def __init__(self, dut, nwellring_device, bias_device, nwellring_current_limit=0.001, minimum_delay=0.1):
        self.dut = dut
        self.nwellring_device = nwellring_device
        self.bias_device = bias_device
        self.minimum_delay = minimum_delay
        
        logging.info('Depletion monitor started!')
        logging.info('bias_device is ', str(self.dut[self.bias_device].get_name().rstrip()))
        logging.info('nwellring_device is ', str(self.dut[self.nwellring_device].get_name().rstrip()))
        
        filestr = 'depletion_' + datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H:%M:%S')
        logfile =  filestr + '.log'
        self.datafile = filestr + '.csv'
        logging.basicConfig(filename=logfile, filemode='wb', level=logging.INFO, format="%(asctime)s - %(name)s - [%(levelname)-8s] (%(threadName)-10s) %(message)s")
        
        logging.info('Reset devices.')
        self.dut[self.nwellring_device].off()
        self.dut[self.bias_device].off()
        time.sleep(minimum_delay)
        self.dut[self.nwellring_device].set_voltage(0)
        self.dut[self.bias_device].set_voltage(0)
        time.sleep(minimum_delay)
        self.dut[self.nwellring_device].set_current_limit(nwellring_current_limit)
        self.dut[self.bias_device].set_current_limit(0.105)
    
    def deplete(self, bias_voltage=30, polarity=1):
        self.bias_voltage = bias_voltage
        self.polarity = polarity
        
        try:
            time.sleep(self.minimum_delay)
            self.dut[self.nwellring_device].on()
            self.dut[self.bias_device].on()
            time.sleep(self.minimum_delay)
        
            logging.info('Ramping up voltage')
            for v in range(0, polarity * bias_voltage + 1, polarity * 5):
                time.sleep(self.minimum_delay*10)
                self.dut[self.nwellring_device].set_voltage(v)
                
            logging.info('Depleted to %d V. Starting monitoring.' % v)
                
        
        except Exception as e:
            logging.error(sys.exc_info()[0] + ': ' + e)
            logging.error('An error occurred! Ramping down Voltage!')
            for v in range(self.bias_voltage, self.polarity * -1, self.polarity * -1 * 5):
                time.sleep(self.minimum_delay)
                self.dut[self.nwellring_device].set_voltage(v)
                
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
                
                event.append(float(self.dut[self.nwellring_device].get_current().split(',')[1]))
                event.append(float(self.dut[self.bias_device].get_current().split(',')[1]))
                
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
                        y1.append(ev[3])
                        y2.append(ev[2])
                          
                    
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
            for v in range(self.bias_voltage, self.polarity * -1, self.polarity * -1 * 5):
                time.sleep(self.minimum_delay)
                self.dut[self.nwellring_device].set_voltage(v)
                
        except KeyboardInterrupt:
            logging.info('Interrupt detected! Ramping down voltage...')
            for v in range(self.bias_voltage, self.polarity * -1, self.polarity * -1 * 5):
                time.sleep(self.minimum_delay)
                self.dut[self.nwellring_device].set_voltage(v)
            logging.info('Done. Shutting down.')

            
if __name__ == '__main__':
    import argparse
    from basil.dut import Dut
    
    parser = argparse.ArgumentParser(description='LF Diodes Depletion Monitor')
    parser.add_argument('-y', '--yaml', help='Sourcemeter YAML file', required=False, default='devices.yaml')
    parser.add_argument('-b', '--biasdev', help='Bias device name in YAML file', required=False, default='Sourcemeter2')
    parser.add_argument('-n', '--nwelldev', help='NWell ring device name in YAML file', required=False, default='Sourcemeter1')
    parser.add_argument('-v', '--voltage', help='Bias voltage', required=True)
    parser.add_argument('-r', '--recnwellcurrent', help='Record also the total current?', required=False, default='False')
    args = parser.parse_args()
    
    dut = Dut(args.yaml)
    dut.init()
    
    mon = depletion_monitor(dut, args.nwelldev, args.biasdev)
    
    mon.deplete(bias_voltage=int(args.voltage))
    mon.monitor_current(record_nwellcurrent=bool(args.recnwellcurrent))