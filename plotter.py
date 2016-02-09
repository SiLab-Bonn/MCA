import matplotlib.pyplot as plt
import tables as tb
import numpy as np

class qmca_plotter():
    def __init__(self):
        pass
    
    def plot_data_file(self, infile='event_data.h5', title=''):
        outfile = infile.split('.')[0] + '.pdf'
        with tb.openFile(infile, 'r') as infile_h5:
            data = infile_h5.root.event_data[:]
            hist, edges = np.histogram(np.amax(data, axis=1), bins=1024, range=(0, 2**14-10))
            x, y = edges[:-1], hist
            
            fig = plt.figure()
            fig.suptitle(title)
            ax = fig.gca()
            ax.cla()
            ax.grid(True)
            ax.set_xlabel('ADC channel')
            ax.set_ylabel('Hits')
            ax.set_xlim(0, 2**14)
            
            ax.plot(x, y, label='Data')
            ax.legend(title=('nHits = %i' % len(data)), loc='best')
    
            fig.savefig(outfile)
            
    def clear_plot(self):
        plt.cla()