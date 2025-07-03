from __future__ import absolute_import
author = 'xlinfr'

from . import sun_distance
import numpy as np
import math

def clearnessindex_2013b(zen, jday, Ta, RH, radG, location, P):

    """ Clearness Index at the Earth's surface calculated from Crawford and Duchon 1999

    :param zen: zenith angle in radians
    :param jday: day of year
    :param Ta: air temperature
    :param RH: relative humidity
    :param radG: global shortwave radiation
    :param location: distionary including lat, lon and alt
    :param P: pressure
    :return:
    """

    if P == -999.0:
        p = 1013.  # Pressure in millibars
    else:
        p = P*10.  # Convert from hPa to millibars

    Itoa = 1370.0  # Effective solar constant
    D = sun_distance.sun_distance(jday)  # irradiance differences due to Sun-Earth distances
    m = 35. * np.cos(zen) * ((1224. * (np.cos(zen)**2) + 1) ** (-1/2.))     # optical air mass at p=1013
    Trpg = 1.021-0.084*(m*(0.000949*p+0.051))**0.5  # Transmission coefficient for Rayliegh scattering and permanent gases

    # empirical constant depending on latitude
    if location['latitude'] < 10.:
        G = [3.37, 2.85, 2.80, 2.64]
    elif location['latitude'] >= 10. and location['latitude'] < 20.:
        G = [2.99, 3.02, 2.70, 2.93]
    elif location['latitude'] >= 20. and location['latitude'] <30.:
        G = [3.60, 3.00, 2.98, 2.93]
    elif location['latitude'] >= 30. and location['latitude'] <40.:
        G = [3.04, 3.11, 2.92, 2.94]
    elif location['latitude'] >= 40. and location['latitude'] <50.:
        G = [2.70, 2.95, 2.77, 2.71]
    elif location['latitude'] >= 50. and location['latitude'] <60.:
        G = [2.52, 3.07, 2.67, 2.93]
    elif location['latitude'] >= 60. and location['latitude'] <70.:
        G = [1.76, 2.69, 2.61, 2.61]
    elif location['latitude'] >= 70. and location['latitude'] <80.:
        G = [1.60, 1.67, 2.24, 2.63]
    elif location['latitude'] >= 80. and location['latitude'] <90.:
        G = [1.11, 1.44, 1.94, 2.02]

    if jday > 335 or jday <= 60:
        G = G[0]
    elif jday > 60 and jday <= 152:
        G = G[1]
    elif jday > 152 and jday <= 244:
        G = G[2]
    elif jday > 244 and jday <= 335:
        G = G[3]

    # dewpoint calculation
    a2 = 17.27
    b2 = 237.7
    Td = (b2*(((a2*Ta)/(b2+Ta))+np.log(RH)))/(a2-(((a2*Ta)/(b2+Ta))+np.log(RH)))
    Td = (Td*1.8)+32  # Dewpoint (F)
    u = np.exp(0.1133-np.log(G+1)+0.0393*Td)  # Precipitable water
    Tw = 1-0.077*((u*m)**0.3)  # Transmission coefficient for water vapor
    Tar = 0.935**m  # Transmission coefficient for aerosols

    I0=Itoa*np.cos(zen)*Trpg*Tw*D*Tar
    if abs(zen)>np.pi/2:
        I0 = 0
    # b=I0==abs(zen)>np.pi/2
    # I0(b==1)=0
    # clear b;
    if not(np.isreal(I0)):
        I0 = 0

    corr=0.1473*np.log(90-(zen/np.pi*180))+0.3454  # 20070329

    CIuncorr = radG / I0
    CI = CIuncorr + (1-corr)
    I0et = Itoa*np.cos(zen)*D  # extra terrestial solar radiation
    Kt = radG / I0et
    if math.isnan(CI):
        CI = float('Inf')

    return I0, CI, Kt, I0et, CIuncorr