import os
import torch

# ============================================================
# 📁 ĐƯỜNG DẪN HỆ THỐNG
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Đường dẫn Model (Tượng trưng - Người dùng sẽ tự điền)
MODEL_ONNX_PATH = os.path.join(BASE_DIR, "models", "mobilenetv2_float32.onnx")
MODEL_META_PATH = os.path.join(BASE_DIR, "models", "model_meta.json")
YOLO_PATH = os.path.join(BASE_DIR, "models", "yolov8n.pt") 

STORAGE_DIR = os.path.join(BASE_DIR, "data", "intrusions")
RECORD_DIR = os.path.join(BASE_DIR, "data", "recordings")

# Đảm bảo thư mục lưu trữ tồn tại
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(RECORD_DIR, exist_ok=True)

# ============================================================
# ⚙️ CẤU HÌNH CAMERA & AI
# ============================================================
CAMERA_ID = 0  # Thử 0, 1 hoặc 2 nếu không mở được camera
WIDTH = 640
HEIGHT = 360
FPS_TARGET = 10

# Cấu hình AI mới (YOLO + MobileNetV2 ONNX)
IMG_SIZE = 224
CLASSES = ["Intrusion", "Normal"]
DEVICE = "cpu" # Ưu tiên CPU cho Raspberry Pi 4

# Tham số lọc và xử lý (Đồng bộ với test_video.py)
BOX_PADDING = 0.10          # Mở rộng box 10%
SMOOTH_WINDOW = 15          # Cửa sổ Moving Average
HYST_HIGH = 0.80            # Ngưỡng cao để kích hoạt Intrusion (Hạ xuống 0.8 để nhạy hơn)
HYST_LOW = 0.4            # Ngưỡng thấp để quay lại Normal
SKIP_FRAMES = 2            # Bỏ qua frame để tăng tốc (Dùng trong AI Loop)

# ============================================================
# 🌐 CẤU HÌNH MEDIA SERVER & WEB
# ============================================================
# MediaMTX RTSP URL để đẩy luồng (chạy local trên Pi)
RTSP_URL = "rtsp://localhost:8554/mystream"

# Cổng truy cập HLS (mặc định cho mạng nội bộ)
HLS_URL = "http://localhost:8888/mystream/"

# URL truy cập HLS từ xa qua Cloudflare (Ví dụ: https://stream.yourdomain.com/mystream/)
# TRÊN CLOUDFLARE: Đổi port cấu hình tunnel sang 8888 (HTTP) thay vì 8889
HLS_REMOTE_URL = "https://stream.giaminh.id.vn/mystream/"

# Flask Web Dashboard
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080
ADMIN_USER = "admin"
ADMIN_PASS = "camera123"

# ============================================================
# ⚙️ CẤU HÌNH BÁO ĐỘNG & ĐIỀU KHIỂN
# ============================================================
ALARM_THRESHOLD = 3      # Số lần phát hiện liên tiếp để báo động
ALARM_DURATION = 5.0    # Thời gian còi kêu (Giây)
GPIO_BUZZER = 18        # Chân GPIO kết nối loa
GPIO_RELAY = 17         # Chân GPIO kết nối Relay (đèn)
GPIO_REBOOT_BTN = 27    # Chân GPIO kết nối nút nhấn Reboot (Emergency)

# ============================================================
# 🎥 CẤU HÌNH GHI HÌNH LIÊN TỤC (CCTV)
# ============================================================
RECORD_SEGMENT_DURATION = 180  # Lưu video bao nhiêu giây mỗi file (Vd: 180s = 3 phút)
RECORD_RETENTION_DAYS = 5      # Xóa file cũ quá bao nhiêu ngày (Vd: 5 ngày)

# ============================================================
# 🐞 GỠ LỖI
# ============================================================
DEBUG_MODE = True
