from pandas import ExcelFile, read_excel, DataFrame, read_csv
from numpy import nonzero, isnan, nan, vectorize, average, int32, int64, int8, float32,float64, zeros, pad, array, ones
from time import sleep
from datetime import datetime
from collections import defaultdict
from qgis.PyQt.QtWidgets import QMessageBox, QApplication
import sys
from scipy.ndimage import maximum_filter, label

zenodo = 'https://doi.org/10.5281/zenodo.2284987'

def read_DB(db_path):
    '''
    function for reading database and parse it to dictionary of dataframes
    nameOrigin is used for indexing and presenting the database entries in a understandable way for the user
    '''
    db_sh = ExcelFile(db_path)
    sheets = db_sh.sheet_names
    db = read_excel(db_path, sheet_name= sheets, index_col= 0)

    for col in sheets:
        
        if col == 'Name':
            db[col]['nameOrigin'] = db[col]['Name'].astype(str) + ', ' + db[col]['Origin'].astype(str)
        elif col == 'References': 
            db[col]['authorYear'] = db[col]['Author'].astype(str) + ', ' + db[col]['Year'].astype(str)
        elif col == 'Country':
            db[col]['nameOrigin'] = db[col]['Country'].astype(str) + ', ' + db[col]['City'].astype(str)  
        elif col == 'Region':
            pass
        elif col == 'Spartacus Material':
            db[col]['nameOrigin'] = db[col]['Name'].astype(str) + '; ' + db[col]['Color'].astype(str)
        # Calculate U-values for roof and wall new columns u_value_wall and u_value_roof
        
        elif col == 'Spartacus Surface':
            db[col]['nameOrigin'] = db[col]['Name'].astype(str) + ', ' + db[col]['Origin'].astype(str)
                # Filter rows where Surface is 'Buildings'
        
            buildings = db['Spartacus Surface'][db['Spartacus Surface']['Surface'] == 'Buildings']

            # Calculate resistances and U-values
            for prefix in ['w', 'r']:

                if prefix == 'w':
                    pr = 'wall'
                else:
                    pr = 'roof'
                materials = buildings[[f'{prefix}{i}Material' for i in range(1, 6)]].values
                thicknesses = buildings[[f'{prefix}{i}Thickness' for i in range(1, 6)]].values

                thicknesses[isnan(thicknesses)] = 0

                for i in range(0,5):
                    materials[isnan(materials)] = materials[nonzero(isnan(materials))[0], nonzero(isnan(materials))[1]-1]


                thermal_conductivities = vectorize(lambda x: db['Spartacus Material'].loc[x, 'Thermal Conductivity'])(materials)

                resistances = thicknesses / thermal_conductivities
                resistance_bulk = resistances.sum(axis=1)

                u_values = 1 / resistance_bulk

                db['Spartacus Surface'].loc[buildings.index, f'u_value_{pr}'] = u_values

            # Calculate albedo and emissivity
            for prop in ['Albedo', 'Emissivity']:
                for prefix, pr in zip(['w', 'r'], ['wall', 'roof']):

                    material_col = f'{prefix}1Material'
                    db['Spartacus Surface'].loc[buildings.index, f'{prop.lower()}_{pr}'] = db['Spartacus Material'].loc[buildings[material_col], prop].values
        
        elif col == 'Profiles':
            # Normalise traffic and energy use profiles to ensure that average of all columns = 1
            normalisation_rows = db[col][(db[col]['Profile Type'] == 'Traffic') | (db[col]['Profile Type'] == 'Energy use')]
            cols = list(range(24))
            normalisation_rows_index = list(normalisation_rows.index)

            # # # Calculate the sum of the values for each row
            sums = db[col].loc[normalisation_rows_index, cols].sum(axis=1)

            # Avoid division by zero by replacing zero sums with NaN
            sums.replace(0, nan, inplace=True)

            # # Calculate the scaling factor to make the sum equal to the number of columns (24)
            scaling_factors = 24 / sums

            # Scale the values
            db[col].loc[normalisation_rows_index, cols] = db[col].loc[normalisation_rows_index, cols].multiply(scaling_factors, axis=0)
            
            # Create unique name
            db[col]['nameOrigin'] = db[col]['Name'].astype(str)  +  ', ' + db[col]['Day'].astype(str) +  ', ' + db[col]['Country'].astype(str) + ', ' + db[col]['City'].astype(str) 

        else:
            # Standard
            db[col]['nameOrigin'] = db[col]['Name'].astype(str) + ', ' + db[col]['Origin'].astype(str)

    db_sh.close() # trying this to close excelfile

    return db

def count_buildings(dsm, dem):
    '''
    functuion for counting buildings in each grid using clipped DEM and DSM
    Nils Wallenberg 20250219
    '''
    dsm_ng = dsm - dem
    dsm_ng[dsm_ng < 2.0] = 0
    binary_mask = dsm_ng > 0
    structure = ones((3, 3), dtype=int8)  # 8-connectivity
    structure = array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
    labeled_array, num_buildings = label(binary_mask, structure=structure)

    return num_buildings

def read_morph_txt(txt_file):
    '''
    This function is used to read output files from morphometric calculator .txt
    '''
    morph_dict = read_csv(txt_file, sep=r"\s+", index_col=[0]).to_dict(orient='index')
    return morph_dict 


# for creating new_codes when aggregating

def GUI_lookup_dict(db_dict):
    # Initialize the dictionary with categories
    categories = [
        'Water use (manual)', 'Water use (automatic)', 'Energy use', 
        'Snow removal', 'Human activity', 'Traffic', 'Population density'
    ]

    new_dict = {category: {} for category in categories}

    # Populate the dictionary for profiles
    profiles = db_dict['Profiles']
    for code in profiles.index:
        profile_type = profiles.loc[code, 'Profile Type']
        if profile_type not in ['Residential', 'Commercial', 'Industry']:
            name_origin = profiles.loc[code, 'nameOrigin']
            
            new_dict[profile_type][name_origin] = code
            new_dict[profile_type][code] = name_origin

    # Populate the dictionary for anthropogenic emissions
    new_dict['AnthropogenicEmission'] = {}
    emissions = db_dict['AnthropogenicEmission']
    for code in emissions.index:
        name_origin = emissions.loc[code, 'nameOrigin']
        new_dict['AnthropogenicEmission'][code] = name_origin
        new_dict['AnthropogenicEmission'][name_origin] = code

    # Populate the dictionary for non-vegetation surfaces
    non_veg_surfaces = ['Paved', 'Buildings', 'Bare Soil']
    non_veg_table = db_dict['NonVeg']
    for surface in non_veg_surfaces:
        new_dict[surface] = {}
        surface_table = non_veg_table.loc[non_veg_table['Surface'] == surface]
        for code in surface_table.index:
            name_origin = surface_table.loc[code, 'nameOrigin']
            new_dict[surface][code] = name_origin
            new_dict[surface][name_origin] = code

    # Populate the dictionary for vegetation surfaces
    veg_surfaces = ['Grass', 'Deciduous Tree', 'Evergreen Tree']
    veg_table = db_dict['Veg']
    for surface in veg_surfaces:
        new_dict[surface] = {}
        surface_table = veg_table.loc[veg_table['Surface'] == surface]
        for code in surface_table.index:
            name_origin = surface_table.loc[code, 'nameOrigin']
            new_dict[surface][code] = name_origin
            new_dict[surface][name_origin] = code

    return new_dict

def create_code(table_name):

    '''
    Create new unique codes for DB and for SUEWS_table.txt files

    Syntax of code 8 digits.
    
    aa-bb-cccc
    aa = code that refers to code_id_dict. OHM code become 50 and Profiles 60 etc.
    bb = year. Last 2 digits. 24 for 2024 etc.
    cccc = milliseconds. Just a way to make the codes unique. 

    ex. 20244307 is a NonVeg code created sometime during 2024

    '''

    sleep(0.000001) # Slow down to make code unique
    table_code = str(code_id_dict[table_name]) 
    year = str(datetime.utcnow().strftime('%Y'))[2:]
    ms = str(datetime.utcnow().strftime('%S%f')) 
    code = int32(table_code + year + ms[4:])
    
    return code

    
# def show_popup():
#     app = QApplication(sys.argv)
#     msg = QMessageBox()
#     msg.setIcon(QMessageBox.Information)
#     msg.setWindowTitle("Information")
#     msg.setText("A difference has been detected. Please select which dataset you want to adjust building fractions from.")
#     landcover_button = msg.addButton("Landcover Dataset", QMessageBox.ActionRole)
#     dsm_button = msg.addButton("DSM Dataset", QMessageBox.ActionRole)
#     msg.exec_()

#     if msg.clickedButton() == landcover_button:
#         return 0
#     elif msg.clickedButton() == dsm_button:
#         return 1


def check_fraction_consistency(ss_dict):

    dataset_of_choice = 1 # Default value
    building_frac_lc = ss_dict['properties']['land_cover']['bldgs']['sfr']['value']
    paved_frac_lc = ss_dict['properties']['land_cover']['paved']['sfr']['value']
    # evergreen_frac_lc = ss_dict['properties']['land_cover']['evetr']['sfr']['value']
    # dec_frac_lc = ss_dict['properties']['land_cover']['dectr']['sfr']['value']
    # grass_frac_lc = ss_dict['properties']['land_cover']['grass']['sfr']['value']
    # bsoil_frac_lc = ss_dict['properties']['land_cover']['bsoil']['sfr']['value']
    # water_frac_lc = ss_dict['properties']['land_cover']['water']['sfr']['value']

    building_frac_spartacus = ss_dict['properties']['vertical_layers']['building_frac']['value'][0]

    diff = building_frac_lc - building_frac_spartacus

    if abs(diff) == 0:
        pass
    elif abs(diff) > 0 and abs(diff) < 0.03:
        print(f'Small difference of {round(abs(diff),4)} between PAI calculated from vertical morphology and Building Fraction detected, OK')
        # we can give user chance to chose on what datasource they think is best

        # If LC fraction is lower, we need to adjust that one since Spartacus needs to work with highest value or PAI at lowest vertical layer
        if dataset_of_choice == 0:
            diff = abs(diff)
            ss_dict['properties']['vertical_layers']['building_frac']['value'][0] = building_frac_lc
            
        elif dataset_of_choice == 1:
            diff = abs(diff)
            ss_dict['properties']['land_cover']['paved']['sfr']['value'] = paved_frac_lc - diff
            ss_dict['properties']['land_cover']['bldgs']['sfr']['value'] = building_frac_lc + diff

    elif abs(diff) > 0.03:
        print('error! ')
        print(f'Unreasonable Difference of {round(abs(diff),4)} between PAI calculated from vertical morphology and Building Fraction detected')

    return ss_dict

def convert_numpy_types(obj):
    ''' 
    function needed to convert numpy entries to naitive python float and int in the ss_dict. 
    yaml does not work with numpy
    '''
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, int32) or isinstance(obj, int64):
        return int(obj)
    elif isinstance(obj, float32) or isinstance(obj, float64):
        return float(obj)
    else:
        return obj

def round_dict(in_dict):
    in_dict = {k: round(v, 4) for k, v in in_dict.items()}
    return in_dict 

# function to examine DB if there is a parameter set for country, if not then use parameter set for region 
def decide_country_or_region(col, country_sel, reg):
    if str(country_sel[col].item()) == 'nan':
        var = reg.loc[reg['Region'] == country_sel['Region'].item(), col].item()
    else:
        var = country_sel[col].item()    
    return var

def horizontal_aggregation(surface_code, roofwall, db_dict, no_rho = False):

    surface = db_dict['Spartacus Surface'].loc[surface_code]
    insulation = surface[f'{roofwall}Insulation']

    agg_surface = DataFrame()
    horizontal_layers_list = []

    # Check for how many layers present in the surface
    for layer in range(1, 6):
        try:
            mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer}Material']]
            horizontal_layers_list.append(layer)
        except:
            pass

    layer1 = horizontal_layers_list[: insulation -1]
    layer2 = insulation
    layer3 = horizontal_layers_list[insulation:]

    # Check if insulation layer is set or not
    # IF no insulation
    if insulation == 6:
        
        d_list = []
        k_list = []
        rho_list = []
        cp_list = []

        for layer in horizontal_layers_list:
            
            mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer}Material']]
            d_list.append(surface[f'{roofwall}{layer}Thickness'])
            k_list.append(mat['Thermal Conductivity'])
            rho_list.append(mat['Density'])
            cp_list.append(mat['Specific Heat'])

        agg_surface.loc[1,'dz'] = sum(d_list)
        agg_surface.loc[1,'k'] = sum(d_list) / sum(d / k for d, k in zip(d_list, k_list))
        agg_surface.loc[1,'rho'] = sum(d * rho for d, rho in zip(d_list, rho_list)) / sum(d_list)
        agg_surface.loc[1,'cp'] = sum(d * rho * cp for d, rho, cp in zip(d_list, rho_list, cp_list)) / (agg_surface.loc[1,'rho'] * agg_surface.loc[1,'dz'])

        # Fill layer 2-5 with nan
        for layer in range(2,6):
            agg_surface.loc[layer,'dz'] = nan
            agg_surface.loc[layer,'k'] = nan
            agg_surface.loc[layer,'rho'] = nan
            agg_surface.loc[layer,'cp'] = nan

    # If insulation Exists. 
    else:
        # ------------------------------------- Layer 1 -------------------------------------
        #                                     Outer Layer
        # -----------------------------------------------------------------------------------

        d_list = []
        k_list = []
        rho_list = []
        cp_list = []

        if len(layer1) == 1:
            mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer1[0] }Material']]
            agg_surface.loc[1,'dz'] = surface[f'{roofwall}{layer1[0]}Thickness']
            agg_surface.loc[1,'k'] = mat['Thermal Conductivity']
            agg_surface.loc[1,'rho'] = mat['Density']
            agg_surface.loc[1,'cp'] = mat['Specific Heat']

        else:
            for layer in layer1:
                
                d_list.append(surface[f'{roofwall}{layer}Thickness'])
                mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer}Material']]
                k_list.append(mat['Thermal Conductivity'])
                rho_list.append(mat['Density'])
                cp_list.append(mat['Specific Heat'])

                agg_surface.loc[1,'dz'] = sum(d_list)
                agg_surface.loc[1,'k'] = sum(d_list) / sum(d / k for d, k in zip(d_list, k_list))
                agg_surface.loc[1,'rho'] = sum(d * k for d, k in zip(d_list, rho_list)) / sum(d_list)
                agg_surface.loc[1,'cp'] = sum(d * rho * cp for d, rho, cp in zip(d_list, rho_list, cp_list)) / (agg_surface.loc[1,'rho'] * agg_surface.loc[1,'dz'])

        # ------------------------------------- Layer 2 -------------------------------------
        #                                   Insulation Layer
        # -----------------------------------------------------------------------------------


        # Just take the values in the layer
        mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer2 }Material']]
        agg_surface.loc[2,'dz'] = surface[f'{roofwall}{layer2}Thickness']
        agg_surface.loc[2,'k'] = mat['Thermal Conductivity']
        agg_surface.loc[2,'rho'] = mat['Density']
        agg_surface.loc[2,'cp'] = mat['Specific Heat']

        # ------------------------------------- Layer 3 -------------------------------------
        #                                     Inner Layer
        # -----------------------------------------------------------------------------------
        
        if len(layer3) > 0:

            if len(layer3) == 1:
                mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer3[0]}Material']]
                agg_surface.loc[3,'dz'] = surface[f'{roofwall}{layer3[0]}Thickness']
                agg_surface.loc[3,'k'] = mat['Thermal Conductivity']
                agg_surface.loc[3,'rho'] = mat['Density']
                agg_surface.loc[3,'cp'] = mat['Specific Heat']

                # Fill 2 inner layers with nan
                for layer in range(4,6):
                    agg_surface.loc[layer,'dz'] = nan
                    agg_surface.loc[layer,'k'] = nan
                    agg_surface.loc[layer,'rho'] = nan
                    agg_surface.loc[layer,'cp'] = nan

            else:
                for layer in layer3:
                    d_list = []
                    k_list = []
                    rho_list = []
                    cp_list = []

                    for layer in layer3:
                        d_list.append(surface[f'{roofwall}{layer}Thickness'])
                        mat = db_dict['Spartacus Material'].loc[surface[f'{roofwall}{layer}Material']]
                        k_list.append(mat['Thermal Conductivity'])
                        rho_list.append(mat['Density'])
                        cp_list.append(mat['Specific Heat'])

                        agg_surface.loc[3,'dz'] = sum(d_list)
                        agg_surface.loc[3,'k'] = sum(d_list) / sum(d / k for d, k in zip(d_list, k_list))
                        agg_surface.loc[3,'rho'] = sum(d * k for d, k in zip(d_list, rho_list)) / sum(d_list)
                        agg_surface.loc[3,'cp'] = sum(d * rho * cp for d, rho, cp in zip(d_list, rho_list, cp_list)) / (agg_surface.loc[3,'rho'] * agg_surface.loc[3,'dz'])

                    # Fill 2 inner layers with nan
                    for layer in range(4,6):
                        agg_surface.loc[layer,'dz'] = nan
                        agg_surface.loc[layer,'k'] = nan
                        agg_surface.loc[layer,'rho'] = nan
                        agg_surface.loc[layer,'cp'] = nan

        else:
            for layer in range(3,6):
                agg_surface.loc[layer,'dz'] = nan
                agg_surface.loc[layer,'k'] = nan
                agg_surface.loc[layer,'rho'] = nan
                agg_surface.loc[layer,'cp'] = nan

        # -----------------------------------------------------------------------------------
    if no_rho == True:
        agg_surface['rho_cp'] = agg_surface['cp'] * agg_surface['rho']
        agg_surface = agg_surface.drop(columns = ['rho', 'cp'])
        agg_surface = agg_surface.round(3).loc[:,['dz','k','rho_cp']].to_dict()

    else:
        agg_surface = agg_surface.round(3).loc[:,['dz','k','cp','rho']].to_dict()

    agg_surface = {key: list(value.values()) for key, value in agg_surface.items()}
    agg_surface = {key: {'value': value} for key, value in agg_surface.items()}

    return agg_surface

def fill_SUEWS_AnthropogenicEmission(settings_dict, table):
    '''
    This function is used to assign correct params to selected Snow code
    Locator is selected code
    This needs to be fiddled with
    # TODO what params should be regional and not? Which ones should be removed
    '''
    locator =  settings_dict['AnthropogenicCode']
    table_dict = {
        'Code' : locator,
        'BaseT_HC' : table.loc[locator, 'BaseT_HC'],
        'QF_A_WD' : table.loc[locator, 'QF_A_WD'], 
        'QF_B_WD' : table.loc[locator, 'QF_B_WD'],
        'QF_C_WD' : table.loc[locator, 'QF_C_WD'],
        'QF_A_WE' : table.loc[locator, 'QF_A_WE'],
        'QF_B_WE' : table.loc[locator, 'QF_B_WE'],
        'QF_C_WE' : table.loc[locator, 'QF_C_WE'],
        'AHMin_WD' : table.loc[locator, 'AHMin_WD'],
        'AHMin_WE' : table.loc[locator, 'AHMin_WE'],
        'AHSlope_Heating_WD' : table.loc[locator, 'AHSlope_Heating_WD'],
        'AHSlope_Heating_WE' : table.loc[locator, 'AHSlope_Heating_WE'],
        'AHSlope_Cooling_WD' : table.loc[locator, 'AHSlope_Cooling_WD'],
        'AHSlope_Cooling_WE' : table.loc[locator, 'AHSlope_Cooling_WE'],
        'TCritic_Heating_WD' : table.loc[locator, 'TCritic_Heating_WD'],
        'TCritic_Heating_WE' : table.loc[locator, 'TCritic_Heating_WE'],
        'TCritic_Cooling_WD' : table.loc[locator, 'TCritic_Cooling_WD'],
        'TCritic_Cooling_WE' : table.loc[locator, 'TCritic_Cooling_WE'],
        'EnergyUseProfWD' : settings_dict['EnergyUseProfWD'],
        'EnergyUseProfWE' : settings_dict['EnergyUseProfWE'],
        'ActivityProfWD' : settings_dict['ActivityProfWD'],
        'ActivityProfWE' : settings_dict['ActivityProfWE'],
        'TraffProfWD' : settings_dict['TraffProfWD'],
        'TraffProfWE' : settings_dict['TraffProfWE'],
        'PopProfWD' : settings_dict['PopProfWD'],
        'PopProfWE' : settings_dict['PopProfWE'],
        'MinQFMetab' : table.loc[locator, 'MinQFMetab'],
        'MaxQFMetab' : table.loc[locator, 'MaxQFMetab'],
        'MinFCMetab' : table.loc[locator, 'MinFCMetab'],
        'MaxFCMetab' : table.loc[locator, 'MaxFCMetab'],
        'FrPDDwe' : table.loc[locator, 'FrPDDwe'],
        'FrFossilFuel_Heat' : table.loc[locator, 'FrFossilFuel_Heat'],
        'FrFossilFuel_NonHeat' : table.loc[locator, 'FrFossilFuel_NonHeat'],
        'EF_umolCO2perJ' : table.loc[locator, 'EF_umolCO2perJ'],
        'EnEF_v_Jkm' : table.loc[locator, 'EnEF_v_Jkm'],
        'FcEF_v_kgkmWD' : table.loc[locator, 'FcEF_v_kgkmWD'],
        'FcEF_v_kgkmWE' : table.loc[locator, 'FcEF_v_kgkmWE'],
        'CO2PointSource' : table.loc[locator, 'CO2PointSource'],
        'TrafficUnits' : table.loc[locator, 'TrafficUnits'],
    }
    
    return table_dict

def findwalls(arr_dsm, walllimit):
    # Get the shape of the input array
    col, row = arr_dsm.shape
    walls = zeros((col, row))
    
    # Create a padded version of the array
    padded_a = pad(arr_dsm, pad_width=1, mode='edge')

    # Create a footprint for cardinal points
    footprint = array([ [0, 1, 0],
                        [1, 0, 1],
                        [0, 1, 0]])

    # Use maximum_filter with the custom footprint
    max_neighbors = maximum_filter(padded_a, footprint=footprint, mode='constant', cval=0)
    
    # Identify wall pixels: walls are where the max neighbors are greater than the original DSM
    walls = max_neighbors[1:-1, 1:-1] - arr_dsm
   
    # Apply wall height limit
    walls[walls < walllimit] = 0

    # Set the edges to zero
    walls[0:walls.shape[0], 0] = 0
    walls[0:walls.shape[0], walls.shape[1] - 1] = 0
    walls[0, 0:walls.shape[1]] = 0
    walls[walls.shape[0] - 1, 0:walls.shape[1]] = 0
    
    return walls

def profiles_to_dict(settings_dict, prof, ref):
    
    profiles_list = ['TraffProfWE','TraffProfWD', 'EnergyUseProfWD','EnergyUseProfWE','ActivityProfWD',
                     'ActivityProfWE','PopProfWD','PopProfWE', 'SnowClearingProfWD', 'SnowClearingProfWE',
                     'WaterUseProfManuWD','WaterUseProfManuWE','WaterUseProfAutoWD','WaterUseProfAutoWE']        
    profile_dict = {}
    for profile in profiles_list:
        locator = settings_dict[profile]
        profile_dict[profile] = {
            '1': prof.loc[locator, 0],
            '2': prof.loc[locator, 1],
            '3': prof.loc[locator, 2],
            '4': prof.loc[locator, 3],
            '5': prof.loc[locator, 4],
            '6': prof.loc[locator, 5],
            '7': prof.loc[locator, 6],
            '8': prof.loc[locator, 7],
            '9': prof.loc[locator, 8],
            '10': prof.loc[locator, 9],
            '11': prof.loc[locator, 10],
            '12': prof.loc[locator, 11],
            '13':  prof.loc[locator, 12],
            '14':  prof.loc[locator, 13],
            '15':  prof.loc[locator, 14],
            '16': prof.loc[locator, 15],
            '17': prof.loc[locator, 16],
            '18': prof.loc[locator, 17],
            '19': prof.loc[locator, 18],
            '20':  prof.loc[locator, 19],
            '21': prof.loc[locator, 20],
            '22':  prof.loc[locator, 21],
            '23':  prof.loc[locator, 22],
            '24':  prof.loc[locator, 23],
            # 'ref' : {
            # 'desc' : prof.loc[locator, 'Profile Type'] + ', ' + prof.loc[locator, 'Day'] + ', ' + prof.loc[locator, 'Name'] + ', ' + prof.loc[locator, 'Country']  + ', ' + prof.loc[locator, 'City'],  
            # 'ID' : str(locator),
            # 'DOI': zenodo
            # } 
        }
        for dict_value in profile_dict:
            for key in list(profile_dict[dict_value].keys()):
                profile_dict[dict_value][key] = round(profile_dict[dict_value][key],2)
                
    return profile_dict
 

##########################################################################################################
####                                        TO YAML                                                    ###
##########################################################################################################

def fill_lai_yaml(indict, db_dict, zenodo):
    '''
    OB 20241212
    Function to fill LAI params in yaml file
    indict = dictionary for storing parameters related to Vegetated surfaces
    db_dict = db_dict
    '''
    VG_code = db_dict['Veg'].loc[indict['Code']['value'], 'Vegetation Growth']
    LAI_code = db_dict['Veg'].loc[indict['Code']['value'], 'Leaf Area Index']
    LGP_code = db_dict['Veg'].loc[indict['Code']['value'], 'Leaf Growth Power']

    lai = {
        # Vegetaion Growth
        'baset':{
            'value' : db_dict['Vegetation Growth'].loc[VG_code,'BaseT'],
            'ref' : {
                'desc' : db_dict['Vegetation Growth'].loc[VG_code, 'nameOrigin'],
                'ID' : str(VG_code),
                'DOI': zenodo
            }   
        },
        'basete': {
            'value' :db_dict['Vegetation Growth'].loc[VG_code,'BaseTe'],
            'ref' : {
                'desc' : db_dict['Vegetation Growth'].loc[VG_code, 'nameOrigin'],
                'ID' : str(VG_code),
                'DOI': zenodo
            }   
        },
        'gddfull':{
            'value' : db_dict['Vegetation Growth'].loc[VG_code,'GDDFull'],
            'ref' : {
                'desc' : db_dict['Vegetation Growth'].loc[VG_code, 'nameOrigin'],
                'ID' : str(VG_code),
                'DOI': zenodo
            }   
        },
        'sddfull': {
            'value' : db_dict['Vegetation Growth'].loc[VG_code,'SDDFull'],
            'ref' : {
                'desc' : db_dict['Vegetation Growth'].loc[VG_code, 'nameOrigin'],
                'ID' : str(VG_code),
                'DOI': zenodo,},
        },
        # LAI
        'laimin': {
            'value' : db_dict['Leaf Area Index'].loc[LAI_code,'LAIMin'],
            'ref' : {
            'desc' : db_dict['Leaf Area Index'].loc[LAI_code, 'nameOrigin'],
            'ID' : str(LAI_code),
            'DOI': zenodo
            }
        },
        'laimax': {
            'value' : db_dict['Leaf Area Index'].loc[LAI_code,'LAIMax'],
            'ref' : {
            'desc' : db_dict['Leaf Area Index'].loc[LAI_code, 'nameOrigin'],
            'ID' : str(LAI_code),
            'DOI': zenodo
            }
        },
        'laipower' : {
            # Leaf Growth Power
            'growth_lai': {
                'value': db_dict['Leaf Growth Power'].loc[LGP_code,'LeafGrowthPower1'],
                'ref' : {
                    'desc' : db_dict['Leaf Growth Power'].loc[LGP_code, 'nameOrigin'],
                    'ID' : str(LGP_code),
                    'DOI': zenodo
                }
            },
            'growth_gdd': {
                'value': db_dict['Leaf Growth Power'].loc[LGP_code, 'LeafGrowthPower1'],
                'ref' : {
                    'desc' : db_dict['Leaf Growth Power'].loc[LGP_code, 'nameOrigin'],
                    'ID' : str(LGP_code),
                    'DOI': zenodo
                }
            },
            'senescence_lai': {
                'value': db_dict['Leaf Growth Power'].loc[LGP_code,'LeafOffPower1'],
                'ref' : {
                    'desc' : db_dict['Leaf Growth Power'].loc[LGP_code, 'nameOrigin'],
                    'ID' : str(LGP_code),
                    'DOI': zenodo
                }
            },
            'senescence_sdd': {
                'value': db_dict['Leaf Growth Power'].loc[LGP_code,'LeafOffPower2'],
                'ref' : {
                    'desc' : db_dict['Leaf Growth Power'].loc[LGP_code, 'nameOrigin'],
                    'ID' : str(LGP_code),
                    'DOI': zenodo
                }
            },
            'ref' : {
                    'desc' : db_dict['Leaf Growth Power'].loc[LGP_code, 'nameOrigin'],
                    'ID' : str(LGP_code),
                    'DOI': zenodo
                }
        },     
        'laitype': {
            'value' : db_dict['Leaf Area Index'].loc[LAI_code,'LAIEq'],
            'ref' : {
                'desc' : db_dict['Leaf Area Index'].loc[LAI_code, 'nameOrigin'],
                'ID' : str(LAI_code),
                'DOI': zenodo
            }
        }
    }

    return lai

def fill_BiogenCO2_yaml(indict, db_dict, zenodo):
    '''
    OB 20241216
    Function to fill BiogenCO2 params in yaml file
    indict = dictionary for storing parameters related to Vegetated surfaces
    db_dict = db_dict
    '''

    BiogenCo2 = db_dict['Biogen CO2']
    BiogenCO2Code = indict['BiogenCO2Code']['value']
    veg_code = indict['Code']['value']
    MVC_code = db_dict['Veg'].loc[veg_code, 'Max Vegetation Conductance']
    
    def fill_BiogenCO2_params(param):
            b_dict = {
                    'value' : BiogenCo2.loc[BiogenCO2Code, param],
                    'ref' : {
                        'desc' : BiogenCo2.loc[BiogenCO2Code, 'nameOrigin'],
                        'ID' : str(BiogenCO2Code),
                        'DOI': zenodo
                    }
            }
            return b_dict

    biogen_dict = {
            
    'beta_enh_bioco2': fill_BiogenCO2_params('beta'),
    'alpha_bioco2': fill_BiogenCO2_params('alpha'),
    'alpha_enh_bioco2': fill_BiogenCO2_params('beta_enh'),
    'resp_a': fill_BiogenCO2_params('resp_a'),
    'resp_b': fill_BiogenCO2_params('resp_b'),
    'theta_bioco2': fill_BiogenCO2_params('theta'),
    'maxconductance': indict['MaxConductance'],
    'min_res_bioco2': fill_BiogenCO2_params('min_respi'),
    }

    return biogen_dict

def fill_snow_yaml(snow, indict, profiles_dict, zenodo):

    snow_dict = {
        'crwmax': {'value': indict['CRWMax']['value']},
        'crwmin': {'value': indict['CRWMin']['value']},
        'narp_emis_snow': { 'value': indict['Emissivity']['value']},
        'preciplimit': {'value': indict['PrecipLimSnow']['value']},
        'preciplimitalb': {'value': indict['PrecipLimAlb']['value']},
        'snowalbmin': {'value' : indict['AlbedoMin']['value']}, 
        'snowalbmax': {'value' : indict['AlbedoMax']['value']},
        'snowdensmin': {'value' : indict['SnowDensMin']['value']},
        'snowdensmax': {'value' : indict['SnowDensMax']['value']},
        
        'snowlimbldg': {
            'value': 100,
            'ref': {
                'desc': 'Example values [mm] [Järvi et al., 2014]'
            }
        },
        'snowlimpaved': {
            'value': 40,
            'ref': {
                'desc': 'Example values [mm] [Järvi et al., 2014]'
            }
        },
        'snowprof_24hr': {
            'working_day': profiles_dict['SnowClearingProfWD'],
            'holiday': profiles_dict['SnowClearingProfWE'],
        },
        'tau_a': {'value' : indict['tau_a']['value']},
        'tau_f': {'value' : indict['tau_f']['value']},
        'tau_r': {'value' : indict['tau_r']['value']},
        'tempmeltfact': {'value' : indict['TempMeltFactor']['value']},         
        'radmeltfact': {'value' : indict['RadMeltFactor']['value']},      
        
        'ref' : indict['ref']
    }

    return snow_dict

def fill_soil_yaml(db_dict, indict, surface, zenodo):
    '''
    OB 20241216
    Function to fill BiogenCO2 params in yaml file
    indict = dictionary for storing parameters related to Vegetated surfaces
    db_dict = db_dict
    surface = 'Veg', 'NonVeg' or 'Water
    '''

    soil_code = indict['SoilTypeCode']['value']
     
    soil_dict = {    
        # Soil
        'soildepth': {
            'value' : db_dict['Soil'].loc[soil_code,'SoilDepth'],
            'ref' : {
                'desc' : db_dict['Soil'].loc[soil_code,'nameOrigin'],
                'ID' : str(soil_code),
                'DOI': zenodo
                } 
        },
        'soilstorecap': {
            'value' : db_dict['Soil'].loc[soil_code,'SoilStoreCap'],
            'ref': {
                'desc' : db_dict['Soil'].loc[soil_code,'nameOrigin'],
                'ID' : str(soil_code),
                'DOI': zenodo 
            }
        },
        'sathydraulicconduct': {
            'value' : db_dict['Soil'].loc[soil_code,'SatHydraulicCond'],
            'ref'  : {
                'desc' : db_dict['Soil'].loc[soil_code,'nameOrigin'],
                'ID' : str(soil_code),
                'DOI': zenodo        
            }
        }
    }
    return soil_dict

def fill_bare_soil_yaml(indict, db_dict, LCF_baresoil, irrFr, zenodo, temp_bsoil):
    '''
     OB 20241216
    Function to fill bare_soil params in yaml file
    indict = dictionary for storing parameters related to bare soil i.e nonVeg_dict[feat_id]['Bare Soil']
    db_dict = db_dict 
    '''

    temp_bsoil['sfr']['value'] = round(LCF_baresoil,3)
    temp_bsoil['emis'] = indict['Emissivity']
    temp_bsoil['alb'] = indict['AlbedoMax']
    temp_bsoil['irrfrac']['value'] = irrFr

    temp_bsoil['ohm_coef'] = indict['ohm_coef']

    temp_bsoil['soildepth'] = {
        'value' : db_dict['Soil'].loc[indict['SoilTypeCode']['value'],'SoilDepth'],
        'ref' : {
            'desc' : db_dict['Soil'].loc[indict['SoilTypeCode']['value'],'nameOrigin'],
            'ID' :  str(indict['SoilTypeCode']['value']),
            'DOI': zenodo} 
        }
        
    temp_bsoil['storedrainprm'] = {
            'store_min': indict['StorageMin'],
            'store_max': indict['StorageMax'],
            'store_cap': indict['StorageMax'], #TODO THIS IS probably wrong this is current storage according to manual
            'drain_eq':  indict['DrainageEq'],
            'drain_coef_1': indict['DrainageCoef1'],
            'drain_coef_2': indict['DrainageCoef2'],
        }
    
        # 'waterdist': {      # TODO Neds to be set somehow
        #     'to_paved': {'value' : 0.0},
        #     'to_bldgs': {'value' : 0.0},
        #     'to_dectr': {'value' : 0.0},
        #     'to_evetr': {'value' : 0.0},
        #     'to_grass': {'value' : 0.0},
        #     'to_bsoil': {'value' : 0.0},
        #     'to_water': {'value' : 0.0},
        #     'to_soilstore': {'value' : 1},
        #     'to_runoff' : {'value' : 0}
        # },

    temp_bsoil = temp_bsoil | fill_soil_yaml(db_dict, indict, 'NonVeg', zenodo)
    temp_bsoil['ref'] = indict['ref']    

    return temp_bsoil

def fill_water_yaml(indict, db_dict, LCF_water, IrrFr_Water, zenodo, temp_water):
    '''
    OB 20241216
    Function to fill water_surface params in yaml file
    indict = dictionary for storing parameters related to water i.e water_dict
    db_dict = db_dict 
    '''

    temp_water['sfr']['value'] = round(LCF_water,3)
    temp_water['emis'] = indict['Emissivity']
    temp_water['alb'] = indict['AlbedoMax']

    temp_water['ohm_coef'] = indict['ohm_coef']
        
    temp_water['statelimit'] = indict['StateLimit']

    temp_water['storedrainprm'] = {
            'store_min': indict['StorageMin'],
            'store_max': indict['StorageMax'],
            'store_cap': indict['StorageMax'], #TODO THIS IS probably wrong this is current storage according to manual
            'drain_eq':  indict['DrainageEq'],
            'drain_coef_1': indict['DrainageCoef1'],
            'drain_coef_2': indict['DrainageCoef2'],
        }
        
    temp_water['irrfrac']['value'] = IrrFr_Water
    
    temp_water = temp_water | fill_soil_yaml(db_dict, indict, 'Water', zenodo)

    temp_water['ref'] = indict['ref'] 
    
    return temp_water

def fill_veg_yaml(veg_dict, db_dict, surface, LCF, irrFr, IMPveg_fai, IMPveg_heights_mean, irr_code, zenodo, temp_veg): 
    temp_veg['sfr']['value'] = round(LCF,3)
    temp_veg['emis'] = veg_dict[surface]['Emissivity']
    temp_veg['alb_min'] = veg_dict[surface]['AlbedoMin']
    temp_veg['alb_max'] = veg_dict[surface]['AlbedoMax']
        # # OHM
        # 'ohm_threshsw': {
        #     'value': 10., # TODO This param is static at the moment. Needs to be set somehow.,
        #     'ref' : {
        #         'desc' : 'Example values from Ward, H. C.; Kotthaus, S.; Järvi, L.; Grimmond, C. S. B.(2016)',
        #         'DOI' : db_dict['References'].loc[90240002, 'DOI']
        #     }
        # },

        # 'ohm_threshwd': {
        #     'value':0.9, # TODO This param is static at the moment. Needs to be set somehow.,
        #     'ref' : {
        #         'desc' : 'Example values from Ward, H. C.; Kotthaus, S.; Järvi, L.; Grimmond, C. S. B.(2016)',
        #         'DOI' : db_dict['References'].loc[90240002, 'DOI']
        #     }
        # },

    temp_veg['ohm_coef'] = veg_dict[surface]['ohm_coef']

        #  LAI
    temp_veg['lai'] = fill_lai_yaml(veg_dict[surface], db_dict, zenodo)

        # Storage and drainage
    temp_veg['storedrainprm'] = {
            'store_min': veg_dict[surface]['StorageMin'],
            'store_max': veg_dict[surface]['StorageMax'],
            'store_cap': veg_dict[surface]['StorageMax'], #TODO THIS IS probably wrong this is current storage according to manual
            'drain_eq':  veg_dict[surface]['DrainageEq'],
            'drain_coef_1': veg_dict[surface]['DrainageCoef1'],
            'drain_coef_2': veg_dict[surface]['DrainageCoef2'],
        }
        
        # # Snow Packlimit
        # 'snowpacklimit': {
        #     'value' :  190,
        #     'ref' : {
        #         'desc' : 'Example Values from Järvi et al., (2014)',
        #         'DOI' : 'https://suews.readthedocs.io/en/latest/input_files/SUEWS_SiteInfo/Input_Options.html#cmdoption-arg-SnowLimPatch : SnowLimPatch'  #TODO At the moment Hardcoded needs to be set somehow
        #     }
        # },
        
    temp_veg['irrfrac']['value'] =  irrFr

    if surface == 'Evergreen Tree':
        temp_veg['faievetree'] = {'value': IMPveg_fai}
        temp_veg['evetreeh'] = {'value': IMPveg_heights_mean}
        temp_veg['ie_a'] = {
            'value' : db_dict['Irrigation'].loc[irr_code, 'Ie_a1'],
            'ref' : {
                'desc' : db_dict['Irrigation'].loc[irr_code, 'nameOrigin'], 
                'ID' : str(irr_code),
                'DOI': zenodo
                } 
            }
        temp_veg['ie_m'] =  {
            'value' : db_dict['Irrigation'].loc[irr_code, 'Ie_m1'],
            'ref' : {
                'desc' : db_dict['Irrigation'].loc[irr_code, 'nameOrigin'], 
                'ID' : str(irr_code),
                'DOI': zenodo
                }
            }
        
    elif surface == 'Deciduous Tree':
        # veg_yaml_dict['waterdist'] = { # TODO Neds to be set somehow
        #     'to_paved': {'value' : 0.1},
        #     'to_bldgs': {'value' : 0.0},
        #     'to_dectr': {'value' : 0.0},
        #     'to_evetr': {'value' : 0.0},
        #     'to_grass': {'value' : 0.0},
        #     'to_bsoil': {'value' : 0.0},
        #     'to_water': {'value' : 0.0},
        #     'to_soilstore': {'value' : 0.9},
        #     'to_runoff' : {'value' : 0}
        # }
        temp_veg['faidectree']['value'] = IMPveg_fai
        temp_veg['dectreeh']['value'] = IMPveg_heights_mean
        temp_veg['ie_a'] = {
            'value' : db_dict['Irrigation'].loc[irr_code, 'Ie_a2'],
            'ref' : {
                'desc' : db_dict['Irrigation'].loc[irr_code, 'nameOrigin'], 
                'ID' : str(irr_code),
                'DOI': zenodo
                }
            }
        temp_veg['ie_m'] =  {
            'value' : db_dict['Irrigation'].loc[irr_code, 'Ie_m2'],
            'ref' : {
                'desc' : db_dict['Irrigation'].loc[irr_code, 'nameOrigin'], 
                'ID' : str(irr_code),
                'DOI': zenodo
                } 
            }

        # porosity_code = veg_dict[surface]['Code']['value']

        temp_veg['pormin_dec'] = {
            'value': veg_dict[surface]['PorosityMin']['value'],
            'ref' : veg_dict[surface]['PorosityMin']['ref']
        } 
        temp_veg['pormax_dec'] = {
            'value': veg_dict[surface]['PorosityMax']['value'],
            'ref' : veg_dict[surface]['PorosityMax']['ref']
        }

 
    elif surface == 'Grass':
        temp_veg['ie_a'] = {
            'value' : db_dict['Irrigation'].loc[irr_code, 'Ie_a3'],
            'ref' : {
                'desc' : db_dict['Irrigation'].loc[irr_code, 'nameOrigin'], 
                'ID' : str(irr_code),
                'DOI': zenodo
                } 
            }
        temp_veg['ie_m'] =  {
            'value' : db_dict['Irrigation'].loc[irr_code, 'Ie_m3'],
            'ref' : {
                'desc' : db_dict['Irrigation'].loc[irr_code, 'nameOrigin'], 
                'ID' : str(irr_code),
                'DOI': zenodo
                } 
            }
        # temp_veg['waterdist'] = { # TODO Neds to be set somehow
        #     'to_paved': {'value' : 0.0},
        #     'to_bldgs': {'value' : 0.0},
        #     'to_dectr': {'value' : 0.0},
        #     'to_evetr': {'value' : 0.0},
        #     'to_grass': {'value' : 0.0},
        #     'to_bsoil': {'value' : 0.0},
        #     'to_water': {'value' : 0.0},
        #     'to_soilstore': {'value' : 1},
        #     'to_runoff' : {'value' : 0.0}
        # }
    # Add on BiogenCO2 & Soil params
    temp_veg = temp_veg | fill_BiogenCO2_yaml(veg_dict[surface], db_dict, zenodo) 
    temp_veg = temp_veg | fill_soil_yaml(db_dict, veg_dict[surface], 'Veg', zenodo)

    temp_veg['ref'] = veg_dict[surface]['ref']

    return temp_veg

def fill_nonveg_yaml(nonveg_dict,surface, db_dict, LCF, irrFr, IMP_fai, IMP_heights_mean, zenodo, temp_nonveg):
    
    temp_nonveg['sfr']['value'] = round(LCF,3)
    temp_nonveg['emis'] = nonveg_dict[surface]['Emissivity']
    temp_nonveg['alb'] = nonveg_dict[surface]['AlbedoMax']
    temp_nonveg['irrfrac']['value'] = irrFr
        # 'ohm_threshsw': {
        #     'value': 10., # TODO This param is static at the moment. Needs to be set somehow.,
        #     'ref' : {
        #         'desc' : 'Example values from Ward, H. C.; Kotthaus, S.; Järvi, L.; Grimmond, C. S. B.(2016)',
        #         'DOI' : db_dict['References'].loc[90240002, 'DOI']
        #     }
        # },

        # 'ohm_threshwd': {
        #     'value':0.9, # TODO This param is static at the moment. Needs to be set somehow.,
        #     'ref' : {
        #         'desc' : 'Example values from Ward, H. C.; Kotthaus, S.; Järvi, L.; Grimmond, C. S. B.(2016)',
        #         'DOI' : db_dict['References'].loc[90240002, 'DOI']
        #     }
        # },

    temp_nonveg['ohm_coef'] = nonveg_dict[surface]['ohm_coef']

    temp_nonveg['storedrainprm'] = {
            'store_min': nonveg_dict[surface]['StorageMin'],
            'store_max': nonveg_dict[surface]['StorageMax'],
            'store_cap': nonveg_dict[surface]['StorageMax'], #TODO THIS IS probably wrong this is current storage according to manual
            'drain_eq':  nonveg_dict[surface]['DrainageEq'],
            'drain_coef_1': nonveg_dict[surface]['DrainageCoef1'],
            'drain_coef_2': nonveg_dict[surface]['DrainageCoef2'],
        }

    #     'snowpacklimit': {
    #         'value' : 190,
    #         'ref' : {
    #             'desc' : 'Example Values from Järvi et al., (2014)',
    #             'DOI' : 'https://suews.readthedocs.io/en/latest/input_files/SUEWS_SiteInfo/Input_Options.html#cmdoption-arg-SnowLimPatch : SnowLimPatch'  #TODO At the moment Hardcoded needs to be set somehow
    #             }
    #        },

    #     'thermal_layers': {
    #         'dz': {'value': [0.1, 0.2, 0.3, 0.4, 0.5]},
    #         'k': {'value': [1.0, 1.0, 1.0, 1.0, 1.0]},
    #         'cp': {'value': [1000, 1000, 1000, 1000, 1000]}
    #     },
    # }   

    if surface == 'Buildings':
        temp_nonveg['faibldg']['value'] =IMP_fai
        temp_nonveg['bldgh']['value'] = IMP_heights_mean
        # temp_nonveg['waterdist'] = { # TODO Neds to be set somehow
        #     'to_paved': {'value' : 0.1},
        #     'to_bldgs': {'value' : 0.0},
        #     'to_dectr': {'value' : 0.0},
        #     'to_evetr': {'value' : 0.0},
        #     'to_grass': {'value' : 0.0},
        #     'to_bsoil': {'value' : 0.0},
        #     'to_water': {'value' : 0.0},
        #     'to_soilstore': {'value' : 0.0},
        #     'to_runoff' : {'value' : 0.9}
        # }
    # else:
        # temp_nonveg['waterdist'] = { # TODO Neds to be set somehow
        #     'to_paved': {'value' : 0.},
        #     'to_bldgs': {'value' : 0.},
        #     'to_dectr': {'value' : 0.},
        #     'to_evetr': {'value' : 0.},
        #     'to_grass': {'value' : 0.02},
        #     'to_bsoil': {'value' : 0.},
        #     'to_water': {'value' : 0.},
        #     'to_soilstore': {'value' : 0.},
        #     'to_runoff' : {'value' : 0.98}
        # }

    temp_nonveg = temp_nonveg | fill_soil_yaml(db_dict, nonveg_dict[surface], 'NonVeg', zenodo)
    
    temp_nonveg['ref'] = nonveg_dict[surface]['ref']

    return temp_nonveg

def fill_AnEm_yaml(db_dict, anem_code, profiles_dict, parameter_dict, start_DLS, end_DLS, TrafficRate_WD, TrafficRate_WE, pop_density_night, pop_density_day, zenodo): 
    AnEm_sel = db_dict['AnthropogenicEmission'].loc[anem_code]

    anthropogenic_emissions =  {
        'startdls': {'value' : start_DLS},
        'enddls': {'value' : end_DLS},
        'heat': {
            'qf0_beu': {
                'working_day': 0.00, # Not set
                'holiday': 0.0, # Not set
                'ref' : {
                    'desc' : 'Not set. Not availible in databse.',
                    'DOI' : 'https://suews.readthedocs.io/en/latest/input_files/SUEWS_SiteInfo/Input_Options.html#cmdoption-arg-QF0_BEU_WD'
                }
            },
            'qf_a': {
                'working_day': AnEm_sel['QF_A_WD'],
                'holiday': AnEm_sel['QF_A_WE']
            },
            'qf_b': {
                'working_day': AnEm_sel['QF_B_WD'],
                'holiday': AnEm_sel['QF_B_WE']
            },
            'qf_c': {
                'working_day': AnEm_sel['QF_C_WD'],
                'holiday': AnEm_sel['QF_C_WE']
            },
            'baset_cooling': {
                'working_day': parameter_dict['TCritic_Cooling_WD'],
                'holiday':parameter_dict['TCritic_Cooling_WE']
            },
            'baset_heating': {
                'working_day': parameter_dict['TCritic_Heating_WD'],
                'holiday': parameter_dict['TCritic_Heating_WE']
            },
            'ah_min': {
                'working_day': AnEm_sel['AHMin_WD'],
                'holiday': AnEm_sel['AHMin_WE']
            },
            'ah_slope_cooling': {
                'working_day': AnEm_sel['AHSlope_Cooling_WD'],
                'holiday': AnEm_sel['AHSlope_Cooling_WE'],
            },
            'ah_slope_heating': {
                'working_day': AnEm_sel['AHSlope_Heating_WD'],
                'holiday': AnEm_sel['AHSlope_Heating_WE'],
            },
            'ahprof_24hr': {
                'working_day': profiles_dict['EnergyUseProfWD'],
                'holiday': profiles_dict['EnergyUseProfWE'],
            },
            'popdensdaytime': {
                'working_day':  float(pop_density_day),
                'holiday':  float(pop_density_day),
            },
            'popdensnighttime': float(pop_density_night),
            'popprof_24hr': {
                'working_day': profiles_dict['PopProfWD'],
                'holiday': profiles_dict['PopProfWE'],
            },
        },
        'ref': { 
        'desc' : AnEm_sel['nameOrigin'],  
        'ID' : str(AnEm_sel.name),   
        'DOI': zenodo,
        },
        'co2' :  {
            'co2pointsource': {'value' : AnEm_sel['CO2PointSource']},
            'ef_umolco2perj': {'value' :AnEm_sel['EF_umolCO2perJ']},
            'enef_v_jkm': {'value' :AnEm_sel['EnEF_v_Jkm']},
            'fcef_v_kgkm': {
                'working_day': AnEm_sel['FcEF_v_kgkmWD'],
                'holiday': AnEm_sel['FcEF_v_kgkmWE']
            },
            'frfossilfuel_heat': {'value' :AnEm_sel['FrFossilFuel_Heat']},
            'frfossilfuel_nonheat': {'value' :AnEm_sel['FrFossilFuel_NonHeat']},
            'maxfcmetab': {'value' :AnEm_sel['MaxFCMetab']},
            'maxqfmetab': {'value' :AnEm_sel['MaxQFMetab']},
            'minfcmetab': {'value' :AnEm_sel['MinFCMetab']},
            'minqfmetab': {'value' :AnEm_sel['MinQFMetab']},
            'trafficrate': {
                'working_day': TrafficRate_WD, 
                'holiday': TrafficRate_WE,
            },
            'trafficunits': {'value' :AnEm_sel['TrafficUnits']},
            'traffprof_24hr': {
                'working_day': profiles_dict['TraffProfWD'],
                'holiday': profiles_dict['TraffProfWE'],
                },
            'humactivity_24hr': {
                'working_day': profiles_dict['ActivityProfWD'],
                'holiday': profiles_dict['ActivityProfWE'],
            },
            'ref' : {
                'desc' : AnEm_sel['nameOrigin'],  
                'ID' :str(AnEm_sel.name),
                'DOI': zenodo
            } 
    }
    }

    return anthropogenic_emissions

def fill_irrigation_yaml(sel_irrigation, profiles_dict, zenodo):

    irrigation =  {
        'h_maintain': {'value' : sel_irrigation['H_maintain']},
        'faut': {'value' : sel_irrigation['Faut']},
        'ie_start': {'value' : sel_irrigation['Ie_start']},
        'ie_end': {'value' : sel_irrigation['Ie_end']},
        'internalwateruse_h': {'value' :  sel_irrigation['InternalWaterUse']},
        'daywatper': {
            'monday': sel_irrigation['DayWatPer(1)'],
            'tuesday': sel_irrigation['DayWatPer(2)'],
            'wednesday': sel_irrigation['DayWatPer(3)'],
            'thursday': sel_irrigation['DayWatPer(4)'],
            'friday': sel_irrigation['DayWatPer(5)'],
            'saturday': sel_irrigation['DayWatPer(6)'],
            'sunday': sel_irrigation['DayWatPer(7)'],
        },
        'daywat': {
            'monday': sel_irrigation['DayWat(1)'],
            'tuesday': sel_irrigation['DayWat(2)'],
            'wednesday': sel_irrigation['DayWat(3)'],
            'thursday': sel_irrigation['DayWat(4)'],
            'friday': sel_irrigation['DayWat(5)'],
            'saturday': sel_irrigation['DayWat(6)'],
            'sunday': sel_irrigation['DayWat(7)'],
        },
        # Automatic
        'wuprofa_24hr': {
            'working_day': profiles_dict['WaterUseProfAutoWD'],
            'holiday': profiles_dict['WaterUseProfAutoWD']
        },
        # Manual
        'wuprofm_24hr': {
            'working_day': profiles_dict['WaterUseProfManuWE'],
            'holiday': profiles_dict['WaterUseProfManuWE']
        },
        'ref' : {
            'desc' : sel_irrigation['nameOrigin'],  
            'ID' : str(sel_irrigation.name),
            'DOI': zenodo
        }
    }

    return irrigation

# def fill_vertical_layers_yaml(ss_dict, db_dict, nonveg_dict, zenodo):

#     a=1

#     # spartacus_material = db_dict['Spartacus Material']
#     # spartacus_surface = db_dict['Spartacus Surface']

#     # vertical_layers = {
#     #     'nlayer': {'value': ss_dict['nlayer']},
#     #     'height': {'value': ss_dict['height']},
#     #     'veg_frac': {'value': ss_dict['veg_frac']},
#     #     'veg_scale': {'value': ss_dict['veg_scale']},
#     #     'building_frac': {'value': ss_dict['building_frac']},
#     #     'building_scale': {'value': ss_dict['building_scale']},
#     #     'roofs' : {},
#     #     'walls' : {}
#     #     }

#     # vertical_layers = {
#     # 'nlayer': {'value': 1},
#     #     'height': {'value': [0.0, 10.0]},
#     #     'veg_frac': {'value': [0.0]},
#     #     'veg_scale': {'value': [1.0]},
#     #     'building_frac': {'value': [0.4]},
#     #     'building_scale': {'value': [1.0]},
#     #     'roofs': [
#     #         {
#     #             'alb': {'value': 0.1},
#     #             'emis': {'value': 0.95},
#     #             'thermal_layers': {
#     #                 'dz': {'value': [0.1, 0.2, 0.3, 0.4, 0.5]},
#     #                 'k': {'value': [1.0, 1.0, 1.0, 1.0, 1.0]},
#     #                 'cp': {'value': [1000, 1000, 1000, 1000, 1000]}
#     #             },
#     #             'statelimit': {'value': 10.0},
#     #             'soilstorecap': {'value': 150.0},
#     #             'wetthresh': {'value': 0.5},
#     #             'roof_albedo_dir_mult_fact':{'value':  0.1},
#     #             'wall_specular_frac':{'value':  0.1}
#     #         }  
#     #     ],
#     #     'walls': [
#     #         {
#     #             'alb': {'value': 0.1},
#     #             'emis': {'value': 0.95},
#     #             'thermal_layers': {
#     #                 'dz': {'value': [0.1, 0.2, 0.3, 0.4, 0.5]},
#     #                 'k': {'value': [1.0, 1.0, 1.0, 1.0, 1.0]},
#     #                 'cp': {'value': [1000, 1000, 1000, 1000, 1000]}
#     #             },
#     #             'statelimit': {'value': 10.0},
#     #             'soilstorecap': {'value': 150.0},
#     #             'wetthresh': {'value': 0.5},
#     #             'roof_albedo_dir_mult_fact':{'value':  0.1},
#     #             'wall_specular_frac':{'value':  0.1}
#     #         } 
#     #     ]
#     # },

#     # for surface in ['roof', 'wall']:
        
#     #     ss_list = []
#     #     for vlayer in range(1, ss_dict['nlayer']+ 1):

#     #         layer = {
#     #                 'alb': {
#     #                     'value' : ss_dict[f'alb_{surface}'][0]
#     #                 },
#     #                 'emis': {
#     #                     'value' : ss_dict[f'emis_{surface}'][0]
#     #                 },
#     #                 'thermal_layers': {
#     #                     'dz': {'value' : ss_dict[f'dz_{surface}({vlayer},:)']},
#     #                     'k': {'value' : ss_dict[f'k_{surface}({vlayer},:)']},
#     #                     'cp': {'value' : ss_dict[f'cp_{surface}({vlayer},:)']}
#     #                 },
#     #                 'statelimit': {'value' : ss_dict[f'statelimit_{surface}'][0]},
#     #                 'soilstorecap': {'value' : ss_dict[f'statelimit_{surface}'][0]},
#     #                 'wetthresh': {'value' : ss_dict[f'statelimit_{surface}'][0]},
#     #                 'roof_albedo_dir_mult_fact': {'value' : ss_dict['roof_albedo_dir_mult_fact'][0]},
#     #                 'wall_specular_frac': {'value' : ss_dict['wall_specular_frac'][0]}
#     #             }

#     #         try:
#     #             spartacus_code = nonveg_dict['Code']['value']['Spartacus Surface']
#     #             layer['alb']['ref'] = {
#     #                 'desc': spartacus_material.loc[spartacus_surface.loc[spartacus_code, f'{surface[0]}1Material'], 'nameOrigin'],
#     #                 'ID' : str(spartacus_surface.loc[spartacus_code, f'{surface[0]}1Material']),
#     #                 'DOI': zenodo
#     #                 }
                
#     #             layer['emis']['ref'] = {
#     #                 'desc': spartacus_material.loc[spartacus_surface.loc[spartacus_code, f'{surface[0]}1Material'], 'nameOrigin'],
#     #                 'ID' : str(spartacus_surface.loc[spartacus_code, f'{surface[0]}1Material']),
#     #                 'DOI': zenodo
#     #             }

#     #         except:
#     #             layer['alb']['ref'] = update_desc_with_materials(nonveg_dict['Spartacus'], db_dict,  f'{surface[0]}1Material')
#     #             layer['emis']['ref'] = update_desc_with_materials(nonveg_dict['Spartacus'], db_dict,  f'{surface[0]}1Material')

#     #         ss_list.append(layer)

#     #     vertical_layers[surface+'s'] = ss_list


#     # try:
#     #     vertical_layers['ref'] = {
#     #         'desc': spartacus_surface.loc[spartacus_code, 'nameOrigin'],
#     #         'ID' : str(spartacus_code),
#     #         'DOI' : zenodo 
#     #     }
#     # except:
#     #     vertical_layers['ref'] = update_desc_with_surface(nonveg_dict['Spartacus'], db_dict)


# # If Spartacus values is not to be calculated in suews-prepare, these standard settings are used. 
# fill_vertical_layers_yaml_no_spartacus = {
#     'nlayer': {'value': 1},
#         'height': {'value': [0.0, 10.0]},
#         'veg_frac': {'value': [0.0]},
#         'veg_scale': {'value': [1.0]},
#         'building_frac': {'value': [0.4]},
#         'building_scale': {'value': [1.0]},
#         'roofs': [
#             {
#                 'alb': {'value': 0.1},
#                 'emis': {'value': 0.95},
#                 'thermal_layers': {
#                     'dz': {'value': [0.1, 0.2, 0.3, 0.4, 0.5]},
#                     'k': {'value': [1.0, 1.0, 1.0, 1.0, 1.0]},
#                     'C': {'value': [1000, 1000, 1000, 1000, 1000]}
#                 },
#                 'statelimit': {'value': 10.0},
#                 'soilstorecap': {'value': 150.0},
#                 'wetthresh': {'value': 0.5},
#                 'roof_albedo_dir_mult_fact':{'value':  0.1},
#                 'wall_specular_frac':{'value':  0.1}
#             }  
#         ],
#         'walls': [
#             {
#                 'alb': {'value': 0.1},
#                 'emis': {'value': 0.95},
#                 'thermal_layers': {
#                     'dz': {'value': [0.1, 0.2, 0.3, 0.4, 0.5]},
#                     'k': {'value': [1.0, 1.0, 1.0, 1.0, 1.0]},
#                     'C': {'value': [1000, 1000, 1000, 1000, 1000]}
#                 },
#                 'statelimit': {'value': 10.0},
#                 'soilstorecap': {'value': 150.0},
#                 'wetthresh': {'value': 0.5},
#                 'roof_albedo_dir_mult_fact':{'value':  0.1},
#                 'wall_specular_frac':{'value':  0.1}
#             } 
#         ]
#     },

# Code Scheme
code_id_dict = {
    'Region': 10,
    'Country': 11,
    'Types': 12, 

    'NonVeg': 20,
    'Soil': 22,
    'Snow': 23,
    'Veg': 24,
    'Water': 25,

    'Biogen': 30,
    'Leaf Area Index': 31,
    'Leaf Growth Power': 32,
    'MVC': 33,
    'Porosity': 34,
    'Vegetation Growth': 35,
    
    'Emissivity': 40,
    'Albedo': 41,   
    'Water State': 42,
    'Storage': 43,
    'Conductance': 44,
    'Drainage': 45,

    'OHM': 50,
    'ANOHM': 51,
    'ESTM': 52,
    'AnthropogenicEmission': 53,
    
    'Profiles': 60,
    'Irrigation': 61,
    
    'Ref': 90,
}

surf_df_dict = {
    'Paved' : 'NonVeg',
    'Buildings' : 'NonVeg',
    'Evergreen Tree' : 'Veg',
    'Deciduous Tree' : 'Veg',
    'Grass' : 'Veg',
    'Bare Soil' : 'NonVeg',
    'Water' : 'Water',
    'IrrigationCode' : 'Irrigation',       #test to fix fill in of irrigation 
    'AnthropogenicCode' : 'AnthropogenicEmission',
    'TraffProfWD' : 'Profiles',   
    'TraffProfWE' : 'Profiles',
    'ActivityProfWD' : 'Profiles',
    'ActivityProfWE' : 'Profiles',
    'WaterUseProfManuWD' : 'Profiles',
    'WaterUseProfManuWE' : 'Profiles',
    'WaterUseProfAutoWD' : 'Profiles',
    'WaterUseProfAutoWE' : 'Profiles',
    'SnowClearingProfWD' : 'Profiles',
    'SnowClearingProfWE' : 'Profiles',
    'PopProfWD' : 'Profiles',
    'PopProfWE' : 'Profiles',
    'EnergyUseProfWD' : 'Profiles',
    'EnergyUseProfWE' : 'Profiles'
}

# This dict sets parameters for initial conditions depending on what sesason selected in suews-prepare
leaf_cycle_dict = {
    1: {  # Winter
        'gdd_1_0': 0,
        'gdd_2_0': -450,
        'laiinitialevetr': 4,
        'laiinitialdectr': 1,
        'laiinitialgrass': 1.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.3,
        'porosity0': 0.2
    },
    2: {
        'gdd_1_0': 50,
        'gdd_2_0': -400,
        'laiinitialevetr': 4.2,
        'laiinitialdectr': 2.0,
        'laiinitialgrass': 2.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.4,
        'porosity0': 0.3
    },
    3: {
        'gdd_1_0': 150,
        'gdd_2_0': -300,
        'laiinitialevetr': 4.6,
        'laiinitialdectr': 3.0,
        'laiinitialgrass': 3.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.6,
        'porosity0': 0.5
    },
    4: {
        'gdd_1_0': 225,
        'gdd_2_0': -150,
        'laiinitialevetr': 4.9,
        'laiinitialdectr': 4.5,
        'laiinitialgrass': 4.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.8,
        'porosity0': 0.6
    },
    5: {  # Summer
        'gdd_1_0': 300,
        'gdd_2_0': 0,
        'laiinitialevetr': 5.1,
        'laiinitialdectr': 5.5,
        'laiinitialgrass': 5.9,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.8,
        'porosity0': 0.6
    },
    6: {
        'gdd_1_0': 225,
        'gdd_2_0': -150,
        'laiinitialevetr': 4.9,
        'laiinitialdectr': 4.5,
        'laiinitialgrass': 4.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.8,
        'porosity0': 0.5
    },
    7: {
        'gdd_1_0': 150,
        'gdd_2_0': -300,
        'laiinitialevetr': 4.6,
        'laiinitialdectr': 3.0,
        'laiinitialgrass': 3.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.5,
        'porosity0': 0.4
    },
    8: {  # Late Autumn
        'gdd_1_0': 50,
        'gdd_2_0': -400,
        'laiinitialevetr': 4.2,
        'laiinitialdectr': 2.0,
        'laiinitialgrass': 2.6,
        'albEveTr0': 0.10,
        'albDecTr0': 0.12,
        'albGrass0': 0.18,
        'decidCap0': 0.4,
        'porosity0': 0.2
    }
}


def fill_SUEWS_NonVeg_typologies(db_dict, parameter_dict, locator_code, zenodo, surface):
        
        '''
        Function for retrieving correct parameters from DB according to typology. 
        This works for Paved, Buildings, and Bare Soil.
        code is the typology code. 
        When adding new parameters, just create new lines and slice DB using similar as of now.
        '''
        
        # Determine the locator based on whether a surface is provided
        locator = db_dict['NonVeg'].loc[locator_code]

        # Define the keys and their corresponding database columns
        keys = {
            'AlbedoMax': ('Albedo', 'Alb_max', 'nameOrigin'),
            'Emissivity': ('Emissivity', 'Emissivity', 'nameOrigin'),
            'StorageMin': ('Water Storage', 'StorageMin', 'nameOrigin'),
            'StorageMax': ('Water Storage', 'StorageMax', 'nameOrigin'),
            'WetThreshold': ('Drainage', 'WetThreshold', 'nameOrigin'),
            'DrainageEq': ('Drainage', 'DrainageEq', 'nameOrigin'),
            'DrainageCoef1': ('Drainage', 'DrainageCoef1', 'nameOrigin'),
            'DrainageCoef2': ('Drainage', 'DrainageCoef2', 'nameOrigin'),
        }

        # Initialize the table dictionary with the typology code
        table_dict = {'Code': {'value': locator}}# 'ref':{'desc': 'N/A', 'ID': 'N/A', 'DOI': zenodo}}}

        # Populate the table dictionary with values from the database
        for key, (db_key, value_col, desc_col) in keys.items():
            table_dict[key] = {
                'value': db_dict[db_key].loc[locator[db_key], value_col],
                'ref' : {
                    'desc': db_dict[db_key].loc[locator[db_key], desc_col] if desc_col else f'{key} value',
                    'ID': str(db_dict[db_key].loc[locator[db_key]].name),
                    'DOI' : zenodo
                    }
            }

        # Add the SoilTypeCode entry
        table_dict['SoilTypeCode'] = {
            'value': parameter_dict['SoilTypeCode'],
            'ref': {
                'desc': db_dict['Soil'].loc[parameter_dict['SoilTypeCode'], 'nameOrigin'],
                'ID': str(parameter_dict['SoilTypeCode']),
                'DOI' : zenodo
                },
        }

        table_dict['Spartacus Surface'] = {
            'value' : locator['Spartacus Surface'],
            'ref' : {
                'desc' : db_dict['Spartacus Surface'].loc[locator['Spartacus Surface'], 'nameOrigin'],
                'ID' : locator['Spartacus Surface'],
                'DOI' : zenodo
            }
        }

        # Add the ohm_coef dictionary to the table dictionary
        table_dict['ohm_coef'] = fill_ohm_coefs(db_dict, locator, zenodo)

        table_dict['ref'] = {
            'desc' : db_dict['NonVeg'].loc[locator.name, 'nameOrigin'],
            'ID' : str(parameter_dict[surface]),
            'DOI': zenodo
        }

        return table_dict

def blend_SUEWS_NonVeg(grid_dict, db_dict, parameter_dict, zenodo, surface):
    '''
    Function for aggregating Building typologies when more than one typology exists in the same grid.
    The function needs typology_IDs and fractions to conduct weighted averages using np.average().
    ''' 

    # Initialize dictionaries to store values and fractions
    values_dict = {}
    fractions = []

    # List of typologies in the grid
    typology_list = list(grid_dict.keys())
    temp_nonveg_dict = {}

    # Populate temp_nonveg_dict with typology data and fractions
    for typology in typology_list:
        locator = db_dict['Types'].loc[typology, surface]
        temp_nonveg_dict[typology] = fill_SUEWS_NonVeg_typologies(db_dict, parameter_dict, locator, zenodo, surface)
        fractions.append(grid_dict[typology]['SAreaFrac'])
        temp_nonveg_dict[typology]['Code']['value'] = typology
        temp_nonveg_dict[typology]['Code']['desc'] = db_dict['Types'].loc[typology, 'nameOrigin']

    # Determine the dominant typology based on the highest fraction
    dominant_typology = typology_list[fractions.index(max(fractions))]
    
    # List of parameters to aggregate
    param_list = [
        'AlbedoMax', 'Emissivity', 'StorageMin', 'StorageMax', 'WetThreshold', 'DrainageEq',
        'DrainageCoef1', 'DrainageCoef2', 'SoilTypeCode', 'ohm_coef']

    # Populate values_dict with parameter values for each typology
    for param in param_list:
        values_dict[param] = [temp_nonveg_dict[typology][param] for typology in typology_list]

    def aggregate_values(param):
    # For non-averageable parameters, return the value from the dominant typology
        if param in ['DrainageEq', 'DrainageCoef1', 'DrainageCoef2', 'SoilTypeCode', 'ohm_coef']:
            return temp_nonveg_dict[dominant_typology][param]
        else:
            # Calculate the weighted average for averageable parameters
            weighted_values = average([v['value'] for v in values_dict[param]], weights=fractions)
            desc_dict = defaultdict(float)
            id_set = set()
            for v, frac in zip(values_dict[param], fractions):
                desc_dict[v['ref']['desc']] += frac * 100
                id_set.add(str(v['ref']['ID']))
            desc_items = [f"{perc:.1f}% {desc}" for desc, perc in desc_dict.items()]
            if len(desc_items) == 1:
                desc = desc_items[0].split(' ', 1)[1]
            else:
                desc = 'aggregated ' + ' '.join(desc_items)
            ids = ', '.join(id_set)
            
        return {'value': round(weighted_values, 3), 'ref':{'desc': desc, 'ID': ids, 'DOI': zenodo}}

    # Create the new aggregated typology dictionary
    new_edit = {
        'Code': 'Aggregated',  # Assuming create_code('NonVeg') generates a new code
        'AlbedoMax': aggregate_values('AlbedoMax'),
        'Emissivity': aggregate_values('Emissivity'),
        'StorageMin': aggregate_values('StorageMin'),
        'StorageMax': aggregate_values('StorageMax'),
        'WetThreshold': aggregate_values('WetThreshold'),
        'DrainageEq': aggregate_values('DrainageEq'),
        'DrainageCoef1': aggregate_values('DrainageCoef1'),
        'DrainageCoef2': aggregate_values('DrainageCoef2'),
        'SoilTypeCode': aggregate_values('SoilTypeCode'),
        'ohm_coef': aggregate_values('ohm_coef'),
        'Spartacus': {
            'desc': [frac * 100 for frac in fractions],
            'ID': [db_dict['NonVeg'].loc[db_dict['Types'].loc[typology, 'Buildings'], 'Spartacus Surface'] for typology in typology_list],
            'DOI': zenodo
        },
        'ref': {
            'desc': 'Aggregated from: ' + ', '.join([f"{frac*100:.1f}% {temp_nonveg_dict[typology]['Code']['desc']}" for typology, frac in zip(typology_list, fractions)]),
            'ID': ', '.join([str(temp_nonveg_dict[typology]['Code']['value']) for typology in typology_list]), #', '.join([str(temp_nonveg_dict[typology]['Code']['value']) for typology in typology_list]),
            'DOI': zenodo
        }
    }
    return new_edit



def fill_SUEWS_Veg(db_dict, settings_dict, parameter_dict, zenodo):
    '''
    This function is used to assign correct params to selected Veg codes 
    Fills for all surfaces (grass, evergreen trees, deciduous trees)
    '''
    # Define the keys and their corresponding database columns
    keys = {
        'AlbedoMin': ('Albedo', 'Alb_min', 'nameOrigin'),
        'AlbedoMax': ('Albedo', 'Alb_max', 'nameOrigin'),
        'Emissivity': ('Emissivity', 'Emissivity', 'nameOrigin'),
        'StorageMin': ('Water Storage', 'StorageMin', 'nameOrigin'),
        'StorageMax': ('Water Storage', 'StorageMax', 'nameOrigin'),
        'WetThreshold': ('Drainage', 'WetThreshold', 'nameOrigin'),
        'DrainageEq': ('Drainage', 'DrainageEq', 'nameOrigin'),
        'DrainageCoef1': ('Drainage', 'DrainageCoef1', 'nameOrigin'),
        'DrainageCoef2': ('Drainage', 'DrainageCoef2', 'nameOrigin'),
        'BaseT': ('Vegetation Growth', 'BaseT', 'nameOrigin'),
        'BaseTe': ('Vegetation Growth', 'BaseTe', 'nameOrigin'),
        # 'GDDFull': ('Vegetation Growth', 'GDDFull', 'nameOrigin'),
        # 'SDDFull': ('Vegetation Growth', 'SDDFull', 'nameOrigin'),
        # 'LAIMin': ('Leaf Area Index', 'LAIMin', 'nameOrigin'),
        # 'LAIMax': ('Leaf Area Index', 'LAIMax', 'nameOrigin'),
        'PorosityMin': ('Porosity', 'PorosityMin', 'nameOrigin'),
        'PorosityMax': ('Porosity', 'PorosityMax', 'nameOrigin'),
        'MaxConductance': ('Max Vegetation Conductance', 'MaxConductance', 'nameOrigin'),
        # 'LAIEq': ('Leaf Area Index', 'LAIEq', 'nameOrigin'),
        # 'LeafGrowthPower1': ('Leaf Growth Power', 'LeafGrowthPower1', 'nameOrigin'),
        # 'LeafGrowthPower2': ('Leaf Growth Power', 'LeafGrowthPower2', 'nameOrigin'),
        # 'LeafOffPower1': ('Leaf Growth Power', 'LeafOffPower1', 'nameOrigin'),
        # 'LeafOffPower2': ('Leaf Growth Power', 'LeafOffPower2', 'nameOrigin'),
    }
    
    table_dict = {}
    for surface in ['Evergreen Tree', 'Deciduous Tree', 'Grass']:
        surf_code = settings_dict[surface]
        locator = db_dict['Veg'].loc[surf_code]
        
        # Initialize the table dictionary with the typology code
        #'Code': {'value': locator['Code']}}#{'value': 'NA', 'ref':{'desc': 'Typology code', 'ID': 'N/A', 'DOI': zenodo}}}
        table_dict[surface] = {'Code': {'value': locator.name}}
        # Populate the table dictionary with values from the database
        for key, (db_key, value_col, desc_col) in keys.items():
            table_dict[surface][key] = {
                'value': db_dict[db_key].loc[locator[db_key], value_col],
                'ref' : {
                    'desc': db_dict[db_key].loc[locator[db_key], desc_col] if desc_col else f'{key} value',
                    'ID': str(db_dict[db_key].loc[locator[db_key]].name),
                    'DOI' : zenodo
                    }
            }

        # Add additional parameters not in the keys dictionary
        table_dict[surface]['SoilTypeCode'] = {
            'value': parameter_dict['SoilTypeCode'],
            'desc': db_dict['Soil'].loc[parameter_dict['SoilTypeCode'], 'nameOrigin'],
        }

        bioco2Code = db_dict['Veg'].loc[table_dict[surface]['Code']['value'], 'Biogen CO2']
        table_dict[surface]['BiogenCO2Code'] = {
            'value': bioco2Code,
            'desc': db_dict['Biogen CO2'].loc[bioco2Code, 'nameOrigin'],
        }

        # Add the ohm_coef dictionary to the table dictionary
        table_dict[surface]['ohm_coef'] = fill_ohm_coefs(db_dict, locator, zenodo)

        table_dict[surface]['ref'] = {
            'desc': db_dict['Veg'].loc[locator.name, 'nameOrigin'],
            'ID': str(locator.name),
            'DOI': zenodo
        }

    return table_dict


def fill_SUEWS_Water(surface_code, db_dict, parameter_dict, zenodo):
    '''
    This function is used to assign correct params to selected Water code.
    Locator is the water code.
    '''
    
    # Define the keys and their corresponding database columns
    keys = {
        'AlbedoMin': ('Albedo', 'Alb_min', 'nameOrigin'),
        'AlbedoMax': ('Albedo', 'Alb_max', 'nameOrigin'),
        'Emissivity': ('Emissivity', 'Emissivity', 'nameOrigin'),
        'StorageMin': ('Water Storage', 'StorageMin', 'nameOrigin'),
        'StorageMax': ('Water Storage', 'StorageMax', 'nameOrigin'),
        'WetThreshold': ('Drainage', 'WetThreshold', 'nameOrigin'),
        'StateLimit': ('Water State', 'StateLimit', 'nameOrigin'),
        'WaterDepth': ('Water State', 'WaterDepth', 'nameOrigin'),
        'DrainageEq': ('Drainage', 'DrainageEq', 'nameOrigin'),
        'DrainageCoef1': ('Drainage', 'DrainageCoef1', 'nameOrigin'),
        'DrainageCoef2': ('Drainage', 'DrainageCoef2', 'nameOrigin')
    }

    locator = db_dict['Water'].loc[surface_code]

    # Initialize the table dictionary with the typology code
    table_dict = {}#'Code': {'value': locator.name, 'ref':{'desc': 'N/A', 'ID': 'N/A', 'DOI': zenodo}}}

    # Populate the table dictionary with values from the database
    for key, (db_key, value_col, desc_col) in keys.items():
        table_dict[key] = {
            'value': db_dict[db_key].loc[locator[db_key], value_col],
            'ref' : {
                'desc': db_dict[db_key].loc[locator[db_key], desc_col] if desc_col else f'{key} value',
                'ID': str(db_dict[db_key].loc[locator[db_key]].name),
                'DOI' : zenodo
                }
        }

    # Add the SoilTypeCode entry
    table_dict['SoilTypeCode'] = {
        'value': parameter_dict['SoilTypeCode'],
        'desc': db_dict['Soil'].loc[parameter_dict['SoilTypeCode'], 'nameOrigin'],
    }

    # Add the ohm_coef dictionary to the table dictionary
    table_dict['ohm_coef'] = fill_ohm_coefs(db_dict, locator, zenodo)

    table_dict['ref'] = {
        'desc': locator['nameOrigin'],
        'ID': str(locator.name),
        'DOI': zenodo
    }

    return table_dict


def fill_SUEWS_Snow(surface_code, db_dict, zenodo):
    '''
    This function is used to assign correct params to selected Snow code.
    Locator is the snow code.
    '''

    # Define the keys and their corresponding database columns
    keys = {
        'RadMeltFactor': ('Snow', 'RadMeltFactor', 'nameOrigin'),
        'TempMeltFactor': ('Snow', 'TempMeltFactor', 'nameOrigin'),
        'AlbedoMin': ('Albedo', 'Alb_min', 'nameOrigin'),
        'AlbedoMax': ('Albedo', 'Alb_max', 'nameOrigin'),
        'Emissivity': ('Emissivity', 'Emissivity', 'nameOrigin'),
        'tau_a': ('Snow', 'tau_a', 'nameOrigin'),
        'tau_f': ('Snow', 'tau_f', 'nameOrigin'),
        'PrecipLimAlb': ('Snow', 'PrecipLimAlb', 'nameOrigin'),
        'SnowDensMin': ('Snow', 'SnowDensMin', 'nameOrigin'),
        'SnowDensMax': ('Snow', 'SnowDensMax', 'nameOrigin'),
        'tau_r': ('Snow', 'tau_r', 'nameOrigin'),
        'CRWMin': ('Snow', 'CRWMin', 'nameOrigin'),
        'CRWMax': ('Snow', 'CRWMax', 'nameOrigin'),
        'PrecipLimSnow': ('Snow', 'PrecipLimSnow', 'nameOrigin')
    }

    locator = db_dict['Snow'].loc[surface_code]
    # Initialize the table dictionary with the typology code
    table_dict = {}#'Code': {'value': locator.name, 'ref':{'desc': 'N/A', 'ID': 'N/A', 'DOI': zenodo}}}

    # Populate the table dictionary with values from the database
    for key, (db_key, value_col, desc_col) in keys.items():
        try:
            table_dict[key] = {
                'value': db_dict[db_key].loc[locator[db_key], value_col],
                'ref' : {
                    'desc': db_dict[db_key].loc[locator[db_key], desc_col] if desc_col else f'{key} value',
                    'ID': str(db_dict[db_key].loc[locator[db_key]].name),
                    'DOI' : zenodo
                    }
        }
        except:
            table_dict[key] = {
                'value': locator[value_col],
                'ref' : {
                    'desc': locator['nameOrigin'],
                    'ID': str(locator.name),
                    'DOI' : zenodo
                    }
        }

    # Add the ohm_coef dictionary to the table dictionary
    table_dict['ohm_coef'] = fill_ohm_coefs(db_dict, locator, zenodo)

    table_dict['ref'] = {
        'desc': locator['nameOrigin'],
        'ID': str(locator.name),
        'DOI': zenodo
    }

    return table_dict

def update_desc_with_materials(data_dict, db_dict, variable):

    merge_string = 'Aggregated from: '

    for ID, percent in zip(data_dict['ID'], data_dict['desc']):
        material = db_dict['Spartacus Surface'].loc[ID, variable]
        
        mat = db_dict['Spartacus Material'].loc[material, 'nameOrigin']

        merge_string = merge_string + str(round(percent, 1)) + '% ' + mat + ', '

    new_edit = data_dict.copy()
    new_edit['desc'] = merge_string
    new_edit['ID'] = str(data_dict['ID'])
    
    return new_edit

def update_desc_with_surface(data_dict, db_dict):

    merge_string = 'Aggregated from: '

    for ID, percent in zip(data_dict['ID'], data_dict['desc']):
        surface = db_dict['Spartacus Surface'].loc[ID, 'nameOrigin']
        
        # mat = db_dict['Spartacus Material'].loc[material, 'nameOrigin']

        merge_string = merge_string + str(round(percent, 1)) + '% ' + surface + ', '

    new_edit = data_dict.copy()
    new_edit['desc'] = merge_string
    new_edit['ID'] = str(data_dict['ID'])
    
    return new_edit

def fill_ohm_coefs(db_dict, locator, zenodo):

# Define the seasons and corresponding database columns for OHM coefficients
    seasons = ['summer_wet', 'summer_dry', 'winter_wet', 'winter_dry']
    db_seasons = ['OHMSummerWet', 'OHMSummerDry', 'OHMWinterWet', 'OHMWinterDry']
    coefficients = ['a1', 'a2', 'a3']

    # Initialize the ohm_coef dictionary
    ohm_coef = {}

    # Populate the ohm_coef dictionary using loops
    for season, db_season in zip(seasons, db_seasons):
        ohm_sel = db_dict['OHM'].loc[locator[db_season]]
        ohm_coef[season] = {}
        for coef in coefficients:
            ohm_coef[season][coef] = {
                'value': ohm_sel[coef],
            }

        ohm_coef[season]['ref'] = {
            'desc': ohm_sel['nameOrigin'],
            'ID': str(ohm_sel.name),
            'DOI': zenodo
                }
        
    return ohm_coef

# Not used. To big TimeZones.shp file
# def get_utc(grid_path, timezone):
    
#     # timezone
#     grid = gread_file(grid_path)
    
#     # Set of grid to crs of timezones vectorlayer (WGS 84)
#     grid_crs = grid.to_crs(timezone.crs)

#     try:
#         spatial_join = gsjoin(left_df=grid_crs,
#                                     right_df=timezone,
#                                     how='inner', op='within')
#         utc = spatial_join.iloc[0]['zone']
#     except:
#         utc = 0
#         print('UTC calc not working')
#     return utc

