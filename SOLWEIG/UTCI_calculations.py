import numpy as np


def utci_polynomial(D_Tmrt, Ta, va, Pa):
    # Precompute powers (CSE) for scalar and 2D array inputs
    Ta2 = Ta * Ta
    Ta3 = Ta2 * Ta
    Ta4 = Ta3 * Ta
    Ta5 = Ta4 * Ta
    Ta6 = Ta5 * Ta

    va2 = va * va
    va3 = va2 * va
    va4 = va3 * va
    va5 = va4 * va
    va6 = va5 * va

    D2 = D_Tmrt * D_Tmrt
    D3 = D2 * D_Tmrt
    D4 = D3 * D_Tmrt
    D5 = D4 * D_Tmrt
    D6 = D5 * D_Tmrt

    Pa2 = Pa * Pa
    Pa3 = Pa2 * Pa
    Pa4 = Pa3 * Pa
    Pa5 = Pa4 * Pa
    Pa6 = Pa5 * Pa

    # calculate 6th order polynomial as approximation
    UTCI_approx = (
        Ta
        + 6.07562052e-01
        + (-2.27712343e-02) * Ta
        + (8.06470249e-04) * Ta2
        + (-1.54271372e-04) * Ta3
        + (-3.24651735e-06) * Ta4
        + (7.32602852e-08) * Ta5
        + (1.35959073e-09) * Ta6
        + (
            (-2.25836520e00)
            + (8.80326035e-02) * Ta
            + (2.16844454e-03) * Ta2
            + (-1.53347087e-05) * Ta3
            + (-5.72983704e-07) * Ta4
            + (-2.55090145e-09) * Ta5
        ) * va
        + (
            (-7.51269505e-01)
            + (-4.08350271e-03) * Ta
            + (-5.21670675e-05) * Ta2
            + (1.94544667e-06) * Ta3
            + (1.14099531e-08) * Ta4
        ) * va2
        + (
            (1.58137256e-01)
            + (-6.57263143e-05) * Ta
            + (2.22697524e-07) * Ta2
            + (-4.16117031e-08) * Ta3
        ) * va3
        + (
            (-1.27762753e-02)
            + (9.66891875e-06) * Ta
            + (2.52785852e-09) * Ta2
        ) * va4
        + ((4.56306672e-04) + (-1.74202546e-07) * Ta) * va5
        + (-5.91491269e-06) * va6
        + (
            (3.98374029e-01)
            + (1.83945314e-04) * Ta
            + (-1.73754510e-04) * Ta2
            + (-7.60781159e-07) * Ta3
            + (3.77830287e-08) * Ta4
            + (5.43079673e-10) * Ta5
            + (
                (-2.00518269e-02)
                + (8.92859837e-04) * Ta
                + (3.45433048e-06) * Ta2
                + (-3.77925774e-07) * Ta3
                + (-1.69699377e-09) * Ta4
            ) * va
            + (
                (1.69992415e-04)
                + (-4.99204314e-05) * Ta
                + (2.47417178e-07) * Ta2
                + (1.07596466e-08) * Ta3
            ) * va2
            + (
                (8.49242932e-05)
                + (1.35191328e-06) * Ta
                + (-6.21531254e-09) * Ta2
            ) * va3
            + ((-4.99410301e-06) + (-1.89489258e-08) * Ta) * va4
            + (8.15300114e-08) * va5
        ) * D_Tmrt
        + (
            (7.55043090e-04)
            + (-5.65095215e-05) * Ta
            + (-4.52166564e-07) * Ta2
            + (2.46688878e-08) * Ta3
            + (2.42674348e-10) * Ta4
            + (
                (1.54547250e-04)
                + (5.24110970e-06) * Ta
                + (-8.75874982e-08) * Ta2
                + (-1.50743064e-09) * Ta3
            ) * va
            + (
                (-1.56236307e-05)
                + (-1.33895614e-07) * Ta
                + (2.49709824e-09) * Ta2
            ) * va2
            + ((6.51711721e-07) + (1.94960053e-09) * Ta) * va3
            + (-1.00361113e-08) * va4
        ) * D2
        + (
            (-1.21206673e-05)
            + (-2.18203660e-07) * Ta
            + (7.51269482e-09) * Ta2
            + (9.79063848e-11) * Ta3
            + (
                (1.25006734e-06)
                + (-1.81584736e-09) * Ta
                + (-3.52197671e-10) * Ta2
            ) * va
            + ((-3.36514630e-08) + (1.35908359e-10) * Ta) * va2
            + (4.17032620e-10) * va3
        ) * D3
        + (
            (-1.30369025e-09)
            + (4.13908461e-10) * Ta
            + (9.22652254e-12) * Ta2
            + ((-5.08220384e-09) + (-2.24730961e-11) * Ta) * va
            + (1.17139133e-10) * va2
        ) * D4
        + (
            (6.62154879e-10)
            + (4.03863260e-13) * Ta
            + (1.95087203e-12) * va
        ) * D5
        + (-4.73602469e-12) * D6
        + (
            (5.12733497e00)
            + (-3.12788561e-01) * Ta
            + (-1.96701861e-02) * Ta2
            + (9.99690870e-04) * Ta3
            + (9.51738512e-06) * Ta4
            + (-4.66426341e-07) * Ta5
            + (
                (5.48050612e-01)
                + (-3.30552823e-03) * Ta
                + (-1.64119440e-03) * Ta2
                + (-5.16670694e-06) * Ta3
                + (9.52692432e-07) * Ta4
            ) * va
            + (
                (-4.29223622e-02)
                + (5.00845667e-03) * Ta
                + (1.00601257e-06) * Ta2
                + (-1.81748644e-06) * Ta3
            ) * va2
            + (
                (-1.25813502e-03)
                + (-1.79330391e-04) * Ta
                + (2.34994441e-06) * Ta2
            ) * va3
            + ((1.29735808e-04) + (1.29064870e-06) * Ta) * va4
            + (-2.28558686e-06) * va5
            + (
                (-3.69476348e-02)
                + (1.62325322e-03) * Ta
                + (-3.14279680e-05) * Ta2
                + (2.59835559e-06) * Ta3
                + (-4.77136523e-08) * Ta4
                + (
                    (8.64203390e-03)
                    + (-6.87405181e-04) * Ta
                    + (-9.13863872e-06) * Ta2
                    + (5.15916806e-07) * Ta3
                ) * va
                + (
                    (-3.59217476e-05)
                    + (3.28696511e-05) * Ta
                    + (-7.10542454e-07) * Ta2
                ) * va2
                + ((-1.24382300e-05) + (-7.38584400e-09) * Ta) * va3
                + (2.20609296e-07) * va4
            ) * D_Tmrt
            + (
                (-7.32469180e-04)
                + (-1.87381964e-05) * Ta
                + (4.80925239e-06) * Ta2
                + (-8.75492040e-08) * Ta3
                + (
                    (2.77862930e-05)
                    + (-5.06004592e-06) * Ta
                    + (1.14325367e-07) * Ta2
                ) * va
                + ((2.53016723e-06) + (-1.72857035e-08) * Ta) * va2
                + (-3.95079398e-08) * va3
            ) * D2
            + (
                (-3.59413173e-07)
                + (7.04388046e-07) * Ta
                + (-1.89309167e-08) * Ta2
                + ((-4.79768731e-07) + (7.96079978e-09) * Ta) * va
                + (1.62897058e-09) * va2
            ) * D3
            + (
                (3.94367674e-08)
                + (-1.18566247e-09) * Ta
                + (3.34678041e-10) * va
            ) * D4
            + (-1.15606447e-10) * D5
        ) * Pa
        + (
            (-2.80626406e00)
            + (5.48712484e-01) * Ta
            + (-3.99428410e-03) * Ta2
            + (-9.54009191e-04) * Ta3
            + (1.93090978e-05) * Ta4
            + (
                (-3.08806365e-01)
                + (1.16952364e-02) * Ta
                + (4.95271903e-04) * Ta2
                + (-1.90710882e-05) * Ta3
            ) * va
            + (
                (2.10787756e-03)
                + (-6.98445738e-04) * Ta
                + (2.30109073e-05) * Ta2
            ) * va2
            + ((4.17856590e-04) + (-1.27043871e-05) * Ta) * va3
            + (-3.04620472e-06) * va4
            + (
                (5.14507424e-02)
                + (-4.32510997e-03) * Ta
                + (8.99281156e-05) * Ta2
                + (-7.14663943e-07) * Ta3
                + (
                    (-2.66016305e-04)
                    + (2.63789586e-04) * Ta
                    + (-7.01199003e-06) * Ta2
                ) * va
                + ((-1.06823306e-04) + (3.61341136e-06) * Ta) * va2
                + (2.29748967e-07) * va3
            ) * D_Tmrt
            + (
                (3.04788893e-04)
                + (-6.42070836e-05) * Ta
                + (1.16257971e-06) * Ta2
                + ((7.68023384e-06) + (-5.47446896e-07) * Ta) * va
                + (-3.59937910e-08) * va2
            ) * D2
            + (
                (-4.36497725e-06)
                + (1.68737969e-07) * Ta
                + (2.67489271e-08) * va
            ) * D3
            + (3.23926897e-09) * D4
        ) * Pa2
        + (
            (-3.53874123e-02)
            + (-2.21201190e-01) * Ta
            + (1.55126038e-02) * Ta2
            + (-2.63917279e-04) * Ta3
            + (
                (4.53433455e-02)
                + (-4.32943862e-03) * Ta
                + (1.45389826e-04) * Ta2
            ) * va
            + ((2.17508610e-04) + (-6.66724702e-05) * Ta) * va2
            + (3.33217140e-05) * va3
            + (
                (-2.26921615e-03)
                + (3.80261982e-04) * Ta
                + (-5.45314314e-09) * Ta2
                + ((-7.96355448e-04) + (2.53458034e-05) * Ta) * va
                + (-6.31223658e-06) * va2
            ) * D_Tmrt
            + (
                (3.02122035e-04)
                + (-4.77403547e-06) * Ta
                + (1.73825715e-06) * va
            ) * D2
            + (-4.09087898e-07) * D3
        ) * Pa3
        + (
            (6.14155345e-01)
            + (-6.16755931e-02) * Ta
            + (1.33374846e-03) * Ta2
            + ((3.55375387e-03) + (-5.13027851e-04) * Ta) * va
            + (1.02449757e-04) * va2
            + (
                (-1.48526421e-03)
                + (-4.11469183e-05) * Ta
                + (-6.80434415e-06) * va
            ) * D_Tmrt
            + (-9.77675906e-06) * D2
        ) * Pa4
        + (
            (8.82773108e-02)
            + (-3.01859306e-03) * Ta
            + (1.04452989e-03) * va
            + (2.47090539e-04) * D_Tmrt
        ) * Pa5
        + (1.48348065e-03) * Pa6
    )

    return UTCI_approx


def utci_calculator(Ta, RH, Tmrt, va10m):
    # Program for calculating UTCI Temperature (UTCI)
    # released for public use after termination of COST Action 730

    # Translated from fortran by Fredrik Lindberg, Sweden
    # UTCI, Version a 0.002, October 2009
    # Copyright (C) 2009  Peter Broede

    if Ta <= -999 or RH <= -999 or va10m <= -999 or Tmrt <= -999:
        UTCI_approx = -999
    else:
        # saturation vapour pressure (es)
        g = np.array(
            [
                -2.8365744e3,
                -6.028076559e3,
                1.954263612e1,
                -2.737830188e-2,
                1.6261698e-5,
                7.0229056e-10,
                -1.8680009e-13,
                2.7150305,
            ]
        )

        tk = Ta + 273.15  # ! air temp in K
        es = g[7] * np.log(tk)
        for i in range(0, 7):
            es = es + g[i] * tk ** (i + 1 - 3.0)

        es = np.exp(es) * 0.01

        ehPa = es * RH / 100.0

        D_Tmrt = Tmrt - Ta
        Pa = ehPa / 10.0  # use vapour pressure in kPa
        va = va10m

        # Calculate 6th order polynomial as approximation
        UTCI_approx = utci_polynomial(D_Tmrt, Ta, va, Pa)

    return UTCI_approx


def utci_calculator_grid(Ta, RH, Tmrt, va10m, feedback=None):
    # Program for calculating UTCI Temperature (UTCI)
    # released for public use after termination of COST Action 730

    # Translated from fortran by Fredrik Lindberg, Sweden
    # UTCI, Version a 0.002, October 2009
    # Copyright (C) 2009  Peter Broede

    rows = Tmrt.shape[0]
    cols = Tmrt.shape[1]

    # If Tair or relative humidity is NaN, set all UTCI to -999
    if Ta <= -999 or RH <= -999:
        UTCI_approx = np.ones((rows, cols)) * -999
    # Else, create an empty raster for UTCI and start estimating UTCI
    else:
        if feedback is not None and feedback.isCanceled():
            feedback.setProgressText("Calculation cancelled")
            return np.zeros((rows, cols))

        # saturation vapour pressure (es)
        g = np.array(
            [
                -2.8365744e3,
                -6.028076559e3,
                1.954263612e1,
                -2.737830188e-2,
                1.6261698e-5,
                7.0229056e-10,
                -1.8680009e-13,
                2.7150305,
            ]
        )

        tk = Ta + 273.15  # ! air temp in K
        es = g[7] * np.log(tk)
        for i in range(0, 7):
            es = es + g[i] * tk ** (i + 1 - 3.0)

        es = np.exp(es) * 0.01

        ehPa = es * RH / 100.0
        Pa = ehPa / 10.0  # use vapour pressure in kPa

        UTCI_approx = np.zeros((rows, cols))
        invalid_mask = (Tmrt <= -999) | (va10m <= -999)
        valid_mask = (~invalid_mask) & (va10m > 0)

        if np.any(valid_mask):
            D_Tmrt_valid = Tmrt[valid_mask] - Ta
            va_valid = va10m[valid_mask]
            UTCI_approx[valid_mask] = utci_polynomial(
                D_Tmrt_valid, Ta, va_valid, Pa
            )

        UTCI_approx[invalid_mask] = -9999

        if feedback is not None:
            feedback.setProgress(100)

    return UTCI_approx
