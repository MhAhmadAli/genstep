def should_send_sos(intense_condition, manual_trigger, now_ts, last_sent_ts, rate_limit_seconds):
    """Return True when a trigger is active and rate limit allows dispatch."""
    if not intense_condition and not manual_trigger:
        return False
    return (now_ts - last_sent_ts) >= rate_limit_seconds


def format_sos_message(trigger_reason, location):
    """Build a user-readable SOS payload with optional GPS coordinates."""
    message = f"SOS: GenStep emergency trigger ({trigger_reason})."
    if location:
        message += (
            f" Lat: {location['latitude']:.6f},"
            f" Lon: {location['longitude']:.6f}"
        )
        if location.get("utc"):
            message += f", UTC: {location['utc']}"
    else:
        message += " GPS fix unavailable."
    return message
