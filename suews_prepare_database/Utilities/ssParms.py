# -*- coding: utf-8 -*-
'''
Calcualte input for spartacus to write info to Gridlayout namelist

Fredrik Lindberg 2023-07-06
'''
import numpy as np
from ..Utilities.db_functions import horizontal_aggregation, findwalls
#from ..Utilities.umep_suewsss_export_component import write_GridLayout_file, create_GridLayout_dict
import pandas as pd
# import matplotlib as plt
from qgis.PyQt.QtWidgets import QMessageBox

def ss_calc(build, cdsm, walls, numPixels):

    walllimit = 0.3 # 30 centimeters height variation identifies a vegetation edge pixel
    total = 100. / (int(build.shape[0] * build.shape[1]))

    if cdsm.max() > 0:
        vegEdges = findwalls(cdsm, walllimit)
 
    buildvec = build[np.where(build > 0)]
    if buildvec.size > 0:
        zHmax_all = buildvec.max()
        iterHeights = int(np.ceil(zHmax_all))
    else:
        zHmax_all = 0
        iterHeights = int(0)

    z = np.zeros((iterHeights, 1))
    paiZ_b = np.zeros((iterHeights, 1))
    bScale = np.zeros((iterHeights, 1)) # building scale
    paiZ_v = np.zeros((iterHeights, 1))
    vScale = np.zeros((iterHeights, 1)) # vegetation scale

    for i in np.arange(0, iterHeights):
        z[i] = i
        buildZ = build - i
        wallsZ = walls - i
        paiZ_b[i] = np.where(buildZ > 0)[0].shape[0] / numPixels
        waiZ_b = np.where(wallsZ > 0)[0].shape[0] / numPixels
        if waiZ_b == 0:
            bScale[i] = 0
        else:
            bScale[i] = (4*paiZ_b[i]) / waiZ_b

        if cdsm.max() > 0:
            vegZ = cdsm - i
            vegedgeZ = vegEdges - i
            paiZ_v[i] = np.where(vegZ > 0)[0].shape[0] / numPixels
            if paiZ_v[i] == 0:
                vScale[i] = 0
            else:
                waiZ_v = np.where(vegedgeZ > 0)[0].shape[0] / numPixels
                if waiZ_v == 0:
                    vScale[i] = 0
                else:
                    vScale[i] = (4*paiZ_v[i]) / waiZ_v
        else:
            paiZ_v[i] = 0
            vScale[i] = 0

    ssResult = {'z': z, 'paiZ_b': paiZ_b, 'bScale': bScale,'paiZ_v': paiZ_v, 'vScale': vScale}

    return ssResult

# GridArea*PAI 

def getVertheights(ssVect, heightMethod, vertHeightsIn, nlayerIn, skew, id):
    '''
    Input:
    ssVect: array from xx_IMPGrid_SS_x.txt
    heightMethod: Method used to set vertical layers
    vertheightsIn: heights of intermediate layers (bottom is 0 and top is maxzH) [option 1]
    nlayersIn: no of vertical layers [option 1 and 2]
    skew: 1 is equal interval between heights and 2 is exponential [option 2 and 3]
    '''
    #error_output={}
    if heightMethod == 1: # static levels (taken from interface). Last value > max height
        # if ssVect['z'].max() < max(vertHeightsIn):
        #     error_output = {id : f'zMax ({str(ssVect['z'].max())}) is lower than max fixed height  {str(max(vertHeightsIn))}.'}
        #     print('error in ID: ', str(id), f'. zMax is lower than max fixed height {str(max(vertHeightsIn))}.')
        if ssVect['z'].max() > max(vertHeightsIn):
            vertHeightsIn.append(ssVect['z'].max())
        heightIntervals = vertHeightsIn
        nlayerOut = len(heightIntervals) - 1

    elif heightMethod == 2: # always nlayers layer based on percentiles
        nlayerOut = nlayerIn
        # if ssVect['z'].max() <= nlayerOut:
        #     error_output = {id : f'zMax ({str(ssVect['z'].max())}) is to low to use {str(nlayerOut)} vertical layers.'}
        #     print('error in ID: ', str(id), f'. zMax is to low to use {str(nlayerOut)} vertical layers.')
            # QMessageBox.critical(None, "Error in Vertical Morphology Spartcus ", 'error in ID: ' + str(id) + '. zMax (' + str(ssVect['z'].max()) + ') is to low to use ' + str(nlayerOut) + ' vertical layers.')
            # return

    elif heightMethod == 3: # vary number of layers based on height variation. Lowest no of nlayers always 3
        nlayerOut = 3
        if ssVect['z'].max() > 40: nlayerOut = 4
        if ssVect['z'].max() > 60: nlayerOut = 5
        if ssVect['z'].max() > 80: nlayerOut = 6
        if ssVect['z'].max() > 120: nlayerOut = 7

    if heightMethod > 1: # detrmine if exponential hieght should be used
        intervals = np.ceil(ssVect['z'].max() / nlayerOut) #TODO: Fix if no buildings and/or no veg is present.
        heightIntervals = []
        heightIntervals.append(.0)
        for i in range(1, nlayerOut):
            heightIntervals.append(float(round((intervals * i) / skew)))
        heightIntervals.append(float(ssVect['z'].max()))

    return heightIntervals, nlayerOut #, error_output Moved out


def calculate_fractions(dictTypofrac, heights):
    """
    Calculates the distribution (fractions) of roof and wall areas for each typology
    across vertical height intervals.

    Parameters:
        dictTypofrac (dict): Dictionary mapping vertical levels to typology data
                             with 'roofSum' and 'wallSum' values.
        heights (list of float): List of vertical layer boundaries (e.g., [0.0, 2.0, 5.0, 13.0]).

    Returns:
        dict: Nested dictionary of fractions per height interval and typology.
    """
    fractions = {}

    # Loop through each vertical interval
    for i in range(len(heights) - 1):
        lower_bound = heights[i]
        upper_bound = heights[i + 1]

        # Identify all levels within the current height interval
        relevant_levels = [k for k in dictTypofrac if lower_bound <= k < upper_bound]

        # Sum all roof and wall areas in this interval
        total_roof_sum = sum(
            dictTypofrac[level][typo]['roofSum']
            for level in relevant_levels
            for typo in dictTypofrac[level]
        )
        total_wall_sum = sum(
            dictTypofrac[level][typo]['wallSum']
            for level in relevant_levels
            for typo in dictTypofrac[level]
        )

        fractions[i] = {}

        # Compute fractions per typology in this interval
        for level in relevant_levels:
            for typo, data in dictTypofrac[level].items():
                # Compute relative contribution (avoid division by zero)
                roof_fraction = data['roofSum'] / total_roof_sum if total_roof_sum > 0 else 0
                wall_fraction = data['wallSum'] / total_wall_sum if total_wall_sum > 0 else 0

                # Store or accumulate fractions per typology
                if typo not in fractions[i]:
                    fractions[i][typo] = {
                        'roofFraction': round(roof_fraction, 5),
                        'wallFraction': round(wall_fraction, 5)
                    }
                else:
                    # If this typology appears in multiple levels in the interval, sum its contribution
                    fractions[i][typo]['roofFraction'] += round(roof_fraction, 5)
                    fractions[i][typo]['wallFraction'] += round(wall_fraction, 5)

    return fractions

def ss_calc_gridlayout(build_array, wall_array, typoList, typo_array, gridlayoutOut, id ,db_dict, zenodo, ss_dir, pre, grid_dict):
    '''
    This function calculates all values in GridLayout based on typology and morhpology
    '''

    ssVect  = pd.read_csv(ss_dir + '/' + pre + '_IMPGrid_SS_' + str(id) + '.txt', sep='\s+')

    dictTypofrac = {} # empty dict to calc fractions for current grid and typology for each meter
    allRoof = [] #for sfr_roof
    allWall = [] #for sfr_wall
    
    vertical_layers = {
        'nlayer': {'value': gridlayoutOut[id]['nlayer']},
        'height': {'value': gridlayoutOut[id]['height']},
        'veg_frac': {'value': []},#gridlayoutOut[id]['paiZ_v']},
        'veg_scale': {'value': [] },#gridlayoutOut[id]['vScale']},
        'building_frac': {'value': [] },#gridlayoutOut[id]['paiZ_b']},
        'building_scale': {'value': [] },# gridlayoutOut[id]['bScale']},
        'roofs' : {},
        'walls' : {}
        }
    
    index = int(0)
    for i in range(1,len(gridlayoutOut[id]['height'])): #TODO this loop need to be confirmed by Reading
        index += 1
        startH = int(gridlayoutOut[id]['height'][index-1])
        endH = int(gridlayoutOut[id]['height'][index])
        if index == 1:
            vertical_layers['building_frac']['value'].append(ssVect.loc[0,'paib']) # first is plan area index of buildings
            vertical_layers['veg_frac']['value'].append(ssVect.loc[0,'paiv']) # first is plan area index of trees
        else:
            vertical_layers['building_frac']['value'].append(np.round(np.mean(ssVect.loc[startH:endH, 'paib']),3)) # intergrated pai_build mean in ith vertical layer
            vertical_layers['veg_frac']['value'].append(np.round(np.mean(ssVect.loc[startH:endH, 'paiv']),3)) # intergrated pai_veg mean in ith vertical layer

        vertical_layers['building_scale']['value'].append(np.round(np.mean(ssVect.loc[startH:endH, 'bScale']),3)) # intergrated bscale mean in ith vertical layer
        vertical_layers['veg_scale']['value'].append(np.round(np.mean(ssVect.loc[startH:endH, 'vScale']),3)) # intergrated vscale mean in ith vertical layer
    

    if len(typoList) != 1:

        for hh in range(0, int(max(gridlayoutOut[id]['height']) + 1)):
            dictTypofrac[hh] = {}
            buildhh = build_array - hh
            buildhh[buildhh < 0] = 0
            buildhhBol = buildhh > 0
            allRoof.append(len(buildhhBol[np.where(buildhhBol != 0)]))
            wallhh = wall_array - hh
            wallhh[wallhh < 0] = 0 
            allWall.append(wallhh.sum())
            totBuildPixelsInTypo = 0
            totWallAreaTypo = 0

            for tt in typoList:
                if tt != 0:
                    dictTypofrac[hh][int(tt)] = {}
                    tR = buildhhBol[np.where(typo_array == tt)]
                    dictTypofrac[hh][tt]['roofSum'] = tR.sum()
                    totBuildPixelsInTypo += tR.sum()
                    tW = wallhh[np.where(typo_array == tt)]
                    dictTypofrac[hh][tt]['wallSum'] = tW.sum()
                    totWallAreaTypo += tW.sum()

        
        # Calculate fractions
        typ_frac_heights_dict = calculate_fractions(dictTypofrac, gridlayoutOut[id]['height']) 

        typology_ss_dict = {}
        for typology in list(grid_dict.keys()):#typoList[1:]:
            building_code = db_dict['Types'].loc[typology,'Buildings']
            spartacus_code = db_dict['NonVeg'].loc[building_code, 'Spartacus Surface']
            typology_ss_dict[typology] = {}
            typology_ss_dict[typology] = {
                'building_code' : building_code,
                'spartacus_code' : spartacus_code,
                'wall' : {
                    'thermal_layers': {'value': horizontal_aggregation(spartacus_code, 'w', db_dict, no_rho = False)},
                    'albedo' : db_dict['Spartacus Material'].loc[(db_dict['Spartacus Surface'].loc[spartacus_code, 'w1Material']), 'Albedo'],
                    'emissivity' : db_dict['Spartacus Material'].loc[(db_dict['Spartacus Surface'].loc[spartacus_code, 'w1Material']), 'Emissivity'],
                },
                'roof' : {
                    'thermal_layers': {'value' : horizontal_aggregation(spartacus_code, 'r', db_dict, no_rho = False)},
                    'albedo' : db_dict['Spartacus Material'].loc[(db_dict['Spartacus Surface'].loc[spartacus_code, 'r1Material']), 'Albedo'],
                    'emissivity' : db_dict['Spartacus Material'].loc[(db_dict['Spartacus Surface'].loc[spartacus_code, 'r1Material']), 'Emissivity'],
                },
            }
    
            for vert_heights in list(typ_frac_heights_dict.keys()):

                typology_ss_dict[typology][vert_heights] = {
                    'wallfrac' : typ_frac_heights_dict[vert_heights][typology]['wallFraction'],
                    'rooffrac' : typ_frac_heights_dict[vert_heights][typology]['roofFraction']
                }
        
        weights = []
        for typo in list(grid_dict.keys()):
            weights.append(grid_dict[typo]['SAreaFrac']) 

        # Aggregation based on the provided steps
        for surface in ['roof','wall']:
            ss_list = []
            for vlayer in [1]:
                dz_list = []
                rho_list = []
                cp_list = []
                k_list = []
                C_list = []
            
                for hlayer in range(5):
                    dz_wall = [typology_ss_dict[typology][surface]['thermal_layers']['value']['dz']['value'][hlayer] for typology in typology_ss_dict]
                    rho_wall = [typology_ss_dict[typology][surface]['thermal_layers']['value']['rho']['value'][hlayer] for typology in typology_ss_dict]
                    cp_wall = [typology_ss_dict[typology][surface]['thermal_layers']['value']['cp']['value'][hlayer] for typology in typology_ss_dict]
                    k_wall = [typology_ss_dict[typology][surface]['thermal_layers']['value']['k']['value'][hlayer] for typology in typology_ss_dict]
                    alb_wall = [typology_ss_dict[typology][surface]['albedo'] for typology in typology_ss_dict]
                    emis_wall =[typology_ss_dict[typology][surface]['emissivity'] for typology in typology_ss_dict]

                    # Aggregate thickness on weighted average

                    # Filter out the nan values and corresponding weights
                    filtered_dz_wall = [dz_wall[i] for i in range(len(dz_wall)) if not np.isnan(dz_wall[i])]
                    if len(filtered_dz_wall) > 0:

                        filtered_rho_wall = [rho_wall[i] for i in range(len(rho_wall)) if not np.isnan(rho_wall[i])]
                        filtered_cp_wall = [cp_wall[i] for i in range(len(cp_wall)) if not np.isnan(cp_wall[i])]
                        filtered_k_wall = [k_wall[i] for i in range(len(k_wall)) if not np.isnan(k_wall[i])]
                        
                        filtered_weights = [weights[i] for i in range(len(weights)) if not np.isnan(dz_wall[i])]

                        # Recalculate the weights to sum up to 1
                        total_weight = sum(filtered_weights)

                        normalized_weights = [w / total_weight for w in filtered_weights]

                        # Weighted average of thickness
                        dz_agg = np.average(filtered_dz_wall, weights=normalized_weights)

                        # Weighted average of density (if needed, but you mention rho not in YAML)
                        rho_agg = np.average(filtered_rho_wall, weights=normalized_weights)

                        # Aggregate thermal conductivity
                        r_wall = [dz / k for dz, k in zip(filtered_dz_wall, filtered_k_wall)]
                        r_agg = np.average(r_wall, weights=normalized_weights)
                        k_agg = dz_agg / r_agg
            
                        # aggregate specific heat capacity
                        cp_agg = sum(cp * rho * dz * weight for cp, rho, dz, weight in zip(filtered_cp_wall, filtered_rho_wall, filtered_dz_wall, normalized_weights)) / (dz_agg * rho_agg)

                        # VOlumentrcu
                        C_agg = cp_agg * rho_agg

                        dz_list.append(round(dz_agg,4))
                        rho_list.append(round(rho_agg,4))
                        k_list.append(round(k_agg,4))
                        cp_list.append(round(cp_agg,4))
                        C_list.append(round(C_agg,4))

                        # Aggregate albedo and emissivity on weighted average
                        alb_agg = np.average(alb_wall, weights=weights)
                        emis_agg = np.average(emis_wall, weights=weights)
                
                    else:
                        # Fill with nothing if nothing existst
                        dz_list.append(-9)
                        rho_list.append(-9)
                        k_list.append(-9)
                        cp_list.append(-9)
                        C_list.append(-9)

                        # Aggregate albedo and emissivity on weighted average
                        alb_agg = np.average(alb_wall, weights=weights)
                        emis_agg = np.average(emis_wall, weights=weights)
                
                layer = {
                    'alb': {
                        'value' : round(alb_agg, 3),
                    },
                    'emis': {
                        'value' : round(emis_agg,3)
                    },
                    'thermal_layers':{
                        'dz': {'value': dz_list},
                        'k': {'value': k_list},
                        'rho_cp': {'value': C_list},
                        # 'rho': rho_list
                        },
                    'statelimit': {'value' :5},
                    'soilstorecap': {'value' : 5},
                    'wetthresh': {'value' : 5},
                    'roof_albedo_dir_mult_fact': {'value' : 1.0},
                    'wall_specular_frac': {'value' : 0.0}
                    }
                ss_list.append(layer)
            vertical_layers[surface+'s'] = ss_list
    
    # TODO Add reference texts

    else:
        surface_code = typoList[0]
        building_code = db_dict['Types'].loc[surface_code,'Buildings']
        code = db_dict['NonVeg'].loc[building_code, 'Spartacus Surface']

        spartacus_sel = db_dict['Spartacus Surface'].loc[code]

        for surface in ['roof', 'wall']:

            ss_list = []
            for vlayer in range(0, gridlayoutOut[id]['nlayer']):

                layer = {
                    'alb': {
                        'value' : spartacus_sel[f'albedo_{surface}'],
                    },
                    'emis': {
                        'value' : spartacus_sel[f'emissivity_{surface}'],
                    },
                    'thermal_layers': horizontal_aggregation(code, surface[0], db_dict, no_rho=True),
                    'statelimit': {'value' :5},
                    'soilstorecap': {'value' : 5},
                    'wetthresh': {'value' : 5},
                    'roof_albedo_dir_mult_fact': {'value' : 1.0},
                    'wall_specular_frac': {'value' : 0.0}
                    }

                try:
                    layer['alb']['ref'] = {
                        'desc': db_dict['Spartacus Material'].loc[spartacus_sel[f'{surface[0]}1Material'], 'nameOrigin'],
                        'ID' : str(spartacus_sel[f'{surface[0]}1Material']),
                        'DOI': zenodo
                        }
                    
                    layer['emis']['ref'] = {
                        'desc': db_dict['Spartacus Material'].loc[spartacus_sel[f'{surface[0]}1Material'], 'nameOrigin'],
                        'ID' : str(spartacus_sel[f'{surface[0]}1Material']),
                        'DOI': zenodo
                        }

                except:
                    pass

                ss_list.append(layer)
            vertical_layers[surface+'s'] = ss_list

    return vertical_layers