import time
import threading
import cv2
import numpy as np

from config import *
from media_streamer import MediaStreamer
from camera_service import CameraService
from ai_detector import AIDetector
from storage_manager import StorageManager
from web_dashboard import WebDashboard
from buzzer_manager import BuzzerManager
from relay_manager import RelayManager
from hardware_buttons import HardwareButtons
from video_recorder import VideoRecorder

class IntrusionApp:
    def __init__(self):
        self.camera = CameraService()
        self.ai = AIDetector()
        self.storage = StorageManager()
        self.streamer = MediaStreamer()
        self.buzzer = BuzzerManager()
        self.relay = RelayManager()
        self.buttons = HardwareButtons() # Kích hoạt ngắt nút nhấn vật lý
        self.recorder = VideoRecorder() # Thêm module ghi video 24/7
        self.web = WebDashboard(buzzer_ctrl=self.buzzer, relay_ctrl=self.relay) # Truyền còi và relay vào dashboard
        
        self.running = True
        self.last_sample_time = 0
        self.intrusion_streak = 0 # Bộ đếm số lần xâm nhập liên tiếp

    def start(self):
        print("[Camera] Đang khởi động Snake Eye...")
        
        # 1. Khởi động Camera
        self.camera.start()
        time.sleep(1.0) # Đợi camera ổn định
        
        # 2. Khởi động Ghi hình CCTV 24/7
        self.recorder.start()
        time.sleep(0.5) # Giảm tải I/O lúc khởi đầu
        
        # 3. Khởi động Streamer (FFmpeg)
        self.streamer.start()
        time.sleep(0.5)
        
        # 4. Chạy Web Dashboard trong luồng riêng
        web_thread = threading.Thread(target=lambda: self.web.run(), daemon=True)
        web_thread.start()
        
        # 4. Chạy luồng AI (Background Thread)
        ai_thread = threading.Thread(target=self.ai_loop, daemon=True)
        ai_thread.start()
        
        # 5. Chạy luồng Video stream chính
        try:
            self.video_stream_loop()
        except KeyboardInterrupt:
            self.stop()
            
    def ai_loop(self):
        print("[Main] Bắt đầu luồng xử lý AI song song (YOLO + ONNX).")
        frame_count = 0
        while self.running:
            try:
                frame = self.camera.get_frame() # Lấy frame mới nhất nạp cho AI
                if frame is not None:
                    frame_count += 1
                    if frame_count % SKIP_FRAMES != 0:
                        time.sleep(0.01)
                        continue
                    
                    # Chạy Inference trực tiếp trên frame
                    # print(f"[Main] AI Loop: Processing frame {frame_count}...")
                    ai_results = self.ai.run_inference(frame)
                    
                    # XỬ LÝ LOGIC NGƯỠNG PHÁT HIỆN & BÁO ĐỘNG
                    if ai_results and ai_results['has_intrusion']:
                        print(f"[Main] !!! PHÁT HIỆN XÂM NHẬP !!!")
                        
                        # Lưu ảnh bằng chứng
                        saved = self.storage.save_intrusion(frame)
                        if saved:
                            print(f"[Main] Saved intrusion image: {saved}")
                        
                        # Kích hoạt còi báo động
                        if not self.buzzer.is_active():
                            self.buzzer.trigger()
                            print("[Main] ALARM TRIGGERED!")
                    
                    # Điều tiết tốc độ vòng lặp AI
                    time.sleep(0.01)
                else:
                    # print("[Main] AI Loop: Waiting for camera frame...")
                    time.sleep(0.1)
            except Exception as e:
                print(f"[Main] [ERROR] AI Loop encountered an error: {e}")
                time.sleep(1) # Chờ 1 giây trước khi thử lại để tránh spam log nếu lỗi liên tục

    def video_stream_loop(self):
        print("[Main] Bắt đầu luồng hiển thị Video.")
        t_prev_gui = time.perf_counter()
        self.last_vid_frame_id = -1
        
        while self.running:
            # A. Lấy frame từ Camera (Chỉ xử lý nếu frame thực sự mới)
            frame, frame_id = self.camera.get_frame_with_id()
            if frame is None or frame_id == self.last_vid_frame_id:
                time.sleep(0.01)
                continue
            self.last_vid_frame_id = frame_id
                
            # BÀN GIAO CHO MODULE CCTB GHI HÌNH LIÊN TỤC (Ảnh nguyên bản)
            self.recorder.push_frame(frame.copy())
                
            # B. VẼ OVERLAY TRẠNG THÁI (BỎ BOUNDING BOX ĐỂ TRÁNH LAG)
            res = self.ai.results 
            h, w = frame.shape[:2]
            
            # Vẽ thanh trạng thái tổng quát trên đỉnh
            has_i = res['has_intrusion']
            status_color = (0, 0, 255) if has_i else (0, 255, 0)
            cv2.rectangle(frame, (0, 0), (w, 45), (20, 20, 20), -1)
            cv2.putText(frame, f"SYSTEM STATUS: {'INTRUSION' if has_i else 'SECURE'}", 
                        (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
            
            # Vẽ viền đỏ toàn khung nếu có đột nhập
            if has_i: cv2.rectangle(frame, (0, 0), (w-1, h-1), (0, 0, 255), 4)

            # 3. Vẽ FPS và AI timing
            t_now = time.perf_counter()
            fps_main = 1.0 / max(t_now - t_prev_gui, 0.001)
            t_prev_gui = t_now
            cv2.putText(frame, f"FPS: {fps_main:.1f} | AI: {res['ai_ms']:.0f}ms", 
                        (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # C. VẼ DEBUG PANEL (Hiển thị các ảnh crop)
            if DEBUG_MODE:
                item_size = 80
                debug_panel = self.ai.get_debug_panel(item_height=item_size)
                
                if debug_panel is not None:
                    ph, pw = debug_panel.shape[:2]
                    start_y = h - ph - 40
                    # Đảm bảo panel không tràn khỏi frame
                    pw_limit = min(pw, w - 20)
                    frame[start_y:start_y+ph, 10:10+pw_limit] = debug_panel[:, :pw_limit]
                    cv2.putText(frame, f"AI INPUT CROPS (DEBUG)", 
                                (10, start_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            # D. ĐẨY FRAME LÊN MEDIAMTX
            self.streamer.push_frame(frame)

            # E. HIỂN THỊ TẠI CHỖ (LOCAL MONITOR)
            if DEBUG_MODE:
                cv2.imshow("Snake Eye - Local Monitoring", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop()
                    break

            # F. Duy trì FPS chuẩn (~30 FPS)
            time.sleep(0.01)

    def stop(self):
        print("\n[Main] Đang dừng hệ thống...")
        self.running = False
        self.camera.stop()
        self.recorder.stop()
        self.streamer.stop()
        self.relay.cleanup()
        self.buttons.cleanup()
        print("[Main] Đã dừng hoàn toàn.")

if __name__ == "__main__":
    app = IntrusionApp()
    app.start()
