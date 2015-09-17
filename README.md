# MCA
Multi Channel Analyzer
This project provides firmware and software for the qMCA setup.


## General description
The analog data from the amplifiers of the four channels on the qMCA card is digitized via the FADCs on the GPAC. The FPGA then analyzes the data stream by means of a threshold. If the analog data crosses the threshold value, an event is defined for a specified amount of ADC samples around the crossing point. The events are then stored in the SRAM on the MIO board.
The SRAM is polled by the software via USB to read out the stored events. The maximum signal rate that can be read out by this mechanism is around 8 kHz with an event size of 200 samples.
The qmca class object regularly writes the recorded events to disk and also sends the data stream to the OnlineMonitor via ZeroMQ.

## Hardware
The qMCA setup consists of a MultiIO board, containing the FPGA and SRAM as well as the controller for USB communication, a General Purpose Analog Card (GPAC), which brings some voltage regulators and the 14 bit FADCs and the qMCA card, that holds the DUT socket and four analog amplifier chains. The MIO board can be powered over USB, though an external power supply is recommended. The GPAC can be powered by the MIO board and the qMCA card requires an external power supply at +-2.5V.
The qMCA card offers a high voltage circuit to supply bias voltage to the DUT. The analog output of the four channels is also easily accessible. It also features an injection circuit for testing the setup without DUT, as well as two additional auxiliary input/output connectors.   

## Firmware
TODO


## Software
### Initialization
On initialization, the qmca class object sets up the necessary power supplies on the GPAC card and sets the reference potential for the (differential) FADCs.
The input parameters are:
- 'sample_count' : A number that defines the length of every event in ADC samples. The default value is 200 samples.
- 'sample_delay' : A number that defines, how many samples before the threshold crossing should be used in every event. The default value is 50. With the default settings, an event will be 200 samples long, with 50 samples before the threshold crossing and 150 samples afterwards.
- 'threshold' : A number between 0 and 2^14 that defines the threshold by which an event is defined. The default value is 4000.
- 'channel' : A number between 0 and 3 that defines the channel number to be read out.
- 'socket_addr' : Defines the socket for the ZeroMQ data stream.
- 'write_after_n_events' : A number that defines, after how many recorded events the data is written to disk.

### Changing settings
The qmca class provides several methods to modify settings during runtime:
- 'set_threshold(threshold)' : Changes the threshold value.
- 'select_channel(channel)' : Changes the selected channel.
- 'set_adc_differential_voltage(value)' : Changes the reference potential for the differential ADCs.
- 'set_adc_eventsize(sample_count, sample_delay)' : Changes the total length ('sample_count') of an event or the number of samples to take before the threshold crossing ('sample_delay')

### Usage
After initialization, start the data acquisition by calling the 'start(out_filename)' method and optionally specifying the filename for the data file. The main loop for data acquisition, that caches the data, writes it to disk and sends it to the OnlineMonitor is launched in an extra thread, so the calling script will not be halted.
Options to monitor data acquisition are for example the elapsed time or the number of recorded events given by the class property 'event_count'.
After your requirements are met, stop the data acquisition by calling the 'stop()' method.