# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SOLWEIG
                                 A QGIS plugin
 Solar and longwave environmental irraniance model
                             -------------------
        begin                : 2016-09-06
        copyright            : (C) 2016 by Fredrik Lindberg, UoG
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
    """Load SOLWEIG class from file SOLWEIG.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .solweig import SOLWEIG
    return SOLWEIG(iface)
