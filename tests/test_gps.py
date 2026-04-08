import serial
import time

# Update with your device's correct serial port
GPS_PORT = "/dev/serial1" 
BAUD_RATE = 9600

def test_gps():
    print(f"Testing GPS on {GPS_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(GPS_PORT, BAUD_RATE, timeout=2)
        print("Serial port opened successfully. Waiting for NMEA sentences...")
        
        # Read 5 lines
        for i in range(5):
            line = ser.readline().decode('ascii', errors='ignore').strip()
            print(f"Line {i+1}: {line}")
            time.sleep(0.1)
            
        ser.close()
        print("GPS Test Complete.")
    except Exception as e:
        print(f"Failed to open or read from GPS serial port: {e}")

if __name__ == "__main__":
    test_gps()
