# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UMEP_Approved_Download
                                 A QGIS plugin
 UMEP approved data downloader
                             -------------------
        begin                : 2017-01-19
        copyright            : (C) 2017 by a
        email                : a
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
    """Load UMEP_Approved_Download class from file UMEP_Approved_Download.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .umep_downloader import UMEP_Data_Download
    return UMEP_Data_Download(iface)
