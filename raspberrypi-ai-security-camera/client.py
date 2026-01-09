import subprocess
import websocket
import time
import serial
import requests
import RPi.GPIO as GPIO
import threading

# ====================== CONFIG ==========================
SERVER = "http://10.95.241.242:5000"
SERVER_GPS = SERVER + "/gps"
SERVER_WS = "ws://10.95.241.242:5000/ws-stream"
SERVER_ALARM = SERVER + "/get_alarm"

# GPIO LOA/Buzzer
BUZZ = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZ, GPIO.OUT)
GPIO.output(BUZZ, GPIO.LOW)

# ======================= GPS INIT =========================
gps = serial.Serial("/dev/serial0", 115200, timeout=1)

def parse_gpsloc(raw):
    parts = raw.split(",")
    lat_raw = parts[1]
    lon_raw = parts[2]

    # --- Latitude ---
    lat_deg = int(lat_raw[:2])
    lat_min = float(lat_raw[2:-1])
    lat = lat_deg + lat_min / 60
    if lat_raw[-1] == "S":
        lat = -lat

    # --- Longitude ---
    lon_deg = int(lon_raw[:3])
    lon_min = float(lon_raw[3:-1])
    lon = lon_deg + lon_min / 60
    if lon_raw[-1] == "W":
        lon = -lon

    return lat, lon

def send_gps(lat, lon):
    try:
        requests.post(SERVER_GPS,
            data={"lat": str(lat), "lon": str(lon)}
        )
    except:
        pass

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def send_at(cmd, delay=0.5):
    gps.write((cmd + "\r").encode())
    time.sleep(delay)
    return gps.read(gps.in_waiting).decode(errors="ignore")


def init_gps():
    print("[GPS] Turning ON GPS...")
    r = send_at("AT+QGPS?")
    if "QGPS: 1" in r:
        print("[GPS] GPS already ON")
    else:
        send_at("AT+QGPS=1", 1)
        print("[GPS] GPS turned ON")







# ===================== CAMERA WS ==========================
ws = websocket.create_connection(SERVER_WS)


cmd = [
    "rpicam-vid",
    "--codec", "mjpeg",
    "-t", "0",
    "-o", "-",
    "--inline",
    "-n",
    "--width", "640",
    "--height", "480",
    "--framerate", "30",
    "--quality", "70"
]



proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

def read_frame(stream):
    data = b""
    while True:
        byte = stream.read(1)
        if not byte:
            return None
        data += byte
        if data.endswith(b'\xff\xd9'):    # JPEG end
            return data

# ================== STATE ALARM ==========================
last_alarm_check = 0
alarm_state = False    # trạng thái hiện tại của loa

# ================== GPS TIMER ============================
last_gps = 0

# ======================== LOOP ===========================
def camera_loop():
    while True:
        frame = read_frame(proc.stdout)
        if frame:
            ws.send(frame, opcode=websocket.ABNF.OPCODE_BINARY)

#==========================================================

init_gps()

def gps_loop():
    while True:
        gps.write(b'AT+QGPSLOC=0\r')
        line = gps.readline().decode(errors="ignore")

        if "+QGPSLOC:" in line:
            raw = line.split(":")[1].strip()
            try:
                lat, lon = parse_gpsloc(raw)
                send_gps(lat, lon)
                print("[GPS]", lat, lon)
            except:
                pass

        time.sleep(1)



def alarm_loop():
    global alarm_state
    while True:
        try:
            st = requests.get(SERVER_ALARM, timeout=1).json()
            new_state = st["alarm"]

            if new_state and not alarm_state:
                GPIO.output(BUZZ, GPIO.HIGH)
                alarm_state = True

            elif not new_state and alarm_state:
                GPIO.output(BUZZ, GPIO.LOW)
                alarm_state = False

        except:
            GPIO.output(BUZZ, GPIO.LOW)
            alarm_state = False

        time.sleep(1)


threading.Thread(target=camera_loop, daemon=True).start()
threading.Thread(target=gps_loop, daemon=True).start()
threading.Thread(target=alarm_loop, daemon=True).start()

while True:
    time.sleep(1)