
'''
This module is used to transform UMEP pre-processing data to fit SuewsSS

input: 
ss_object: dictonary with all relevant inputs
refdir = outputfolder
fname = filename       
'''

import os
import numpy as np


def create_GridLayout_dict():

    ssDict = {}

    # dim
    ssDict['nlayer'] = 3 # number of vertical layers

    # geom
    ssDict['height'] = [0., 11., 15., 22.] # height of top of each layer (start with 0 i.e. one more than nlayers)
    ssDict['building_frac'] = [0.43, 0.38, .2] # fraction of building coverage of each layer; the first one is plan area index of buildings
    ssDict['veg_frac'] = [0.01, 0.02, .01] # fraction of vegetation coverage of each layer
    ssDict['building_scale'] =[50., 50., 50] # building scale of each layer [m]
    ssDict['veg_scale'] = [10., 10., 10] # vegetation scale of each layer [m]

    # roof
    ssDict['sfr_roof'] = [.3, .3, .4] # (sum should be 1)
    ssDict['tin_roof'] = [5, 5, 6] # initial temperatures of roofs [degC]
    ssDict['alb_roof'] = [.5, .5, .2]  #T albedo of roofs
    ssDict['emis_roof'] = [.95, .95, .95] # emissivity of roofs
    ssDict['state_roof'] = [.0, .0, .0]  # initial surface water depth state of roofs [mm]
    ssDict['statelimit_roof'] = [5, 5, 5] # surface water depth state limit of roofs [mm]
    ssDict['wetthresh_roof'] = [5, 5, 5] # surface water depth threshold of roofs (used in latent heat flux calculation) [mm]
    ssDict['soilstore_roof'] = [20, 20, 20] # soil water store of roofs [mm]
    ssDict['soilstorecap_roof'] = [120, 120, 120] # soil water store capacity of roofs [mm]
    ssDict['roof_albedo_dir_mult_fact'] = [1.,1.,1.] # initial surface water depth state of roofs [mm]

    # The following parameters are used to calculate the heat flux from the roof
    # first roof facet
    ssDict['dz_roof(1,:)'] = [.2, .1, .1, .01, .01] #TODO thickness of each layer (strictly five lyaers in total) [m]
    ssDict['k_roof(1,:)'] = [1.2, 1.2, 1.2, 1.2, 1.2] #TODO thermal conductivity of each layer [W/m/K]
    ssDict['cp_roof(1,:)'] = [2e6, 2e6, 2e6, 2e6, 2e6] #TODO specific heat capacity of each layer [J/kg/K]

    ssDict['dz_roof(2,:)'] = [.2, .1, .1, .01, .01] #TODO
    ssDict['k_roof(2,:)'] = [2.2, 1.2, 1.2, 1.2, 1.2] #TODO
    ssDict['cp_roof(2,:)'] = [2e6, 2e6, 2e6, 2e6, 2e6] #TODO

    ssDict['dz_roof(3,:)'] = [.2, .1, .1, .01, .01] #TODO
    ssDict['k_roof(3,:)'] = [2.2, 1.2, 1.2, 1.2, 1.2] #TODO
    ssDict['cp_roof(3,:)'] = [2e6, 2e6, 2e6, 2e6, 2e6] #TODO

    # wall # similarly to roof parameters but for walls
    ssDict['sfr_wall'] = [.3, .3, .4] # (sum should be 1)
    ssDict['tin_wall'] = [5, 5, 5]
    ssDict['alb_wall'] = [.5, .5, .5]
    ssDict['emis_wall'] = [.95, .95, .95]
    ssDict['state_wall'] = [.0, .0, .0]
    ssDict['statelimit_wall'] = [5, 5, 5]
    ssDict['wetthresh_wall'] = [5, 5, 5]
    ssDict['soilstore_wall'] = [20, 20, 20]
    ssDict['soilstorecap_wall'] = [120, 120, 120]
    ssDict['wall_specular_frac'] = [0.,0.,0.]

    ssDict['dz_wall(1,:)'] = [.2,  .1,  .1,  .01, .01]#TODO
    ssDict['k_wall(1,:)'] = [1.2, 1.2, 1.2, 1.2, 1.2]#TODO
    ssDict['cp_wall(1,:)'] = [3e6, 2e6, 2e6, 2e6, 2e6]#TODO

    ssDict['dz_wall(2,:)'] = [.2,  .1,  .1,  .01, .01]#TODO
    ssDict['k_wall(2,:)'] = [2.2, 1.2, 1.2, 1.2, 1.2]#TODO
    ssDict['cp_wall(2,:)'] = [2e6, 3e6, 2e6, 2e6, 2e6]#TODO

    ssDict['dz_wall(3,:)'] = [.2,  .1,  .1,  .01, .01]#TODO
    ssDict['k_wall(3,:)'] = [2.2, 1.2, 1.2, 1.2, 1.2]#TODO
    ssDict['cp_wall(3,:)'] = [2e6, 3e6, 2e6, 2e6, 2e6]#TODO

    # surf # for generic SUEWS surfaces, used in storage heat flux calculations
    ssDict['tin_surf'] = [2, 2, 2, 2, 2, 2, 2] # intitial temperature

    ssDict['dz_surf_paved'] = [.2,    .15,   .01,   .01,   .01]
    ssDict['k_surf_paved'] = [1.1,   1.1,   1.1,   1.1,   1.1]
    ssDict['cp_surf_paved'] = [2.2e6, 2.2e6, 2.2e6, 2.2e6, 2.6e6]

    ssDict['dz_surf_buildings'] = [.2,    .1,    .1,    .5,    1.6]
    ssDict['k_surf_buildings'] = [1.2,   1.1,   1.1,   1.5,   1.6]
    ssDict['cp_surf_buildings'] = [1.2e6, 1.1e6, 1.1e6, 1.5e6, 1.6e6]

    ssDict['dz_surf_evergreen'] = [.2,    .15,   .01,   .01,   .01]
    ssDict['k_surf_evergreen'] = [1.1,   1.1,   1.1,   1.1,   1.1]
    ssDict['cp_surf_evergreen'] = [3.2e6, 1.1e6, 1.1e6, 1.5e6, 1.6e6]

    ssDict['dz_surf_decid'] = [.2,    .1,    .1,    .1,    2.2]
    ssDict['k_surf_decid'] = [1.2,   1.1,   1.1,   1.5,   1.6]
    ssDict['cp_surf_decid'] = [3.2e6, 1.1e6, 1.1e6, 1.5e6, 1.6e6]

    ssDict['dz_surf_grass'] = [.2,    .05,   .1,    .1,    2.2]
    ssDict['k_surf_grass'] = [1.2,   1.1,   1.1,   1.5,   1.6]
    ssDict['cp_surf_grass'] = [1.6e6, 1.1e6, 1.1e6, 1.5e6, 1.6e6]

    ssDict['dz_surf_baresoil'] = [.2,    .05,   .1,    .1,    2.2]
    ssDict['k_surf_baresoil'] = [1.2,   1.1,   1.1,   1.5,   1.6]
    ssDict['cp_surf_baresoil'] = [1.9e6, 1.1e6, 1.1e6, 1.5e6, 1.6e6]

    ssDict['dz_surf_water'] = [.2,    .05,   .1,    .1,    2.2]
    ssDict['k_surf_water'] = [1.2,   1.1,   1.1,   1.5,   1.6]
    ssDict['cp_surf_water'] = [1.9e6, 1.1e6, 1.1e6, 1.5e6, 1.6e6]

    return ssDict


def writeGridLayout(ssVect, fileCode, featID, outputFolder, gridlayoutIn):
    '''
    Input:
    ssVect: array from xx_IMPGrid_SS_x.txt
    fileCode: from GUI
    featID: id of grid from vector polygon grid in GUI
    outputFolder: from GUI
    gridlayoutIn: dict with values to populate new values in ssDict
    '''

    ssDict = create_GridLayout_dict()
    
    ssDict['nlayer'] = gridlayoutIn[featID]['nlayer']
    ssDict['height'] = gridlayoutIn[featID]['height']
    ssDict['building_frac'] = []
    ssDict['veg_frac'] = []
    ssDict['building_scale'] = []
    ssDict['veg_scale'] = []

    index = int(0)
    for i in range(1,len(ssDict['height'])): #TODO this loop need to be confirmed by Reading
        index += 1
        startH = int(ssDict['height'][index-1])
        endH = int(ssDict['height'][index])
        if index == 1:
            ssDict['building_frac'].append(ssVect[0,1]) # first is plan area index of buildings
            ssDict['veg_frac'].append(ssVect[0,3]) # first is plan area index of trees
        else:
            ssDict['building_frac'].append(np.round(np.mean(ssVect[startH:endH, 1]),3)) # intergrated pai_build mean in ith vertical layer
            ssDict['veg_frac'].append(np.round(np.mean(ssVect[startH:endH, 3]),3)) # intergrated pai_veg mean in ith vertical layer

        ssDict['building_scale'].append(np.round(np.mean(ssVect[startH:endH, 2]),3)) # intergrated bscale mean in ith vertical layer
        ssDict['veg_scale'].append(np.round(np.mean(ssVect[startH:endH, 4]),3)) # intergrated vscale mean in ith vertical layer

    #roof
    ssDict['sfr_roof'] = gridlayoutIn[featID]['sfr_roof']
    ssDict['alb_roof'] = gridlayoutIn[featID]['alb_roof']
    ssDict['emis_roof'] = gridlayoutIn[featID]['emis_roof']

    for r in range(1, gridlayoutIn[featID]['nlayer'] + 1):
        ssDict['dz_roof(' + str(r) + ',:)'] = gridlayoutIn[featID]['dz_roof(' + str(r) + ',:)']
        ssDict['k_roof(' + str(r) + ',:)'] = gridlayoutIn[featID]['k_roof(' + str(r) + ',:)']
        ssDict['cp_roof(' + str(r) + ',:)'] = gridlayoutIn[featID]['cp_roof(' + str(r) + ',:)']

    #wall
    ssDict['sfr_wall'] = gridlayoutIn[featID]['sfr_wall']
    ssDict['alb_wall'] = gridlayoutIn[featID]['alb_wall']
    ssDict['emis_wall'] = gridlayoutIn[featID]['emis_wall']

    for r in range(1, gridlayoutIn[featID]['nlayer'] + 1):
        ssDict['dz_wall(' + str(r) + ',:)'] = gridlayoutIn[featID]['dz_wall(' + str(r) + ',:)']
        ssDict['k_wall(' + str(r) + ',:)'] = gridlayoutIn[featID]['k_wall(' + str(r) + ',:)']
        ssDict['cp_wall(' + str(r) + ',:)'] = gridlayoutIn[featID]['cp_wall(' + str(r) + ',:)']

    #TODO here we need to adjust post if vertical layers are not 3


    write_GridLayout_file(ssDict, outputFolder + '/', 'GridLayout' +  fileCode + str(featID))
    
    return ssDict

def write_GridLayout_file(ss_object, refdir, fname):
    ss_file_path = os.path.join(refdir,fname+".nml")
    f = open(ss_file_path, "w")

    f.write("&dim\n")
    f.write("nlayer = {}\n".format(ss_object['nlayer']))
    f.write("/\n")
    f.write("\n")

    f.write("&geom\n")
    f.write("height = {}\n".format(str(ss_object['height'])[1:-1]))
    f.write("building_frac = {}\n".format(str(ss_object['building_frac'])[1:-1]))
    f.write("veg_frac = {}\n".format(str(ss_object['veg_frac'])[1:-1]))
    f.write("building_scale = {}\n".format(str(ss_object['building_scale'])[1:-1]))
    f.write("veg_scale = {}\n".format(str(ss_object['veg_scale'])[1:-1]))
    f.write("/\n")
    f.write("\n")

    f.write("&roof\n")
    f.write("sfr_roof = {}\n".format(str(ss_object['sfr_roof'])[1:-1]))
    f.write("tin_roof = {}\n".format(str(ss_object['tin_roof'])[1:-1]))
    f.write("alb_roof = {}\n".format(str(ss_object['alb_roof'])[1:-1]))
    f.write("emis_roof = {}\n".format(str(ss_object['emis_roof'])[1:-1]))
    f.write("state_roof = {}\n".format(str(ss_object['state_roof'])[1:-1]))   
    f.write("statelimit_roof = {}\n".format(str(ss_object['statelimit_roof'])[1:-1]))      
    f.write("wetthresh_roof = {}\n".format(str(ss_object['wetthresh_roof'])[1:-1]))  
    f.write("soilstore_roof = {}\n".format(str(ss_object['soilstore_roof'])[1:-1]))     
    f.write("soilstorecap_roof = {}\n".format(str(ss_object['soilstorecap_roof'])[1:-1])) 
    f.write("\n")
    f.write("roof_albedo_dir_mult_fact(1,:) = {}\n".format(str(ss_object['roof_albedo_dir_mult_fact'])[1:-1]))   
    f.write("\n") 
    
    for j in range(1,ss_object['nlayer'] + 1):
        f.write("dz_roof(" + str(j) + ",:) = {}\n".format(str(ss_object['dz_roof(' + str(j) + ',:)'])[1:-1])) 
        f.write("k_roof(" + str(j) + ",:) = {}\n".format(str(ss_object['k_roof(' + str(j) + ',:)'])[1:-1])) 
        f.write("cp_roof(" + str(j) + ",:) = {}\n".format(str(ss_object['cp_roof(' + str(j) + ',:)'])[1:-1])) 
        f.write("\n")

    f.write("/\n")
    f.write("\n")

    f.write("&wall\n") 
    f.write("sfr_wall = {}\n".format(str(ss_object['sfr_wall'])[1:-1])) 
    f.write("tin_wall = {}\n".format(str(ss_object['tin_wall'])[1:-1]))   
    f.write("alb_wall = {}\n".format(str(ss_object['alb_wall'])[1:-1])) 
    f.write("emis_wall = {}\n".format(str(ss_object['emis_wall'])[1:-1]))   
    f.write("state_wall = {}\n".format(str(ss_object['state_wall'])[1:-1])) 
    f.write("statelimit_wall = {}\n".format(str(ss_object['statelimit_wall'])[1:-1]))      
    f.write("wetthresh_wall = {}\n".format(str(ss_object['wetthresh_wall'])[1:-1])) 
    f.write("soilstore_wall = {}\n".format(str(ss_object['soilstore_wall'])[1:-1]))    
    f.write("soilstorecap_wall = {}\n".format(str(ss_object['soilstorecap_wall'])[1:-1])) 
    f.write("\n")
    f.write("wall_specular_frac(1,:) = {}\n".format(str(ss_object['wall_specular_frac'])[1:-1]))    
    f.write("\n")

    for j in range(1,ss_object['nlayer'] + 1):
        f.write("dz_wall(" + str(j) + ",:) = {}\n".format(str(ss_object['dz_wall(' + str(j) + ',:)'])[1:-1])) 
        f.write("k_wall(" + str(j) + ",:) = {}\n".format(str(ss_object['k_wall(' + str(j) + ',:)'])[1:-1])) 
        f.write("cp_wall(" + str(j) + ",:) = {}\n".format(str(ss_object['cp_wall(' + str(j) + ',:)'])[1:-1])) 
        f.write("\n")

    f.write("/\n")
    f.write("\n")

    f.write("&surf\n") 
    f.write("tin_surf = {}\n".format(str(ss_object['tin_surf'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(1,:) = {}\n".format(str(ss_object['dz_surf_paved'])[1:-1]))
    f.write("k_surf(1,:) = {}\n".format(str(ss_object['k_surf_paved'])[1:-1]))
    f.write("cp_surf((1,:) = {}\n".format(str(ss_object['cp_surf_paved'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(2,:) = {}\n".format(str(ss_object['dz_surf_buildings'])[1:-1]))
    f.write("k_surf(2,:) = {}\n".format(str(ss_object['k_surf_buildings'])[1:-1]))
    f.write("cp_surf((2,:) = {}\n".format(str(ss_object['cp_surf_buildings'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(3,:) = {}\n".format(str(ss_object['dz_surf_evergreen'])[1:-1]))
    f.write("k_surf(3,:) = {}\n".format(str(ss_object['k_surf_evergreen'])[1:-1]))
    f.write("cp_surf((3,:) = {}\n".format(str(ss_object['cp_surf_evergreen'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(4,:) = {}\n".format(str(ss_object['dz_surf_decid'])[1:-1]))
    f.write("k_surf(4,:) = {}\n".format(str(ss_object['k_surf_decid'])[1:-1]))
    f.write("cp_surf((4,:) = {}\n".format(str(ss_object['cp_surf_decid'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(5,:) = {}\n".format(str(ss_object['dz_surf_grass'])[1:-1]))
    f.write("k_surf(5,:) = {}\n".format(str(ss_object['k_surf_grass'])[1:-1]))
    f.write("cp_surf((5,:) = {}\n".format(str(ss_object['cp_surf_grass'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(6,:) = {}\n".format(str(ss_object['dz_surf_baresoil'])[1:-1]))
    f.write("k_surf(6,:) = {}\n".format(str(ss_object['k_surf_baresoil'])[1:-1]))
    f.write("cp_surf((6,:) = {}\n".format(str(ss_object['cp_surf_baresoil'])[1:-1]))
    f.write("\n")
    f.write("dz_surf(7,:) = {}\n".format(str(ss_object['dz_surf_water'])[1:-1]))
    f.write("k_surf(7,:) = {}\n".format(str(ss_object['k_surf_water'])[1:-1]))
    f.write("cp_surf((7,:) = {}\n".format(str(ss_object['cp_surf_water'])[1:-1]))

    f.write("/\n")
    f.write("\n")
    f.close()

    return ss_file_path

