import glob
import os

import subprocess
import sys

import ktl

import matplotlib.pyplot as plt
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QApplication, QWidget, QTextEdit, \
    QGridLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


import SpecFocus


def main():
    app = QApplication(sys.argv)
    w = MyWindow()
    w.show()
    sys.exit(app.exec_())


class MyWindow(QWidget):
    def __init__(self, *args):
        super().__init__()
        self.runMode = 'normal'
        self.lris = ktl.cache('lris')
        self.lrisblue = ktl.cache('lrisblue')
        #self.runMode = 'debug'
        self.init_ui()

    def init_ui(self):
        # create objects
        # labels

        # turn on all lampss
        self.grid = QGridLayout()
        self.lampsOn = QPushButton('Turn on arc lamps')
        self.lampsOn.clicked.connect(self.turnOnLamps)
        # labels and buttons for the focus loop
        self.center_lbl = QLabel("Center")
        self.step_lbl = QLabel("Step")
        self.number_lbl = QLabel("Number")
        self.red_lbl = QLabel("Red")
        self.blu_lbl = QLabel("Blue")

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


        # analyze self.expose_red = QPushButton("Take red focus images")
        self.expose_red = QPushButton("Take red focus images")
        self.expose_red.clicked.connect(self.takeRedImages)
        self.expose_blu = QPushButton("Take blue focus images")
        self.expose_blu.clicked.connect(self.takeBlueImages)
        self.analyze_red = QPushButton("Measure red focus")
        self.analyze_blu = QPushButton("Measure blue focus")
        self.analyze_blu.clicked.connect(self.analyzeFocus)
        self.analyze_red.clicked.connect(self.analyzeFocus)
        self.output = QTextEdit()

        # create process calls
        self.redimages = QtCore.QProcess(self)
        self.bluimages = QtCore.QProcess(self)
        self.redimages.readyRead.connect(self.dataReady)
        self.bluimages.readyRead.connect(self.dataReady)
        self.redimages.started.connect(lambda: self.expose_red.setEnabled(False))
        self.redimages.finished.connect(self.redSideDone)
        self.bluimages.started.connect(lambda: self.expose_blu.setEnabled(False))
        self.bluimages.finished.connect(self.bluSideDone)

        self.qbtn = QPushButton("Done and Quit")
        self.qbtn.clicked.connect(self.allDone)
        self.vlayout1 = QVBoxLayout()
        self.vlayout1.addLayout(self.grid)
        self.vlayout1.addStretch(1)
        self.vlayout1.addWidget(self.lampsOn)
        self.vlayout1.addWidget(self.expose_red)
        self.vlayout1.addWidget(self.expose_blu)
        self.vlayout1.addWidget(self.analyze_red)
        self.vlayout1.addWidget(self.analyze_blu)
        self.vlayout1.addWidget(self.qbtn)
        self.vlayout1.addWidget(self.output)

        self.figure = plt.figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        self.layout = QHBoxLayout()
        self.layout.addLayout(self.vlayout1)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)




    def allDone(self):

        self.close()

    def dataReady(self):
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(str(self.redimages.readAll(), 'utf-8'))
        cursor.insertText(str(self.bluimages.readAll(), 'utf-8'))
        self.output.ensureCursorVisible()

    def showOutput(self, text):
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.output.ensureCursorVisible()

    def plot(self):

        plt.clf()

        """
        Plots the (focus, std) pairs
        """

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
        # how many images do I look for:
        sender = self.sender().text()
        print("The sender is %s" % (str(sender)))
        if sender == 'Measure red focus':
            prefix = 'rfoc*.fits'
            numberToAnalyze = int(self.number_red.text())
        elif sender == 'Measure blue focus':
            prefix = 'bfoc*.fits'
            numberToAnalyze = int(self.number_blu.text())

        output, errors = self.run_command('ssh lriseng@lrisserver outdir')
        directory = str(output.decode()).replace('\n', '')

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
        else:
            print("No files to examine in directory [%s]" % (directory))

    def turnOnLamps(self):
        self.lriscal = ktl.cache('self.lriscal')
        self.lriscal['neon'].write('on')
        self.lriscal['mercury'].write('on')
        self.lriscal['cadmium'].write('on')
        self.lriscal['zinc'].write('on')
        self.lriscal['feargon'].write('off')
        self.lriscal['deuteri'].write('off')
        self.lriscal['halogen'].write('off')


    def saveRedState(self):
        self.originalPrefixRed = self.lris['outfile'].read()
        binningx,binningy = self.lris['binning'].read(binary=True)
        self.binningRed = '%s,%s' % (binningx, binningy)

    def saveBluState(self):
        output, errors = self.run_command('show -s lrisblue -terse outfile')
        self.originalPrefixBlu = self.lrisblue['outfile'].read()
        binningx,binningy = self.lris['binning'].read(binary=True)
        self.binningBlu = '%s,%s' % (binningx, binningy)

    def redSideDone(self):
        self.expose_red.setEnabled(True)
        self.lris['outfile'].write(self.originalPrefixRed)
        self.lris['ccdspeed'].write('normal')
        self.lris['binning'].write(self.binningRed)

    def bluSideDone(self):
        self.expose_blu.setEnabled(True)
        self.lrisblue['outfile'].write(self.originalPrefixBlu)
        self.lrisblue['numamps'].write(4)
        self.lrisblue['amplist'].write('1,4,0,0')
        self.lrisblue['ccdsel'].write('mosaic')
        self.lrisblue['binning'].write('1,1')
        self.lrisblue['window'].write('1,0,0,2048,4096')
        self.lrisblue['prepix'].write(51)
        self.lrisblue['postpix'].write(80)
        self.lrisblue['binning'].write(self.binningBlu)

    def takeRedImages(self):
        self.saveRedState()
        self.lris['outfile'].write('rfoc_')
        self.lris['binning'].write('1,1')
        self.lris['pane'].write('0,0,4096,4096')
        self.lris['ttime'].write(1)
        self.lris['ccdspeed'].write('fast')

        center = self.center_red.text()
        step = self.step_red.text()
        number = self.number_red.text()
        startingPoint = str(float(center) - (float(step) * int(number) / 2))
        self.redimages.start('ssh', ['lriseng@lrisserver', 'focusloop', 'red', startingPoint, number, step])

    def takeBlueImages(self):
        self.saveBluState()
        self.lrisblue['outfile']=('bfoc_')
        self.lrisblue['numamps'].write(4)
        self.lrisblue['amplist'].write('1,4,0,0')
        self.lrisblue['ccdsel'].write('mosaic')
        self.lrisblue['binning'].write('1,1')
        self.lrisblue['window'].write('1,0,0,2048,4096')
        self.lrisblue['prepix'].write(51)
        self.lrisblue['postpix'].write(80)
        self.lrisblue['ttime'].write(1)

        center = self.center_blu.text()
        step = self.step_blu.text()
        number = self.number_blu.text()
        startingPoint = str(float(center) - (float(step) * int(number) / 2))
        self.bluimages.start('ssh', ['lriseng@lrisserver', 'focusloop', 'blue', startingPoint, number, step])

    def run_command(self, command):
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
        #self.output.setText(str(output))
        if len(errors)>0:
            output = output+errors
        self.showOutput(str(output.decode()).replace('\n', ''))
        self.showOutput('\n')

        return output, errors


if __name__ == "__main__":
    main()
