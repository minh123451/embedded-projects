import json
import os
import time
import cv2
import numpy as np
from collections import deque
import onnxruntime as ort
from ultralytics import YOLO

from config import (
    MODEL_ONNX_PATH, MODEL_META_PATH, YOLO_PATH, 
    IMG_SIZE, DEVICE, CLASSES, DEBUG_MODE,
    BOX_PADDING, SMOOTH_WINDOW, HYST_HIGH, HYST_LOW, ALARM_THRESHOLD
)

# ──────────────────────────────────────────────
#  TEMPORAL SMOOTHER (Moving Average + Hysteresis)
# ──────────────────────────────────────────────
class TemporalSmoother:
    def __init__(self, window=SMOOTH_WINDOW, high_thr=HYST_HIGH, low_thr=HYST_LOW, min_frames=ALARM_THRESHOLD):
        self.window = window
        self.high_thr = high_thr
        self.low_thr = low_thr
        self.min_frames = min_frames
        self._tracks = {}

    def _get_track(self, track_id: int) -> dict:
        if track_id not in self._tracks:
            self._tracks[track_id] = {
                "buf": deque(maxlen=self.window),
                "state": "Normal",
                "intrusion_streak": 0,
            }
        return self._tracks[track_id]

    def update(self, track_id: int, intrusion_prob: float) -> tuple[str, float]:
        track = self._get_track(track_id)
        buf = track["buf"]
        buf.append(intrusion_prob)
        avg_prob = float(np.mean(buf))

        if avg_prob >= self.high_thr:
            track["intrusion_streak"] += 1
        else:
            track["intrusion_streak"] = 0

        state = track["state"]
        if state == "Normal" and track["intrusion_streak"] >= self.min_frames:
            state = "Intrusion"
        elif state == "Intrusion" and avg_prob < self.low_thr:
            state = "Normal"
            track["intrusion_streak"] = 0

        track["state"] = state
        return state, avg_prob

# ──────────────────────────────────────────────
#  SIMPLE IOU TRACKER (Dùng để thay thế YOLO Track khi thiếu 'lap')
# ──────────────────────────────────────────────
class SimpleTracker:
    def __init__(self, max_disappeared=10):
        self.next_id = 0
        self.objects = {} # {id: (box, disappeared_count)}
        self.max_disappeared = max_disappeared

    def update(self, rects):
        if len(rects) == 0:
            for object_id in list(self.objects.keys()):
                box, count = self.objects[object_id]
                self.objects[object_id] = (box, count + 1)
                if count + 1 > self.max_disappeared:
                    del self.objects[object_id]
            return []

        input_objects = []
        for rect in rects:
            input_objects.append(rect)

        if len(self.objects) == 0:
            for rect in input_objects:
                self.objects[self.next_id] = (rect, 0)
                self.next_id += 1
        else:
            object_ids = list(self.objects.keys())
            object_boxes = [self.objects[oid][0] for oid in object_ids]

            # Tính IoU hoặc khoảng cách tâm để khớp
            for i, rect in enumerate(input_objects):
                best_iou = -1
                best_id = -1
                
                for j, old_rect in enumerate(object_boxes):
                    iou = self._get_iou(rect, old_rect)
                    if iou > best_iou and iou > 0.3: # Ngưỡng IoU tối thiểu
                        best_iou = iou
                        best_id = object_ids[j]
                
                if best_id != -1:
                    self.objects[best_id] = (rect, 0)
                else:
                    self.objects[self.next_id] = (rect, 0)
                    self.next_id += 1
        
        # Trả về danh sách (box, id)
        results = []
        for oid, (box, _) in self.objects.items():
            results.append((box, oid))
        return results

    def _get_iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

class AIDetector:
    def __init__(self):
        print(f"[AI] Loading models on {DEVICE}...")
        
        # 1. Load Meta
        self.meta = self._load_meta(MODEL_META_PATH)
        self.img_size_infer = self.meta.get("img_size_infer", IMG_SIZE)
        
        # 2. Load ONNX Session
        self.session, self.input_name, self.output_name = self._load_onnx(MODEL_ONNX_PATH)
        
        # 3. Load YOLO
        self.yolo = self._load_yolo(YOLO_PATH)
        
        # Buffers for results and debug
        self.last_detections = [] 
        self.debug_crops = deque(maxlen=10) 
        self.ai_times = deque(maxlen=20)
        
        self.results = {
            "detections": [],
            "has_intrusion": False,
            "ai_ms": 0.0,
            "fps_ai": 0.0
        }

        self._MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self._STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def _load_meta(self, path):
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        print(f"[AI] [WARN] Metadata not found at {path}, using defaults.")
        return {"class_names": CLASSES, "img_size_infer": IMG_SIZE}

    def _load_onnx(self, path):
        if not os.path.exists(path):
            print(f"[AI] [ERROR] ONNX model not found at {path}")
            return None, None, None
        
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4
        session = ort.InferenceSession(path, sess_options=sess_options, providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        print(f"[AI] ONNX Loaded: {path}")
        return session, input_name, output_name

    def _load_yolo(self, path):
        if path and os.path.exists(path):
            model = YOLO(path)
            print(f"[AI] YOLO Loaded from file: {path}")
        else:
            model = YOLO("yolov8n.pt")
            print("[AI] YOLO Loaded default yolov8n.pt")
        return model

    def _get_padded_crop(self, frame, x1, y1, x2, y2):
        h, w = frame.shape[:2]
        bw, bh = x2 - x1, y2 - y1
        pad_x, pad_y = int(bw * BOX_PADDING), int(bh * BOX_PADDING)
        x1n = max(0, x1 - pad_x)
        y1n = max(0, y1 - pad_y)
        x2n = min(w, x2 + pad_x)
        y2n = min(h, y2 + pad_y)
        return frame[y1n:y2n, x1n:x2n], (x1n, y1n, x2n, y2n)

    def _preprocess_crop(self, crop_bgr):
        # Resize 1.1x -> center crop -> normalize (Giống test_video.py)
        resize_dim = int(self.img_size_infer * 1.1)
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(crop_rgb, (resize_dim, resize_dim), interpolation=cv2.INTER_LINEAR)
        
        start = (resize_dim - self.img_size_infer) // 2
        crop_center = resized[start:start + self.img_size_infer, start:start + self.img_size_infer]
        
        norm = (crop_center.astype(np.float32) / 255.0 - self._MEAN) / self._STD
        chw = norm.transpose(2, 0, 1)
        return np.expand_dims(chw, axis=0)

    def _softmax(self, x):
        e = np.exp(x - x.max())
        return e / e.sum()

    def run_inference(self, frame):
        if frame is None:
            return None
        
        if self.session is None:
            print("[AI] [ERROR] ONNX Session is None. Inference skipped.")
            return None

        try:
            t0 = time.perf_counter()
            
            # 1. YOLO Predict People
            results = self.yolo.predict(frame, classes=[0], conf=0.4, verbose=False)
            
            detections = []
            has_intrusion = False
            
            for result in results:
                if not result.boxes: continue
                
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    
                    # 2. Crop with Padding
                    crop, (px1, py1, px2, py2) = self._get_padded_crop(frame, x1, y1, x2, y2)
                    if crop.size == 0: continue
                    
                    # 3. MobileNetV2 ONNX
                    try:
                        # --- BẮT ĐẦU LOGIC LETTERBOX (PADDING) ---
                        h_orig, w_orig = crop.shape[:2]
                        scale = self.img_size_infer / max(h_orig, w_orig)
                        new_w, new_h = int(w_orig * scale), int(h_orig * scale)
                        
                        # Resize giữ tỉ lệ
                        resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                        
                        # Tạo khung Xám trung tính (114, 114, 114) - Tốt hơn cho AI
                        canvas = np.full((self.img_size_infer, self.img_size_infer, 3), 114, dtype=np.uint8)
                        
                        # Dán ảnh vào giữa khung
                        x_offset = (self.img_size_infer - new_w) // 2
                        y_offset = (self.img_size_infer - new_h) // 2
                        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
                        
                        crop_center = canvas # Đây là ảnh 224x224 đã được padding
                        # --- KẾT THÚC LOGIC LETTERBOX ---

                        # Chuẩn hóa và chạy inference (Chuyển sang RGB trước)
                        crop_rgb = cv2.cvtColor(crop_center, cv2.COLOR_BGR2RGB)
                        norm = (crop_rgb.astype(np.float32) / 255.0 - self._MEAN) / self._STD
                        chw = norm.transpose(2, 0, 1)
                        inp = np.expand_dims(chw, axis=0)
                        
                        logits = self.session.run([self.output_name], {self.input_name: inp})[0][0]
                        probs = self._softmax(logits)
                        
                        # Lấy index của class 'intrusion' từ metadata
                        class_names = [c.lower() for c in self.meta.get("class_names", [])]
                        try:
                            intr_idx = class_names.index("intrusion")
                        except ValueError:
                            intr_idx = 0
                        
                        intr_prob = float(probs[intr_idx])
                        
                        # 4. Logic tức thì (Raw Frame-by-Frame)
                        is_intr = intr_prob >= HYST_HIGH
                        state = "Intrusion" if is_intr else "Normal"

                        if is_intr:
                            has_intrusion = True
                        
                        display_prob = intr_prob if is_intr else (1.0 - intr_prob)

                        # Hiển thị thực tế ảnh AI nhận được (Debug) kèm kết quả nhận diện
                        if DEBUG_MODE:
                            debug_img = crop_center.copy()
                            color = (0, 0, 255) if is_intr else (0, 255, 0)
                            text = f"{state} {int(display_prob*100)}%"
                            # Vẽ text lên góc trên cùng bên trái của crop
                            cv2.putText(debug_img, text, (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            self.debug_crops.append(debug_img)

                        detections.append({
                            "box": (px1, py1, px2, py2),
                            "label": state,
                            "prob": display_prob,
                            "track_id": -1
                        })
                    except Exception as e:
                        print(f"[AI] [ERROR] ONNX error: {e}")

            t1 = time.perf_counter()
            ai_ms = (t1 - t0) * 1000
            self.ai_times.append(ai_ms)
            avg_ms = float(np.mean(self.ai_times))

            self.results.update({
                "detections": detections,
                "has_intrusion": has_intrusion,
                "ai_ms": avg_ms,
                "fps_ai": 1000.0 / avg_ms if avg_ms > 0 else 0
            })
            
            return self.results

        except Exception as e:
            print(f"[AI] [FATAL ERROR] In run_inference: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_debug_panel(self, item_height=80):
        """Trả về dải ảnh gồm các crop gần nhất để kiểm tra đầu vào AI"""
        if len(self.debug_crops) == 0:
            return None
        
        # Đảo ngược danh sách để frame mới nhất nằm bên trái, tránh bị cắt lẹm ở góc phải
        crops = list(self.debug_crops)[::-1]
        panel = np.hstack([cv2.resize(c, (item_height, item_height)) for c in crops])
        return panel
