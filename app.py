

import numpy as np,cv2,os,sys, _io
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QVBoxLayout, QApplication
from pyqtgraph import ImageView
from typing import *

def read_id()->int:
    def write_fresh():
        f:_io.TextIOWrappe = open('/home/ibex/Documents/ID','w')
        f.write('0')
        f.close()
    if os.path.exists('/home/ibex/Documents/ID'):
        f:_io.TextIOWrappe = open('/home/ibex/Documents/ID','r')
        try:
            id= eval(f.readline())
            f.close()
        except:
            f.close()
            write_fresh()    
    else:
        f:_io.TextIOWrappe = open('/home/ibex/Documents/ID','w')
        f.write('0')
        f.close()
        return 0
    return id

def write_id(id:int)->bool:
    f:_io.TextIOWrappe = open('/home/ibex/Documents/ID','w')
    f.write(str(id))
    f.close()
    return True

def create_barn(id:int)->str:
    p:str = f'/home/ibex/Pictures/{id}'
    if os.path.exists(p):
        return p
    os.mkdir(p)
    return p

class motion_detector():
    sensitivity:int
    threshold: int
    def __init__(self,sensitivity:int=50,threshold:int=30) -> None:
        # sensitivity is in percents
        _max = int(round(120*160/25))
        self.sensitivity=int(round(_max*sensitivity/100)) #px
        self.threshold = threshold
        
    def __call__(self, images:List[np.ndarray]) -> bool:
        threshold:np.ndarray
        motion_mask:np.ndarray
        # input should have 5 images at least
        images0:List[np.ndarray] = images[:-1]
        images1:List[np.ndarray] = images[1:]
        # Compute absolute difference between consecutive images
        diffs:List[np.ndarray] = [cv2.absdiff(i0,i1) for i0,i1 in zip(images0,images1)]
        # Threshold the differences to create binary motion masks
        thresholds:List[np.ndarray] = [cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)[1] for diff in diffs ]
        # Perform bitwise OR operation to combine the motion masks
        motion_mask:List[np.ndarray] = cv2.bitwise_or(thresholds[0], thresholds[1])
        for threshold in thresholds[2:]:    
            motion_mask = cv2.bitwise_or(motion_mask, threshold)
        motion_mask = cv2.cvtColor(motion_mask,cv2.COLOR_BGR2GRAY)
        # Check if motion is detected
        '''
        print('=============================================')
        print(motion_mask.shape)
        print('=============================================')
        '''
        if cv2.countNonZero(motion_mask) > self.sensitivity:
            return True
        return False


class MovieThread(QThread):
    camera:cv2.VideoCapture
    def __init__(self, camera:cv2.VideoCapture):
        super().__init__()
        self.camera = camera

    def run(self):
        pass
        #self.camera.acquire_movie(200)

class StartWindow(QMainWindow):
    id:int
    motion_frames:List[np.ndarray]
    save_path:str
    camera:cv2.VideoCapture
    central_widget:QWidget
    button_movie:QPushButton
    image_view:ImageView
    layout:QVBoxLayout
    update_timer:QTimer
    movie_thread:MovieThread
    moving:motion_detector
    
    def __init__(self)->None:
        super().__init__()
        self.id = read_id()
        self.motion_frames = []
        self.save_path = create_barn(self.id)
        self.camera = cv2.VideoCapture(0)
        self.central_widget = QWidget()
        self.moving = motion_detector(sensitivity=30)
        # self.button_frame = QPushButton('Acquire Frame', self.central_widget)
        self.button_movie = QPushButton('Start Movie', self.central_widget)
        self.image_view = ImageView()

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.addWidget(self.image_view)
        self.setCentralWidget(self.central_widget)

        self.button_movie.clicked.connect(self.start_movie)
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_movie)
        self.button_movie.click()
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        self.showMaximized()

    def update_image(self)->None:
        return_value:bool
        frame:np.ndarray
        return_value, frame = self.camera.read()
        frame = cv2.transpose(frame,frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.rotate(frame,cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.image_view.setImage(frame)

    def update_movie(self)->None:
        return_value:bool
        frame:np.ndarray
        return_value, frame = self.camera.read()
        if not return_value:return
        self.motion_frames.append(frame)
        isMoving:bool=False
        if len(self.motion_frames)>=5:
            isMoving = self.moving(self.motion_frames)
            self.motion_frames.pop(0)

        if isMoving:
            cv2.imwrite(f'{self.save_path}/{self.id}.png',frame)
            self.id+=1
            write_id(self.id)
        
        frame = cv2.transpose(frame,frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.rotate(frame,cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        if isMoving:
            frame = cv2.circle(frame,(10,10),3,(255,0,0),-1)

        self.image_view.setImage(frame)

    def update_brightness(self, value):
        value /= 10
        self.camera.set_brightness(value)
    
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.camera.release()
        return super().closeEvent(a0)

    def start_movie(self)->None:
        self.movie_thread = MovieThread(self.camera)
        self.movie_thread.start()
        self.update_timer.start(1)

if __name__ == '__main__':
    app = QApplication([])
    window = StartWindow()
    window.show()
    app.exit(app.exec_())
