import numpy as np

def sunonsurface_2018a(azimuthA, scale, buildings, shadow, sunwall, first, second, aspect, walls, Tg, Tgwall, Ta,
                       emis_grid, ewall, alb_grid, SBC, albedo_b, Twater, lc_grid, landcover):
    # This version of sunonsurfce goes with SOLWEIG 2015a. It also simulates
    # Lup and albedo based on landcover information and shadow patterns.
    # Fredrik Lindberg, fredrikl@gvc.gu.se

    sizex = np.shape(walls)[0]
    sizey = np.shape(walls)[1]

    # sizex=size(buildings,1);sizey=size(buildings,2);
    wallbol = (walls > 0) * 1
    sunwall[sunwall > 0] = 1  # test 20160910

    # conversion into radians
    azimuth = azimuthA * (np.pi / 180)

    # loop parameters
    index = 0
    f = buildings
    Lup = SBC * emis_grid * (Tg * shadow + Ta + 273.15) ** 4 - SBC * emis_grid * (Ta + 273.15) ** 4  # +Ta
    if landcover == 1:
        Tg[lc_grid == 3] = Twater - Ta  # Setting water temperature

    Lwall = SBC * ewall * (Tgwall + Ta + 273.15) ** 4 - SBC * ewall * (Ta + 273.15) ** 4  # +Ta
    albshadow = alb_grid * shadow
    alb = alb_grid
    # sh(sh<=0.1)=0;
    # sh=sh-(1-vegsh)*(1-psi);
    # shadow=sh-(1-vegsh)*(1-psi);
    # dx=0;
    # dy=0;
    # ds=0; ##ok<NASGU>

    tempsh = np.zeros((sizex, sizey))
    tempbu = np.zeros((sizex, sizey))
    tempbub = np.zeros((sizex, sizey))
    tempbubwall = np.zeros((sizex, sizey))
    tempwallsun = np.zeros((sizex, sizey))
    weightsumsh = np.zeros((sizex, sizey))
    weightsumwall = np.zeros((sizex, sizey))
    first = np.round(first * scale)
    if first < 1:
        first = 1
    second = np.round(second * scale)
    # tempTgsh=tempsh;
    weightsumLupsh = np.zeros((sizex, sizey))
    weightsumLwall = np.zeros((sizex, sizey))
    weightsumalbsh = np.zeros((sizex, sizey))
    weightsumalbwall = np.zeros((sizex, sizey))
    weightsumalbnosh = np.zeros((sizex, sizey))
    weightsumalbwallnosh = np.zeros((sizex, sizey))
    tempLupsh = np.zeros((sizex, sizey))
    tempalbsh = np.zeros((sizex, sizey))
    tempalbnosh = np.zeros((sizex, sizey))

    # other loop parameters
    pibyfour = np.pi / 4
    threetimespibyfour = 3 * pibyfour
    fivetimespibyfour = 5 * pibyfour
    seventimespibyfour = 7 * pibyfour
    sinazimuth = np.sin(azimuth)
    cosazimuth = np.cos(azimuth)
    tanazimuth = np.tan(azimuth)
    signsinazimuth = np.sign(sinazimuth)
    signcosazimuth = np.sign(cosazimuth)

    ## The Shadow casting algoritm
    for n in np.arange(0, second):
        if (pibyfour <= azimuth and azimuth < threetimespibyfour) or (
                fivetimespibyfour <= azimuth and azimuth < seventimespibyfour):
            dy = signsinazimuth * index
            dx = -1 * signcosazimuth * np.abs(np.round(index / tanazimuth))
            # ds = dssin
        else:
            dy = signsinazimuth * abs(round(index * tanazimuth))
            dx = -1 * signcosazimuth * index
            # ds = dscos

        absdx = np.abs(dx)
        absdy = np.abs(dy)

        xc1 = ((dx + absdx) / 2)
        xc2 = (sizex + (dx - absdx) / 2)
        yc1 = ((dy + absdy) / 2)
        yc2 = (sizey + (dy - absdy) / 2)

        xp1 = -((dx - absdx) / 2)
        xp2 = (sizex - (dx + absdx) / 2)
        yp1 = -((dy - absdy) / 2)
        yp2 = (sizey - (dy + absdy) / 2)

        tempbu[int(xp1):int(xp2), int(yp1):int(yp2)] = buildings[int(xc1):int(xc2),
                                                       int(yc1):int(yc2)]  # moving building
        tempsh[int(xp1):int(xp2), int(yp1):int(yp2)] = shadow[int(xc1):int(xc2), int(yc1):int(yc2)]  # moving shadow
        tempLupsh[int(xp1):int(xp2), int(yp1):int(yp2)] = Lup[int(xc1):int(xc2), int(yc1):int(yc2)]  # moving Lup/shadow
        tempalbsh[int(xp1):int(xp2), int(yp1):int(yp2)] = albshadow[int(xc1):int(xc2),
                                                          int(yc1):int(yc2)]  # moving Albedo/shadow
        tempalbnosh[int(xp1):int(xp2), int(yp1):int(yp2)] = alb[int(xc1):int(xc2), int(yc1):int(yc2)]  # moving Albedo
        f = np.min([f, tempbu], axis=0)  # utsmetning av buildings

        shadow2 = tempsh * f
        weightsumsh = weightsumsh + shadow2

        Lupsh = tempLupsh * f
        weightsumLupsh = weightsumLupsh + Lupsh

        albsh = tempalbsh * f
        weightsumalbsh = weightsumalbsh + albsh

        albnosh = tempalbnosh * f
        weightsumalbnosh = weightsumalbnosh + albnosh

        tempwallsun[int(xp1):int(xp2), int(yp1):int(yp2)] = sunwall[int(xc1):int(xc2),
                                                            int(yc1):int(yc2)]  # moving buildingwall insun image
        tempb = tempwallsun * f
        tempbwall = f * -1 + 1
        tempbub = ((tempb + tempbub) > 0) * 1
        tempbubwall = ((tempbwall + tempbubwall) > 0) * 1
        weightsumLwall = weightsumLwall + tempbub * Lwall
        weightsumalbwall = weightsumalbwall + tempbub * albedo_b
        weightsumwall = weightsumwall + tempbub
        weightsumalbwallnosh = weightsumalbwallnosh + tempbubwall * albedo_b

        ind = 1
        if (n + 1) <= first:
            weightsumwall_first = weightsumwall / ind
            weightsumsh_first = weightsumsh / ind
            wallsuninfluence_first = weightsumwall_first > 0
            weightsumLwall_first = (weightsumLwall) / ind  # *Lwall
            weightsumLupsh_first = weightsumLupsh / ind

            weightsumalbwall_first = weightsumalbwall / ind  # *albedo_b
            weightsumalbsh_first = weightsumalbsh / ind
            weightsumalbwallnosh_first = weightsumalbwallnosh / ind  # *albedo_b
            weightsumalbnosh_first = weightsumalbnosh / ind
            wallinfluence_first = weightsumalbwallnosh_first > 0
            #         gvf1=(weightsumwall+weightsumsh)/first;
            #         gvf1(gvf1>1)=1;
            ind += 1
        index += 1

    wallsuninfluence_second = weightsumwall > 0
    wallinfluence_second = weightsumalbwallnosh > 0
    # gvf2(gvf2>1)=1;

    # Removing walls in shadow due to selfshadowing
    azilow = azimuth - np.pi / 2
    azihigh = azimuth + np.pi / 2
    if azilow >= 0 and azihigh < 2 * np.pi:  # 90 to 270  (SHADOW)
        facesh = (np.logical_or(aspect < azilow, aspect >= azihigh).astype(float) - wallbol + 1)
    elif azilow < 0 and azihigh <= 2 * np.pi:  # 0 to 90
        azilow = azilow + 2 * np.pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh) * -1 + 1  # (SHADOW)    # check for the -1
    elif azilow > 0 and azihigh >= 2 * np.pi:  # 270 to 360
        azihigh = azihigh - 2 * np.pi
        facesh = np.logical_or(aspect > azilow, aspect <= azihigh) * -1 + 1  # (SHADOW)

    # removing walls in self shadoing
    keep = (weightsumwall == second) - facesh
    keep[keep == -1] = 0

    # gvf from shadow only
    gvf1 = ((weightsumwall_first + weightsumsh_first) / (first + 1)) * wallsuninfluence_first + \
           (weightsumsh_first) / (first) * (wallsuninfluence_first * -1 + 1)
    weightsumwall[keep == 1] = 0
    gvf2 = ((weightsumwall + weightsumsh) / (second + 1)) * wallsuninfluence_second + \
           (weightsumsh) / (second) * (wallsuninfluence_second * -1 + 1)

    gvf2[gvf2 > 1.] = 1.

    # gvf from shadow and Lup
    gvfLup1 = ((weightsumLwall_first + weightsumLupsh_first) / (first + 1)) * wallsuninfluence_first + \
              (weightsumLupsh_first) / (first) * (wallsuninfluence_first * -1 + 1)
    weightsumLwall[keep == 1] = 0
    gvfLup2 = ((weightsumLwall + weightsumLupsh) / (second + 1)) * wallsuninfluence_second + \
              (weightsumLupsh) / (second) * (wallsuninfluence_second * -1 + 1)

    # gvf from shadow and albedo
    gvfalb1 = ((weightsumalbwall_first + weightsumalbsh_first) / (first + 1)) * wallsuninfluence_first + \
              (weightsumalbsh_first) / (first) * (wallsuninfluence_first * -1 + 1)
    weightsumalbwall[keep == 1] = 0
    gvfalb2 = ((weightsumalbwall + weightsumalbsh) / (second + 1)) * wallsuninfluence_second + \
              (weightsumalbsh) / (second) * (wallsuninfluence_second * -1 + 1)

    # gvf from albedo only
    gvfalbnosh1 = ((weightsumalbwallnosh_first + weightsumalbnosh_first) / (first + 1)) * wallinfluence_first + \
                  (weightsumalbnosh_first) / (first) * (wallinfluence_first * -1 + 1)  #
    gvfalbnosh2 = ((weightsumalbwallnosh + weightsumalbnosh) / (second)) * wallinfluence_second + \
                  (weightsumalbnosh) / (second) * (wallinfluence_second * -1 + 1)

    # Weighting
    gvf = (gvf1 * 0.5 + gvf2 * 0.4) / 0.9
    gvfLup = (gvfLup1 * 0.5 + gvfLup2 * 0.4) / 0.9
    gvfLup = gvfLup + ((SBC * emis_grid * (Tg * shadow + Ta + 273.15) ** 4) - SBC * emis_grid * (Ta + 273.15) ** 4) * (
                buildings * -1 + 1)  # +Ta
    gvfalb = (gvfalb1 * 0.5 + gvfalb2 * 0.4) / 0.9
    gvfalb = gvfalb + alb_grid * (buildings * -1 + 1) * shadow
    gvfalbnosh = (gvfalbnosh1 * 0.5 + gvfalbnosh2 * 0.4) / 0.9
    gvfalbnosh = gvfalbnosh * buildings + alb_grid * (buildings * -1 + 1)

    return gvf, gvfLup, gvfalb, gvfalbnosh, gvf2