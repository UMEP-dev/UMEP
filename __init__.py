# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UMEP
                                 A QGIS plugin
 UMEP
                             -------------------
        begin                : 2015-04-29
        copyright            : (C) 2015 by fredrikl@gvc.gu.se
        email                : Fredrik Lindberg
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
    """Load UMEP class from file UMEP.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .UMEP import UMEP
    return UMEP(iface)
