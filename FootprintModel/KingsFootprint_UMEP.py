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
from ..Utilities import RoughnessCalcFunction as rg

#### 1 - Model settings: Set up the grid space that the model will run in ####
#Calculation of morphometric Roughness Parameters, roughness information and provides input
# d_input = 4.0           # Model resolution - at the moment using a 4m resolution
# domain_x = 4000.0       # Modelled area in longitudinal direction
# domain_y = 2000.0       # Modelled area in lateral direction
# domain_output = 8000.   # Domain x*2
# timezone='UTC'
# g=9.8
# k=0.4

def footprintiter(iterations,z_0_input,z_d_input,z_m_input,wind,sigv,Obukhov,ustar,dir,dsm,dem,rows,cols,res,dlg,maxfetch,rm):

    dlg.progressBar.setRange(0, iterations)
    dlg.progressBar.setValue(0)
    scale = 1. / res
    maxfetch = maxfetch * scale
    domain_y = np.round(maxfetch / 2.)  # pixels ?
    domain_x = np.round(maxfetch)  # pixels ?
    domain_output = maxfetch * 2  # in meters
    d_input = res # meters

    totRotatedphiPerc = np.zeros((rows,cols))

    # g=9.8
    k=0.4

    Totphi=np.zeros((domain_y,domain_y))
    Wfai=np.zeros((iterations,1))
    Wpai=np.zeros((iterations,1))
    WzH=np.zeros((iterations,1))
    WzMax=np.zeros((iterations,1))
    WzSdev=np.zeros((iterations,1))
    Wz_d_output=np.zeros((iterations,1))
    Wz_0_output=np.zeros((iterations,1))
    Wz_m_output=np.zeros((iterations,1))
    for i in np.arange(0,iterations,1):
        dlg.progressBar.setValue(i + 1)
        z_0 = z_0_input[i]
        z_d = z_d_input[i]
        z_m = z_m_input[i]
        u = wind[i]
        sig_v_input = sigv[i]
        L = Obukhov[i]
        u_star = ustar[i]
        wd_input=dir[i]

        #Set z_m to above ground
        z_m=z_m-z_d

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
        fx=domain_output
        domain_x = domain_x / d_input
        domain_y = domain_y / d_input
        fy = fx
        full = np.zeros([fx,fy])
        full[(fx+1)/2:(fx+1)/2+(domain_x),(fy/2+1)-domain_y:(fy/2+1)+domain_y+1]=phi
        full[np.isnan(full)]=0

        ##Rotation for wind angle for absolute plot and correction for rotation algorithm
        rotang =180 - wd_input
        rotatedphi = scnd.rotate(full, rotang, reshape=False, mode='nearest')

        #Conversion into percentages in each grid square
        rotatedphiPerc = (rotatedphi/np.nanmax(rotatedphi))*100
        totRotatedphiPerc = totRotatedphiPerc + rotatedphiPerc

        #Calculate weighted morphometry and therefore weighted zo and zd
        Wfai[i],Wpai[i],WzH[i],WzMax[i],WzSdev[i] = CalcWeightedMorph(dsm, dem, rotatedphiPerc, wd_input, scale)
        # Wz_m_output[i] = z_m - Wz_d_output[i]
        Wz_d_output[i],Wz_0_output[i] = rg.RoughnessCalc(rm,WzH[i],Wfai[i],Wpai[i],WzMax[i],WzSdev[i])



    return(Wfai,Wpai,WzH,WzMax,WzSdev,Wz_d_output,Wz_0_output,rotatedphi,totRotatedphiPerc)
##### Load in DSM/ DEM and centre on site ####
# scale = 0.25                    # This is scale between horizontal and vertical
# Res = domain_output             # Define resolution of area in m
#Load in LiDAR DSM and DEM
# Lidarbld = np.loadtxt('D:/Users/Christoph/Google Drive/Reading (2015-2018)/WindGusts/ImageMorphStart/lidar_builddem_4m.asc', skiprows=6) #Set dsm = Building + Surface height text file
# Lidargrd = np.loadtxt('D:/Users/Christoph/Google Drive/Reading (2015-2018)/WindGusts/ImageMorphStart/lidar_grounddem_4m.asc', skiprows=6) #Set dem = Surface height text file

# site='KSS'
#Set site, coords and domain
# R = (Res*scale)/2           #Sets cropping around site based on defined resolution
# if site == 'KSSW':
#     yc = 1446
#     xc = 1026
#     z_ag = 50.3
# elif site == 'KSK':
#     yc = 1457
#     xc = 1036
#     z_ag = 38.8
# elif site == 'KSS':
#     yc = 1454
#     xc = 1021
#     z_ag = 48.9
# else:
#     print('ERROR - SELECT TRUE SITE')
# dsm = (Lidarbld[xc-R:xc+R,yc-R:yc+R])           #Crop around DSM
# dem = (Lidargrd[xc-R:xc+R,yc-R:yc+R])           #Crop around DEM


#### Function that uses dsm and dem to return weighted morphometric descriptors ####
def CalcWeightedMorph(dsm,dem,rotatedphiPerc,wd_input,scale):
    #Defines building heights only and only keeps buildings that are bigger than 2m
    build = dsm - dem
    build[(build < 2.)] = 0.
    #plt.imshow(build)

    #Single layer models for phi
    fpA = rotatedphiPerc>0                          #Boolean of area where footprint contributes
    W_totalA = np.nansum(rotatedphiPerc)            #Total area

    #plan area index
    isb_fp = (build>0)*fpA                      #Building pixels in source area
    W_isb_fp = np.nansum(isb_fp* rotatedphiPerc)     #weight foorprint function of pixels
    pai = W_isb_fp/W_totalA

    #Building heights (zH, zMax, zSdev)
    build_fp = (build)*fpA                        #Building heights in source area
    W_build_fp = np.nansum(build_fp* rotatedphiPerc)
    zH=W_build_fp/W_isb_fp
    zMax=np.nanmax(build_fp*( rotatedphiPerc/100))
    build_fp[np.where(build_fp<2)] = np.nan
    zSdev = np.nanstd(build_fp*( rotatedphiPerc/100))
    #Ground height
    ground_fp = dem*fpA                               #Ground in source area
    W_ground_fp = np.nansum(ground_fp* rotatedphiPerc)      #weighted by footprint function
    grd=W_ground_fp/W_totalA

    #Frontal area index
    rot_dsm = sc.imrotate(dsm, wd_input, interp='nearest')                #rotated buildings into wind direction
    rot_build = sc.imrotate(build, wd_input, interp='nearest')                #rotated buildings into wind direction
    rot_phi = sc.imrotate(rotatedphiPerc, -wd_input-180, interp='nearest')       #rotate footprint function into wind direction
    n=dsm.shape[0]
    filt1 = np.ones((n, 1.)) * -1.
    filt2 = np.ones((n, 1.))
    filt = np.array(np.hstack((filt1, filt2))).conj().T
    wall = np.zeros((n, n))                                        #for each iteration makes a new c as a matrix full of zeros with 200 columns and 200 rows
    a = rot_build
    for i in np.arange(1., (n-1.)+1):                           #CALCULATIONS ON EACH GRID POINT IN EACH ROTATION this inside each rotated for i in length of n
        wall[int(i)-1, :] = np.sum((filt*a[int(i)-1:i+1., :]), 0)  #for every position 1 in c make it the sum of filter function to find where walls are (i.e. where the height changes)
    wall[np.where(wall<=2.)]=0
    wall[np.where(rot_build==0.)]=0
    front_fp = np.float32(wall)*(rot_phi>0)
    W_front_fp = np.nansum(front_fp*rot_phi)           #weight by footprint function
    fai = W_front_fp/(W_totalA/scale)
    return fai,pai,zH,zMax,zSdev

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