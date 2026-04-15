# GenStep AI

An assistive walking stick powered by Raspberry Pi 4 that improves mobility, independence, and safety for visually impaired users through real-time environment sensing, audio feedback, and emergency communication.

## Features

- **Obstacle Detection** — 3 ultrasonic sensors (2 front-facing, 1 downward) detect barriers within 3 meters.
- **Step/Drop-off Detection** — Downward sonar + 2 IR sensors detect stairs and elevation changes.
- **Adaptive Feedback** — Buzzer with 3 intensity levels (light → moderate → intense) based on proximity.
- **GPS Tracking** — Real-time location via GPS module over UART.
- **Emergency SOS** — SMS alerts via GSM module with AT commands.
- **Camera + AI** — Camera feed ready for AI-based object recognition (stairs, people, vehicles).
- **Sensor Calibration** — Automatic calibration with persistent JSON storage.

## Hardware

| Component         | GPIO Pins          |
|-------------------|--------------------|
| Sonar 1 (Ground)  | Trig 24, Echo 23   |
| Sonar 2 (Front)   | Trig 18, Echo 25   |
| Sonar 3 (Front)   | Trig 13, Echo 19   |
| IR Sensor 1       | GPIO 6             |
| IR Sensor 2       | GPIO 5             |
| Buzzer            | GPIO 8             |
| GSM Module        | TX → GPIO 2, RX → GPIO 3 |
| GPS Module        | TX → GPIO 14, RX → GPIO 15 |
| Camera            | CSI / USB          |

## Project Structure

```
genstep/
├── src/
│   ├── config.py               # Pin mappings & thresholds
│   ├── main.py                 # Core application loop
│   ├── calibration.py          # Sensor calibration manager
│   ├── calibrate_cli.py        # CLI calibration tool
│   ├── sensors/
│   │   ├── ultrasonic.py       # Ultrasonic sensor array
│   │   ├── ir.py               # IR drop-off detection
│   │   └── camera.py           # Camera feed for AI
│   ├── feedback/
│   │   └── alerter.py          # Buzzer alert patterns
│   └── comms/
│       ├── gps.py              # GPS NMEA parsing
│       └── gsm.py              # GSM SMS via AT commands
├── tests/                      # Individual hardware & unit tests
├── data/                       # Auto-generated calibration data
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites
- Raspberry Pi 4 with Raspbian OS
- Python 3.7+
- pigpio daemon running (`sudo systemctl enable pigpiod && sudo systemctl start pigpiod`)

## Deployment

To deploy the latest code to your Raspberry Pi:

1.  **Ensure SSH is enabled** on your Pi.
2.  **Run the deployment script** from your local machine:
    ```bash
    ./scripts/deploy.sh [SSH_HOST]
    ```
    *Example:* `./scripts/deploy.sh` (defaults to `genstep`) or `./scripts/deploy.sh 192.168.1.100`

This script will:
1.  Zip the current project (respecting uncommitted changes but excluding `venv`, `.git`, etc.).
2.  `scp` the zip to the Pi host.
3.  Automatically `unzip` it to `~/genstep`.
4.  **Create a virtual environment (`venv`)** on the Pi (if it doesn't exist).
5.  Run `pip install` within that venv to update dependencies safely.

### Install Dependencies
```bash
pip3 install -r requirements.txt
```

### UART Mapping Checks (Raspberry Pi)
- Verify enabled UART devices before running comms features:
  ```bash
  ls -l /dev/serial*
  ```
- Update `src/config.py` if your Pi exposes GSM/GPS on different device names (`/dev/ttyS0` or `/dev/ttyAMA0`).
- Ensure your user has serial access permissions (or run via a service account configured for serial devices).

## Usage

### Run the Main Application
```bash
python3 src/main.py
```

Before running, set these values in `src/config.py`:
- `ENABLE_GPS` and `ENABLE_GSM` to enable/disable each module independently.
- `EMERGENCY_PHONE_NUMBER` for SMS destination.
- `SOS_RATE_LIMIT_SECONDS` to avoid repeated emergency SMS spam.
- `GPS_READ_RETRIES`, `GPS_SERIAL_TIMEOUT_SECONDS` for GPS reliability tuning.
- `ENABLE_MANUAL_SOS_STDIN` and `MANUAL_SOS_COMMAND` for manual SOS from terminal.

Manual SOS trigger:
- While `src/main.py` is running in a terminal, type `sos` then press Enter to send an emergency SMS (rate-limited).

### Calibrate Sensors
Hold the stick naturally on flat ground and run:
```bash
python3 src/calibrate_cli.py              # Default 5-second calibration
python3 src/calibrate_cli.py --time 10    # Custom duration
python3 src/calibrate_cli.py --show       # View stored calibration
```

### Test Individual Components
```bash
python3 tests/test_ultrasonic_1.py    # Test ground sonar
python3 tests/test_ultrasonic_2.py    # Test front sonar
python3 tests/test_ir.py              # Test IR sensors
python3 tests/test_buzzer.py          # Test buzzer
python3 tests/test_camera.py          # Test camera
python3 tests/test_gps.py             # Test GPS module
python3 tests/test_gsm.py             # Test GSM module
```

### Run Unit Tests
```bash
python3 -m unittest tests/test_calibration.py tests/test_gps.py tests/test_gsm.py tests/test_emergency_flow.py -v
```

## Emergency SMS Payload
- Trigger reasons:
  - automatic blocked/severe condition
  - manual terminal trigger (`sos`)
- Message includes parsed GPS coordinates when fix is available:
  - `Lat`, `Lon`, optional `UTC`
- If GPS has no valid fix, message includes `GPS fix unavailable`.

## GPS/GSM Troubleshooting
- **No GPS fix**: test outdoors with clear sky view, increase `GPS_READ_RETRIES`.
- **GSM AT failures**: verify SIM/network readiness and power stability; inspect startup response with `tests/test_gsm.py`.
- **No SMS sent during alerts**: check `EMERGENCY_PHONE_NUMBER`, `ENABLE_GSM`, and rate limit (`SOS_RATE_LIMIT_SECONDS`).
- **Wrong serial device**: run `ls -l /dev/serial*` and align `GPS_PORT`/`GSM_PORT` in `src/config.py`.

## Alert Thresholds

| Distance       | Feedback              |
|----------------|-----------------------|
| < 3.0 m        | Light beeping         |
| < 1.5 m        | Moderate beeping      |
| < 1.0 m        | Intense emergency     |
| Step detected   | Intense emergency     |
| IR drop-off     | Intense emergency     |

## License

MIT
