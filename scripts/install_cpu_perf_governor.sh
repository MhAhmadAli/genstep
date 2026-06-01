#!/usr/bin/env bash
set -euo pipefail

# Pins all CPU cores to the "performance" governor at boot so YOLO inference
# is not throttled by the default on-demand scaling on the Raspberry Pi.

SERVICE_NAME="cpu-perf-governor-genstep.service"
SOURCE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${SERVICE_NAME}"
TARGET_FILE="/etc/systemd/system/${SERVICE_NAME}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./scripts/install_cpu_perf_governor.sh"
  exit 1
fi

if [[ ! -f "${SOURCE_FILE}" ]]; then
  echo "Service template not found: ${SOURCE_FILE}"
  exit 1
fi

if [[ ! -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; then
  echo "cpufreq scaling is not available on this system; nothing to do."
  exit 1
fi

cp "${SOURCE_FILE}" "${TARGET_FILE}"
chmod 644 "${TARGET_FILE}"

systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" || true
systemctl enable --now "${SERVICE_NAME}"

echo "Installed and enabled ${SERVICE_NAME}."
echo "Current governors:"
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor || true
