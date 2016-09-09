import numpy as np

def Tgmaps_v1(lc_grid, lc_class):

    #Tgmaps_v1 Populates grids with cooeficients for Tg wave
    #   Detailed explanation goes here

    id = np.unique(lc_grid)
    TgK = np.copy(lc_grid)
    Tstart = np.copy(lc_grid)
    alb_grid = np.copy(lc_grid)
    emis_grid = np.copy(lc_grid)
    TmaxLST = np.copy(lc_grid)

    for i in np.arange(0, id.__len__()):
        row = (lc_class[:, 0] == id[i])
        Tstart[Tstart == id[i]] = lc_class[row, 4]
        alb_grid[alb_grid == id[i]] = lc_class[row, 1]
        emis_grid[emis_grid == id[i]] = lc_class[row, 2]
        TmaxLST[TmaxLST == id[i]] = lc_class[row, 5]
        TgK[TgK == id[i]] = lc_class[row, 3]

    wall_pos = np.where(lc_class[:, 0] == 99)
    TgK_wall = lc_class[wall_pos, 3]
    Tstart_wall = lc_class[wall_pos, 4]
    TmaxLST_wall = lc_class[wall_pos, 5]

    return TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST, TmaxLST_wall
