import serial
import time

class GSMModule:
    """Sends SMS and handles calls via AT commands."""

    def __init__(self, port, baud_rate=9600):
        try:
            self.serial = serial.Serial(port, baud_rate, timeout=1)
            # Give it a moment to initialize
            time.sleep(1)
        except Exception as e:
            print(f"Failed to initialize GSM: {e}")
            self.serial = None

    def _send_at_command(self, command, expected_response="OK", wait_time=1):
        if not self.serial:
            return False
            
        self.serial.write((command + '\r\n').encode('ascii'))
        time.sleep(wait_time)
        response = self.serial.read_all().decode('ascii', errors='ignore')
        
        return expected_response in response

    def send_sms(self, phone_number, message):
        """Sends an SMS to the specified number."""
        if not self.serial:
            return False

        # Set text mode
        if not self._send_at_command("AT+CMGF=1"):
            return False

        # Set recipient
        self.serial.write((f'AT+CMGS="{phone_number}"\r\n').encode('ascii'))
        time.sleep(1)

        # Send message content and CTRL+Z (ASCII 26)
        self.serial.write((message + chr(26)).encode('ascii'))
        time.sleep(3) # Give it time to send
        
        response = self.serial.read_all().decode('ascii', errors='ignore')
        return "+CMGS" in response

    def close(self):
        if self.serial:
            self.serial.close()
