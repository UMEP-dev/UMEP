# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FootprintModel
                                 A QGIS plugin
 Generates source area contributing to turbulent fluxes at central point
                             -------------------
        begin                : 2015-10-22
        copyright            : (C) 2015 by Christoph Kent
        email                : C.W.Kent@pgr.reading.ac.uk
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
    """Load FootprintModel class from file FootprintModel.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .footprint_model import FootprintModel
    return FootprintModel(iface)
