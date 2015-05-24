# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SkyViewFactorCalculator
                                 A QGIS plugin
 Calculates SVF on high resolution DSM (building and vegetation)
                             -------------------
        begin                : 2015-02-04
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
    """Load SkyViewFactorCalculator class from file SkyViewFactorCalculator.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .svf_calculator import SkyViewFactorCalculator
    return SkyViewFactorCalculator(iface)
