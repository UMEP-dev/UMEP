# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SolweigAnalyzer
                                 A QGIS plugin
 This plugin postprocess model output from the SOLWEIG model
                             -------------------
        begin                : 2016-10-21
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
    """Load SolweigAnalyzer class from file SolweigAnalyzer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .solweig_analyzer import SolweigAnalyzer
    return SolweigAnalyzer(iface)
