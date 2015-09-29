from __future__ import division
import data_io
import numpy as np
from collections import defaultdict
import json
import os
import csv
import itertools
import matplotlib.cm as cm
from math import radians


def write_roof_energy_raster(energy_year_wall,filename,trans,Energymonthroof=None):
    data_io.write_dem(energy_year_wall,filename,trans)

def get_rgb_color(energy_value,min_clamp=450,max_clamp=1150,colormap="RdYlBu_r"):
    if energy_value<min_clamp:
        energy_value=450
    elif energy_value>max_clamp:
        energy_value=1150
    energy_value=(energy_value-min_clamp)/(max_clamp-min_clamp)
    rgb_float=getattr(cm,colormap)(energy_value)
    return rgb_float

#steps=12
#for i in range(steps+1):
#    rgb_tuple=get_rgb_color(400.0+(i*750/steps),min_clamp=400,max_clamp=2150,colormap="RdYlBu_r")
#    print "%s-%s : %s" % (400.0+(i*750/steps),400+((i+1)*750/steps),rgb_tuple)

def get_roof_energy_blocks(energy_year_roof,building_dsm,building_slope,building_aspect,building_IDs,voxelsize):
    roof_row,roof_column=np.nonzero(building_IDs)
    print building_dsm.shape
    print building_IDs.shape
    assert(building_dsm.shape==building_IDs.shape)

    building_roof_dict=defaultdict(list)
    for x,y in itertools.izip(roof_row,roof_column):
        building_id=building_IDs[x,y]
        assert(building_id>0)
        energy=energy_year_roof[x,y]
        block_color=get_rgb_color(energy)
        aspect=building_aspect[x,y]
        slope=building_slope[x,y]
        building_roof_dict[building_id].append([x*voxelsize,y*voxelsize,building_dsm[x,y]-(voxelsize),radians(aspect),radians(slope),energy,block_color[0],block_color[1],block_color[2]])
    return building_roof_dict





def get_wall_energy_blocks(energy_year_wall,wall_angles,wall_ids,Energywall_index,voxelsize):
    #energy_year_wall=energy_year_wall/1000
    #wall_ids=wall_ids+1

    wall_row,wall_column=np.nonzero(wall_ids)

    print wall_row.shape
    print energy_year_wall.shape
    building_wall_blocks=defaultdict(list)
    wall_energy=defaultdict(int)

    for idx,((row,col),wall_block) in enumerate(zip(Energywall_index,energy_year_wall)):
        #print wall_block
        #row=wall_row[idx]
        #col=wall_column[idx]
        #building_id=wall_ids[wall_row[idx],wall_column[idx]]
        building_id=wall_ids[row,col]
        if building_id<=0:
            print "building_id",building_id
            print "idx: %s" % (idx)
            print "row: %s col: %s" % (row,col)
            assert(building_id>0)
        for z,block in enumerate(wall_block):
            if block==0:
                break
            block_color=get_rgb_color(block)
            building_wall_blocks[building_id].append([row*voxelsize,col*voxelsize,z*voxelsize,radians(wall_angles[row,col]),0,block,block_color[0],block_color[1],block_color[2]])
    return  building_wall_blocks


def generate_histogram(energy_blocks,bins=None):
    #bins=[0,200,300,400,500,600,700,800,900,1000,10000]
    if bins is None:
        bins=[0,700,750,800,850,900,950,1000,1050,1100,1150,10000]
    energy_histograms={}
    for building_id,blocks in energy_blocks.iteritems():
        blocks=np.array(blocks)
        energy_histograms[building_id]=np.histogram(blocks[:,5],bins=bins)
    return energy_histograms





def write_blocks_to_json_files(wall_blocks,roof_blocks,building_info,voxelsize,out_dir='.'):
    building_info_dict={}
    print "starting histogram"
    wall_bins=[0,450,500,550,600,650,700,750,800,850,900,10000]
    roof_bins=[0,700,750,800,850,900,950,1000,1050,1100,1150,10000]
    wall_energy_histograms=generate_histogram(wall_blocks,wall_bins)
    roof_energy_histograms=generate_histogram(roof_blocks,roof_bins)
    with open(building_info,'rb') as info:
        info_dict=csv.DictReader(info)
        for r in info_dict:
            building_info_dict[int(r['buildingID'])]=r


    for building_id,blocks in wall_blocks.iteritems():
        building_blocks={}
        wall_block_array=np.array(blocks)

        total_wall_energy=wall_block_array[:,5].sum()

        x_min=wall_block_array[:,0].min()
        x_max=wall_block_array[:,0].max()
        y_min=wall_block_array[:,1].min()
        y_max=wall_block_array[:,1].max()
        z_min=wall_block_array[:,2].min()
        z_max=wall_block_array[:,2].max()

        x_range=x_max-x_min
        y_range=y_max-y_min
        z_range=z_max-z_min

        wall_block_array[:,0]-=(x_min+x_range/2.0)
        wall_block_array[:,1]-=(y_min+y_range/2.0)
        #wall_block_array[:,2]-=z_min






        roof_block_array=np.array(roof_blocks[building_id])
        total_roof_energy=roof_block_array[:,5].sum()
        roof_block_array.shape
        roof_block_array[:,0]-=(x_min+x_range/2.0)
        roof_block_array[:,1]-=(y_min+y_range/2.0)
        roof_block_array[:,2]-=float(building_info_dict[building_id]['_wall_base_min'])

        building_blocks['x_range']=x_range
        building_blocks['y_range']=y_range
        building_blocks['z_range']=z_range
        building_blocks['z_offset']=z_min
        building_blocks['center_point']=(building_info_dict[building_id]['_lon'],building_info_dict[building_id]['_lat'])
        building_blocks['voxelsize']=voxelsize
        building_blocks['basemap_filename']=building_info_dict[building_id]['_image_filename']
        building_blocks['basemap_spacing_x']=building_info_dict[building_id]['_spacing_x']
        building_blocks['basemap_spacing_y']=building_info_dict[building_id]['_spacing_y']


        building_blocks['blocks']=np.vstack([wall_block_array,roof_block_array]).tolist()
        building_blocks['histogram']=(wall_energy_histograms[building_id][0]*(voxelsize**2)).tolist()
        building_blocks['roof_histogram']=(roof_energy_histograms[building_id][0]*(voxelsize**2)).tolist()
        building_blocks['total_wall_energy']=total_wall_energy*(voxelsize**2)
        building_blocks['total_roof_energy']=total_roof_energy*(voxelsize**2)
        orig_float_ecoder=json.encoder.FLOAT_REPR
        json.encoder.FLOAT_REPR = lambda o: format(o, '.3f')
        with open(os.path.join(out_dir,'blocks_building_%s.json' % (building_id)),'w') as j:
            json.dump(building_blocks,j,separators=(',',':'))
        json.encoder.FLOAT_REPR=orig_float_ecoder






