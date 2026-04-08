import time
from config import *
from sensors.ultrasonic import UltrasonicArray
from sensors.ir import IRArray
from sensors.camera import AIObjectDetector
from feedback.alerter import BuzzerAlerter
from comms.gps import GPSModule
from comms.gsm import GSMModule
from calibration import CalibrationManager

def main():
    print("Initializing GenStep AI...")

    # Hardware Init
    sonar = UltrasonicArray(SONAR_1_PINS, SONAR_2_PINS, SONAR_3_PINS)
    ir = IRArray(IR_1_PIN, IR_2_PIN)
    camera = AIObjectDetector()
    buzzer = BuzzerAlerter(BUZZER_PIN)
    
    # GSM/GPS disabled during initial tests unless fully wired.
    # gps = GPSModule(GPS_PORT, BAUD_RATE)
    # gsm = GSMModule(GSM_PORT, BAUD_RATE)

    # Load calibration (falls back to defaults if no file exists)
    cal = CalibrationManager()
    cal_data = cal.load()
    step_up = cal_data["step_up_threshold"]
    step_down = cal_data["step_down_threshold"]
    print(f"[Thresholds] Step-up: {step_up:.3f}m | Step-down: {step_down:.3f}m")

    current_alert_level = 0 # 0=none, 1=light, 2=moderate, 3=intense

    print("System active. Monitoring environments...")
    
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
            
            if drop_off or is_step:
                # Extreme danger or step/drop-off detected, immediate intense alert
                if current_alert_level != 3:
                    buzzer.intense_alert()
                    current_alert_level = 3
                    
            elif distance < DIST_INTENSE_ALERT:
                if current_alert_level != 3:
                    buzzer.intense_alert()
                    current_alert_level = 3
                    # Emergency protocol could go here:
                    # loc = gps.get_location()
                    # gsm.send_sms("+1234567890", f"SOS: User is blocked. Loc: {loc}")

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

            # Small delay to prevent CPU pegging
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down safely...")
    finally:
        sonar.close()
        ir.close()
        camera.close()
        buzzer.close()
        # gps.close()
        # gsm.close()

if __name__ == "__main__":
    main()
