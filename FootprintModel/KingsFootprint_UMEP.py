####################### FOOTPRINT MODEL WITH ITERATIONS TO CALC NEW ZO AND ZD #######################################
#%Date: 22 October 2015                                                                                            %#
#%Author:                                                                                                          %#
#%   Kent, C.                                                                                                      %#
#%   PhD Student at Reading Meteorology Dept.                                                                      %#
#%   Coding of Korman and Meixner (2001) analytical footprint model                                                %#
#%   This script is built for UMEP to employ FPR model around central point                                        %#
#####################################################################################################################

####Import packages####
# import netCDF4 as netCDF4
# import matplotlib.pylab as plt
# import matplotlib.image as mpimg
# from PIL import Image
import numpy as np
import math as math
import scipy.misc as sc
# from scipy.ndimage.interpolation import rotate as imrotate
# from matplotlib.patches import Circle
from scipy.optimize import fsolve
# import copy as copy
import scipy.ndimage.interpolation as scnd
from osgeo import gdal
from osgeo.gdalconst import *
from ..Utilities import RoughnessCalcFunctionV2 as rg


##1 - Kormann and Mexiner (2001) model functions

##### {Running of KM model} ####
def footprintiterKAM(iterations,z_0_input,z_d_input,z_ag,sigv,Obukhov,ustar,dir,porosity,bld,veg,rows,cols,res,dlg,maxfetch,rm):

    dlg.progressBar.setRange(0, iterations)
    dlg.progressBar.setValue(0)
    scale = 1. / res
    maxfetch = maxfetch * scale
    domain_y = np.round(maxfetch / 2.)  # pixels ?
    domain_x = np.round(maxfetch)  # pixels ?
    domain_output = maxfetch * 2  # in meters
    d_input = res # meters

    # g=9.8
    k=0.4

    totRotatedphi = np.zeros((rows, cols))
    Wfai=np.zeros((iterations,1))
    Wpai=np.zeros((iterations,1))
    WzH=np.zeros((iterations,1))
    WzMax=np.zeros((iterations,1))
    WzSdev=np.zeros((iterations,1))
    Wfaiveg=np.zeros((iterations,1))
    Wpaiveg=np.zeros((iterations,1))
    WzHveg=np.zeros((iterations,1))
    WzMaxveg=np.zeros((iterations,1))
    WzSdevveg=np.zeros((iterations,1))
    Wfaibuild=np.zeros((iterations,1))
    Wpaibuild=np.zeros((iterations,1))
    WzHbuild=np.zeros((iterations,1))
    WzMaxbuild=np.zeros((iterations,1))
    WzSdevbuild=np.zeros((iterations,1))
    Wz_d_output=np.zeros((iterations,1))
    Wz_0_output=np.zeros((iterations,1))
    Wz_m_output=np.zeros((iterations,1))
    phi_maxdist=np.zeros((iterations,1))
    phi_totdist =np.zeros((iterations,1))

    for i in np.arange(0,iterations,1):
        dlg.progressBar.setValue(i + 1)
        z_0 = z_0_input[i]
        z_d = z_d_input[i]
        z_m = z_ag[i] - z_d_input[i]
        sig_v_input = sigv[i]
        L = Obukhov[i]
        u_star = ustar[i]
        wd_input=dir[i]
        por = porosity[i]


        ###Bounds of integration for equation 42 tp 46 defined on pg 218### {X1}
        z_1=3.0*z_0
        z_2=(1+k)*z_m
        z = np.linspace(z_1/z_m,z_2/z_m,999)

        ###Implementation of root finding for eqn 39 & 40###
        ##Fequ_m formulation but optimized for python {X2} {J} ##EQUATION 39
        fequ_m= lambda m: (I_1(2.*m,z_1,z_2,z_m)*(I_3(m,z_0/z_m,z_1,z_2,z_m)+J_2(m,z_1,z_2,z_m,L,f_psi_m(z*z_m,z_m,L))))-(I_2(2.*m,1,z_1,z_2,z_m)*(I_2(2.*m,z_0/z_m,z_1,z_2,z_m)+ J_1(m,z_1,z_2,z_m,L,f_psi_m(z*z_m,z_m,L))))
        m = fsolve(fequ_m,0.2)

        ##fequ_n formulation but optimized for python {X3} {K} ##EQUATION 40
        fequ_n = lambda n: I_1(2.*n,z_1,z_2,z_m)*J_2(n,z_1,z_2,z_m,L,f_z_phi_c(z*z_m,z_m,L)) - I_2(2.*n,1,z_1,z_2,z_m)*J_1(n,z_1,z_2,z_m,L,f_z_phi_c(z*z_m,z_m,L))
        n = fsolve(fequ_n,0.5)      #solve when fequ_n falls to zero with starting guess of 0.5

        ##Option to work out ustar as an algorithm of wind with rearrangement of log wind profile if observations are not present   ##EQUATION 31 {X4..}
        #u_star = u* (k/(np.log(z_m/z_0)+psi_m(z_m,L)))

        #Calculation of U constant EQUATION 41 {X5}
        U = (u_star/k) * ((I_2(m,z_0/z_m,z_1,z_2,z_m) + J_1(m,z_1,z_2,z_m,L,f_psi_m(z*z_m,z_m,L)))/ (I_1(2.*m,z_1,z_2,z_m)*(z_m**m)))
        #Calculation of Kappa constant EQUATION 41 {X6}
        kappa= (k*u_star)*(J_1(n,z_1,z_2,z_m,L,f_z_phi_c(z*z_m,z_m,L))/(I_1(2.*n,z_1,z_2,z_m)*(z_m**(n-1))))


        #Definition of the grid over which footpint phi is going to be calculated over (xspace,yspace,2dimensions). {X7}
        d=d_input                                   #resolution therefore dimensionality
        domain_x = domain_x * d
        domain_y = domain_y * d
        xs=np.arange(d,domain_x+d,d)
        ys=np.arange(-domain_y,domain_y+d,d)

        x = np.zeros([len(xs),len(ys),2])

        for j in np.arange(0,(len(xs)-1),1):
            x[:,j,0]=xs
        for j in np.arange(0,len(ys)-1,1):
            x[j,:,1]=ys

        #Cross wind integrated footprint {x8}
        # r is defined at top of pg 213, mu after eqn 18
        r = 2.+m-n
        mu= (1.+ m)/r
        #EQUATION 19
        xsi=(U*(z_m**r))/((r**2)*kappa)
        #xsix
        exc = -xsi/x[:,:,0]
        #EQUATION 21
        f= (math.gamma(mu)**-1)*((xsi**mu)/(x[:,:,0]**(1+mu)))*np.exp(exc)

        #Cross wind diffusion {X9}
        #EQUATION 18
        u_bar=(math.gamma(mu)/math.gamma(1./r))*((((r**2)*kappa)/U)**(m/r))*(U*(x[:,:,0]**(m/r)))
        #EQUATION 9, sig definition right after it
        sig = (sig_v_input*x[:,:,0])/u_bar
        inm = (-x[:,:,1]**2)/(2.*(sig**2))
        D_y=((np.sqrt(2.*math.pi)*sig)**(-1))*np.exp(inm)
        #EQUATION 8 & Get phi into plot compatible
        phi= D_y*f
        phi[np.isnan(phi)]=0

        #Re-shape into gridded form
        phi=np.reshape((phi*(d**2)),(len(xs),len(ys)))
        D_y=np.reshape((D_y*d),(len(xs),len(ys)))
        f=np.reshape((f*d),(len(xs),len(ys)))

        #PAD and ROTATE
        #Extract distance of max footprint
        ixs = np.where(f[:,1] == np.nanmax(f[:,1]))
        x_distance = x[:,:,0]
        x_max = x_distance[ixs[0]]

        #PAD and rotate footprint
        ##Paddington it up to the defined domain_output (default = 2km x 2km)
        fx=int(domain_output)
        domain_x = domain_x / d_input
        domain_y = domain_y / d_input
        fy = fx
        full = np.zeros([fx, fy])
        full[(fx+1)/2:int((fx+1)/2+(domain_x)),int((fy/2+1)-domain_y):int((fy/2+1)+domain_y+1)]=phi
        full[np.isnan(full)]=0

        ##Rotation for wind angle for absolute plot and correction for rotation algorithm
        rotang =180-wd_input
        rotatedphi = scnd.rotate(full, rotang, order =0, reshape=False, mode='nearest')

        totRotatedphi = totRotatedphi + rotatedphi

        #Calculate weighted morphometry and therefore weighted zo and zd
        Wfai[i],Wpai[i],WzH[i],WzMax[i],WzSdev[i],Wfaiveg[i],Wpaiveg[i],WzHveg[i],WzMaxveg[i],WzSdevveg[i],Wfaibuild[i],Wpaibuild[i],WzHbuild[i],WzMaxbuild[i],WzSdevbuild[i] = CalcWeightedMorphVegV2(bld=bld,veg=veg,porosity = por, rotatedphi=rotatedphi,wd_input=wd_input,scale=1/d_input)
        Wz_d_output[i], Wz_0_output[i] = rg.RoughnessCalc(zH=WzH[i],fai=Wfai[i],pai=Wpai[i],zMax=WzMax[i],zSdev=WzSdev[i],Roughnessmethod=rm)

        Wz_m_output[i] = z_ag[i] - Wz_d_output[i]

    return(totRotatedphi,Wz_d_output,Wz_0_output,Wz_m_output,phi_maxdist,phi_totdist,Wfai,Wpai,WzH,WzMax,WzSdev,Wfaiveg,Wpaiveg,WzHveg,WzMaxveg,WzSdevveg,Wfaibuild,Wpaibuild,WzHbuild,WzMaxbuild,WzSdevbuild)


#### Functions required for model operation Korman and Meixner (2001) ####
##define  psi_m {A} ##EQUATION 35
def psi_m(z,L):
    if L > 0:
        phi_m = 5.*z/L
    else:
        zeta = (1.-16. * z/L)**(1./4.)
        phi_m=(-2.)*np.log((1+zeta)/2)-np.log((1+zeta**2)/2)+(2*np.arctan(zeta))-(np.pi/2)
    return phi_m
#def_phi_c {B} ##EQUATION 34
def phi_c(z,L):
    if L > 0:
        phi_c = 1.+5.*z/L
    else:
        phi_c = ((1.-(16. * (z/L)))**(-1./2.))
    return phi_c
#function I_1 {C} ## EQUATION 42
def I_1(p,z_1,z_2,z_m):
    z = np.linspace(z_1/z_m,z_2/z_m,1000)
    dz = np.diff(z)
    z=z[0:(len(z)-1)]+dz/2
    d=np.sum((z**p)*dz)
    return d
##function I_2 {D} ##EQUATION 43
def I_2(p,z0,z_1,z_2,z_m):
    z = np.linspace(z_1/z_m,z_2/z_m,1000)
    dz = np.diff(z)
    z=z[0:(len(z)-1)]+dz/2
    d=np.sum((z**p)*np.log(z/z0)*dz)
    return d
##function I_3 {E} ##EQUATION 44
def I_3(p,z0,z_1,z_2,z_m):
    z = np.linspace(z_1/z_m,z_2/z_m,1000)
    dz = np.diff(z)
    z=z[0:(len(z)-1)]+dz/2
    d=np.sum((z**p)*np.log(z)*np.log(z/z0)*dz)        #z0
    return d
##function J_1 {F2} #EQUATION 45     (for use in equation 40)
def J_1(p,z_1,z_2,z_m,L,fun):
    z = np.linspace(z_1/z_m,z_2/z_m,1000)
    dz = np.diff(z)
    z=z[0:(len(z)-1)]+dz/2
    d=np.sum((z**p)*fun*dz)
    return d
##function J_2 {G2} #EQUATION 46    (for use in equation 40)
def J_2(p,z_1,z_2,z_m,L,fun):
    z = np.linspace(z_1/z_m,z_2/z_m,1000)
    dz = np.diff(z)
    z=z[0:(len(z)-1)]+dz/2
    d=np.sum((z**p)*fun*np.log(z)*dz)
    return d

####Functions that are arguments of J_1 and J_2
#{H}
def f_psi_m(z,z_m,L):
    d = psi_m(z,L)
    return d
#{I}
def f_z_phi_c(z,z_m,L):
    d = z/(phi_c(z,L)*z_m)
    return d


##2 - Klujn et al. (2015) model functions
#### {Running of Klukn model} ####
def footprintiterKLJ(iterations,z_0_input,z_d_input,z_ag,sigv,Obukhov,ustar,dir,porosity,h,bld,veg,rows,cols,res,dlg,maxfetch,rm):

    dlg.progressBar.setRange(0, iterations)
    dlg.progressBar.setValue(0)
    domain_output_inm = maxfetch*2.
    domain_output_inpix = domain_output_inm/res

    moddomain_inm = ([-maxfetch,maxfetch,-maxfetch,maxfetch])


    totRotatedphi = np.zeros((int(domain_output_inpix),int(domain_output_inpix)))
    Wfai=np.zeros((iterations,1))
    Wpai=np.zeros((iterations,1))
    WzH=np.zeros((iterations,1))
    WzMax=np.zeros((iterations,1))
    WzSdev=np.zeros((iterations,1))
    Wfaiveg=np.zeros((iterations,1))
    Wpaiveg=np.zeros((iterations,1))
    WzHveg=np.zeros((iterations,1))
    WzMaxveg=np.zeros((iterations,1))
    WzSdevveg=np.zeros((iterations,1))
    Wfaibuild=np.zeros((iterations,1))
    Wpaibuild=np.zeros((iterations,1))
    WzHbuild=np.zeros((iterations,1))
    WzMaxbuild=np.zeros((iterations,1))
    WzSdevbuild=np.zeros((iterations,1))
    Wz_d_output=np.zeros((iterations,1))
    Wz_0_output=np.zeros((iterations,1))
    Wz_m_output=np.zeros((iterations,1))
    phi_maxdist=np.zeros((iterations,1))
    phi_totdist =np.zeros((iterations,1))

    for i in np.arange(0,iterations,1):
        dlg.progressBar.setValue(i + 1)
        z_0 = z_0_input[i]
        z_d = z_d_input[i]
        z_m = z_ag[i] - z_d_input[i]
        sig_v = sigv[i]
        L = Obukhov[i]
        u_star = ustar[i]
        wd_input=dir[i]
        por = porosity[i]
        hbl = h[i]

        FFP = FFP_climatology(zm=z_m, z0=z_0, umean=None, h=hbl, ol=L, sigmav=sig_v, ustar=u_star,
                    wind_dir=wd_input, domain=moddomain_inm,dx=res,dy=res,rs=None, rslayer=1,smooth_data=0)
        phi = FFP['fclim_2d']

        #Return distance where footprint is max contribution (in pixels)
        phi_maxdist[i] = np.argmax(phi[:, int(maxfetch / res)])
        #Return distance of maximum footprint extent (in pixels)
        phi_totdist[i] = (phi_maxdist[i] + np.nansum((phi[int(phi_maxdist[i]):int(len(phi)), int((len(phi) / 2))] > 0)))            #Flip Klj for wind angle
        rotatedphi = np.flipud(phi)
        rotatedphi=rotatedphi[0:int(domain_output_inpix),0:int(domain_output_inpix)]

        totRotatedphi = totRotatedphi + rotatedphi

        Wfai[i],Wpai[i],WzH[i],WzMax[i],WzSdev[i],Wfaiveg[i],Wpaiveg[i],WzHveg[i],WzMaxveg[i],WzSdevveg[i],Wfaibuild[i],Wpaibuild[i],WzHbuild[i],WzMaxbuild[i],WzSdevbuild[i] = CalcWeightedMorphVegV2(bld=bld,veg=veg,porosity = por, rotatedphi=rotatedphi,wd_input=wd_input,scale=1./res)
        Wz_d_output[i], Wz_0_output[i] = rg.RoughnessCalc(zH=WzH[i],fai=Wfai[i],pai=Wpai[i],zMax=WzMax[i],zSdev=WzSdev[i],Roughnessmethod=rm)

        Wz_m_output[i] = z_ag[i] - Wz_d_output[i]

    return(totRotatedphi,Wz_d_output,Wz_0_output,Wz_m_output,phi_maxdist,phi_totdist,Wfai,Wpai,WzH,WzMax,WzSdev,Wfaiveg,Wpaiveg,WzHveg,WzMaxveg,WzSdevveg,Wfaibuild,Wpaibuild,WzHbuild,WzMaxbuild,WzSdevbuild)


#### {Functions for Klj model} ####
def FFP_climatology(zm=None, z0=None, umean=None, h=None, ol=None, sigmav=None, ustar=None,
                    wind_dir=None, domain=None, dx=None, dy=None, nx=None, ny=None,
                    rs=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], rslayer=0,
                    smooth_data=1, crop=False, pulse=None, verbosity=2):
    """
    Derive a flux footprint estimate based on the simple parameterisation FFP
    See Kljun, N., P. Calanca, M.W. Rotach, H.P. Schmid, 2015:
    The simple two-dimensional parameterisation for Flux Footprint Predictions FFP.
    Geosci. Model Dev. 8, 3695-3713, doi:10.5194/gmd-8-3695-2015, for details.
    contact: n.kljun@swansea.ac.uk

    This function calculates footprints within a fixed physical domain for a series of
    time steps, rotates footprints into the corresponding wind direction and aggregates
    all footprints to a footprint climatology. The percentage of source area is
    calculated for the footprint climatology.
    For determining the optimal extent of the domain (large enough to include footprints)
    use calc_footprint_FFP.py.

    FFP Input
        All vectors need to be of equal length (one value for each time step)
        zm       = Measurement height above displacement height (i.e. z-d) [m]
                   usually a scalar, but can also be a vector
        z0       = Roughness length [m] - enter [None] if not known
                   usually a scalar, but can also be a vector
        umean    = Vector of mean wind speed at zm [ms-1] - enter [None] if not known
                   Either z0 or umean is required. If both are given,
                   z0 is selected to calculate the footprint
        h        = Vector of boundary layer height [m]
        ol       = Vector of Obukhov length [m]
        sigmav   = Vector of standard deviation of lateral velocity fluctuations [ms-1]
        ustar    = Vector of friction velocity [ms-1]
        wind_dir = Vector of wind direction in degrees (of 360) for rotation of the footprint

        Optional input:
        domain       = Domain size as an array of [xmin xmax ymin ymax] [m].
                       Footprint will be calculated for a measurement at [0 0 zm] m
                       Default is smallest area including the r% footprint or [-1000 1000 -1000 1000]m,
                       whichever smallest (80% footprint if r not given).
        dx, dy       = Cell size of domain [m]
                       Small dx, dy results in higher spatial resolution and higher computing time
                       Default is dx = dy = 2 m. If only dx is given, dx=dy.
        nx, ny       = Two integer scalars defining the number of grid elements in x and y
                       Large nx/ny result in higher spatial resolution and higher computing time
                       Default is nx = ny = 1000. If only nx is given, nx=ny.
                       If both dx/dy and nx/ny are given, dx/dy is given priority if the domain is also specified.
        rs           = Percentage of source area for which to provide contours, must be between 10% and 90%.
                       Can be either a single value (e.g., "80") or a list of values (e.g., "[10, 20, 30]")
                       Expressed either in percentages ("80") or as fractions of 1 ("0.8").
                       Default is [10:10:80]. Set to "None" for no output of percentages
        rslayer      = Calculate footprint even if zm within roughness sublayer: set rslayer = 1
                       Note that this only gives a rough estimate of the footprint as the model is not
                       valid within the roughness sublayer. Default is 0 (i.e. no footprint for within RS).
                       z0 is needed for estimation of the RS.
        smooth_data  = Apply convolution filter to smooth footprint climatology if smooth_data=1 (default)
        crop         = Crop output area to size of the 80% footprint or the largest r given if crop=1
        pulse        = Display progress of footprint calculations every pulse-th footprint (e.g., "100")
        verbosity    = Level of verbosity at run time: 0 = completely silent, 1 = notify only of fatal errors,
                       2 = all notifications
    FFP output
        FFP      = Structure array with footprint climatology data for measurement at [0 0 zm] m
        x_2d	    = x-grid of 2-dimensional footprint [m]
        y_2d	    = y-grid of 2-dimensional footprint [m]
        fclim_2d = Normalised footprint function values of footprint climatology [m-2]
        rs       = Percentage of footprint as in input, if provided
        fr       = Footprint value at r, if r is provided
        xr       = x-array for contour line of r, if r is provided
        yr       = y-array for contour line of r, if r is provided
        n        = Number of footprints calculated and included in footprint climatology
        flag_err = 0 if no error, 1 in case of error, 2 if not all contour plots (rs%) within specified domain


    Created: 19 May 2016 natascha kljun
    Converted from matlab to python, together with Gerardo Fratini, LI-COR Biosciences Inc.
    version: 1.22
    last change: 01/10/2016 natascha kljun
    Copyright (C) 2015, Natascha Kljun
    """

    import numpy as np
    import sys
    import numbers
    from scipy import signal as sg


    #===========================================================================
    # Input check
    flag_err = 0

    # Check existence of required input pars
    if None in [zm, h, ol, sigmav, ustar] or (z0 is None and umean is None):
        raise_ffp_exception(1, verbosity)

    # Convert all input items to lists
    if not isinstance(zm, list): zm = [zm]
    if not isinstance(h, list): h = [h]
    if not isinstance(ol, list): ol = [ol]
    if not isinstance(sigmav, list): sigmav = [sigmav]
    if not isinstance(ustar, list): ustar = [ustar]
    if not isinstance(wind_dir, list): wind_dir = [wind_dir]
    if not isinstance(z0, list): z0 = [z0]
    if not isinstance(umean, list): umean = [umean]

    # Check that all lists have same length, if not raise an error and exit
    ts_len = len(ustar)
    if any(len(lst) != ts_len for lst in [sigmav, wind_dir, h, ol]):
        # at least one list has a different length, exit with error message
        raise_ffp_exception(11, verbosity)

    # Special treatment for zm, which is allowed to have length 1 for any
    # length >= 1 of all other parameters
    if all(val is None for val in zm): raise_ffp_exception(12, verbosity)
    if len(zm) == 1:
        raise_ffp_exception(17, verbosity)
        zm = [zm[0] for i in range(ts_len)]

    # Resolve ambiguity if both z0 and umean are passed (defaults to using z0)
    # If at least one value of z0 is passed, use z0 (by setting umean to None)
    if not all(val is None for val in z0):
        raise_ffp_exception(13, verbosity)
        umean = [None for i in range(ts_len)]
        # If only one value of z0 was passed, use that value for all footprints
        if len(z0) == 1: z0 = [z0[0] for i in range(ts_len)]
    elif len(umean) == ts_len and not all(val is None for val in umean):
        raise_ffp_exception(14, verbosity)
        z0 = [None for i in range(ts_len)]
    else:
        raise_ffp_exception(15, verbosity)

    # Rename lists as now the function expects time series of inputs
    ustars, sigmavs, hs, ols, wind_dirs, zms, z0s, umeans = \
            ustar, sigmav, h, ol, wind_dir, zm, z0, umean

    #===========================================================================
    # Handle rs
    if rs is not None:

        # Check that rs is a list, otherwise make it a list
        if isinstance(rs, numbers.Number):
            if 0.9 < rs <= 1 or 90 < rs <= 100: rs = 0.9
            rs = [rs]
        if not isinstance(rs, list): raise_ffp_exception(18, verbosity)

        # If rs is passed as percentages, normalize to fractions of one
        if np.max(rs) >= 1: rs = [x/100. for x in rs]

        # Eliminate any values beyond 0.9 (90%) and inform user
        if np.max(rs) > 0.9:
            raise_ffp_exception(19, verbosity)
            rs = [item for item in rs if item <= 0.9]

        # Sort levels in ascending order
        rs = list(np.sort(rs))

    #===========================================================================
    # Define computational domain
    # Check passed values and make some smart assumptions
    if isinstance(dx, numbers.Number) and dy is None: dy = dx
    if isinstance(dy, numbers.Number) and dx is None: dx = dy
    if not all(isinstance(item, numbers.Number) for item in [dx, dy]): dx = dy = None
    if isinstance(nx, int) and ny is None: ny = nx
    if isinstance(ny, int) and nx is None: nx = ny
    if not all(isinstance(item, int) for item in [nx, ny]): nx = ny = None
    if not isinstance(domain, list) or len(domain) != 4: domain = None

    if all(item is None for item in [dx, nx, domain]):
        # If nothing is passed, default domain is a square of 2 Km size centered
        # at the tower with pizel size of 2 meters (hence a 1000x1000 grid)
        domain = [-1000., 1000., -1000., 1000.]
        dx = dy = 2.
        nx = ny = 1000
    elif domain is not None:
        # If domain is passed, it takes the precendence over anything else
        if dx is not None:
            # If dx/dy is passed, takes precendence over nx/ny
            nx = int((domain[1]-domain[0]) / dx)
            ny = int((domain[3]-domain[2]) / dy)
        else:
            # If dx/dy is not passed, use nx/ny (set to 1000 if not passed)
            if nx is None: nx = ny = 1000
            # If dx/dy is not passed, use nx/ny
            dx = (domain[1]-domain[0]) / float(nx)
            dy = (domain[3]-domain[2]) / float(ny)
    elif dx is not None and nx is not None:
        # If domain is not passed but dx/dy and nx/ny are, define domain
        domain = [-nx*dx/2, nx*dx/2, -ny*dy/2, ny*dy/2]
    elif dx is not None:
        # If domain is not passed but dx/dy is, define domain and nx/ny
        domain = [-1000, 1000, -1000, 1000]
        nx = int((domain[1]-domain[0]) / dx)
        ny = int((domain[3]-domain[2]) / dy)
    elif nx is not None:
        # If domain and dx/dy are not passed but nx/ny is, define domain and dx/dy
        domain = [-1000, 1000, -1000, 1000]
        dx = (domain[1]-domain[0]) / float(nx)
        dy = (domain[3]-domain[2]) / float(nx)

    # Put domain into more convenient vars
    xmin, xmax, ymin, ymax = domain

    # Define rslayer if not passed
    if rslayer == None: rslayer == 0

    # Define smooth_data if not passed
    if smooth_data == None: smooth_data == 1

    # Define pulse if not passed
    if pulse == None:
        if ts_len <= 20:
            pulse = 1
        else:
            pulse = int(ts_len / 20)

    #===========================================================================
    # Model parameters
    a = 1.4524
    b = -1.9914
    c = 1.4622
    d = 0.1359
    ac = 2.17
    bc = 1.66
    cc = 20.0

    oln = 5000 #limit to L for neutral scaling
    k = 0.4 #von Karman

    #===========================================================================
    # Define physical domain in cartesian and polar coordinates
    # Cartesian coordinates
    x = np.linspace(xmin, xmax, nx + 1)
    y = np.linspace(ymin, ymax, ny + 1)
    x_2d, y_2d = np.meshgrid(x, y)

    # Polar coordinates
    # Set theta such that North is pointing upwards and angles increase clockwise
    rho = np.sqrt(x_2d**2 + y_2d**2)
    theta = np.arctan2(x_2d, y_2d)

    # initialize raster for footprint climatology
    fclim_2d = np.zeros(x_2d.shape)

    #===========================================================================
    # Loop on time series

    # Initialize logic array valids to those 'timestamps' for which all inputs are
    # at least present (but not necessarily phisically plausible)
    valids = [True if not any([val is None for val in vals]) else False \
              for vals in zip(ustars, sigmavs, hs, ols, wind_dirs, zms)]

    if verbosity > 1: print ''
    for ix, (ustar, sigmav, h, ol, wind_dir, zm, z0, umean) \
            in enumerate(zip(ustars, sigmavs, hs, ols, wind_dirs, zms, z0s, umeans)):

        # Counter
        if verbosity > 1 and ix % pulse == 0:
            print 'Calculating footprint ', ix+1, ' of ', ts_len

        valids[ix] = check_ffp_inputs(ustar, sigmav, h, ol, wind_dir, zm, z0, umean, rslayer, verbosity)

        # If inputs are not valid, skip current footprint
        if not valids[ix]:
            raise_ffp_exception(16, verbosity)
        else:
            #===========================================================================
            # Rotate coordinates into wind direction
            if wind_dir is not None:
                rotated_theta = theta - wind_dir * np.pi / 180.

            #===========================================================================
            # Create real scale crosswind integrated footprint and dummy for
            # rotated scaled footprint
            fstar_ci_dummy = np.zeros(x_2d.shape)
            f_ci_dummy = np.zeros(x_2d.shape)
            if z0 is not None:
                # Use z0
                if ol <= 0 or ol >= oln:
                    xx = (1 - 19.0 * zm/ol)**0.25
                    psi_f = (np.log((1 + xx**2) / 2.) + 2. * np.log((1 + xx) / 2.) - 2. * np.arctan(xx) + np.pi/2)
                elif ol > 0 and ol < oln:
                    psi_f = -5.3 * zm / ol
                if (np.log(zm / z0)-psi_f)>0:
                    xstar_ci_dummy = (rho * np.cos(rotated_theta) / zm * (1. - (zm / h)) / (np.log(zm / z0) - psi_f))
                    px = np.where(xstar_ci_dummy > d)
                    fstar_ci_dummy[px] = a * (xstar_ci_dummy[px] - d)**b * np.exp(-c / (xstar_ci_dummy[px] - d))
                    f_ci_dummy[px] = (fstar_ci_dummy[px] / zm * (1. - (zm / h)) / (np.log(zm / z0) - psi_f))
                else:
                    flag_err = 1
            else:
                # Use umean if z0 not available
                xstar_ci_dummy = (rho * np.cos(rotated_theta) / zm * (1. - (zm / h)) / (umean / ustar * k))
                px = np.where(xstar_ci_dummy > d)
                fstar_ci_dummy[px] = a * (xstar_ci_dummy[px] - d)**b * np.exp(-c / (xstar_ci_dummy[px] - d))
                f_ci_dummy[px] = (fstar_ci_dummy[px] / zm * (1. - (zm / h)) / (umean / ustar * k))

            #===========================================================================
            # Calculate dummy for scaled sig_y* and real scale sig_y
            sigystar_dummy = np.zeros(x_2d.shape)
            sigystar_dummy[px] = (ac * np.sqrt(bc * np.abs(xstar_ci_dummy[px])**2 / (1 +
                                  cc * np.abs(xstar_ci_dummy[px]))))

            if abs(ol) > oln:
                ol = -1E6
            if ol <= 0:   #convective
                scale_const = 1E-5 * abs(zm / ol)**(-1) + 0.80
            elif ol > 0:  #stable
                scale_const = 1E-5 * abs(zm / ol)**(-1) + 0.55
            if scale_const > 1:
                scale_const = 1.0

            sigy_dummy = np.zeros(x_2d.shape)
            sigy_dummy[px] = (sigystar_dummy[px] / scale_const * zm * sigmav / ustar)
            sigy_dummy[sigy_dummy < 0] = np.nan

            #===========================================================================
            # Calculate real scale f(x,y)
            f_2d = np.zeros(x_2d.shape)
            f_2d[px] = (f_ci_dummy[px] / (np.sqrt(2 * np.pi) * sigy_dummy[px]) *
                        np.exp(-(rho[px] * np.sin(rotated_theta[px]))**2 / ( 2. * sigy_dummy[px]**2)))

            #===========================================================================
            # Add to footprint climatology raster
            fclim_2d = fclim_2d + f_2d;

    #===========================================================================
    # Continue if at least one valid footprint was calculated
    n = sum(valids)
    vs = None
    clevs = None
    if n==0:
        print "No footprint calculated"
        flag_err = 1
    else:

        #===========================================================================
        # Normalize and smooth footprint climatology
        fclim_2d = fclim_2d / n;

        if smooth_data is not None:
            skernel  = np.matrix('0.05 0.1 0.05; 0.1 0.4 0.1; 0.05 0.1 0.05')
            fclim_2d = sg.convolve2d(fclim_2d,skernel,mode='same');
            fclim_2d = sg.convolve2d(fclim_2d,skernel,mode='same');

        #===========================================================================
        # Derive footprint ellipsoid incorporating R% of the flux, if requested,
        # starting at peak value.
        if rs is not None:
            clevs = get_contour_levels(fclim_2d, dx, dy, rs)
            frs = [item[2] for item in clevs]
            xrs = []
            yrs = []
            for ix, fr in enumerate(frs):
                xr,yr = get_contour_vertices(x_2d, y_2d, fclim_2d, fr)
                if xr is None:
                    frs[ix]  = None
                    flag_err = 2
                xrs.append(xr)
                yrs.append(yr)
        else:
            if crop:
                rs_dummy = 0.8 #crop to 80%
                clevs = get_contour_levels(fclim_2d, dx, dy, rs_dummy)
                xrs = []
                yrs = []
                xrs,yrs = get_contour_vertices(x_2d, y_2d, fclim_2d, clevs[0][2])


        #===========================================================================
        # Crop domain and footprint to the largest rs value
        if crop:
            xrs_crop = [x for x in xrs if x is not None]
            yrs_crop = [x for x in yrs if x is not None]
            if rs is not None:
                dminx = np.floor(min(xrs_crop[-1]))
                dmaxx = np.ceil(max(xrs_crop[-1]))
                dminy = np.floor(min(yrs_crop[-1]))
                dmaxy = np.ceil(max(yrs_crop[-1]))
            else:
                dminx = np.floor(min(xrs_crop))
                dmaxx = np.ceil(max(xrs_crop))
                dminy = np.floor(min(yrs_crop))
                dmaxy = np.ceil(max(yrs_crop))

            if dminy>=ymin and dmaxy<=ymax:
                jrange = np.where((y_2d[:,0] >= dminy) & (y_2d[:,0] <= dmaxy))[0]
                jrange = np.concatenate(([jrange[0]-1], jrange, [jrange[-1]+1]))
                jrange = jrange[np.where((jrange>=0) & (jrange<=y_2d.shape[0]))[0]]
            else:
                jrange = np.linspace(0, 1, y_2d.shape[0]-1)

            if dminx>=xmin and dmaxx<=xmax:
                irange = np.where((x_2d[0,:] >= dminx) & (x_2d[0,:] <= dmaxx))[0]
                irange = np.concatenate(([irange[0]-1], irange, [irange[-1]+1]))
                irange = irange[np.where((irange>=0) & (irange<=x_2d.shape[1]))[0]]
            else:
                irange = np.linspace(0, 1, x_2d.shape[1]-1)

            jrange = [[it] for it in jrange]
            x_2d = x_2d[jrange,irange]
            y_2d = y_2d[jrange,irange]
            fclim_2d = fclim_2d[jrange,irange]

    #===========================================================================
    # Fill output structure
    if rs is not None:
        return {'x_2d': x_2d, 'y_2d': y_2d, 'fclim_2d': fclim_2d,
                'rs': rs, 'fr': frs, 'xr': xrs, 'yr': yrs, 'n':n, 'flag_err':flag_err}
    else:
        return {'x_2d': x_2d, 'y_2d': y_2d, 'fclim_2d': fclim_2d,
                'n':n, 'flag_err':flag_err}

#===============================================================================
#===============================================================================
def check_ffp_inputs(ustar, sigmav, h, ol, wind_dir, zm, z0, umean, rslayer, verbosity):
    # Check passed values for physical plausibility and consistency
    if zm <= 0.:
        raise_ffp_exception(2, verbosity)
        return False
    if z0 is not None and umean is None and z0 <= 0.:
        raise_ffp_exception(3, verbosity)
        return False
    if h <= 10.:
        raise_ffp_exception(4, verbosity)
        return False
    if zm > h :
        raise_ffp_exception(5, verbosity)
        return False
    if z0 is not None and umean is None and zm <= 12.5*z0:
        if rslayer is 1:
            raise_ffp_exception(6, verbosity)
        else:
            raise_ffp_exception(20, verbosity)
            return False
    if float(zm)/ol <= -15.5:
        raise_ffp_exception(7, verbosity)
        return False
    if sigmav <= 0:
        raise_ffp_exception(8, verbosity)
        return False
    if ustar <= 0.1:
        raise_ffp_exception(9, verbosity)
        return False
    if wind_dir > 360:
        raise_ffp_exception(10, verbosity)
        return False
    if wind_dir < 0:
        raise_ffp_exception(10, verbosity)
        return False
    return True

#===============================================================================
#===============================================================================
def get_contour_levels(f, dx, dy, rs=None):
    '''Contour levels of f at percentages of f-integral given by rs'''

    import numpy as np
    from numpy import ma
    import sys

    #Check input and resolve to default levels in needed
    if not isinstance(rs, (int, float, list)):
        rs = list(np.linspace(0.10, 0.90, 9))
    if isinstance(rs, (int, float)): rs = [rs]

    #Levels
    pclevs = np.empty(len(rs))
    pclevs[:] = np.nan
    ars = np.empty(len(rs))
    ars[:] = np.nan

    sf = np.sort(f, axis=None)[::-1]
    msf = ma.masked_array(sf, mask=(np.isnan(sf) | np.isinf(sf))) #Masked array for handling potential nan
    csf = msf.cumsum().filled(np.nan)*dx*dy
    for ix, r in enumerate(rs):
        dcsf = np.abs(csf - r)
        pclevs[ix] = sf[np.nanargmin(dcsf)]
        ars[ix] = csf[np.nanargmin(dcsf)]

    return [(round(r, 3), ar, pclev) for r, ar, pclev in zip(rs, ars, pclevs)]

#===============================================================================
def get_contour_vertices(x, y, f, lev):
    import matplotlib._cntr as cntr
    c = cntr.Cntr(x, y, f)
    nlist = c.trace(lev, lev, 0)
    segs = nlist[:len(nlist)//2]
    N = len(segs[0][:, 0])
    xr = [segs[0][ix, 0] for ix in range(N)]
    yr = [segs[0][ix, 1] for ix in range(N)]

    #Set contour to None if it's found to reach the physical domain
    if x.min() >= min(segs[0][:, 0]) or max(segs[0][:, 0]) >= x.max() or \
       y.min() >= min(segs[0][:, 1]) or max(segs[0][:, 1]) >= y.max():
        return [None, None]

    return [xr, yr]   # x,y coords of contour points.

#===============================================================================
def plot_footprint(x_2d, y_2d, fs, clevs=None, show_footprint=True, normalize=None,
                   colormap=None, line_width=0.3, iso_labels=None):
    '''Plot footprint function and contours if request'''

    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.colors import LogNorm

    #If input is a list of footprints, don't show footprint but only contours,
    #with different colors
    if isinstance(fs, list):
        show_footprint = False
    else:
        fs = [fs]

    if colormap is None: colormap = cm.jet
    #Define colors for each contour set
    cs = [colormap(ix) for ix in np.linspace(0, 1, len(fs))]

    # Initialize figure
    fig, ax = plt.subplots(figsize=(12, 10))
    # fig.patch.set_facecolor('none')
    # ax.patch.set_facecolor('none')

    if clevs is not None:
        #Temporary patch for pyplot.contour requiring contours to be in ascending orders
        clevs = clevs[::-1]

        #Eliminate contour levels that were set to None
        #(e.g. because they extend beyond the defined domain)
        clevs = [clev for clev in clevs if clev is not None]

        #Plot contour levels of all passed footprints
        #Plot isopleth
        levs = [clev for clev in clevs]
        for f, c in zip(fs, cs):
            cc = [c]*len(levs)
            if show_footprint:
                cp = ax.contour(x_2d, y_2d, f, levs, colors = 'r', linewidths=line_width)
            else:
                cp = ax.contour(x_2d, y_2d, f, levs, colors = cc, linewidths=line_width)
            #Isopleth Labels
            if iso_labels is not None:
                pers = [str(int(clev[0]*100))+'%' for clev in clevs]
                fmt = {}
                for l,s in zip(cp.levels, pers):
                    fmt[l] = s
                plt.clabel(cp, cp.levels[:], inline=1, fmt=fmt, fontsize=7)

    #plot footprint heatmap if requested and if only one footprint is passed
    if show_footprint:
        if normalize == 'log':
            norm = LogNorm()
        else:
            norm = None

        xmin = np.nanmin(x_2d)
        xmax = np.nanmax(x_2d)
        ymin = np.nanmin(y_2d)
        ymax = np.nanmax(y_2d)
        for f in fs:
            im = ax.imshow(f[:, :], cmap=colormap, extent=(xmin, xmax, ymin, ymax),
                 norm=norm, origin='lower', aspect=1)

        #Colorbar
        cbar = fig.colorbar(im, shrink=1.0, format='%.8f')
        cbar.set_label('Flux contribution', color = 'k')
    plt.show()

    return fig, ax

#===============================================================================
#===============================================================================
exTypes = {'message': 'Message',
           'alert': 'Alert',
           'error': 'Error',
           'fatal': 'Fatal error'}

exceptions = [
    {'code': 1,
     'type': exTypes['fatal'],
     'msg': 'At least one required parameter is missing. Please enter all '
            'required inputs. Check documentation for details.'},
    {'code': 2,
     'type': exTypes['error'],
     'msg': 'zm (measurement height) must be larger than zero.'},
    {'code': 3,
     'type': exTypes['error'],
     'msg': 'z0 (roughness length) must be larger than zero.'},
    {'code': 4,
     'type': exTypes['error'],
     'msg': 'h (BPL height) must be larger than 10 m.'},
    {'code': 5,
     'type': exTypes['error'],
     'msg': 'zm (measurement height) must be smaller than h (PBL height).'},
    {'code': 6,
     'type': exTypes['alert'],
     'msg': 'zm (measurement height) should be above roughness sub-layer (12.5*z0).'},
    {'code': 7,
     'type': exTypes['error'],
     'msg': 'zm/ol (measurement height to Obukhov length ratio) must be equal or larger than -15.5.'},
    {'code': 8,
     'type': exTypes['error'],
     'msg': 'sigmav (standard deviation of crosswind) must be larger than zero.'},
    {'code': 9,
     'type': exTypes['error'],
     'msg': 'ustar (friction velocity) must be >=0.1.'},
    {'code': 10,
     'type': exTypes['error'],
     'msg': 'wind_dir (wind direction) must be >=0 and <=360.'},
    {'code': 11,
     'type': exTypes['fatal'],
     'msg': 'Passed data arrays (ustar, zm, h, ol) don\'t all have the same length.'},
    {'code': 12,
     'type': exTypes['fatal'],
     'msg': 'No valid zm (measurement height above displacement height) passed.'},
    {'code': 13,
     'type': exTypes['alert'],
     'msg': 'Using z0, ignoring umean if passed.'},
    {'code': 14,
     'type': exTypes['alert'],
     'msg': 'No valid z0 passed, using umean.'},
    {'code': 15,
     'type': exTypes['fatal'],
     'msg': 'No valid z0 or umean array passed.'},
    {'code': 16,
     'type': exTypes['error'],
     'msg': 'At least one required input is invalid. Skipping current footprint.'},
    {'code': 17,
     'type': exTypes['alert'],
     'msg': 'Only one value of zm passed. Using it for all footprints.'},
    {'code': 18,
     'type': exTypes['fatal'],
     'msg': 'if provided, rs must be in the form of a number or a list of numbers.'},
    {'code': 19,
     'type': exTypes['alert'],
     'msg': 'rs value(s) larger than 90% were found and eliminated.'},
    {'code': 20,
     'type': exTypes['error'],
     'msg': 'zm (measurement height) must be above roughness sub-layer (12.5*z0).'},
    ]

def raise_ffp_exception(code, verbosity):
    '''Raise exception or prints message according to specified code'''

    ex = [it for it in exceptions if it['code'] == code][0]
    string = ex['type'] + '(' + str(ex['code']).zfill(4) + '):\n '+ ex['msg']

    if verbosity > 0: print('')

    if ex['type'] == exTypes['fatal']:
        if verbosity > 0:
            string = string + '\n FFP_fixed_domain execution aborted.'
        else:
            string = ''
        raise Exception(string)
    elif ex['type'] == exTypes['alert']:
        string = string + '\n Execution continues.'
        if verbosity > 1: print string
    elif ex['type'] == exTypes['error']:
        string = string + '\n Execution continues.'
        if verbosity > 1: print string
    else:
        if verbosity > 1: print string





##3 - Roughness calculation functions
#### {morphology} ####
def CalcWeightedMorphVegV2(bld, veg, porosity, rotatedphi,wd_input,scale):
    '''
    Function to calculate morphology of vegetation and buildings
    INPUT
    bld = 2d array of building heights
    veg = 2d numpy array of vegetation heights
    porosity = porosity of vegetation
    rotatedphi = 2d array of footprint weightings
    wd_input = wind direction
    scale = ratio of horizontal to vertical scale in DEMs
    OUTPUT
    geometry of buildings and vegetation
    '''
    build = bld
    build[(build < 2.)] = 0.  # building should be higher than 2 meter therefore 'gets rid' of ones that aren't
    #Rid of where overlap in buildings and veg
    bool_vb = (veg>0)*(build>0)    # boolean where veg and builds >0 (i.e. overlap)
    veg = veg * ~bool_vb
    #building and veg DSM
    bldveg = build + veg
    #Single layer models for phi
    fpA = rotatedphi>0                          #Boolean of area where footprint contributes
    W_totalA = np.nansum(rotatedphi)         #Total area
    #plan area index buildings
    isb_fp = (build>0)*fpA                      #Building pixels in source area
    W_isb_fp = np.nansum(isb_fp* rotatedphi) #weight foorprint function of pixels
    #plan area index veg
    isv_fp = (veg>0)*fpA                      #veg pixels in source area
    W_isv_fp = np.nansum(isv_fp* rotatedphi)     #weight foorprint function of pixels
    #plan area index total
    plantot = W_isb_fp+(W_isv_fp*(1-porosity))
    pai = plantot/W_totalA
    paibuild = W_isb_fp/W_totalA
    paiveg = (W_isv_fp*(1-porosity))/W_totalA
    #Building heights (zH, zMax, zSdev)
    #zH
    #builds | veg
    build_fp = (build)*fpA                        #Building heights in source area
    veg_fp = (veg)*fpA                            #veg heights in source area
    veg_fp[veg_fp<=0.]=np.nan
    W_build_fp = np.nansum(build_fp* rotatedphi)
    W_veg_fp = np.nansum(veg_fp* rotatedphi)
    zHbuild = W_build_fp/W_isb_fp
    zHveg = W_veg_fp/W_isv_fp
    isbv_fp = (bldveg>0)*fpA
    buildveg_fp = (bldveg)*fpA
    buildveg_fp[buildveg_fp<=0]=np.nan
    W_isbldveg_fp = np.nansum(isbv_fp* rotatedphi)
    W_buildveg_fp = np.nansum(buildveg_fp* rotatedphi)
    zH = W_buildveg_fp/W_isbldveg_fp
    #zMax
    zMaxbuild=np.nanmax(build_fp)
    zMaxveg=np.nanmax(veg_fp)
    zMax = np.nanmax(buildveg_fp)
    #zSdev
    #set nans for sdev calc
    build_fp[np.where(build_fp==0.)] = np.nan
    veg_fp[np.where(veg_fp==0.)] = np.nan
    buildveg_fp[np.where(buildveg_fp==0.)] = np.nan
    zSdevbuild = np.nanstd(build_fp)
    zSdevveg = np.nanstd(veg_fp)
    zSdev = np.nanstd(buildveg_fp)
    #Frontal area index
    #rot_dsm = scnd.rotate(dsm, wd_input,order=0, reshape=False, mode='nearest')                #rotated buildings into wind direction
    #rot_dsm[rot_dsm<0]=0
    rot_build = scnd.rotate(build, wd_input,order=0, reshape=False, mode='nearest')                #rotated buildings into wind direction
    rot_build[rot_build<0]=0
    rot_veg = scnd.rotate(veg, wd_input,order=0, reshape=False, mode='nearest')                #rotated veg into wind direction
    rot_veg[rot_veg<0]=0
    #rot_vegdsm = scnd.rotate(veg+dem, wd_input,order=0, reshape=False, mode='nearest')                #rotated veg dsm into wind direction
    #rot_vegdsm[rot_vegdsm<0]=0
    #rot_phi = scnd.rotate(rotatedphi, wd_input,order=0, reshape=False, mode='nearest')       #rotate footprint function into wind direction - not this is already 	northward so 	not rotated
    rot_phi = scnd.rotate(rotatedphi, wd_input,order=0, reshape=False, mode='nearest')       #Dont rotate cos already rotated
    rot_phi[rot_phi<0]=0
    d = np.shape(build)
    #buildings
    wall=np.zeros(d)
    wall[2:d[1],:]=rot_build[2:d[1],:]-rot_build[1:d[1]-1,:]
    wall[np.where(wall<=2.)]=0
    wall[np.where(rot_build==0.)]=0
    frontbld_fp = np.float32(wall)*(rot_phi>0)
    W_frontbld_fp = np.nansum(frontbld_fp*rot_phi)           #weight by footprint function
    d_input = 1/scale
    faibuild = W_frontbld_fp/(W_totalA/scale)
    #veg
    leaf=np.zeros(d)
    leaf[2:d[1],:]=rot_veg[2:d[1],:]-rot_veg[1:d[1]-1,:]
    leaf[np.where(leaf<=0.1)]=0
    leaf[np.where(rot_veg==0.)]=0
    frontveg_fp = np.float32(leaf)*(rot_phi>0)
    W_frontveg_fp = np.nansum(frontveg_fp*rot_phi)           #weight by footprint function
    faiveg = W_frontveg_fp/(W_totalA/scale)
    #build and veg
    #build and veg
    Pv = ((-1.251*porosity**2)/1.2)+((0.489*porosity)/1.2) + (0.803/1.2)		#factor accounting for porosity
    faitop = (W_frontveg_fp*Pv)+ W_frontbld_fp
    faibot = (W_totalA/scale)
    fai = faitop/faibot
    #faivegdrag =1.2*(1-porosity)*(W_frontveg_fp*(1-(20/zH)))
    #fai = (faiblddrag+faivegdrag)/W_totalA

    return fai,pai,zH,zMax,zSdev,faiveg,paiveg,zHveg,zMaxveg,zSdevveg,faibuild,paibuild,zHbuild,zMaxbuild,zSdevbuild


######## CHANGES TO BE MADE ##########
###To add to dialog:
#BLheight option
#porosity
#vegetation cdsm option
#drop down table for choosing KAM or KLJ --> this will change what fucntion is run

#####To add to main FPR model
#INPUT TABLE both now use porosity and KLJ uses boundary layer height therefore input files and variables may differ -
# can use a single input file and just not use BLH in KAM
#OUTPUT TABLE - we can now save other geometry (veg and builds) if we want to.

#selection of footprint model and addition of new variables into functions
# if FPRmodel === "KAM":
#     footprintiterKAM()
# elif FPRmodel == "KLJ":
#     footprintiterKLJ()
#
#
# #setting of elevation databases
# if dtm supplied:
#     bld = dsm - dtm
#     veg = cdsm - dtm
#
# if no dtm supplied
#     bld = dsm
#     veg = cdsm
#
# if veg is None:
#     veg = np.zeros(np.shape(dsm))
#     print("no CDSM supplied, assuming no vegetation")
#
#
# ###BLheight for Klj
# if h is None:
#     h = 1000.
#     print("no BLH supplied, assuming 1000 m")


#### Function that reads in observational data by timestep at a time and calculates footprint ####
#number of timesteps to run for:
# iterations=1



#SET UP INPUT FILE
#z_0_input,z_d_input,z_m_input,wind,sigv,Obukhov,ustar,dir = [0.5,0.5],[10,10],[30,30],[3,3],[2,2],[-1000,-1000],[0.75,0.75],[120,120]
#np.savetext("UMEPFPRTestfile-INPUT.txt",np.column_stack((z_0_input,z_d_input,z_m_input,wind,sigv,Obukhov,ustar,dir)), fmt=('%5.5f'), comments='', header=' z_0_input z_d_input z_m_input wind sigv Obukhov ustar dir')


#Load input
# z_0_input,z_d_input,z_m_input,wind,sigv,Obukhov,ustar,dir = np.loadtxt("UMEPFPRTestfile-INPUT.txt",skiprows=1,unpack=True)
# Run model
# iterations,fai,pai,zH,zMax,zSdev,zSdev,rotatedphi,rotatedphiPerc = footprintiter(iterations,z_0_input,z_d_input,z_m_input,wind,sigv,Obukhov,ustar,dir)
#Save output parameters
# np.savetxt('UMEPTestfile-PARAMS_OUTPUT.txt', np.column_stack((z_0_input,z_d_input,z_m_input,wind,sigv,Obukhov,ustar,dir,fai,pai,zH,zMax,zSdev)), fmt=('%5.5f'), comments='', header=' z_0_input z_d_input z_m_input wind sigv Obukhov ustar dir fai pai zH zMax zSdev')
# #Save output raw phi
# np.savetxt('UMEPTestfile-PHI_OUTPUT.txt',rotatedphi)
# #Save ouput phi as percentage
# np.savetxt('UMEPTestfile-PHIPERC_OUTPUT.txt',rotatedphi)

def saveraster(gdal_data, filename, raster):  ## This should move at some point (Utilities.misc)
    rows = gdal_data.RasterYSize
    cols = gdal_data.RasterXSize

    # outDs = gdal.GetDriverByName("GTiff").Create(folder + 'shadow' + tv + '.tif', cols, rows, int(1), GDT_Float32)
    outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
    # outDs = gdal.GetDriverByName(gdal_data.GetDriver().LongName).Create(filename, cols, rows, int(1), GDT_Float32)
    outBand = outDs.GetRasterBand(1)

    # write the data
    outBand.WriteArray(raster, 0, 0)
    # flush data to disk, set the NoData value and calculate stats
    outBand.FlushCache()
    outBand.SetNoDataValue(-9999)

    # georeference the image and set the projection
    outDs.SetGeoTransform(gdal_data.GetGeoTransform())
    outDs.SetProjection(gdal_data.GetProjection())