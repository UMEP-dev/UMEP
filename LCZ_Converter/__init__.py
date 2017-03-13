# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LCZ_test
                                 A QGIS plugin
 Converts LCZ raster to input for SUEWS
                             -------------------
        begin                : 2017-02-03
        copyright            : (C) 2017 by University of Reading
        email                : n.e.theeuwes@reading.ac.uk
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
    """Load LCZ_test class from file LCZ_test.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .LCZ_converter import LCZ_test
    return LCZ_test(iface)
