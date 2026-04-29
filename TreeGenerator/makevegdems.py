from builtins import range
import numpy as np
# import matplotlib.pylab as plt

def vegunitsgeneration(buildings, vegdem, vegdem2, ttype, height, trunk, dia, rowa, cola, sizex, sizey, scale):
    # This function creates the shape of each vegetation unit and locates it a grid.

    vegdemtemp = np.zeros([sizey, sizex])
    vegdem2temp = np.copy(vegdemtemp)
    dia = dia * scale
    trees = conifertree(dia)
    if ttype == 1:  # conifer tree
        trees = trees * (height - trunk)
        circle = imcircle(dia)
        trees = circle * (trees + trunk)
        treetrunkunder = trunk * circle

    else:  #ttype == 2  # desiduous tree
        canopy = 1 - ((1 - trees) ** 2)
        trees = canopy * (height - trunk)
        circle = imcircle(dia)
        trees = circle * (trees + trunk)
        treetrunkunder = circle * trunk

    col1 = cola - (np.floor(dia / 2))
    row1 = rowa - (np.floor(dia / 2))

    rowmin = abs(row1)
    colmin = abs(col1)
    rowmax = trees.shape[0]
    colmax = trees.shape[0]

    # cutting trees at dem egde
    rowcutmax = rowmax
    colcutmax = rowcutmax
    rowcutmin = 0
    colcutmin = 0
    if row1 + rowmax - 1 > vegdem.shape[0]:
        rowcutmax = rowmax - abs(vegdem.shape[0] - (row1 + rowmax))
        rowmax = vegdem.shape[0]

    if col1 + rowmax - 1 > vegdem.shape[1]:
        colcutmax = rowmax - abs(vegdem.shape[1] - (col1 + rowmax))
        colmax = vegdem.shape[1]

    if row1 < 1:
        rowcutmin = abs(row1)
        rowmin = 0
        if rowcutmin == 0:
            rowcutmin = 0

    if col1 < 1:
        colcutmin = abs(col1)
        colmin = 0
        if colcutmin == 0:
            colcutmin = 0

    if row1 < 1 or col1 < 1 or row1 + rowmax - 1 > vegdem.shape[0] or col1 + rowmax - 1 > vegdem.shape[1]:
        # cutting tree at dem edge
        if ((treetrunkunder.ndim > 1) and (trees.ndim > 1)):
            trees = trees[int(rowcutmin):int(rowcutmax), int(colcutmin):int(colcutmax)]
            treetrunkunder = treetrunkunder[int(rowcutmin): int(rowcutmax), int(colcutmin): int(colcutmax)]
            vegdemtemp[int(rowmin):int(rowmin + trees.shape[0]), int(colmin):int(colmin + trees.shape[1])] = trees
            vegdem2temp[int(rowmin):int(rowmin + trees.shape[0]), int(colmin):int(colmin + trees.shape[1])] = treetrunkunder
    else:
        # no cutting of tree at dem edge
        vegdemtemp[int(rowmin):int(rowmin + rowmax), int(colmin):int(colmin + colmax)] = trees
        vegdem2temp[int(rowmin):int(rowmin + rowmax), int(colmin):int(colmin + colmax)] = treetrunkunder

    if ttype == 0:  # remove trees
        if row1 < 1 or col1 < 1 or row1 + rowmax - 1 > vegdem.shape[0] or col1 + rowmax - 1 > vegdem.shape[1]:
            vegdemtemp[int(rowmin):int(rowmin + trees.shape[0]), int(colmin):int(colmin + trees.shape[1])] = trees * 0
            vegdem2temp[int(rowmin):int(rowmin + trees.shape[0]), int(colmin):int(colmin + trees.shape[1])] = treetrunkunder * 0
        else:
            vegdemtemp[int(rowmin):int(rowmin + rowmax), int(colmin):int(colmin + colmax)] = trees * 0
            vegdem2temp[int(rowmin):int(rowmin + rowmax), int(colmin):int(colmin + colmax)] = treetrunkunder * 0
    else:  # add trees
        vegdem = np.maximum(vegdem, vegdemtemp)
        vegdem2temp[vegdemtemp == 0] = -1000
        vegdem2[vegdem2 == 0] = -1000
        vegdem2 = np.maximum(vegdem2, vegdem2temp)

    vegdem = vegdem * buildings  # remove vegetation from building pixels
    vegdem2 = vegdem2 * buildings  # remove vegetation from building pixels

    vegdem2[vegdem2 == -1000] = 0

    return vegdem, vegdem2


def conifertree(dia):
    circle = imcircle(dia)
    dia = circle.shape[0]
    index = 1
    while dia - index * 2 >= 1:
        if dia - index * 2 >= 2:
            circle2 = imcircle(dia-index*2)
            circle3 = np.zeros([circle.shape[0], circle.shape[0]])
            circle3[index:circle2.shape[0]+index, index:circle2.shape[0]+index] = circle2
            circle = circle+circle3
            index = index + 1

        if dia - index * 2 == 1:
            circle3 = np.zeros([circle.shape[0], circle.shape[0]])
            circle3[index, index] = 1
            circle = circle + circle3
            index = index + 1

    tree = circle/np.max(circle)

    return tree


def imcircle(n):

    n = round(n)

    if n < 4:
        y = np.ones(int(n))

    elif np.fmod(n, 2) == 0:  # even n
        DIAMETER = n
        diameter = n - 1
        RADIUS = DIAMETER / 2
        radius = diameter / 2
        height_45 = round(radius / np.sqrt(2))
        width = np.zeros([1, int(RADIUS)])
        semicircle = np.zeros([int(DIAMETER), int(RADIUS)])

        for i in range(0, int(height_45)):
            upward = i + 1 - 0.5
            sine = upward / radius
            cosine = np.sqrt(1 - sine ** 2)
            width[0, i] = np.ceil(cosine * radius)

        array = width[0, 0:int(height_45)] - height_45

        for j in range(int(np.max(array)), int(np.min(array)) - 1, -1):
            width[0, int(height_45 + j - 1)] = np.max(np.where(array == j)) + 1

        if np.min(width) == 0:
            ind = np.where(width == 0)
            index = ind[1]
            width[0, index] = np.round(np.mean([width[0, index - 1], width[0, index + 1]]))

        width = np.append(np.fliplr(width), width, axis=1)

        for k in range(0, int(DIAMETER)):
            semicircle[k, 0:int(width[0, k])] = np.ones([1, int(width[0, k])])

        y = np.append(np.fliplr(semicircle), semicircle,axis=1)

    else:  # odd n
        DIAMETER = n
        diameter = n - 1
        RADIUS = DIAMETER / 2
        radius = diameter / 2
        semicircle = np.zeros([int(DIAMETER), int(radius)])
        height_45 = round(radius / np.sqrt(2) - 0.5)
        width = np.zeros([1, int(radius)])

        for i in range(0, int(height_45)):
            upward = i + 1
            sine = upward / radius
            cosine = np.sqrt(1 - sine ** 2)
            width[0, i] = np.ceil(cosine * radius - 0.5)

        array = width[0, 0:int(height_45)] - height_45

        for j in range(int(np.max(array)), int(np.min(array)) - 1, -1):
            width[0, int(height_45 + j - 1)] = np.max(np.where(array == j)) + 1

        if np.min(width) == 0:
            ind = np.where(width == 0)
            index = ind[1]
            width[0, index] = np.round(np.mean([width[0, index - 1], width[0, index + 1]]))

        width1 = np.append(np.fliplr(width), np.ones([1, 1]) * np.max(width), axis=1)
        width = np.append(width1, width,axis=1)

        for k in range(0, int(DIAMETER)):
            semicircle[k, 0:int(width[0, k])] = np.ones([1, int(width[0, k])])

        y = np.append(np.fliplr(semicircle), np.ones([int(DIAMETER), 1]), axis=1)
        y = np.append(y, semicircle, axis=1)

    return y


