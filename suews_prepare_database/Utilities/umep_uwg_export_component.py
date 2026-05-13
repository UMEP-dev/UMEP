# import cPickle
import os

"""
This module is adjusted from dragonfly_uwg_export_component to
transform UMEP pre-processing data to fit uwg

input: 
uwg_object: dictonary with all relevant inputs
refdir = outputfolder
fname = filename       
"""


def create_uwgdict():

    uwgDict = {}

    # Urban characteristics
    uwgDict["bldHeight"] = 10  # average building height (m)
    uwgDict["bldDensity"] = 0.5  # urban area building plan density (0-1)
    uwgDict["verToHor"] = 0.8  # urban area vertical to horizontal ratio
    # fraction of building HVAC waste heat set to the street canyon [as opposed to the roof]
    uwgDict["h_mix"] = 1
    # dimension of a square that encompasses the whole neighborhood [aka. characteristic length] (m)
    uwgDict["charLength"] = 1000
    uwgDict["albRoad"] = 0.1  # road albedo (0 - 1)
    uwgDict["dRoad"] = 0.5  # road pavement thickness (m)
    uwgDict["kRoad"] = 1  # road pavement conductivity (W/m K)
    uwgDict["cRoad"] = 1600000  # road volumetric heat capacity (J/m^3 K)
    # non-building sensible heat at street level [aka. heat from cars, pedestrians, street cooking, etc. ] (W/m^2)
    uwgDict["sensAnth"] = 20

    # Climate Zone (Eg. City)
    uwgDict["zone"] = "1A"

    # Vegetation parameters
    # Fraction of the urban ground covered in grass/shrubs only (0-1)
    uwgDict["grasscover"] = 0.1
    # Fraction of the urban ground covered in trees (0-1)
    uwgDict["treeCover"] = 0.1
    # The month in which vegetation starts to evapotranspire (leaves are out)
    uwgDict["vegStart"] = 4
    # The month in which vegetation stops evapotranspiring (leaves fall)
    uwgDict["vegEnd"] = 10
    uwgDict["albVeg"] = 0.25  # Vegetation albedo
    # Fraction of the heat absorbed by grass that is latent (goes to evaporating water)
    uwgDict["latGrss"] = 0.4
    # Fraction of the heat absorbed by trees that is latent (goes to evaporating water)
    uwgDict["latTree"] = 0.6
    # Fraction of the rural ground covered by vegetation
    uwgDict["rurVegCover"] = 0.9

    # Traffic schedule [1 to 24 hour],# Weekday# Saturday# Sunday
    uwgDict["SchTraffic"] = [
        [
            0.2,
            0.2,
            0.2,
            0.2,
            0.2,
            0.4,
            0.7,
            0.9,
            0.9,
            0.6,
            0.6,
            0.6,
            0.6,
            0.6,
            0.7,
            0.8,
            0.9,
            0.9,
            0.8,
            0.8,
            0.7,
            0.3,
            0.2,
            0.2,
        ],
        [
            0.2,
            0.2,
            0.2,
            0.2,
            0.2,
            0.3,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.6,
            0.7,
            0.7,
            0.7,
            0.7,
            0.5,
            0.4,
            0.3,
            0.2,
            0.2,
        ],
        [
            0.2,
            0.2,
            0.2,
            0.2,
            0.2,
            0.3,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.4,
            0.3,
            0.3,
            0.2,
            0.2,
        ],
    ]

    # Fraction of building stock for each DOE Building type (pre-80's build, 80's-present build, new)
    # Note that sum(bld) must be equal to 1

    # Choose from the following built eras:
    # 'Pre80'
    # 'Pst80'
    # 'New'

    uwgDict["bld"] = [
        [
            "FullServiceRestaurant",
            "Hospital",
            "LargeHotel",
            "LargeOffice",
            "MedOffice",
            "MidRiseApartment",
            "OutPatient",
            "PrimarySchool",
            "QuickServiceRestaurant",
            "SecondarySchool",
            "SmallHotel",
            "SmallOffice",
            "StandAloneRetail",
            "StripMall",
            "SuperMarket",
            "Warehouse",
        ],
        [
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
            "Pst80",
        ],
        [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ],
    ]

    # =================================================
    # OPTIONAL URBAN PARAMETERS
    # =================================================
    # If not provided, optional parameters are taken from corresponding DOE Reference building
    uwgDict["albRoof"] = None  # roof albedo (0 - 1)
    # Fraction of the roofs covered in grass/shrubs (0 - 1)
    uwgDict["vegRoof"] = None
    uwgDict["glzR"] = None  # Glazing Ratio (0 - 1)
    uwgDict["SHGC"] = None  # Solar Heat Gain Coefficient (0 - 1)
    uwgDict["albWall"] = None  # wall albedo (0 - 1)
    uwgDict["flr_h"] = None  # average building floor height

    # =================================================,
    # OPTIONAL PARAMETERS FOR SIMULATION CONTROL,
    # =================================================,
    # Simulation parameters,
    uwgDict["Month"] = 10  # starting month (1-12)
    uwgDict["Day"] = 1  # starting day (1-31)
    uwgDict["nDay"] = 10  # number of days to run simultion
    uwgDict["dtSim"] = 300  # simulation time step (s)
    uwgDict["dtWeather"] = 3600  # weather time step (s)

    uwgDict["autosize"] = 0  # autosize HVAC (1 for yes; 0 for no)
    uwgDict["sensOcc"] = 100  # Sensible heat per occupant (W)
    # Latent heat fraction from occupant (normally 0.3)
    uwgDict["LatFOcc"] = 0.3
    # Radiant heat fraction from occupant (normally 0.2)
    uwgDict["RadFOcc"] = 0.2
    # Radiant heat fraction from equipment (normally 0.5)
    uwgDict["RadFEquip"] = 0.5
    # Radiant heat fraction from light (normally 0.7)
    uwgDict["RadFLight"] = 0.7

    # Urban climate parameters
    uwgDict["h_ubl1"] = 1000  # ubl height - day (m)
    uwgDict["h_ubl2"] = 80  # ubl height - night (m)
    uwgDict["h_ref"] = 150  # inversion height (m)
    uwgDict["h_temp"] = 2  # temperature height (m)
    uwgDict["h_wind"] = 10  # wind height (m)
    # circulation coefficient (default = 1.2 per Bruno (2012))
    uwgDict["c_circ"] = 1.2
    # exchange coefficient (default = 1; ref Bruno (2014))
    uwgDict["c_exch"] = 1
    uwgDict["maxDay"] = 150  # max day threshold (W/m^2)
    uwgDict["maxNight"] = 20  # max night threshold (W/m^2)
    uwgDict["windMin"] = 1  # min wind speed (m/s)
    uwgDict["h_obs"] = 0.1  # rural average obstacle height (m)

    return uwgDict


def get_uwg_file(uwg_object, refdir, fname):
    uwg_file_path = os.path.join(refdir, fname + ".uwg")
    f = open(uwg_file_path, "w")

    f.write("# =================================================\n")
    f.write("# REQUIRED PARAMETERS\n")
    f.write("# =================================================\n")
    f.write("\n")
    f.write("# Urban characteristics\n")
    f.write("bldHeight,{},\n".format(uwg_object["bldHeight"]))
    f.write("bldDensity,{},\n".format(uwg_object["bldDensity"]))
    f.write("verToHor,{},\n".format(uwg_object["verToHor"]))
    f.write("h_mix,{},\n".format(uwg_object["h_mix"]))
    # dimension of a square that encompasses the whole neighborhood [aka. characteristic length] (m)
    f.write("charLength,{},\n".format(uwg_object["charLength"]))
    # road albedo (0 - 1)
    f.write("albRoad,{},\n".format(uwg_object["albRoad"]))
    # road pavement thickness (m)
    f.write("dRoad,{},\n".format(uwg_object["dRoad"]))
    # road pavement conductivity (W/m K)
    f.write("kRoad,{},\n".format(uwg_object["kRoad"]))
    # road volumetric heat capacity (J/m^3 K)
    f.write("cRoad,{},\n".format(uwg_object["cRoad"]))
    # non-building sensible heat at street level [aka. heat from cars, pedestrians, street cooking, etc. ] (W/m^2)
    f.write("sensAnth,{},\n".format(uwg_object["sensAnth"]))
    # f.write("latAnth,{},\n".format(uwg_object['latAnth']))        # non-building latent heat (W/m^2) (currently not used)
    f.write("\n")
    f.write("zone,{},\n".format(uwg_object["zone"]))
    f.write("\n")
    f.write("# Vegetation parameters\n")
    # Fraction of the urban ground covered in grass/shrubs only (0-1)
    f.write("grasscover,{},\n".format(uwg_object["grasscover"]))
    # Fraction of the urban ground covered in trees (0-1)
    f.write("treeCover,{},\n".format(uwg_object["treeCover"]))
    # The month in which vegetation starts to evapotranspire (leaves are out)
    f.write("vegStart,{},\n".format(uwg_object["vegStart"]))
    # The month in which vegetation stops evapotranspiring (leaves fall)
    f.write("vegEnd,{},\n".format(uwg_object["vegEnd"]))
    # Vegetation albedo
    f.write("albVeg,{},\n".format(uwg_object["albVeg"]))
    # Fraction of the rural ground covered by vegetation
    f.write("rurVegCover,{},\n".format(uwg_object["rurVegCover"]))
    # Fraction of the heat absorbed by grass that is latent. Used in UWG only to calculate sensible heat fraction.
    f.write("latGrss,{},\n".format(uwg_object["latGrss"]))
    # Fraction of the heat absorbed by trees that is latent. Used in UWG only to calculate sensible heat fraction.
    f.write("latTree,{},\n".format(uwg_object["latTree"]))
    f.write("\n")
    f.write("# Traffic schedule [1 to 24 hour],\n")
    f.write("SchTraffic,\n")
    for i in range(3):
        for j in range(24):
            f.write("{},".format(uwg_object["SchTraffic"][i][j]))
        f.write("\n")
    f.write("\n")
    f.write(
        "# Fraction of building stock for each DOE Building type (pre-80's build, 80's-present build, new)\n"
    )
    f.write("# Note that sum(bld) must be equal to 1\n")
    f.write("bld,\n")
    for i in range(16):
        for j in range(3):
            f.write("{},".format(uwg_object["bld"][j][i]))
        f.write("\n")
    f.write("\n")
    f.write("# =================================================\n")
    f.write("# OPTIONAL URBAN PARAMETERS\n")
    f.write("# =================================================\n")
    f.write(
        "# If not provided, optional parameters are taken from corresponding DOE Reference building\n"
    )
    f.write(
        "albRoof,{},\n".format(
            # roof albedo (0 - 1)
            uwg_object["albRoof"]
            if uwg_object["albRoof"]
            else ""
        )
    )
    # Fraction of the roofs covered in grass/shrubs (0 - 1)
    f.write(
        "vegRoof,{},\n".format(
            uwg_object["vegRoof"] if uwg_object["vegRoof"] else ""
        )
    )
    # Glazing Ratio (0 - 1)
    f.write(
        "glzR,{},\n".format(uwg_object["glzR"] if uwg_object["glzR"] else "")
    )
    # Solar Heat Gain Coefficient (0 - 1)
    f.write(
        "SHGC,{},\n".format(uwg_object["SHGC"] if uwg_object["SHGC"] else "")
    )
    f.write(
        "albWall,{},\n".format(
            # wall albedo (0 - 1)
            uwg_object["albWall"]
            if uwg_object["albWall"]
            else ""
        )
    )
    # average building floor height
    f.write(
        "flr_h,{},\n".format(
            uwg_object["flr_h"] if uwg_object["flr_h"] else ""
        )
    )
    f.write("\n")
    f.write("# =================================================\n")
    f.write("# OPTIONAL PARAMETERS FOR SIMULATION CONTROL,\n")
    f.write("# =================================================\n")
    f.write("\n")
    f.write("# Simulation parameters,\n")
    # starting month (1-12)
    f.write("Month,{},\n".format(uwg_object["Month"]))
    # starting day (1-31)
    f.write("Day,{},\n".format(uwg_object["Day"]))
    # number of days to run simultion
    f.write("nDay,{},\n".format(uwg_object["nDay"]))
    # simulation time step (s)
    f.write("dtSim,{},\n".format(uwg_object["dtSim"]))
    # weather time step (s)
    f.write("dtWeather,{},\n".format(uwg_object["dtWeather"])),
    f.write("\n")
    f.write("# HVAC system and internal loads\n")
    # autosize HVAC (1 for yes; 0 for no)
    f.write("autosize,{},\n".format(uwg_object["autosize"]))
    # Sensible heat per occupant (W)
    f.write("sensOcc,{},\n".format(uwg_object["sensOcc"]))
    # Latent heat fraction from occupant (normally 0.3)
    f.write("LatFOcc,{},\n".format(uwg_object["LatFOcc"]))
    # Radiant heat fraction from occupant (normally 0.2)
    f.write("RadFOcc,{},\n".format(uwg_object["RadFOcc"]))
    # Radiant heat fraction from equipment (normally 0.5)
    f.write("RadFEquip,{},\n".format(uwg_object["RadFEquip"]))
    # Radiant heat fraction from light (normally 0.7)
    f.write("RadFLight,{},\n".format(uwg_object["RadFLight"]))
    f.write("\n")
    f.write("#Urban climate parameters\n")
    # ubl height - day (m)
    f.write("h_ubl1,{},\n".format(uwg_object["h_ubl1"]))
    # ubl height - night (m)
    f.write("h_ubl2,{},\n".format(uwg_object["h_ubl2"]))
    # inversion height (m)
    f.write("h_ref,{},\n".format(uwg_object["h_ref"]))
    # temperature height (m)
    f.write("h_temp,{},\n".format(uwg_object["h_temp"]))
    f.write("h_wind,{},\n".format(uwg_object["h_wind"]))  # wind height (m)
    # circulation coefficient (default = 1.2 per Bruno (2012))
    f.write("c_circ,{},\n".format(uwg_object["c_circ"]))
    # exchange coefficient (default = 1; ref Bruno (2014))
    f.write("c_exch,{},\n".format(uwg_object["c_exch"]))
    # max day threshold (W/m^2)
    f.write("maxDay,{},\n".format(uwg_object["maxDay"]))
    # max night threshold (W/m^2)
    f.write("maxNight,{},\n".format(uwg_object["maxNight"]))
    # min wind speed (m/s)
    f.write("windMin,{},\n".format(uwg_object["windMin"]))
    # rural average obstacle height (m)
    f.write("h_obs,{},\n".format(uwg_object["h_obs"]))

    f.close()

    return uwg_file_path


def read_uwg_file(refdir, fname):
    uwg_file_path = os.path.join(refdir, fname + ".uwg")
    # f = open(uwg_file_path, "r")

    uwgdict = {}
    skiptype = 0
    skipcount = 0
    trafficlist = []
    bldlist = []
    l1 = []
    l2 = []
    l3 = []

    with open(uwg_file_path) as file:
        # next(file)
        for line in file:
            if line[0:7] == "SchTraf":
                skiptype = 1
            if line[0:4] == "bld,":
                skiptype = 2
            if skiptype == 0:
                if line[0] == "#" or line == "\n":  # empty line or comment
                    test = 4
                else:  # regular input
                    a = line.find(",")
                    if line[0:a] == "zone":
                        uwgdict[line[0:a]] = line[a + 1 : len(line) - 2]
                    elif line[-3:] == ",,\n":
                        uwgdict[line[0:a]] = None
                    else:
                        uwgdict[line[0:a]] = float(line[a + 1 : len(line) - 2])
            elif skiptype == 1:  # Traffic
                if skipcount >= 1:
                    letter_list = line.split(",")
                    floats_list = []
                    for item in letter_list:
                        if item == "\n":
                            test = 4
                        else:
                            floats_list.append(float(item))
                    trafficlist.append(floats_list)
                skipcount += 1
                if skipcount == 4:
                    skipcount = 0
                    skiptype = 0
                    uwgdict["SchTraffic"] = trafficlist
            elif skiptype == 2:  # Buildings
                if skipcount >= 1:
                    letter_list = line.split(",")
                    l1.append(letter_list[0])
                    l2.append(letter_list[1])
                    l3.append(float(letter_list[2]))

                    # if skipcount < 3:
                    #     for item in letter_list:
                    #         if item == '\n':
                    #             test = 4
                    #         else:
                    #             floats_list.append(item)
                    #     bldlist.append(floats_list)
                    # else:
                    #     for item in letter_list:
                    #         if item == '\n':
                    #             test = 4
                    #         else:
                    #             floats_list.append(float(item))
                    #     bldlist.append(floats_list)
                skipcount += 1
                if skipcount == 17:
                    skipcount = 0
                    skiptype = 0
                    bldlist.append(l1)
                    bldlist.append(l2)
                    bldlist.append(l3)
                    uwgdict["bld"] = bldlist

    return uwgdict
