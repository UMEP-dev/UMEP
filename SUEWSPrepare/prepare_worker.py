from builtins import next
from builtins import str
from builtins import range
from qgis.PyQt import QtCore
# from PyQt4.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox  #, QFileDialog, QAction, QIcon
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
# from qgis.gui import QgsMessageBar
import traceback
import numpy as np
from osgeo import gdal, osr
# import subprocess
import sys
import linecache
import os
# import fileinput
# import time
from shutil import copyfile
from ..Utilities import f90nml
from ..Utilities import RoughnessCalcFunction as rg
import copy

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, vlayer, nbr_header, poly_field, Metfile_path, start_DLS, end_DLS, LCF_from_file, LCFfile_path, LCF_paved,
                 LCF_buildings, LCF_evergreen, LCF_decidious, LCF_grass, LCF_baresoil, LCF_water, IMP_from_file, IMPfile_path,
                 IMP_heights_mean, IMP_z0, IMP_zd, IMP_fai, IMPveg_from_file, IMPvegfile_path, IMPveg_heights_mean_eve,
                 IMPveg_heights_mean_dec, IMPveg_fai_eve, IMPveg_fai_dec, pop_density, widget_list, # wall_area,
                 land_use_from_file, land_use_file_path, lines_to_write, plugin_dir, output_file_list, map_units, header_sheet, output_dir, #, wall_area_info (second last)
                 day_since_rain, leaf_cycle, soil_moisture, file_code, utc, checkBox_twovegfiles, IMPvegfile_path_dec, IMPvegfile_path_eve, pop_density_day, daypop):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.vlayer = vlayer
        self.nbr_header = nbr_header
        self.poly_field = poly_field
        self.Metfile_path = Metfile_path
        self.start_DLS = start_DLS
        self.end_DLS = end_DLS
        self.LCF_from_file = LCF_from_file
        self.LCFfile_path = LCFfile_path
        self.LCF_paved = LCF_paved
        self.LCF_buildings = LCF_buildings
        self.LCF_evergreen = LCF_evergreen
        self.LCF_decidious = LCF_decidious
        self.LCF_grass = LCF_grass
        self.LCF_baresoil = LCF_baresoil
        self.LCF_water = LCF_water
        self.IMP_from_file = IMP_from_file
        self.IMPfile_path = IMPfile_path
        self.IMP_heights_mean = IMP_heights_mean
        self.IMP_z0 = IMP_z0
        self.IMP_zd = IMP_zd
        self.IMP_fai = IMP_fai
        self.IMPveg_from_file = IMPveg_from_file
        self.IMPvegfile_path = IMPvegfile_path
        self.IMPveg_heights_mean_eve = IMPveg_heights_mean_eve
        self.IMPveg_heights_mean_dec = IMPveg_heights_mean_dec
        self.IMPveg_fai_eve = IMPveg_fai_eve
        self.IMPveg_fai_dec = IMPveg_fai_dec
        self.pop_density = pop_density
        self.widget_list = widget_list
        # self.wall_area = wall_area
        self.land_use_from_file = land_use_from_file
        self.land_use_file_path = land_use_file_path
        self.lines_to_write = lines_to_write
        self.output_dir = output_dir
        self.output_file_list = output_file_list
        self.map_units = map_units
        self.header_sheet = header_sheet
        # self.wall_area_info = wall_area_info
        self.input_path = plugin_dir + '/Input/'
        # self.output_path = plugin_dir + '/Output/'
        self.output_path = plugin_dir[:-12] + 'suewsmodel/Input/'
        self.plugin_dir = plugin_dir
        self.day_since_rain = day_since_rain
        self.leaf_cycle = leaf_cycle
        self.soil_moisture = soil_moisture
        self.file_code = file_code
        self.utc = utc
        self.checkBox_twovegfiles = checkBox_twovegfiles
        self.IMPvegfile_path_dec = IMPvegfile_path_dec
        self.IMPvegfile_path_eve = IMPvegfile_path_eve
        self.pop_density_day = pop_density_day
        self.daypop = daypop

    def run(self):
        try:
            ind = 1
            for feature in self.vlayer.getFeatures():
                if self.killed is True:
                    break
                new_line = [None] * (len(self.nbr_header) - 3)
                print_line = True
                feat_id = int(feature.attribute(self.poly_field))
                code = "Grid"
                index = self.find_index(code)
                new_line[index] = str(feat_id)
                print('Processing ID: ' + str(feat_id))
                year = None
                year2 = None

                if self.Metfile_path is None:
                    QMessageBox.critical(None, "Error", "Meteorological data file has not been provided,"
                                                        " please check the main tab")
                    return
                elif os.path.isfile(self.Metfile_path[0]):
                    with open(self.Metfile_path[0]) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if year == split[0]:
                                break
                            else:
                                if year2 == split[0]:
                                    year = split[0]
                                    break
                                elif year is None:
                                    year = split[0]
                                else:
                                    year2 = split[0]

                    # figure out the time res of input file
                    if ind == 1:
                        met_old = np.genfromtxt(self.Metfile_path[0], skip_header=1, skip_footer=2)
                        id = met_old[:, 1]
                        it = met_old[:, 2]
                        imin = met_old[:, 3]
                        dectime0 = id[0] + it[0] / 24 + imin[0] / (60 * 24)
                        dectime1 = id[1] + it[1] / 24 + imin[1] / (60 * 24)
                        res = int(np.round((dectime1 - dectime0) * (60 * 24)))
                        ind = 999

                else:
                    QMessageBox.critical(None, "Error",
                                         "Could not find the file containing meteorological data")
                    return

                code = "Year"
                index = self.find_index(code)
                new_line[index] = str(year)
                code = "StartDLS"
                index = self.find_index(code)
                new_line[index] = str(self.start_DLS)
                code = "EndDLS"
                index = self.find_index(code)
                new_line[index] = str(self.end_DLS)

                old_cs = osr.SpatialReference()
                vlayer_ref = self.vlayer.crs().toWkt()
                old_cs.ImportFromWkt(vlayer_ref)

                wgs84_wkt = """
                GEOGCS["WGS 84",
                    DATUM["WGS_1984",
                        SPHEROID["WGS 84",6378137,298.257223563,
                            AUTHORITY["EPSG","7030"]],
                        AUTHORITY["EPSG","6326"]],
                    PRIMEM["Greenwich",0,
                        AUTHORITY["EPSG","8901"]],
                    UNIT["degree",0.01745329251994328,
                        AUTHORITY["EPSG","9122"]],
                    AUTHORITY["EPSG","4326"]]"""

                new_cs = osr.SpatialReference()
                new_cs.ImportFromWkt(wgs84_wkt)

                transform = osr.CoordinateTransformation(old_cs, new_cs)

                centroid = feature.geometry().centroid().asPoint()
                area = feature.geometry().area()

                if self.map_units == 0:
                    hectare = area * 0.0001 # meter

                elif self.map_units == 1:
                    hectare = area / 107640. # square foot

                else:
                    hectare = area
                gdalver = float(gdal.__version__[0])
                lonlat = transform.TransformPoint(centroid.x(), centroid.y())
                code = "lat"
                index = self.find_index(code)
                if gdalver == 3.:
                    new_line[index] = '%.6f' % lonlat[0] #changed to gdal 3
                else:
                    new_line[index] = '%.6f' % lonlat[1] #changed to gdal 2
                code = "lng"
                index = self.find_index(code)
                if gdalver == 3.:
                    new_line[index] = '%.6f' % lonlat[1] #changed to gdal 3
                else:
                    new_line[index] = '%.6f' % lonlat[0] #changed to gdal 2

                code = "Timezone"
                index = self.find_index(code)
                new_line[index] = str(self.utc)

                code = "SurfaceArea"
                index = self.find_index(code)
                new_line[index] = str(hectare)

                altitude = 0
                day = 1
                hour = 0
                minute = 0

                code = "Alt"
                index = self.find_index(code)
                new_line[index] = str(altitude)
                code = "id"
                index = self.find_index(code)
                new_line[index] = str(day)
                code = "ih"
                index = self.find_index(code)
                new_line[index] = str(hour)
                code = "imin"
                index = self.find_index(code)
                new_line[index] = str(minute)

                if self.LCF_from_file:
                    found_LCF_line = False
                    with open(self.LCFfile_path[0]) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                LCF_paved = split[1]
                                LCF_buildings = split[2]
                                LCF_evergreen = split[3]
                                LCF_decidious = split[4]
                                LCF_grass = split[5]
                                LCF_baresoil = split[6]
                                LCF_water = split[7]
                                found_LCF_line = True
                                break
                        if not found_LCF_line:
                            LCF_paved = -999
                            LCF_buildings = -999
                            LCF_evergreen = -999
                            LCF_decidious = -999
                            LCF_grass = -999
                            LCF_baresoil = -999
                            LCF_water = -999
                            print_line = False

                else:
                    LCF_paved = feature.attribute(self.LCF_paved.getFieldName())
                    LCF_buildings = feature.attribute(self.LCF_buildings.getFieldName())
                    LCF_evergreen = feature.attribute(self.LCF_evergreen.getFieldName())
                    LCF_decidious = feature.attribute(self.LCF_decidious.getFieldName())
                    LCF_grass = feature.attribute(self.LCF_grass.getFieldName())
                    LCF_baresoil = feature.attribute(self.LCF_baresoil.getFieldName())
                    LCF_water = feature.attribute(self.LCF_water.getFieldName())

                code = "Fr_Paved"
                index = self.find_index(code)
                new_line[index] = str(LCF_paved)
                code = "Fr_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(LCF_buildings)
                code = "Fr_EveTr"
                index = self.find_index(code)
                new_line[index] = str(LCF_evergreen)
                code = "Fr_DecTr"
                index = self.find_index(code)
                new_line[index] = str(LCF_decidious)
                code = "Fr_Grass"
                index = self.find_index(code)
                new_line[index] = str(LCF_grass)
                code = "Fr_Bsoil"
                index = self.find_index(code)
                new_line[index] = str(LCF_baresoil)
                code = "Fr_Water"
                index = self.find_index(code)
                new_line[index] = str(LCF_water)

                irrFr_EveTr = 0
                irrFr_DecTr = 0
                irrFr_Grass = 0
                IrrFr_Bldgs = 0
                IrrFr_Paved = 0
                IrrFr_Water = 0
                IrrFr_BSoil = 0

                code = "IrrFr_EveTr"
                index = self.find_index(code)
                new_line[index] = str(irrFr_EveTr)
                code = "IrrFr_DecTr"
                index = self.find_index(code)
                new_line[index] = str(irrFr_DecTr)
                code = "IrrFr_Grass"
                index = self.find_index(code)
                new_line[index] = str(irrFr_Grass)
                code = "IrrFr_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(IrrFr_Bldgs)
                code = "IrrFr_Paved"
                index = self.find_index(code)
                new_line[index] = str(IrrFr_Paved)
                code = "IrrFr_Water"
                index = self.find_index(code)
                new_line[index] = str(IrrFr_Water)
                code = "IrrFr_BSoil"
                index = self.find_index(code)
                new_line[index] = str(IrrFr_BSoil)

                TrafficRate_WD = 0.01
                TrafficRate_WE = 0.01
                code = "TrafficRate_WD"
                index = self.find_index(code)
                new_line[index] = str(TrafficRate_WD)
                code = "TrafficRate_WE"
                index = self.find_index(code)
                new_line[index] = str(TrafficRate_WE)

                QF0_BEU_WD = 0.88
                QF0_BEU_WE = 0.88
                code = "QF0_BEU_WD"
                index = self.find_index(code)
                new_line[index] = str(QF0_BEU_WD)
                code = "QF0_BEU_WE"
                index = self.find_index(code)
                new_line[index] = str(QF0_BEU_WE)

                # Activity_ProfWD = 55663
                # Activity_ProfWE = 55664
                #
                # code = "ActivityProfWD"
                # index = self.find_index(code)
                # new_line[index] = str(Activity_ProfWD)
                # code = "ActivityProfWE"
                # index = self.find_index(code)
                # new_line[index] = str(Activity_ProfWE)

                if self.IMP_from_file:
                    found_IMP_line = False

                    with open(self.IMPfile_path[0]) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                IMP_heights_mean = split[3]
                                IMP_z0 = split[6]
                                IMP_zd = split[7]
                                IMP_fai = split[2]
                                IMP_max = split[4]
                                IMP_sd = split[5]
                                IMP_wai = split[8]
                                found_IMP_line = True
                                break
                        if not found_IMP_line:
                            IMP_heights_mean = -999
                            IMP_z0 = -999
                            IMP_zd = -999
                            IMP_fai = -999
                            IMP_wai = -999
                            print_line = False
                else:
                    IMP_heights_mean = feature.attribute(self.IMP_mean_height.getFieldName())
                    IMP_z0 = feature.attribute(self.IMP_z0.getFieldName())
                    IMP_zd = feature.attribute(self.IMP_zd.getFieldName())
                    IMP_fai = feature.attribute(self.IMP_fai.getFieldName())
                    IMP_wai = feature.attribute(self.IMP_wai.getFieldName())

                if self.IMPveg_from_file:
                    found_IMPveg_line = False

                    with open(self.IMPvegfile_path[0]) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                IMPveg_heights_mean_eve = split[3]
                                IMPveg_heights_mean_dec = split[3]
                                IMPveg_fai_eve = split[2]
                                IMPveg_fai_dec = split[2]
                                IMPveg_max_eve = split[4]  #TODO not used yet
                                IMPveg_sd_eve = split[5]  #TODO not used yet
                                IMPveg_max_dec = split[4]
                                IMPveg_sd_dec = split[5]
                                found_IMPveg_line = True
                                break
                        if not found_IMPveg_line:
                            IMPveg_heights_mean_eve = -999
                            IMPveg_heights_mean_dec = -999
                            IMPveg_fai_eve = -999
                            IMPveg_fai_dec = -999
                            print_line = False
                else:
                    IMPveg_heights_mean_eve = feature.attribute(self.IMPveg_mean_height_eve.getFieldName())
                    IMPveg_heights_mean_dec = feature.attribute(self.IMPveg_mean_height_dec.getFieldName())
                    IMPveg_fai_eve = feature.attribute(self.IMPveg_fai_eve.getFieldName())
                    IMPveg_fai_dec = feature.attribute(self.IMPveg_fai_dec.getFieldName())

                code = "H_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(IMP_heights_mean)
                code = "H_EveTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_heights_mean_eve)
                code = "H_DecTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_heights_mean_dec)

                # New calcualtion of rouhgness params v2017 (Kent et al. 2017b)
				# Evergreen not yet included in the calculations
                LCF_de = float(LCF_decidious)
                LCF_ev = float(LCF_evergreen)
                LCF_bu = float(LCF_buildings)
                LCF_tr = LCF_de + LCF_ev # temporary fix while ev and de is not separated, issue 155
                if (LCF_de  == 0 and LCF_ev == 0 and LCF_bu == 0):
                    zH = 0
                    zMAx = 0
                else:
                    zH = (float(IMP_heights_mean) * LCF_bu + float(IMPveg_heights_mean_eve) * LCF_ev + float(IMPveg_heights_mean_dec) * LCF_de) / (LCF_bu + LCF_ev + LCF_de)                    
                    zMax = max(float(IMPveg_max_dec),float(IMP_max))

                if (LCF_de  == 0 and LCF_ev == 0 and LCF_bu == 0):
                    sdComb = 0
                    IMP_z0 = 0
                    IMP_zd = 0
                    # sdTree = np.sqrt((IMPveg_sd_eve ^ 2 / LCF_evergreen * area) + (IMPveg_sd_dec ^ 2 / LCF_decidious * area))  # not used yet
                elif (LCF_tr == 0 and LCF_bu != 0):
                    sdComb = np.sqrt(float(IMP_sd) ** 2. / (LCF_bu * float(area)))  # Fix (fLCF_bu) issue #162
                elif (LCF_tr != 0 and LCF_bu == 0):
                    sdComb = np.sqrt(float(IMPveg_sd_dec) ** 2. / (LCF_tr * float(area)))
                elif (LCF_tr != 0 and LCF_bu != 0):
                    sdComb = np.sqrt(float(IMPveg_sd_dec) ** 2. / (LCF_tr * float(area)) + float(IMP_sd) ** 2. / (LCF_bu * float(area)))

                pai = LCF_bu + LCF_ev + LCF_de
                
                # paiall = (planareaB + planareaV) / AT
                porosity = 0.2  # This should change with season. Net, set for Summer
                Pv = ((-1.251 * porosity ** 2) / 1.2) + ((0.489 * porosity) / 1.2) + (0.803 / 1.2)  # factor accounting for porosity to correct total fai in roughness calc Kent et al. 2017b
                # faiall_rgh = (frontalareaB + (Pv * frontalareaV)) / (AT / (1 / scale))  # frontal area used in roughness calculation Kent et al. 2017b
                fai = Pv * (float(IMPveg_fai_eve) + float(IMPveg_fai_dec)) + float(IMP_fai)
                if (fai == 0. and pai == 1.):
                    IMP_z0 = 0.
                    IMP_zd = zH
                elif (fai == 0. and pai < 1.):
                    IMP_z0 = 0.
                    IMP_zd = 0.
                else:
                    IMP_zd, IMP_z0 = rg.RoughnessCalc("Kan", zH, fai, pai, zMax, sdComb)

                # clean up and give open country values if non-existant
                if np.isnan(IMP_z0) or IMP_z0 < 0.03:
                    IMP_z0 = 0.03
                if np.isnan(IMP_zd) or IMP_zd < 0.2:
                    IMP_zd = 0.2

                code = "z0"
                index = self.find_index(code)
                new_line[index] = '%.3f' % IMP_z0
                code = "zd"
                index = self.find_index(code)
                new_line[index] = '%.3f' % IMP_zd
                code = "FAI_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(IMP_fai)
                code = "FAI_EveTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_fai_eve)
                code = "FAI_DecTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_fai_dec)

                # new for z (2017)
                code = "z"
                index = self.find_index(code)
                try:
                    z = ((float(IMP_heights_mean) * float(LCF_buildings) + float(IMPveg_heights_mean_eve) * float(LCF_evergreen) +
                        float(IMPveg_heights_mean_dec) * float(LCF_decidious)) / (float(LCF_buildings) + float(LCF_evergreen) + float(LCF_decidious))) * 3
                except:
                    z = 10.
                if z < 10.:
                    z = 10.
                new_line[index] = '%.3f' % z

                if self.pop_density is not None:
                    pop_density_night = feature.attribute(self.pop_density.currentField())
                else:
                    pop_density_night = -999

                if self.daypop == 1:
                    pop_density_day = feature.attribute(self.pop_density_day.currentField())
                else:
                    pop_density_day = pop_density_night
                code = "PopDensDay"
                index = self.find_index(code)
                new_line[index] = '%.3f' % pop_density_day
                code = "PopDensNight"
                index = self.find_index(code)
                new_line[index] = '%.3f' % pop_density_night
                for widget in self.widget_list:
                    if widget.get_checkstate():
                        code_field = str(widget.comboBox_uniquecodes.currentText())
                        try:
                            code = int(feature.attribute(code_field))
                        except ValueError as e:
                            QMessageBox.critical(None, "Error",
                                                 "Unique code field for widget " + widget.get_title() +
                                                 " should only contain integers")
                            return
                        match = widget.comboBox.findText(str(code))
                        if match == -1:
                            QMessageBox.critical(None, "Error",
                                                 "Unique code field for widget " + widget.get_title() +
                                                 " contains one or more codes with no match in site library")
                            return
                        index = widget.get_sitelistpos()
                        new_line[index - 1] = str(code)

                    else:
                        code = widget.get_combo_text()
                        index = widget.get_sitelistpos()
                        new_line[index - 1] = str(code)

                LUMPS_drate = 0.25
                LUMPS_Cover = 1
                LUMPS_MaxRes = 10
                NARP_Trans = 1
                code = "LUMPS_DrRate"
                index = self.find_index(code)
                new_line[index] = str(LUMPS_drate)
                code = "LUMPS_Cover"
                index = self.find_index(code)
                new_line[index] = str(LUMPS_Cover)
                code = "LUMPS_MaxRes"
                index = self.find_index(code)
                new_line[index] = str(LUMPS_MaxRes)
                code = "NARP_Trans"
                index = self.find_index(code)
                new_line[index] = str(NARP_Trans)

                flow_change = 0
                RunoffToWater = 0.1
                PipeCap = 100
                GridConn1of8 = 0
                Fraction1of8 = 0
                GridConn2of8 = 0
                Fraction2of8 = 0
                GridConn3of8 = 0
                Fraction3of8 = 0
                GridConn4of8 = 0
                Fraction4of8 = 0
                GridConn5of8 = 0
                Fraction5of8 = 0
                GridConn6of8 = 0
                Fraction6of8 = 0
                GridConn7of8 = 0
                Fraction7of8 = 0
                GridConn8of8 = 0
                Fraction8of8 = 0
                code = "FlowChange"
                index = self.find_index(code)
                new_line[index] = str(flow_change)
                code = "RunoffToWater"
                index = self.find_index(code)
                new_line[index] = str(RunoffToWater)
                code = "PipeCapacity"
                index = self.find_index(code)
                new_line[index] = str(PipeCap)
                code = "GridConnection1of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn1of8)
                code = "Fraction1of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction1of8)
                code = "GridConnection2of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn2of8)
                code = "Fraction2of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction2of8)
                code = "GridConnection3of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn3of8)
                code = "Fraction3of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction3of8)
                code = "GridConnection4of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn4of8)
                code = "Fraction4of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction4of8)
                code = "GridConnection5of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn5of8)
                code = "Fraction5of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction5of8)
                code = "GridConnection6of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn6of8)
                code = "Fraction6of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction6of8)
                code = "GridConnection7of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn7of8)
                code = "Fraction7of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction7of8)
                code = "GridConnection8of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn8of8)
                code = "Fraction8of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction8of8)

                WhitinGridPav = 661
                WhitinGridBldg = 662
                WhitinGridEve = 663
                WhitinGridDec = 664
                WhitinGridGrass = 665
                WhitinGridUnmanBsoil = 666
                WhitinGridWaterCode = 667
                code = "WithinGridPavedCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridPav)
                code = "WithinGridBldgsCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridBldg)
                code = "WithinGridEveTrCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridEve)
                code = "WithinGridDecTrCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridDec)
                code = "WithinGridGrassCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridGrass)
                code = "WithinGridUnmanBSoilCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridUnmanBsoil)
                code = "WithinGridWaterCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridWaterCode)

                # if self.wall_area_info:
                #     wall_area = feature.attribute(self.wall_area.getFieldName())
                # else:
                #     wall_area = -999

                code = "AreaWall"
                index = self.find_index(code)
                new_line[index] = str(float(IMP_wai) * hectare * 10000.) # currently wallarea. Will change to wai

                Fr_ESTMClass_Paved1 = 0.
                Fr_ESTMClass_Paved2 = 1.
                Fr_ESTMClass_Paved3 = 0.
                Code_ESTMClass_Paved1 = 99999
                Code_ESTMClass_Paved2 = 807
                Code_ESTMClass_Paved3 = 99999
                Fr_ESTMClass_Bldgs1 = 1.0
                Fr_ESTMClass_Bldgs2 = 0.
                Fr_ESTMClass_Bldgs3 = 0.
                Fr_ESTMClass_Bldgs4 = 0.
                Fr_ESTMClass_Bldgs5 = 0.
                Code_ESTMClass_Bldgs1 = 801
                Code_ESTMClass_Bldgs2 = 99999
                Code_ESTMClass_Bldgs3 = 99999
                Code_ESTMClass_Bldgs4 = 99999
                Code_ESTMClass_Bldgs5 = 99999

                if self.land_use_from_file:
                    with open(self.land_use_file_path[0]) as file:
                        next(file)
                        found_LUF_line = False
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                Fr_ESTMClass_Paved1 = split[1]
                                Fr_ESTMClass_Paved2 = split[2]
                                Fr_ESTMClass_Paved3 = split[3]
                                if (float(Fr_ESTMClass_Paved1) == 0 and float(Fr_ESTMClass_Paved2) == 0 and float(Fr_ESTMClass_Paved3) == 0):
                                    Fr_ESTMClass_Paved2 = 1.0
                                Code_ESTMClass_Paved1 = split[4]
                                Code_ESTMClass_Paved2 = split[5]
                                Code_ESTMClass_Paved3 = split[6]
                                Fr_ESTMClass_Bldgs1 = split[7]
                                Fr_ESTMClass_Bldgs2 = split[8]
                                Fr_ESTMClass_Bldgs3 = split[9]
                                Fr_ESTMClass_Bldgs4 = split[10]
                                Fr_ESTMClass_Bldgs5 = split[11]
                                if (float(Fr_ESTMClass_Bldgs1) == 0 and float(Fr_ESTMClass_Bldgs2) == 0 and float(Fr_ESTMClass_Bldgs3) == 0 and float(Fr_ESTMClass_Bldgs4) == 0 and float(Fr_ESTMClass_Bldgs5) == 0):
                                    Fr_ESTMClass_Bldgs3 = 1.0
                                Code_ESTMClass_Bldgs1 = split[12]
                                Code_ESTMClass_Bldgs2 = split[13]
                                Code_ESTMClass_Bldgs3 = split[14]
                                Code_ESTMClass_Bldgs4 = split[15]
                                Code_ESTMClass_Bldgs5 = split[16]

                                # if (float(Fr_ESTMClass_Paved1) + float(Fr_ESTMClass_Paved2) + float(Fr_ESTMClass_Paved3)) != 1:
                                #     QMessageBox.critical(None, "Error", "Land use fractions for paved not equal to 1 at " + str(feat_id))
                                #     return
                                #
                                # if (float(Fr_ESTMClass_Bldgs1) + float(Fr_ESTMClass_Bldgs2) + float(Fr_ESTMClass_Bldgs3) + float(Fr_ESTMClass_Bldgs4) + float(Fr_ESTMClass_Bldgs5)) != 1:
                                #     QMessageBox.critical(None, "Error", "Land use fractions for buildings not equal to 1 at " + str(feat_id))
                                #     return

                                found_LUF_line = True
                                break

                code = "Fr_ESTMClass_Bldgs1"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs1)
                code = "Fr_ESTMClass_Bldgs2"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs2)
                code = "Fr_ESTMClass_Bldgs3"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs3)
                code = "Fr_ESTMClass_Bldgs4"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs4)
                code = "Fr_ESTMClass_Bldgs5"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs5)
                code = "Fr_ESTMClass_Paved1"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Paved1)
                code = "Fr_ESTMClass_Paved2"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Paved2)
                code = "Fr_ESTMClass_Paved3"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Paved3)
                code = "Code_ESTMClass_Bldgs1"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs1)
                code = "Code_ESTMClass_Bldgs2"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs2)
                code = "Code_ESTMClass_Bldgs3"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs3)
                code = "Code_ESTMClass_Bldgs4"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs4)
                code = "Code_ESTMClass_Bldgs5"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs5)
                code = "Code_ESTMClass_Paved1"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Paved1)
                code = "Code_ESTMClass_Paved2"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Paved2)
                code = "Code_ESTMClass_Paved3"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Paved3)

                new_line.append("!")

                if print_line:
                    self.lines_to_write.append(new_line)

                self.progress.emit()

            # Writing met files and add lines in SIteSelect if multiple years
            met_in = np.genfromtxt(self.Metfile_path[0], skip_header=1)

            YYYYmin = np.min(met_in[:, 0])
            YYYYmax = np.max(met_in[:, 0])
            addrows = 0

            # check if full year
            if YYYYmin < YYYYmax:
                t = np.where(met_in[:, 0] == YYYYmax)
                if not t.__len__() > 1:
                    # YYYYmax = YYYYmin
                    YYYYmax = YYYYmax - 1  # Issue #65

            lensiteselect = self.lines_to_write.__len__() - 2
            for YYYY in range(int(YYYYmin), int(YYYYmax) + 1):
                # find start end end of 5 min file for each year
                if res == 60:
                    posstart = np.where((met_in[:, 0] == YYYY) & (met_in[:, 1] == 1) & (met_in[:, 2] == 1) & (met_in[:, 3] == 0))
                elif res == 120:
                    posstart = np.where((met_in[:, 0] == YYYY) & (met_in[:, 1] == 1) & (met_in[:, 2] == 2) & (met_in[:, 3] == 0))
                elif res == 180:
                    posstart = np.where((met_in[:, 0] == YYYY) & (met_in[:, 1] == 1) & (met_in[:, 2] == 3) & (met_in[:, 3] == 0))
                else:
                    posstart = np.where((met_in[:, 0] == YYYY) & (met_in[:, 1] == 1) & (met_in[:, 2] == 0) & (met_in[:, 3] == res))

                posend = np.where((met_in[:, 0] == (YYYY + 1)) & (met_in[:, 1] == 1) & (met_in[:, 2] == 0) & (met_in[:, 3] == 0))
                fixpos = 1

                if len(posstart[0]) == 0:
                    starting = 0
                else:
                    starting = posstart[0]
                if len(posend[0]) == 0:
                    ending = met_in.shape[0]
                    fixpos = 0
                else:
                    ending = posend[0]

                met_save = met_in[int(starting):int(ending) + fixpos, :]  # originally for one full year

                # --- save met-file --- #
                data_out = self.output_dir[0] + "/" + self.file_code + '_' + str(YYYY) + '_data_' + str(res) + '.txt'
                header = '%iy id it imin Q* QH QE Qs Qf Wind RH Td press rain Kdn snow ldown fcld wuh xsmd lai_hr ' \
                         'Kdiff Kdir Wd'
                numformat = '%3d %2d %3d %2d %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f %6.4f %6.2f %6.2f ' \
                            '%6.2f %6.2f %6.4f %6.2f %6.2f %6.2f %6.2f %6.2f'

                np.savetxt(data_out, met_save, fmt=numformat, delimiter=' ', header=header, comments='')

                # Add new year in SiteSelect
                if addrows > 0:
                    for i in range(0, lensiteselect):
                        lines_to_write_oneyear = copy.copy(self.lines_to_write[i+2])
                        lines_to_write_oneyear[1] = str(YYYY)
                        self.lines_to_write.append(lines_to_write_oneyear)
                addrows += 1

            init_out = self.output_dir[0] + '/InitialConditions' + str(self.file_code) + '_' + str(year) + '.nml'
            self.write_to_init(self.input_path + 'InitialConditions.nml', init_out)

            output_lines = []
            output_file = self.output_dir[0] + "/SUEWS_SiteSelect.txt"
            with open(output_file, 'w+') as ofile:
                for line in self.lines_to_write:
                    string_to_print = ''
                    for element in line:
                        string_to_print += str(element) + '\t'
                    string_to_print += "\n"
                    output_lines.append(string_to_print)
                output_lines.append("-9\n")
                output_lines.append("-9\n")
                ofile.writelines(output_lines)
                for input_file in self.output_file_list:
                    try:
                        copyfile(self.output_path + input_file, self.output_dir[0] + "/" + input_file)
                    except IOError as e:
                        QgsMessageLog.logMessage(
                            "Error copying output files with SUEWS_SiteSelect.txt: " + str(e),
                            level=Qgis.Critical)

            if self.killed is False:
                self.progress.emit()
                ret = 1

        except Exception as e:
            ret = 0
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

    def find_index(self, code):
        values = self.header_sheet.row_values(1)
        index = values.index(code)
        return index

    def write_to_init(self, initfilein, initfileout):
        LeafCycle = self.leaf_cycle
        SoilMoisture = self.soil_moisture
        moist = int(SoilMoisture * 1.5)
        snowinitially = 0

        nml = f90nml.read(initfilein)

        nml['initialconditions']['soilstorepavedstate'] = moist
        nml['initialconditions']['soilstorebldgsstate'] = moist
        nml['initialconditions']['soilstoreevetrstate'] = moist
        nml['initialconditions']['soilstoredectrstate'] = moist
        nml['initialconditions']['soilstoregrassstate'] = moist
        nml['initialconditions']['soilstorebsoilstate'] = moist

        # Based on London data
        if LeafCycle == 1:  # Winter
            nml['initialconditions']['gdd_1_0'] = 0
            nml['initialconditions']['gdd_2_0'] = -450
            nml['initialconditions']['laiinitialevetr'] = 4
            nml['initialconditions']['laiinitialdectr'] = 1
            nml['initialconditions']['laiinitialgrass'] = 1.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.3
            nml['initialconditions']['porosity0'] = 0.2
        elif LeafCycle == 2:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.4
            nml['initialconditions']['porosity0'] = 0.3
        elif LeafCycle == 3:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.6
            nml['initialconditions']['porosity0'] = 0.5
        elif LeafCycle == 4:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4.5
            nml['initialconditions']['laiinitialgrass'] = 4.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.8
            nml['initialconditions']['porosity0'] = 0.6
        elif LeafCycle == 5:  # Summer
            nml['initialconditions']['gdd_1_0'] = 300
            nml['initialconditions']['gdd_2_0'] = 0
            nml['initialconditions']['laiinitialevetr'] = 5.1
            nml['initialconditions']['laiinitialdectr'] = 5.5
            nml['initialconditions']['laiinitialgrass'] = 5.9
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.8
            nml['initialconditions']['porosity0'] = 0.6
        elif LeafCycle == 6:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4, 5
            nml['initialconditions']['laiinitialgrass'] = 4.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.8
            nml['initialconditions']['porosity0'] = 0.5
        elif LeafCycle == 7:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.5
            nml['initialconditions']['porosity0'] = 0.4
        elif LeafCycle == 8:  # Late Autumn
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
            nml['initialconditions']['albEveTr0'] = 0.10
            nml['initialconditions']['albDecTr0'] = 0.12
            nml['initialconditions']['albGrass0'] = 0.18
            nml['initialconditions']['decidCap0'] = 0.4
            nml['initialconditions']['porosity0'] = 0.2

        nml['initialconditions']['snowinitially'] = snowinitially

        nml.write(initfileout, force=True)