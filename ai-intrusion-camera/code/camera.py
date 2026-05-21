import cv2
import time
from config import CAMERA_ID


class Camera:

    def __init__(self, width=640, height=480):
        # Mở camera cơ bản nhất
        self.cap = cv2.VideoCapture(CAMERA_ID)

        # Set kích thước
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        if not self.cap.isOpened():
            print(f"[Camera] [ERROR] Không thể mở camera ID: {CAMERA_ID}")
        else:
            print(f"[Camera] Đã mở camera (ID: {CAMERA_ID})")

        # Xả buffer
        print("[Camera] Đang xả buffer...")
        for i in range(10): # Giảm xuống 10 frame
            self.cap.read()
            if i % 5 == 0: print(f"[Camera] Flushing... {i}")

        print("[Camera] Sẵn sàng!")


    def read(self):
        ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        self.cap.release()

