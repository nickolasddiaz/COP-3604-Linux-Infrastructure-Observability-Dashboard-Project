#!/usr/bin/env bash
# stress_load.sh
# Alternately generates high server loads across 5 stress-ng classes and varying intervals.

set -uo pipefail

if ! command -v stress-ng >/dev/null 2>&1; then
    echo "Error: stress-ng is not installed. Install with: sudo apt update && sudo apt install -y stress-ng"
    exit 1
fi

ping_watchdog() {
    if [[ -n "${WATCHDOG_USEC:-}" ]] && command -v systemd-notify >/dev/null 2>&1; then
        systemd-notify WATCHDOG=1
    fi
}

echo "[*] Starting alternating stress-ng load generator..."

while true; do
    # 1. CPU Class — Spikes Metrics.CPU & Metrics.LOAD (20 seconds)
    ping_watchdog
    echo "[$(date '+%T')] Class 1/5 (CPU): 2 workers @ 85% load for 20s"
    stress-ng --cpu 2 --cpu-load 85 --timeout 20s --metrics-brief
    sleep 8

    # 2. Memory (VM) Class — Spikes Metrics.MEMORY (25 seconds)
    ping_watchdog
    echo "[$(date '+%T')] Class 2/5 (MEMORY): 2 VM workers allocating 75% RAM for 25s"
    stress-ng --vm 2 --vm-bytes 75% --timeout 25s --metrics-brief
    sleep 8

    # 3. Filesystem / Storage (HDD) Class — Spikes Metrics.STORAGE (30 seconds)
    ping_watchdog
    echo "[$(date '+%T')] Class 3/5 (FILESYSTEM): Writing/unlinking 1GB temp files for 30s"
    stress-ng --hdd 2 --hdd-bytes 1G --timeout 30s --metrics-brief
    sleep 10

    # 4. Block I/O Class — Spikes I/O wait and Metrics.LOAD (15 seconds)
    ping_watchdog
    echo "[$(date '+%T')] Class 4/5 (IO): 4 I/O sync workers for 15s"
    stress-ng --io 4 --timeout 15s --metrics-brief
    sleep 8

    # 5. Context Switch / Socket Class — Spikes OS scheduler & loopback activity (18 seconds)
    ping_watchdog
    echo "[$(date '+%T')] Class 5/5 (SWITCH): 4 context-switching workers for 18s"
    stress-ng --switch 4 --timeout 18s --metrics-brief
    sleep 12
done