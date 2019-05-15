from __future__ import print_function
from __future__ import absolute_import
from builtins import str
__author__ = 'xlinfr'

def wrapper(pathtoplugin):

    import supy as sp
    from pathlib import Path
    import numpy as np
    from . import suewsdataprocessing
    from . import suewsplottingpandas
    import subprocess
    from ..Utilities import f90nml
    import os
    import sys
    import stat
    sys.path.append(pathtoplugin)

    try:
        import matplotlib.pyplot as plt
        nomatplot = 0
    except ImportError:
        nomatplot = 1
        pass

    # su = suewsdataprocessing.SuewsDataProcessing()
    plp = suewsplottingpandas.SuewsPlottingPandas()

    # supy
    path_runcontrol = Path(pathtoplugin + '/RunControl.nml')
    df_state_init = sp.init_supy(path_runcontrol)
    grid = df_state_init.index[0]
    df_forcing = sp.load_forcing_grid(path_runcontrol, grid)
    df_output, df_state_final = sp.run_supy(df_forcing, df_state_init)
    df_output_suews = df_output['SUEWS']
    df_output_suews_rsmp = df_output_suews.loc[grid].resample('1h').mean()
    sp.save_supy(df_output, df_state_final, path_runcontrol=path_runcontrol)

    # pandasplotting
    plotnml = f90nml.read(pathtoplugin + '/plot.nml')
    plotforcing = plotnml['plot']['plotforcing']
    plotbasic = plotnml['plot']['plotbasic']
    plotmonthlystat = plotnml['plot']['plotmonthlystat']

    if nomatplot == 0:
        plt.close('all')
        if plotbasic == 1:
            if plotmonthlystat == 1:
                plp.plotmonthly(df_output_suews_rsmp, grid)
            plp.plotbasic(df_output_suews_rsmp, grid)
            # plt.show()
        if plotforcing == 1:
            plp.plotforcing(df_forcing)
            # plt.show()
    plt.show()

    del df_state_init
    del df_forcing
    del df_state_final
    del df_output, df_output_suews, df_output_suews_rsmp

    # Remove 5 minutes files
    nml = f90nml.read(pathtoplugin + '/RunControl.nml')
    fileoutputpath = nml['runcontrol']['fileoutputpath']
    for file in os.listdir(fileoutputpath):
        if file.endswith("_5.txt"):
            os.remove(os.path.join(fileoutputpath, file))


