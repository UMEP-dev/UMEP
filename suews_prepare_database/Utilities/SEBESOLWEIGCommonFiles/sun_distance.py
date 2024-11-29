__author__ = 'xlinfr'
import numpy as np


def sun_distance(jday):
    """

    #% Calculatesrelative earth sun distance
    #% with day of year as input.
    #% Partridge and Platt, 1975
    """
    b = 2.*np.pi*jday/365.
    D = np.sqrt((1.00011+np.dot(0.034221, np.cos(b))+np.dot(0.001280, np.sin(b))+np.dot(0.000719,
                                        np.cos((2.*b)))+np.dot(0.000077, np.sin((2.*b)))))
    return D
