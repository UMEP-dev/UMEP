
def Kvikt_veg(svf,svfveg,vikttot):

    # Least
    viktwall=(vikttot-(63.227*svf**6-161.51*svf**5+156.91*svf**4-70.424*svf**3+16.773*svf**2-0.4863*svf))/vikttot
    
    svfvegbu=(svfveg+svf-1)  # Vegetation plus buildings
    viktveg=(vikttot-(63.227*svfvegbu**6-161.51*svfvegbu**5+156.91*svfvegbu**4-70.424*svfvegbu**3+16.773*svfvegbu**2-0.4863*svfvegbu))/vikttot
    viktveg=viktveg-viktwall
    
    return viktveg,viktwall