import numpy as np


def TsWaveDelay_2015a(gvfLup, firstdaytime, timeadd, timestepdec, Tgmap1):

    Tgmap0 = gvfLup  # current timestep
    if firstdaytime == 1:  # "first in morning"
        Tgmap1 = Tgmap0

    if timeadd >= (59/1440):  # more or equal to 59 min
        weight1 = np.exp(-33.27 * timeadd)  # surface temperature delay function - 1 step
        Tgmap1 = Tgmap0 * (1 - weight1) + Tgmap1 * weight1
        Lup = Tgmap1
        if timestepdec > (59/1440):
            timeadd = timestepdec
        else:
            timeadd = 0
    else:
        timeadd = timeadd + timestepdec
        weight1 = np.exp(-33.27 * timeadd)  # surface temperature delay function - 1 step
        Lup = (Tgmap0 * (1 - weight1) + Tgmap1 * weight1)

    return Lup, timeadd, Tgmap1