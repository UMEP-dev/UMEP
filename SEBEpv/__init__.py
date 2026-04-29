# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SEBEpv
                                 A QGIS plugin
 Derived from SEBE:
 Calculated solar energy on roofs, walls and ground
                             -------------------
        begin                : 2015-09-17
        copyright            : (C) 2015 by Fredrik Lindberg - Dag Wästberg
        email                : fredrikl@gvc.gu.se
        git sha              : $Format:%H$

 New SEBEpv:
 Calculate Photovoltaic power on walls and roofs
                              -------------------
        begin                : 2016-11-17
        copyright            : (C) 2016 by Michael Revesz
        email                : michael.revesz@ait.ac.at
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
    """Load SEBEpv class from file SEBEpv.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .sebepv import SEBEpv
    return SEBEpv(iface)
