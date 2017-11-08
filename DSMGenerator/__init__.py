# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DSMGenerator
                                 A QGIS plugin
 This plugin generates a DSM from DEM and OSM or other polygon height data.
                             -------------------
        begin                : 2017-10-26
        copyright            : (C) 2017 by Nils Wallenberg
        email                : nils.wallenberg@gvc.gu.se
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
    """Load DSMGenerator class from file DSMGenerator.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .dsm_generator import DSMGenerator
    return DSMGenerator(iface)
