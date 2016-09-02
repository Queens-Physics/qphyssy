import numpy as np
import qexpy as q
import qexpy.error as qe
import qexpy.utils as qu
import qexpy.fitting as qf
import qexpy.plot_utils as qpu

import bokeh.plotting as bp
import bokeh.io as bi
import bokeh.models as mo
import bokeh.palettes as bpal

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from ipywidgets import interact 

CONSTANT = qu.number_types
ARRAY = qu.array_types



def MakePlot(x=None, y=None, xerr=None, yerr=None, data_name=None, dataset=None, xname=None, xunits=None, yname=None, yunits=None):
    '''Use this function to create a plot object, by providing either arrays
    corresponding to the x and y data, Measurement_Arrays for x and y, or
    an XYDataset. If providing a dataset, it can be specified as either the 
    x argument or the dataset argument.
   
    '''
    
    if x is None and y is None and dataset is None:
        return Plot(None)
    
    elif x is not None and y is None:
        #assume that x is a dataset:
        if isinstance(x, qf.XYDataSet):
            if xname is not None and isinstance(xname, str):
                x.xname = xname
            if yname is not None and isinstance(yname, str):
                x.yname = yname           
            if xunits is not None and isinstance(xunits, str):
                x.xunits = xunits
            if yunits is not None and isinstance(yunits, str):
                x.yunits = yunits 
            if data_name is not None and isinstance(data_name, str):
                x.name = data_name
            return Plot(x)
        else:
            print("Must specify x AND y or dataset, returning empty plot")
            return Plot(None)
        
    elif dataset is not None:
        if xname is not None and isinstance(xname, str):
            dataset.xname = xname
        if yname is not None and isinstance(yname, str):
            dataset.yname = yname           
        if xunits is not None and isinstance(xunits, str):
            dataset.xunits = xunits
        if yunits is not None and isinstance(yunits, str):
            dataset.yunits = yunits 
        if data_name is not None and isinstance(data_name, str):
            dataset.name = data_name
        return Plot(dataset)
  
    elif (x is not None and y is not None):
        ds = qf.XYDataSet(x, y, xerr=xerr, yerr=yerr, data_name=data_name,
                          xname=xname, xunits=xunits, yname=yname, yunits=yunits)
        return Plot(dataset = ds)
    
    else:
        return Plot(None)
  
    


class Plot:
    '''Object for plotting and fitting datasets built on
    Measurement_Arrays

    The Plot object holds a list of XYDatasets, themselves containing
    pairs of MeasurementArrays holding x and y values to be plotted and 
    fitted. The Plot object uses bokeh or matplotlib to display the data,
    along with fit functions, and user-specified functions. One should configure
    the various aspects of the plot, and then call the show() function
    which will actually build the plot object and display it. 
    '''

    def __init__(self, dataset=None):
        '''
        Constructor to make a plot based on a dataset
        '''                                    
    
        #Colors to be used for coloring elements automatically
        self.color_palette = bpal.Set1_9+bpal.Set2_8
        self.color_count = 0
        
        #Add margins to the range of the plot
        self.x_range_margin = 0.5
        self.y_range_margin = 0.5  
        
        #Dimensions of the figure in pixels for bokeh
        self.dimensions = [600, 400]
        #Convert to something similar for matplotlib (although that is 
        #screen resolution dependent)
        self.mpl_scaling = 0.017
        
        #Functions that the user can add to be plotted
        self.user_functions_count=0
        self.user_functions = []
        self.user_functions_pars = []
        self.user_functions_names = []
        self.user_functions_colors = []
                
        #Where to save the plot              
        self.save_filename = 'myplot.html'
        
        #How big to draw error bands on fitted functions
        self.errorband_sigma = 1.0
        #whether to show residuals
        self.show_residuals=False
        #whether to include text labels on plot with fit parameters
        self.show_fit_results=True 
        self.fit_results_x_offset=0
        self.fit_results_y_offset=0
        
        #location of legend
        self.bk_legend_location = "top_left"
        self.bk_legend_orientation = "vertical"
        self.mpl_legend_location = "upper left"
        self.mpl_show_legend = True
        
        #The data to be plotted are held in a list of datasets:
        self.datasets=[]
        #Each data set has a color, so that the user can choose specific
        #colors for each dataset
        self.datasets_colors=[]      
        
        #Things to initialize from a data set:
        self.xunits = ""
        self.xname = "x"      
        self.yunits = ""
        self.yname = "y"
        self.x_range = [0,1]
        self.y_range = [0,1]
        self.title = "y as a function of x"
        
        if dataset != None:
            self.datasets.append(dataset)            
            self.datasets_colors.append(self._get_color_from_palette())
            self.initialize_from_dataset(dataset)
        else:
            self.initialized_from_dataset = False
        
        #Some parameters to make the plots have proper labels
        self.axes = {'xscale': 'linear', 'yscale': 'linear'}      
        self.labels = {
            'title': self.title,
            'xtitle': self.xname+' ['+self.xunits+']',
            'ytitle': self.yname+' ['+self.yunits+']'}
 

    def initialize_from_dataset(self, dataset):
        self.xunits = dataset.xunits
        self.xname = dataset.xname      
        self.yunits = dataset.yunits
        self.yname = dataset.yname 
        self.title = dataset.name
        self.labels = {
            'title': self.title,
            'xtitle': self.xname+' ['+self.xunits+']',
            'ytitle': self.yname+' ['+self.yunits+']'}
        
        #Get the range from the dataset (will include the margin)
        self.set_range_from_dataset(dataset)
        self.initialized_from_dataset = True
        
    def _get_color_from_palette(self):
        '''Automatically select a color from the palette'''
        self.color_count += 1
        if self.color_count>len(self.color_palette):
            self.color_count = 1
        return self.color_palette[self.color_count-1]
    
    def set_range_from_dataset(self, dataset):
        '''Use a dataset to set the range for the figure'''
        self.x_range = dataset.get_x_range(self.x_range_margin)
        self.y_range = dataset.get_y_range(self.y_range_margin)
        self.set_yres_range_from_fits()
        
    def set_yres_range_from_fits(self):
        '''Set the range for the residual plot, based on all datasets that
        have a fit'''      
        for dataset in self.datasets:
            if dataset.nfits > 0:
                self.yres_range = dataset.get_yres_range(self.y_range_margin)
        
    def fit(self, model=None, parguess=None, fit_range=None, print_results=True, datasetindex=-1):
        '''Fit a dataset to model - calls XYDataset.fit and returns a 
        Measurement_Array of fitted parameters'''
        results = self.datasets[datasetindex].fit(model, parguess, fit_range) 
        return results
        
    def print_fit_parameters(self, dataset=-1):
        if self.datasets[-1].nfits>0:
            print("Fit parameters:\n"+str(self.datasets[dataset].fit_pars[-1]))    
        else:
            print("Datasets have not been fit")
            
###############################################################################
# User Methods for adding to Plot Objects
###############################################################################

    def add_residuals(self):
        '''Add a subfigure with residuals to the main figure when plotting'''
        self.set_yres_range_from_fits()
        if self.datasets[-1].nfits>0:
            self.show_residuals = True

    
    def add_function(self, function, pars = None, name=None, color=None):
        '''Add a user-specifed function to the list of functions to be plotted.
        
        All datasets are functions when populate_bokeh_figure is called
        - usually when show() is called
        '''
        
        xvals = np.linspace(self.x_range[0],self.x_range[1], 100)
        
        #check if we should change the y-axis range to accomodate the function
        if not isinstance(pars, np.ndarray) and pars == None:
            fvals = function(xvals)
        elif isinstance(pars, qe.Measurement_Array) :
            recall = qe.Measurement.minmax_n
            qe.Measurement.minmax_n=1
            fmes = function(xvals, *(pars))
            fvals = fmes.get_means()
            qe.Measurement.minmax_n=recall
        elif isinstance(pars,(list, np.ndarray)):
            fvals = function(xvals, *pars)
        else:
            print("Error: Not a recognized format for parameter")
            return
                 
        fmax = fvals.max()+self.y_range_margin
        fmin = fvals.min()-self.y_range_margin
        
        if fmax > self.y_range[1]:
            self.y_range[1]=fmax
        if fmin < self.y_range[0]:
            self.y_range[0]=fmin
            
        self.user_functions.append(function)
        self.user_functions_pars.append(pars)
        fname = "userf_{}".format(self.user_functions_count) if name==None else name
        self.user_functions_names.append(fname)
        self.user_functions_count +=1
        
        if color is None:
            self.user_functions_colors.append(self._get_color_from_palette())
        else: 
            self.user_functions_colors.append(color)
        
    def add_dataset(self, dataset, color=None, name=None):
        '''Add a dataset to the Plot object. All datasets are plotted
        when populate_bokeh_figure is called - usually when show() is called'''
        self.datasets.append(dataset)
        
        if len(self.datasets) < 2:    
            self.initialize_from_dataset(dataset)
            
        if color is None:
            self.datasets_colors.append(self._get_color_from_palette())
        else: 
            self.datasets_colors.append(color)
        if name != None:
            self.datasets[-1].name=name
            
        x_range = dataset.get_x_range(self.x_range_margin)
        y_range = dataset.get_y_range(self.y_range_margin)    
        
        if x_range[0] < self.x_range[0]:
            self.x_range[0]=x_range[0]
        if x_range[1] > self.x_range[1]:
            self.x_range[1]=x_range[1]
            
        if y_range[0] < self.y_range[0]:
            self.y_range[0]=y_range[0]
        if y_range[1] > self.y_range[1]:
            self.y_range[1]=y_range[1] 
            
        self.set_yres_range_from_fits()

#
###############################################################################
# Methods for changing parameters of Plot Object
###############################################################################
        
    def set_plot_range(self, x_range=None, y_range=None):
        '''Set the range for the figure'''
        if type(x_range) in ARRAY and len(x_range) is 2:
            self.x_range = x_range
        elif x_range is not None:
            print('''X range must be a list containing a minimun and maximum
            value for the range of the plot.''')

        if type(y_range) in ARRAY and len(y_range) is 2:
            self.y_range = y_range
        elif y_range is not None:
            print('''Y range must be a list containing a minimun and maximum
            value for the range of the plot.''')

            
    def set_labels(self, title=None, xtitle=None, ytitle=None):
        '''Change the labels for plot axis, datasets, or the plot itself.

        Method simply overwrites the automatically generated names used in
        the Bokeh plot.'''
        if title is not None:
            self.labels['title'] = title

        if xtitle is not None:
            self.labels['xtitle'] = xtitle

        if ytitle is not None:
            self.labels['ytitle'] = ytitle


    def resize_plot(self, width=None, height=None, mpl_scaling=None):
        if width is None:
            width = 600
        if height is None:
            height = 400
        if mpl_scaling is not None:
            self.mpl_scaling = mpl_scaling
        self.dimensions = [width, height]

    def set_errorband_sigma(self, sigma=1):
        '''Change the confidence bounds of the error range on a fit.
        '''
        self.errorband_sigma = sigma


            
    def show(self, output='inline', populate_figure=True, refresh = True):
        '''
        Show the figure, will call one of the populate methods
        by default to build a figure.
        '''
        
        if q.plot_engine in q.plot_engine_synonyms["bokeh"]:
               
            self.set_bokeh_output(output)      
            if populate_figure:
                bp.show(self.populate_bokeh_figure())
            else:
                bp.show(self.bkfigure)
                
        elif q.plot_engine in q.plot_engine_synonyms["mpl"]:
            self.set_mpl_output()
            if populate_figure:
                self.populate_mpl_figure(refresh=refresh)
            plt.show()
            
        else:
            print("Error: unrecognized plot engine")

###############################################################################
# Methods for Returning or Rendering Matplotlib
###############################################################################  

    def set_mpl_output(self, output='inline'):
        '''Choose where to output (in a notebook or to a file)'''
        #TODO not tested, the output notebook part does not work
        if output == 'file' or not qu.in_notebook():
            plt.savefig(self.save_filename, bbox_inches='tight')
        elif not qu.mpl_ouput_notebook_called:
            qu.mpl_output_notebook()
            # This must be the first time calling output_notebook,
            # keep track that it's been called:
            qu.mpl_ouput_notebook_called = True
        else:
            pass
        
        
    def populate_mpl_figure(self, refresh = True):
        '''Thia is the main function to populate the matplotlib figure. It will create
        the figure, and then draw all of the data sets, their residuals, their fits,
        and any user-supplied functions'''
        
        self.initialize_mpl_figure(refresh)
      
        #Plot the data sets
        legend_offset = 0
        for dataset, color in zip(self.datasets, self.datasets_colors):           
            self.mpl_plot_dataset(dataset, color, show_fit_function=True,
                                  show_residuals=self.show_residuals)
            
            if self.show_fit_results and dataset.nfits > 0:
                    legend_offset = self.mpl_plot_fit_results_text_box(dataset, legend_offset)
                    
         
        #Now add any user defined functions:
        #The range over which to plot the functions:
        xvals = [self.x_range[0]+self.x_range_margin, 
                 self.x_range[1]-self.x_range_margin]
        for func, pars, fname, color in zip(self.user_functions,
                                            self.user_functions_pars, 
                                            self.user_functions_names,
                                            self.user_functions_colors):
        
            self.mpl_plot_function(function=func, xdata=xvals,pars=pars, n=100,
                               legend_name= fname, color=color,
                               errorbandfactor=self.errorband_sigma)
            
        if self.mpl_show_legend:
            plt.legend(loc=self.mpl_legend_location,fontsize=11)
            
    def initialize_mpl_figure(self, refresh = True):
        '''Build a matplotlib figure with the desired size to draw on'''
        
        if not refresh and hasattr(self, 'mplfigure'):
            if self.show_residuals and not hasattr(self,'mpl_gs'):
                pass
            else:
                return
         
        if not self.show_residuals:            
            self.mplfigure = plt.figure(figsize=(self.dimensions[0]*self.mpl_scaling,
                                       self.dimensions[1]*self.mpl_scaling))
            
        else:
            self.mplfigure = plt.figure(figsize=(self.dimensions[0]*self.mpl_scaling,
                                                1.33*self.dimensions[1]*self.mpl_scaling)) 
            self.mpl_gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
            
            plt.subplot(self.mpl_gs[1])
            plt.axis([self.x_range[0], self.x_range[1], 
                     self.yres_range[0], self.yres_range[1]])
            plt.xlabel(self.labels['xtitle'])
            plt.ylabel("Residuals")
            plt.grid()
            #switch to main figure
            plt.subplot(self.mpl_gs[0])          

        
        plt.axis([self.x_range[0], self.x_range[1], 
                 self.y_range[0], self.y_range[1]])
        plt.xlabel(self.labels['xtitle'])
        plt.ylabel(self.labels['ytitle'])
        plt.title(self.labels['title'])
        plt.grid()
           
    def mpl_plot_fit_results_text_box(self, dataset, yoffset=0):
        '''Add a text box with the fit parameters from the last fit 
        of the dataset'''
        
        if not hasattr(self, 'mplfigure'):
            self.initialize_mpl_figure()
            
        offset = yoffset    
        h = self.y_range[1]-self.y_range[0]
        l = self.x_range[1]-self.x_range[0]
        start_x = self.x_range[1]-0.02*l + self.fit_results_x_offset
        start_y = self.y_range[1]-0.12*h-offset + self.fit_results_y_offset
        
        textfit=""
        for i in range(dataset.fit_npars[-1]):
            short_name =  dataset.fit_pars[-1][i].__str__().split('_')
            textfit += short_name[0]+"_"+short_name[-1]+"\n"
           
        plt.text(start_x, start_y, textfit,fontsize=11, horizontalalignment='right',
                verticalalignment='bottom', bbox=dict(facecolor='white', alpha=0.0, edgecolor='none'))
        offset = dataset.fit_npars[-1] * 0.045 * h
        return offset
           
        
    def mpl_plot_dataset(self, dataset, color='black', show_fit_function=True, show_residuals=True):
        '''Add a dataset, its fit function and its residuals to the main figure.
        It is better to use add_function() and to let populate_mpl_plot() actually
        add the function.
        '''
        
        if not hasattr(self, 'mplfigure'):       
            if show_residuals:
                if dataset.nfits > 0:
                    self.show_residuals = True
            self.initialize_mpl_figure()
        
        if hasattr(self, 'mpl_gs'):
            plt.subplot(self.mpl_gs[0])
            
        if dataset.is_histogram:
            if hasattr(dataset, 'hist_data'):
                plt.hist(dataset.hist_data, bins=dataset.hist_bins,
                    label=dataset.name, color=color, alpha=0.7)
            else:
                plt.bar(dataset.xdata, dataset.ydata, width = dataset.xdata[-1]-dataset.xdata[-2],
                      label=dataset.name, color=color, alpha=0.7)
            
        else:   
            plt.errorbar(dataset.xdata, dataset.ydata,
                    xerr=dataset.xerr,yerr=dataset.yerr,
                    fmt='o',color=color,markeredgecolor = 'none',
                    label=dataset.name)
            
        if dataset.nfits > 0 and show_fit_function:   
            self.mpl_plot_function(function=dataset.fit_function[-1], xdata=dataset.xdata,
                                   pars=dataset.fit_pars[-1], n=50,
                                   legend_name=dataset.fit_function_name[-1],
                                   color=color, errorbandfactor=self.errorband_sigma)
            
        if self.show_residuals and hasattr(self, 'mpl_gs') and show_residuals:
            plt.subplot(self.mpl_gs[1])
            plt.errorbar(dataset.xdata, dataset.fit_yres[-1].get_means(),
                        xerr=dataset.xerr,yerr=dataset.yerr,
                        fmt='o',color=color,markeredgecolor = 'none')
            plt.subplot(self.mpl_gs[0])
                    
     
    def mpl_plot_function(self, function, xdata, pars=None, n=100,
                      legend_name=None, color='black', errorbandfactor=1.0):
        '''Add a function to the main figure. It is better to use add_function() and to
        let populate_mpl_plot() actually add the function.
        
        The function can be either f(x) or f(x, *pars), in which case, if *pars is
        a Measurement_Array, then error bands will be drawn
        '''
        if not hasattr(self, 'mplfigure'):
            self.initialize_mpl_figure()
        
        if hasattr(self, 'mpl_gs'):
            plt.subplot(self.mpl_gs[0])
        xvals = np.linspace(min(xdata), max(xdata), n)
        
        if pars is None:
            fvals = function(xvals)
        elif isinstance(pars, qe.Measurement_Array):
            recall = qe.Measurement.minmax_n
            qe.Measurement.minmax_n=1
            fmes = function(xvals, *pars)
            fvals = fmes.get_means()
            ferr = fmes.get_stds()
            qe.Measurement.minmax_n=recall
        elif isinstance(pars,(list, np.ndarray)):
            fvals = function(xvals, *pars)
        else:
            print("Error: unrecognized parameters for function")
            pass
        
        plt.plot(xvals,fvals, color=color, label = legend_name)
        
        if isinstance(pars, qe.Measurement_Array):
            fmax = fvals + ferr
            fmin = fvals - ferr
            plt.fill_between(xvals, fmin, fmax, facecolor=color,
                            alpha=0.3, edgecolor = 'none',
                            interpolate=True)
        
    def interactive_linear_fit(self, error_range=5):
        '''Fits the last dataset to a linear function and displays the
        result as an interactive fit'''
                
        if len(self.datasets) >1:
            print("Warning: only using the last added dataset, and clearing previous fits")
                     
        dataset = self.datasets[-1]
        color = self.datasets_colors[-1]
        
        dataset.clear_fits()
        dataset.fit("linear")
        
        func = dataset.fit_function[-1]
        pars = dataset.fit_pars[-1]
        fname = "linear"       
        
        #Extend the x range to 0
        if self.x_range[0] > -0.5:
            self.x_range[0] = -0.5
            self.y_range[0] = dataset.fit_function[-1](self.x_range[0], *pars.get_means())
                
        off_min = pars[0].mean-error_range*pars[0].std
        off_max = pars[0].mean+error_range*pars[0].std
        off_step = (off_max-off_min)/50.
       
        slope_min = pars[1].mean-error_range*pars[1].std
        slope_max = pars[1].mean+error_range*pars[1].std
        slope_step = (slope_max-slope_min)/50.
        
            
        @interact(offset=(off_min, off_max, off_step),
                  offset_err = (0, error_range*pars[0].std, pars[0].std/50.),
                  slope=(slope_min, slope_max, slope_step),
                  slope_err = (0, error_range*pars[1].std, pars[1].std/50.),
                  correlation = (-1,1,0.05)                 
                 )
        
        def update(offset=pars[0].mean, offset_err=pars[0].std, slope=pars[1].mean,
                   slope_err=pars[1].std, correlation=dataset.fit_pcorr[-1][0][1]):  
            
            plt.figure(figsize=(self.dimensions[0]*self.mpl_scaling,
                               self.dimensions[1]*self.mpl_scaling))
            
            xvals = np.linspace(self.x_range[0], self.x_range[1], 20)
            
            omes = qe.Measurement(offset,offset_err, name="offset")
            smes = qe.Measurement(slope,slope_err, name="slope")
            omes.set_correlation(smes,correlation)
            
            recall = qe.Measurement.minmax_n
            qe.Measurement.minmax_n=1
            fmes = omes + smes*xvals
            qe.Measurement.minmax_n=recall
            fvals = fmes.get_means()
            ferr = fmes.get_stds()
            
            fmax = fvals + ferr
            fmin = fvals - ferr
            
            plt.errorbar(dataset.xdata, dataset.ydata,
                    xerr=dataset.xerr,yerr=dataset.yerr,
                    fmt='o',color=color,markeredgecolor = 'none',
                    label=dataset.name)
            
            plt.plot(xvals,fvals, color=color, label ="linear fit")
            plt.fill_between(xvals, fmin, fmax, facecolor=color,
                            alpha=0.3, edgecolor = 'none',
                            interpolate=True)
            
            #Add text with currently chosen fits
            h = self.y_range[1]-self.y_range[0]
            l = self.x_range[1]-self.x_range[0]
            start_x = self.x_range[1]-0.02*l + self.fit_results_x_offset
            start_y = self.y_range[1]-0.08*h+ self.fit_results_y_offset
        
            textfit=str(omes)+"\n"+str(smes)
            plt.text(start_x, start_y, textfit,fontsize=12, horizontalalignment='right',
                verticalalignment='bottom')
     
            plt.axis([self.x_range[0], self.x_range[1], 
                 self.y_range[0], self.y_range[1]])
            plt.xlabel(self.labels['xtitle'])
            plt.ylabel(self.labels['ytitle'])
            plt.title(self.labels['title'])
            plt.legend(loc=self.mpl_legend_location)
            plt.grid()
            plt.show()

###Some wrapped matplotlib functions
    def mpl_plot(self, *args, **kwargs):
        '''Wrapper for matplotlib plot(), typically to plot a line'''
        if not hasattr(self, 'mplfigure'):
            self.initialize_mpl_figure()
            
        plt.plot(*args, **kwargs)
        
    def mpl_error_bar(self, x, y, yerr=None, xerr=None, fmt='', ecolor=None, 
                      elinewidth=None, capsize=None, barsabove=False, lolims=False,
                      uplims=False, xlolims=False, xuplims=False, errorevery=1,
                      capthick=None, hold=None, data=None, **kwargs):
        '''Wrapper for matplotlib error_bar(), adds points with error bars '''
        if not hasattr(self, 'mplfigure'):
            self.initialize_mpl_figure()
            
        plt.error_bar(self, x, y, yerr, xerr, fmt, ecolor, 
                      elinewidth, capsize, barsabove, lolims,
                      uplims, xlolims, xuplims, errorevery,
                      capthick, hold, data, **kwargs)
        
    def mpl_hist(self,x, bins=10, range=None, normed=False, weights=None,
                 cumulative=False, bottom=None, histtype='bar', align='mid',
                 orientation='vertical', rwidth=None, log=False, color=None,
                 label=None, stacked=False, hold=None, data=None, **kwargs):
        '''Wrapper for matplotlib hist(), creates a histogram'''
        if not hasattr(self, 'mplfigure'):
            self.initialize_mpl_figure()
            
        plt.hist(x, bins, range, normed, weights, cumulative, bottom,
                histtype, align,   orientation, rwidth, log, color,
                label, stacked, hold, data, **kwargs)
            
            
###############################################################################
# Methods for Returning or Rendering Bokeh
###############################################################################    

    def set_bokeh_output(self, output='inline'):
        '''Choose where to output (in a notebook or to a file)'''
        
        if output == 'file' or not qu.in_notebook():
            bi.output_file(self.save_filename,
                           title=self.labels['title'])
        elif not qu.bokeh_ouput_notebook_called:
            bi.output_notebook()
            # This must be the first time calling output_notebook,
            # keep track that it's been called:
            qu.bokeh_ouput_notebook_called = True
        else:
            pass        
        
    def populate_bokeh_figure(self):  
        '''Main method for building the plot - this creates the Bokeh figure,
        and then loops through all datasets (and their fit functions), as
        well as user-specified functions, and adds them to the bokeh figure'''
        
        #create a new bokeh figure
        
        #expand the y-range to accomodate the fit results text
        yrange_recall = self.y_range[1]
        if self.show_fit_results:
            pixelcount = 0
            for dataset in self.datasets:
                if dataset.nfits > 0:
                    pixelcount += dataset.fit_npars[-1] * 25
            self.y_range[1] += pixelcount * self.y_range[1]/self.dimensions[1]
        self.initialize_bokeh_figure(residuals=False)
        self.y_range[1] = yrange_recall
        
        # create the one for residuals if needed
        if self.show_residuals:
            self.initialize_bokeh_figure(residuals=True)
                              
        #plot the datasets and their latest fit
        legend_offset=0
        for dataset, color in zip(self.datasets, self.datasets_colors):
            self.bk_plot_dataset(dataset, residual=False, color=color, show_fit_function=True)
            if dataset.nfits>0:      
                if self.show_fit_results:
                    legend_offset = self.bk_plot_fit_results_text_box(dataset, legend_offset)
                    legend_offset += 3
                if self.show_residuals:
                    self.bk_plot_dataset(dataset, residual=True, color=color)


        #Now add any user defined functions:
        #The range over which to plot the functions:
        xvals = [self.x_range[0]+self.x_range_margin, 
                 self.x_range[1]-self.x_range_margin]
   
        for func, pars, fname, color in zip(self.user_functions,
                                            self.user_functions_pars, 
                                            self.user_functions_names,
                                            self.user_functions_colors):
        
            self.bk_plot_function(function=func, xdata=xvals,pars=pars, n=100,
                               legend_name= fname, color=color,
                               errorbandfactor=self.errorband_sigma)

        #Specify the location of the legend (must be done after stuff has been added)
        self.bkfigure.legend.location = self.bk_legend_location
        self.bkfigure.legend.orientation = self.bk_legend_orientation
        
        if self.show_residuals:
            self.bkfigure = bi.gridplot([[self.bkfigure], [self.bkres]])
          
        return self.bkfigure
    
    def initialize_bokeh_figure(self, residuals=False):  
        '''Create the bokeh figure with desired labeling and axes'''
        if residuals==False:
            self.bkfigure = bp.figure(
                tools='save, pan, box_zoom, wheel_zoom, reset',
                toolbar_location="above",
                width=self.dimensions[0], height=self.dimensions[1],
                y_axis_type=self.axes['yscale'],
                y_range=self.y_range,
                x_axis_type=self.axes['xscale'],
                x_range=self.x_range,
                title=self.labels['title'],
                x_axis_label=self.labels['xtitle'],
                y_axis_label=self.labels['ytitle'],
            )
            return self.bkfigure
        else:
            self.set_yres_range_from_fits
            self.bkres =  bp.figure(
                width=self.dimensions[0], height=self.dimensions[1]//3,
                tools='save, pan, box_zoom, wheel_zoom, reset',
                toolbar_location="above",
                y_axis_type='linear',
                y_range=self.yres_range,
                x_range=self.bkfigure.x_range,
                x_axis_label=self.labels['xtitle'],
                y_axis_label='Residuals'
            )
            return self.bkres
        
    def bk_plot_fit_results_text_box(self, dataset, yoffset=0):
        '''Add a text box with the fit parameters from the last fit to
        the data set'''
        if not hasattr(self, 'bkfigure'):
            self.bkfigure = self.initialize_bokeh_figure(residuals=False)
            
        offset = yoffset    
        start_x = self.dimensions[0]-5 + self.fit_results_x_offset   
        start_y = self.dimensions[1]-30-offset + self.fit_results_y_offset 
        
        for i in range(dataset.fit_npars[-1]):
            #shorten the name of the fit parameters
            short_name =  dataset.fit_pars[-1][i].__str__().split('_')
            short_name = short_name[0]+"_"+short_name[-1]
            if i > 0:
                offset += 18
            tbox = mo.Label(x=start_x, y=start_y-offset,
                                text_align='right',
                                text_baseline='top',
                                text_font_size='11pt',
                                x_units='screen',
                                y_units='screen',
                                text=short_name,
                                render_mode='css',
                                background_fill_color='white',
                                background_fill_alpha=0.7)
            self.bkfigure.add_layout(tbox)
        return offset
        
    def bk_plot_dataset(self, dataset, residual=False, color='black', show_fit_function=True):
        '''Add a dataset to the bokeh figure for the plot - it is better to 
        use add_dataset() to add a dataset to the Plot object and let
        populate_bokeh_figure take care of calling this function'''
        
        if residual == True:
            if not hasattr(self, 'bkfigure'):
                self.bkres = self.initialize_bokeh_figure(residuals=True)
            return qpu.bk_plot_dataset(self.bkres, dataset, residual=True, color=color)
            
        if not hasattr(self, 'bkfigure'):
            self.bkfigure = self.initialize_bokeh_figure(residuals=False)
            
        qpu.bk_plot_dataset(self.bkfigure, dataset, residual=False, color=color)
        if dataset.nfits > 0 and show_fit_function:
            self.bk_plot_function(function=dataset.fit_function[-1], xdata=dataset.xdata,
                               pars=dataset.fit_pars[-1], n=50,
                               legend_name=dataset.fit_function_name[-1],
                               color=color, errorbandfactor=self.errorband_sigma)
    
    def bk_add_points_with_error_bars(self, xdata, ydata, xerr=None, yerr=None,
                                   color='black', data_name='dataset'):
        '''Add a set of data points with error bars to the main figure -it is better 
        to use add_dataset if the data should be treated as a dataset that can be fit'''
        if not hasattr(self, 'bkfigure'):
            self.bkfigure = self.initialize_bokeh_figure(residuals=False)
        return qpu.bk_add_points_with_error_bars(self.bkfigure, xdata, ydata, xerr=xerr,
                                              yerr=yerr, color=color,
                                              data_name=data_name)
    
    def bk_plot_function(self, function, xdata, pars=None, n=100,
                      legend_name=None, color='black', errorbandfactor=1.0):
        '''Add a function to the main figure. It is better to use add_function() and to
        let populate_bokeh_plot() actually add the function.
        
        The function can be either f(x) or f(x, *pars), in which case, if *pars is
        a Measurement_Array, then error bands will be drawn
        '''
        if not hasattr(self, 'bkfigure'):
            self.bkfigure = self.initialize_bokeh_figure(residuals=False)
        return qpu.bk_plot_function(self.bkfigure, function, xdata, pars=pars, n=n,
                      legend_name=legend_name, color=color, errorbandfactor=errorbandfactor)       
        
    def bk_show_linear_fit(self, output='inline'):
        '''Fits the last dataset to a linear function and displays the
        result. The fit parameters are not displayed as this function is 
        designed to be used in conjunction with bk_interarct_linear_fit()'''
        
        
        if len(self.datasets) >1:
            print("Warning: only using the last added dataset, and clearing previous fits")
                     
        dataset = self.datasets[-1]
        color = self.datasets_colors[-1]
        
        dataset.clear_fits()
        dataset.fit("linear")
        
        func = dataset.fit_function[-1]
        pars = dataset.fit_pars[-1]
        fname = "linear"       
        
        #Extend the x range to 0
        if self.x_range[0] > -0.5:
            self.x_range[0] = -0.5
            self.y_range[0] = dataset.fit_function[-1](self.x_range[0], *pars.get_means())
        
        self.bkfigure = self.initialize_bokeh_figure(residuals=False)
        
        self.bk_plot_dataset(dataset, residual=False,color=color, show_fit_function=False)
        
        xvals = [self.x_range[0]+self.x_range_margin, 
                 self.x_range[1]-self.x_range_margin]
        
        line, patches = self.bk_plot_function( function=func, xdata=xvals,
                              pars=pars, n=100, legend_name= fname,
                              color=color, errorbandfactor=self.errorband_sigma)
        
        #stuff that is only needed by interact_linear_fit
        self.linear_fit_line = line
        self.linear_fit_patches = patches
        self.linear_fit_pars = pars
        self.linear_fit_corr = dataset.fit_pcorr[-1][0][1]
               
        #Specify the location of the legend
        self.bkfigure.legend.location = self.bk_legend_location      
        self.show(output=output,populate_figure=False)

    def bk_interact_linear_fit(self, error_range = 2):  
        '''After show_linear_fit() has been called, this will display
        sliders allowing the user to adjust the parameters of the linear
        fit - only works in a notebook, require ipywigets''' 
        
        off_mean = self.linear_fit_pars[0].mean
        off_std = self.linear_fit_pars[0].std
        off_min = off_mean-error_range*off_std
        off_max = off_mean+error_range*off_std
        off_step = (off_max-off_min)/50.
       
        slope_mean = self.linear_fit_pars[1].mean
        slope_std = self.linear_fit_pars[1].std
        slope_min = slope_mean-error_range*slope_std
        slope_max = slope_mean+error_range*slope_std
        slope_step = (slope_max-slope_min)/50.
        
            
        @interact(offset=(off_min, off_max, off_step),
                  offset_err = (0, 2.*off_std, off_std/50.),
                  slope=(slope_min, slope_max, slope_step),
                  slope_err = (0, 2.*slope_std, off_std/50.),
                  correlation = (-1,1,0.05)                 
                 )
        def update(offset=off_mean, offset_err=off_std, slope=slope_mean, slope_err=slope_std, correlation=self.linear_fit_corr):
              
            recall = qe.Measurement.minmax_n
            qe.Measurement.minmax_n=1
            omes = qe.Measurement(offset,offset_err)
            smes = qe.Measurement(slope,slope_err)
            omes.set_correlation(smes,correlation)
            xdata = np.array(self.linear_fit_line.data_source.data['x'])
            fmes = omes+ smes*xdata
            qe.Measurement.minmax_n=recall
            
            ymax = fmes.get_means()+fmes.get_stds()
            ymin = fmes.get_means()-fmes.get_stds()        
            
            self.linear_fit_line.data_source.data['y'] = fmes.get_means()
            self.linear_fit_patches.data_source.data['y'] = np.append(ymax,ymin[::-1])

            bi.push_notebook()

            
        