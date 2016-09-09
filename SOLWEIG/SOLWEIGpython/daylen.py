
import numpy as np

def daylen(DOY, XLAT):
    # Calculation of declination of sun (Eqn. 16). Amplitude= +/-23.45
    # deg. Minimum = DOY 355 (DEC 21), maximum = DOY 172.5 (JUN 21/22).
    # Sun angles.  SOC limited for latitudes above polar circles.
    # Calculate daylength, sunrise and sunset (Eqn. 17)

    RAD=np.pi/180.0

    DEC = -23.45 * np.cos(2.0*np.pi*(DOY+10.0)/365.0)

    SOC = np.tan(RAD*DEC) * np.tan(RAD*XLAT)
    SOC = min(max(SOC,-1.0),1.0)
    # SOC=alt

    DAYL = 12.0 + 24.0*np.arcsin(SOC)/np.pi
    SNUP = 12.0 - DAYL/2.0
    SNDN = 12.0 + DAYL/2.0

    return DAYL, DEC, SNDN, SNUP
