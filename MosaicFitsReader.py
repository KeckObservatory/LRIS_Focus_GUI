import astropy.io.fits as pyfits
import numpy as np
import re

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
        Returns the raw image data.
        """
        
        #open
        print("reading...", fname)
        hdus = pyfits.open(fname, ignore_missing_end=True)
        #needed hdr vals
        self.hdrs = hdus
        hdr0 = hdus[0].header
        if len(hdus) == 2:
                return hdus[0].data
        binning  = hdr0['BINNING'].split(',')
        precol   = int(hdr0['PRECOL'])   // int(binning[0])
        postpix  = int(hdr0['POSTPIX'])  // int(binning[0])
        preline  = int(hdr0['PRELINE'])  // int(binning[1])
        postline = int(hdr0['POSTLINE']) // int(binning[1])

        #get extension order (uses DETSEC keyword)
        ext_order = self.get_ext_data_order(hdus)
        assert ext_order, "ERROR: Could not determine extended data order"

        #loop thru extended headers in order, create png and add to list in order
        vmin = None
        vmax = None
        alldata = None
        for i, ext in enumerate(ext_order):
            data = hdus[ext].data
            hdr  = hdus[ext].header

            #calc bias array from postpix area
            sh = data.shape
            x1 = 0
            x2 = sh[0]
            y1 = sh[1] - postpix + 1
            y2 = sh[1] - 1
            bias = np.median(data[x1:x2, y1:y2], axis=1)
            bias = np.array(bias, dtype=np.int64)

            #subtract bias
            data = data - bias[:,None]

            #get min max of each ext (not including pre/post pixels)
            #NOTE: using sample box that is 90% of full area
            #todo: should we take an average min/max of each ext for balancing?
            sh = data.shape
            x1 = int(preline          + (sh[0] * 0.10))
            x2 = int(sh[0] - postline - (sh[0] * 0.10))
            y1 = int(precol           + (sh[1] * 0.10))
            y2 = int(sh[1] - postpix  - (sh[1] * 0.10))

            #remove pre/post pix columns
            data = data[:,precol:data.shape[1]-postpix]

            #flip data left/right 
            #NOTE: This should come after removing pre/post pixels
            ds = self.get_detsec_data(hdr['DETSEC'])
            if ds and ds[0] > ds[1]: 
                data = np.fliplr(data)
            if ds and ds[2] > ds[3]: 
                data = np.flipud(data)

            #concatenate horizontally
            if i==0: alldata = data
            else   : alldata = np.append(alldata, data, axis=1)
        return alldata
        
    def get_ext_data_order(self,hdus):
        '''
        Use DETSEC keyword to figure out true order of extension data for horizontal tiling
        '''
        key_orders = {}
        for i in range(1, len(hdus)):
            ds = self.get_detsec_data(hdus[i].header['DETSEC'])
            if not ds: return None
            key_orders[ds[0]] = i

        orders = []
        for key in sorted(key_orders):
            orders.append(key_orders[key])
        return orders


    def get_detsec_data(self,detsec):
        '''
        Parse DETSEC string for x1, x2, y1, y2
        '''
        match = re.search( r'([+-]*\d+):([+-]*\d+),([+-]*\d+):([+-]*\d+)', detsec)
        if not match:
            return None
        else:
            x1 = int(match.groups(1)[0])
            x2 = int(match.groups(1)[1])
            y1 = int(match.groups(1)[2])
            y2 = int(match.groups(1)[3])
            return [x1, x2, y1, y2]

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
            


        