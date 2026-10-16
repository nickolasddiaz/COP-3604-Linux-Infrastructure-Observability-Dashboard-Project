#!/usr/bin/env bash
# setup_firewall.sh
# Limits access to the receiver/API port (8080) to a single authorized IP address.

set -euo pipefail

AUTHORIZED_IP="${1:-}"
PORT="${2:-8080}"

if [[ -z "$AUTHORIZED_IP" ]]; then
    echo "Usage: sudo $0 <ALLOWED_IP_ADDRESS> [PORT]"
    echo "Example: sudo $0 34.73.112.90 8080"
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "Error: Run this script with sudo."
    exit 1
fi

echo "[*] Locking down TCP port ${PORT} to single IP: ${AUTHORIZED_IP}..."

# 1. Allow localhost traffic (for local testing and local collector processes)
iptables -C INPUT -i lo -j ACCEPT 2>/dev/null || iptables -A INPUT -i lo -j ACCEPT

# 2. Allow established/related connections and SSH (Port 22) so you don't lock out GCP SSH
iptables -C INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
    iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -C INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || \
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 3. Clean up any prior rules on PORT to avoid duplicate entries
iptables -D INPUT -p tcp -s "$AUTHORIZED_IP" --dport "$PORT" -j ACCEPT 2>/dev/null || true
iptables -D INPUT -p tcp --dport "$PORT" -j DROP 2>/dev/null || true

# 4. Allow strictly the single authorized IP on PORT (8080) and drop all others
iptables -A INPUT -p tcp -s "$AUTHORIZED_IP" --dport "$PORT" -j ACCEPT
iptables -A INPUT -p tcp --dport "$PORT" -j DROP

echo "[+] Active iptables rules for port ${PORT}:"
iptables -L INPUT -v -n | grep "$PORT"

# Optional GCP VPC Firewall equivalent (run in GCP Cloud Shell if restricting via VPC):
# gcloud compute firewall-rules create allow-observability-single-ip \
#     --network=default \
#     --action=ALLOW \
#     --direction=INGRESS \
#     --rules="tcp:${PORT}" \
#     --source-ranges="${AUTHORIZED_IP}/32"