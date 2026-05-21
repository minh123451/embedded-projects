import subprocess
import cv2
import numpy as np
from config import RTSP_URL, WIDTH, HEIGHT, FPS_TARGET

class MediaStreamer:
    def __init__(self):
        self.process = None
        # Khởi tạo lệnh FFmpeg tối ưu cho Pi 4 (Sử dụng tăng tốc h264_v4l2m2m)
        self.command = [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f"{WIDTH}x{HEIGHT}",
            '-use_wallclock_as_timestamps', '1', # [QUAN TRỌNG] Đánh dấu thời gian thực cho stream, cấm trình duyệt phát lại tua nhanh
            '-framerate', '30', # Giả định Python đẩy vào ~30 FPS từ camera gốc
            '-i', '-',  # Nhận đầu vào từ stdin (PIPE)
            '-r', str(FPS_TARGET), # FFmpeg sẽ tự động vứt bỏ (drop) các frame thừa để phân bổ ĐỀU 10 khung hình ra 1 giây
            '-c:v', 'h264_v4l2m2m', # Tăng tốc phần cứng Raspberry Pi
            '-g', str(FPS_TARGET),  # BẮT BUỘC: Tạo Keyframe mỗi giây để HLS cắt segment
            '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-f', 'rtsp',
            RTSP_URL
        ]

    def start(self):
        """Khởi động tiến trình FFmpeg"""
        try:
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE)
            print(f"[Streamer] FFmpeg started. Pushing to {RTSP_URL}")
        except Exception as e:
            print(f"[Streamer] [ERROR] Failed to start FFmpeg: {e}")

    def push_frame(self, frame):
        """Đẩy một frame vào PIPE của FFmpeg"""
        if self.process and self.process.stdin:
            try:
                # Đảm bảo frame đúng kích thước cấu hình
                if frame.shape[1] != WIDTH or frame.shape[0] != HEIGHT:
                    frame = cv2.resize(frame, (WIDTH, HEIGHT))
                self.process.stdin.write(frame.tobytes())
            except Exception as e:
                print(f"[Streamer] [ERROR] Streaming failed: {e}")
                self.stop()

    def stop(self):
        """Dừng tiến trình FFmpeg"""
        if self.process:
            self.process.stdin.close()
            self.process.terminate()
            self.process = None
            print("[Streamer] FFmpeg stopped.")
            self.process = None
            print("[Streamer] FFmpeg stopped.")
