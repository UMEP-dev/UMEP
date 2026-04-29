#### Function that calculates z0 and zd according to different methods ####
####INPUTS####
##Roughness Methods:
# 'RT'  - Rule of thumb
# 'Rau' - Raupach (1994/95)
# 'Bot' - Simplified Bottema (1995)
# 'Mac' - MacDonald et al. (1998)
# 'Mho' - Millward-Hopkins et al. (2011) [SIMPLIFIED]
# 'Kan' - Kanda et al. (2013)
##Building information
#zH - average building height,
#fai - frontal area,
#pai - plan area,
#zMax - max building height,
#zSdev - standard dev of building heights
####OUTPUTS####
#zd = zero-plane displacement height
#z0 = roughness length

import numpy as np
import math

####FUNCTION####
def RoughnessCalcMany(Roughnessmethod, zH, fai, pai, zMax, zSdev):

    z_d_output = np.zeros((fai.shape[0], 1)) - 999.
    z_0_output = np.zeros((fai.shape[0], 1)) - 999.

    for i in range(0, fai.shape[0]):
        if Roughnessmethod == 'RT':
            #Rule of thumb method
            z_d_output = 0.7*zH
            z_0_output = 0.1*zH
        elif Roughnessmethod == 'Rau':
            ##### Raupach 1994/95 ####
            Cs=0.003
            Cr=0.3
            Stab=0.193
            UdivUmax=0.3
            Cdl=7.5
            k=0.4
            RauZdexpW=(math.exp(-((Cdl*2*fai[i])**0.5)))-1
            z_d_output[i] = (1 + (RauZdexpW/((Cdl*2*fai[i])**0.5)))*zH[i]
            RauZoUtermW = 1/(min(((Cs+(Cr*fai[i]))**0.5), UdivUmax))
            RauZoexpW = np.exp((-k*RauZoUtermW)+Stab)
            z_0_output[i] = ((1-(z_d_output[i]/zH[i]))*RauZoexpW)*zH[i]

        elif Roughnessmethod == 'Bot':
            #Bottema
            Cdh = 0.8
            k=0.4
            z_d_output[i] = (pai[i]**0.6)*zH[i]
            BotZoexpW =np.exp(-k/((0.5*fai[i]*Cdh)**0.5))
            z_0_output[i] = (zH[i] - z_d_output[i])*(BotZoexpW)
        elif Roughnessmethod == 'Mac':
            #MacDonald
            Clb = 1.2
            k=0.4
            #Staggered array
            Alph = 4.43
            Beet = 1.0
            #Square array
            #Alph = 3.59
            #Beet = 0.55
            if zH[i]>0.:
                z_d_output[i] = (1+((Alph**-pai[i])*(pai[i]-1)))*zH[i]
                if z_d_output[i] != zH[i]:
                    z_0_output[i] = (zH[i]*((1-z_d_output[i]/zH[i]))*np.exp(-(0.5*(1.2/0.4**2)*(1-(z_d_output[i]/zH[i]))*fai[i])**-0.5))
                else:
                    z_0_output[i] = 0.
            else:
                z_d_output[i] = 0.
                z_0_output[i] = 0.
        elif Roughnessmethod == 'Kan':
            #Kanda
            Kanmeth = 1
            if Kanmeth == 1:
                    Ao = 1.29
                    Bo = 0.36
                    Co = -0.17
                    A1 = 0.71
                    B1= 20.21
                    C1 = -0.77
            elif Kanmeth == 2:
                    Ao = 0.86
                    Bo = 0.28
                    Co = -0.18
                    A1 = 0.93
                    B1 = 8.93
                    C1 = 4.68
            #First perform MacD method
            #MacDonald
            Clb = 1.2
            k=0.4
            #Staggered array
            Alph = 4.43
            Beet = 1.0
            #Square array
            #Alph = 3.59
            #Beet = 0.55
            if zH[i] > 0.:
                z_d_output[i] = (1+((Alph**-pai[i])*(pai[i]-1)))*zH[i]
                if z_d_output[i] != zH[i]:
                    z0Mac= (zH[i]*((1-z_d_output[i]/zH[i]))*np.exp(-(0.5*(1.2/0.4**2)*(1-(z_d_output[i]/zH[i]))*fai[i])**-0.5))
                else:
                    z0Mac = 0.
                X=(zSdev[i]+zH[i])/zMax[i]
                if (0<X<=1):
                    z_d_output[i] = ((Co*(X**2))+((((Ao*(pai[i]**Bo))-Co))*X))*zMax[i]
                else:
                    z_d_output[i] = (Ao*(pai[i]**Bo))*zH[i]
                Y = (pai[i]*zSdev[i])/zH[i]
                if Y >= 0:
                    z_0_output[i] = ((B1*(Y**2))+(C1*Y)+A1)*z0Mac
                else:
                    z_0_output[i] = A1*z0Mac
            else:
                z_d_output[i] = 0.
                z_0_output[i] = 0.
        elif Roughnessmethod == 'Mho':
            #Millward Hopkins
            #### MHO - Heterogenous - Displacement Height ####
            CD = 1.2
            CDD = 2
            k= 0.4
            #### Millward-Hopkins (2011)- Uniform with correction ####
            CD=1.2

            if pai[i] >=0.19:
                ZdMho_U = (((19.2*pai[i]) - 1 + (np.exp(-19.2*pai[i])))/((19.2*pai[i])*(1-(np.exp(-19.2*pai[i])))))*zH[i]
            elif pai[i] < 0.19:
                ZdMho_U = (((117*pai[i]) + ((187.2*(pai[i]**3))-6.1)*(1-np.exp(-19.2*pai[i])))/((1+(114*pai[i])+(187*pai[i]**3))*(1-(np.exp(-19.2*pai[i])))))*zH[i]
            ZoMhoexp_U = np.exp(-((0.5*CD*(k**-2)*fai[i])**-0.5))
            ZoMho_U=((1-(ZdMho_U/zH[i]))* ZoMhoexp_U)*zH[i]
            ZdMho_UCor=zH[i]*((ZdMho_U/zH[i])+((0.2375*np.log(pai[i])+1.1738)*(zSdev[i]/zH[i])))
            ZoMho_UCor= zH[i]*((ZoMho_U/zH[i])+ (np.exp((0.8867*fai[i])-1)*((zSdev[i]/zH[i])**np.exp(2.3271*fai[i]))))
            z_d_output[i] = ZdMho_UCor
            z_0_output[i] = ZoMho_UCor

    return(z_d_output, z_0_output)

def RoughnessCalc(Roughnessmethod,zH,fai,pai,zMax,zSdev):
    if Roughnessmethod == 'RT':
        #Rule of thumb method
        z_d_output = 0.7*zH
        z_0_output = 0.1*zH
    elif Roughnessmethod == 'Rau':
        ##### Raupach 1994/95 ####
        Cs=0.003
        Cr=0.3
        Stab=0.193
        UdivUmax=0.3
        Cdl=7.5
        k=0.4
        RauZdexpW=(math.exp(-((Cdl*2*fai)**0.5)))-1
        z_d_output= (1+ (RauZdexpW/((Cdl*2*fai)**0.5)))*zH
        RauZoUtermW = 1/(min(((Cs+(Cr*fai))**0.5), UdivUmax))
        RauZoexpW = np.exp((-k*RauZoUtermW)+Stab)
        z_0_output = ((1-(z_d_output/zH))*RauZoexpW)*zH
    elif Roughnessmethod == 'Bot':
        #Bottema
        Cdh = 0.8
        k=0.4
        z_d_output = (pai**0.6)*zH
        BotZoexpW =np.exp(-k/((0.5*fai*Cdh)**0.5))
        z_0_output = (zH - z_d_output)*(BotZoexpW)
    elif Roughnessmethod == 'Mac':
        #MacDonald
        Clb = 1.2
        k=0.4
        #Staggered array
        Alph = 4.43
        Beet = 1.0
        #Square array
        #Alph = 3.59
        #Beet = 0.55
        if zH > 0.:
            z_d_output = (1+((Alph**-pai)*(pai-1)))*zH
            if z_d_output != zH:
                z_0_output = (zH*((1-z_d_output/zH))*np.exp(-(0.5*(1.2/0.4**2)*(1-(z_d_output/zH))*fai)**-0.5))
            else:
                z_0_output = 0.
        else:
            z_0_output = 0.
            z_d_output = 0.
    elif Roughnessmethod == 'Kan':
        #Kanda
        Kanmeth = 1
        if Kanmeth == 1:
                Ao = 1.29
                Bo = 0.36
                Co = -0.17
                A1 = 0.71
                B1= 20.21
                C1 = -0.77
        elif Kanmeth == 2:
                Ao = 0.86
                Bo = 0.28
                Co = -0.18
                A1 = 0.93
                B1 = 8.93
                C1 = 4.68
        #First perform MacD method
        #MacDonald
        Clb = 1.2
        k=0.4
        #Staggered array
        Alph = 4.43
        Beet = 1.0
        #Square array
        #Alph = 3.59
        #Beet = 0.55
        if zH > 0.:
            z_d_output = (1+((Alph**-pai)*(pai-1)))*zH
            if z_d_output != zH:
                z0Mac= (zH*((1-z_d_output/zH))*np.exp(-(0.5*(1.2/0.4**2)*(1-(z_d_output/zH))*fai)**-0.5))
            else:
                z0Mac = 0.
            X=(zSdev+zH)/zMax
            if (0<X<=1):
                z_d_output = ((Co*(X**2))+((((Ao*(pai**Bo))-Co))*X))*zMax
            else:
                z_d_output = (Ao*(pai**Bo))*zH
            Y = (pai*zSdev)/zH
            if Y >= 0:
                z_0_output = ((B1*(Y**2))+(C1*Y)+A1)*z0Mac
            else:
                z_0_output = A1*z0Mac
        else:
            z_0_output = 0.
            z_d_output = 0.
    elif Roughnessmethod == 'Mho':
        #Millward Hopkins
        #### MHO - Heterogenous - Displacement Height ####
        CD = 1.2
        CDD = 2
        k= 0.4
        #### Millward-Hopkins (2011)- Uniform with correction ####
        CD=1.2

        if pai >=0.19:
            ZdMho_U = (((19.2*pai) - 1 + (np.exp(-19.2*pai)))/((19.2*pai)*(1-(np.exp(-19.2*pai)))))*zH
        elif pai < 0.19:
            ZdMho_U = (((117*pai) + ((187.2*(pai**3))-6.1)*(1-np.exp(-19.2*pai)))/((1+(114*pai)+(187*pai**3))*(1-(np.exp(-19.2*pai)))))*zH
        ZoMhoexp_U = np.exp(-((0.5*CD*(k**-2)*fai)**-0.5))
        if zH>0.:
            ZoMho_U=((1-(ZdMho_U/zH))* ZoMhoexp_U)*zH
            ZdMho_UCor=zH*((ZdMho_U/zH)+((0.2375*np.log(pai)+1.1738)*(zSdev/zH)))
            ZoMho_UCor= zH*((ZoMho_U/zH)+ (np.exp((0.8867*fai)-1)*((zSdev/zH)**np.exp(2.3271*fai))))
            z_d_output = ZdMho_UCor
            z_0_output = ZoMho_UCor
        else:
            z_0_output = 0.
            z_d_output = 0.
    return(z_d_output,z_0_output)