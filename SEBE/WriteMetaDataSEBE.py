from builtins import str
# This file prints out run information used for each specific run
from time import strftime
from osgeo import osr


def writeRunInfo(folderPath, filepath_dsm, gdal_dsm, usevegdem, filePath_cdsm, trunkfile, filePath_tdsm, lat, lon, UTC,
                 filePath_metfile, albedo, onlyglobal, trunkratio, trans, rows, cols):

    with open(folderPath + '/RunInfoSEBE.txt', 'w') as file:
        file.write('This file provides run settings for the SEBE run initiated at: '
                   + strftime("%a, %d %b %Y %H:%M:%S"))
        file.write('\n')
        file.write('Version: ' + 'SEBE v2015a')
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
        file.write('\n')
        file.write('METEOROLOGICAL FORCING DATA')
        file.write('\n')
        file.write('Meteorological file: ' + filePath_metfile)
        file.write('\n')
        if onlyglobal == 1:
            file.write('Diffuse and direct shortwave radiation estimated from global radiation')
            file.write('\n')

        file.write('\n')
        file.write('ENVIRONMENTAL PARAMETERS')
        file.write('\n')
        file.write('Albedo: ' + str(albedo))
        file.write('\n')
        file.close()
