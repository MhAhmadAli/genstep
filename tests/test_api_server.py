import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from comms.api_server import MobileAPIServer


class TestMobileAPIServer(unittest.TestCase):
    def test_health_and_telemetry_endpoints(self):
        api = MobileAPIServer()
        api.update_state(
            status="running",
            rest_mode_enabled=False,
            obstacle_distance_m=1.2,
            alert_level=2,
            camera_enabled=True,
            camera_hazards={
                "stairs_detected": True,
                "general_hazard_detected": False,
                "labels": ["stairs"],
            },
            camera_detections=[
                {
                    "source": "stairs_model",
                    "label": "stairs",
                    "confidence": 0.88,
                    "bbox": [1.0, 2.0, 3.0, 4.0],
                }
            ],
        )
        api.update_sos(last_result="sent", last_trigger_reason="manual")

        client = api.app.test_client()

        health_response = client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.get_json()["status"], "ok")

        telemetry_response = client.get("/api/telemetry")
        self.assertEqual(telemetry_response.status_code, 200)
        payload = telemetry_response.get_json()
        self.assertEqual(payload["status"], "running")
        self.assertFalse(payload["rest_mode_enabled"])
        self.assertAlmostEqual(payload["obstacle_distance_m"], 1.2)
        self.assertEqual(payload["alert_level"], 2)
        self.assertTrue(payload["camera_enabled"])
        self.assertTrue(payload["camera_hazards"]["stairs_detected"])
        self.assertEqual(payload["camera_detections"][0]["label"], "stairs")
        self.assertEqual(payload["sos"]["last_result"], "sent")
        self.assertEqual(payload["sos"]["last_trigger_reason"], "manual")

    def test_action_endpoints_success(self):
        api = MobileAPIServer()
        api.set_action_handlers(
            find_stick_handler=lambda: {
                "message": "Find stick started",
                "location": {
                    "lat": 24.8607,
                    "lng": 67.0011,
                    "accuracy_m": 8.5,
                    "timestamp_unix": 1776312345.12,
                },
            },
            play_sound_handler=lambda: {"message": "Buzzer beep played"},
        )
        client = api.app.test_client()

        find_response = client.post("/api/actions/find-stick")
        self.assertEqual(find_response.status_code, 200)
        find_payload = find_response.get_json()
        self.assertTrue(find_payload["ok"])
        self.assertEqual(find_payload["action"], "find_stick")
        self.assertEqual(find_payload["message"], "Find stick started")
        self.assertAlmostEqual(find_payload["location"]["lat"], 24.8607)

        sound_response = client.post("/api/actions/play-sound")
        self.assertEqual(sound_response.status_code, 200)
        sound_payload = sound_response.get_json()
        self.assertTrue(sound_payload["ok"])
        self.assertEqual(sound_payload["action"], "play_sound")
        self.assertEqual(sound_payload["message"], "Buzzer beep played")

    def test_find_stick_without_gps_fix(self):
        api = MobileAPIServer()
        api.set_action_handlers(
            find_stick_handler=lambda: {
                "message": "Find stick started; GPS fix not available yet",
                "location": None,
            },
            play_sound_handler=lambda: {"message": "Buzzer beep played"},
        )
        client = api.app.test_client()

        response = client.post("/api/actions/find-stick")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["location"])
        self.assertIn("GPS fix not available yet", payload["message"])

    def test_action_endpoints_failure_shape(self):
        api = MobileAPIServer()
        api.set_action_handlers(
            find_stick_handler=lambda: (_ for _ in ()).throw(RuntimeError("find failed")),
            play_sound_handler=lambda: (_ for _ in ()).throw(RuntimeError("beep failed")),
        )
        client = api.app.test_client()

        find_response = client.post("/api/actions/find-stick")
        self.assertEqual(find_response.status_code, 500)
        self.assertFalse(find_response.get_json()["ok"])
        self.assertEqual(find_response.get_json()["message"], "find failed")

        sound_response = client.post("/api/actions/play-sound")
        self.assertEqual(sound_response.status_code, 500)
        self.assertFalse(sound_response.get_json()["ok"])
        self.assertEqual(sound_response.get_json()["message"], "beep failed")

    def test_action_endpoints_handler_rejects(self):
        api = MobileAPIServer()
        api.set_action_handlers(
            find_stick_handler=lambda: {
                "ok": False,
                "message": "Buzzer cooldown active. Try again in 9.9s",
            },
            play_sound_handler=lambda: {
                "ok": False,
                "message": "Buzzer cooldown active. Try again in 9.7s",
            },
        )
        client = api.app.test_client()

        find_response = client.post("/api/actions/find-stick")
        self.assertEqual(find_response.status_code, 429)
        find_payload = find_response.get_json()
        self.assertFalse(find_payload["ok"])
        self.assertIn("cooldown", find_payload["message"])

        sound_response = client.post("/api/actions/play-sound")
        self.assertEqual(sound_response.status_code, 429)
        sound_payload = sound_response.get_json()
        self.assertFalse(sound_payload["ok"])
        self.assertIn("cooldown", sound_payload["message"])

    def test_rest_mode_endpoints(self):
        api = MobileAPIServer()
        client = api.app.test_client()

        start_response = client.post("/api/actions/rest-mode/start")
        self.assertEqual(start_response.status_code, 200)
        start_payload = start_response.get_json()
        self.assertTrue(start_payload["ok"])
        self.assertTrue(start_payload["rest_mode_enabled"])
        self.assertTrue(api.is_rest_mode_enabled())

        telemetry_response = client.get("/api/telemetry")
        self.assertEqual(telemetry_response.status_code, 200)
        self.assertTrue(telemetry_response.get_json()["rest_mode_enabled"])

        stop_response = client.post("/api/actions/rest-mode/stop")
        self.assertEqual(stop_response.status_code, 200)
        stop_payload = stop_response.get_json()
        self.assertTrue(stop_payload["ok"])
        self.assertFalse(stop_payload["rest_mode_enabled"])
        self.assertFalse(api.is_rest_mode_enabled())


if __name__ == "__main__":
    unittest.main()
