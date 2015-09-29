# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WallHeight
                                 A QGIS plugin
 This plugin identifies wall pixels on a DSM and derives wall height and aspect 
                             -------------------
        begin                : 2015-09-16
        copyright            : (C) 2015 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
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
    """Load WallHeight class from file WallHeight.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .wall_height import WallHeight
    return WallHeight(iface)
