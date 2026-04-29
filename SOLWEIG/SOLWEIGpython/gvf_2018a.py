import numpy as np
from .sunonsurface_2018a import sunonsurface_2018a
# import matplotlib.pyplot as plt


def gvf_2018a(wallsun, walls, buildings, scale, shadow, first, second, dirwalls, Tg, Tgwall, Ta, emis_grid, ewall,
              alb_grid, SBC, albedo_b, rows, cols, Twater, lc_grid, landcover):
    azimuthA = np.arange(5, 359, 20)  # Search directions for Ground View Factors (GVF)

    #### Ground View Factors ####
    gvfLup = np.zeros((rows, cols))
    gvfalb = np.zeros((rows, cols))
    gvfalbnosh = np.zeros((rows, cols))
    gvfLupE = np.zeros((rows, cols))
    gvfLupS = np.zeros((rows, cols))
    gvfLupW = np.zeros((rows, cols))
    gvfLupN = np.zeros((rows, cols))
    gvfalbE = np.zeros((rows, cols))
    gvfalbS = np.zeros((rows, cols))
    gvfalbW = np.zeros((rows, cols))
    gvfalbN = np.zeros((rows, cols))
    gvfalbnoshE = np.zeros((rows, cols))
    gvfalbnoshS = np.zeros((rows, cols))
    gvfalbnoshW = np.zeros((rows, cols))
    gvfalbnoshN = np.zeros((rows, cols))
    gvfSum = np.zeros((rows, cols))

    #  sunwall=wallinsun_2015a(buildings,azimuth(i),shadow,psi(i),dirwalls,walls);
    sunwall = (wallsun / walls * buildings) == 1  # new as from 2015a

    for j in np.arange(0, azimuthA.__len__()):
        _, gvfLupi, gvfalbi, gvfalbnoshi, gvf2 = sunonsurface_2018a(azimuthA[j], scale, buildings, shadow, sunwall,
                                                                    first,
                                                                    second, dirwalls * np.pi / 180, walls, Tg, Tgwall,
                                                                    Ta,
                                                                    emis_grid, ewall, alb_grid, SBC, albedo_b, Twater,
                                                                    lc_grid, landcover)

        gvfLup = gvfLup + gvfLupi
        gvfalb = gvfalb + gvfalbi
        gvfalbnosh = gvfalbnosh + gvfalbnoshi
        gvfSum = gvfSum + gvf2

        if (azimuthA[j] >= 0) and (azimuthA[j] < 180):
            gvfLupE = gvfLupE + gvfLupi
            gvfalbE = gvfalbE + gvfalbi
            gvfalbnoshE = gvfalbnoshE + gvfalbnoshi

        if (azimuthA[j] >= 90) and (azimuthA[j] < 270):
            gvfLupS = gvfLupS + gvfLupi
            gvfalbS = gvfalbS + gvfalbi
            gvfalbnoshS = gvfalbnoshS + gvfalbnoshi

        if (azimuthA[j] >= 180) and (azimuthA[j] < 360):
            gvfLupW = gvfLupW + gvfLupi
            gvfalbW = gvfalbW + gvfalbi
            gvfalbnoshW = gvfalbnoshW + gvfalbnoshi

        if (azimuthA[j] >= 270) or (azimuthA[j] < 90):
            gvfLupN = gvfLupN + gvfLupi
            gvfalbN = gvfalbN + gvfalbi
            gvfalbnoshN = gvfalbnoshN + gvfalbnoshi

    gvfLup = gvfLup / azimuthA.__len__() + SBC * emis_grid * (Ta + 273.15) ** 4
    gvfalb = gvfalb / azimuthA.__len__()
    gvfalbnosh = gvfalbnosh / azimuthA.__len__()

    gvfLupE = gvfLupE / (azimuthA.__len__() / 2) + SBC * emis_grid * (Ta + 273.15) ** 4
    gvfLupS = gvfLupS / (azimuthA.__len__() / 2) + SBC * emis_grid * (Ta + 273.15) ** 4
    gvfLupW = gvfLupW / (azimuthA.__len__() / 2) + SBC * emis_grid * (Ta + 273.15) ** 4
    gvfLupN = gvfLupN / (azimuthA.__len__() / 2) + SBC * emis_grid * (Ta + 273.15) ** 4

    gvfalbE = gvfalbE / (azimuthA.__len__() / 2)
    gvfalbS = gvfalbS / (azimuthA.__len__() / 2)
    gvfalbW = gvfalbW / (azimuthA.__len__() / 2)
    gvfalbN = gvfalbN / (azimuthA.__len__() / 2)

    gvfalbnoshE = gvfalbnoshE / (azimuthA.__len__() / 2)
    gvfalbnoshS = gvfalbnoshS / (azimuthA.__len__() / 2)
    gvfalbnoshW = gvfalbnoshW / (azimuthA.__len__() / 2)
    gvfalbnoshN = gvfalbnoshN / (azimuthA.__len__() / 2)

    gvfNorm = gvfSum / (azimuthA.__len__())
    gvfNorm[buildings == 0] = 1
    
    return gvfLup, gvfalb, gvfalbnosh, gvfLupE, gvfalbE, gvfalbnoshE, gvfLupS, gvfalbS, gvfalbnoshS, gvfLupW, gvfalbW, gvfalbnoshW, gvfLupN, gvfalbN, gvfalbnoshN, gvfSum, gvfNorm