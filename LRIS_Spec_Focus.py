import glob
import os
import subprocess
import sys
import time
import traceback

try:
    import ktl
    useKTL = True
except:
    print("KTL functions are not available")
    useKTL = False

import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QApplication, QWidget, QTextEdit, \
    QGridLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# this imports the module written by S. Kwok.
import SpecFocus


def main():
    app = QApplication(sys.argv)
    w = MyWindow()
    w.show()
    sys.exit(app.exec_())
class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    finished = pyqtSignal()
    started = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    output = pyqtSignal(object)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        self.kwargs['output_callback'] = self.signals.output

    @pyqtSlot()
    def run(self):
        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.signals.started.emit()
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done




class MyWindow(QWidget):
    def __init__(self, *args):
        super().__init__()
        # runMode can be set to debug if we don't want to run the command, but just see that the buttons are connected correctly
        self.runMode = 'normal'
        # creation of KTL services for lris and lrisblue
        if useKTL:
            self.lris = ktl.cache('lris')
            self.lrisblue = ktl.cache('lrisblue')
        # call to the main routine to create the interface
        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        self.init_ui()

    def init_ui(self):
        # create objects

        self.redColor = 'LightCoral'
        self.bluColor = 'SkyBlue'
        self.genericColor = 'Gold'
        self.doneColor = 'LawnGreen'

        # turn on all lamps
        self.grid = QGridLayout()
        self.lampsOn = QPushButton('Turn on arc lamps')
        self.lampsOn.setStyleSheet("background-color: %s" % self.genericColor)
        self.lampsOn.clicked.connect(self.run_turnOnLamps)
        # turn off all lamps
        self.lampsOff = QPushButton('Turn off arc lamps')
        self.lampsOff.setStyleSheet("background-color: %s" % self.genericColor)
        self.lampsOff.clicked.connect(self.run_turnOffLamps)

        # labels and buttons for the focus loop
        self.center_lbl = QLabel("Center")
        self.step_lbl = QLabel("Step")
        self.number_lbl = QLabel("Number")
        self.red_lbl = QLabel("Red")
        self.blu_lbl = QLabel("Blue")

        # default values for the focus loop
        self.center_red = QLineEdit()
        self.center_red.setText("-0.60")
        self.step_red = QLineEdit()
        self.step_red.setText("0.05")
        self.number_red = QLineEdit()
        self.number_red.setText("7")

        self.center_blu = QLineEdit()
        self.center_blu.setText("-3550")
        self.step_blu = QLineEdit()
        self.step_blu.setText("90")
        self.number_blu = QLineEdit()
        self.number_blu.setText("7")

        # grid arrangement for the default values for the focus loop
        self.grid.addWidget(self.red_lbl, 1, 0)
        self.grid.addWidget(self.blu_lbl, 2, 0)
        self.grid.addWidget(self.center_lbl, 0, 1)
        self.grid.addWidget(self.step_lbl, 0, 2)
        self.grid.addWidget(self.number_lbl, 0, 3)
        self.grid.addWidget(self.center_red, 1, 1)
        self.grid.addWidget(self.step_red, 1, 2)
        self.grid.addWidget(self.number_red, 1, 3)
        self.grid.addWidget(self.center_blu, 2, 1)
        self.grid.addWidget(self.step_blu, 2, 2)
        self.grid.addWidget(self.number_blu, 2, 3)

        # buttons to run the focus loop

        self.expose_red = QPushButton("Take red focus images")
        self.expose_red.setStyleSheet("background-color: %s" % self.redColor)
        self.expose_red.clicked.connect(self.takeRedImages)

        self.expose_blu = QPushButton("Take blue focus images")
        self.expose_blu.setStyleSheet("background-color: %s" % self.bluColor)
        self.expose_blu.clicked.connect(self.takeBlueImages)

        self.analyze_red = QPushButton("Measure red focus")
        self.analyze_red.setStyleSheet("background-color: %s" % self.redColor)
        self.analyze_blu = QPushButton("Measure blue focus")
        self.analyze_blu.setStyleSheet("background-color: %s" % self.bluColor)

        self.analyze_blu.clicked.connect(self.analyzeFocus)
        self.analyze_red.clicked.connect(self.analyzeFocus)
        self.output = QTextEdit()

        # create process calls. Here we use the built-in PYQT5 process management
        #self.redimages = QtCore.QProcess(self)
        #self.bluimages = QtCore.QProcess(self)
        # connect the output of each process to a dataReady function
        #self.redimages.readyRead.connect(self.dataReady)
        #self.bluimages.readyRead.connect(self.dataReady)
        # connect the start of a process to a simple function to disable the button (so we don't run it twice)
        # and connect the end of the process to a cleanup function
        #self.redimages.started.connect(lambda: self.expose_red.setEnabled(False))
        #Self.redimages.finished.connect(self.redSideDone)
        #self.bluimages.started.connect(lambda: self.expose_blu.setEnabled(False))
        #self.bluimages.finished.connect(self.bluSideDone)


        # add buttons to set the focus
        self.setBluFocus = QPushButton("Set blue camera focus")
        self.setBluFocus.setStyleSheet("background-color: %s" % self.bluColor)
        self.setRedFocus = QPushButton("Set red camera focus")
        self.setRedFocus.setStyleSheet("background-color: %s" % self.redColor)
        self.setBluFocus.clicked.connect(self.setFocus)
        self.setRedFocus.clicked.connect(self.setFocus)

        # add a "quit" button
        self.qbtn = QPushButton("Done and Quit")
        self.qbtn.setStyleSheet("background-color: %s" % self.doneColor)
        self.qbtn.clicked.connect(self.allDone)

        # the main layout
        self.vlayout1 = QVBoxLayout()
        self.vlayout1.addLayout(self.grid)
        self.vlayout1.addStretch(1)
        self.vlayout1.addWidget(self.lampsOn)
        self.vlayout1.addWidget(self.expose_red)
        self.vlayout1.addWidget(self.expose_blu)
        self.vlayout1.addWidget(self.analyze_red)
        self.vlayout1.addWidget(self.analyze_blu)
        self.vlayout1.addWidget(self.lampsOff)
        self.vlayout1.addWidget(self.setBluFocus)
        self.vlayout1.addWidget(self.setRedFocus)
        self.setBluFocus.setEnabled(False)
        self.setRedFocus.setEnabled(False)
        self.vlayout1.addWidget(self.qbtn)
        self.vlayout1.addWidget(self.output)

        self.figure = plt.figure(figsize=(5, 5))
        self.canvas = FigureCanvas(self.figure)
        self.layout = QHBoxLayout()
        self.layout.addLayout(self.vlayout1)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)

    def setFocus(self):
        sender =  self.sender().text()
        if sender == 'Set blue camera focus':
            lris = ktl.cache('lris')
            lris['blufocus'].write(self.bestBluFocus)
            self.showOutput("\nBlue focus set to %s\n" % str(self.bestBluFocus))
        elif sender == 'Set red camera focus':
            lris = ktl.cache('lris')
            lris['redfocus'].write(self.bestRedFocus)
            self.showOutput("\nRed focus set to %s\n" % str(self.bestRedFocus))


    def allDone(self):

        """
        Closes the GUI and quit
        """
        self.close()

    def dataReady(self):
        """
        Captures the output of background processes using the readAll() method
        """
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(str(self.redimages.readAll(), 'utf-8'))
        cursor.insertText(str(self.bluimages.readAll(), 'utf-8'))
        self.output.ensureCursorVisible()

    def showOutput(self, text):
        """
        Used to display a generic string into the output textbox
        @param text: Text to display
        """
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.output.ensureCursorVisible()

    def plot(self):
        """
        Plots the (focus, std) pairs
        """
        plt.clf()

        xpoints = set(self.pairs[0])
        print(xpoints)
        uniqueX = []
        uniqueY = []
        for point in xpoints:
            print(point)
            selectedPoints = self.pairs[1][(self.pairs[0] == point)]
            averagePoint = np.median(selectedPoints)
            uniqueY= np.append(uniqueY, averagePoint)
            uniqueX= np.append(uniqueX, point)

        #plt.plot(self.pairs[0], self.pairs[1], 'o')
        print(uniqueX)
        print(uniqueY)
        plt.plot(uniqueX, uniqueY, 'o')
        padding = 10  # this means 10% of the range will be added to each side of the plot

        plotRange = max(self.pairs[0]) - min(self.pairs[0])
        x0, x1 = min(self.pairs[0]) - plotRange / 100 * padding, max(self.pairs[0]) + plotRange / 100 * padding
        # x0, x1 = -4000, -3000 # min(pairs[0]), max(pairs[0])
        # x0, x1 = -0.8,-0.5
        """
        Plots the fitted hyperbola
        """
        xs = np.linspace(x0, x1, 100)
        plt.plot(xs, self.funcV(xs))

        """
        Plots a vertical line at best focus and a horizontal line at best focus
        """
        plt.plot((x0, x1), (self.funcV(self.minX), self.funcV(self.minX)), 'k:')
        plt.plot((self.minX, self.minX), (min(self.pairs[1]), max(self.pairs[1])), 'k:')

        """
        Plots the asymptotes
        """
        posAsymp = SpecFocus.asympFunc(self.m0, self.b0)
        negAsymp = SpecFocus.asympFunc(-self.m0, -self.b0)

        plt.plot((x0, self.minX), (negAsymp(x0), negAsymp(self.minX)), 'g-')
        plt.plot((self.minX, x1), (posAsymp(self.minX), posAsymp(x1)), 'g-')
        plt.grid()
        plt.title("Focus: %.2f" % (float(self.minX)))

        self.canvas.draw()


    def analyzeFocus(self):
        """
        Reads the selected number of images and produces the data to be plotted
        """
        # how many images do I look for:
        sender = self.sender().text()
        if sender == 'Measure red focus':
            prefix = 'rfoc*.fits'
            numberToAnalyze = int(self.number_red.text())
        elif sender == 'Measure blue focus':
            prefix = 'bfoc*.fits'
            numberToAnalyze = int(self.number_blu.text())

        # location of the output images
        directory = '/s'+self.lris['outdir'].read()

        self.files = glob.glob(os.path.join(directory, prefix))
        self.files.sort(key=os.path.getmtime)
        self.files = self.files[-numberToAnalyze:]
        self.showOutput("Files to be analyzed: %s \n" % (str(self.files)))
        if len(self.files) > 0:
            self.out = SpecFocus.measureWidths(self.files)
            print(self.out)
            self.pairs = SpecFocus.generatePairs(self.out)
            self.funcV, self.m0, self.b0, self.minX = SpecFocus.fitPairs(self.pairs)
            self.plot()
            self.showOutput("\nThe Focus is %.2f" % (float(self.minX)))
            if sender == 'Measure red focus':
                self.bestRedFocus = self.minX
                self.setRedFocus.setEnabled(True)
            elif sender == 'Measure blue focus':
                self.bestBluFocus = self.minX
                self.setBluFocus.setEnabled(True)

        else:
            print("No files to examine in directory [%s]" % (directory))

    def run_turnOnLamps(self):
        """
        Turn on the calibration lamps
        """
        worker = Worker(self.turnOnLamps)
        worker.signals.started.connect(lambda: self.lampsOn.setEnabled(False))
        worker.signals.result.connect(self.showOutput)
        worker.signals.output.connect(self.showOutput)
        worker.signals.finished.connect(lambda: self.lampsOn.setEnabled(True))
        self.threadpool.start(worker)

    def turnOnLamps(self, output_callback):
        if useKTL:
            output_callback.emit("\nTurning on arc lamps.\n")
            lriscal = ktl.cache('lriscal')
            output_callback.emit("Argon..")
            lriscal['argon'].write('on')
            output_callback.emit("Neon..")
            lriscal['neon'].write('on')
            output_callback.emit("Mercury..")
            lriscal['mercury'].write('on')
            output_callback.emit("Cadmium..")
            lriscal['cadmium'].write('on')
            output_callback.emit("Zinc..\n")
            lriscal['zinc'].write('on')
            output_callback.emit("Turning off FeAr, Deuterium and Halogen\n")
            lriscal['feargon'].write('off')
            lriscal['deuteri'].write('off')
            lriscal['halogen'].write('off')
            output_callback.emit("\nLamps are on. \n Please wait 3 minutes for blue lamps to warm up.\n")
        else:
            output_callback.emit("\n KTL is NOT ENABLED")

    def run_turnOffLamps(self):
        worker = Worker(self.turnOffLamps)
        worker.signals.started.connect(lambda: self.lampsOff.setEnabled(False))
        worker.signals.result.connect(self.showOutput)
        worker.signals.output.connect(self.showOutput)
        worker.signals.finished.connect(lambda: self.lampsOff.setEnabled(True))
        self.threadpool.start(worker)

    def turnOffLamps(self, output_callback):
        """
        Turn off the calibration lamps
        """
        if useKTL:
            lriscal = ktl.cache('lriscal')

            output_callback.emit("\nTurning off arc lamps.\n")
            lriscal['argon'].write('off')
            lriscal['neon'].write('off')
            lriscal['mercury'].write('off')
            lriscal['cadmium'].write('off')
            lriscal['zinc'].write('off')
            lriscal['feargon'].write('off')
            lriscal['deuteri'].write('off')
            lriscal['halogen'].write('off')
            output_callback.emit("\nLamps are off.\n")
        else:
            output_callback.emit("\n KTL is NOT ENABLED")

    def saveRedState(self):
        """
        Save original parameters for red side
        """
        if useKTL:
            self.originalPrefixRed = self.lris['outfile'].read()
            self.binningx_red,self.binningy_red = self.lris['binning'].read(binary=True)


    def saveBluState(self):
        """
        Save original parameters for blue side
        """
        if useKTL:
            self.originalPrefixBlu = self.lrisblue['outfile'].read()
            self.binningx_blu,self.binningy_blu = self.lris['binning'].read(binary=True)

    def redSideDone(self):
        """
        Run when the red side images have been taken, to restore binning, ccdspeed, and original file names
        """
        self.expose_red.setEnabled(True)
        self.showOutput("Red side focus images complete\n")
        if useKTL:
            self.lris['outfile'].write(self.originalPrefixRed)
            self.lris['ccdspeed'].write('normal')
            self.lris['binning'].write([self.binningx_red,self.binningy_red])

    def bluSideDone(self):
        """
        Run when the blue side images have been taken, to restore binning, ccdspeed, and original file names
        """
        self.expose_blu.setEnabled(True)
        self.showOutput("Blue side focus images complete\n")
        if useKTL:
            self.lrisblue['outfile'].write(self.originalPrefixBlu)
            self.lrisblue['numamps'].write(4)
            self.lrisblue['amplist'].write([1,4,0,0])
            self.lrisblue['ccdsel'].write('mosaic')
            self.lrisblue['binning'].write([1,1])
            self.lrisblue['window'].write([1,0,0,2048,4096])
            self.lrisblue['prepix'].write(51)
            self.lrisblue['postpix'].write(80)
            self.lrisblue['binning'].write([self.binningx_blu,self.binningy_blu])

    def takeRedImages(self):
        """
        Using an ssh to lrisserver (which might not be needed), run the focus loop
        """
        self.saveRedState()
        if useKTL:
            self.lris['outfile'].write('rfoc_')
            self.lris['binning'].write([1,1])
            self.lris['pane'].write([0,0,4096,4096])
            self.lris['ttime'].write(1)
            self.lris['ccdspeed'].write('fast')
            self.lris['object'].write('Focus loop')

        center = float(self.center_red.text())
        step = float(self.step_red.text())
        number = int(self.number_red.text())
        startingPoint = float(center - (step * (number / 2)))

        worker = Worker(self.focusloop, 'red', startingPoint, number, step)
        worker.signals.started.connect(lambda: self.expose_red.setEnabled(False))
        worker.signals.result.connect(self.showOutput)
        worker.signals.output.connect(self.showOutput)
        worker.signals.finished.connect(self.redSideDone)
        self.threadpool.start(worker)


    def takeBlueImages(self):
        """
        Using an ssh to lrisserver (which might not be needed), run the focus loop
        """
        self.saveBluState()
        if useKTL:
            self.lrisblue['outfile'].write('bfoc_')
            self.lrisblue['numamps'].write(4)
            self.lrisblue['amplist'].write([1,4,0,0])
            self.lrisblue['ccdsel'].write('mosaic')
            self.lrisblue['binning'].write([1,1])
            self.lrisblue['window'].write([1,0,0,2048,4096])
            self.lrisblue['prepix'].write(51)
            self.lrisblue['postpix'].write(80)
            self.lrisblue['ttime'].write(1)
            self.lris['object'].write('Focus loop')

        center = float(self.center_blu.text())
        step = int(self.step_blu.text())
        number = int(self.number_blu.text())
        startingPoint = float(center - (step * (number / 2)))

        worker = Worker(self.focusloop,'blue',startingPoint, number, step)
        worker.signals.started.connect(lambda: self.expose_blu.setEnabled(False))
        worker.signals.result.connect(self.showOutput)
        worker.signals.output.connect(self.showOutput)
        worker.signals.finished.connect(self.bluSideDone)
        self.threadpool.start(worker)
        #self.bluimages.start('ssh', ['lriseng@lrisserver', 'focusloop', 'blue', startingPoint, number, step])
        #self.bluimages.start('focusloop', ['blue', startingPoint, number, step])

    def setLrisFocus(self,side, value, output_callback):

        if useKTL is False:
            output_callback.emit("KTL not available, not setting focus\n")
            return
        lris= ktl.cache('lris')
        if side == 'red':
            keyword = lris['redfocus']
        elif side == 'blue':
            keyword = lris['blufocus']
            if value<-3820:
                output_callback.emit("Blue focus value is beyond limits. Resetting to -3820\n")
                value = -3820
        else:
            return
        keyword.write(value)
        output_callback.emit("\n%s focus set to %s\n" % (side, str(value)))

    def focusloop(self, side, startingPoint, number_of_steps, increment, output_callback):

        backlash_correction = {}
        backlash_correction['red'] = -1.0
        backlash_correction['blue'] = -200

        if side not in ['red', 'blue']:
            output_callback.emit(self, 'Error in side specification')
            return

        if number_of_steps > 100:
            output_callback.emit(self, 'Too many steps requested')
            return

        # backlash correction
        self.setLrisFocus(side, startingPoint + backlash_correction[side], output_callback)

        for step in range(0,number_of_steps-1):
            focus = startingPoint + step * increment
            self.setLrisFocus(side, focus, output_callback)
            #print("Acquiring %s image at focus value %f\n" % (side,focus))

            #self.showOutput("Acquiring %s image at focus value %f\n" % (side,focus))
            output_callback.emit("Image %d of %d: %s image at focus value %f\n" % (step+1, number_of_steps,side,focus))
            if side == 'red':
                self.goir()
            elif side == 'blue':
                self.goib()


    def goib(self):
        if useKTL is False:
            time.sleep(1)
            return
        # create and monitor keywords
        lrisb = ktl.cache('lrisblue')
        exposip = lrisb['exposip']
        wcrate = lrisb['wcrate']
        rserv = lrisb['rserv']
        #object = lrisb['object']
        ttime = lrisb['ttime']
        expose = lrisb['expose']
        keywords = [exposip, wcrate, rserv, ttime]
        for key in keywords:
            key.monitor()

        # make sure no other exposure is in progress
        exposip.waitFor('==False')
        wcrate.waitFor('==False')
        rserv.waitFor('==False')

        # start the exposure
        expose.write(True, wait=True)

        # wait for end of exposure
        wcrate.waitFor('==True')
        wcrate.waitFor('==False', timeout = 200)
        rserv.waitFor('==False', timeout = 200)

    def goir(self):
        if useKTL is False:
            time.sleep(1)
            return
        # create and monitor keywords
        lris = ktl.cache('lris')
        observip = lris['observip']
        #exposip = lrib['exposip']
        wcrate = lris['wcrate']
        #rserv = lrisb['rserv']
        #object = lrib['object']
        #ttime = lrisb['ttime']
        expose = lris['expose']
        keywords = [observip, wcrate]
        for key in keywords:
            key.monitor()

        # make sure no other exposure is in progress
        observip.waitFor('==False')

        # start the exposure
        expose.write(True, wait=True)

        # wait for end of exposure
        wcrate.waitFor('==True')
        observip.waitFor('==False', timeout = 200)


    def run_command(self, command):
        """
        Generic routine to run a command with call to the operating system
        @param command: Command to run
        @param return: Return code
        """
        cmdline = command
        if self.runMode is 'debug':
            self.output.setText('Simulation mode\n Running:\n %s' % (cmdline))
            return '', ''
        try:
            p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output, errors = p.communicate()
        except RuntimeError:
            output = ''
            errors = 'Cannot execute command %s' % command
        except FileNotFoundError:
            output = ''
            errors = 'The command does not exist'
        if len(errors)>0:
            output = output+errors
        self.showOutput(str(output.decode()).replace('\n', ''))
        self.showOutput('\n')

        return output, errors


if __name__ == "__main__":
    main()
