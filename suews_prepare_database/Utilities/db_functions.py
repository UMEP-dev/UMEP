from pandas import ExcelFile, read_excel, MultiIndex, DataFrame, read_csv,concat
from numpy import nonzero, isnan, nan, vectorize, average, int32, zeros, pad, array
from time import sleep
from datetime import datetime

from scipy.ndimage import maximum_filter


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
        if profile_type not in ['Residential', 'commercial', 'Industry']:
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

def blend_SUEWS_NonVeg(grid_dict, db_dict, parameter_dict, surface):
    '''
    Function for aggregating Building typologies when more than one typology exists in the same grid
    The function needs typology_IDs and fractions to conduct weighted averages using np.average()

    For adding or removing params, do that both in param_list and in new_edit dictionary
    Some parameters are not averageable, or needs to be taken from regional scale, such as SoilTypeCode or OHMThresh_WD
    Drainage Eq and drainagecoefieccents are taken from dominant typology (04/10-23). A checker should be made to check 
    if drainageEQ is the same, then we can aggregate the coefficents, otherwise, just take dominant.

    OHM codes are not averageable. Right now (04/10-23), the dominant is used. This could be solved using a new function
    to aggregate and create new OHM codes. But not done yet.

    '''
    values_dict = {} 
    fractions = []

    typology_list = list(grid_dict.keys())
    temp_nonveg_dict = {}
    for typology in typology_list:
        temp_nonveg_dict[typology] = fill_SUEWS_NonVeg_typologies(typology, db_dict, parameter_dict, surface)
        fractions.append(grid_dict[typology]['SAreaFrac'])

    dominant_typology = typology_list[fractions.index(max(fractions))]
    param_list = [
        'AlbedoMin', 'AlbedoMax', 'Emissivity', 'StorageMin', 'StorageMax', 'WetThreshold', 'StateLimit', 'DrainageEq',
        'DrainageCoef1', 'DrainageCoef2', 'SnowLimPatch', 'SnowLimRemove', 'OHMCode_SummerWet', 'OHMCode_SummerDry',
        'OHMCode_WinterWet', 'OHMCode_WinterDry', 'OHMThresh_SW', 'OHMThresh_WD', 'ESTMCode', 'AnOHM_Cp', 'AnOHM_Kk', 'AnOHM_Ch'
    ]   #TODO Make this list not hardcoded and adaptable for new parameters added

    typology_list
    for param in param_list:
        values_dict[param] = [temp_nonveg_dict[typology][param] for typology in typology_list]
    new_edit = {
            'Code': create_code('NonVeg'),
            'AlbedoMin': average(values_dict['AlbedoMin'], weights=fractions),
            'AlbedoMax': average(values_dict['AlbedoMax'], weights=fractions),
            'Emissivity': average(values_dict['Emissivity'], weights=fractions),
            'StorageMin': average(values_dict['StorageMin'], weights=fractions),
            'StorageMax': average(values_dict['StorageMax'], weights=fractions),
            'WetThreshold': average(values_dict['WetThreshold'], weights=fractions),
            'StateLimit': -999,#average(values_dict['StateLimit'], weights=fractions),
            'DrainageEq': temp_nonveg_dict[dominant_typology]['DrainageEq'],
            'DrainageCoef1': temp_nonveg_dict[dominant_typology]['DrainageCoef1'],
            'DrainageCoef2': temp_nonveg_dict[dominant_typology]['DrainageCoef2'],
            'SoilTypeCode': parameter_dict['SoilTypeCode'],
            'SnowLimPatch': average(values_dict['SnowLimPatch'], weights=fractions),
            'SnowLimRemove': average(values_dict['SnowLimRemove'], weights=fractions),
            'OHMThresh_SW': 10,  # TODO: set regional Country --> parameter_dict['OHMThresh_SW'],
            'OHMThresh_WD': 0.9,  # TODO: set regional Country --> parameter_dict['OHMThresh_WD'],
            'ESTMCode': -999,  # not used
            'AnOHM_Cp': -999,
            'AnOHM_Kk': -999,
            'AnOHM_Ch': -999,
        }

    # This loop is for ohm codes as they are not averagable
    for column in ['OHMCode_SummerWet', 'OHMCode_SummerDry', 'OHMCode_WinterWet', 'OHMCode_WinterDry']:
        if len(set(values_dict[column])) == 1:
            new_edit[column] = values_dict[column][0]
        else:
            new_edit[column] = values_dict[column][0]  # TODO: need to make a new blend OHM function if these are not the same

    return new_edit

def fill_SUEWS_NonVeg_typologies(code, db_dict, parameter_dict, surface = False):
    '''
    Function for retrieving correct parameters from DB according to typology. 
    This works for Paved, Buildings and Bare Soil
    code is the typology code. 
    When adding new parameters, just create new lines and slice DB using similar as of now
    '''
    
    # locator is the code for the for the selected typology
    # if this function is used from the blend_SUEWS_NonVeg function, a surface needs to be provided to get correct codes
    if surface:
        locator = db_dict['NonVeg'].loc[db_dict['Types'].loc[code, surface]]
    else:
        locator = db_dict['NonVeg'].loc[code]

    table_dict = {
        'Code' : locator.name,
        'AlbedoMin' :   db_dict['Albedo'].loc[locator['Albedo'], 'Alb_min'],
        'AlbedoMax' :   db_dict['Albedo'].loc[locator['Albedo'], 'Alb_max'], 
        'Emissivity' : db_dict['Emissivity'].loc[locator['Emissivity'], 'Emissivity'],
        'StorageMin' :  db_dict['Water Storage'].loc[locator['Water Storage'], 'StorageMin'], 
        'StorageMax' : db_dict['Water Storage'].loc[locator['Water Storage'], 'StorageMax'],
        'WetThreshold' : db_dict['Drainage'].loc[locator['Drainage'], 'WetThreshold'], 
        'StateLimit' : -999, # Not used for Non Veg
        'DrainageEq' : db_dict['Drainage'].loc[locator['Drainage'], 'DrainageEq'],
        'DrainageCoef1' : db_dict['Drainage'].loc[locator['Drainage'], 'DrainageCoef1'], 
        'DrainageCoef2' : db_dict['Drainage'].loc[locator['Drainage'], 'DrainageCoef2'], 
        'SoilTypeCode' : parameter_dict['SoilTypeCode'], 
        'SnowLimPatch' : 190, # TODO Set regional
        'SnowLimRemove': 90,    # TODO Set regional
        'OHMCode_SummerWet' :  locator['OHMSummerWet'], 
        'OHMCode_SummerDry' : locator['OHMSummerDry'], 
        'OHMCode_WinterWet' : locator['OHMWinterWet'], 
        'OHMCode_WinterDry' : locator['OHMWinterDry'], 
        'OHMThresh_SW' : 10, # TODO Set regional
        'OHMThresh_WD' : 0.9, # TODO Set regional
        'ESTMCode' : -999, 
        'AnOHM_Cp' : -999,
        'AnOHM_Kk' : -999,
        'AnOHM_Ch' : -999,
        }
    return table_dict

def fill_SUEWS_Water(locator, db_dict, column_dict):
    '''
    This function is used to assign correct params to selected Water code
    Locator is 
    '''
    table_dict = {}
    table_dict['Water'] = {
        'Code' : locator,
        'AlbedoMin' :   db_dict['Albedo'].loc[db_dict['Water'].loc[locator, 'Albedo'], 'Alb_min'],
        'AlbedoMax' :   db_dict['Albedo'].loc[db_dict['Water'].loc[locator, 'Albedo'], 'Alb_max'],
        'Emissivity' : db_dict['Emissivity'].loc[db_dict['Water'].loc[locator, 'Emissivity'], 'Emissivity'],
        'StorageMin' :  db_dict['Water Storage'].loc[db_dict['Water'].loc[locator, 'Water Storage'], 'StorageMin'],
        'StorageMax' : db_dict['Water Storage'].loc[db_dict['Water'].loc[locator, 'Water Storage'], 'StorageMax'],
        'WetThreshold' : db_dict['Drainage'].loc[db_dict['Water'].loc[locator, 'Drainage'], 'WetThreshold'],
        'StateLimit' : db_dict['Water State'].loc[db_dict['Water'].loc[locator, 'Water State'], 'StateLimit'],
        'WaterDepth' : db_dict['Water State'].loc[db_dict['Water'].loc[locator, 'Water State'], 'WaterDepth'],
        'DrainageEq' : db_dict['Drainage'].loc[db_dict['Water'].loc[locator, 'Drainage'], 'DrainageEq'],
        'DrainageCoef1' : db_dict['Drainage'].loc[db_dict['Water'].loc[locator, 'Drainage'], 'DrainageCoef1'],
        'DrainageCoef2' : db_dict['Drainage'].loc[db_dict['Water'].loc[locator, 'Drainage'], 'DrainageCoef2'],
        'SoilTypeCode' : column_dict['SoilTypeCode'], #table.loc[locator, 'SoilTypeCode'],  36),
        'SnowLimPatch' : -999,
        'SnowLimRemove': -999,    
        'OHMCode_SummerWet' : db_dict['Water'].loc[locator, 'OHMSummerWet'],
        'OHMCode_SummerDry' : db_dict['Water'].loc[locator, 'OHMSummerDry'],
        'OHMCode_WinterWet' : db_dict['Water'].loc[locator, 'OHMWinterWet'],
        'OHMCode_WinterDry' : db_dict['Water'].loc[locator, 'OHMWinterDry'],
        'OHMThresh_SW' : 10, # table.loc[locator, 'OHMThresh_SW'],
        'OHMThresh_WD' : 0.9, #table.loc[locator, 'OHMThresh_WD'],
        'ESTMCode' : -999,
        'AnOHM_Cp' : -999,
        'AnOHM_Kk' : -999,
        'AnOHM_Ch' : -999,
    }
    return table_dict

def fill_SUEWS_Veg(db_dict, settings_dict, soilTypeCode):
    '''
    This function is used to assign correct params to selected Veg codes 
    Fills for all surfaces (grass, evergreen trees, deciduous trees)
    '''
    table = db_dict['Veg']
    table_dict = {}
    
    for surface in ['Evergreen Tree', 'Deciduous Tree', 'Grass']:
        table_dict[surface] = {}

        locator = settings_dict[surface]
        table_dict[surface] = {
                'Code' : locator,
                'AlbedoMin' :   db_dict['Albedo'].loc[table.loc[locator, 'Albedo'], 'Alb_min'],
                'AlbedoMax' :   db_dict['Albedo'].loc[table.loc[locator, 'Albedo'], 'Alb_max'],
                'Emissivity' : db_dict['Emissivity'].loc[table.loc[locator, 'Emissivity'], 'Emissivity'],
                'StorageMin' :  db_dict['Water Storage'].loc[table.loc[locator, 'Water Storage'], 'StorageMin'],
                'StorageMax' : db_dict['Water Storage'].loc[table.loc[locator, 'Water Storage'], 'StorageMax'],
                'WetThreshold' : db_dict['Drainage'].loc[table.loc[locator, 'Drainage'], 'WetThreshold'],
                'StateLimit' : -999, #db_dict['Water State'].loc[table.loc[locator, 'Water State'], 'StateLimit'],
                'DrainageEq' : db_dict['Drainage'].loc[table.loc[locator, 'Drainage'], 'DrainageEq'],
                'DrainageCoef1' : db_dict['Drainage'].loc[table.loc[locator, 'Drainage'], 'DrainageCoef1'],
                'DrainageCoef2' : db_dict['Drainage'].loc[table.loc[locator, 'Drainage'], 'DrainageCoef2'],
                'SoilTypeCode' : soilTypeCode, #table.loc[locator, 'SoilTypeCode'],  36),
                'SnowLimPatch' : 190, # TODO set regional
                'BaseT' :       db_dict['Vegetation Growth'].loc[table.loc[locator, 'Vegetation Growth'], 'BaseT'],
                'BaseTe' :      db_dict['Vegetation Growth'].loc[table.loc[locator, 'Vegetation Growth'], 'BaseTe'],
                'GDDFull' :     db_dict['Vegetation Growth'].loc[table.loc[locator, 'Vegetation Growth'], 'GDDFull'],
                'SDDFull' :     db_dict['Vegetation Growth'].loc[table.loc[locator, 'Vegetation Growth'], 'SDDFull'],
                'LAIMin' :      db_dict['Leaf Area Index'].loc[table.loc[locator, 'Leaf Area Index'], 'LAIMin'],
                'LAIMax' :      db_dict['Leaf Area Index'].loc[table.loc[locator, 'Leaf Area Index'], 'LAIMax'],
                'PorosityMin' : db_dict['Porosity'].loc[table.loc[locator, 'Porosity'], 'PorosityMin'],
                'PorosityMax' : db_dict['Porosity'].loc[table.loc[locator, 'Porosity'], 'PorosityMax'],
                'MaxConductance' : db_dict['Max Vegetation Conductance'].loc[table.loc[locator, 'Max Vegetation Conductance'], 'MaxConductance'],
                'LAIEq' :       db_dict['Leaf Area Index'].loc[table.loc[locator, 'Leaf Area Index'], 'LAIEq'],
                'LeafGrowthPower1' : db_dict['Leaf Growth Power'].loc[table.loc[locator, 'Leaf Growth Power'], 'LeafGrowthPower1'],
                'LeafGrowthPower2' : db_dict['Leaf Growth Power'].loc[table.loc[locator, 'Leaf Growth Power'], 'LeafGrowthPower2'],
                'LeafOffPower1' : db_dict['Leaf Growth Power'].loc[table.loc[locator, 'Leaf Growth Power'], 'LeafOffPower1'],
                'LeafOffPower2' : db_dict['Leaf Growth Power'].loc[table.loc[locator, 'Leaf Growth Power'], 'LeafOffPower2'],    
                'OHMCode_SummerWet' : table.loc[locator, 'OHMSummerWet'],
                'OHMCode_SummerDry' : table.loc[locator, 'OHMSummerDry'],
                'OHMCode_WinterWet' : table.loc[locator, 'OHMWinterWet'],
                'OHMCode_WinterDry' : table.loc[locator, 'OHMWinterDry'],
                'OHMThresh_SW' : 10,#table.loc[locator, 'OHMThresh_SW'],# TODO set regional
                'OHMThresh_WD' : 0.9,#table.loc[locator, 'OHMThresh_WD'],# TODO set regional
                'ESTMCode' : -999,
                'AnOHM_Cp' : -999,
                'AnOHM_Kk' : -999,
                'AnOHM_Ch' : -999,
                'BiogenCO2Code' : table.loc[locator, 'Biogen CO2']
            }
        
    return table_dict

def fill_SUEWS_Snow(locator, db_dict):
    
    '''
    This function is used to assign correct params to selected Snow code
    Locator is selected code
    '''

    table_dict = {
        'Code' : locator,
        'RadMeltFactor' : db_dict['Snow'].loc[locator, 'RadMeltFactor'], 
        'TempMeltFactor': db_dict['Snow'].loc[locator, 'TempMeltFactor'],
        'AlbedoMin' : db_dict['Albedo'].loc[db_dict['Snow'].loc[locator, 'Albedo'], 'Alb_min'],
        'AlbedoMax' : db_dict['Albedo'].loc[db_dict['Snow'].loc[locator, 'Albedo'], 'Alb_max'],
        'Emissivity' : db_dict['Emissivity'].loc[db_dict['Snow'].loc[locator, 'Emissivity'], 'Emissivity'],
        'tau_a' : db_dict['Snow'].loc[locator, 'tau_a'],
        'tau_f' : db_dict['Snow'].loc[locator, 'tau_f'],
        'PrecipLimAlb' : db_dict['Snow'].loc[locator, 'PrecipLimAlb'],
        'SnowDensMin' : db_dict['Snow'].loc[locator, 'SnowDensMin'],
        'SnowDensMax' : db_dict['Snow'].loc[locator, 'SnowDensMax'],
        'tau_r' : db_dict['Snow'].loc[locator, 'tau_r'], 
        'CRWMin' : db_dict['Snow'].loc[locator, 'CRWMin'],
        'CRWMax' : db_dict['Snow'].loc[locator, 'CRWMax'],
        'PrecipLimSnow' : db_dict['Snow'].loc[locator, 'PrecipLimSnow'],
        'OHMCode_SummerWet' : db_dict['Snow'].loc[locator, 'OHMSummerWet'],
        'OHMCode_SummerDry' : db_dict['Snow'].loc[locator, 'OHMSummerDry'],
        'OHMCode_WinterWet' : db_dict['Snow'].loc[locator, 'OHMWinterWet'],
        'OHMCode_WinterDry' : db_dict['Snow'].loc[locator, 'OHMWinterDry'],
        'OHMThresh_SW' : 10,
        'OHMThresh_WD' : 0.9,
        'ESTMCode' : -999,
        'AnOHM_Cp' : -999,
        'AnOHM_Kk' : -999,
        'AnOHM_Ch' : -999,
    }

    return table_dict

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

# Aggregation of OHM Parameters
def new_table_edit(db_dict, table_dict, values, param, name, frac_dict, surface):

    weights_dict = {}
    weights_dict = {k : 0 for k in values['Code'].keys()}

    for i in list(values['Code'].keys()):
        weights_dict[i] ={}
        weights_dict[i]['Code'] = values[param][i]
        weights_dict[i]['Weight'] = + frac_dict[i]

    # Create dicts for fractions to be aggregates
    weight_dict_merged ={}
    weight_dict_merged['Code'] = {}
    for i in weights_dict:
        weight_dict_merged['Code'][weights_dict[i]['Code']] = 0

    for i in weights_dict:
        code = weights_dict[i]['Code'] 
        weight = weights_dict[i]['Weight']
        weight_dict_merged['Code'][code] = weight_dict_merged['Code'][code] + weight

    #params = different ohm codes in db_dict['OHM']

    blend_edit_dict = {}

    # edit_params = (list(edit_dict[type].keys()))
    edit_params = list(values[param].values())

    edit_params = list(values[param].values())

    for edit_code in ['a1', 'a2', 'a3']:
        blend_edit_dict[edit_code] = {}
        for p in edit_params:
            blend_edit_dict[edit_code][p] = db_dict['OHM'].loc[p,edit_code]

    new_code = create_code(name)

    new_edit_dict = {'Code' : new_code}
    weight = list(list(weight_dict_merged['Code'].values()))


    for i in ['a1', 'a2', 'a3']:
        try:
            new_edit_dict[i] = average(list(blend_edit_dict[i].values()), weights = weight)
        except:
            new_edit_dict[i] = -999.

    table_dict[surface][param]  = new_edit_dict['Code']
    new_edit_dict['Code'] = new_code

    dict_df = DataFrame(new_edit_dict, index = [0]).set_index('Code')

    dict_df = dict_df.rename_axis('ID')
    db_dict[name] = concat([db_dict[name], dict_df])

    return db_dict

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


def fill_SUEWS_profiles(settings_dict ,save_folder, prof):
    '''
    This function is used to assign correct profiles
    Locator is selected code
    This function also saves the profiles to .txt
    '''

    # profiles_list = []
    # for keys in profiles_dict.keys():
    #     profiles_list.append(profiles_dict[keys]['profileCode'])

    profiles_list = ['TraffProfWE','TraffProfWD', 'EnergyUseProfWD','EnergyUseProfWE','ActivityProfWD','ActivityProfWE','PopProfWD','PopProfWE', 'SnowClearingProfWD', 'SnowClearingProfWE','WaterUseProfManuWD','WaterUseProfManuWE','WaterUseProfAutoWD','WaterUseProfAutoWE']        


    df_m = DataFrame()

    for profile in profiles_list:
        locator = settings_dict[profile]
        table_dict = {
            'Code' : locator,
            '0'  : prof.loc[locator, 0],
            '1'  : prof.loc[locator, 1],
            '2'  : prof.loc[locator, 2],
            '3'  : prof.loc[locator, 3],
            '4'  : prof.loc[locator, 4],
            '5'  : prof.loc[locator, 5],
            '6'  : prof.loc[locator, 6],
            '7'  : prof.loc[locator, 7],
            '8'  : prof.loc[locator, 8],
            '9'  : prof.loc[locator, 9],
            '10' : prof.loc[locator, 10],
            '11' : prof.loc[locator, 11],
            '12' : prof.loc[locator, 12],
            '13' : prof.loc[locator, 13],
            '14' : prof.loc[locator, 14],
            '15' : prof.loc[locator, 15],
            '16' : prof.loc[locator, 16],
            '17' : prof.loc[locator, 17],
            '18' : prof.loc[locator, 18],
            '19' : prof.loc[locator, 19],
            '20' : prof.loc[locator, 20],
            '21' : prof.loc[locator, 21],
            '22' : prof.loc[locator, 22],
            '23' : prof.loc[locator, 23],
        }

        dict_df = DataFrame(table_dict, index = [0])
        df_m = concat([df_m, dict_df]).drop_duplicates(keep='first')

    df_m.columns = [df_m.columns, list(range(1, len(df_m.columns)+1))]

    # add -9 rows to text files
    df_m = df_m.swaplevel(0,1,1)
    df_m.loc[-1] = nan
    df_m.iloc[-1, 0] = -9
    df_m.loc[-2]= nan
    df_m.iloc[-1, 0] = -9

    df_m.to_csv(save_folder + 'SUEWS_Profiles.txt', sep = '\t' ,index = False)

def save_SUEWS_txt(df_m, table_name, save_folder, db_dict):
    '''
    This function is used to prepare the data and saving into correct way for the .txt files used in SUEWS
    # TODO Add comment column in the end and specify where the specific code is used
    '''
    col = ['Surface', 'Name', 'Origin', 'Ref', 'Season', 'Day' ,'Profile Type', 'nameOrigin']
    dropFilter = df_m.filter(col)
    df_m.drop(dropFilter, inplace= True, axis = 1)
    df_m.reset_index(inplace = True)
    df_m = df_m.round(4)
    df_m = df_m.fillna(-999)

    if table_name == 'SUEWS_AnthropogenicEmission.txt':
        cd = list(df_m.filter(like='Code').columns)
        cd = cd + list(df_m.filter(like= 'WD'))
        cd = cd + list(df_m.filter(like= 'WE'))

    else:
        cd = df_m.filter(like='Code').columns

    try:
        df_m['Code'] = df_m['Code'].apply(lambda x: x)
    except:
        pass

    # These two columns are made for adding information on what the code is inside the .txt file
    df_m['!'] = '!'
    df_m[''] = ''
    table_name_short = table_name[6:-4] # table_name_short is used to set correct table in DB. all table names are such as "SUEWS_table.txt, and DB only wants table"

    if table_name == 'SUEWS_OHMCoefficients.txt':
        table_name_short = 'OHM'
    elif table_name == 'SUEWS_BiogenCO2.txt':
        table_name_short = 'Biogen CO2'

    df_m = df_m.set_index('Code')
    for idx in list(df_m.index):
        
        if table_name == 'SUEWS_Veg.txt' or table_name == 'SUEWS_NonVeg.txt':
            surface_sel = db_dict[table_name_short].loc[idx,'Surface'] # table_name_short is used to set correct table in DB. all table names are such as "SUEWS_table.txt, and DB only wants table"
            nameOrigin_sel = db_dict[table_name_short].loc[idx,'nameOrigin']
            id_string = surface_sel + ', ' + nameOrigin_sel
        else:
            nameOrigin_sel = db_dict[table_name_short].loc[idx,'nameOrigin']
            id_string =  nameOrigin_sel

        df_m.loc[idx,''] = id_string

    df_m = df_m.reset_index()
    # Add column numbers 1-max columns needed for .txt files
    df_m.columns = [df_m.columns, list(range(1, len(df_m.columns)+1))]

    # add -9 rows to text files
    df_m = df_m.swaplevel(0,1,1)
    # This can probably be done better. Used append() but this will be deprecated. This works, but not the most clean coding
    df_m.loc[-1] = nan
    df_m.iloc[-1, 0] = -9
    df_m.loc[-2]= nan
    df_m.iloc[-1, 0] = -9

    columns = df_m.columns

    new_columns = list(columns[:-2]) + [('', ''), ('', '')]

    df_m.columns = MultiIndex.from_tuples(new_columns)

    df_m.to_csv(save_folder + table_name, sep = '\t' ,index = False)
    
def save_snow(snow_dict, save_folder, db_dict):
    '''
    This function is used to save to .txt file related to Snow
    '''
    df_m = DataFrame.from_dict(snow_dict, orient = 'index').T

    # These two columns are made for adding information on what the code is inside the .txt file
    df_m['!'] = '!'
    df_m[''] = nan

    idx = df_m['Code'].item()

    nameOrigin_sel = db_dict['Snow'].loc[idx,'nameOrigin']
    df_m[''] = nameOrigin_sel

    column_list = list(range(1, len(df_m.columns)+1))
    df_m.columns = [df_m.columns, column_list]

    df_m = df_m.swaplevel(0,1,1)
    # This can probably be done better. Used append() but this will be deprecated. This works, but not the most clean coding
    df_m.loc[-1] = nan
    df_m.iloc[-1, 0] = -9
    df_m.loc[-2]= nan
    df_m.iloc[-1, 0] = -9

    columns = df_m.columns

    new_columns = list(columns[:-2]) + [('', ''), ('', '')]

    df_m.columns = MultiIndex.from_tuples(new_columns)

    df_m.to_csv(save_folder + 'SUEWS_Snow.txt', sep = '\t' ,index = False)

def save_NonVeg_types(nonveg_dict, save_folder, db_dict):

    '''
    This function is used to save to .txt file related to NonVeg
    '''

    # Initialize an empty list to store rows
    rows = []

    # Iterate over the dictionary to flatten it
    for grid, data in nonveg_dict.items():
        for key, value in data.items():
            row = value.copy()
            row['Grid'] = str(grid)
            row['Surface'] = key
            rows.append(row)

    # Convert the list of rows to a DataFrame
    df = DataFrame(rows)
    df = df.set_index('Code')
    for idx in list(df.index):
        try:
            surface_sel = db_dict['NonVeg'].loc[idx,'Surface'] 
            nameOrigin_sel = db_dict['NonVeg'].loc[idx,'nameOrigin']
            id_string = surface_sel + ', ' + nameOrigin_sel
            df.loc[idx,'Locator'] = id_string
        except:
            pass
            df.loc[idx,'Locator'] = 'aggregated from X(fraction) Y(fracion) Z(fraction)'
    df = df.reset_index()
    columns = list(df.columns)
    # # List of columns to be aggregated
    for remove_col in ['Code', 'Grid']:
        columns.remove(remove_col)

    # Create the aggregation dictionary for groupby
    agg_dict = {col: 'first' for col in columns}
    agg_dict['Grid'] = lambda x: ','.join(sorted(set(x)))
    agg_dict['Surface'] = lambda x: ','.join(sorted(set(x)))
    agg_dict['Locator'] = lambda x: ','.join(sorted(set(x)))

    # Group by 'Code' and aggregate the columns
    df = df.groupby('Code').agg(agg_dict).reset_index()

    df['!'] = '!'
    df['t'] = df['Surface'] + ', ' + df['Locator'] + '. Used in Grid No. ' + df['Grid']
    df = df.rename(columns={'t': ''})
    df = df.drop(columns=['Grid', 'Surface', 'Locator'])

    # Adjust the DataFrame columns using the provided code snippet
    df.columns = [df.columns, list(range(1, len(df.columns)+1))]
    df = df.swaplevel(0, 1, axis=1)

    # Add 2 rows with empty columns except that the 'Code' value is -9
    df.loc[-1] = nan
    df.iloc[-1, 0] = -9
    df.loc[-2] = nan
    df.iloc[-2, 0] = -9

    # Ensure both rows have the 'Code' value as -9
    df.iloc[-1, 0] = -9
    df.iloc[-2, 0] = -9

    # Remove name of columns for ! comment columns
    df.columns = df.columns = MultiIndex.from_tuples([('', '') if col == (25, '!') else ('', '') if col == (26, '') else col for col in df.columns])

    df.to_csv(save_folder + 'SUEWS_NonVeg.txt', sep = '\t' ,index = False)

def save_SiteSelect(ss_dict, save_folder, path_to_ss):
    '''
    This function is used to save to SUEWS_SiteSelect.txt
    '''
    df_m = DataFrame.from_dict(ss_dict).T
    ss_txt = read_csv(path_to_ss, delim_whitespace=True, skiprows=1)
    df_m = df_m.reset_index()
    df_m = df_m.rename(columns={'index' : 'Grid'})
    df_m['Grid'] = df_m['Grid'].apply(str)
    df_m = df_m[ss_txt.columns]
    df_m.columns = [df_m.columns, list(range(1, len(df_m.columns)+1))]
    df_m = df_m.round(4)

    cd = list(df_m.filter(like='Code').columns)
    cd = cd + list(df_m.filter(like= 'WD'))
    cd = cd + list(df_m.filter(like= 'WE'))

    df_m = df_m.swaplevel(0,1,1)
    df_m.loc[-1] = nan
    df_m.iloc[-1, 0] = -9
    df_m.loc[-2]= nan
    df_m.iloc[-1, 0] = -9

    df_m.to_csv(save_folder + 'SUEWS_SiteSelect.txt', sep = '\t' ,index = False)

def presave(table, name ,var_list, save_folder, db_dict):
    '''
    This function is used to prepare some of the data used to be able to save to .txt
    '''
    df = table.loc[var_list]
    df = df.drop(columns=df.select_dtypes(include='object').columns).rename_axis('Code')
    save_SUEWS_txt(df, ('SUEWS_' + name + '.txt'), save_folder, db_dict)


def read_morph_txt(txt_file):
    '''
    This function is used to read output files from morphometric calculator .txt
    '''
    morph_dict = read_csv(txt_file, delim_whitespace=True, index_col=[0]).to_dict(orient='index')
    return morph_dict  



# Not used. To big TimeZones.shp file
# def get_utc(grid_path, timezone):
    
#     # timezone
#     grid = gread_file(grid_path)
    
#     # Set of grid to crs of timezones vectorlayer (WGS 84)
#     grid_crs = grid.to_crs(timezone.crs)

#     try:
#         spatial_join = gsjoin(left_df=grid_crs,
#                                     right_df=timezone,
#                                     how="inner", op='within')
#         utc = spatial_join.iloc[0]['zone']
#     except:
#         utc = 0
#         print('UTC calc not working')
#     return utc

