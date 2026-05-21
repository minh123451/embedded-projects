import RPi.GPIO as GPIO
import time
import threading
from config import GPIO_BUZZER, ALARM_DURATION

class BuzzerManager:
    def __init__(self):
        self.pin = GPIO_BUZZER
        self.duration = ALARM_DURATION
        self._manual_on = False
        
        # Thiết lập GPIO
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)
            print(f"[Buzzer] Initialized on GPIO {self.pin}")
        except Exception as e:
            print(f"[Buzzer] [ERROR] Failed to init GPIO: {e}")

    def trigger(self):
        """Kích hoạt còi kêu tự động (hồi dài)"""
        if self._manual_on:
            return

        def _run_alarm():
            print(f"[Buzzer] Alarm triggered for {self.duration}s")
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(self.duration)
            if not self._manual_on:
                GPIO.output(self.pin, GPIO.LOW)
                print("[Buzzer] Alarm off")
        
        # Chạy trong luồng riêng để không làm đứng ứng dụng chính
        threading.Thread(target=_run_alarm, daemon=True).start()

    def set_manual(self, state):
        """Điều khiển Bật/Tắt thủ công từ Dashboard với thời gian chờ ALARM_DURATION"""
        if state:
            if self._manual_on: # Đã đang bật rồi thì thôi
                return
            
            self._manual_on = True
            
            def _run_manual():
                print(f"[Buzzer] Manual Pulse started ({self.duration}s)")
                GPIO.output(self.pin, GPIO.HIGH)
                
                # Chờ 5s nhưng cho phép ngắt nếu bấm Tắt thủ công
                start_time = time.time()
                while time.time() - start_time < self.duration:
                    if not self._manual_on: # Nếu flag bị gạt xuống False bởi lệnh Tắt
                        break
                    time.sleep(0.1)
                
                GPIO.output(self.pin, GPIO.LOW)
                self._manual_on = False # Reset trạng thái
                print("[Buzzer] Manual Pulse ended")
            
            threading.Thread(target=_run_manual, daemon=True).start()
        else:
            self._manual_on = False
            GPIO.output(self.pin, GPIO.LOW)
            print("[Buzzer] Manual OFF (Interrupted)")

    def is_active(self):
        """Kiểm tra trạng thái hiện tại của còi"""
        try:
            return GPIO.input(self.pin) == GPIO.HIGH
        except:
            return self._manual_on

    def cleanup(self):
        """Dọn dẹp GPIO khi dừng ứng dụng"""
        GPIO.output(self.pin, GPIO.LOW)
        GPIO.cleanup(self.pin)
