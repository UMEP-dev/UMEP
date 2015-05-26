#-----------------------------------------------------------
#
# QGIS Combo Manager is a python module to easily manage a combo
# box with a layer list and eventually relate it with one or
# several combos with list of corresponding fields.
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------


class OptionDictionary(dict):
    """
    Conveninent class for options
    use OptionDictionary(availableOptions, userOptions)
    - availableOptions: a dictionary of {option_name: default_values}. default_value can be:
        - list-of-possible-values (default listed first)
        - or a single default value (no check)
        - or a type (no check, default is an empty instance of type)
    - userOptions: the dictionary given as argument in your method  {option_name: value}
    """
    def __init__(self, availableOptions, userOptions):
        dict.__init__(self)

        # check user options
        for key in userOptions:
            if key not in availableOptions:
                raise NameError("Option '%s' does not exist" % key)
            if type(availableOptions[key]) in (list, tuple) and userOptions[key] not in availableOptions[key]:
                raise NameError("Invalid value '%s' for option '%s'" % (userOptions[key], key))

        # create dictionary
        for key, value in availableOptions.iteritems():
            try:
                self[key] = userOptions[key]
            except KeyError:
                if type(value) in (list, tuple):
                    self[key] = value[0]
                elif type(value) == type:
                    self[key] = value()
                else:
                    self[key] = value

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        self[key] = value
