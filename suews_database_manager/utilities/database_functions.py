from pandas import ExcelFile, read_excel, ExcelWriter
from numpy import nonzero, isnan, nan, vectorize, int32
from time import sleep
from datetime import datetime


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
            db[col]['nameOrigin'] = db[col]['Name'].astype(str) + '; ' + db[col]['Color'].astype(str) + '; ' + db[col]['Origin'].astype(str)    
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
                for prefix in ['w', 'r']:
                    if prefix == 'w':
                        pr = 'wall'
                    elif prefix == 'r':
                        pr == 'roof'
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
    
    # # add 
    # for col in sheets:
    #     if col == 'Name':
    #         db[col]['nameOrigin'] = db[col]['Name'].astype(str) + ', ' + db[col]['Origin'].astype(str)
    #     elif col == 'References': 
    #         db[col]['authorYear'] = db[col]['Author'].astype(str) + ', ' + db[col]['Year'].astype(str)
    #     elif col == 'Country':
    #         db[col]['nameOrigin'] = db[col]['Country'].astype(str) + ', ' + db[col]['City'].astype(str)  
    #     elif col == 'Region':
    #         pass
    #     elif col == 'Spartacus Material':
    #         db[col]['nameOrigin'] = db[col]['Name'].astype(str) + '; ' + db[col]['Color'].astype(str) + '; ' + db[col]['Origin'].astype(str)    
    #     # Calculate U-values for roof and wall new columns u_value_wall and u_value_roof
    #     elif col == 'Profiles':
    #         # Normalise traffic and energy use profiles to ensure that mean == 1
    #         normalisation_rows = db[col][(db[col]['Profile Type'] == 'Traffic') | (db[col]['Profile Type'] == 'Energy use')]
    #         cols = list(range(24))
    #         normalisation_rows_index = list(normalisation_rows.index)

    #         # # # Calculate the sum of the values for each row
    #         sums = db[col].loc[normalisation_rows_index, cols].sum(axis=1)

    #         # Avoid division by zero by replacing zero sums with NaN
    #         sums.replace(0, np.nan, inplace=True)

    #         # # Calculate the scaling factor to make the sum equal to the number of columns (24)
    #         scaling_factors = 24 / sums

    #         # Scale the values
    #         db[col].loc[normalisation_rows_index, cols] = db[col].loc[normalisation_rows_index, cols].multiply(scaling_factors, axis=0)

    #         db[col]['nameOrigin'] = db[col]['Name'].astype(str)  +  ', ' + db[col]['Day'].astype(str) +  ', ' + db[col]['Country'].astype(str) + ', ' + db[col]['City'].astype(str) 

    #     elif col == 'Spartacus Surface':
    #         db[col]['nameOrigin'] = db[col]['Name'].astype(str) + ', ' + db[col]['Origin'].astype(str)
    #     # Filter rows where Surface is 'Buildings'
    #         buildings = db['Spartacus Surface'][db['Spartacus Surface']['Surface'] == 'Buildings']

    #         # Calculate resistances and U-values
    #         for prefix in ['w', 'r']:
    #             materials = buildings[[f'{prefix}{i}Material' for i in range(1, 4)]].values
    #             thicknesses = buildings[[f'{prefix}{i}Thickness' for i in range(1, 4)]].values

    #             thermal_conductivities = np.vectorize(lambda x: db['Spartacus Material'].loc[x, 'Thermal Conductivity'])(materials)
    #             resistances = thicknesses / thermal_conductivities
    #             resistance_bulk = resistances.sum(axis=1)

    #             u_values = 1 / resistance_bulk
    #             db['Spartacus Surface'].loc[buildings.index, f'u_value_{prefix}all'] = u_values

    #         # Calculate albedo and emissivity
    #         for prop in ['Albedo', 'Emissivity']:
    #             for prefix in ['w', 'r']:
    #                 material_col = f'{prefix}1Material'
    #                 db['Spartacus Surface'].loc[buildings.index, f'{prop.lower()}_{prefix}all'] = db['Spartacus Material'].loc[buildings[material_col], prop].values
    #     else:
    #         print(col)
    #         db[col]['nameOrigin'] = db[col]['Name'].astype(str) + ', ' + db[col]['Origin'].astype(str)

    db_sh.close() # trying this to close excelfile

    return db

def save_to_db(db_path, db_dict):
    # Drop columns in a 
    for col in db_dict.keys():
        if col == 'References':
            db_dict[col] = db_dict[col].drop(columns='authorYear', errors='ignore')
        elif col not in ['Country', 'Region']:
            db_dict[col] = db_dict[col].drop(columns='nameOrigin', errors='ignore')

    # Save to Excel
    with ExcelWriter(db_path) as writer:
        for sheet_name, df in db_dict.items():
            df.to_excel(writer, sheet_name=sheet_name)

    # Add 'nameOrigin' and 'authorYear' columns back
    if 'References' in db_dict:
        db_dict['References']['authorYear'] = db_dict['References']['Author'].astype(str) + ', ' + db_dict['References']['Year'].astype(str)
    if 'Profiles' in db_dict:
        db_dict['Profiles']['nameOrigin'] = db_dict['Profiles']['Name'].astype(str)  +  ', ' + db_dict['Profiles']['Day'].astype(str) +  ', ' + db_dict['Profiles']['Country'].astype(str) + ', ' + db_dict['Profiles']['City'].astype(str) 
    for col in db_dict.keys():
        if col not in ['Profiles', 'References', 'Country', 'Region']:
            db_dict[col]['nameOrigin'] = db_dict[col]['Name'].astype(str) + ', ' + db_dict[col]['Origin'].astype(str)

# def save_to_db(db_path, db_dict):
#     for col in list(db_dict.keys()):
#         if col == 'References':
#             db_dict[col] = db_dict[col].drop(columns = 'authorYear')
#         elif col == 'Country' or col == 'Region':
#             pass
#         else:
#             try:
#                 db_dict[col] = db_dict[col].drop(columns = 'nameOrigin')
#             except:
#                 print('ERROR IN SAVE TO DB IN: ' + col)

#     with pd.ExcelWriter(db_path) as writer: 
#         db_dict['Region'].to_excel(writer, sheet_name='Region')
#         db_dict['Country'].to_excel(writer, sheet_name='Country')
#         db_dict['Types'].to_excel(writer, sheet_name='Name')
#         db_dict['Veg'].to_excel(writer, sheet_name='Veg')
#         db_dict['NonVeg'].to_excel(writer, sheet_name='NonVeg')
#         db_dict['Water'].to_excel(writer, sheet_name='Water')
#         db_dict['Emissivity'].to_excel(writer, sheet_name='Emissivity')
#         db_dict['Vegetation Growth'].to_excel(writer, sheet_name='Vegetation Growth')
#         db_dict['Water State'].to_excel(writer, sheet_name='Water State')
#         db_dict['OHM'].to_excel(writer, sheet_name='OHM')
#         db_dict['Albedo'].to_excel(writer, sheet_name='Albedo')
#         db_dict['ANOHM'].to_excel(writer, sheet_name='ANOHM')
#         db_dict['Biogen CO2'].to_excel(writer, sheet_name='Biogen CO2')
#         db_dict['Leaf Area Index'].to_excel(writer, sheet_name='Leaf Area Index')
#         db_dict['Water Storage'].to_excel(writer, sheet_name='Water Storage')
#         db_dict['Conductance'].to_excel(writer, sheet_name='Conductance')
#         db_dict['Leaf Growth Power'].to_excel(writer, sheet_name='Leaf Growth Power')
#         db_dict['Drainage'].to_excel(writer, sheet_name='Drainage')
#         db_dict['Max Vegetation Conductance'].to_excel(writer, sheet_name='Max Vegetation Conductance')
#         db_dict['Porosity'].to_excel(writer, sheet_name='Porosity')
#         db_dict['ESTM'].to_excel(writer, sheet_name='ESTM')
#         db_dict['Profiles'].to_excel(writer, sheet_name='Profiles')
#         db_dict['Irrigation'].to_excel(writer, sheet_name='Irrigation')
#         db_dict['Soil'].to_excel(writer, sheet_name='Soil')
#         db_dict['Snow'].to_excel(writer, sheet_name='Snow')
#         db_dict['AnthropogenicEmission'].to_excel(writer, sheet_name='AnthropogenicEmission')
#         db_dict['Spartacus Surface'].to_excel(writer, sheet_name = 'Spartacus Surface')
#         db_dict['Spartacus Material'].to_excel(writer, sheet_name = 'Spartacus Material')
#         db_dict['References'].to_excel(writer, sheet_name='References')

#     for col in list(db_dict.keys()):
#         if col == 'Name':
#             db_dict[col]['nameOrigin'] = db_dict[col]['Type'].astype(str) + ', ' + db_dict[col]['Origin'].astype(str)
#         elif col == 'References': 
#             db_dict[col]['authorYear'] = db_dict[col]['Author'].astype(str) + ', ' + db_dict[col]['Year'].astype(str)
#         elif col == 'Country' or col == 'Region':
#             pass
#         else:
#             db_dict[col]['nameOrigin'] = db_dict[col]['Name'].astype(str) + ', ' + db_dict[col]['Origin'].astype(str)


def update_db(db_dict, db_path, updated_db_path, backup_path):
    
    db_dict_update = read_DB(updated_db_path)   # This dict is the database that is to be updated from 
    updated_db_dict = db_dict | db_dict_update  # Merge the two dicts   

    save_to_db(updated_db_dict, db_path)        # Save to db
    save_to_db(db_dict, backup_path)            # Save to db

    return updated_db_dict




surf_df_dict = {
    'Paved' : 'NonVeg',
    'Buildings' : 'NonVeg',
    'Evergreen Tree' : 'Veg',
    'Deciduous Tree' : 'Veg',
    'Grass' : 'Veg',
    'Bare Soil' : 'NonVeg',
    'Water' : 'Water',           
}

code_id_dict = {
    'Region': 10,
    'Country': 11,
    'Name': 12, 

    'NonVeg': 20,
    'Soil': 22,
    'Snow': 23,
    'Veg': 24,
    'Water': 25,

    'Biogen': 30,
    'Leaf Area Index': 31,
    'Leaf Growth Power': 32,
    'Max Vegetation Conductance': 33,
    'Porosity': 34,
    'Vegetation Growth': 35,
    'Spartacus Material' : 36,
    'Spartacus Surface': 37,
    'SnowLimPatch' : 38,
    
    'Emissivity': 40,
    'Albedo': 41,   
    'Water State': 42,
    'Water Storage': 43,
    'Conductance': 44,
    'Drainage': 45,

    'OHM': 50,
    'ANOHM': 51,
    'ESTM': 52,
    'AnthropogenicEmission': 53,
    
    'Profiles': 60,
    'Irrigation': 61,
    
    'Reference': 90,
}


def get_combobox_items(combobox):
    items = [combobox.itemText(i) for i in range(combobox.count())]  # Get all items
    items = [item.split(': ', 1)[1] for item in items]
    return items


def ref_changed(dlg, db_dict):
    dlg.textBrowserRef.clear()
    try:
        ID = db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item()
        dlg.textBrowserRef.setText(
            '<b>Author: ' +'</b>' + str(db_dict['References'].loc[ID, 'Author']) + '<br><br><b>' +
            'Year: ' + '</b> '+ str(db_dict['References'].loc[ID, 'Year']) + '<br><br><b>' +
            'Title: ' + '</b> ' +  str(db_dict['References'].loc[ID, 'Title']) + '<br><br><b>' +
            'Journal: ' + '</b>' + str(db_dict['References'].loc[ID, 'Journal']) + '<br><br><b>' +
            'DOI: ' + '</b>' + str(db_dict['References'].loc[ID, 'DOI']) + '<br><br><b>' 
        )
    except:
            pass

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


param_info_dict = {
    'Albedo': {
        'description': 'Effective bulk surface albedo (middle of the day value) for summertime.',
        'surface': ['Paved','Buildings','Deciduous Tree',  'Evergreen Tree','Grass', 'Bare Soil','Water', 'Snow'],
        'param': {
            'Alb_min': {
                'min': 0,
                'max': 1,
                'tooltip': 'Effective surface albedo (middle of the day value) for wintertime (not including snow).'},
            'Alb_max': {
                'min': 0,
                'max': 1,
                'tooltip': 'Effective surface albedo (middle of the day value) for summertime.'}
                }
            },
    # 'ANOHM': {'surface': ['Paved','Buildings','Deciduous Tree', 'Evergreen Tree','Grass','Bare Soil','Water','Snow'],
    #         'param': {'AnOHM_Cp': {'min': 0,
    #             'max': 1,
    #             'tooltip': 'Volumetric heat capacity for this surface to use in AnOHM [J |m^-3|]'},
    #         'AnOHM_Kk': {'min': 0,
    #             'max': 1,
    #             'tooltip': 'Thermal conductivity for this surface to use in AnOHM [W m |K^-1|]'},
    #         'AnOHM_Ch': {'min': 0,
    #             'max': 1,
    #             'tooltip': 'Bulk transfer coefficient for this surface to use in AnOHM [-]'}}},

    'Biogen CO2': {
        'surface': ['Deciduous Tree', 'Evergreen Tree', 'Grass'],
        'param': {'alpha': {'min': 0,
            'max': 1,
            'tooltip': 'The mean apparent ecosystem quantum. Represents the initial slope of the light-response curve. [umol CO2 umol photons^-1]'},
        'beta': {'min': 0, 'max': 1,
            'tooltip': 'The light-saturated gross photosynthesis of the canopy. [umol m-2 s-1 ]'},
        'theta': {'min': 0, 'max': 1,
        'tooltip': 'The convexity of the curve at light saturation.'},
        'alpha_enh': {'min': 0, 'max': 1,
        'tooltip': 'Part of the alpha coefficient related to the fraction of vegetation.'},
        'beta_enh': {'min': 0, 'max': 1, 'tooltip':'Part of the beta coefficient related to the fraction of vegetation.'},
        'resp_a': {'min': 0, 'max': 1, 'tooltip': 'Respiration coefficient a.'},
        'resp_b': {'min': 0, 'max': 1, 'tooltip': 'Respiration coefficient b - related to air temperature dependency.'},
        'min_respi': {'min': 0, 'max': 1, 'tooltip':'Minimum soil respiration rate (for cold-temperature limit) [umol m-2 s-1].'}
            }
        },
    'Conductance': {
        'surface': ['Paved','Buildings','Deciduous Tree','Evergreen Tree','Grass','Bare Soil'],
        'param': {
            'G1': {'min': 0,
            'max': 1,
            'tooltip': 'Related to maximum surface conductance [mm |s^-1|]'},
        'G2': {'min': 0,
            'max': 1,
            'tooltip': 'Related to Kdown dependence [W |m^-2|]'},
        'G3': {'min': 0,
            'max': 1,
            'tooltip': 'Related to VPD dependence [units depend on `gsModel`]'},
        'G4': {'min': 0,
            'max': 1,
            'tooltip': 'Related to VPD dependence [units depend on `gsModel`]'},
        'G5': {'min': 0,
            'max': 1,
            'tooltip': 'Related to temperature dependence [°C]'},
        'G6': {'min': 0,
            'max': 1,
            'tooltip': 'Related to soil moisture dependence [|mm^-1|]'},
        'TH': {'min': 0, 'max': 1, 'tooltip': 'Upper air temperature limit [°C]'},
        'TL': {'min': 0, 'max': 1, 'tooltip': 'Lower air temperature limit [°C]'},
        'S1': {'min': 0,
            'max': 1,
            'tooltip': 'A parameter related to soil moisture dependence [-]'},
        'S2': {'min': 0,
            'max': 1,
            'tooltip': 'A parameter related to soil moisture dependence [mm]'},
        'Kmax': {'min': 0,
            'max': 1,
            'tooltip': 'Maximum incoming shortwave radiation [W |m^-2|]'},
        'gsModel': {'min': 0,
            'max': 1,
            'tooltip': 'Formulation choice for conductance calculation.'}
            }
        },
    'Drainage': {
        'Description': 'Drainage settings for surface',
        'surface': ['Paved','Buildings','Deciduous Tree','Evergreen Tree','Grass','Bare Soil'],
    'param': {
        'DrainageCoef1': {'min': 0,
        'max': 1,
        'tooltip': 'Coefficient D0 [mm |h^-1|] used in :option:`DrainageEq`'},
    'DrainageCoef2': {
        'min': 0,
        'max': 1,
        'tooltip': 'Coefficient b [-] used in :option:`DrainageEq`'},
    'DrainageEq': {
        'min': 0,
        'max': 1,
        'tooltip': 'Calculation choice for Drainage equation'},
    'WetThreshold': {
        'min': 0, 
        'max': 1, 
        'tooltip': 'Depth of water which determines whether evaporation occurs from a partially wet or completely wet surface [mm].'}
        }
    },
    'Emissivity': {
        'description': 'Effective bulk surface emissivity.',
        'surface':  ['Paved','Buildings','Deciduous Tree','Evergreen Tree','Grass','Bare Soil'],
        'param': {'Emissivity': {'min': 0,
            'max': 1,
            'tooltip': 'Effective surface emissivity.'}
                 }
             },
    'Leaf Area Index': {
        'surface': ['Deciduous Tree', 'Evergreen Tree', 'Grass'],
        'param': {'LAIEq': {'min': 0,
            'max': 1,
            'tooltip': 'LAI calculation choice. [0,1]'},
        'LAIMin': {'min': 0, 'max': 1, 'tooltip': 'leaf-off wintertime value'},
        'LAIMax': {'min': 0,
            'max': 1,
            'tooltip': 'full leaf-on summertime value'}}},

    'Leaf Growth Power': {
        'surface': ['Deciduous Tree', 'Evergreen Tree', 'Grass'],
        'param': {'LeafGrowthPower1': {'min': 0,
            'max': 1,
            'tooltip': 'a parameter required by LAI calculation in `LAIEq`'},
        'LeafGrowthPower2': {'min': 0,
            'max': 1,
            'tooltip': 'a parameter required by LAI calculation [|K^-1|] in `LAIEq`'},
        'LeafOffPower1': {'min': 0,
            'max': 1,
            'tooltip': 'a parameter required by LAI calculation [|K^-1|] in `LAIEq`'},
        'LeafOffPower2': {'min': 0,
            'max': 1,
            'tooltip': 'a parameter required by LAI calculation [|K^-1|] in `LAIEq`'},
        'LAIEq': {'min': 0,
            'max': 1,
            'tooltip': 'LAI calculation choice. [0,1]'},
            },
    }, 
    'Max Vegetation Conductance': {
        'surface': ['Deciduous Tree','Evergreen Tree','Grass'],
        'param': {'MaxConductance': {'min': 0, 'max': 1, 'tooltip' : 'The maximum conductance of each vegetation or surface type. [mm s-1]'}}},
    'Porosity': {
        'surface': ['Deciduous Tree'],
        'param': {'PorosityMin': {'min': 0, 'max': 1, 'tooltip': 'leaf-off wintertime value Used only for DecTr (can affect roughness calculation)'},
        'PorosityMax': {'min': 0, 'max': 1, 'tooltip' : 'full leaf-on summertime value Used only for DecTr (can affect roughness calculation)'}}},
    'Vegetation Growth': {
        'surface': ['Deciduous Tree', 'Evergreen Tree', 'Grass'],
        'param': {
            'BaseT': {'min': 0, 'max': 1, 'tooltip':'Base Temperature for initiating growing degree days (GDD) for leaf growth. [°C]'},
            'BaseTe': {'min': 0, 'max': 1, 'tooltip': 'Base temperature for initiating sensesance degree days (SDD) for leaf off. [°C]'},
            'GDDFull': {'min': 0, 'max': 1, 'tooltip': 'The growing degree days (GDD) needed for full capacity of the leaf area index (LAI) [°C].'},
            'SDDFull': {'min': 0, 'max': 1, 'tooltip': 'The sensesence degree days (SDD) needed to initiate leaf off. [°C]'}}},
    'Water State': {
        'Description' : 'Minimum and maximum water storage capacity for upper surfaces (i.e. canopy).',
        'surface': ['Water'],
        'param': {
            'StateLimit': {'min': 0, 'max': 1, 'tooltip':'Upper limit to the surface state. [mm]. Currently only used for the water surface. Set to a large value (e.g. 20000 mm = 20 m) if the water body is substantial (lake, river, etc) or a small value (e.g. 10 mm) if water bodies are very shallow (e.g. fountains). WaterDepth (column 9) must not exceed this value.'},
            'WaterDepth': {'min': 0, 'max': 1, 'tooltip': 'Water depth [mm].'}}},
    'Water Storage': {
        'surface': ['Paved',
        'Buildings',
        'Deciduous Tree',
        'Evergreen Tree',
        'Grass',
        'Bare Soil',
        'Water'],
        'param': {
            'StorageMin': {'min': 0,'max': 1, 'tooltip': 'Minimum water storage capacity for upper surfaces (i.e. canopy).'},
            'StorageMax': {'min': 0,
                'max': 1,
                'tooltip': 'Maximum water storage capacity for upper surfaces (i.e. canopy)'}}},
    'Soil': {
        'surface': ['No Surface'],
        'param': {
            'SoilDepth': {'min': 0, 'max': 1, 'tooltip': 'Soil density [kg m-3]'},
            'SoilStoreCap': {'min': 0, 'max': 1, 'tooltip': 'Limit value for SoilDepth [mm]'},
            'SatHydraulicCond': {'min': 0, 'max': 1, 'tooltip' : 'Hydraulic conductivity for saturated soil [mm s-1]'},
            'SoilDensity': {'min': 0, 'max': 1, 'tooltip' : 'Soil density [kg m-3]'},
            'InfiltrationRate': {'min': 0, 'max': 1, 'tooltip': 'Infiltration rate (Not currently used)'},
            'OBS_SMCap' : {'min':0,'max':1, 'tooltip': 'The maximum observed soil moisture. [m3 m-3 or kg kg-1]'},
            'OBS_SMDepth': {'min': 0, 'max': 1, 'tooltip':'The depth of soil moisture measurements. [mm]'},
            'OBS_SoilNotRocks': {'min': 0, 'max': 1, 'tooltip':'Fraction of soil without rocks. [-]'}}},

    'OHM': {
        'surface' : ['Paved','Buildings','Deciduous Tree',  'Evergreen Tree','Grass', 'Bare Soil','Water', 'Snow'],
        'param'   : {
            'a1': {'tooltip' : 'Coefficient for Q* term [-]'},
            'a2': {'tooltip' : 'Coefficient for dQ*/dt term [h]'},
            'a3': {'tooltip' : 'Constant term [W m-2]'},
        }
    },
    'SnowLimPatch': {
        'surface': ['Paved','Buildings','Deciduous Tree','Evergreen Tree','Grass','Bare Soil'], 
        'param' : {
            'SnowLimPatch' : {'tooltip' : 'Limit for the snow water equivalent when snow cover starts to be patchy [mm]. Not needed if SnowUse = 0 in RunControl.nml'}
        }
    }
}