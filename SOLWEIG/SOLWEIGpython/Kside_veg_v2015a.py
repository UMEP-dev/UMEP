from __future__ import absolute_import
import numpy as np
from .Kvikt_veg import Kvikt_veg

def Kside_veg_v2015a(radI,radD,radG,shadow,svfS,svfW,svfN,svfE,svfEveg,svfSveg,svfWveg,svfNveg,azimuth,altitude,psi,t,albedo,F_sh,KupE,KupS,KupW,KupN,cyl):

    # New reflection equation 2012-05-25
    vikttot=4.4897
    aziE=azimuth+t
    aziS=azimuth-90+t
    aziW=azimuth-180+t
    aziN=azimuth-270+t
    deg2rad=np.pi/180
    
    ### Direct radiation ###
    if cyl == 1: ### Kside with cylinder ###
        KsideI=shadow*radI*0.28*np.cos(altitude*deg2rad)
        KeastI=0;KsouthI=0;KwestI=0;KnorthI=0
    else: ### Kside with weights ###
        if azimuth > (360-t)  or  azimuth <= (180-t):
            KeastI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziE*deg2rad)
            #radD*(1-svfviktbuveg)+albedo*svfviktbuveg.*(radG*(1-F_sh)+radD*(F_sh));  OLD
            #radD*(1-svfviktbuveg)+radG*albedo*svfviktbuveg.*(1-F_sh);#*sin(altitude*(pi/180)); OLDER
        else:
            KeastI=0
        if azimuth > (90-t)  and  azimuth <= (270-t):
            KsouthI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziS*deg2rad)
        else:
            KsouthI=0
        if azimuth > (180-t)  and  azimuth <= (360-t):
            KwestI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziW*deg2rad)
        else:
            KwestI=0
        if azimuth <= (90-t)  or  azimuth > (270-t):
            KnorthI=radI*shadow*np.cos(altitude*deg2rad)*np.sin(aziN*deg2rad)
        else:
            KnorthI=0

        KsideI=shadow*0
    
    ### Diffuse and reflected radiation ###
    [viktveg,viktwall]=Kvikt_veg(svfE,svfEveg,vikttot)
    svfviktbuveg=(viktwall+(viktveg)*(1-psi))
    KeastDG=(radD*(1-svfviktbuveg)+albedo*(svfviktbuveg*(radG*(1-F_sh)+radD*F_sh))+KupE)*0.5
    Keast=KeastI+KeastDG
    
    [viktveg,viktwall]=Kvikt_veg(svfS,svfSveg,vikttot)
    svfviktbuveg=(viktwall+(viktveg)*(1-psi))
    KsouthDG=(radD*(1-svfviktbuveg)+albedo*(svfviktbuveg*(radG*(1-F_sh)+radD*F_sh))+KupS)*0.5
    Ksouth=KsouthI+KsouthDG
    
    [viktveg,viktwall]=Kvikt_veg(svfW,svfWveg,vikttot)
    svfviktbuveg=(viktwall+(viktveg)*(1-psi))
    KwestDG=(radD*(1-svfviktbuveg)+albedo*(svfviktbuveg*(radG*(1-F_sh)+radD*F_sh))+KupW)*0.5
    Kwest=KwestI+KwestDG
    
    [viktveg,viktwall]=Kvikt_veg(svfN,svfNveg,vikttot)
    svfviktbuveg=(viktwall+(viktveg)*(1-psi))
    KnorthDG=(radD*(1-svfviktbuveg)+albedo*(svfviktbuveg*(radG*(1-F_sh)+radD*F_sh))+KupN)*0.5
    Knorth=KnorthI+KnorthDG
    
    return Keast,Ksouth,Kwest,Knorth,KsideI