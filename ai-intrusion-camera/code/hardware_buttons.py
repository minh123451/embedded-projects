import RPi.GPIO as GPIO
import os
import time
from config import GPIO_REBOOT_BTN

class HardwareButtons:
    def __init__(self):
        self.reboot_pin = GPIO_REBOOT_BTN
        
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            
            # Thiết lập chân INPUT, kích hoạt điện trở kéo LÊN (Pull-Up) bên trong Pi
            GPIO.setup(self.reboot_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Đăng ký Ngắt phần cứng (Hardware Interrupt)
            # Phát hiện sự thay đổi từ HIGH xuống LOW (FALLING - Cạnh xuống)
            # bouncetime=2000 (2 giây) để chống dội phím (debounce)
            GPIO.add_event_detect(
                self.reboot_pin, 
                GPIO.FALLING, 
                callback=self.reboot_system, 
                bouncetime=2000
            )
            print(f"[HardwareButtons] Emergency Reboot Button initialized on GPIO {self.reboot_pin} (Interrupt mode)")
        except Exception as e:
            print(f"[HardwareButtons] [ERROR] Failed to init GPIO for buttons: {e}")

    def reboot_system(self, channel):
        """Hàm callback được RPi.GPIO tự động gọi trên luồng riêng khi nút bị nhấn"""
        print(f"\n[HardwareButtons] !!! EMERGENCY REBOOT BUTTON PRESSED ON GPIO {channel} !!!")
        print("[HardwareButtons] Initiating system reboot in 1 second...")
        time.sleep(1) # Chờ 1 chút để log kịp ghi ra
        # Gọi lệnh khởi động lại mức hệ điều hành
        os.system("sudo reboot")
        
    def cleanup(self):
        """Dọn dẹp GPIO khi thoát ứng dụng"""
        try:
            GPIO.remove_event_detect(self.reboot_pin)
            GPIO.cleanup(self.reboot_pin)
        except:
            pass
