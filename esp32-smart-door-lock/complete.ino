#include <Keypad.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Adafruit_Fingerprint.h>
#include <ESP32Servo.h>
#include <WiFi.h>

#define BLYNK_TEMPLATE_ID "TMPL6HhLs-NAY"
#define BLYNK_TEMPLATE_NAME "doan"
#define BLYNK_AUTH_TOKEN "zJqa2htDByRn-oga9_Hy9IEdMZ9mA_BY"
#include <BlynkSimpleEsp32.h>

Servo myservo;  // Tạo đối tượng servo

// #define BLYNK_TEMPLATE_ID "TMPL6HhLs-NAY"
// #define BLYNK_TEMPLATE_NAME "doan"
// #define BLYNK_AUTH_TOKEN "zJqa2htDByRn-oga9_Hy9IEdMZ9mA_BY"

char ssid[] = "gjghh";
char pass[] = "11123456";

#define SS_PIN 5
#define RST_PIN 4
#define BUZZER_PIN 2
const int servoPin = 33;  // GPIO 33 cho tín hiệu PWM của servo
const int smokePin = 34;               // MP-2 nối vào GPIO 34
const int smokeThreshold = 3600;       // Ngưỡng phát hiện khói
bool smokeAlertTriggered = false;      // Tránh cảnh báo liên tục

// thay đổi vân tay 
bool waitingForSecondStar = false;
unsigned long lastStarTime = 0;
int currentFingerID = 1; // ID vân tay bắt đầu từ 1



// LCD
LiquidCrystal_I2C lcd(0x27, 16, 2); // Đổi thành 0x3F nếu cần

// RFID
MFRC522 rfid(SS_PIN, RST_PIN);

// Vân tay
HardwareSerial fingerSerial(2); // UART2
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fingerSerial);

// Keypad
const byte ROWS = 4;
const byte COLS = 3;
char keys[ROWS][COLS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'}
};
byte rowPins[ROWS] = {13, 14, 12, 25};  // R1-R4
byte colPins[COLS] = {26, 27, 32};      // C1-C3
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// Biến lưu mã PIN
String inputPIN = "";
String correctPIN = "1234";


// Hàm tìm ID trống trong cảm biến vân tay
int findFreeID() {
  for (int id = 1; id < 127; id++) { // ID hợp lệ thường từ 1 đến 126
    if (finger.loadModel(id) != FINGERPRINT_OK) {
      return id; // Trả về ID chưa có vân tay
    }
  }
  return -1; // Không còn chỗ trống
}


void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("ESP32 bat dau chay setup()");  // ← Thêm dòng này
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("He thong san sang");

  // Khởi tạo servo
  myservo.setPeriodHertz(50);    // SG92R yêu cầu tần số PWM 50Hz
  myservo.attach(servoPin, 500, 2400);
  // ✅ Kiểm tra servo có attach được không
  if (myservo.attached()) {
    Serial.println("✅ Servo đã được attach thành công");
  } else {
    Serial.println("❌ Servo CHƯA attach");
  }
  // myservo.write(0); // Đặt servo về 0 độ ban đầu
  // Serial.println("Servo khởi động ở góc 0 độ");

  SPI.begin(18, 19, 23, 5); // SCK, MISO, MOSI, SS
  rfid.PCD_Init();
  Serial.println("RFID đã khởi tạo");

  fingerSerial.begin(57600, SERIAL_8N1, 16, 17); // RX, TX
  finger.begin(57600);
  if (finger.verifyPassword()) {
    Serial.println("Tìm thấy cảm biến vân tay!");
  } else {
    Serial.println("Không tìm thấy cảm biến vân tay!");
    while (1); // Dừng nếu cảm biến lỗi
  }

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
}

void loop() {
  Blynk.run();
  handleKeypad();
  handleRFID();
  handleFingerprint();
  handleSmokeSensor();
}

// ========== XỬ LÝ KEYPAD ==========
void handleKeypad() {
  char key = keypad.getKey();
  if (key) {
    Serial.print("Nhấn phím: ");
    Serial.println(key);
    lcd.setCursor(0, 1);
    lcd.print("Phim: ");
    lcd.print(key);
    lcd.print("      ");

    if (key == '#') {
      if (inputPIN == "**") {
        Serial.println("Yêu cầu ghi dấu vân tay mới!");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Tim ID trong...");

        int emptyID = findFreeID();  // Tìm ID trống
        delay(500);

        if (emptyID != -1) {
          lcd.clear();
          lcd.setCursor(0, 0);
          lcd.print("Ghi ID moi: ");
          lcd.print(emptyID);

          Serial.print("Bắt đầu ghi vân tay vào ID: ");
          Serial.println(emptyID);

          bool success = enrollFingerprint(emptyID);  // Hàm đã có sẵn trong mã

          if (success) {
            Serial.println("✔️ Ghi vân tay thành công!");
            lcd.setCursor(0, 1);
            lcd.print("Thanh cong!");
          } else {
            Serial.println("❌ Ghi vân tay thất bại.");
            lcd.setCursor(0, 1);
            lcd.print("That bai!");
          }
        } else {
          Serial.println("❌ Không còn ID trống.");
          lcd.setCursor(0, 1);
          lcd.print("Het bo nho!");
        }

        delay(3000);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("He thong san sang");
        inputPIN = "";
        return;
      }


      if (inputPIN == correctPIN) {
        Serial.println("Mở khóa bằng PIN");
        Blynk.virtualWrite(V0, "Mo cua bang password"); 
        openDoor();
      } else {
        Serial.println("PIN sai");
        lcd.setCursor(0, 1);
        lcd.print("PIN sai       ");
      }
      inputPIN = ""; // Reset sau khi nhấn #
    } else if (key == '*0') {
      inputPIN = ""; // Xóa
      lcd.setCursor(0, 1);
      lcd.print("Da xoa        ");
    } else {
      inputPIN += key;
    }
  }
}

// ========== XỬ LÝ RFID ==========
void handleRFID() {
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    Serial.print("UID thẻ: ");
    for (byte i = 0; i < rfid.uid.size; i++) {
      Serial.print(rfid.uid.uidByte[i] < 0x10 ? " 0" : " ");
      Serial.print(rfid.uid.uidByte[i], HEX);
    }
    Serial.println();
    Serial.println("Mở khóa bằng RFID");
    Blynk.virtualWrite(V0, "Mo cua bang RFID");
    openDoor();
    rfid.PICC_HaltA();
  }
}

// ========== XỬ LÝ VÂN TAY ==========
void handleFingerprint() {
  int id = getFingerprintIDez();
  if (id >= 0) {
    Serial.print("Mở khóa bằng vân tay ID: ");
    Serial.println(id);
    Blynk.virtualWrite(V0, "Mo cua bang van tay ID: " + String(id));
    openDoor();
  }
}

int getFingerprintIDez() {
  if (finger.getImage() != FINGERPRINT_OK) return -1;
  if (finger.image2Tz() != FINGERPRINT_OK) return -1;
  if (finger.fingerFastSearch() != FINGERPRINT_OK) return -1;
  return finger.fingerID;
}

// ========== GHI DẤU VÂN TAY MỚI ==========
bool enrollFingerprint(int id) {
  int p = -1;
  Serial.print("Ghi vân tay mới vào ID: "); Serial.println(id);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ghi van tay ID ");
  lcd.print(id);

  delay(2000);
  while (p != FINGERPRINT_OK) {
    Serial.println("Đặt ngón tay...");
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) continue;
    if (p != FINGERPRINT_OK) return false;
  }

  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) return false;

  Serial.println("Lấy tay ra...");
  lcd.setCursor(0, 1);
  lcd.print("Lay tay ra...");
  delay(2000);

  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }

  Serial.println("Đặt lại ngón tay...");
  lcd.setCursor(0, 1);
  lcd.print("Dat lai van tay");
  delay(1000);

  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) continue;
    if (p != FINGERPRINT_OK) return false;
  }

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) return false;

  p = finger.createModel();
  if (p != FINGERPRINT_OK) return false;

  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println("✅ Ghi vân tay thành công!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Ghi thanh cong!");
    delay(2000);
    return true;
  } else {
    Serial.println("❌ Ghi vân tay thất bại");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("That bai!");
    delay(2000);
    return false;
  }
}


// ========== KÍCH HOẠT MOTOR ==========
void activateServo() {
  Serial.println("Vào hàm activateServo()");
  // tone(BUZZER_PIN, 1000);
  // delay(300);
  // noTone(BUZZER_PIN);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(300);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.println("Tín hiệu kích hoạt hàm! Quay servo đến 90 độ");

  myservo.write(0); // Đặt servo về 0 độ ban đầu
  Serial.print("Góc servo: ");
  Serial.println(myservo.read());
  delay(1000);

  // Quay servo đến 180 độ
  myservo.write(90);
  Serial.print("Góc servo: ");
  Serial.println(myservo.read());

  Serial.println("Servo đang ở góc 180 độ, giữ trong 5 giây...");
  delay(5000);

  // Trả servo về 0 độ
  Serial.println("Trả servo về góc 0 độ");
  myservo.write(0);
  Serial.print("Góc servo: ");
  Serial.println(myservo.read());
}

// ========== PHÁT HIỆN KHỐI ==========

void handleSmokeSensor() {
  int smokeValue = analogRead(smokePin);
  Serial.print("Giá trị khói: ");
  Serial.println(smokeValue);
  Blynk.virtualWrite(V1, smokeValue);
  if (smokeValue > smokeThreshold && !smokeAlertTriggered) {
    smokeAlertTriggered = true;

    Serial.println("⚠️ Phát hiện khói! Kích hoạt báo động...");
    Blynk.virtualWrite(V3, "fire warning");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("PHAT HIEN KHOI!");
    digitalWrite(BUZZER_PIN, HIGH);  // Bật còi
    delay(10000);                    // Hú còi 10 giây
    digitalWrite(BUZZER_PIN, LOW);   // Tắt còi

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("He thong san sang");
  } else if (smokeValue <= smokeThreshold) {
    smokeAlertTriggered = false;  // Reset khi giá trị bình thường
  }
}

BLYNK_WRITE(V2) {
  int state = param.asInt();
  if (state == 1) {
    Serial.println("Yeu cau mo cua tu xa");
    Blynk.virtualWrite(V0, "Mo cua tu xa");
    openDoor();
        // Sau khi mở cửa xong, đặt lại nút thành OFF
    Blynk.virtualWrite(V2, 0);
  }
}


// ========== MỞ KHÓA ==========
void openDoor() {
  Serial.println("Vào hàm openDoor()");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Cua da mo khoa");
    // Gửi thông báo đến Blynk Terminal
  Blynk.virtualWrite(V0, "Mo cua thanh cong!");
  activateServo();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("He thong san sang");
}

