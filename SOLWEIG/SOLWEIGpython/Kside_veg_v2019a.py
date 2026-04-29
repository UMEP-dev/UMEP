from __future__ import absolute_import
import numpy as np
from .Kvikt_veg import Kvikt_veg

def Kside_veg_v2019a(radI,radD,radG,shadow,svfS,svfW,svfN,svfE,svfEveg,svfSveg,svfWveg,svfNveg,azimuth,altitude,psi,t,albedo,F_sh,KupE,KupS,KupW,KupN,cyl,lv,ani,diffsh,rows,cols):

    # New reflection equation 2012-05-25
    vikttot=4.4897
    aziE=azimuth+t
    aziS=azimuth-90+t
    aziW=azimuth-180+t
    aziN=azimuth-270+t
    deg2rad=np.pi/180
    KsideD = np.zeros((rows, cols))

    ### Direct radiation ###
    if cyl == 1: ### Kside with cylinder ###
        KsideI=shadow*radI*np.cos(altitude*deg2rad)
        KeastI=0;KsouthI=0;KwestI=0;KnorthI=0
    else: ### Kside with weights ###
        if azimuth > (360-t)  or  azimuth <= (180-t):
            KeastI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziE*deg2rad)
        else:
            KeastI=0
        if azimuth > (90-t)  and  azimuth <= (270-t):
            KsouthI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziS*deg2rad)
        else:
            KsouthI=0
        if azimuth > (180-t)  and  azimuth <= (360-t):
            KwestI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziW*deg2rad)
        else:
            KwestI=0
        if azimuth <= (90-t)  or  azimuth > (270-t):
            KnorthI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziN*deg2rad)
        else:
            KnorthI=0

        KsideI=shadow*0
    
    ### Diffuse and reflected radiation ###
    [viktveg,viktwall]=Kvikt_veg(svfE,svfEveg,vikttot)
    svfviktbuvegE=(viktwall+(viktveg)*(1-psi))

    [viktveg,viktwall]=Kvikt_veg(svfS,svfSveg,vikttot)
    svfviktbuvegS=(viktwall+(viktveg)*(1-psi))

    [viktveg,viktwall]=Kvikt_veg(svfW,svfWveg,vikttot)
    svfviktbuvegW=(viktwall+(viktveg)*(1-psi))

    [viktveg,viktwall]=Kvikt_veg(svfN,svfNveg,vikttot)
    svfviktbuvegN=(viktwall+(viktveg)*(1-psi))

    ### Anisotropic Diffuse Radiation after Perez et al. 1993 ###
    if ani == 1:

        aniAlt = lv[0][:, 0]
        aniAzi = lv[0][:, 1]
        aniLum = lv[0][:, 2]

        phiVar = np.zeros((145, 1))

        radTot = np.zeros(1)

        for ix in range(0, 145):    # Azimuth delta
            if ix < 60:
                aziDel = 12
            elif ix >= 60 and ix < 108:
                aziDel = 15
            elif ix >= 108 and ix < 126:
                aziDel = 20
            elif ix >= 126 and ix < 138:
                aziDel = 30
            elif ix >= 138 and ix < 144:
                aziDel = 60
            elif ix == 144:
                aziDel = 360

            phiVar[ix] = (aziDel * deg2rad) * (np.sin((aniAlt[ix] + 6) * deg2rad) - np.sin((aniAlt[ix] - 6) * deg2rad)) # Solid angle / Steradian

            radTot = radTot + (aniLum[ix] * phiVar[ix] * np.sin(aniAlt[ix] * deg2rad)) # Radiance fraction normalization

        lumChi = (aniLum * radD) / radTot # Radiance fraction normalization

        if cyl == 1:
            for idx in range(0, 145):
                anglIncC = np.cos(aniAlt[idx] * deg2rad) * np.cos(0) * np.sin(np.pi / 2) + np.sin(
                    aniAlt[idx] * deg2rad) * np.cos(np.pi / 2)                                    # Angle of incidence, np.cos(0) because cylinder - always perpendicular
                KsideD = KsideD + diffsh[:, :, idx] * lumChi[idx] * anglIncC * phiVar[idx]        # Diffuse vertical radiation
            Keast  = (albedo * (svfviktbuvegE * (radG * (1 - F_sh) + radD * F_sh)) + KupE) * 0.5
            Ksouth = (albedo * (svfviktbuvegS * (radG * (1 - F_sh) + radD * F_sh)) + KupS) * 0.5
            Kwest  = (albedo * (svfviktbuvegW * (radG * (1 - F_sh) + radD * F_sh)) + KupW) * 0.5
            Knorth = (albedo * (svfviktbuvegN * (radG * (1 - F_sh) + radD * F_sh)) + KupN) * 0.5
        else: # Box
            diffRadE = np.zeros((rows, cols)); diffRadS = np.zeros((rows, cols)); diffRadW = np.zeros((rows, cols)); diffRadN = np.zeros((rows, cols))

            for idx in range(0, 145):
                if aniAzi[idx] <= (180):
                    anglIncE = np.cos(aniAlt[idx] * deg2rad) * np.cos((90 - aniAzi[idx]) * deg2rad) * np.sin(
                        np.pi / 2) + np.sin(
                        aniAlt[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadE = diffRadE + diffsh[:, :, idx] * lumChi[idx] * anglIncE * phiVar[idx] #* 0.5

                if aniAzi[idx] > (90) and aniAzi[idx] <= (270):
                    anglIncS = np.cos(aniAlt[idx] * deg2rad) * np.cos((180 - aniAzi[idx]) * deg2rad) * np.sin(
                        np.pi / 2) + np.sin(
                        aniAlt[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadS = diffRadS + diffsh[:, :, idx] * lumChi[idx] * anglIncS * phiVar[idx] #* 0.5

                if aniAzi[idx] > (180) and aniAzi[idx] <= (360):
                    anglIncW = np.cos(aniAlt[idx] * deg2rad) * np.cos((270 - aniAzi[idx]) * deg2rad) * np.sin(
                        np.pi / 2) + np.sin(
                        aniAlt[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadW = diffRadW + diffsh[:, :, idx] * lumChi[idx] * anglIncW * phiVar[idx] #* 0.5

                if aniAzi[idx] > (270) or aniAzi[idx] <= (90):
                    anglIncN = np.cos(aniAlt[idx] * deg2rad) * np.cos((0 - aniAzi[idx]) * deg2rad) * np.sin(
                        np.pi / 2) + np.sin(
                        aniAlt[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadN = diffRadN + diffsh[:, :, idx] * lumChi[idx] * anglIncN * phiVar[idx] #* 0.5

            KeastDG = diffRadE + (albedo * (svfviktbuvegE * (radG * (1 - F_sh) + radD * F_sh)) + KupE) * 0.5
            Keast = KeastI + KeastDG

            KsouthDG = diffRadS + (albedo * (svfviktbuvegS * (radG * (1 - F_sh) + radD * F_sh)) + KupS) * 0.5
            Ksouth = KsouthI + KsouthDG

            KwestDG = diffRadW + (albedo * (svfviktbuvegW * (radG * (1 - F_sh) + radD * F_sh)) + KupW) * 0.5
            Kwest = KwestI + KwestDG

            KnorthDG = diffRadN + (albedo * (svfviktbuvegN * (radG * (1 - F_sh) + radD * F_sh)) + KupN) * 0.5
            Knorth = KnorthI + KnorthDG

    else:
        KeastDG = (radD * (1 - svfviktbuvegE) + albedo * (
        svfviktbuvegE * (radG * (1 - F_sh) + radD * F_sh)) + KupE) * 0.5
        Keast = KeastI + KeastDG

        KsouthDG = (radD * (1 - svfviktbuvegS) + albedo * (
        svfviktbuvegS * (radG * (1 - F_sh) + radD * F_sh)) + KupS) * 0.5
        Ksouth = KsouthI + KsouthDG

        KwestDG = (radD * (1 - svfviktbuvegW) + albedo * (
        svfviktbuvegW * (radG * (1 - F_sh) + radD * F_sh)) + KupW) * 0.5
        Kwest = KwestI + KwestDG

        KnorthDG = (radD * (1 - svfviktbuvegN) + albedo * (
        svfviktbuvegN * (radG * (1 - F_sh) + radD * F_sh)) + KupN) * 0.5
        Knorth = KnorthI + KnorthDG

    return Keast,Ksouth,Kwest,Knorth,KsideI,KsideD