import speedtest
import sys
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow#, QDesktopWidget
from main import *

class worker_class(QThread):
    worker = pyqtSignal(list)
    def __init__(self,type):
        super(QThread, self).__init__()
        self.type=type
    def run(self):
        #upload_speed = self.test.upload()
        #download_speed = self.test.download()
        try:
            self.test = speedtest.Speedtest()
            self.test.get_best_server()
            speed = self.test.upload() if self.type=='upload' else self.test.download()
        #self.worker.emit(download_speed/10**6,upload_speed/10**6)
        #speed = 'Check Your Internet Connectivity' if speed/10**6<0.01 else speed
        except Exception as e:
            print("No Network",str(e))
            speed = 0
            
        self.worker.emit([self.type,speed/10**6])

class MyMainWindow(QMainWindow):
    def __init__(self):
        super(MyMainWindow,self).__init__()
        self.loading_image = QMovie('loading.gif')
        self.no_internet = QMovie('no_internet.gif')
        self.ui = Ui_MainWindow()
        #self.geometry = QDesktopWidget().screenGeometry()
        self.ui.setupUi(self)
        self.ui.uploadButton.clicked.connect(lambda:self.calculateSpeed('upload'))
        self.ui.downloadButton.clicked.connect(lambda:self.calculateSpeed('download'))
        self.ui.label2.setMovie(self.loading_image)
        self.ui.actionFullscreen.triggered.connect(lambda:self.showFullScreen())
        self.ui.actionExitFullScreen.triggered.connect(lambda:self.showNormal())
        self.ui.actionExit.triggered.connect(lambda:exit(0))
        self.ui.label.setText("Internet Speed Tester")
        
        #self.setMaximumSize(self.geometry.width()/2,self.geometry.height()/2)
        
    #def reset(self):
    #    self.ui.label2.setMovie(self.loading_image)
        
    
    def calculateSpeed(self,type):
        self.ui.uploadButton.setEnabled(False) if type=='upload' else self.ui.downloadButton.setEnabled(False)
        self.ui.label2.setMovie(self.loading_image)
        self.loading_image.start()
        self.worker_object = worker_class(type)
        self.worker_object.start()
        #self.loading_image.start()
        self.ui.label.setText(f"Calculating {type} Speed..")
        self.worker_object.worker.connect(self.showSpeed)
    
    
    def showSpeed(self,speed):
        self.loading_image.stop()
        if speed[1]<0.01:
            self.ui.label.setText("No Internet. Check Your Internet Connectivity..")
            self.ui.label2.setMovie(self.no_internet)
            self.no_internet.start()
        else:
            self.ui.label2.setMovie(self.loading_image)
            self.loading_image.start()
            self.ui.label.setText(f"Upload Speed: {speed[1]:.2f} Mbps") if speed[0]=='upload' else self.ui.label.setText(f"Download Speed: {speed[1]:.2f} Mbps")
            self.loading_image.stop()
            
        self.ui.uploadButton.setEnabled(True)
        self.ui.downloadButton.setEnabled(True)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MyMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

