''' Calculates the sensible, latent, wastewater parts of each source and sector.
Calculations consider the gross and net heat combustion for each fuel used. 
'''
def getQFComponents():
    # List and return the components of anthropogenic heat flux
    # Same order as GreaterQF output array
    # TODO: Hard-link these together using pandas arrays or named lists
    components = {}
    components[0] = "Dm El Unre"
    components[1] = "Dm El Eco7"
    components[2] = "Id El"
    components[3] = "Dm gas"
    components[4] = "Id gas"
    components[5] = "Id Other"
    components[6] = "Sum Dm Bld"
    components[7] = "Sum Id Bld"
    components[8] = "Sum Bld"
    components[9] = "Motorcyc"
    components[10] = "Taxis"
    components[11] = "Cars"
    components[12] = "Buses"
    components[13] = "LGVs"
    components[14] = "HGV Rigid"
    components[15] = "HGV artic"
    components[16] = "Sum tspt"
    components[17] = "Metabolism"
    components[18] = "Everything"
    return components

