import numpy as np
from copy import deepcopy
from . import emissivity_models
from . import patch_characteristics

''' This function combines the method to divide the sky vault into patches (Tregenza (1987) and Robinson & Stone (2004)) 
    and the approach by Unsworth & Monteith or Martin & Berdahl (1984) or Bliss (1961) to calculate emissivities of the 
    different parts of the sky vault. '''

def Lcyl_v2022a(esky, sky_patches, Ta, Tgwall, ewall, Lup, shmat, vegshmat, vbshvegshmat, solar_altitude, solar_azimuth, rows, cols, asvf):

    # Stefan-Boltzmann's Constant
    SBC = 5.67051e-8

    # Sky longwave radiation from emissivity based on Prata (1996)
    Ldown_prata = (esky * SBC * ((Ta + 273.15) ** 4))

    # Degrees to radians
    deg2rad = np.pi / 180

    # Unique altitudes for patches
    skyalt, skyalt_c = np.unique(sky_patches[:, 0], return_counts=True)
    # skyzen = 90-skyalt                  # Unique zeniths for the patches

    # Altitudes of the Robinson & Stone patches
    patch_altitude = sky_patches[:, 0]
    # Azimuths of the Robinson & Stone patches, used for box
    patch_azimuth = sky_patches[:, 1]
    
    emis_m = 2

    # Unsworth & Monteith (1975)
    if emis_m == 1:
        patch_emissivity_normalized, esky_band = emissivity_models.model1(sky_patches, esky, Ta)
    # Martin & Berdahl (1984)
    elif emis_m == 2:
        patch_emissivity_normalized, esky_band = emissivity_models.model2(sky_patches, esky, Ta)
    # Bliss (1961)
    elif emis_m == 3:
        patch_emissivity_normalized, esky_band = emissivity_models.model3(sky_patches, esky, Ta)

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

    # True = anisotropic sky, False = isotropic sky
    anisotropic_sky = True
    # anisotropic_sky = False

    # Longwave based on spectral flux density (divide by pi)
    Ldown = np.zeros((patch_altitude.shape[0]))
    Lside = np.zeros((patch_altitude.shape[0]))
    Lnormal = np.zeros((patch_altitude.shape[0]))
    for altitude in skyalt:
        # Anisotropic sky
        if anisotropic_sky:
            temp_emissivity = esky_band[skyalt == altitude]
        # Isotropic sky but with patches (need to switch anisotropic_sky to False)
        else:
            temp_emissivity = esky
        # Estimate longwave radiation on a horizontal surface (Ldown), vertical surface (Lside) and perpendicular (Lnormal)
        Ldown[patch_altitude == altitude] = ((temp_emissivity * SBC * ((Ta + 273.15) ** 4)) / np.pi) * steradian[patch_altitude == altitude] * np.sin(altitude * deg2rad)
        Lside[patch_altitude == altitude] = ((temp_emissivity * SBC * ((Ta + 273.15) ** 4)) / np.pi) * steradian[patch_altitude == altitude] * np.cos(altitude * deg2rad)
        Lnormal[patch_altitude == altitude] = ((temp_emissivity * SBC * ((Ta + 273.15) ** 4)) / np.pi) * steradian[patch_altitude == altitude]

    Lsky_normal = deepcopy(sky_patches)
    Lsky_down = deepcopy(sky_patches)
    Lsky_side = deepcopy(sky_patches)

    Lsky_normal[:,2] = Lnormal
    Lsky_down[:,2] = Ldown
    Lsky_side[:,2] = Lside

    # Estimate longwave radiation in each patch based on patch characteristics, i.e. sky, vegetation or building (shaded or sunlit)
    Ldown, Lside, Lside_sky, Lside_veg, Lside_sh, Lside_sun, Lside_ref, \
            Least_, Lwest_, Lnorth_, Lsouth_ = patch_characteristics.define_patch_characteristics(solar_altitude, solar_azimuth, 
                                 patch_altitude, patch_azimuth, steradian,
                                 asvf,
                                 shmat, vegshmat, vbshvegshmat,
                                 Lsky_down, Lsky_side, Lsky_normal, Lup,
                                 Ta, Tgwall, ewall,
                                 rows, cols)

    return Ldown, Lside, Least_, Lwest_, Lnorth_, Lsouth_
    # return Ldown, Lside, Lside_sky, Lside_veg, Lside_sh, Lside_sun, Lside_ref, Lsky_normal, Lsky_down, Lsky_side, Least_, Lwest_, Lnorth_, Lsouth_