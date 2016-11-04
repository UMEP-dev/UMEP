# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExtremeFinder
                                 A QGIS plugin
 This plugin is for finding extreme events.
                             -------------------
        begin                : 2016-10-12
        copyright            : (C) 2016 by Bei Huang
        email                : b.huang@pgr.reading.ac.uk
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
    """Load ExtremeFinder class from file ExtremeFinder.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .extreme_finder import ExtremeFinder
    return ExtremeFinder(iface)
