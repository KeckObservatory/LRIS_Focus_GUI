import sys,os,glob
import subprocess
from PyQt5.QtWidgets import QLabel,QHBoxLayout,QLineEdit,QPushButton,QVBoxLayout,QApplication,QAction,qApp,QWidget, QTextEdit, QGridLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import random
import numpy as np
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
        self.center_blu.setText("-3450")
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

        # defaults


        # analyze results
        self.expose_red = QPushButton("Take red focus images")
        self.expose_red.clicked.connect(self.takeRedImages)
        self.expose_blu = QPushButton("Take blue focus images")
        self.expose_blu.clicked.connect(self.takeBlueImages)
        self.analyze_red = QPushButton("Measure red focus")
        self.analyze_blu = QPushButton("Measure blue focus")
        self.analyze_blu.clicked.connect(self.analyzeFocus)
        self.output = QTextEdit()

        self.vlayout1 = QVBoxLayout()
        self.vlayout1.addLayout(self.grid)
        self.vlayout1.addStretch(1)
        self.vlayout1.addWidget(self.lampsOn)
        self.vlayout1.addWidget(self.expose_red)
        self.vlayout1.addWidget(self.expose_blu)
        self.vlayout1.addWidget(self.analyze_red)
        self.vlayout1.addWidget(self.analyze_blu)
        self.vlayout1.addWidget(self.output)

        self.figure = plt.figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        self.layout = QHBoxLayout()
        self.layout.addLayout(self.vlayout1)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)
        #self.plot()


    def plot(self):
        #data = [random.random() for i in range(10)]
        #ax = self.figure.add_subplot(111)
        ##ax.hold(False)
        #ax.plot(data, '*-')

        """
        Plots the (focus, std) pairs
        """
        plt.plot(self.pairs[0], self.pairs[1], 'o')
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

        self.canvas.draw()


    def analyzeFocus(self):
        # how many images do I look for:
        numberOfImages = int(self.number_blu.text())
        sender = self.sender()
        if sender == 'Measure red focus':
            prefix = 'rfoc*.fits'
            numberToAnalyze = self.number_red.text()
        elif sender == 'Measure blue focus':
            prefix = 'bfoc*.fits'
            numberToAnalyze = self.number_blu.text()

        output, errors = self.run_command('ssh lriseng@lrisserver outdir')
        directory = str(output.decode()).replace('\n','')
        #directory = '/s/sdata243/lriseng/2017dec10'
        self.files = glob.glob(os.path.join(directory,prefix))
        self.files.sort(key=os.path.getmtime)[-numberOfImages:]
        print(self.files)
        if len(self.files) > 0:
            self.out = SpecFocus.measureWidths(self.files)
            print(self.out)
            self.pairs = SpecFocus.generatePairs(self.out)
            self.funcV, self.m0, self.b0, self.minX = SpecFocus.fitPairs(self.pairs)
            self.plot()
        else:
            print("No files to examine in directory [%s]" % (directory))

    def turnOnLamps(self):
        self.run_command('modify -s lriscal neon=on')
        self.run_command('modify -s lriscal argon=on')
        self.run_command('modify -s lriscal mercury=on')
        self.run_command('modify -s lriscal cadmium=on')
        self.run_command('modify -s lriscal zinc=on')
        self.run_command('modify -s lriscal feargon=off')
        self.run_command('modify -s lriscal deuteri=off')
        self.run_command('modify -s lriscal halogen=off')

    def takeBlueImages(self):
        center = self.center_blu.text()
        step = self.step_blu.text()
        number = self.number_blu.text()
        startingPoint = center-(step*int(number/2))
        command = "ssh lriseng@lrisserver focusloop blue %s %s %s" % (startingPoint,number,step)
        self.run_command(command)

    def takeRedImages(self):
        center = self.center_red.text()
        step = self.step_red.text()
        number = self.number_red.text()
        startingPoint = center-(step*int(number/2))
        command = "ssh lriseng@lrisserver focusloop red %s %s %s" % (startingPoint,number,step)
        self.run_command(command)


    def run_command(self, command):
        #try:
        #    kroot = os.environ['KROOT']
        #except:
        #    kroot = ''
        #cmdline = os.path.join(kroot, 'bin', command)
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
        self.output.setText(str(output))
        if errors:
            self.output.setText(str(errors))

        return output, errors

if __name__ == "__main__":
    main()
