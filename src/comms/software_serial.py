import time


class SoftwareSerial:
    """Minimal serial-like interface using pigpio bit-banged UART on GPIO pins."""

    def __init__(self, rx_pin, tx_pin, baud_rate=9600, timeout=1.0):
        import pigpio

        self._pigpio = pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon (pigpiod).")

        self.rx_pin = int(rx_pin)
        self.tx_pin = int(tx_pin)
        self.baud_rate = int(baud_rate)
        self.timeout = float(timeout)
        self._rx_buffer = bytearray()
        self._rx_open = False

        # Reset any stale bit-bang reader state before opening.
        # pigpio raises if there is nothing to close; that's fine here.
        try:
            self.pi.bb_serial_read_close(self.rx_pin)
        except pigpio.error:
            pass
        status = self.pi.bb_serial_read_open(self.rx_pin, self.baud_rate, 8)
        if status != 0:
            self.pi.stop()
            raise RuntimeError(
                f"Failed to open software serial RX on GPIO {self.rx_pin} (status={status})."
            )
        self._rx_open = True

        # UART idle line should be high.
        self.pi.set_mode(self.tx_pin, pigpio.OUTPUT)
        self.pi.write(self.tx_pin, 1)

    def _drain_rx(self):
        if not self._rx_open:
            return
        count, data = self.pi.bb_serial_read(self.rx_pin)
        if count > 0 and data:
            self._rx_buffer.extend(data)

    def reset_input_buffer(self):
        self._rx_buffer.clear()
        # Drain any queued bytes in pigpio.
        while True:
            count, _ = self.pi.bb_serial_read(self.rx_pin)
            if count <= 0:
                break

    def reset_output_buffer(self):
        # No persistent output queue in this implementation.
        return

    def write(self, payload):
        if isinstance(payload, str):
            payload = payload.encode("ascii")
        if not payload:
            return 0

        self.pi.wave_clear()
        self.pi.wave_add_serial(self.tx_pin, self.baud_rate, payload)
        wave_id = self.pi.wave_create()
        if wave_id < 0:
            raise RuntimeError(f"Failed creating serial TX wave (id={wave_id}).")

        self.pi.wave_send_once(wave_id)
        deadline = time.monotonic() + max(self.timeout, 1.0)
        try:
            while self.pi.wave_tx_busy():
                if time.monotonic() > deadline:
                    raise TimeoutError("Software serial TX timed out.")
                time.sleep(0.001)
        finally:
            self.pi.wave_delete(wave_id)

        return len(payload)

    def read_all(self):
        self._drain_rx()
        if not self._rx_buffer:
            return b""
        output = bytes(self._rx_buffer)
        self._rx_buffer.clear()
        return output

    def readline(self):
        deadline = time.monotonic() + self.timeout
        while True:
            self._drain_rx()
            newline_idx = self._rx_buffer.find(b"\n")
            if newline_idx != -1:
                chunk = bytes(self._rx_buffer[: newline_idx + 1])
                del self._rx_buffer[: newline_idx + 1]
                return chunk

            if time.monotonic() >= deadline:
                if self._rx_buffer:
                    chunk = bytes(self._rx_buffer)
                    self._rx_buffer.clear()
                    return chunk
                return b""
            time.sleep(0.01)

    def close(self):
        try:
            if self._rx_open:
                self.pi.bb_serial_read_close(self.rx_pin)
                self._rx_open = False
        finally:
            self.pi.wave_tx_stop()
            self.pi.stop()
