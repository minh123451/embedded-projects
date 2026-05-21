# AI-Powered Intrusion Detection Camera System

An advanced, edge-computing security system deployed on **Raspberry Pi 4** utilizing a multi-stage Deep Learning pipeline for real-time human intrusion and climbing behavior detection. The system features a custom-designed PCB for hardware alert handling, automated rolling video storage, and a central Web Application for local monitoring and remote control.


## 🚀 Key Features

### 1. Multi-Stage AI Pipeline (Edge Computing)
- **Human Detection:** Utilizes the **YOLO** model to scan the video feed, identify humans, and dynamically crop the bounding boxes.
- **Behavior Classification:** Passes the cropped human image into a trained **MobileNet** classifier to instantly recognize suspicious behaviors (climbing/intrusion).

### 2. Intelligent Rolling Storage Management
- **Event Logging:** Captures and stores time-stamped images immediately upon intrusion detection.
- **Continuous Recording:** Saves 3-minute video segments of the live camera feed.
- **Automated Ring-Buffer (FIFO):** Implements a rolling storage mechanism with a 3-day retention period, automatically overwriting the oldest data when storage limits are reached.

### 3. Hardware Interfacing & Web App Control
- **Instant Local Alarm:** Automatically activates an on-board buzzer using GPIO signaling when an intrusion is validated by the AI.
- **Remote Appliance Control:** Allows users to securely turn high-voltage warning lights On/Off from the web application via custom on-board **PCB relays**.
- **Local Network Web App:** Built with Flask, providing an isolated, secure LAN-accessible dashboard for live streaming, log auditing, and manual peripheral controls.

---

## 📐 System Architecture & Flow

```text
[Camera Feed] 
      │
      ▼
  [YOLO Model] ───► (Detects Human & Crops Image)
      │
      ▼
[MobileNet Model] ───► (Classifies Intrusion/Climbing Behavior)
      │
      ├─► [TRUE] ──► 1. Trigger On-board Buzzer (GPIO)
      │              2. Capture Event Image & Log Timestamp
      │              3. Update Web Dashboard Notification
      │
      └─► [Continuous] ──► Save 3-Min Video Segments ──► 3-Day Ring-Buffer Storage