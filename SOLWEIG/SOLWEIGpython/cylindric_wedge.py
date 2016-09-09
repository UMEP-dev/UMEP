import numpy as np

def cylindric_wedge(zen, svfalfa, rows, cols):

    # Fraction of sunlit walls based on sun altitude and svf wieghted building angles
    # input: 
    # sun zenith angle "beta"
    # svf related angle "alfa"

    beta=zen
    alfa=svfalfa
    
    # measure the size of the image
    # sizex=size(svfalfa,2)
    # sizey=size(svfalfa,1)
    
    xa=1-2./(np.tan(alfa)*np.tan(beta))
    ha=2./(np.tan(alfa)*np.tan(beta))
    ba=(1./np.tan(alfa))
    hkil=2.*ba*ha
    
    qa=np.zeros((rows, cols))
    # qa(length(svfalfa),length(svfalfa))=0;
    qa[xa<0]=np.tan(beta)/2
    
    Za=np.zeros((rows, cols))
    # Za(length(svfalfa),length(svfalfa))=0;
    Za[xa<0]=((ba[xa<0]**2)-((qa[xa<0]**2)/4))**0.5
    
    phi=np.zeros((rows, cols))
    #phi(length(svfalfa),length(svfalfa))=0;
    phi[xa<0]=np.arctan(Za[xa<0]/qa[xa<0])
    
    A=np.zeros((rows, cols))
    # A(length(svfalfa),length(svfalfa))=0;
    A[xa<0]=(np.sin(phi[xa<0])-phi[xa<0]*np.cos(phi[xa<0]))/(1-np.cos(phi[xa<0]))
    
    ukil=np.zeros((rows, cols))
    # ukil(length(svfalfa),length(svfalfa))=0
    ukil[xa<0]=2*ba[xa<0]*xa[xa<0]*A[xa<0]
    
    Ssurf=hkil+ukil
    
    F_sh=(2*np.pi*ba-Ssurf)/(2*np.pi*ba)#Xa
    
    return F_sh