
import numpy as np
from daylen import daylen
from ...Utilities.SEBESOLWEIGCommonFiles.clearnessindex_2013b import clearnessindex_2013b
from ...Utilities.SEBESOLWEIGCommonFiles.diffusefraction import diffusefraction
from ...Utilities.SEBESOLWEIGCommonFiles.shadowingfunction_wallheight_13 import shadowingfunction_wallheight_13
from ...Utilities.SEBESOLWEIGCommonFiles.shadowingfunction_wallheight_23 import shadowingfunction_wallheight_23
from gvf_2015a import gvf_2015a
from cylindric_wedge import cylindric_wedge
from TsWaveDelay_2015a import TsWaveDelay_2015a
from Kup_veg_2015a import Kup_veg_2015a
from Lside_veg_v2015a import Lside_veg_v2015a
from Kside_veg_v2015a import Kside_veg_v2015a

def Solweig_2015a_calc(i, dsm, scale, rows, cols, svf, svfN, svfW, svfE, svfS, svfveg, svfNveg, svfEveg, svfSveg,
                       svfWveg, svfaveg, svfEaveg, svfSaveg, svfWaveg, svfNaveg, vegdem, vegdem2, albedo_b, absK, absL,
                       ewall, Fside, Fup, altitude, azimuth, zen, jday, usevegdem, onlyglobal, buildings, location, psi,
                       landcover, lc_grid, dectime, altmax, dirwalls, walls, cyl, elvis, Ta, RH, radG, radD, radI, P,
                       amaxvalue, bush, Twater, TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST,
                       TmaxLST_wall, first, second, svfalfa, svfbuveg, firstdaytime, timeadd, timeaddE, timeaddS,
                       timeaddW, timeaddN, timestepdec, Tgmap1, Tgmap1E, Tgmap1S, Tgmap1W, Tgmap1N, CI):

    # This is the core function of the SOLWEIG model
    # 2016-Aug-28
    # Fredrik Lindberg, fredrikl@gvc.gu.se
    # Goteborg Urban Climate Group
    # Gothenburg University
    #
    # Input variables:
    # dsm = digital surface model
    # scale = height to pixel size (2m pixel gives scale = 0.5)
    # header = ESRI Ascii Grid header
    # sizey,sizex = no. of pixels in x and y
    # svf,svfN,svfW,svfE,svfS = SVFs for building and ground
    # svfveg,svfNveg,svfEveg,svfSveg,svfWveg = Veg SVFs blocking sky
    # svfaveg,svfEaveg,svfSaveg,svfWaveg,svfNaveg = Veg SVFs blocking buildings
    # vegdem = Vegetation canopy DSM
    # vegdem2 = Vegetation trunk zone DSM
    # albedo_b = buildings
    # absK = human absorption coefficient for shortwave radiation
    # absL = human absorption coefficient for longwave radiation
    # ewall = Emissivity of building walls
    # Fside = The angular factors between a person and the surrounding surfaces
    # Fup = The angular factors between a person and the surrounding surfaces
    # altitude = Sun altitude (degree)
    # azimuth = Sun azimuth (degree)
    # zen = Sun zenith angle (radians)
    # jday = day of year
    # usevegdem = use vegetation scheme
    # onlyglobal = calculate dir and diff from global
    # buildings = Boolena grid to identify building pixels
    # location = geographic location
    # height = height of measurements point
    # psi = 1 - Transmissivity of shortwave through vegetation
    # output = output settings
    # fileformat = fileformat of output grids
    # landcover = use landcover scheme !!!NEW IN 2015a!!!
    # sensorheight = Sensorheight of wind sensor
    # lc_grid = grid with landcoverclasses
    # lc_class = table with landcover properties
    # dectime = decimal time
    # altmax = maximum sun altitude
    # dirwalls = aspect of walls
    # walls = one pixel row outside building footprints
    # cyl = consider man as cylinder instead of cude

    # # # Core program start # # #
    # for i in np.arange(1., (length(altitude))+1): ## loop move outside

    # %Instrument offset in degrees
    t = 0.

    # %Stefan Bolzmans Constant
    SBC = 5.67051e-8

    # Find sunrise decimal hour - new from 2014a
    _, _, _, SNUP = daylen(jday, location['latitude'])

    # Vapor pressure
    ea = 6.107 * 10 ** ((7.5 * Ta) / (237.3 + Ta)) * (RH / 100.)

    # Determination of clear - sky emissivity from Prata (1996)
    msteg = 46.5 * (ea / (Ta + 273.15))
    esky = (1 - (1 + msteg) * np.exp(-((1.2 + 3.0 * msteg) ** 0.5))) + elvis  # -0.04 old error from Jonsson et al.2006

    if altitude > 0: # # # # # # DAYTIME # # # # # #
        # Clearness Index on Earth's surface after Crawford and Dunchon (1999) with a correction
        #  factor for low sun elevations after Lindberg et al.(2008)
        I0, CI, Kt, I0et, CIuncorr = clearnessindex_2013b(zen, jday, Ta, RH / 100., radG, location, P)
        if (CI > 1) or (CI == np.inf):
            CI = 1

        # Estimation of radD and radI if not measured after Reindl et al.(1990)
        if onlyglobal == 1:
            radI, radD = diffusefraction(radG, altitude, Kt, Ta, RH)

        # Shadow  images
        if usevegdem == 1:
            # print str(vegdem)
            # print str(vegdem2)
            vegsh, sh, _, wallsh, wallsun, wallshve, _, facesun = shadowingfunction_wallheight_23(dsm, vegdem, vegdem2,
                                        azimuth, altitude, scale, amaxvalue, bush, walls, dirwalls * np.pi / 180.)
            shadow = sh - (1 - vegsh) * (1 - psi)
        else:
            sh, wallsh, wallsun, facesh, facesun = shadowingfunction_wallheight_13(dsm, azimuth, altitude, scale,
                                                                                   walls, dirwalls * np.pi / 180.)
            shadow = sh

        # # # Surface temperature parameterisation during daytime # # # #
        # new using max sun alt.instead of  dfm
        Tgamp = (TgK * altmax - Tstart) + Tstart
        Tgampwall = (TgK_wall * altmax - (Tstart_wall)) + (Tstart_wall)
        Tg = Tgamp * np.sin((((dectime - np.floor(dectime)) - SNUP / 24) / (TmaxLST / 24 - SNUP / 24)) * np.pi / 2) + Tstart  # 2015 a, based on max sun altitude
        Tgwall = Tgampwall * np.sin((((dectime - np.floor(dectime)) - SNUP / 24) / (TmaxLST_wall / 24 - SNUP / 24)) * np.pi / 2) + (Tstart_wall)  # 2015a, based on max sun altitude

        if Tgwall < 0:  # temporary for removing low Tg during morning 20130205
            # Tg = 0
            Tgwall = 0

        # New estimation of Tg reduction for non - clear situation based on Reindl et al.1990
        radI0, _ = diffusefraction(I0, altitude, 1., Ta, RH)
        corr = 0.1473 * np.log(90 - (zen / np.pi * 180)) + 0.3454  # 20070329 correction of lat, Lindberg et al. 2008
        CI_Tg = (radI / radI0) + (1 - corr)
        if (CI_Tg > 1) or (CI_Tg == np.inf):
            CI_Tg = 1
        Tg = Tg * CI_Tg  # new estimation
        Tgwall = Tgwall * CI_Tg
        if landcover == 1:
            Tg[Tg < 0] = 0  # temporary for removing low Tg during morning 20130205

        # Tw = Tg

        # # # # Ground View Factors # # # #
        gvfLup, gvfalb, gvfalbnosh, gvfLupE, gvfalbE, gvfalbnoshE, gvfLupS, gvfalbS, gvfalbnoshS, gvfLupW, gvfalbW,\
        gvfalbnoshW, gvfLupN, gvfalbN, gvfalbnoshN = gvf_2015a(wallsun, walls, buildings, scale, shadow, first,
                second, dirwalls, Tg, Tgwall, Ta, emis_grid, ewall, alb_grid, SBC, albedo_b, rows, cols,
                                                                 Twater, lc_grid, landcover)

        # # # # Lup, daytime # # # #
        # Surface temperature wave delay - new as from 2014a
        Lup, timeadd, Tgmap1 = TsWaveDelay_2015a(gvfLup, firstdaytime, timeadd, timestepdec, Tgmap1)
        LupE, timeaddE, Tgmap1E = TsWaveDelay_2015a(gvfLupE, firstdaytime, timeaddE, timestepdec, Tgmap1E)
        LupS, timeaddS, Tgmap1S = TsWaveDelay_2015a(gvfLupS, firstdaytime, timeaddS, timestepdec, Tgmap1S)
        LupW, timeaddW, Tgmap1W = TsWaveDelay_2015a(gvfLupW, firstdaytime, timeaddW, timestepdec, Tgmap1W)
        LupN, timeaddN, Tgmap1N = TsWaveDelay_2015a(gvfLupN, firstdaytime, timeaddN, timestepdec, Tgmap1N)

        # Building height angle from svf
        F_sh = cylindric_wedge(zen, svfalfa, rows, cols)  # Fraction shadow on building walls based on sun altitude and svf
        F_sh[np.isnan(F_sh)] = 0.5

        # # # # # # # Calculation of shortwave daytime radiative fluxes # # # # # # #
        Kdown = radI * shadow * np.sin(altitude * (np.pi / 180)) + radD * svfbuveg + albedo_b * (1 - svfbuveg) * \
                            (radG * (1 - F_sh) + radD * F_sh) # *sin(altitude(i) * (pi / 180))

        Kup, KupE, KupS, KupW, KupN = Kup_veg_2015a(radI, radD, radG, altitude, svfbuveg, albedo_b, F_sh, gvfalb,
                    gvfalbE, gvfalbS, gvfalbW, gvfalbN, gvfalbnosh, gvfalbnoshE, gvfalbnoshS, gvfalbnoshW, gvfalbnoshN)

        Keast, Ksouth, Kwest, Knorth, KsideI = Kside_veg_v2015a(radI, radD, radG, shadow, svfS, svfW, svfN, svfE,
                    svfEveg, svfSveg, svfWveg, svfNveg, azimuth, altitude, psi, t, albedo_b, F_sh, KupE, KupS, KupW,
                    KupN, cyl)

        firstdaytime = 0

    else:  # # # # # # # NIGHTTIME # # # # # # # #

        Tgwall = 0
        # CI_Tg = -999  # F_sh = []

        # Nocturnal Kfluxes set to 0
        Knight = np.zeros((rows, cols))
        Kdown = np.zeros((rows, cols))
        Kwest = np.zeros((rows, cols))
        Kup = np.zeros((rows, cols))
        Keast = np.zeros((rows, cols))
        Ksouth = np.zeros((rows, cols))
        Knorth = np.zeros((rows, cols))
        KsideI = np.zeros((rows, cols))
        F_sh = np.zeros((rows, cols))
        Tg = np.zeros((rows, cols))
        shadow = np.zeros((rows, cols))

        # # # # Lup # # # #
        Lup = SBC * emis_grid * ((Knight + Ta + Tg + 273.15) ** 4)
        if landcover == 1:
            Lup[lc_grid == 3] = SBC * 0.98 * (Twater + 273.15) ** 4  # nocturnal Water temp

        LupE = Lup
        LupS = Lup
        LupW = Lup
        LupN = Lup

        I0 = 0
        timeadd = 0
        firstdaytime = 1

    # # # # Ldown # # # #
    Ldown = (svf + svfveg - 1) * esky * SBC * ((Ta + 273.15) ** 4) + (2 - svfveg - svfaveg) * ewall * SBC * \
                    ((Ta + 273.15) ** 4) + (svfaveg - svf) * ewall * SBC * ((Ta + 273.15 + Tgwall) ** 4) + \
                    (2 - svf - svfveg) * (1 - ewall) * esky * SBC * ((Ta + 273.15) ** 4)  # Jonsson et al.(2006)
    # Ldown = Ldown - 25 # Shown by Jonsson et al.(2006) and Duarte et al.(2006)

    if CI < 0.95:  # non - clear conditions
        c = 1 - CI
        Ldown = Ldown * (1 - c) + c * ((svf + svfveg - 1) * SBC * ((Ta + 273.15) ** 4) + (2 - svfveg - svfaveg) *
                ewall * SBC * ((Ta + 273.15) ** 4) + (svfaveg - svf) * ewall * SBC * ((Ta + 273.15 + Tgwall) ** 4) +
                (2 - svf - svfveg) * (1 - ewall) * SBC * ((Ta + 273.15) ** 4))  # NOT REALLY TESTED!!! BUT MORE CORRECT?

    # # # # Lside # # # #
    Least, Lsouth, Lwest, Lnorth = Lside_veg_v2015a(svfS, svfW, svfN, svfE, svfEveg, svfSveg, svfWveg, svfNveg,
                    svfEaveg, svfSaveg, svfWaveg, svfNaveg, azimuth, altitude, Ta, Tgwall, SBC, ewall, Ldown,
                                                      esky, t, F_sh, CI, LupE, LupS, LupW, LupN)

    # # # # Calculation of radiant flux density and Tmrt # # # #
    if cyl == 1:  # Human body considered as an cyliner
        Sstr = absK * (KsideI + (Kdown + Kup) * Fup + (Knorth + Keast + Ksouth + Kwest) * Fside) + absL * \
                        (Ldown * Fup + Lup * Fup + Lnorth * Fside + Least * Fside + Lsouth * Fside + Lwest * Fside)
    # Knorth = nan Ksouth = nan Kwest = nan Keast = nan
    else: # Human body considered as a standing cube
        Sstr = absK * ((Kdown + Kup) * Fup + (Knorth + Keast + Ksouth + Kwest) * Fside) +absL * \
                        (Ldown * Fup + Lup * Fup + Lnorth * Fside + Least * Fside + Lsouth * Fside + Lwest * Fside)
    # Sstr = absK * (Kdown * Fup + Kup * Fup + Knorth * Fside + Keast * Fside + Ksouth * Fside + Kwest * Fside)...
    # +absL * (Ldown * Fup + Lup * Fup + Lnorth * Fside + Least * Fside + Lsouth * Fside + Lwest * Fside)
    # KsideI = nan

    Tmrt = np.sqrt(np.sqrt((Sstr / (absL * SBC)))) - 273.2
    # Sstr = absK * (Kdown * Fup + Kup * Fup + Knorth * Fside + Keast * Fside + Ksouth * Fside + Kwest * Fside)...
    # +absL * (Ldown * Fup + Lup * Fup + Lnorth * Fside + Least * Fside + Lsouth * Fside + Lwest * Fside)
    # Tmrt = sqrt(sqrt((Sstr / (absL * SBC)))) - 273.2

    return Tmrt, Kdown, Kup, Ldown, Lup, Tg, ea, esky, I0, CI, shadow, firstdaytime, timestepdec, \
           timeadd, Tgmap1, timeaddE, Tgmap1E, timeaddS, Tgmap1S, timeaddW, Tgmap1W, timeaddN, Tgmap1N, \
           Keast, Ksouth, Kwest, Knorth, Least, Lsouth, Lwest, Lnorth, KsideI