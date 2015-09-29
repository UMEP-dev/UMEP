"""f90nml.fpy
   =============

   Module for conversion between basic data types and Fortran string
   representations.

   :copyright: Copyright 2014 Marshall Ward, see AUTHORS for details.
   :license: Apache License, Version 2.0, see LICENSE for details.
"""


def pyfloat(v_str):
    """Convert string repr of Fortran floating point to Python double."""
    # NOTE: There is no loss of information from SP to DP floats

    return float(v_str.lower().replace('d', 'e'))


def pycomplex(v_str):
    """Convert string repr of Fortran complex to Python complex."""
    assert isinstance(v_str, str)

    if v_str[0] == '(' and v_str[-1] == ')' and len(v_str.split(',')) == 2:
        v_re, v_im = v_str[1:-1].split(',', 1)

        # NOTE: Failed float(str) will raise ValueError
        return complex(pyfloat(v_re), pyfloat(v_im))
    else:
        raise ValueError('{0} must be in complex number form (x, y).'
                         ''.format(v_str))


def pybool(v_str):
    """Convert string repr of Fortran logical to Python logical."""
    assert isinstance(v_str, str)

    try:
        if v_str.startswith('.'):
            v_bool = v_str[1].lower()
        else:
            v_bool = v_str[0].lower()
    except IndexError:
        raise ValueError('{0} is not a valid logical constant.'.format(v_str))

    if v_bool == 't':
        return True
    elif v_bool == 'f':
        return False
    else:
        raise ValueError('{0} is not a valid logical constant.'.format(v_str))


def pystr(v_str):
    """Convert string repr of Fortran string to Python string."""
    assert isinstance(v_str, str)

    if v_str[0] in ("'", '"') and v_str[0] == v_str[-1]:
        return v_str[1:-1]
    else:
        return v_str
