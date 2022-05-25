from __future__ import absolute_import
import numpy as np
from .Kvikt_veg import Kvikt_veg
from . import sunlit_shaded_patches

def Kside_veg_v2022a(radI,radD,radG,
                    shadow,svfS,svfW,svfN,svfE,svfEveg,svfSveg,svfWveg,svfNveg,
                    azimuth,altitude,psi,t,albedo,F_sh,
                    KupE,KupS,KupW,KupN,
                    cyl,lv,anisotropic_diffuse,diffsh,rows,cols,asvf,
                    shmat, vegshmat, vbshvegshmat):

    # New reflection equation 2012-05-25
    vikttot=4.4897
    aziE=azimuth+t
    aziS=azimuth-90+t
    aziW=azimuth-180+t
    aziN=azimuth-270+t
    deg2rad=np.pi/180
    KsideD = np.zeros((rows, cols))
    Kref_sun = np.zeros((rows, cols))
    Kref_sh = np.zeros((rows, cols))
    Kref_veg = np.zeros((rows, cols))
    Kside = np.zeros((rows, cols))

    Kref_veg_n = np.zeros((rows, cols))
    Kref_veg_s = np.zeros((rows, cols))
    Kref_veg_e = np.zeros((rows, cols))
    Kref_veg_w = np.zeros((rows, cols))

    Kref_sh_n = np.zeros((rows, cols))
    Kref_sh_s = np.zeros((rows, cols))
    Kref_sh_e = np.zeros((rows, cols))
    Kref_sh_w = np.zeros((rows, cols))

    Kref_sun_n = np.zeros((rows, cols))
    Kref_sun_s = np.zeros((rows, cols))
    Kref_sun_e = np.zeros((rows, cols))
    Kref_sun_w = np.zeros((rows, cols))

    KeastRef = np.zeros((rows, cols)); KwestRef = np.zeros((rows, cols)); KnorthRef = np.zeros((rows, cols)); KsouthRef = np.zeros((rows, cols))
    diffRadE = np.zeros((rows, cols)); diffRadS = np.zeros((rows, cols)); diffRadW = np.zeros((rows, cols)); diffRadN = np.zeros((rows, cols))

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
    if anisotropic_diffuse == 1:

        anisotropic_sky = True

        patch_altitude = lv[:, 0]
        patch_azimuth = lv[:, 1]
        if anisotropic_sky:
            patch_luminance = lv[:, 2]
        else:
            patch_luminance = np.zeros((patch_altitude.shape[0]))
            patch_luminance[:] = 1.0/patch_luminance.shape[0]

        # Unique altitudes for patches
        skyalt, skyalt_c = np.unique(patch_altitude, return_counts=True)

        radTot = np.zeros(1)

        # Calculation of steradian for each patch
        steradian = np.zeros((patch_altitude.shape[0]))
        for i in range(patch_altitude.shape[0]):
            # If there are more than one patch in a band
            if skyalt_c[skyalt == patch_altitude[i]] > 1:
                steradian[i] = ((360 / skyalt_c[skyalt == patch_altitude[i]]) * deg2rad) * (np.sin((patch_altitude[i] + patch_altitude[0]) * deg2rad) \
                - np.sin((patch_altitude[i] - patch_altitude[0]) * deg2rad))
            # If there is only one patch in band, i.e. 90 degrees
            else:
                steradian[i] = ((360 / skyalt_c[skyalt == patch_altitude[i]]) * deg2rad) * (np.sin((patch_altitude[i]) * deg2rad) \
                    - np.sin((patch_altitude[i-1] + patch_altitude[0]) * deg2rad))

            radTot += (patch_luminance[i] * steradian[i] * np.sin(patch_altitude[i] * deg2rad)) # Radiance fraction normalization

        lumChi = (patch_luminance * radD) / radTot # Radiance fraction normalization

        if cyl == 1:
            for idx in range(patch_azimuth.shape[0]):
                # Angle of incidence, np.cos(0) because cylinder - always perpendicular
                anglIncC = np.cos(patch_altitude[idx] * deg2rad) * np.cos(0) # * np.sin(np.pi / 2) \
                    # + np.sin(patch_altitude[idx] * deg2rad) * np.cos(np.pi / 2)
                # Diffuse vertical radiation
                KsideD += diffsh[:, :, idx] * lumChi[idx] * anglIncC * steradian[idx]

                # Shortwave reflected on sunlit surfaces
                # sunlit_surface = ((albedo * radG) / np.pi)
                sunlit_surface = ((albedo * (radI * np.cos(altitude * deg2rad)) + (radD * 0.5)) / np.pi)
                # Shortwave reflected on shaded surfaces and vegetation
                shaded_surface = ((albedo * radD * 0.5) / np.pi)
                
                # Shortwave radiation reflected on vegetation - based on diffuse shortwave radiation
                temp_vegsh = ((vegshmat[:,:,idx] == 0) | (vbshvegshmat[:,:,idx] == 0))
                Kref_veg += shaded_surface * temp_vegsh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)

                # Shortwave radiation reflected on buildings (shaded and sunlit) - based on global and diffuse shortwave radiation
                temp_vbsh = (1 - shmat[:,:,idx]) * vbshvegshmat[:,:,idx]
                temp_sh = (temp_vbsh == 1) # & (vbshvegshmat[:,:,idx] == 1)

                sunlit_patches, shaded_patches = sunlit_shaded_patches.shaded_or_sunlit(altitude, azimuth, patch_altitude[idx], patch_azimuth[idx], asvf)
                Kref_sun += sunlit_surface * sunlit_patches * temp_sh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)
                Kref_sh += shaded_surface * shaded_patches * temp_sh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)

            Kside = KsideI + KsideD + Kref_sun + Kref_sh + Kref_veg

            Keast = (KupE * 0.5)
            Kwest = (KupW * 0.5)
            Knorth = (KupN * 0.5)
            Ksouth = (KupS * 0.5)

            # Keast  = (albedo * (svfviktbuvegE * (radG * (1 - F_sh) + radD * F_sh)) + KupE) * 0.5
            # Ksouth = (albedo * (svfviktbuvegS * (radG * (1 - F_sh) + radD * F_sh)) + KupS) * 0.5
            # Kwest  = (albedo * (svfviktbuvegW * (radG * (1 - F_sh) + radD * F_sh)) + KupW) * 0.5
            # Knorth = (albedo * (svfviktbuvegN * (radG * (1 - F_sh) + radD * F_sh)) + KupN) * 0.5
        else: # Box
            diffRadE = np.zeros((rows, cols)); diffRadS = np.zeros((rows, cols)); diffRadW = np.zeros((rows, cols)); diffRadN = np.zeros((rows, cols))

            for idx in range(patch_azimuth.shape[0]):
                if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] <= 180):
                    anglIncE = np.cos(patch_altitude[idx] * deg2rad) * np.cos((90 - patch_azimuth[idx] + t) * deg2rad) # * np.sin(np.pi / 2) \
                        # + np.sin(patch_altitude[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadE += diffsh[:, :, idx] * lumChi[idx] * anglIncE * steradian[idx] #* 0.5

                if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] <= 270):
                    anglIncS = np.cos(patch_altitude[idx] * deg2rad) * np.cos((180 - patch_azimuth[idx] + t) * deg2rad) # * np.sin(np.pi / 2) \
                        # + np.sin(patch_altitude[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadS += diffsh[:, :, idx] * lumChi[idx] * anglIncS * steradian[idx] #* 0.5

                if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] <= 360):
                    anglIncW = np.cos(patch_altitude[idx] * deg2rad) * np.cos((270 - patch_azimuth[idx] + t) * deg2rad) # * np.sin(np.pi / 2) \
                        # + np.sin(patch_altitude[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadW += diffsh[:, :, idx] * lumChi[idx] * anglIncW * steradian[idx] #* 0.5

                if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] <= 90):
                    anglIncN = np.cos(patch_altitude[idx] * deg2rad) * np.cos((0 - patch_azimuth[idx] + t) * deg2rad) # * np.sin(np.pi / 2) \
                        # + np.sin(patch_altitude[idx] * deg2rad) * np.cos(np.pi / 2)
                    diffRadN += diffsh[:, :, idx] * lumChi[idx] * anglIncN * steradian[idx] #* 0.5
            
                # Shortwave reflected on sunlit surfaces
                # sunlit_surface = ((albedo * radG) / np.pi)
                sunlit_surface = ((albedo * (radI * np.cos(altitude * deg2rad)) + (radD * 0.5)) / np.pi)
                # Shortwave reflected on shaded surfaces and vegetation
                shaded_surface = ((albedo * radD * 0.5) / np.pi)
                
                # Shortwave radiation reflected on vegetation - based on diffuse shortwave radiation
                temp_vegsh = ((vegshmat[:,:,idx] == 0) | (vbshvegshmat[:,:,idx] == 0))
                Kref_veg += shaded_surface * temp_vegsh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)

                if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
                    Kref_veg_e += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((90 - patch_azimuth[idx] + t) * deg2rad)
                if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
                    Kref_veg_s += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((180 - patch_azimuth[idx] + t) * deg2rad)
                if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
                    Kref_veg_w += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((270 - patch_azimuth[idx] + t) * deg2rad)
                if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
                    Kref_veg_n += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((0 - patch_azimuth[idx] + t) * deg2rad)

                # Shortwave radiation reflected on buildings (shaded and sunlit) - based on global and diffuse shortwave radiation
                temp_vbsh = (1 - shmat[:,:,idx]) * vbshvegshmat[:,:,idx]
                temp_sh = (temp_vbsh == 1) # & (vbshvegshmat[:,:,idx] == 1)
                azimuth_difference = np.abs(azimuth - patch_azimuth[idx])

                if ((azimuth_difference > 90) and (azimuth_difference < 270)):
                    sunlit_patches, shaded_patches = sunlit_shaded_patches.shaded_or_sunlit(altitude, azimuth, patch_altitude[idx], patch_azimuth[idx], asvf)
                    Kref_sun += sunlit_surface * sunlit_patches * temp_sh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)
                    Kref_sh += shaded_surface * shaded_patches * temp_sh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)

                    if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
                        Kref_sun_e += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx] + t) * deg2rad)
                        Kref_sh_e += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx] + t) * deg2rad)
                    if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
                        Kref_sun_s += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx] + t) * deg2rad)
                        Kref_sh_s += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx] + t) * deg2rad)
                    if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
                        Kref_sun_w += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx] + t) * deg2rad)
                        Kref_sh_w += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx] + t) * deg2rad)
                    if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
                        Kref_sun_n += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx] + t) * deg2rad)
                        Kref_sh_n += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx] + t) * deg2rad)
                else:
                    Kref_sh += shaded_surface * temp_sh * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad)

                    if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
                        Kref_sh_e += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx] + t) * deg2rad)
                    if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
                        Kref_sh_s += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx] + t) * deg2rad)
                    if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
                        Kref_sh_w += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx] + t) * deg2rad)
                    if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
                        Kref_sh_n += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx] + t) * deg2rad)

            Keast = KeastI + diffRadE + Kref_sun_e + Kref_sh_e + Kref_veg_e + KupE * 0.5
            Kwest = KwestI + diffRadW + Kref_sun_w + Kref_sh_w + Kref_veg_w + KupW * 0.5
            Knorth = KnorthI + diffRadN + Kref_sun_n + Kref_sh_n + Kref_veg_n + KupN * 0.5
            Ksouth = KsouthI + diffRadS + Kref_sun_s + Kref_sh_s + Kref_veg_s + KupS * 0.5

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

    return Keast, Ksouth, Kwest, Knorth, KsideI, KsideD, Kside
    # return Keast, Ksouth, Kwest, Knorth, KsideI, KsideD, Kref_sh, Kref_sun, Kref_veg, Kside