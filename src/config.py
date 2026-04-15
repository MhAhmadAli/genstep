# GenStep AI Configuration
# Defines all GPIO pin mappings and systemic thresholds

# Ultrasonic Sensors (Trig, Echo)
SONAR_1_PINS = (24, 23)
SONAR_2_PINS = (18, 25)
SONAR_3_PINS = (13, 19)

# IR Sensors
IR_1_PIN = 6
IR_2_PIN = 5

# Feedback
BUZZER_PIN = 8

# Communication (UART RX, TX info - Note: pyserial uses the serial port name like /dev/serial0)
GSM_PORT = "/dev/serial0" # May need to be updated to /dev/ttyS0 or /dev/ttyAMA0 based on Pi config
GPS_PORT = "/dev/serial1" # Depending on UART mapping
BAUD_RATE = 9600
ENABLE_GSM = True
ENABLE_GPS = True

# Emergency messaging
EMERGENCY_PHONE_NUMBER = "+1234567890"
SOS_RATE_LIMIT_SECONDS = 60
GSM_SMS_RETRY_ATTEMPTS = 2
GSM_INIT_RETRY_ATTEMPTS = 2

# GPS read behavior
GPS_READ_RETRIES = 10
GPS_SERIAL_TIMEOUT_SECONDS = 1

# Manual SOS trigger behavior
ENABLE_MANUAL_SOS_STDIN = True
MANUAL_SOS_COMMAND = "sos"

# Actionable Thresholds (in meters)
DIST_LIGHT_ALERT = 3.0
DIST_MODERATE_ALERT = 1.5
DIST_INTENSE_ALERT = 1.0

# Downward Sonar Thresholds - Fallback defaults (in meters)
# Used when no calibration data exists
STEP_UP_THRESHOLD = 0.15
STEP_DOWN_THRESHOLD = 0.45
GROUND_BASELINE = 0.30

# Calibration Settings
import os
CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "calibration.json")
CALIBRATION_TIME_SECONDS = 5.0
STEP_TOLERANCE = 0.15  # Buffer in meters around the baseline
