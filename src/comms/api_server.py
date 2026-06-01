import threading
import time
from copy import deepcopy

from flask import Flask, jsonify


class MobileAPIServer:
    """Exposes latest runtime telemetry for a mobile client."""

    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self._lock = threading.Lock()
        self._server_thread = None
        self._find_stick_handler = None
        self._play_sound_handler = None
        self._state = {
            "updated_at_unix": None,
            "status": "starting",
            "rest_mode_enabled": False,
            "obstacle_distance_m": None,
            "ground_distance_m": None,
            "drop_off": False,
            "is_step": False,
            "intense_condition": False,
            "alert_level": 0,
            "camera_enabled": False,
            "camera_hazards": {
                "stairs_detected": False,
                "general_hazard_detected": False,
                "labels": [],
            },
            "camera_detections": [],
            "sos": {
                "last_attempt_unix": None,
                "last_sent_unix": None,
                "last_trigger_reason": None,
                "last_result": None,
                "last_error": None,
            },
        }
        self.app = Flask(__name__)
        self._register_routes()

    def _register_routes(self):
        @self.app.get("/")
        def root():
            return jsonify(
                {
                    "service": "GenStep Mobile API",
                    "endpoints": [
                        "/health",
                        "/api/telemetry",
                        "/api/actions/find-stick",
                        "/api/actions/play-sound",
                        "/api/actions/rest-mode/start",
                        "/api/actions/rest-mode/stop",
                    ],
                }
            )

        @self.app.get("/health")
        def health():
            with self._lock:
                updated_at = self._state["updated_at_unix"]
            return jsonify(
                {
                    "status": "ok",
                    "updated_at_unix": updated_at,
                }
            )

        @self.app.get("/api/telemetry")
        def telemetry():
            return jsonify(self.get_state())

        @self.app.post("/api/actions/find-stick")
        def find_stick():
            if not self._find_stick_handler:
                return jsonify({"ok": False, "message": "Find stick action is unavailable."}), 503
            try:
                payload = {
                    "ok": True,
                    "action": "find_stick",
                    "message": "Find stick started",
                    "location": None,
                }
                result = self._find_stick_handler() or {}
                if isinstance(result, dict):
                    if result.get("ok") is False:
                        status_code = int(result.get("status_code", 429))
                        return jsonify(
                            {
                                "ok": False,
                                "message": result.get("message", "Find stick failed"),
                            }
                        ), status_code
                    if "message" in result and result["message"]:
                        payload["message"] = result["message"]
                    if "location" in result:
                        payload["location"] = result["location"]
                return jsonify(payload)
            except Exception as exc:
                return jsonify({"ok": False, "message": str(exc)}), 500

        @self.app.post("/api/actions/play-sound")
        def play_sound():
            if not self._play_sound_handler:
                return jsonify({"ok": False, "message": "Play sound action is unavailable."}), 503
            try:
                result = self._play_sound_handler() or {}
                if isinstance(result, dict) and result.get("ok") is False:
                    status_code = int(result.get("status_code", 429))
                    return jsonify(
                        {
                            "ok": False,
                            "message": result.get("message", "Play sound failed"),
                        }
                    ), status_code
                message = "Buzzer beep played"
                if isinstance(result, dict) and result.get("message"):
                    message = result["message"]
                return jsonify(
                    {
                        "ok": True,
                        "action": "play_sound",
                        "message": message,
                    }
                )
            except Exception as exc:
                return jsonify({"ok": False, "message": str(exc)}), 500

        @self.app.post("/api/actions/rest-mode/start")
        def rest_mode_start():
            self.set_rest_mode_enabled(True)
            return jsonify(
                {
                    "ok": True,
                    "action": "rest_mode_start",
                    "message": "Rest mode enabled; buzzer is disabled",
                    "rest_mode_enabled": True,
                }
            )

        @self.app.post("/api/actions/rest-mode/stop")
        def rest_mode_stop():
            self.set_rest_mode_enabled(False)
            return jsonify(
                {
                    "ok": True,
                    "action": "rest_mode_stop",
                    "message": "Rest mode disabled; buzzer resumed",
                    "rest_mode_enabled": False,
                }
            )

    def start(self):
        if self._server_thread and self._server_thread.is_alive():
            return

        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

    def _run_server(self):
        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    def update_state(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)
            self._state["updated_at_unix"] = time.time()

    def update_sos(self, **kwargs):
        with self._lock:
            self._state["sos"].update(kwargs)
            self._state["updated_at_unix"] = time.time()

    def set_action_handlers(self, find_stick_handler=None, play_sound_handler=None):
        self._find_stick_handler = find_stick_handler
        self._play_sound_handler = play_sound_handler

    def set_rest_mode_enabled(self, enabled):
        with self._lock:
            self._state["rest_mode_enabled"] = bool(enabled)
            self._state["updated_at_unix"] = time.time()

    def is_rest_mode_enabled(self):
        with self._lock:
            return bool(self._state["rest_mode_enabled"])

    def get_state(self):
        with self._lock:
            return deepcopy(self._state)
