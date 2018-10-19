from builtins import str
# This file prints out run information used for each specific run
from time import strftime
from osgeo import osr


def writeRunInfo(folderPath, filepath_dsm, gdal_dsm, usevegdem, filePath_cdsm, trunkfile, filePath_tdsm, lat, lon, UTC,
                 landcover, filePath_lc, metfileexist, filePath_metfile, metdata, plugin_dir, absK, absL, albedo_b,
                 albedo_g, ewall, eground, onlyglobal, trunkratio, trans, rows, cols, pos, elvis, cyl, demforbuild):

    with open(folderPath + '/RunInfoSOLWEIG.txt', 'w') as file:
        file.write('This file provides run settings for the SOLWEIG run initiated at: '
                   + strftime("%a, %d %b %Y %H:%M:%S"))
        file.write('\n')
        file.write('Version: ' + 'SOLWEIG v2015a')
        file.write('\n')
        file.write('\n')
        file.write('SURFACE DATA')
        file.write('\n')
        file.write('Digital surface model (DSM): ' + filepath_dsm)
        file.write('\n')
        file.write('Model domain: rows = ' + str(rows) + ', columns = ' + str(cols))
        file.write('\n')
        # get CRS
        prj = gdal_dsm.GetProjection()
        srs = osr.SpatialReference(wkt=prj)
        if srs.IsProjected:
            file.write('Projected referece system: ' + srs.GetAttrValue('projcs'))
        file.write('\n')
        file.write('Geographical coordinate system: ' + srs.GetAttrValue('geogcs'))
        file.write('\n')
        file.write('Latitude: ' + str(lat))
        file.write('\n')
        file.write('Longitude: ' + str(lon))
        file.write('\n')
        file.write('UTC: ' + str(UTC))
        file.write('\n')
        if usevegdem == 1:
            file.write('Transmissivity of light through vegetation: ' + str(trans))
            file.write('\n')
            file.write('Digital vegetation canopy model (CDSM): ' + filePath_cdsm)
            file.write('\n')
            if trunkfile == 1:
                file.write('Digital vegetation zrunk zone model (TDSM): ' + filePath_tdsm)
                file.write('\n')
            else:
                file.write('Trunkzone estimated from CDSM')
                file.write('\n')
                file.write('Trunkzone as percent of canopy height: ' + str(trunkratio))
                file.write('\n')
        else:
            file.write('Vegetation scheme inactive')
            file.write('\n')
        if landcover == 1:
            file.write('Landcover scheme active. Parameters taken from: ' + plugin_dir + "/landcoverclasses_2016a.txt")
            file.write('\n')
            file.write('Landcover grid: ' + filePath_lc)
            file.write('\n')
        else:
            file.write('Landcover scheme inactive')
            file.write('\n')
        file.write('\n')
        if demforbuild == 1:
            file.write('DEM used to identify buildings')
        else:
            file.write('Land cover used to identify buildings')
            file.write('\n')
        file.write('\n')
        file.write('METEOROLOGICAL FORCING DATA')
        file.write('\n')
        if metfileexist == 1:
            file.write('Meteorological file: ' + filePath_metfile)
            file.write('\n')
            if onlyglobal == 1:
                file.write('Diffuse and direct shortwave radiation estimated from global radiation')
                file.write('\n')
        else:
            file.write('Meteorological file not used')
            file.write('Year: ' + str(metdata[0, 0]))
            file.write('\n')
            file.write('Day of Year: ' + str(metdata[0, 1]))
            file.write('\n')
            file.write('Hour: ' + str(metdata[0, 2]))
            file.write('\n')
            file.write('Minute: ' + str(metdata[0, 3]))
            file.write('\n')
            file.write('Ait temperature: ' + str(metdata[0, 11]))
            file.write('\n')
            file.write('Relative humidity: ' + str(metdata[0, 10]))
            file.write('\n')
            file.write('Global radiation: ' + str(metdata[0, 14]))
            file.write('\n')
            file.write('Diffuse radiation: ' + str(metdata[0, 21]))
            file.write('\n')
            file.write('Direct radiation: ' + str(metdata[0, 22]))
            file.write('\n')
        file.write('\n')
        file.write('HUMAN EXPOSURE PARAMETERS')
        file.write('\n')
        file.write('Absorption, shortwave radiation: ' + str(absK))
        file.write('\n')
        file.write('Absorption, longwave radiation: ' + str(absL))
        file.write('\n')
        if pos == 0:
            file.write('Posture of human body: Standing')
        else:
            file.write('Posture of human body: Sitting')
        file.write('\n')
        file.write('ENVIRONMENTAL PARAMETERS')
        file.write('\n')
        file.write('Albedo of walls: ' + str(albedo_b))
        file.write('\n')
        file.write('Albedo of ground (not used if land cover scheme is active): ' + str(albedo_g))
        file.write('\n')
        file.write('Emissivity (walls): ' + str(ewall))
        file.write('\n')
        file.write('Emissivity of ground (not used if land cover scheme is active): ' + str(eground))
        file.write('\n')
        file.write('\n')
        file.write('ADDITIONAL SETTINGS')
        file.write('\n')
        if elvis == 1:
            file.write('Sky emissivity adjusted according to Jonsson et al. (2005)')
            file.write('\n')
        if cyl == 1:
            file.write('Human considered as a cylinder')
        else:
            file.write('Human considered as a standing cube')
        file.write('\n')
        file.close()
