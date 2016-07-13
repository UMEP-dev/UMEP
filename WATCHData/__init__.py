# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WATCHData
                                 A QGIS plugin
 Downloads and process WATCH data for UMEP applications
                             -------------------
        begin                : 2016-07-08
        copyright            : (C) 2016 by Andrew Mark Gabey
        email                : a.m.gabey@reading.ac.uk
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
    """Load WATCHData class from file WATCHData.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .watch import WATCHData
    return WATCHData(iface)
