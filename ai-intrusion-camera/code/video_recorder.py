import os
import cv2
import time
import threading
import subprocess
from datetime import datetime

from config import RECORD_DIR, RECORD_SEGMENT_DURATION, RECORD_RETENTION_DAYS, WIDTH, HEIGHT, FPS_TARGET

class VideoRecorder:
    def __init__(self):
        self.running = False
        self.process = None
        self.segment_start_time = 0
        self.lock = threading.RLock() # Dùng RLock để tránh bị deadlock khi gọi hàm lồng nhau
        self._cleanup_thread = None

    def start(self):
        self.running = True
        self._start_new_segment()
        
        # Chạy một luồng dọn dẹp file ngầm chạy định kỳ
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        print("[Recorder] 24/7 Video Recording started.")

    def _start_new_segment(self):
        with self.lock:
            # Nếu đang ghi file thì ngắt file cũ (thực hiện ở luồng chạy nền để không block main thread và cho FFmpeg thời gian ghi MP4 header)
            if self.process is not None:
                old_process = self.process
                self.process = None
                def close_ffmpeg(proc):
                    try:
                        proc.stdin.close()
                        proc.wait(timeout=10) # Tăng timeout lên 10s để Pi kịp lưu metadata
                    except:
                        proc.kill()
                threading.Thread(target=close_ffmpeg, args=(old_process,), daemon=True).start()
                
            # Tạo tên file mới dựa theo thời gian hiện tại
            now = datetime.now()
            filename = now.strftime("cctv_%Y%m%d_%H%M%S.mp4")
            filepath = os.path.join(RECORD_DIR, filename)
            
            # Sử dụng FFmpeg để ghi hình (Ổn định hơn OpenCV VideoWriter trên Pi)
            # Codec libx264 đảm bảo chạy được trên trình duyệt Web
            print(f"[Recorder] Opening new video file with FFmpeg: {filepath}")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo', '-vcodec', 'rawvideo',
                '-s', f"{WIDTH}x{HEIGHT}",
                '-pix_fmt', 'bgr24',
                '-r', str(FPS_TARGET), # Dùng đúng FPS của luồng camera để khớp thời gian
                '-i', '-',  # Nhận input từ stdin
                '-c:v', 'libx264',
                '-preset', 'ultrafast', # Cực nhanh để giảm tải CPU
                '-pix_fmt', 'yuv420p', # Quan trọng cho web playback
                '-crf', '25', # Chất lượng vừa phải để giảm dung lượng
                filepath
            ]
            
            try:
                self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.segment_start_time = time.time()
                print(f"[Recorder] Started new segment: {filename}")
            except Exception as e:
                print(f"[Recorder] [ERROR] Failed to start FFmpeg for recording: {e}")

    def push_frame(self, frame):
        """Nhận frame mới và đẩy vào FFmpeg qua PIPE."""
        if not self.running or self.process is None:
            return
            
        with self.lock:
            now = time.time()

            # Kiểm tra xem đã hết thời gian của đoạn video hiện tại chưa
            if now - self.segment_start_time >= RECORD_SEGMENT_DURATION:
                self._start_new_segment()
                
            if self.process and self.process.stdin:
                try:
                    # Đảm bảo frame đúng kích thước
                    if frame.shape[1] != WIDTH or frame.shape[0] != HEIGHT:
                        frame = cv2.resize(frame, (WIDTH, HEIGHT))
                    
                    self.process.stdin.write(frame.tobytes())
                except Exception as e:
                    print(f"[Recorder] [ERROR] Writing frame failed: {e}")
                    self.process = None

    def _cleanup_loop(self):
        """Định kỳ xóa các file cũ hơn RECORD_RETENTION_DAYS"""
        while self.running:
            try:
                now_ts = time.time()
                retention_seconds = RECORD_RETENTION_DAYS * 24 * 3600
                
                if os.path.exists(RECORD_DIR):
                    for filename in os.listdir(RECORD_DIR):
                        if not filename.endswith('.mp4'):
                            continue
                            
                        filepath = os.path.join(RECORD_DIR, filename)
                        file_mtime = os.path.getmtime(filepath)
                        
                        # Nếu thời gian từ lúc file được sửa lần cuối lớn hơn tuổi thọ chỉ định => Xóa
                        if now_ts - file_mtime > retention_seconds:
                            os.remove(filepath)
                            print(f"[Recorder] Auto-deleted old file: {filename}")
                            
            except Exception as e:
                print(f"[Recorder] Cleanup Error: {e}")
                
            # Ngủ 60s rồi mới quét lại 1 lần (dùng sleep ngắn để dễ thoát thread khi tắt app)
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self):
        """Dừng quay và lưu file an toàn."""
        self.running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)
            
        with self.lock:
            if self.process is not None:
                try:
                    self.process.stdin.close()
                    self.process.wait(timeout=10) # Tăng timeout khi tắt app để không hỏng file MP4 cuối cùng
                except:
                    self.process.kill()
                self.process = None
        print("[Recorder] 24/7 Video Recording stopped.")
