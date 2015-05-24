# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageMorphParmsPoint
                                 A QGIS plugin
 This plugin calculates Morphometric parameters fro a high resolution DSM around a point of interest
                             -------------------
        begin                : 2015-01-12
        copyright            : (C) 2015 by Fredrik Lindberg GU
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
    """Load ImageMorphParmsPoint class from file ImageMorphParmsPoint.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .imagemorphparmspoint_v1 import ImageMorphParmsPoint
    return ImageMorphParmsPoint(iface)
