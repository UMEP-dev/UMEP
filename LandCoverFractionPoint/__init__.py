# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandCoverFractionPoint
                                 A QGIS plugin
 Calculates land cover fraction from a buffered point
                             -------------------
        begin                : 2015-07-13
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
    """Load LandCoverFractionPoint class from file LandCoverFractionPoint.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .landcover_fraction_point import LandCoverFractionPoint
    return LandCoverFractionPoint(iface)
