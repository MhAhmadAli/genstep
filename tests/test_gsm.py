import serial
import time

# Update with your device's correct serial port
GSM_PORT = "/dev/serial0" 
BAUD_RATE = 9600

def test_gsm():
    print(f"Testing GSM on {GSM_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(GSM_PORT, BAUD_RATE, timeout=2)
        print("Serial port opened successfully. Sending 'AT' command...")
        
        # Send AT command
        ser.write(b"AT\r\n")
        time.sleep(1)
        
        response = ser.read_all().decode('ascii', errors='ignore')
        print(f"Response: {response}")
        
        if "OK" in response:
            print("GSM Test Passed: Module is responding.")
        else:
            print("GSM Test Warning: Module did not respond with 'OK'.")
            
        ser.close()
    except Exception as e:
        print(f"Failed to open or read from GSM serial port: {e}")

if __name__ == "__main__":
    test_gsm()
