# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandCoverReclassifier
                                 A QGIS plugin
 Reclassifies a raster to a UMEP land cover grid
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
    """Load LandCoverReclassifier class from file LandCoverReclassifier.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .land_cover_reclassifier import LandCoverReclassifier
    return LandCoverReclassifier(iface)
