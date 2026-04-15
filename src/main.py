import time
import select
import sys
from config import *
from sensors.ultrasonic import UltrasonicArray
from sensors.ir import IRArray
from sensors.camera import AIObjectDetector
from feedback.alerter import BuzzerAlerter
from comms.gps import GPSModule
from comms.gsm import GSMModule
from comms.emergency import format_sos_message, should_send_sos
from calibration import CalibrationManager


def _read_manual_sos_trigger():
    if not ENABLE_MANUAL_SOS_STDIN or not sys.stdin.isatty():
        return False
    try:
        readable, _, _ = select.select([sys.stdin], [], [], 0)
        if not readable:
            return False
        command = sys.stdin.readline().strip().lower()
        return command == MANUAL_SOS_COMMAND.lower()
    except Exception:
        return False


def main():
    print("Initializing GenStep AI...")

    # Hardware Init
    sonar = UltrasonicArray(SONAR_1_PINS, SONAR_2_PINS, SONAR_3_PINS)
    ir = IRArray(IR_1_PIN, IR_2_PIN)
    camera = AIObjectDetector()
    buzzer = BuzzerAlerter(BUZZER_PIN)

    gps = None
    gsm = None

    if ENABLE_GPS:
        gps = GPSModule(
            GPS_PORT,
            BAUD_RATE,
            timeout=GPS_SERIAL_TIMEOUT_SECONDS,
            read_retries=GPS_READ_RETRIES,
        )
        if gps.serial:
            print(f"[GPS] Enabled on {GPS_PORT}.")
        else:
            print(f"[GPS] Disabled due to initialization failure: {gps.last_error}")
            gps = None
    else:
        print("[GPS] Disabled by configuration.")

    if ENABLE_GSM:
        gsm = GSMModule(
            GSM_PORT,
            BAUD_RATE,
            init_retries=GSM_INIT_RETRY_ATTEMPTS,
        )
        if gsm.serial:
            print(f"[GSM] Enabled on {GSM_PORT}.")
        else:
            print(f"[GSM] Disabled due to initialization failure: {gsm.last_error}")
            gsm = None
    else:
        print("[GSM] Disabled by configuration.")

    # Load calibration (falls back to defaults if no file exists)
    cal = CalibrationManager()
    cal_data = cal.load()
    step_up = cal_data["step_up_threshold"]
    step_down = cal_data["step_down_threshold"]
    print(f"[Thresholds] Step-up: {step_up:.3f}m | Step-down: {step_down:.3f}m")

    current_alert_level = 0  # 0=none, 1=light, 2=moderate, 3=intense
    last_sos_sent_at = 0.0

    print("System active. Monitoring environments...")
    if ENABLE_MANUAL_SOS_STDIN and sys.stdin.isatty():
        print(f"Type '{MANUAL_SOS_COMMAND}' then press Enter to manually send SOS.")

    try:
        while True:
            # 1. Read Obstacle Distance (Front)
            distance = sonar.get_obstacle_distance()
            
            # 2. Read Ground Distance (Downward)
            ground_dist = sonar.get_ground_distance()
            
            # 3. Read IR (drop-off)
            drop_off = ir.detect_dropoff()

            # 4. Read camera AI detections
            # objects = camera.analyze_frame()

            # 5. Logic & Feedback
            is_step = ground_dist > step_down or ground_dist < step_up
            intense_condition = drop_off or is_step or distance < DIST_INTENSE_ALERT

            if drop_off or is_step:
                # Extreme danger or step/drop-off detected, immediate intense alert
                if current_alert_level != 3:
                    buzzer.intense_alert()
                    current_alert_level = 3

            elif distance < DIST_INTENSE_ALERT:
                if current_alert_level != 3:
                    buzzer.intense_alert()
                    current_alert_level = 3

            elif distance < DIST_MODERATE_ALERT:
                if current_alert_level != 2:
                    buzzer.moderate_alert()
                    current_alert_level = 2

            elif distance < DIST_LIGHT_ALERT:
                if current_alert_level != 1:
                    buzzer.light_alert()
                    current_alert_level = 1

            else:
                if current_alert_level != 0:
                    buzzer.stop()
                    current_alert_level = 0

            manual_sos = _read_manual_sos_trigger()
            now = time.monotonic()
            if should_send_sos(
                intense_condition,
                manual_sos,
                now,
                last_sos_sent_at,
                SOS_RATE_LIMIT_SECONDS,
            ):
                trigger_reason = "manual" if manual_sos else "blocked"
                location = gps.get_location() if gps else None
                message = format_sos_message(trigger_reason, location)

                if gsm and EMERGENCY_PHONE_NUMBER:
                    sent = gsm.send_sms(
                        EMERGENCY_PHONE_NUMBER,
                        message,
                        retry_attempts=GSM_SMS_RETRY_ATTEMPTS,
                    )
                    if sent:
                        print(f"[SOS] Sent successfully ({trigger_reason}).")
                        last_sos_sent_at = now
                    else:
                        print(f"[SOS] Send failed: {gsm.last_error}")
                elif not gsm:
                    print("[SOS] Skipped send: GSM module unavailable.")
                else:
                    print("[SOS] Skipped send: EMERGENCY_PHONE_NUMBER is not configured.")

            # Small delay to prevent CPU pegging
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down safely...")
    finally:
        sonar.close()
        ir.close()
        camera.close()
        buzzer.close()
        if gps:
            gps.close()
        if gsm:
            gsm.close()

if __name__ == "__main__":
    main()
