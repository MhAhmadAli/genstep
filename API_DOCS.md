# GenStep Mobile API Docs

This document describes the API your frontend (including AI-assisted clients) can use.

## Base URL

- Local app server: `http://<PI_IP>:5000`
- Via Nginx reverse proxy (recommended): `http://<PI_IP>`

All endpoints below work on either base URL.

## Authentication

- None currently (local network API).

## Content Type

- Requests: no body for current endpoints
- Responses: `application/json`

---

## `GET /`

Basic API discovery endpoint.

### Response

```json
{
  "service": "GenStep Mobile API",
  "endpoints": [
    "/health",
    "/api/telemetry",
    "/api/actions/find-stick",
    "/api/actions/play-sound",
    "/api/actions/rest-mode/start",
    "/api/actions/rest-mode/stop"
  ]
}
```

---

## `GET /health`

Service health/readiness endpoint.

### Response

```json
{
  "status": "ok",
  "updated_at_unix": 1776306109.2659397
}
```

### Notes

- `updated_at_unix` is `null` until first telemetry update.
- Use this for liveness checks and reconnect logic.

---

## `GET /api/telemetry`

Main runtime state endpoint for frontend UI and AI logic.

### Response Schema

```json
{
  "updated_at_unix": "number|null",
  "status": "string",
  "rest_mode_enabled": "boolean",
  "obstacle_distance_m": "number|null",
  "ground_distance_m": "number|null",
  "drop_off": "boolean",
  "is_step": "boolean",
  "intense_condition": "boolean",
  "alert_level": "0|1|2|3",
  "camera_enabled": "boolean",
  "camera_hazards": {
    "stairs_detected": "boolean",
    "general_hazard_detected": "boolean",
    "labels": ["string"]
  },
  "camera_detections": [
    {
      "source": "stairs_model|general_model",
      "label": "string",
      "confidence": "number",
      "bbox": ["number", "number", "number", "number"]
    }
  ],
  "sos": {
    "last_attempt_unix": "number|null",
    "last_sent_unix": "number|null",
    "last_trigger_reason": "manual|blocked|null",
    "last_result": "attempting|sent|failed|skipped|null",
    "last_error": "string|null"
  }
}
```

### Example Response

```json
{
  "updated_at_unix": 1776306128.441,
  "status": "running",
  "rest_mode_enabled": false,
  "obstacle_distance_m": 1.22,
  "ground_distance_m": 0.31,
  "drop_off": false,
  "is_step": false,
  "intense_condition": false,
  "alert_level": 1,
  "camera_enabled": true,
  "camera_hazards": {
    "stairs_detected": false,
    "general_hazard_detected": true,
    "labels": ["person"]
  },
  "camera_detections": [
    {
      "source": "general_model",
      "label": "person",
      "confidence": 0.87,
      "bbox": [315.2, 130.8, 502.6, 697.4]
    }
  ],
  "sos": {
    "last_attempt_unix": 1776306000.1,
    "last_sent_unix": 1776306000.9,
    "last_trigger_reason": "manual",
    "last_result": "sent",
    "last_error": null
  }
}
```

### Field Semantics

- `alert_level`
  - `0`: no alert
  - `1`: light
  - `2`: moderate
  - `3`: intense
- `rest_mode_enabled`
  - `true` means all buzzer output is suppressed, including action APIs.
- `intense_condition`
  - `true` when severe hazard conditions are active (sonar/IR/camera risk logic).
- `camera_hazards.stairs_detected`
  - Triggered by your custom stairs model.
- `camera_hazards.general_hazard_detected`
  - Triggered by YOLOv11 detections matching configured hazard classes.
- `camera_detections`
  - Latest normalized detections (source, label, confidence, bbox).

---

## `POST /api/actions/find-stick`

Trigger the stick's predefined "find me" buzzer pattern.

### Request

- No request body

### Success Response (GPS fix available)

```json
{
  "ok": true,
  "action": "find_stick",
  "message": "Find stick started",
  "location": {
    "lat": 24.8607,
    "lng": 67.0011,
    "accuracy_m": 8.5,
    "timestamp_unix": 1776312345.12
  }
}
```

### Success Response (no GPS fix yet)

```json
{
  "ok": true,
  "action": "find_stick",
  "message": "Find stick started; GPS fix not available yet",
  "location": null
}
```

### Failure Response

```json
{
  "ok": false,
  "message": "<reason>"
}
```

---

## `POST /api/actions/play-sound`

Play one short predefined buzzer beep.

### Request

- No request body

### Success Response

```json
{
  "ok": true,
  "action": "play_sound",
  "message": "Buzzer beep played"
}
```

### Failure Response

```json
{
  "ok": false,
  "message": "<reason>"
}
```

---

## `POST /api/actions/rest-mode/start`

Enable rest mode. While active, buzzer output is disabled until rest mode is stopped.

### Request

- No request body

### Success Response

```json
{
  "ok": true,
  "action": "rest_mode_start",
  "message": "Rest mode enabled; buzzer is disabled",
  "rest_mode_enabled": true
}
```

### Failure Response

```json
{
  "ok": false,
  "message": "<reason>"
}
```

---

## `POST /api/actions/rest-mode/stop`

Disable rest mode and allow buzzer behavior again.

### Request

- No request body

### Success Response

```json
{
  "ok": true,
  "action": "rest_mode_stop",
  "message": "Rest mode disabled; buzzer resumed",
  "rest_mode_enabled": false
}
```

### Failure Response

```json
{
  "ok": false,
  "message": "<reason>"
}
```

---

## Frontend Polling Guidance

- Recommended polling interval: `250ms` to `1000ms` depending on UI.
- Backoff on errors:
  - Start at `1s`, backoff to `5s`, recover to normal on next success.
- Consider stale-data detection:
  - If `Date.now()/1000 - updated_at_unix > 3`, treat telemetry as stale.

---

## cURL Quick Tests

```bash
curl http://<PI_IP>/health
curl http://<PI_IP>/api/telemetry
curl -X POST http://<PI_IP>/api/actions/find-stick
curl -X POST http://<PI_IP>/api/actions/play-sound
curl -X POST http://<PI_IP>/api/actions/rest-mode/start
curl -X POST http://<PI_IP>/api/actions/rest-mode/stop
```

---

## Versioning

No explicit API versioning yet.

If the API evolves, recommended next step is path versioning (for example `/api/v1/telemetry`).
