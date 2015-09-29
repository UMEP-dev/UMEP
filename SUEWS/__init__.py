# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SUEWS
                                 A QGIS plugin
 Full version of SUEWS v2015a
                             -------------------
        begin                : 2015-09-27
        copyright            : (C) 2015 by Sue Grimmond
        email                : sue.grimmond@reading.ac.uk
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SUEWS class from file SUEWS.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .suews import SUEWS
    return SUEWS(iface)
