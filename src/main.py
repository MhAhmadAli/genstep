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
from comms.api_server import MobileAPIServer
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
    camera = AIObjectDetector(
        camera_index=CAMERA_INDEX,
        enabled=ENABLE_CAMERA_AI,
        stairs_model_path=STAIRS_MODEL_PATH,
        general_model_path=GENERAL_MODEL_PATH,
        stairs_conf=STAIRS_CONFIDENCE_THRESHOLD,
        general_conf=GENERAL_CONFIDENCE_THRESHOLD,
        hazard_classes=GENERAL_HAZARD_CLASSES,
        frame_interval_seconds=CAMERA_FRAME_INTERVAL_SECONDS,
        image_size=CAMERA_IMAGE_SIZE,
    )
    buzzer = BuzzerAlerter(BUZZER_PIN)

    gps = None
    gsm = None
    api_server = None

    if ENABLE_GPS:
        if USE_SOFTWARE_SERIAL:
            gps = GPSModule(
                baud_rate=BAUD_RATE,
                timeout=GPS_SERIAL_TIMEOUT_SECONDS,
                read_retries=GPS_READ_RETRIES,
                rx_pin=GPS_RX_PIN,
                tx_pin=GPS_TX_PIN,
            )
            gps_endpoint = f"GPIO RX{GPS_RX_PIN}/TX{GPS_TX_PIN} (software serial)"
        else:
            gps = GPSModule(
                GPS_PORT,
                BAUD_RATE,
                timeout=GPS_SERIAL_TIMEOUT_SECONDS,
                read_retries=GPS_READ_RETRIES,
            )
            gps_endpoint = GPS_PORT
        if gps.serial:
            print(f"[GPS] Enabled on {gps_endpoint}.")
        else:
            print(f"[GPS] Disabled due to initialization failure: {gps.last_error}")
            gps = None
    else:
        print("[GPS] Disabled by configuration.")

    if ENABLE_GSM:
        if USE_SOFTWARE_SERIAL:
            gsm = GSMModule(
                baud_rate=BAUD_RATE,
                timeout=GSM_SERIAL_TIMEOUT_SECONDS,
                init_retries=GSM_INIT_RETRY_ATTEMPTS,
                rx_pin=GSM_RX_PIN,
                tx_pin=GSM_TX_PIN,
            )
            gsm_endpoint = f"GPIO RX{GSM_RX_PIN}/TX{GSM_TX_PIN} (software serial)"
        else:
            gsm = GSMModule(
                GSM_PORT,
                BAUD_RATE,
                timeout=GSM_SERIAL_TIMEOUT_SECONDS,
                init_retries=GSM_INIT_RETRY_ATTEMPTS,
            )
            gsm_endpoint = GSM_PORT
        if gsm.serial:
            print(f"[GSM] Enabled on {gsm_endpoint}.")
        else:
            print(f"[GSM] Disabled due to initialization failure: {gsm.last_error}")
            gsm = None
    else:
        print("[GSM] Disabled by configuration.")

    if ENABLE_MOBILE_API:
        api_server = MobileAPIServer(MOBILE_API_HOST, MOBILE_API_PORT)
        api_server.start()
        print(f"[API] Enabled on http://{MOBILE_API_HOST}:{MOBILE_API_PORT}")
    else:
        print("[API] Disabled by configuration.")

    if ENABLE_CAMERA_AI and camera.enabled:
        print("[Camera] AI inference enabled.")
    elif ENABLE_CAMERA_AI:
        print(f"[Camera] Disabled due to initialization failure: {camera.last_error}")
    else:
        print("[Camera] Disabled by configuration.")

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
            objects = camera.analyze_frame() if camera.enabled else []
            camera_hazards = camera.summarize_hazards(objects) if camera.enabled else {
                "stairs_detected": False,
                "general_hazard_detected": False,
                "labels": [],
            }

            # 5. Logic & Feedback
            is_step = ground_dist > step_down or ground_dist < step_up
            camera_intense_condition = (
                camera_hazards["stairs_detected"] or camera_hazards["general_hazard_detected"]
            )
            intense_condition = (
                drop_off
                or is_step
                or distance < DIST_INTENSE_ALERT
                or camera_intense_condition
            )

            if drop_off or is_step or camera_hazards["stairs_detected"]:
                # Extreme danger or step/drop-off detected, immediate intense alert
                if current_alert_level != 3:
                    buzzer.intense_alert()
                    current_alert_level = 3

            elif camera_hazards["general_hazard_detected"]:
                if current_alert_level != 2:
                    buzzer.moderate_alert()
                    current_alert_level = 2

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

            if api_server:
                api_server.update_state(
                    status="running",
                    obstacle_distance_m=distance,
                    ground_distance_m=ground_dist,
                    drop_off=drop_off,
                    is_step=is_step,
                    intense_condition=intense_condition,
                    alert_level=current_alert_level,
                    camera_enabled=camera.enabled,
                    camera_hazards=camera_hazards,
                    camera_detections=objects[:10],
                )

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
                if api_server:
                    api_server.update_sos(
                        last_attempt_unix=time.time(),
                        last_trigger_reason=trigger_reason,
                        last_result="attempting",
                        last_error=None,
                    )

                if gsm and EMERGENCY_PHONE_NUMBER:
                    sent = gsm.send_sms(
                        EMERGENCY_PHONE_NUMBER,
                        message,
                        retry_attempts=GSM_SMS_RETRY_ATTEMPTS,
                    )
                    if sent:
                        print(f"[SOS] Sent successfully ({trigger_reason}).")
                        last_sos_sent_at = now
                        if api_server:
                            api_server.update_sos(
                                last_sent_unix=time.time(),
                                last_result="sent",
                                last_error=None,
                            )
                    else:
                        print(f"[SOS] Send failed: {gsm.last_error}")
                        if api_server:
                            api_server.update_sos(
                                last_result="failed",
                                last_error=gsm.last_error,
                            )
                elif not gsm:
                    print("[SOS] Skipped send: GSM module unavailable.")
                    if api_server:
                        api_server.update_sos(
                            last_result="skipped",
                            last_error="GSM module unavailable",
                        )
                else:
                    print("[SOS] Skipped send: EMERGENCY_PHONE_NUMBER is not configured.")
                    if api_server:
                        api_server.update_sos(
                            last_result="skipped",
                            last_error="EMERGENCY_PHONE_NUMBER is not configured",
                        )

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
