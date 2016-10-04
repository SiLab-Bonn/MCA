import tables
import numpy as np
import os
import csv
from collections import deque
from scipy.optimize import curve_fit
import pylandau as landau
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import logging
import progressbar

class MCA_analysis(object):
    '''
        Collection of methods for analysis of LF Diode Teststructure data obtained via qMCA setup
        Parameters:
            outformat:string    -    [Optional] Format of saved plots. Default value is 'pdf'.
    '''
    def __init__(self, outformat='pdf'):
        self.outformat = outformat
        self.event_count = 0
        self.errorfiles = []
        self.error = False
        self._energy_calibrated = False
        self._darkframe_corrected = False
        self._energy_slope = 0
        self._energy_intercept = 0
        self._energy_unit = 'ADC channels'
        self.outfile= ''
    
    
    def load_data_file(self, path):
        '''
            Reads a h5 data file to memory
            Parameters:
                path:string    -    Full path to input h5 file
            Returns:
                data:np.ndarray    -    Numpy array of numpy arrays containing all waveforms from path
        '''
        if not os.path.split(path)[1].split('.')[1] == 'h5':
            raise IOError('Wrong filetype!')
        self.dirpath = os.path.split(path)[0]
        self.f = os.path.split(path)[1]
        self.title = self._make_title(os.path.split(path)[1].split('.')[0])
        self.outfile = os.path.join(os.path.split(path)[0], (os.path.split(path)[1].split('.')[0]))
        self._energy_calibrated = False
        self._darkframe_corrected = False
        with tables.open_file(path, 'r') as infile:
            try:
                data = infile.root.event_data[:]
            except tables.exceptions.HDF5ExtError:
                logging.error('HDF5ExtError: Blosc decompression error! Omitting last 100 events...')
                data = infile.root.event_data[:-100]
            
        self.event_count = len(data)
        logging.debug('Event count is: %i' % self.event_count)
        return data
    
    
    def _make_title(self, filename):
        '''
            Parse title for plot from data file name
            Parameters:
                filename:string    -    Filename of the data file
            Returns:
                title:string       -    Filename of the output file
        '''
        pcb, structure, bias, add = 'PCB?', 'Structure?', '?V Bias', ''
        f_arr = filename.split('_')
        for p in f_arr:
            if 'PCB' in p or 'Board' in p or 'board' in p:
                pcb = p
            elif 'Structure' in p or 'structure' in p or 'Device' in p or 'device' in p or 'Diode' in p or 'diode' in p:
                structure = 'Structure' + p[-1]
            elif 'HV' in p:
                try:
                    bias_value = p.split('=')[1]
                except:
                    bias_value = '?'
                bias = bias_value + ' Bias'
            elif 'nwell' in p:
                add = p
            elif 'Am241' in p:
                if add:
                    add += ', Am241 spectrum'
                else:
                    add = 'Am241 spectrum'
            elif 'Tb' in p:
                if add:
                    add += ', Tb spectrum'
                else:
                    add = 'Tb spectrum'
            elif 'Ba133' in p:
                if add:
                    add += ', Ba133 spectrum'
                else:
                    add = 'Ba133 spectrum'
        
        if '?' in pcb:
            pcb = ''
        
        ret =  pcb + ' ' + structure + ' at ' + bias
        if add:
            ret = ret + ' (' + add + ')'
        
        return ret
    
    
    def _apply_multiplicator(self, y, multi=None):
        '''
            Apply multiplicator to y-values to plot y-axis e.g. in uA
            Parameters:
                y:np.ndarray    -    Original y-values to apply multiplicator to.
                multi:float     -    Possibility to override global multiplicator.
            Returns:
                y:np.ndarray    -    New y-values with applied multiplicator.
        '''
        if multi is not None:
            self.multi = multi
        return np.array([v*self.multi for v in y])
    
    
    def just_plot_waveform(self, y, threshold):
        '''
            Simply plot a single waveform from qMCA data.
            Parameters:
                y:np.ndarray     -    y-values of waveform.
                threshold:int    -    Threshold of qMCA setup when waveform was taken.
        '''
        x = np.arange(len(y))
        
        plt.cla()
        plt.plot(x, y, label='Data', color='blue', zorder=0, linewidth=1)
        plt.fill_between(x, y, facecolor='blue', alpha=0.3, zorder=0)


        plt.ylim(0, 2**14)
        plt.grid()
        plt.title(self.title)
        plt.xlabel('Time [ADU]')
        plt.ylabel('Amplitude [ADC channels]')
        
        plt.axhline(y=threshold, color='black', linestyle='--')
        
        ax = plt.axes()
        ax.annotate('Threshold', xy=(0.9*x[-1], threshold), xytext=(0.9*x[-1], 1.15*threshold), horizontalalignment='center', arrowprops=dict(facecolor='black', shrink=0.05, width=0, headwidth=0))
        
        plt.savefig(self.outfile + '_waveform.' + self.outformat)


    def overlay_waveforms(self, x, data, n_max=1000, cut=2**14, color='blue', filename=None):
        '''
            Overlay many waveforms with low opacity to identify dysfunction of qMCA.
            Parameters:
                data:np.ndarray    -    Numpy array of numpy arrays containing waveforms.
                n_max:int          -    [Optional] Maximum number of waveforms to plot for performance reasons. n_max=None plots all waveforms in data.
                cut:int            -    [Optional] Maximum amplitude. Waveforms with amplitude > cut are not included into the plot.
        '''
        _, histy = self.histogram_data(data)
        threshold = self.find_threshold(histy)
        
        if n_max is None:
            alp = 100./len(data)
        else:
            alp = 100./n_max
        
        plt.cla()
        n=0
        for event in data:
            if np.amax(event) < cut:
                plt.plot(x, event, color=color, zorder=0, linewidth=1, alpha=alp)
                n += 1
            if n_max is not None and n == n_max:
                break
        
        plt.ylim(0, 2**14)
        plt.grid()
        plt.title(self.title)
        plt.xlabel('Time [ADU]')
        plt.ylabel('Amplitude [ADC channels]')
        
        plt.axhline(y=threshold, color='black', linestyle='--')
        
        ax = plt.axes()
        ax.annotate('Threshold', xy=(0.9*x[-1], threshold), xytext=(0.9*x[-1], 1.15*threshold), horizontalalignment='center', arrowprops=dict(facecolor='black', shrink=0.05, width=0, headwidth=0))
        
        if not filename:
            outfile = self.outfile + '_waveforms.' + self.outformat
        else:
            outfile = filename
        plt.savefig(outfile)
    
    
    def substract_darkframe(self, y, datafile):
        '''
            Reads a darkframe from the h5 file, histograms the waveforms and substracts the histogram from the data.
            Parameters:
                y:np.ndarray       -    Histogram y-values of the data.
                datafile:string    -    Full path to darkframe h5 file.
            Returns:
                y:np.ndarray       -    Difference of histogram y-values and darkframe histogram y-values.
        '''
        if not os.path.split(datafile)[1].split('.')[1] == 'h5':
            raise IOError('Wrong filetype!')
        with tables.open_file(datafile, 'r') as infile:
            darkframe_data = infile.root.event_data[:]
            
        logging.debug('Darkframe correction successful!')
        self._darkframe_corrected = True
        _, darkframe = self.histogram_data(darkframe_data)
        return np.array([v if v > 0 else 0 for v in (y - darkframe)])
        
        
    def correct_baseline(self, data):
        self.outfile += '_baselineCorrected'
        new_data = []
        baselines = []
        for wave in data:
            new_wave = []
            baseline = np.round(np.mean(wave[:40]))
            baselines.append(baseline)

            for sample in wave:
                new_wave.append(int(sample - baseline))
            
            if np.amax(wave) < 2**14-1:
                new_data.append(np.array(new_wave))
        
        logging.debug('Mean baseline was at %i' % np.mean(baselines))
        plt.hist(baselines, 50)
        plt.xlabel('Baseline [ADC]')
        plt.ylabel('#')
        plt.grid()
        plt.savefig('baseline_histogram.pdf')
        
        return np.array(new_data)
        
        
    def histogram_data(self, data, bins=1024, hist_range=(0, 2**14-10)):
        '''
            Histograms a set of waveforms.
            Parameters:
                data:np.ndarray     -    Numpy array of numpy arrays containing all waveforms.
                bins:int            -    [Optional] Number of bins in the histogram.
                hist_range:tuple    -    [Optional] Minimum and maximum label of x-axis of the histogram.
            Returns:
                x:np.ndarray        -    Bin edges of histogram.
                y:np.ndarray        -    Histogrammed amplitudes per bin.
        '''
        hist, edges = np.histogram(np.amax(data, axis=1), bins=bins, range=hist_range)
        return edges[:-1], hist
       
       
    def calibrate_energy(self, x, m, b, unit):
        '''
            Perform energy calibration of histogrammed data.
            Parameters:
                x:np.ndarray    -    x-values of histogrammed data in ADC channels.
                m:float         -    Slope in energy_unit/ADC channel as obtained from energy calibration.
                b:float         -    Intercept in energy_unit as obtained from energy calibration.
                unit:string     -    Name of new energy unit (e.g. Electrons / keV) to be used in axis labels.
            Returns:
                x:np.ndarray    -    x-values of histogrammed data in new energy unit.
        '''
        self._energy_calibrated = True
        self._energy_slope = m
        self._energy_intercept = b
        self._energy_unit = unit
        self.outfile += '_calibrated'
        return np.array([m*newx+b for newx in x])


    def _fitfunction_testbeam(self, x, *p):
        '''
            Custom fit function for testbeam histograms.
        '''
        mu, eta, sigma, A, p4, p5 = p
        return landau.langau(x, mu, eta, sigma, A) + p4*np.exp(-x/p5)
    
    
    def _fitfunction_source(self, x, *p):
        '''
            Custom fit function for sourcescan histograms.
        '''
        #mu1, sigma1, A1, mu2, sigma2, A2, mu3, sigma3, A3, m, b = p
        #return  A1*np.exp(-(x-mu1)**2/(2*sigma1**2)) + A2*np.exp(-(x-mu2)**2/(2*sigma2**2))+ A3*np.exp(-(x-mu3)**2/(2*sigma3**2)) + m*x+b
        
        mu, sigma, A = p
        return A*np.exp(-(x-mu)**2/(2*sigma**2))
    
    
    def find_threshold(self, y, condition=90):
        '''
            Automatically finds used threshold of histogrammed data.
            Parameters:
                y:np.ndarray       -    y-values of histogrammed data.
                condition:int    -    At the threshold, the y-value rises by this factor within 2 bins.
            Returns:
                threshold:int      -    Threshold energy in the same unit as x-values.
        '''
        threshold = 0      
        for i in range(0,len(y)):
            if y[i]/condition > y[i-2]:
                threshold = i*16
                break
        if threshold == 0:
            logging.error('Could not determine threshold!')
            self.errorfiles.append([os.path.join(self.dirpath, self.f), 'Could not determine threshold!'])
            #self.error = True
        else:
            threshold = int(round(threshold/500.0) * 500.0)
            if self._energy_calibrated:
                threshold = self._energy_slope*threshold + self._energy_intercept
            logging.debug('Automatically found threshold: %i' % threshold)
        return threshold
    
    
    def just_plot_histogram(self, x, y, ymax=None):
        '''
            Plots histogrammed data without any fitting or further analysis.
            Parameters:
                x:np.ndarray        -    x-values of histogrammed data.
                y:np.ndarray        -    y-values of histogrammed data.
                ymax:int            -    [Optional] Maximum of y-axis of plot. Obtained automatically if None.
        '''
        threshold = self.find_threshold(y)
        plot_range = (threshold, np.round(np.amax(x)))
        
        if ymax is None:
            ymax = 1.1*np.amax(y)
            
        plt.cla()
        plt.plot(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], label='Data', color='blue', zorder=0, linewidth=1)
        plt.fill_between(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], facecolor='blue', alpha=0.3, zorder=0)
        
        if self._energy_calibrated:
            plt.xlim(self._energy_intercept,np.round(np.amax(x)))
        else:
            plt.xlim(0, np.round(np.amax(x)))
        plt.ylim(0, ymax)
        plt.grid()
        plt.title(self.title)
        plt.xlabel('Energy [%s]' % self._energy_unit)
        plt.ylabel('Count')
            
        ax = plt.axes()
        ax.annotate('Threshold', xy=(threshold,0), xytext=(threshold,-0.1*ymax), horizontalalignment='center', arrowprops=dict(facecolor='black', shrink=0.05, width=0, headwidth=0))
        textstr = '$N = %i$' % self.event_count
        if self._darkframe_corrected:
            textstr += '\nCorrected via darkframe'
        box = AnchoredText(textstr, loc=5)
        ax.add_artist(box)
        
        plt.savefig(self.outfile + '.' + self.outformat)
        
        
    def fit_langau(self, x, y, p0, fit_range, ymax=None, debug=False):
        '''
            Fit a simple langau function only to peak of arbitrary spectrum and plot both data and fitted function.
            Parameters:
                x:np.ndarray       -    x-values of histogrammed data.
                y:np.ndarray       -    y-values of histogrammed data.
                p0:tuple           -    Set of startparameters for fit. Format: (mu, eta, sigma, A).
                fit_range:tuple    -    Approximate region of peak where the fit should be performed.
                ymax:int           -    [Optional] Maximum of y-axis of plot. Obtained automatically if None.
                debug:boolean      -    [Optional] If set, the fitfunction is plotted with startparameters for debugging.
        '''
        self.error = False
        threshold = self.find_threshold(y)
        plot_range = (threshold, np.round(np.amax(x)))
        
        if fit_range is None:
            fit_range = (threshold, np.round(np.amax(x)))
        if ymax is None:
            ymax = 1.1*np.amax(y)
        
        try:
            p, _ = curve_fit(landau.langau, x[(x > fit_range[0]) & (x < fit_range[1])], y[(x > fit_range[0]) & (x < fit_range[1])], p0=p0)
            if debug:
                p = p0
        except RuntimeError as e:
            logging.error('Encountered an error during analysis of file %s: %s' % (os.path.join(self.dirpath, self.f), e))
            self.errorfiles.append([os.path.join(self.dirpath, self.f), e])
            self.error = True
            p = p0

        if p[3] <= 0:
            logging.error('Encountered an error during analysis of file %s: Amplitude is negative!' % (os.path.join(self.dirpath, self.f)))
            self.errorfiles.append([os.path.join(self.dirpath, self.f), 'Fit: Amplitude is negative!'])
            self.error = True
            p = p0
        
        p = tuple([abs(e) for e in p])
        
        logging.debug('Fitparameters:\nmu = %1.3f\neta = %1.3f\nsigma = %1.3f\nA = %1.3f' % tuple(p))
        
        plt.cla()
        plt.plot(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], label='Data', color='blue', zorder=0, linewidth=1)
        plt.fill_between(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], facecolor='blue', alpha=0.3, zorder=0)
        plt.plot(x[(x > fit_range[0]) & (x < fit_range[1])], landau.langau(x, *p)[(x > fit_range[0]) & (x < fit_range[1])], label='Fit', color='red', zorder=2, linewidth=1)
        
        if self._energy_calibrated:
            plt.xlim(self._energy_intercept,np.round(np.amax(x)))
        else:
            plt.xlim(0,np.round(np.amax(x)))
        plt.ylim(0,ymax)
        plt.legend(loc=1, fontsize=12)
        plt.grid()
        plt.title(self.title)
        plt.xlabel('Energy [%s]' % self._energy_unit)
        plt.ylabel('Count')
        
        ax = plt.axes()
        textstr = '$N = %i$' % self.event_count
        if self._darkframe_corrected:
            textstr += '\nDarkframe-cor.'
        if self.error:
            textstr += '\nFit failed!'
        else:
            textstr += '\nFit parameters:\n$\mu=%.2f$\n$\eta=%.2f$\n$\sigma=%.2f$\n$A=%.2f$' % (p)
        box = AnchoredText(textstr, loc=5)
        ax.add_artist(box)
        ax.annotate('Threshold', xy=(threshold,0), xytext=(threshold,-0.1*ymax), horizontalalignment='center', arrowprops=dict(facecolor='black', shrink=0.05, width=0, headwidth=0))
        
        plt.savefig(self.outfile + '.' + self.outformat)
        
        
    def fit_source_spectrum(self, x, y, p0, fit_range=None, ymax=None, debug=False):
        '''
            Fit custom fitfunction to spectrum from sourcescan and plot both data and fitted function.
            Parameters:
                x:np.ndarray       -    x-values of histogrammed data.
                y:np.ndarray       -    y-values of histogrammed data.
                p0:tuple           -    Set of startparameters for fit. Format: (mu, eta, sigma, A).
                fit_range:tuple    -    [Optional] Region where the fit should be performed. Obtained automatically if None.
                ymax:int           -    [Optional] Maximum of y-axis of plot. Obtained automatically if None.
                debug:boolean      -    [Optional] If set, the fitfunction is plotted with startparameters for debugging.
        '''
        self.error = False
        threshold = self.find_threshold(y)
        if not fit_range or fit_range == 'auto':
            fit_range = (threshold, np.round(np.amax(x)))
        if ymax is None:
            ymax = 1.1*np.amax(y)
        
        plot_range = (threshold, np.round(np.amax(x)))

        try:
            p, _ = curve_fit(self._fitfunction_source, x[(x > fit_range[0]) & (x < fit_range[1])], y[(x > fit_range[0]) & (x < fit_range[1])], p0=p0)
            logging.debug('Fit successful! Parameters:')
            
            if debug:
                p = p0
                
            if p[0] <= threshold:
                logging.error('Encountered an error during analysis of file %s: Peak is below threshold!' % (os.path.join(self.dirpath, self.f)))
                self.errorfiles.append([os.path.join(self.dirpath, self.f), 'Fit: Peak below threshold!'])
                self.error = True
        except RuntimeError as e:
            logging.error('Encountered an error during analysis of file %s: %s' % (os.path.join(self.dirpath, self.f), e))
            self.errorfiles.append([os.path.join(self.dirpath, self.f), e])
            self.error = True
        
        if self.error:
            p = p0
        else:
            if len(p) == 5:
                p = tuple([abs(e) for e in p])
            elif len(p) == 7:
                p = tuple([abs(e) for e in p[:-2]]) + (p[5], p[6])
        
        if len(p) == 5:
            logging.debug('Fitparameters:\nmu = %1.3f\nsigma = %1.3f\nA = %1.3f\np4 = %1.3f\np5 = %1.3f' % (p))
        elif len(p) == 7:
            logging.debug('Fitparameters:\nmu = %1.3f\nsigma = %1.3f\nA = %1.3f\np4 = %1.3f\np5 = %1.3f\nm = %1.3f\nb = %1.3f' % (p))
        else:
            str = 'Fitparamters:'
            for i, pa in enumerate(p):
                str += '\np%i = %1.3f' % (i, pa)
            logging.debug(str) 
        
        plt.cla()
        plt.plot(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], label='Data', color='blue', zorder=0, linewidth=1)
        plt.fill_between(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], facecolor='blue', alpha=0.3, zorder=0)
        plt.plot(x[(x > fit_range[0]) & (x < fit_range[1])], self._fitfunction_source(x, *p)[(x > fit_range[0]) & (x < fit_range[1])], label='Fit', color='red', zorder=2, linewidth=1)
        
        if self._energy_calibrated:
            plt.xlim(self._energy_intercept, np.round(np.amax(x)))
        else:
            plt.xlim(0, np.round(np.amax(x)))
        plt.ylim(0, ymax)
        plt.legend(loc=1, fontsize=12)
        plt.grid()
        plt.title(self.title)
        plt.xlabel('Energy [%s]' % self._energy_unit)
        plt.ylabel('Count')
        
        ax = plt.axes()
        textstr = '$N = %i$' % self.event_count
        if self._darkframe_corrected:
            textstr += '\nDarkframe-cor.'
        if self.error:
            textstr += '\nFit failed!'
        else:
            if len(p) == 5:
                textstr += '\nFit parameters:\n$\mu=%.2f$\n$\sigma=%.2f$\n$A=%.2f$\n$p_4=%.2f$\n$p_5=%.2f$' % (p)
            elif len(p) == 7:
                textstr += '\nFit parameters:\n$\mu=%.2f$\n$\sigma=%.2f$\n$A=%.2f$\n$p_4=%.2f$\n$p_5=%.2f$\n$m = %.2f$\n$b = %.2f$' % (p)
            else:
                str = '\nFitparamters:'
                for i, pa in enumerate(p):
                    str += '\np%i = %1.1f' % (i, pa)
                textstr += str
        box = AnchoredText(textstr, loc=5)
        ax.add_artist(box)
        ax.annotate('Threshold', xy=(threshold,0), xytext=(threshold,-0.1*ymax), horizontalalignment='center', arrowprops=dict(facecolor='black', shrink=0.05, width=0, headwidth=0))
        
        plt.savefig(self.outfile + '.' + self.outformat)
        
        
    def fit_testbeam_spectrum(self, x, y, p0, fit_range=None, ymax=None, debug=False, detail=False):
        '''
            Fit custom fitfunction to spectrum from testbeam and plot both data and fitted function.
            Parameters:
                x:np.ndarray       -    x-values of histogrammed data.
                y:np.ndarray       -    y-values of histogrammed data.
                p0:tuple           -    Set of startparameters for fit. Format: (mu, eta, sigma, A).
                fit_range:tuple    -    [Optional] Region where the fit should be performed. Obtained automatically if None.
                ymax:int           -    [Optional] Maximum of y-axis of plot. Obtained automatically if None.
                debug:boolean      -    [Optional] If set, the fitfunction is plotted with startparameters for debugging.
        '''
        self.error = False
        threshold = self.find_threshold(y)
        if not fit_range or fit_range == 'auto':
            fit_range = (threshold, np.round(np.amax(x)))
        if ymax is None:
            ymax = 1.1*np.amax(y)
        
        plot_range = (threshold, np.round(np.amax(x)))

        try:
            p, _ = curve_fit(self._fitfunction_testbeam, x[(x > fit_range[0]) & (x < fit_range[1])], y[(x > fit_range[0]) & (x < fit_range[1])], p0=p0)
            
            mpv = float(x[np.argmax(landau.langau(x, p[0], p[1], p[2], p[3]))])
            
            if debug:
                p = p0
                
            if p[0] <= threshold:
                logging.error('Encountered an error during analysis of file %s: Peak is below threshold!' % (self.f))
                self.errorfiles.append([os.path.join(self.dirpath, self.f), 'Fit: Peak below threshold!'])
                self.error = True
            elif p[3] <= 0:
                logging.error('Encountered an error during analysis of file %s: Amplitude is negative!' % (self.f))
                self.errorfiles.append([os.path.join(self.dirpath, self.f), 'Fit: Amplitude is negative!'])
                self.error = True
            elif (10. * float(p[1]) < float(p[2])):
                logging.error('Encountered an error during analysis of file %s: Oscillation occurred!' % (self.f))
                self.errorfiles.append([os.path.join(self.dirpath, self.f), 'Fit: Oscillation occurred!'])
                #self.error = True
        except RuntimeError as e:
            logging.error('Encountered an error during analysis of file %s: %s' % (self.f, e))
            self.errorfiles.append([os.path.join(self.dirpath, self.f), e])
            self.error = True
        
        if self.error:
            p = p0
            mpv = p0[0]
        else:
            p = tuple([abs(e) for e in p])
        
        logging.debug('Fitparameters:\nMPV = %1.2f\nmu = %1.3f\neta = %1.3f\nsigma = %1.3f\nA = %1.3f\np4 = %1.3f\np5 = %1.3f' % ((mpv,) + p))
        
        plt.cla()
        plt.plot(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], label='Data', color='blue', zorder=0, linewidth=1)
        plt.fill_between(x[(x > plot_range[0]) & (x < plot_range[1])], y[(x > plot_range[0]) & (x < plot_range[1])], facecolor='blue', alpha=0.3, zorder=0)
        plt.plot(x[(x > fit_range[0]) & (x < fit_range[1])], self._fitfunction_testbeam(x, *p)[(x > fit_range[0]) & (x < fit_range[1])], label='Fit', color='red', zorder=2, linewidth=1)
        
        if detail:
            plt.plot(x[(x > fit_range[0]) & (x < fit_range[1])], landau.langau(x, *p[:4])[(x > fit_range[0]) & (x < fit_range[1])], label='Langau', color='purple', linestyle='--', zorder=2, linewidth=1)
            plt.plot(x[(x > fit_range[0]) & (x < fit_range[1])], p[4]*np.exp(-x/p[5])[(x > fit_range[0]) & (x < fit_range[1])], label='Exponential', color='yellow', linestyle='--', zorder=2, linewidth=1)
            plt.plot([mpv, mpv], [0., ymax], label='MPV', color='green', linestyle='--')
        
        if self._energy_calibrated:
            plt.xlim(self._energy_intercept, np.round(np.amax(x)))
        else:
            plt.xlim(0, np.round(np.amax(x)))
        plt.ylim(0, ymax)
        plt.legend(loc=1, fontsize=12)
        plt.grid()
        plt.title(self.title)
        plt.xlabel('Energy [%s]' % self._energy_unit)
        plt.ylabel('Count')
        
        ax = plt.axes()
        textstr = '$N = %i$' % self.event_count
        if self._darkframe_corrected:
            textstr += '\nDarkframe-cor.'
        if self.error:
            textstr += '\nFit failed!'
        else:
            textstr += '\nFit parameters:\n$MPV = %1.2f$\n$\mu=%.2f$\n$\eta=%.2f$\n$\sigma=%.2f$\n$A=%.2f$\n$p_4=%.2f$\n$p_5=%.2f$' % ((mpv,) + p)
        box = AnchoredText(textstr, loc=5)
        ax.add_artist(box)
        ax.annotate('Threshold', xy=(threshold,0), xytext=(threshold,-0.1*ymax), horizontalalignment='center', arrowprops=dict(facecolor='black', shrink=0.05, width=0, headwidth=0))
        
        plt.savefig(self.outfile + '.' + self.outformat)
        
    
        
    
'''
Examples
'''    
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - [%(levelname)-8s] (%(threadName)-10s) %(message)s")
    
    a = MCA_analysis()
    

    '''
    Just plot a single waveform
    '''
#     dirpath = '/path/to/data'
#     f = 'filename.h5'
#     data = a.load_data_file(os.path.join(dirpath, f))
#     
#     a.just_plot_waveform(y=data[0], threshold=a.find_threshold(a.histogram_data(data)[1]))
         
    
    '''
    Overlay a bunch of waveforms
    '''
#     dirpath = ''/path/to/data''
#     f = 'filename.h5'
#     data = a.load_data_file(os.path.join(dirpath, f))
#      
#     a.overlay_waveforms(x=range(0, 200), data=data, n_max=1000, cut=2**14)
    
    
    '''
    Just plot a histogram
    '''
#     f = '/path/to/data'
#  
#     data = a.load_data_file(f)
#     data = a.correct_baseline(data)
#     x,y = a.histogram_data(data)
#     
#     a.just_plot_histogram(x, y)
    
    
    '''
    Just plot a bunch of histograms
    '''
#     folder = '/path/to/data'
#       
#     files = []
#     for (dirpath, dirnames, filenames) in os.walk(folder):
#         for f in filenames:
#             if not os.path.split(f)[1].split('.')[1] == 'h5':
#                 continue
#             files.append(os.path.join(dirpath, f))
#       
#     pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=len(files), poll=10, term_width=80).start()
#     i=1
#     for f in files:
#         try:
#             ''' Do analysis here '''
#             data = a.load_data_file(f)
#             x,y = a.histogram_data(data)
#             a.just_plot_histogram(x, y)
#             
#         except Exception as e:
#             logging.error('Encountered an error during analysis of file %s: %s' % (f, e))
#             continue
#         pbar.update(i)
#         i += 1
#     pbar.finish()
  
    
    '''
    Fit and plot single source scan file with optional energy calibration
    '''
#     dirpath = '/path/to/data'
#     f = 'filename.h5'
#     data = a.load_data_file(os.path.join(dirpath, f))
#     data = a.correct_baseline(data)
#     
#     x,y = a.histogram_data(data)
#      
#      
#     #x = a.calibrate_to(x, f, 'keV')   # 'Electrons' or 'keV'
#     
#     x = a.calibrate_energy(x, m=0.004, b=21.32, unit='keV')
#      
#     #p0 = (1900, 500, 140, 4200, 1500, 35, 9500, 1000, 30, 0, 0)    # mu, sigma, A, p4, p5, m, b
#     
#     p0 = (60, 10, 30) 
#     a.fit_source_spectrum(x, y, p0, fit_range=(53,80), ymax=200, debug=False)
    
    
    '''
    Fit and plot single testbeam file with optional darkframe substraction and energy calibration
    '''
#     dirpath = '/path/to/data'
#     f = 'filename.h5'
#     darkframefile = 'filename.h5'
#       
#            
#     data = a.load_data_file(os.path.join(dirpath, f))
#     x,y = a.histogram_data(data)
#        
#     #y = a.substract_darkframe(y, darkframefile)    
#     #x = a.calibrate_to(x, f, 'Electrons')   # 'Electrons' or 'keV'
#   
#        
#     p0 = (8000, 200, 1500, 500, 500000, 700)    # mu, eta, sigma, A, p4, p5
#     a.fit_testbeam_spectrum(x, y, p0, fit_range=(4500, 20000), ymax=1300, debug=False, detail=False)
#       
#     #p0 = (12000, 300, 2000, 100)
#     #a.fit_langau(x, y, p0, (10600, 20000), ymax=1000)
    
    
    '''
    Analyze all h5 files in folder (recursively)
    '''
#     folder = '/path/to/data'
#     p0 = (9000, 1000, 1000, 900, 10000, 500)
#       
#     files = []
#     for (dirpath, dirnames, filenames) in os.walk(folder):
#         for f in filenames:
#             if not os.path.split(f)[1].split('.')[1] == 'h5':
#                 continue
#              
#             '''Blacklist files here'''
#             #if 'PCB2_structureH' in f:
#             #    continue
#              
#             files.append(os.path.join(dirpath, f))
#   
#     pbar = progressbar.ProgressBar(widgets=['', progressbar.Percentage(), ' ', progressbar.Bar(marker='*', left='|', right='|'), ' ', progressbar.AdaptiveETA()], maxval=len(files), poll=10, term_width=80).start()
#     i=1
#     for f in files:
#         logging.debug('now analyzing file %s' % f)
#           
#         try:
#             ''' Do analysis here '''
#             data = a.load_data_file(f)
#             x,y = a.histogram_data(data)
#             a.fit_testbeam_spectrum(x, y, p0)
#         except Exception as e:
#             logging.error('Encountered an error during analysis of file %s: %s' % (f, e))
#             continue
#            
#          
#        
#           
#         pbar.update(i)
#         i+=1
#                   
#     pbar.finish()
#     logging.info('Done! Analyzed %i files in total.' % len(files))
#     if len(a.errorfiles) > 0:
#         logging.error('%i files encountered errors during analysis:' % len(a.errorfiles))
#         logging.error(a.errorfiles)
#         with open('errorfiles.log', 'w') as ef:
#             for f in a.errorfiles:
#                 ef.write('%s <- %s\n' %(f[1], f[0]))
    
    