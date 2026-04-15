import serial
import time


class GSMModule:
    """Sends SMS via AT commands with retry and error tracking."""

    def __init__(self, port, baud_rate=9600, timeout=1, init_retries=2):
        self.serial = None
        self.last_error = None
        self.last_response = ""

        for attempt in range(max(1, int(init_retries))):
            try:
                self.serial = serial.Serial(port, baud_rate, timeout=timeout)
                # Give modem time to boot and flush startup noise.
                time.sleep(1)
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                ready, _ = self._send_at_command("AT", expected_response="OK", wait_time=0.5)
                if ready:
                    return
                self.last_error = "GSM modem did not respond to AT."
                self.close()
            except Exception as exc:
                self.last_error = f"Failed to initialize GSM: {exc}"
                print(self.last_error)
                self.serial = None

            if attempt < max(1, int(init_retries)) - 1:
                time.sleep(1)

    def _send_at_command(self, command, expected_response="OK", wait_time=1):
        if not self.serial:
            self.last_error = "GSM serial connection is unavailable."
            return False, ""

        try:
            self.serial.reset_input_buffer()
            self.serial.write((command + "\r\n").encode("ascii"))
            time.sleep(wait_time)
            response = self.serial.read_all().decode("ascii", errors="ignore")
            self.last_response = response
            if expected_response in response:
                self.last_error = None
                return True, response
            self.last_error = f"AT command failed: {command}. Response: {response.strip()}"
            return False, response
        except Exception as exc:
            self.last_error = f"AT command exception ({command}): {exc}"
            self.last_response = ""
            return False, ""

    def send_sms(self, phone_number, message, retry_attempts=2):
        """Sends an SMS to the specified number."""
        if not self.serial:
            self.last_error = "GSM serial connection is unavailable."
            return False

        for attempt in range(max(1, int(retry_attempts))):
            ready, _ = self._send_at_command("AT", expected_response="OK", wait_time=0.5)
            if not ready:
                if attempt < max(1, int(retry_attempts)) - 1:
                    time.sleep(1)
                    continue
                return False

            text_mode_set, _ = self._send_at_command("AT+CMGF=1", expected_response="OK", wait_time=0.5)
            if not text_mode_set:
                if attempt < max(1, int(retry_attempts)) - 1:
                    time.sleep(1)
                    continue
                return False

            try:
                self.serial.reset_input_buffer()
                self.serial.write((f'AT+CMGS="{phone_number}"\r\n').encode("ascii"))
                time.sleep(0.5)
                prompt = self.serial.read_all().decode("ascii", errors="ignore")
                if ">" not in prompt:
                    self.last_error = f"GSM did not provide SMS prompt. Response: {prompt.strip()}"
                    if attempt < max(1, int(retry_attempts)) - 1:
                        time.sleep(1)
                        continue
                    return False

                self.serial.write((message + chr(26)).encode("ascii"))
                time.sleep(3)
                response = self.serial.read_all().decode("ascii", errors="ignore")
                self.last_response = response
                if "+CMGS" in response and "ERROR" not in response:
                    self.last_error = None
                    return True

                self.last_error = f"SMS send failed. Response: {response.strip()}"
                if attempt < max(1, int(retry_attempts)) - 1:
                    time.sleep(1)
                    continue
                return False
            except Exception as exc:
                self.last_error = f"SMS send exception: {exc}"
                if attempt < max(1, int(retry_attempts)) - 1:
                    time.sleep(1)
                    continue
                return False

        return False

    def close(self):
        if self.serial:
            self.serial.close()
            self.serial = None
