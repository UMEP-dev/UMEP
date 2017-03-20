# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GreaterQF
                                 A QGIS plugin
 GreaterQF model
                             -------------------
        begin                : 2016-06-20
        copyright            : (C) 2016 by University of reading
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
    """Load GreaterQF class from file GreaterQF.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .LQF import LQF
    return LQF(iface)
