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

# The .egg packages shipped with QGIS sometimes appear before the user site dir
# in sys.path. To make sure package versions we install with "--user" take precedence,
# prepend the user site dir to sys.path before importing other packages.
# This works around https://github.com/qgis/QGIS/issues/55258
import site
import sys
sys.path.insert(0, site.getusersitepackages())


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load UMEP class from file UMEP.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .UMEP import UMEP
    return UMEP(iface)
