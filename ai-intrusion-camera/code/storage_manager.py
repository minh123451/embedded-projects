import os
import cv2
import time
from datetime import datetime
from config import STORAGE_DIR, RECORD_DIR

class StorageManager:
    def __init__(self):
        # Đảm bảo thư mục lưu trữ tồn tại
        os.makedirs(STORAGE_DIR, exist_ok=True)
        # Giới hạn số ảnh lưu mỗi lần đột nhập (Cooldown 2 giây)
        self.last_save_time = 0
        self.cooldown = 2.0

    def save_intrusion(self, frame):
        """Lưu lại frame ảnh khi có đột nhập"""
        current_time = time.time()
        if current_time - self.last_save_time >= self.cooldown:
            now = datetime.now()
            filename = now.strftime("intrusion_%Y%m%d_%H%M%S.jpg")
            filepath = os.path.join(STORAGE_DIR, filename)
            
            # Lưu ảnh
            cv2.imwrite(filepath, frame)
            
            print(f"[Storage] Saved intrusion image: {filename}")
            self.last_save_time = current_time
            return filename
        return None

    def get_all_intrusions(self):
        """Lấy danh sách tất cả các ảnh đột nhập (xếp mới nhất lên đầu)"""
        if not os.path.exists(STORAGE_DIR):
            return []
        files = [f for f in os.listdir(STORAGE_DIR) if f.endswith('.jpg')]
        # Sắp xếp theo thời gian sửa đổi (mới nhất đầu tiên)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(STORAGE_DIR, x)), reverse=True)
        return files

    def delete_intrusion(self, filename):
        """Xóa một ảnh đột nhập"""
        filepath = os.path.join(STORAGE_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[Storage] Deleted: {filename}")
            return True
        return False

    def get_all_recordings(self):
        """Lấy danh sách tất cả file CCTV video (đã quay xong)"""
        if not os.path.exists(RECORD_DIR):
            return []
        files = [f for f in os.listdir(RECORD_DIR) if f.endswith('.mp4')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(RECORD_DIR, x)), reverse=True)
        return files

    def delete_recording(self, filename):
        """Xóa thủ công một file video rác/cũ"""
        filepath = os.path.join(RECORD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[Storage] Deleted recording: {filename}")
            return True
        return False
