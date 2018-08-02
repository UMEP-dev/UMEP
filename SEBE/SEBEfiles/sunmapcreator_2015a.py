from __future__ import division
from __future__ import absolute_import
from builtins import range
import numpy as np
from ...Utilities.SEBESOLWEIGCommonFiles.diffusefraction import diffusefraction
from .Perez_v3 import Perez_v3
from ...Utilities.SEBESOLWEIGCommonFiles.clearnessindex_2013b import clearnessindex_2013b


def sunmapcreator_2015a(met, altitude, azimuth, onlyglobal, output, jday, albedo, location, zen):
    """
    % This function creates a sun map based on hourly values of solar radiation.

    :param met:
    :param altitude: 2D array
    :param azimuth:
    :param onlyglobal:
    :param output:
    :param jday:
    :param albedo:
    :return:
    """
    np.seterr(over='raise')
    np.seterr(invalid='raise')
    # Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
    # index = 1
    skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
    skyvaultaziint = np.array([12, 12, 15, 15, 20, 30, 60, 360])
    aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])
    azistart = np.array([0, 4, 2, 5, 8, 0, 10, 0])
    # annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])
    skyvaultazi = np.array([])
    for j in range(8):
        for k in range(1, int(360/skyvaultaziint[j]) + 1):
            # skyvaultalt(index)=skyvaultaltint(j);
            skyvaultazi = np.append(skyvaultazi, k*skyvaultaziint[j] + azistart[j])
            if skyvaultazi[-1] > 360:
                skyvaultazi[-1] = skyvaultazi[-1] - 360
            # index = index + 1

    iangle2 = np.array([])
    Gyear = 0
    Dyear = 0
    Gmonth = np.zeros([1, 12])
    Dmonth = Gmonth
    for j in range(len(aziinterval)):
        iangle2 = np.append(iangle2, skyvaultaltint[j] * np.ones([1, aziinterval[j]]))

    radmatI = np.transpose(np.vstack((iangle2, skyvaultazi, np.zeros((13, len(iangle2))))))
    radmatD = np.transpose(np.vstack((iangle2, skyvaultazi, np.zeros((13, len(iangle2))))))
    radmatR = np.transpose(np.vstack((iangle2, skyvaultazi, np.zeros((13, len(iangle2))))))

    iazimuth = skyvaultazi
    # Ta = met[:, 11]
    # RH = met[:, 10]

    # Main loop
    for i in range(len(met[:, 0])):
        alt = altitude[0, i]
        azi = azimuth[0, i]
        #disp(alt)
        if alt > 2:
            # Estimation of radD and radI if not measured after Reindl et al. (1990)
            if onlyglobal:
                if met[i, 11] <= -999.00 or met[i, 10] <= -999.00 or np.isnan(met[i, 11]) or np.isnan(met[i, 10]):
                    met[i, 11] = 15.0
                    met[i, 10] = 75.0

                I0, CI, Kt, I0et, CIuncorr = clearnessindex_2013b(zen[0, i], jday[0, i], met[i, 11], met[i, 10],
                                                                  met[i, 14], location, -999.0)
                I, D = diffusefraction(met[i, 14], altitude[0, i], Kt, met[i, 11], met[i, 10])
            else:
                I = met[i, 22]
                D = met[i, 21]

            G = met[i, 14]

            # anisotrophic diffuse distribution (Perez)
            lv, _, _ = Perez_v3(90-altitude[0, i], azimuth[0, i], D, I, jday[0, i], 1)

            distalt = np.abs(iangle2-alt)
            altlevel = distalt == (np.min(np.abs(distalt)))
            distazi = np.abs(iazimuth-azi)
            azipos = distazi[altlevel] == (np.min(distazi[altlevel]))
            azipos2 = np.where(altlevel)[0][0] + np.where(azipos)[0][0]
            #azipos2 = np.where(altlevel)[0] + np.where(azipos)[0]
            #azipos2 = find(altlevel, 1)-1 + find(azipos, 1)
            radmatI[azipos2, 2] = radmatI[azipos2, 2] + I
            radmatD[:, 2] = radmatD[:, 2] + D*lv[:, 2]
            radmatR[:, 2] = radmatR[:, 2] + G*(1/145)*albedo
            #         Gyear=Gyear+(G*sin(altitude(i)*(pi/180)));
            #         Dyear=Dyear+D;

            if output['energymonth'] == 1:
                radmatI[azipos2, met[i, 1] + 2] = radmatI[azipos2, met[i, 1] + 2] + I
                radmatD[:, met[i, 1] + 2] = radmatD[:, met[i, 1] + 2] + D*lv[:, 2]
                radmatR[:, met[i, 1] + 2] = radmatR[:, met[i, 1] + 2] + G*(1/145)*albedo
                #             Gmonth(met(i,2))=Gmonth(met(i,2))+(G*sin(altitude(i)*(pi/180)));
                #             Dmonth(met(i,2))=Dmonth(met(i,2))+D;

            #         plot(distazi),hold on
            #         plot(distalt,'r')
            #         plot(azipos2,15,'r*'),hold off
            #         pause(0.1);

    # Adjusting the numbers if multiple years is used

    if np.shape(met)[0] > 8760:
        multiyear = np.shape(met)[0]/8760
        radmatI[:, 2:15] = radmatI[:, 2:15]/multiyear
        radmatD[:, 2:15] = radmatD[:, 2:15]/multiyear
        radmatR[:, 2:15] = radmatR[:, 2:15]/multiyear

    #     Gyear=Gyear/multiyear;
    #     Dyear=Dyear/multiyear;
    #     Gmonth=Gmonth/multiyear;
    #     Dmonth=Gmonth/multiyear;
    # # Plotting
    # maxrad=max(radmat(:,3));
    # for i=1:length(radmat(:,1))
    #     if  radmat(i,3)>0
    #         pp(radmat(i,2)*(pi/180),(radmat(i,1)*-1)+90,[0 90],'LineStyle','none','Marker','h',...
    #             'LineColor',[(1-(radmat(i,3)/maxrad)) (1-(radmat(i,3)/maxrad)) (1-(radmat(i,3)/maxrad))],'NumRings',3)
    #         hold on
    #     end
    # end
    # set(gca,'YDir','reverse','FontSize',8,'View',[270 90],'XTickLabel','')

    ## Old skyvault
    # noa=19;# No. of anglesteps minus 1
    # step=89/noa;
    # iangle=[((step/2):step:89) 90];
    # [iazimuth aziinterval]=svf_angles_100121(iangle);
    # iangle2=[];
    # Gyear=0;
    # Dyear=0;
    # Gmonth=zeros(1,12);
    # Dmonth=Gmonth;
    # for j=1:length(aziinterval)
    #     iangle2=[iangle2 iangle(j)*ones(1,aziinterval(j))];
    # end
    #
    # radmat=[iangle2;iazimuth;zeros(13,length(iangle2))]';

    return radmatI, radmatD, radmatR
