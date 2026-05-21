from flask import Flask, render_template, send_from_directory, request, Response, jsonify, session, redirect, url_for
import os
from datetime import datetime, timedelta
from config import WEB_HOST, WEB_PORT, ADMIN_USER, ADMIN_PASS, STORAGE_DIR, RECORD_DIR, HLS_URL, HLS_REMOTE_URL, ALARM_THRESHOLD
from storage_manager import StorageManager

class WebDashboard:
    def __init__(self, buzzer_ctrl=None, relay_ctrl=None):
        # Thiết lập đường dẫn tương đối cho templates và static
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        
        self.app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
        self.app.secret_key = os.urandom(24) # Tạo khóa bí mật cho session
        self.app.permanent_session_lifetime = timedelta(minutes=60) # Ép phiên đăng nhập hết hạn sau 60 phút
        self.storage = StorageManager()
        self.buzzer = buzzer_ctrl
        self.relay = relay_ctrl
        self._setup_routes()

    def _setup_routes(self):
        @self.app.before_request
        def require_auth():
            # Danh sách các trang không cần đăng nhập
            if request.endpoint in ['login', 'static']:
                return
            
            # Kiểm tra session
            if not session.get('logged_in'):
                return redirect(url_for('login'))

        @self.app.after_request
        def add_header(response):
            # Ép trình duyệt KHÔNG ĐƯỢC lưu bộ nhớ đệm (cache) trang web.
            # Tránh lỗi: ấn đăng xuất xong ấn "Back/Quay lại" vẫn xem được trang (do cache)
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            return response

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            error = None
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                if username == ADMIN_USER and password == ADMIN_PASS:
                    session.permanent = True # Đánh dấu session tính thời gian hết hạn
                    session['logged_in'] = True
                    return redirect(url_for('index'))
                else:
                    error = "Sai tài khoản hoặc mật khẩu!"
            
            return render_template('login.html', error=error)

        @self.app.route('/logout')
        def logout():
            session.pop('logged_in', None)
            return redirect(url_for('login'))

        @self.app.route('/')
        def index():
            host = request.host.split(':')[0]
            is_local = host in ['localhost', '127.0.0.1'] or host.startswith('192.168.') or host.startswith('10.')
            stream_url = HLS_URL if is_local else HLS_REMOTE_URL
            
            return render_template('index.html', stream_url=stream_url, threshold=ALARM_THRESHOLD)

        @self.app.route('/gallery')
        def gallery():
            images = self.storage.get_all_intrusions()
            return render_template('gallery.html', images=images)

        @self.app.route('/recordings')
        def recordings():
            videos = self.storage.get_all_recordings()
            
            # Format file video size (MB)
            video_info = []
            for v in videos:
                filepath = os.path.join(RECORD_DIR, v)
                size_mb = os.path.getsize(filepath) / (1024 * 1024) if os.path.exists(filepath) else 0
                video_info.append({"name": v, "size": f"{size_mb:.1f} MB"})
                
            return render_template('recordings.html', videos=video_info)

        # --- API ENDPOINTS ---

        @self.app.route('/api/stats')
        def get_stats():
            images = self.storage.get_all_intrusions()
            total_count = len(images)
            
            last_time = "Chưa có"
            if images:
                # Lấy timestamp từ tên file: intrusion_YYYYMMDD_HHMMSS.jpg
                last_file = images[0]
                try:
                    time_str = last_file.replace('intrusion_', '').replace('.jpg', '')
                    # Format lại cho đẹp: HH:MM:SS DD/MM
                    dt = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
                    last_time = dt.strftime("%H:%M:%S %d/%m")
                except:
                    last_time = "Định dạng lỗi"

            return jsonify({
                "total_count": total_count,
                "last_time": last_time
            })

        @self.app.route('/api/buzzer/status')
        def buzzer_status():
            active = False
            if self.buzzer:
                active = self.buzzer.is_active()
            return jsonify({"active": active})

        @self.app.route('/buzzer/on')
        def buzzer_on():
            if self.buzzer:
                self.buzzer.set_manual(True)
                return "Buzzer ON"
            return "No buzzer", 404

        @self.app.route('/buzzer/off')
        def buzzer_off():
            if self.buzzer:
                self.buzzer.set_manual(False)
                return "Buzzer OFF"
            return "No buzzer", 404

        @self.app.route('/api/relay/status')
        def relay_status():
            active = False
            if self.relay:
                active = self.relay.is_active()
            return jsonify({"active": active})

        @self.app.route('/relay/on')
        def relay_on():
            if self.relay:
                self.relay.set_state(True)
                return "Relay ON"
            return "No relay", 404

        @self.app.route('/relay/off')
        def relay_off():
            if self.relay:
                self.relay.set_state(False)
                return "Relay OFF"
            return "No relay", 404

        @self.app.route('/api/delete/<filename>', methods=['DELETE'])
        def delete_image(filename):
            if self.storage.delete_intrusion(filename):
                return jsonify({"status": "deleted"}), 200
            return jsonify({"status": "error", "message": "File not found"}), 404

        @self.app.route('/intrusions/<filename>')
        def get_image(filename):
            return send_from_directory(STORAGE_DIR, filename)

        @self.app.route('/api/recordings/delete/<filename>', methods=['DELETE'])
        def delete_video(filename):
            if self.storage.delete_recording(filename):
                return jsonify({"status": "deleted"}), 200
            return jsonify({"status": "error", "message": "Video not found"}), 404

        @self.app.route('/recordings/play/<filename>')
        def play_video(filename):
            # Stream video qua giao thức HTTP cho thẻ <video>
            return send_from_directory(RECORD_DIR, filename)

    def run(self, debug=False):
        print(f"[WebDashboard] Professional Flask server running on http://{WEB_HOST}:{WEB_PORT}")
        # Tắt reloader nếu đang chạy trunng với camera service
        self.app.run(host=WEB_HOST, port=WEB_PORT, debug=debug, use_reloader=False)
