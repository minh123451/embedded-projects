import cv2
import threading
import time
from camera import Camera
from config import WIDTH, HEIGHT, FPS_TARGET

class CameraService:
    def __init__(self):
        self.camera = Camera(width=WIDTH, height=HEIGHT)
        self.raw_frame = None
        self.running = False
        self.lock = threading.Lock()
        self._thread = None
        self.frame_id = 0

    def start(self):
        """Khởi chạy luồng capture camera"""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            print("[CameraService] Thread started.")

    def stop(self):
        """Dừng camera"""
        self.running = False
        if self._thread:
            self._thread.join()
        self.camera.release()
        print("[CameraService] Thread stopped.")

    def _capture_loop(self):
        """Luồng chính capture liên tục"""
        while self.running:
            ret, frame = self.camera.read()
            if ret:
                with self.lock:
                    self.raw_frame = frame
                    self.frame_id += 1
            else:
                # Nếu mất kết nối, chờ một chút rồi thử lại
                time.sleep(0.01)

    def get_frame(self):
        """Lấy frame mới nhất (trả về bản copy để an toàn luồng)"""
        with self.lock:
            if self.raw_frame is not None:
                return self.raw_frame.copy()
            return None

    def get_frame_with_id(self):
        """Lấy frame kèm ID để kiểm tra frame đã cũ hay mới"""
        with self.lock:
            if self.raw_frame is not None:
                return self.raw_frame.copy(), self.frame_id
            return None, 0
