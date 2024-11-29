# -*- coding: utf-8 -*-
'''
Calcualte input for spartacus to write info to Gridlayout namelist

Fredrik Lindberg 2023-07-06
'''
import numpy as np
from ..Utilities import wallalgorithms as wa
#from ..Utilities.umep_suewsss_export_component import write_GridLayout_file, create_GridLayout_dict
import pandas as pd
# import matplotlib as plt
from qgis.PyQt.QtWidgets import QMessageBox

def ss_calc(build, cdsm, walls, numPixels, feedback):

    walllimit = 0.3 # 30 centimeters height variation identifies a vegetation edge pixel
    total = 100. / (int(build.shape[0] * build.shape[1]))

    if cdsm.max() > 0:
        vegEdges = wa.findwalls(cdsm, walllimit, feedback, total)
 
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
        # if ssVect[:,0].max() < max(vertHeightsIn):
        #     error_output = {id : f'zMax ({str(ssVect[:,0].max())}) is lower than max fixed height  {str(max(vertHeightsIn))}.'}
        #     print('error in ID: ', str(id), f'. zMax is lower than max fixed height {str(max(vertHeightsIn))}.')
        if ssVect[:,0].max() > max(vertHeightsIn):
            vertHeightsIn.append(ssVect[:,0].max())
        heightIntervals = vertHeightsIn
        nlayerOut = len(heightIntervals) - 1

    elif heightMethod == 2: # always nlayers layer based on percentiles
        nlayerOut = nlayerIn
        # if ssVect[:,0].max() <= nlayerOut:
        #     error_output = {id : f'zMax ({str(ssVect[:,0].max())}) is to low to use {str(nlayerOut)} vertical layers.'}
        #     print('error in ID: ', str(id), f'. zMax is to low to use {str(nlayerOut)} vertical layers.')
            # QMessageBox.critical(None, "Error in Vertical Morphology Spartcus ", 'error in ID: ' + str(id) + '. zMax (' + str(ssVect[:,0].max()) + ') is to low to use ' + str(nlayerOut) + ' vertical layers.')
            # return

    elif heightMethod == 3: # vary number of layers based on height variation. Lowest no of nlayers always 3
        nlayerOut = 3
        if ssVect[:,0].max() > 40: nlayerOut = 4
        if ssVect[:,0].max() > 60: nlayerOut = 5
        if ssVect[:,0].max() > 80: nlayerOut = 6
        if ssVect[:,0].max() > 120: nlayerOut = 7

    if heightMethod > 1: # detrmine if exponential hieght should be used
        intervals = np.ceil(ssVect[:,0].max() / nlayerOut) #TODO: Fix if no buildings and/or no veg is present.
        heightIntervals = []
        heightIntervals.append(.0)
        for i in range(1, nlayerOut):
            heightIntervals.append(float(round((intervals * i) / skew)))
        heightIntervals.append(float(ssVect[:,0].max()))


    return heightIntervals, nlayerOut #, error_output Moved out


def ss_calc_gridlayout(heightIntervals, build_array, wall_array, typoList, typo_array, grid_dict, gridlayoutOut, id, nlayer, db_dict):
    '''
    This function calculates all values in GridLayout based on typology and morhpology
    '''
    dictTypofrac = {} # empty dict to calc fractions for current grid and typology for each meter
    allRoof = [] #for sfr_roof
    allWall = [] #for sfr_wall
    dfT = pd.DataFrame(columns=['height','alb_roof','alb_wall','emis_roof','emis_wall','u_roof','u_wall'], index=range(int(max(heightIntervals)))) #df for temp storage

    for hh in range(0, int(max(heightIntervals) + 1)):
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
        albRoof = 0
        albWall = 0
        URoof = 0
        UWall = 0
        ERoof = 0
        EWall = 0
        for tt in typoList:
            if tt != 0:
                dictTypofrac[hh][tt]['roofFrac'] = dictTypofrac[hh][tt]['roofSum'] / totBuildPixelsInTypo
                dictTypofrac[hh][tt]['wallFrac'] = dictTypofrac[hh][tt]['wallSum'] / totWallAreaTypo
                albRoof = albRoof + dictTypofrac[hh][tt]['roofFrac'] * grid_dict[id][tt]['albedo_roof']
                albWall = albWall + dictTypofrac[hh][tt]['wallFrac'] * grid_dict[id][tt]['albedo_wall']
                URoof = URoof + dictTypofrac[hh][tt]['roofFrac'] * grid_dict[id][tt]['uvalue_roof']
                UWall = UWall + dictTypofrac[hh][tt]['wallFrac'] * grid_dict[id][tt]['uvalue_wall']
                ERoof = ERoof + dictTypofrac[hh][tt]['roofFrac'] * grid_dict[id][tt]['emissivity_roof']
                EWall = EWall + dictTypofrac[hh][tt]['wallFrac'] * grid_dict[id][tt]['emissivity_wall']
        dfT['height'][hh] = hh
        dfT['alb_roof'][hh] = albRoof
        dfT['alb_wall'][hh] = albWall
        dfT['u_roof'][hh] = URoof
        dfT['u_wall'][hh] = UWall
        dfT['emis_roof'][hh] = ERoof
        dfT['emis_wall'][hh] = EWall

    sfr_roof = []
    sfr_wall = []
    for fr in range(1,len(allRoof)):
        sfr_roof.append((allRoof[fr - 1] - allRoof[fr]) / allRoof[0])
        sfr_wall.append((allWall[fr - 1] - allWall[fr]) / allWall[0])
    
    # aggergation based on vertical layers
    gridlayoutOut[id]['sfr_roof'] = []
    gridlayoutOut[id]['sfr_wall'] = []
    gridlayoutOut[id]['alb_roof'] = []
    gridlayoutOut[id]['alb_wall'] = []
    gridlayoutOut[id]['emis_roof'] = []
    gridlayoutOut[id]['emis_wall'] = []
    gridlayoutOut[id]['u_roof'] = []
    gridlayoutOut[id]['u_wall'] = []
    start = int(0)
    for p in heightIntervals:
        if p > 0:
            gridlayoutOut[id]['sfr_roof'].append(np.sum(sfr_roof[start:int(p)]))
            gridlayoutOut[id]['sfr_wall'].append(np.sum(sfr_wall[start:int(p)]))
            gridlayoutOut[id]['alb_roof'].append(dfT['alb_roof'][start:int(p)].mean())
            gridlayoutOut[id]['alb_wall'].append(dfT['alb_wall'][start:int(p)].mean())
            gridlayoutOut[id]['emis_roof'].append(dfT['emis_roof'][start:int(p)].mean())
            gridlayoutOut[id]['emis_wall'].append(dfT['emis_wall'][start:int(p)].mean())
            gridlayoutOut[id]['u_roof'].append(dfT['u_roof'][start:int(p)].mean())
            gridlayoutOut[id]['u_wall'].append(dfT['u_wall'][start:int(p)].mean())
            start = int(p)

    # Find dominating typology in vertical layer and grid
    findDomTypo = {}
    domTypoWall = []
    domTypoRoof = []
    start = 0
    layer = 1
    #id = 1
    for p in heightIntervals:
        if p > 0:
            findDomTypo[layer] = {}
            for n in dictTypofrac[start].keys():
                findDomTypo[layer][n] = {}
                findDomTypo[layer][n]['wallFrac'] = 0
                findDomTypo[layer][n]['roofFrac'] = 0
            for hh in range(int(start), int(p + 1)):
                for q in dictTypofrac[0].keys():
                    findDomTypo[layer][q]['wallFrac'] = findDomTypo[layer][q]['wallFrac'] + dictTypofrac[hh][q]['wallFrac'] 
                    findDomTypo[layer][q]['roofFrac'] = findDomTypo[layer][q]['roofFrac'] + dictTypofrac[hh][q]['roofFrac']

            #Find dominating typology
            domTypoWall.append(max(findDomTypo[layer], key=lambda v: findDomTypo[layer][v]['wallFrac']))
            domTypoRoof.append(max(findDomTypo[layer], key=lambda v: findDomTypo[layer][v]['roofFrac']))

            layer = layer + 1
        start = p 

    # create list for gridlayoutOut
    for r in range(1, nlayer + 1): #iterate over number of vertical layers
        gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'] = []
        gridlayoutOut[id]['k_roof(' + str(r) + ',:)'] = []
        gridlayoutOut[id]['cp_roof(' + str(r) + ',:)'] = []
        gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'] = []
        gridlayoutOut[id]['k_wall(' + str(r) + ',:)'] = []
        gridlayoutOut[id]['cp_wall(' + str(r) + ',:)'] = []
        for s in range(1, 6): # iterate over number of horisontal layers in wall/roof
            if s <= 3: # fill first three from database
                # materialRoof = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[domTypoRoof[r-1], 'Spartacus Surface'], 'r' + str(s) + 'Material']
                # materialWall = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[domTypoWall[r-1], 'Spartacus Surface'], 'r' + str(s) + 'Material']
                materialRoof = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[db_dict['Types'].loc[domTypoRoof[r-1]]['Buildings']]['Spartacus Surface'], 'r' + str(s) + 'Material']
                materialWall = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[db_dict['Types'].loc[domTypoWall[r-1]]['Buildings']]['Spartacus Surface'], 'w' + str(s) + 'Material']
                # gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'].append(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[domTypoRoof[r-1], 'Spartacus Surface'], 'r' + str(s) + 'Thickness'])
                gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'].append(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[db_dict['Types'].loc[domTypoRoof[r-1]]['Buildings']]['Spartacus Surface'], 'r' + str(s) + 'Thickness'])
                gridlayoutOut[id]['k_roof(' + str(r) + ',:)'].append(db_dict['Spartacus Material'].loc[materialRoof]['Thermal Conductivity'])
                gridlayoutOut[id]['cp_roof(' + str(r) + ',:)'].append(db_dict['Spartacus Material'].loc[materialRoof]['Specific Heat'] * 1000)
                # gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'].append(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[domTypoWall[r-1], 'Spartacus Surface'], 'w' + str(s) + 'Thickness'])
                gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'].append(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[db_dict['Types'].loc[domTypoWall[r-1]]['Buildings']]['Spartacus Surface'], 'w' + str(s) + 'Thickness'])
                gridlayoutOut[id]['k_wall(' + str(r) + ',:)'].append(db_dict['Spartacus Material'].loc[materialWall]['Thermal Conductivity'])
                gridlayoutOut[id]['cp_wall(' + str(r) + ',:)'].append(db_dict['Spartacus Material'].loc[materialWall]['Specific Heat'] * 1000)
            else: # fill last two with thin wall paper (ignorable)
                gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'].append(0.001)
                gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'].append(0.001)
                gridlayoutOut[id]['k_roof(' + str(r) + ',:)'].append(1.2)
                gridlayoutOut[id]['k_wall(' + str(r) + ',:)'].append(1.2)
                gridlayoutOut[id]['cp_roof(' + str(r) + ',:)'].append(2000000.0)
                gridlayoutOut[id]['cp_wall(' + str(r) + ',:)'].append(2000000.0)

        #update middle layer with new thickness based on updated u-value (backward calculation)
        k_roof1 = gridlayoutOut[id]['k_roof(' + str(r) + ',:)'][0]
        k_roof2 = gridlayoutOut[id]['k_roof(' + str(r) + ',:)'][1]
        k_roof3 = gridlayoutOut[id]['k_roof(' + str(r) + ',:)'][2]
        dz_roof1 = gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'][0]
        #dz_roof2 = gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'][1]
        dz_roof3 = gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'][2]
        k_wall1 = gridlayoutOut[id]['k_wall(' + str(r) + ',:)'][0]
        k_wall2 = gridlayoutOut[id]['k_wall(' + str(r) + ',:)'][1]
        k_wall3 = gridlayoutOut[id]['k_wall(' + str(r) + ',:)'][2]
        dz_wall1 = gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'][0]
        #dz_wall2 = gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'][1]
        dz_wall3 = gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'][2]
        gridlayoutOut[id]['dz_roof(' + str(r) + ',:)'][1] = k_roof2 / gridlayoutOut[id]['u_roof'][r-1] - k_roof2 * ((dz_roof1/k_roof1)+dz_roof3/k_roof3)
        gridlayoutOut[id]['dz_wall(' + str(r) + ',:)'][1] = k_wall2 / gridlayoutOut[id]['u_wall'][r-1] - k_wall2 * ((dz_wall1/k_wall1)+dz_wall3/k_wall3)

    return gridlayoutOut