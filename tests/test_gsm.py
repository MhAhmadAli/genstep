import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from comms.gsm import GSMModule


class TestGSMModule(unittest.TestCase):
    @staticmethod
    def _read_all_sequence(values):
        data = list(values)

        def _reader():
            if data:
                return data.pop(0)
            return b""

        return _reader

    @patch("comms.gsm.time.sleep", return_value=None)
    def test_send_sms_successful_command_flow(self, _sleep_patch):
        fake_serial = MagicMock()
        fake_serial.read_all.side_effect = self._read_all_sequence(
            [
                b"OK\r\n",  # init AT check
                b"OK\r\n",  # runtime AT check
                b"OK\r\n",  # AT+CMGF
                b"> ",  # AT+CMGS prompt
                b"+CMGS: 42\r\nOK\r\n",  # send confirmation
            ]
        )

        with patch("comms.gsm.serial.Serial", return_value=fake_serial):
            gsm = GSMModule("/dev/mock", 9600, timeout=1, init_retries=1)
            sent = gsm.send_sms("+10000000000", "SOS TEST", retry_attempts=1)

        self.assertTrue(sent)
        self.assertIsNone(gsm.last_error)

    @patch("comms.gsm.time.sleep", return_value=None)
    def test_send_sms_sets_error_when_prompt_missing(self, _sleep_patch):
        fake_serial = MagicMock()
        fake_serial.read_all.side_effect = self._read_all_sequence(
            [
                b"OK\r\n",  # init AT check
                b"OK\r\n",  # runtime AT check
                b"OK\r\n",  # AT+CMGF
                b"ERROR\r\n",  # AT+CMGS prompt missing
            ]
        )

        with patch("comms.gsm.serial.Serial", return_value=fake_serial):
            gsm = GSMModule("/dev/mock", 9600, timeout=1, init_retries=1)
            sent = gsm.send_sms("+10000000000", "SOS TEST", retry_attempts=1)

        self.assertFalse(sent)
        self.assertIn("SMS prompt", gsm.last_error)


if __name__ == "__main__":
    unittest.main()
