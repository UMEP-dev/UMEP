# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TreeGenerator
                                 A QGIS plugin
 This plugin generates a vegetation canopy DSM and Trunk zone DSM from point data
                             -------------------
        begin                : 2016-10-25
        copyright            : (C) 2016 by Fredrik Lindberg
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
    """Load TreeGenerator class from file TreeGenerator.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .tree_generator import TreeGenerator
    return TreeGenerator(iface)
