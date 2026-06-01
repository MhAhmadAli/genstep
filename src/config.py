# GenStep AI Configuration
# Defines all GPIO pin mappings and systemic thresholds

# Ultrasonic Sensors (Trig, Echo)
# Sensor order:
#   SONAR_1 = bottom (downward-facing)
#   SONAR_2 = middle (front-facing)
#   SONAR_3 = top (front-facing)
SONAR_1_PINS = (18, 25)
SONAR_2_PINS = (13, 19)
SONAR_3_PINS = (24, 23)

# IR Sensors
IR_1_PIN = 6
IR_2_PIN = 5

# Feedback
BUZZER_PIN = 8
# Minimum silence gap between buzzer starts to reduce repeated annoyance.
BUZZER_COOLDOWN_SECONDS = 10

# Communication
# Default mode uses pigpio software serial on GPIO pins.
USE_SOFTWARE_SERIAL = True

# Pi-side serial pins (BCM numbering) used when USE_SOFTWARE_SERIAL=True.
# GSM module: module TX -> Pi RX, module RX -> Pi TX
GSM_RX_PIN = 2
GSM_TX_PIN = 3
# GPS module: module TX -> Pi RX, module RX -> Pi TX
GPS_RX_PIN = 14
GPS_TX_PIN = 15

# Optional hardware UART fallback when USE_SOFTWARE_SERIAL=False.
GSM_PORT = "/dev/serial0"
GPS_PORT = "/dev/serial1"
BAUD_RATE = 9600
ENABLE_GSM = True
ENABLE_GPS = True

# Emergency messaging
EMERGENCY_PHONE_NUMBER = "+1234567890"
SOS_RATE_LIMIT_SECONDS = 60
GSM_SMS_RETRY_ATTEMPTS = 2
GSM_INIT_RETRY_ATTEMPTS = 2
GSM_SERIAL_TIMEOUT_SECONDS = 1

# GPS read behavior
GPS_READ_RETRIES = 10
GPS_SERIAL_TIMEOUT_SECONDS = 1

# Manual SOS trigger behavior
ENABLE_MANUAL_SOS_STDIN = True
MANUAL_SOS_COMMAND = "sos"

# Mobile app API server
ENABLE_MOBILE_API = True
MOBILE_API_HOST = "0.0.0.0"
MOBILE_API_PORT = 5000

# Camera AI
ENABLE_CAMERA_AI = True
CAMERA_INDEX = 0
CAMERA_USE_PICAMERA2 = True
# Capture at a smaller source resolution for better Pi-side inference throughput.
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAME_INTERVAL_SECONDS = 0.2
CAMERA_IMAGE_SIZE = 320
STAIRS_MODEL_PATH = "models/stairs.pt"
GENERAL_MODEL_PATH = "yolo11n.pt"
STAIRS_CONFIDENCE_THRESHOLD = 0.45
GENERAL_CONFIDENCE_THRESHOLD = 0.35
CAMERA_STAIRS_INFER_EVERY_N = 1
CAMERA_GENERAL_INFER_EVERY_N = 2
# Classes treated as path hazards by the general model.
GENERAL_HAZARD_CLASSES = {"person", "bicycle", "motorcycle", "car", "bus", "truck"}

# Actionable Thresholds (in meters)
DIST_LIGHT_ALERT = 1.0
DIST_MODERATE_ALERT = 0.5
DIST_INTENSE_ALERT = 0.3

# Downward Sonar Thresholds - Fallback defaults (in meters)
# Used when no calibration data exists
STEP_UP_THRESHOLD = 0.15
STEP_DOWN_THRESHOLD = 0.45
GROUND_BASELINE = 0.30
STEP_DETECTION_MAX_DISTANCE = 1.0
STEP_CONFIRMATION_READS = 3

# Startup grace periods (seconds) to prevent false alerts/SOS while sensors settle.
ALERT_STARTUP_GRACE_SECONDS = 8
SOS_STARTUP_GRACE_SECONDS = 20
ALERT_MAX_ACTIVE_SECONDS = 5

# Calibration Settings
import os
CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "calibration.json")
CALIBRATION_TIME_SECONDS = 5.0
STEP_TOLERANCE = 0.15  # Buffer in meters around the baseline
