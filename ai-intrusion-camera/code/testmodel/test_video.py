# ============================================================
#  inference_video_folder.py
#  Nhận diện hành vi từ folder video
#
#  Pipeline:
#    1. Đọc từng video trong folder
#    2. YOLO → crop từng người trong frame
#    3. MobileNetV2 (ONNX) → phân loại hành vi từng crop
#    4. Vẽ bbox + label lên frame
#    5. Lưu video kết quả vào OUTPUT_DIR
#
#  Cài đặt:
#    pip install onnxruntime opencv-python ultralytics
#
#  Cách dùng:
#    Chỉnh các đường dẫn trong phần CONFIG bên dưới rồi chạy:
#    python inference_video_folder.py
# ============================================================

import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
from collections import deque


# ╔══════════════════════════════════════════════════════════╗
#  ██  CONFIG – SỬA ĐƯỜNG DẪN Ở ĐÂY  ██
# ╚══════════════════════════════════════════════════════════╝

# ── [BẮT BUỘC] Folder chứa các video cần test
#    Ví dụ Windows : r"C:\Users\ten_ban\Videos\test_videos"
#    Ví dụ Linux   : "/home/pi/videos"
VIDEO_DIR   = r"C:\Users\USER\GIAMINH\Máy tính\KLTN\dataset_1\test_video"

# ── [BẮT BUỘC] File model ONNX
#    Ví dụ Windows : r"C:\Users\ten_ban\Downloads\results\mobilenetv2_float32.onnx"
#    Ví dụ Linux   : "/home/pi/model/mobilenetv2_float32.onnx"
MODEL_PATH  = r"mobilenetv2_float32.onnx"

# ── [BẮT BUỘC] File metadata JSON
#    Ví dụ Windows : r"C:\Users\ten_ban\Downloads\results\model_meta.json"
#    Ví dụ Linux   : "/home/pi/model/model_meta.json"
META_PATH   = r"model_meta.json"

# ── [TÙY CHỌN] File YOLO weight (.pt)
#    - Để None  → tự tải yolov8n.pt lần đầu chạy (cần internet)
#    - Điền path → dùng file có sẵn (không cần internet, phù hợp Pi 4)
#    Tải thủ công tại:
#    https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt
#    Ví dụ Windows : r"C:\Users\ten_ban\Downloads\yolov8n.pt"
#    Ví dụ Linux   : "/home/pi/model/yolov8n.pt"
YOLO_PATH   = None   # hoặc r"C:\Users\ten_ban\Downloads\yolov8n.pt"

# ── [TÙY CHỌN] Folder lưu video kết quả
#    Để None → tự tạo folder "results" bên trong VIDEO_DIR
OUTPUT_DIR  = r"C:\Users\USER\GIAMINH\Máy tính\KLTN\dataset_1\test_video\giaminh"   # hoặc r"C:\Users\ten_ban\Videos\output"

# ── Ngưỡng confidence YOLO (0.0 – 1.0)
#    Thấp hơn → detect nhiều hơn nhưng dễ nhầm
#    Khuyến nghị: 0.5
CONF_THRESHOLD = 0.5

# ── Bỏ qua N frame để tăng tốc (1 = xử lý mọi frame)
#    Khuyến nghị Pi 4: 2 hoặc 3
SKIP_FRAMES = 2

# ── Lưu video kết quả hay không
SAVE_VIDEO  = True

# ── Lưu ảnh crop từ YOLO để kiểm tra
#    True  → tạo folder "crops" bên trong OUTPUT_DIR, lưu từng crop
#    False → không lưu crop
#
#    Cấu trúc folder crops:
#    crops/
#      tên_video/
#        normal/          ← crop được classify là "normal"
#          frame0012_p0.jpg
#          frame0025_p1.jpg
#        intrusion/       ← crop được classify là "intrusion"
#          frame0030_p0.jpg
#
#    Lưu ý: chỉ lưu tối đa CROPS_MAX_PER_CLASS ảnh mỗi class mỗi video
#    để tránh đầy ổ đĩa
SAVE_CROPS          = True
CROPS_MAX_PER_CLASS = 200   # tối đa 200 ảnh mỗi class mỗi video

# ── Thông số lọc nhiễu và padding (Đồng bộ với bản .pth)
BOX_PADDING          = 0.10  # Mở rộng box 10% mỗi cạnh
SMOOTH_WINDOW        = 15    # Số frame trong moving average buffer
HYST_HIGH            = 0.90  # Prob > HIGH  → chuyển sang intrusion
HYST_LOW             = 0.35  # Prob < LOW   → chuyển về normal
MIN_INTRUSION_FRAMES = 10    # Số frame liên tiếp avg >= HIGH trước khi alert

# ╔══════════════════════════════════════════════════════════╗
#  KẾT THÚC CONFIG – KHÔNG CẦN SỬA GÌ THÊM BÊN DƯỚI
# ╚══════════════════════════════════════════════════════════╝


# ──────────────────────────────────────────────
#  LOAD MODEL META
# ──────────────────────────────────────────────
def load_meta(meta_path: str) -> dict:
    with open(meta_path, "r") as f:
        meta = json.load(f)
    print(f"[META] Classes      : {meta['class_names']}")
    print(f"[META] Infer size   : {meta['img_size_infer']}x{meta['img_size_infer']}")
    print(f"[META] Best val acc : {meta.get('best_val_acc', 'N/A'):.4f}")
    return meta


# ──────────────────────────────────────────────
#  LOAD ONNX SESSION
# ──────────────────────────────────────────────
def load_onnx_session(model_path: str):
    import onnxruntime as ort

    # Ưu tiên CPU provider cho Pi 4
    providers = ["CPUExecutionProvider"]

    sess_options = ort.SessionOptions()
    # Tối ưu cho Pi 4: dùng 4 thread (Pi 4 có 4 core)
    sess_options.intra_op_num_threads  = 4
    sess_options.inter_op_num_threads  = 1
    sess_options.execution_mode        = ort.ExecutionMode.ORT_SEQUENTIAL
    sess_options.graph_optimization_level = (
        ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    )

    session = ort.InferenceSession(
        model_path,
        sess_options=sess_options,
        providers=providers,
    )
    input_name  = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    print(f"[ONNX] Loaded: {model_path}")
    print(f"[ONNX] Input : {input_name}  {session.get_inputs()[0].shape}")
    return session, input_name, output_name


# ──────────────────────────────────────────────
#  LOAD YOLO
# ──────────────────────────────────────────────
def load_yolo(yolo_path: str | None, device: str):
    from ultralytics import YOLO

    if yolo_path and os.path.exists(yolo_path):
        model = YOLO(yolo_path)
        print(f"[YOLO] Loaded từ file: {yolo_path}")
    else:
        # Tự tải yolov8n.pt (nhỏ nhất, nhanh nhất, phù hợp Pi 4)
        model = YOLO("yolov8n.pt")
        print("[YOLO] Tự tải yolov8n.pt (lần đầu cần internet)")
        print("[YOLO] File được lưu tại: ~/.config/Ultralytics/")
        print("[YOLO] Để tải thủ công:")
        print("       https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt")

    return model


# ──────────────────────────────────────────────
#  TEMPORAL SMOOTHER (Moving Average + Hysteresis)
# ──────────────────────────────────────────────
class TemporalSmoother:
    def __init__(self, window=SMOOTH_WINDOW, high_thr=HYST_HIGH, low_thr=HYST_LOW, min_frames=MIN_INTRUSION_FRAMES):
        self.window   = window
        self.high_thr = high_thr
        self.low_thr  = low_thr
        self.min_frames = min_frames
        self._tracks = {}

    def _get_track(self, track_id: int) -> dict:
        if track_id not in self._tracks:
            self._tracks[track_id] = {
                "buf": deque(maxlen=self.window),
                "state": "normal",
                "intrusion_streak": 0,
            }
        return self._tracks[track_id]

    def update(self, track_id: int, intrusion_prob: float) -> tuple[str, float]:
        track = self._get_track(track_id)
        buf   = track["buf"]
        buf.append(intrusion_prob)
        avg_prob = float(np.mean(buf))

        if avg_prob >= self.high_thr:
            track["intrusion_streak"] += 1
        else:
            track["intrusion_streak"] = 0

        state = track["state"]
        if state == "normal" and track["intrusion_streak"] >= self.min_frames:
            state = "intrusion"
        elif state == "intrusion" and avg_prob < self.low_thr:
            state = "normal"
            track["intrusion_streak"] = 0

        track["state"] = state
        return state, avg_prob

# ──────────────────────────────────────────────
#  MỞ RỘNG BOUNDING BOX (PADDING)
# ──────────────────────────────────────────────
def get_padded_crop(frame, x1, y1, x2, y2, width, height, padding=BOX_PADDING):
    bw, bh = x2 - x1, y2 - y1
    pad_x, pad_y = int(bw * padding), int(bh * padding)
    x1n = max(0,      x1 - pad_x)
    y1n = max(0,      y1 - pad_y)
    x2n = min(width,  x2 + pad_x)
    y2n = min(height, y2 + pad_y)
    return frame[y1n:y2n, x1n:x2n], (x1n, y1n, x2n, y2n)

# ──────────────────────────────────────────────
#  PREPROCESS CROP → ONNX INPUT
# ──────────────────────────────────────────────
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
def preprocess_crop(crop_bgr: np.ndarray, img_size: int) -> np.ndarray:
    """
    Resize crop to 1.1 * img_size (like torchvision.Resize),
    then center‑crop to img_size, normalize with ImageNet mean/std,
    and return a tensor of shape (1, 3, H, W) float32.
    """
    # Resize (emulate torchvision.Resize(int(img_size*1.1)))
    resize_dim = int(img_size * 1.1)
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(crop_rgb, (resize_dim, resize_dim), interpolation=cv2.INTER_LINEAR)
    # Center crop to img_size
    start = (resize_dim - img_size) // 2
    crop_center = resized[start:start + img_size, start:start + img_size]
    # Normalize using ImageNet statistics
    norm = (crop_center.astype(np.float32) / 255.0 - MEAN) / STD
    chw = norm.transpose(2, 0, 1)
    return np.expand_dims(chw, axis=0)
# ──────────────────────────────────────────────
#  SOFTMAX
# ──────────────────────────────────────────────
def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


# ──────────────────────────────────────────────
#  VẼ LABEL LÊN FRAME
# ──────────────────────────────────────────────
# Màu theo class index (thêm màu nếu có nhiều class hơn)
COLORS = [
    (0, 255, 0),    # xanh lá  – class 0
    (0, 0, 255),    # đỏ       – class 1
    (255, 165, 0),  # cam      – class 2
    (255, 0, 255),  # tím      – class 3
    (0, 255, 255),  # cyan     – class 4
]

def draw_result(frame, x1, y1, x2, y2, label: str, conf: float, cls_idx: int):
    color = COLORS[cls_idx % len(COLORS)]
    # Bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    # Label background
    text    = f"{label} {conf:.2f}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, text, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                cv2.LINE_AA)


# ──────────────────────────────────────────────
#  XỬ LÝ MỘT VIDEO
# ──────────────────────────────────────────────
def process_video(
    video_path: str,
    output_path: str | None,
    crop_dir: str | None,
    yolo_model,
    ort_session,
    input_name: str,
    output_name: str,
    meta: dict,
    conf_threshold: float,
    skip_frames: int,
    crops_max_per_class: int = 200,
):
    class_names = meta["class_names"]
    img_size    = meta["img_size_infer"]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  [SKIP] Không mở được: {video_path}")
        return

    fps    = cap.get(cv2.CAP_PROP_FPS) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # ── Tạo subfolder crops/<tên_video>/<class_name>/
    class_crop_dirs = {}
    crop_counters   = {}   # đếm số ảnh đã lưu mỗi class
    if crop_dir:
        video_stem = Path(video_path).stem
        for cls_name in class_names:
            d = os.path.join(crop_dir, video_stem, cls_name)
            os.makedirs(d, exist_ok=True)
            class_crop_dirs[cls_name] = d
            crop_counters[cls_name]   = 0

    print(f"  Đang xử lý: {Path(video_path).name}  ({width}x{height}, {fps:.1f}fps, {total} frames)")

    frame_idx       = 0
    processed       = 0
    t_start         = time.time()
    last_detections = []   # Giữ kết quả frame trước nếu bỏ qua frame

    # ── Khởi tạo bộ lọc nhiễu (Smoother)
    smoother = TemporalSmoother()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # ── Skip frames để tăng FPS trên Pi 4
        if frame_idx % skip_frames == 0:
            processed += 1
            detections = []

            # ── YOLO detect + track người (class 0)
            results = yolo_model.track(
                frame,
                classes=[0],             # chỉ detect người
                conf=conf_threshold,
                persist=True,            # quan trọng: giữ ID qua các frame
                verbose=False,
            )

            for result in results:
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    continue

                for box in boxes:
                    # Lấy track_id từ YOLO
                    if box.id is None:
                        continue
                    track_id = int(box.id[0])

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                    # ── Padding 10% (giống bản .pth)
                    crop, (px1, py1, px2, py2) = get_padded_crop(frame, x1, y1, x2, y2, width, height)
                    
                    if crop.size == 0:
                        continue

                    # ── MobileNetV2 phân loại hành vi
                    inp    = preprocess_crop(crop, img_size)
                    logits = ort_session.run([output_name], {input_name: inp})[0][0]
                    probs  = softmax(logits)
                    
                    # Giả sử class_names[0] là 'intrusion' hoặc 'normal'
                    # Tìm xác suất của 'intrusion' để đưa vào smoother
                    try:
                        intr_idx = class_names.index("intrusion")
                        intr_prob = float(probs[intr_idx])
                    except ValueError:
                        # Nếu không có class 'intrusion', dùng class index 1 (giả định)
                        intr_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])

                    # ── Cập nhật bộ lọc nhiễu
                    smooth_label, avg_prob = smoother.update(track_id, intr_prob)
                    
                    # Lấy class index tương ứng với label đã lọc
                    try:
                        cls_id = class_names.index(smooth_label)
                    except ValueError:
                        cls_id = 0

                    detections.append((px1, py1, px2, py2, smooth_label, avg_prob, cls_id, crop))

                    # ── Lưu crop nếu chưa đủ giới hạn
                    if crop_dir and crop_counters[smooth_label] < crops_max_per_class:
                        # Tên file: frame0012_p0_conf0.92.jpg
                        fname = (
                            f"frame{frame_idx:06d}"
                            f"_tid{track_id}"
                            f"_conf{avg_prob:.2f}.jpg"
                        )
                        save_path = os.path.join(class_crop_dirs[smooth_label], fname)

                        # Lưu crop có padding để giống dữ liệu test bản .pth
                        cv2.imwrite(save_path, crop)
                        crop_counters[smooth_label] += 1

            last_detections = detections

        # ── Vẽ kết quả (dùng last_detections cho frame bị skip)
        for (x1, y1, x2, y2, label, cls_cf, cls_id, _) in last_detections:
            draw_result(frame, x1, y1, x2, y2, label, cls_cf, cls_id)

        # ── FPS overlay
        elapsed = time.time() - t_start
        fps_cur = processed / elapsed if elapsed > 0 else 0
        cv2.putText(
            frame, f"FPS: {fps_cur:.1f}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA
        )

        if writer:
            writer.write(frame)

    cap.release()
    if writer:
        writer.release()

    elapsed = time.time() - t_start
    print(f"  Hoàn thành: {processed} frames xử lý / {frame_idx} tổng  |  {elapsed:.1f}s  |  ~{processed/elapsed:.1f} FPS")
    if output_path:
        print(f"  Video lưu : {output_path}")
    if crop_dir:
        total_crops = sum(crop_counters.values())
        print(f"  Crops lưu : {total_crops} ảnh  →  {os.path.join(crop_dir, Path(video_path).stem)}")
        for cls_name, cnt in crop_counters.items():
            print(f"             {cls_name:20s}: {cnt} ảnh")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def main():
    # ── Kiểm tra đường dẫn
    assert os.path.isdir(VIDEO_DIR),  f"Không tìm thấy folder video: {VIDEO_DIR}"
    assert os.path.isfile(MODEL_PATH), f"Không tìm thấy model ONNX : {MODEL_PATH}"
    assert os.path.isfile(META_PATH),  f"Không tìm thấy metadata   : {META_PATH}"
    if YOLO_PATH is not None:
        assert os.path.isfile(YOLO_PATH), f"Không tìm thấy YOLO weight: {YOLO_PATH}"

    # ── Output folder
    output_dir = OUTPUT_DIR or os.path.join(VIDEO_DIR, "results")
    if SAVE_VIDEO:
        os.makedirs(output_dir, exist_ok=True)

    # ── Crops folder
    crop_dir = None
    if SAVE_CROPS:
        crop_dir = os.path.join(output_dir, "crops")
        os.makedirs(crop_dir, exist_ok=True)

    print("\n" + "="*60)
    print("  INFERENCE – VIDEO FOLDER")
    print("="*60)
    print(f"  Video dir  : {VIDEO_DIR}")
    print(f"  Model      : {MODEL_PATH}")
    print(f"  Meta       : {META_PATH}")
    print(f"  YOLO       : {YOLO_PATH or 'tự tải yolov8n.pt'}")
    print(f"  Output dir : {output_dir if SAVE_VIDEO else '(không lưu)'}")
    print(f"  Crops dir  : {crop_dir if SAVE_CROPS else '(không lưu)'}")
    print(f"  YOLO conf  : {CONF_THRESHOLD}")
    print(f"  Skip frames: {SKIP_FRAMES}")
    print("="*60 + "\n")

    # ── Load
    meta                            = load_meta(META_PATH)
    ort_session, inp_name, out_name = load_onnx_session(MODEL_PATH)
    yolo_model                      = load_yolo(YOLO_PATH, device="cpu")

    # ── Lấy danh sách video
    VIDEO_EXTS  = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}
    video_files = sorted([
        f for f in Path(VIDEO_DIR).iterdir()
        if f.suffix.lower() in VIDEO_EXTS
    ])

    if not video_files:
        print(f"[WARNING] Không tìm thấy video nào trong: {VIDEO_DIR}")
        return

    print(f"Tìm thấy {len(video_files)} video:\n")
    for vf in video_files:
        print(f"  - {vf.name}")
    print()

    # ── Xử lý từng video
    for vf in video_files:
        out_path = None
        if SAVE_VIDEO:
            out_path = os.path.join(output_dir, vf.stem + "_result.mp4")

        process_video(
            video_path          = str(vf),
            output_path         = out_path,
            crop_dir            = crop_dir,
            yolo_model          = yolo_model,
            ort_session         = ort_session,
            input_name          = inp_name,
            output_name         = out_name,
            meta                = meta,
            conf_threshold      = CONF_THRESHOLD,
            skip_frames         = SKIP_FRAMES,
            crops_max_per_class = CROPS_MAX_PER_CLASS,
        )
        print()

    print("="*60)
    print("  HOÀN THÀNH TẤT CẢ VIDEO")
    if SAVE_VIDEO:
        print(f"  Video lưu tại : {output_dir}")
    if SAVE_CROPS:
        print(f"  Crops lưu tại : {crop_dir}")
    print("="*60)


if __name__ == "__main__":
    main()