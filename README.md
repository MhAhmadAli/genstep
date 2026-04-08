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
4.  Run `pip3 install -r requirements.txt` on the Pi to update dependencies.

### Install Dependencies
```bash
pip3 install -r requirements.txt
```

## Usage

### Run the Main Application
```bash
python3 src/main.py
```

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
python3 -m unittest tests/test_calibration.py -v
```

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
