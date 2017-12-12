import astropy.io.fits as pyfits
import numpy as np


class MosaicFitsReader:
    def __init__(self, fname=None):
        self.fname = fname
        self.data = self.read(fname)
    
    def getImage(self):
        return self.data    
    
    def _splitFormat (self, value):
        parts = value.replace('[', '').replace(']','').replace(',',':').split(':')
        return [int(x) for x in parts]

    def _getRegion (self, reg):
        def reorder (x0, x1):
            if x0 > x1:
                return slice(x0-1, x1-1, -1)
            return slice(x0-1, x1-1, 1)

        return reorder(reg[0], reg[1]), reorder(reg[2], reg[3])

    def read (self, fname):
        """
        Reads image data from a DEIMOS fits file.
        Returns the raw image data and locations of the regions and the minmax.
        """
        info = []
        img = []
        minx, maxx, miny, maxy = 1E9, 0, 1E9, 0
        with pyfits.open(fname) as hdrs:
            self.hdrs = hdrs
            for h in hdrs:
                header = h.header
                try:
                    dstr = header.get('DETSIZE')
                    if not dstr:
                        # Primary HDU has no DETSIZE
                        continue

                    detSize = self._splitFormat(dstr)
                    if len(img) == 0:
                        img = np.zeros((detSize[3],detSize[1]))

                    srcReg = self._getRegion(self._splitFormat(header.get('DATASEC')))
                    dstReg = self._getRegion(self._splitFormat(header.get('DETSEC')))

                    regMinx, regMaxx, regMiny, regMaxy = min(dstReg[0].start, dstReg[0].stop), \
                        max(dstReg[0].start, dstReg[0].stop), \
                        min(dstReg[1].start, dstReg[1].stop), \
                        max(dstReg[1].start, dstReg[1].stop)

                    minx = min(minx, regMinx)
                    maxx = max(maxx, regMaxx)
                    miny = min(miny, regMiny)
                    maxy = max(maxy, regMaxy)

                    img[dstReg[1],dstReg[0]] = h.data[srcReg[1], srcReg[0]]
                    info.append((regMinx, regMaxx, regMiny, regMaxy))
                except Exception as e:
                    print ("While reading", fname, e)
                    return None
            self.minmax = minx,maxx,miny,maxx
            self.info = info
            return img

    def readCut (self, fname):
        img = self.read(fname)
        minmax = self.minmax
        return img[minmax[2]:minmax[3], minmax[0]:minmax[1]]

    def getKeyword(self, kwd):
        for h in self.hdrs:
            try:
                value = h.header.get(kwd)
                return value
            except:
                continue
        return None
            
        