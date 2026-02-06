from __future__ import print_function
from __future__ import absolute_import
from builtins import str
__author__ = 'xlinfr'


def wrapper(pathtoplugin, plotornot, filecode):
    try:
        import supy as sp
    except:
        pass
    from pathlib import Path
    from . import suewsdataprocessing
    from . import suewsplotting
    from ..Utilities import f90nml
    import sys
    sys.path.append(pathtoplugin)
    import yaml
    from qgis.PyQt.QtWidgets import QMessageBox

    try:
        import matplotlib.pyplot as plt
        nomatplot = 0
    except ImportError:
        nomatplot = 1
        pass

    su = suewsdataprocessing.SuewsDataProcessing()
    pl = suewsplotting.SuewsPlotting()

    #####################################################################################
    # SuPy initialisation
    yaml_path = Path(pathtoplugin + f'/Input/{filecode}_suews_simple.yml')
    #from supy.data_model import init_config_from_yaml 
    #from supy import SUEWSKernelError
    from supy import SUEWSSimulation

    # Create simulation from YAML configuration
    sim = SUEWSSimulation(yaml_path)
    df_state_init = sim.state_init
    df_forcing = sim.forcing

    # Run the simulation
    sim.run()

    # use SuPy function to save results
    with open(yaml_path, 'r') as f:
        yaml_dict = yaml.load(f, Loader=yaml.SafeLoader)

    sim.save(yaml_dict['model']['control']['output_file'])
    # sp.save_supy(df_output, df_state_final, path_dir_save = yaml_dict['model']['control']['output_file'])

    # --- plot results --- #
    if plotornot == 1:
        a = list(df_forcing.iloc[[1]].index)
        b = list(df_forcing.iloc[[2]].index)
        # resolutionfilesin = int((b[0]-a[0]).total_seconds())
        
        plotnml = f90nml.read(pathtoplugin + '/plot.nml')
        plotbasic = plotnml['plot']['plotbasic']
        # choosegridbasic = plotnml['plot']['choosegridbasic']
        # chooseyearbasic = plotnml['plot']['chooseyearbasic']
        fileoutputpath = yaml_dict['model']['control']['output_file']
        # fileinputpath = nml['runcontrol']['fileinputpath']
        # timeaggregation = 60
        multiplemetfiles = 0 # nml['runcontrol']['multiplemetfiles']
        plotmonthlystat = plotnml['plot']['plotmonthlystat']
        # choosegridstat = plotnml['plot']['choosegridstat']
        # chooseyearstat = plotnml['plot']['chooseyearstat']
        # TimeCol_plot = np.array([1, 2, 3, 4]) - 1
        # SumCol_plot = np.array([14]) - 1
        # LastCol_plot = np.array([16]) - 1

        YYYY = df_forcing.index[0].year

        gridcode = df_state_init.index[0]  # for plotting
        if multiplemetfiles == 0:  # one file
            met_data_file = yaml_dict['model']['control']['forcing_file']['value']

        suews_out = fileoutputpath + filecode + str(gridcode) + '_' + str(YYYY) + '_SUEWS_' + str(60) + '.txt'
        
        df_output_suews = suewsdataprocessing.SUEWS_txt_to_df(suews_out)
        df_met_forcing = suewsdataprocessing.SUEWS_met_txt_to_df(met_data_file)
       
        if plotbasic == 1:
            pl.plotbasic(df_output_suews, df_met_forcing)
            
        if plotmonthlystat == 1:
            pl.plotmonthlystatistics(df_output_suews, df_met_forcing)

        if plotmonthlystat == 1:
            plt.show()

        if plotbasic == 1:
            plt.show()
    else:
        print("No plots generated - No matplotlib installed")
