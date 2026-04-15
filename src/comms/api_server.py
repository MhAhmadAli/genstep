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
        self._state = {
            "updated_at_unix": None,
            "status": "starting",
            "obstacle_distance_m": None,
            "ground_distance_m": None,
            "drop_off": False,
            "is_step": False,
            "intense_condition": False,
            "alert_level": 0,
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
                    "endpoints": ["/health", "/api/telemetry"],
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

    def get_state(self):
        with self._lock:
            return deepcopy(self._state)
