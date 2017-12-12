
# coding: utf-8

# In[1]:



import MosaicFitsReader as mfr
from scipy import stats
from scipy.ndimage.filters import gaussian_filter
import numpy as np
import math

def centroid(arr):
    """
    One step 1D centroiding algo.
    Returns centroid position and standard deviation
    """
    l = arr.shape[0]
    ixs = np.arange(l)
    arr = arr - np.median(arr)
    arr = np.where(arr < 0, 0, arr)    
    ixs2 = ixs * ixs
    sumarr = arr.sum()
    cen = np.dot(arr, ixs)/sumarr
    return cen, math.sqrt(np.dot(arr, ixs2)/sumarr - cen * cen)

def centroidLoop(arr, fromIdx, toIdx, nLoops=10, epsilon=1E-1):
    """
    Finds the centroid by repeatedly centering and recalculating 
    until the centroid position changes by less than epsilon.
    
    Returns status, centroid position, standard deviation, iterations
    
    status: 0 OK, -1 bad centroid or no signal
    centroid position: position relative to input array, ie. 0 is first pixel
    standard deviation: standard deviation as calculated by the centroid algorithm (assumed Gaussian stats)
    iterations: number of iterations needed until change is less than epsilon
    """
    def limit(x):
        if x < 0: return 0
        if x >= length: return length
        return x
    
    length = len(arr)
    radius = (toIdx - fromIdx)/2
    lastCenPos = -9999
    for i in range(nLoops):
        fromIdx = int(limit(fromIdx))
        toIdx = int(limit(fromIdx + radius + radius + 0.5))
        pos, cenStd = centroid(arr[fromIdx:toIdx])
        cenPos = pos + fromIdx
        #print (i, fromIdx, toIdx, cenPos, cenStd, lastCenPos)
        
        if cenPos < fromIdx or toIdx < cenPos:
            return -1, 0, 0, i
        
        if abs(lastCenPos - cenPos) < epsilon:
            return 0, cenPos, cenStd, i
        if cenStd > radius/3:
            return -1, cenPos, cenStd, i
        fromIdx = cenPos - radius
        lastCenPos = cenPos
        
    return -1, cenPos, cenStd, i

def findWidths (arr1d, size=60):
    """
    Divides the input array in segments of size length.
    For each segment, finds the centroid, if centroid is good then record it.
    Sorts the centroids by standard deviation.
    Returns the smallest half of the standard deviation
    """
    out = []
    for x in range(0, len(arr1d)-size, size):
        ok, cen, std, idx = centroidLoop(arr1d, x, x+size)     
        #print (res)
        if ok == 0:
            out.append(std)
    #print (out)
    if len(out) <= 0:
        return []
    out = sorted(out)
    return out[:len(out)//2]

def makePairs(data):
    """
    Input data is in the format: ((focus1, (v1, v2, v3...)), (focus2, (v1, v2, v3)))
    
    Outputs the focus and std as pairs: ((focus1, v1), (focus1, v2), ....)
    """
    for a, b in data:
        for c in b:
            yield (a, c)
            
def calcAsymptote(A, B, C):
    """
    y^2 = Ax^2 + Bx + C
    
    Returns the parameters for the asymptotes for given A, B, C
    """
    h = -B/A/2
    a2 = C - A * h*h
    b2 = a2/A
    m0 = math.sqrt(a2/b2)
    b0 = -m0 * h
    return m0, b0, h

def asympFunc(m, b):
    """
    Returns a function to calculate the asymptote y for given x.
    """
    def f(x):
        return m * x + b
    return f

"""
Shui's version
For all input files, finds the standard deviations of the centroids.
These standard deviations are assosicated with the focus. 

Output is stored in out[].
"""
def measureWidths(files):
    minrow = 200
    maxrow = 3800
    out = []
    print("Received this list of files: %s" % str(files))
    for f in files:
        fname = f

    #for f in range(8,15): #LongSlit blue
    #    fname = "test_images/longslit/bfoc%04d.fits" % f
    
    #for f in range(1,7): #LongSlit red
    #    fname = "test_images/longslit/rfoc%04d.fits" % f
    
        print("Attempting to open file %s\n" % f)
        ffile = mfr.MosaicFitsReader(fname)
        img = np.array(ffile.data)
        instrument = ffile.getKeyword('INSTRUME')
        if "BLU" in instrument:
            Focus = ffile.getKeyword('BLUFOCUS')
        else:
            Focus = ffile.getKeyword('REDFOCUS')
        if Focus == None:
            continue
        for row in range(minrow,maxrow,100):
            cut1d = img[:,row]
            if np.max(gaussian_filter(cut1d,sigma=20))> 2000:
                widths = findWidths(cut1d)
                if len(widths)>5:
                    clippedWidths,low,upp = stats.sigmaclip(widths,low=4,high=2)
                    if clippedWidths.std()<1:
                        print(row,Focus,clippedWidths.mean(),low,upp,clippedWidths.std())
                        out.append((Focus, clippedWidths))
    return out



def generatePairs(out):
    return np.array(list(makePairs(out))).T


"""
Fits a hyperbola: x=focus, y=standard deviation

Hyperbola equation: y^2 = Ax^2 + Bx + C

"""
def fitPairs(pairs):
    res = np.polyfit(pairs[0], np.multiply(pairs[1], pairs[1]), deg=2)

    func = np.poly1d(res)
    def func1 (x):
        return math.sqrt(func(x))

    funcV = np.vectorize(func1)

    """
    Finds the parameters for the asymptotes 
    """
    A, B, C = res
    m0, b0, minX = calcAsymptote(A, B, C)
    print ("minX", minX, "Asymp", m0, b0)

    return funcV, m0, b0, minX



