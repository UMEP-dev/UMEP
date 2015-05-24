# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageMorphParam
                                 A QGIS plugin
 This plugin calculates morphometric parameters based on high resolution urban DSMs
                             -------------------
        begin                : 2015-01-06
        copyright            : (C) 2015 by Fredrik Lindberg, GU
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
    """Load ImageMorphParam class from file ImageMorphParam.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .image_morph_param import ImageMorphParam
    return ImageMorphParam(iface)
