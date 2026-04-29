import numpy as np

def create_patches(patch_option):

    deg2rad = np.pi/180

    # patch_option = 1 = 145 patches (Robinson & Stone, 2004)
    # patch_option = 2 = 153 patches (Wallenberg et al., 2022)
    # patch_option = 3 = 306 patches -> test 
    # patch_option = 4 = 612 patches -> test

    skyvaultalt = np.atleast_2d([])
    skyvaultazi = np.atleast_2d([])
            
    # Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
    # Patch option 1, 145 patches, Original Robinson & Stone (2004) after Tregenza (1987)/Tregenza & Sharples (1993)
    if patch_option == 1:
        annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])
        skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90]) # Robinson & Stone (2004)
        azistart = np.array([0, 4, 2, 5, 8, 0, 10, 0]) # Fredrik/Nils
        patches_in_band = np.array([30, 30, 24, 24, 18, 12, 6, 1]) # Robinson & Stone (2004)
    # Patch option 1, 153 patches, Wallenberg et al. (2022)
    elif patch_option == 2:
        annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])
        skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90]) # Robinson & Stone (2004)
        azistart = np.array([0, 4, 2, 5, 8, 0, 10, 0]) # Fredrik/Nils
        patches_in_band = np.array([31, 30, 28, 24, 19, 13, 7, 1]) # Nils
    # Patch option 2, 306 patches, test
    elif patch_option == 3:
        annulino = np.array([0, 12, 24, 36, 48, 60, 72, 84, 90])
        skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90]) # Robinson & Stone (2004)
        azistart = np.array([0, 4, 2, 5, 8, 0, 10, 0]) # Fredrik/Nils
        patches_in_band = np.array([31*2, 30*2, 28*2, 24*2, 19*2, 13*2, 7*2, 1]) # Nils
    # Patch option 3, 612 patches, test
    elif patch_option == 4:
        annulino = np.array([0, 4.5, 9, 15, 21, 27, 33, 39, 45, 51, 57, 63, 69, 75, 81, 90]) # Nils
        skyvaultaltint = np.array([3, 9, 15, 21, 27, 33, 39, 45, 51, 57, 63, 69, 75, 81, 90]) # Nils
        patches_in_band = np.array([31*2, 31*2, 30*2, 30*2, 28*2, 28*2, 24*2, 24*2, 19*2, 19*2, 13*2, 13*2, 7*2, 7*2, 1]) # Nils
        azistart = np.array([0, 0, 4, 4, 2, 2, 5, 5, 8, 8, 0, 0, 10, 10, 0]) # Nils

    skyvaultaziint = np.array([360/patches for patches in patches_in_band])

    for j in range(0, skyvaultaltint.shape[0]):
        for k in range(0, patches_in_band[j]):
            skyvaultalt = np.append(skyvaultalt, skyvaultaltint[j])
            skyvaultazi = np.append(skyvaultazi, k*skyvaultaziint[j] + azistart[j])

    # skyvaultzen = (90 - skyvaultalt) * deg2rad
    # skyvaultalt = skyvaultalt * deg2rad
    # skyvaultazi = skyvaultazi * deg2rad

    return skyvaultalt, skyvaultazi, annulino, skyvaultaltint, patches_in_band, skyvaultaziint, azistart