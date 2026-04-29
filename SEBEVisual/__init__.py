# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Sun
                                 A QGIS plugin
 Creates a sun energy analyzing environment with statistics and 3D model 
                             -------------------
        begin                : 2014-03-20
        copyright            : (C) 2014 by Niklas Krave
        email                : niklaskrave@gmail.com
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

def classFactory(iface):
    # load Sun class from file Sun
    from .sun import Visual
    return Visual(iface)
