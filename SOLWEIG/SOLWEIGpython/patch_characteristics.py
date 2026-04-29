import numpy as np
from copy import deepcopy
from . import sunlit_shaded_patches

''' This function defines if a patch seen from a pixel is sky, building or vegetation. 
    It also calculates if a building patch is sunlit or shaded. From this it estimates 
    corresponding longwave radiation originating from each surface.'''

def define_patch_characteristics(solar_altitude, solar_azimuth,
                             patch_altitude, patch_azimuth, steradian,
                             asvf,
                             shmat, vegshmat, vbshvegshmat,
                             Lsky_down, Lsky_side, Lsky, Lup,
                             Ta, Tgwall, ewall,
                             rows, cols):
    
    # Stefan-Boltzmann's Constant
    SBC = 5.67051e-8

    # Degrees to radians
    deg2rad = np.pi / 180

    # Define variables
    Ldown = np.zeros((rows,cols))
    Ldown_sky = np.zeros((rows,cols))
    Ldown_veg = np.zeros((rows,cols))
    Ldown_sun = np.zeros((rows,cols))
    Ldown_sh = np.zeros((rows,cols))
    Ldown_ref = np.zeros((rows,cols))

    Lside = np.zeros((rows,cols))
    Lside_sky = np.zeros((rows,cols))
    Lside_veg = np.zeros((rows,cols))
    Lside_sun = np.zeros((rows,cols))
    Lside_sh = np.zeros((rows,cols))
    Lside_ref = np.zeros((rows,cols))

    Least = np.zeros((rows,cols))
    Lwest = np.zeros((rows,cols))
    Lnorth = np.zeros((rows,cols))
    Lsouth = np.zeros((rows,cols))

    # Define patch characteristics (sky, vegetation or building, and sunlit or shaded if building)
    for idx in range(patch_altitude.shape[0]):
        # Calculations for patches on sky, shmat = 1 = sky is visible
        temp_sky = ((shmat[:,:,idx] == 1) & (vegshmat[:,:,idx] == 1))
        
        # Longwave radiation from sky to vertical surface
        Ldown_sky += temp_sky * Lsky_down[idx,2]
        
        # Longwave radiation from sky to horizontal surface
        Lside_sky += temp_sky * Lsky_side[idx,2]

        # Calculations for patches that are vegetation, vegshmat = 0 = shade from vegetation
        temp_vegsh = ((vegshmat[:,:,idx] == 0) | (vbshvegshmat[:,:,idx] == 0))
        # Longwave radiation from vegetation surface (considered vertical)
        vegetation_surface = ((ewall * SBC * ((Ta + 273.15) ** 4)) / np.pi)

        # Longwave radiation reaching a vertical surface
        Lside_veg += vegetation_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh
        
        # Longwave radiation reaching a horizontal surface
        Ldown_veg += vegetation_surface * steradian[idx] * np.sin(patch_altitude[idx] * deg2rad) * temp_vegsh
        
        # Portion into cardinal directions to be used for standing box or POI output
        if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
            Least += temp_sky * Lsky_side[idx,2] * np.cos((90 - patch_azimuth[idx]) * deg2rad)
            Least += vegetation_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((90 - patch_azimuth[idx]) * deg2rad)
        if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
            Lsouth += temp_sky * Lsky_side[idx,2] * np.cos((180 - patch_azimuth[idx]) * deg2rad)
            Lsouth += vegetation_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((180 - patch_azimuth[idx]) * deg2rad)
        if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
            Lwest += temp_sky * Lsky_side[idx,2] * np.cos((270 - patch_azimuth[idx]) * deg2rad)
            Lwest += vegetation_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((270 - patch_azimuth[idx]) * deg2rad)
        if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
            Lnorth += temp_sky * Lsky_side[idx,2] * np.cos((0 - patch_azimuth[idx]) * deg2rad)
            Lnorth += vegetation_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_vegsh * np.cos((0 - patch_azimuth[idx]) * deg2rad)

        # Calculations for patches that are buildings, shmat = 0 = shade from buildings
        temp_vbsh = (1 - shmat[:,:,idx]) * vbshvegshmat[:,:,idx]
        temp_sh = (temp_vbsh == 1)
        azimuth_difference = np.abs(solar_azimuth - patch_azimuth[idx])

        # Longwave radiation from sunlit surfaces
        sunlit_surface = ((ewall * SBC * ((Ta + Tgwall + 273.15) ** 4)) / np.pi)
        # Longwave radiation from shaded surfaces
        shaded_surface = ((ewall * SBC * ((Ta + 273.15) ** 4)) / np.pi)
        if ((azimuth_difference > 90) and (azimuth_difference < 270) and (solar_altitude > 0)):
            # Calculate which patches defined as buildings that are sunlit or shaded
            sunlit_patches, shaded_patches = sunlit_shaded_patches.shaded_or_sunlit(solar_altitude, solar_azimuth, patch_altitude[idx], patch_azimuth[idx], asvf)
            
            # Calculate longwave radiation from sunlit walls to vertical surface
            Lside_sun += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh
            # Calculate longwave radiation from shaded walls to vertical surface
            Lside_sh += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh
            
            # Calculate longwave radiation from sunlit walls to horizontal surface
            Ldown_sun += sunlit_surface * sunlit_patches * steradian[idx] * np.sin(patch_altitude[idx] * deg2rad) * temp_sh
            # Calculate longwave radiation from shaded walls to horizontal surface
            Ldown_sh += shaded_surface * shaded_patches * steradian[idx] * np.sin(patch_altitude[idx] * deg2rad) * temp_sh
            
            # Portion into cardinal directions to be used for standing box or POI output
            if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
                Least += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx]) * deg2rad)
                Least += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx]) * deg2rad)
            if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
                Lsouth += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx]) * deg2rad)
                Lsouth += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx]) * deg2rad)
            if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
                Lwest += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx]) * deg2rad)
                Lwest += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx]) * deg2rad)
            if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
                Lnorth += sunlit_surface * sunlit_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx]) * deg2rad)
                Lnorth += shaded_surface * shaded_patches * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx]) * deg2rad)

        else:
            # Calculate longwave radiation from shaded walls reaching a vertical surface
            Lside_sh += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh
            
            # Calculate longwave radiation from shaded walls reaching a horizontal surface
            Ldown_sh += shaded_surface * steradian[idx] * np.sin(patch_altitude[idx] * deg2rad) * temp_sh

            # Portion into cardinal directions to be used for standing box or POI output
            if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
                Least += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx]) * deg2rad)
            if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
                Lsouth += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx]) * deg2rad)
            if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
                Lwest += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx]) * deg2rad)
            if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
                Lnorth += shaded_surface * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx]) * deg2rad)

    # Calculate reflected longwave in each patch
    reflected_on_surfaces = (((Ldown_sky+Lup)*(1-ewall)*0.5) / np.pi)
    for idx in range(patch_altitude.shape[0]):
        temp_sh = ((shmat[:,:,idx] == 0) | (vegshmat[:,:,idx] == 0) | (vbshvegshmat[:,:,idx] == 0))
        
        # Reflected longwave radiation reaching vertical surfaces
        Lside_ref += reflected_on_surfaces * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh
        
        # Reflected longwave radiation reaching horizontal surfaces
        Ldown_ref += reflected_on_surfaces * steradian[idx] * np.sin(patch_altitude[idx] * deg2rad) * temp_sh
        
        # Portion into cardinal directions to be used for standing box or POI output
        if (patch_azimuth[idx] > 360) or (patch_azimuth[idx] < 180):
            Least += reflected_on_surfaces * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((90 - patch_azimuth[idx]) * deg2rad)
        if (patch_azimuth[idx] > 90) and (patch_azimuth[idx] < 270):
            Lsouth += reflected_on_surfaces * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((180 - patch_azimuth[idx]) * deg2rad)
        if (patch_azimuth[idx] > 180) and (patch_azimuth[idx] < 360):
            Lwest += reflected_on_surfaces * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((270 - patch_azimuth[idx]) * deg2rad)
        if (patch_azimuth[idx] > 270) or (patch_azimuth[idx] < 90):
            Lnorth += reflected_on_surfaces * steradian[idx] * np.cos(patch_altitude[idx] * deg2rad) * temp_sh * np.cos((0 - patch_azimuth[idx]) * deg2rad)

    # Sum of all Lside components (sky, vegetation, sunlit and shaded buildings, reflected)
    Lside = Lside_sky + Lside_veg + Lside_sh + Lside_sun + Lside_ref

    # Sum of all Lside components (sky, vegetation, sunlit and shaded buildings, reflected)
    Ldown = Ldown_sky + Ldown_veg + Ldown_sh + Ldown_sun + Ldown_ref

    return Ldown, Lside, Lside_sky, Lside_veg, Lside_sh, Lside_sun, Lside_ref, Least, Lwest, Lnorth, Lsouth