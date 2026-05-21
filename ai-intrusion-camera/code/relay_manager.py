import RPi.GPIO as GPIO

class RelayManager:
    def __init__(self):
        from config import GPIO_RELAY
        self.pin = GPIO_RELAY
        self._is_on = False
        
        # Thiết lập GPIO
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            # Tắt relay lúc khởi động (tùy thuộc vào relay kích LOW hay HIGH, giả sử kích HIGH)
            GPIO.output(self.pin, GPIO.LOW)
            print(f"[Relay] Initialized on GPIO {self.pin}")
        except Exception as e:
            print(f"[Relay] [ERROR] Failed to init GPIO: {e}")

    def set_state(self, state):
        """Bật/Tắt relay theo yêu cầu"""
        try:
            if state:
                GPIO.output(self.pin, GPIO.HIGH)
                self._is_on = True
                print(f"[Relay] Turned ON (GPIO {self.pin})")
            else:
                GPIO.output(self.pin, GPIO.LOW)
                self._is_on = False
                print(f"[Relay] Turned OFF (GPIO {self.pin})")
        except Exception as e:
            print(f"[Relay] [ERROR] Failed to set state: {e}")

    def is_active(self):
        """Kiểm tra trạng thái hiện tại của relay"""
        try:
            return GPIO.input(self.pin) == GPIO.HIGH
        except:
            return self._is_on

    def cleanup(self):
        """Dọn dẹp GPIO khi dừng ứng dụng"""
        try:
            GPIO.output(self.pin, GPIO.LOW)
            self._is_on = False
            GPIO.cleanup(self.pin)
        except:
            pass
