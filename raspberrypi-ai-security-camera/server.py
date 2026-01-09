from flask import Flask, Response, request, render_template_string, render_template, jsonify, redirect, url_for
from flask_sock import Sock
import cv2, time, numpy as np
from ultralytics import YOLO
import threading
import os # THÊM: Để làm việc với hệ thống file
import shutil # THÊM: Để sao chép file
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash



# ================== Cấu hình Lưu Trữ Ảnh ==================
LATEST_WEAPON_IMAGE = "/home/minhda/images/weapon.jpg"
# Ảnh đang được hiển thị trên web
WEAPON_IMAGES_FOLDER = "/home/minhda/images/weapon_archive" # Thư mục lưu trữ ảnh cũ
# Đảm bảo thư mục tồn tại
os.makedirs("/home/minhda/images/", exist_ok=True)
os.makedirs(WEAPON_IMAGES_FOLDER, exist_ok=True)



# ================== Khởi tạo Flask ==================
app = Flask(
    __name__,
    template_folder="templates"
)
app.config['SECRET_KEY'] = '001122' # ⚠️ RẤT QUAN TRỌNG
sock = Sock(app)

gps_data = {"lat": 0.0, "lon": 0.0}

# Khởi tạo Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Đặt tên hàm (route) đăng nhập
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."

# --- THÔNG TIN USER ĐƠN GIẢN (CÓ THỂ LƯU VÀO DB THỰC TẾ) ---
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    # Tạm thời chỉ dùng 1 user cứng, bạn có thể thay bằng Database
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- USER TẠM THỜI (thay 'sha256:...' bằng giá trị băm của mật khẩu bạn muốn) ---
# Mật khẩu mẫu: 'admin123'
users = {
    1: User(1, 'admin', 'scrypt:32768:8:1$X2T6l2PN2foBavUd$380088008e66754512584d0a73636baac39244f5cb22633d5e92a7181da98444357d0e4f31f59807e7f8d24a026603f4a4fac5c62a90508633054c2df54878fb') 
    # Mật khẩu: admin123. Dùng generate_password_hash('mật khẩu') để tạo hash mới.
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))

# ================== Load mô hình YOLO ==================
# Đường dẫn đến file .pt (đặt cùng thư mục với server)
model = YOLO("/home/minhda/best7.pt")   # ⚠️ đổi tên file theo file của bạn, ví dụ best.pt

latest_frame = None
latest_annotated = None

alarm_state = False
# ================== Biến Trạng thái Nâng cao ==================
latest_detection_time = 0 
last_saved_detection_path = ""# Theo dõi đường dẫn ảnh mới nhất đã lưu
ARCHIVE_INTERVAL = 15 



first_detection_time = 0 
CONFIRMATION_DELAY = 1.5 

# ================== WebSocket nhận frame từ Raspberry Pi ==================
@sock.route('/ws-stream')
def ws_stream(ws):
    global latest_frame
    while True:
        frame = ws.receive()
        if frame:
            latest_frame = frame

# ================== API upload ==================
@app.route('/upload', methods=['POST'])
def upload():
    global latest_frame
    file = request.files['file']
    latest_frame = file.read()
    return "OK"



#==================Thread chạy YOLO riêng (không block stream)============================

def yolo_worker():
    global latest_frame, latest_annotated, alarm_state, latest_detection_time, last_saved_detection_path, first_detection_time # ⚠️ Đã thêm first_detection_time vào global
    frame_count = 0

    while True:
        if latest_frame:
            frame_count += 1

            
            if frame_count % 10 != 0:
                time.sleep(0.005)
                continue

            np_frame = np.frombuffer(latest_frame, np.uint8)
            frame = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)

            results = model.predict(frame, conf=0.6, imgsz=320, verbose=False)
            det = results[0]
            annotated = det.plot()

            weapon_detected = False
            for box in det.boxes:
                cls = int(box.cls[0])
                name = det.names[cls]
                if name.lower() in ["knife", "hammer"]:
                    weapon_detected = True
                    break

            if weapon_detected:
# --- LOGIC MỚI: Xử lý Độ trễ 2s và Kích hoạt Alarm ---
                current_time = time.time()
                if not alarm_state:
                    if first_detection_time == 0:
                        first_detection_time = current_time
                        print(f"🕒 Phát hiện vũ khí lần đầu. Bắt đầu đếm ngược {CONFIRMATION_DELAY}s...")

                    elif current_time - first_detection_time >= CONFIRMATION_DELAY:
                        alarm_state = True
                        latest_detection_time = current_time # Ghi lại thời điểm KÍCH HOẠT BÁO ĐỘNG

                        # 1b. Lưu ảnh mới nhất và cập nhật đường dẫn (Ảnh có Box)
                        cv2.imwrite(LATEST_WEAPON_IMAGE, annotated)
                        last_saved_detection_path = LATEST_WEAPON_IMAGE
                        print(f"🔥🔥 ĐÃ XÁC NHẬN! Kích hoạt alarm sau {CONFIRMATION_DELAY}s liên tục và lưu ảnh: {LATEST_WEAPON_IMAGE}")
                    else:
                        pass
                elif alarm_state:
                    first_detection_time = 0 

                    if current_time - latest_detection_time > ARCHIVE_INTERVAL:
                        # Lưu ảnh CŨ (lần trước) vào Archive
                        if os.path.exists(LATEST_WEAPON_IMAGE):
                            ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(latest_detection_time))
                            gps_str = f"Lat{gps_data['lat']:.4f}_Lon{gps_data['lon']:.4f}"
                            archive_filename = f"weapon_{ts}_{gps_str}.jpg"
                            archive_path = os.path.join(WEAPON_IMAGES_FOLDER, archive_filename)
                            shutil.copy(LATEST_WEAPON_IMAGE, archive_path)
                            print(f"💾 Lưu ảnh cũ vào archive: {archive_path}")
                        latest_detection_time = current_time # Cập nhật thời điểm phát hiện mới nhất
                        cv2.imwrite(LATEST_WEAPON_IMAGE, annotated)
                        print("♻️ Cập nhật ảnh vũ khí mới.")

            else: 
                if first_detection_time != 0 and not alarm_state:
                    print("❌ Mất phát hiện. Reset đếm ngược.")
                first_detection_time = 0 # Reset đếm ngược 2s nếu không thấy vũ khí
            latest_annotated = annotated

        time.sleep(0.005)   


# ================== Video stream có AI ==================================================
@app.route('/video')
@login_required
def video_feed():
    def generate():
        global latest_frame, latest_annotated
        while True:
            if latest_annotated is not None:
                _, buffer = cv2.imencode('.jpg', latest_annotated, [
                    cv2.IMWRITE_JPEG_QUALITY, 50 # Giảm chất lượng nén cho frame AI
                ])
            elif latest_frame is not None:
                buffer = latest_frame  # <-- ĐÂY LÀ TỐI ƯU QUAN TRỌNG
                
            else:
                time.sleep(0.01)
                continue

            # ... Gửi buffer ra trình duyệt ...

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            time.sleep(0.01) # Giữ nguyên 0.01s
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ================== Các API khác ==================


@app.route('/alarm', methods=['POST'])
@login_required
def alarm():
    global alarm_state, latest_detection_time, last_saved_detection_path # THÊM
    state = request.form.get("state")

    new_alarm_state = (state == "on")
    
    # --- Logic Tắt Alarm (Lưu ảnh cuối cùng) ---
    if alarm_state and not new_alarm_state:
        if os.path.exists(LATEST_WEAPON_IMAGE):
            # Lưu ảnh cuối cùng vào Archive kèm thông tin GPS và thời gian
            ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(latest_detection_time))
            gps_str = f"Lat{gps_data['lat']:.4f}_Lon{gps_data['lon']:.4f}"
            archive_filename = f"weapon_{ts}_{gps_str}_END.jpg" # Thêm END để đánh dấu kết thúc sự kiện
            archive_path = os.path.join(WEAPON_IMAGES_FOLDER, archive_filename)

            shutil.copy(LATEST_WEAPON_IMAGE, archive_path)
            print(f"✅ Đã tắt báo động. Lưu ảnh cuối cùng vào archive: {archive_path}")
            
            # Reset trạng thái
            last_saved_detection_path = ""
            latest_detection_time = 0

    alarm_state = new_alarm_state # THAY THẾ logic cũ bằng biến mới

    print("🔔 Alarm:", alarm_state)
    return f"Alarm {'ON' if alarm_state else 'OFF'}"

#===========================GPS======================
@app.route('/gps', methods=['POST'])
def gps():
    global gps_data
    lat = request.form.get("lat")
    lon = request.form.get("lon")

    try:
        gps_data = {
            "lat": float(lat),
            "lon": float(lon)
        }
        return "GPS OK"
    except:
        return "GPS ERROR"



@app.route('/weapon_image')
@login_required
def weapon_image():
    return Response(open("/home/minhda/images/weapon.jpg", "rb"),
                    mimetype="image/jpeg")





LOGIN_HTML = """
<html>
<head>
    <title>Đăng Nhập</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .login-container { background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); width: 300px; text-align: center; }
        h2 { color: #667eea; margin-bottom: 20px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        input[type="submit"] { background-color: #667eea; color: white; padding: 10px 15px; margin-top: 10px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px; transition: background-color 0.3s; }
        input[type="submit"]:hover { background-color: #764ba2; }
        .error { color: red; margin-bottom: 10px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>🔒 Đăng Nhập Hệ Thống</h2>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Tên đăng nhập" required>
            <input type="password" name="password" placeholder="Mật khẩu" required>
            <input type="submit" value="Đăng Nhập">
        </form>
    </div>
</body>
</html>
"""



# ================== ROUTE ĐĂNG NHẬP/ĐĂNG XUẤT ==================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index')) # Đã đăng nhập thì chuyển về trang chủ

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Kiểm tra user
        user = users.get(1) # Lấy user duy nhất
        
        if user and user.username == username and user.check_password(password):
            login_user(user)
            # Chuyển hướng đến trang người dùng muốn truy cập trước đó, nếu có
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            error = "Tên người dùng hoặc mật khẩu không đúng."
            return render_template_string(LOGIN_HTML, error=error), 401

    return render_template_string(LOGIN_HTML) # Hiển thị form đăng nhập GET

@app.route('/logout')
@login_required # Chỉ người đã đăng nhập mới logout được
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template("index.html")

@app.route('/status')
def status():
    global alarm_state
    return jsonify({
        "alarm": 1 if alarm_state else 0
    })


#===============API client sẽ gọi khi phát hiện vũ khí=============

@app.route('/get_alarm')
def get_alarm():
    return jsonify({"alarm": alarm_state})


#================Thêm API để trình duyệt xem GPS realtime===========
@app.route('/get_gps')
def get_gps():
    return jsonify(gps_data)


#===========================API xem danh sách ảnh Archive (Đã thêm)==================
@app.route('/archive_list')
@login_required
def archive_list():
    files = sorted(os.listdir(WEAPON_IMAGES_FOLDER), reverse=True)
    html_list = "<ul>"
    for file in files:
        html_list += f'<li><a href="/archive_image/{file}">{file}</a></li>'
    html_list += "</ul>"
    return render_template_string(f"<h1>Ảnh Archive</h1><a href='/'>Quay lại Dashboard</a>{html_list}")

@app.route('/archive_image/<filename>')
@login_required
def archive_image(filename):
    path = os.path.join(WEAPON_IMAGES_FOLDER, filename)
    if os.path.exists(path):
        return Response(open(path, "rb"), mimetype="image/jpeg")
    return "File not found", 404



## ================== KHỞI ĐỘNG THREAD YOLO ==================
threading.Thread(target=yolo_worker, daemon=True).start()


# ================== Chạy Flask server ==================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
