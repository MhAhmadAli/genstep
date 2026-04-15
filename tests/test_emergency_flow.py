import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from comms.emergency import format_sos_message, should_send_sos


class TestEmergencyFlow(unittest.TestCase):
    def test_blocked_condition_triggers_when_rate_limit_elapsed(self):
        self.assertTrue(
            should_send_sos(
                intense_condition=True,
                manual_trigger=False,
                now_ts=120.0,
                last_sent_ts=0.0,
                rate_limit_seconds=60,
            )
        )

    def test_manual_trigger_sends_even_without_blocked_condition(self):
        self.assertTrue(
            should_send_sos(
                intense_condition=False,
                manual_trigger=True,
                now_ts=120.0,
                last_sent_ts=0.0,
                rate_limit_seconds=60,
            )
        )

    def test_rate_limit_blocks_repeated_send(self):
        self.assertFalse(
            should_send_sos(
                intense_condition=True,
                manual_trigger=False,
                now_ts=20.0,
                last_sent_ts=0.0,
                rate_limit_seconds=60,
            )
        )

    def test_message_uses_gps_fallback_when_location_missing(self):
        message = format_sos_message("blocked", None)
        self.assertIn("GPS fix unavailable", message)


if __name__ == "__main__":
    unittest.main()
