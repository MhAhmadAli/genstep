import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from comms.api_server import MobileAPIServer


class TestMobileAPIServer(unittest.TestCase):
    def test_health_and_telemetry_endpoints(self):
        api = MobileAPIServer()
        api.update_state(status="running", obstacle_distance_m=1.2, alert_level=2)
        api.update_sos(last_result="sent", last_trigger_reason="manual")

        client = api.app.test_client()

        health_response = client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.get_json()["status"], "ok")

        telemetry_response = client.get("/api/telemetry")
        self.assertEqual(telemetry_response.status_code, 200)
        payload = telemetry_response.get_json()
        self.assertEqual(payload["status"], "running")
        self.assertAlmostEqual(payload["obstacle_distance_m"], 1.2)
        self.assertEqual(payload["alert_level"], 2)
        self.assertEqual(payload["sos"]["last_result"], "sent")
        self.assertEqual(payload["sos"]["last_trigger_reason"], "manual")


if __name__ == "__main__":
    unittest.main()
