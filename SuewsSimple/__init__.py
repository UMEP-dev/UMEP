# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SuewsSimple
                                 A QGIS plugin
 SUEWS in simple mode
                             -------------------
        begin                : 2015-06-30
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
    """Load SuewsSimple class from file SuewsSimple.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .suews_simple import SuewsSimple
    return SuewsSimple(iface)
