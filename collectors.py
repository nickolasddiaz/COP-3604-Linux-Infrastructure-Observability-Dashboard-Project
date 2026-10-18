#!/usr/bin/env python3
import os
import psutil
import requests
from getmac import get_mac_address as gma
import psutil
import argparse

from metrics import Metrics


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Metrics Collection")
    parser.add_argument (
        "--ip",
        dest="ip_address",
        required=True,
        help="Target IP address (http://127.0.0.1:8080)"
    )
    args = parser.parse_args()

    if args is None:
        raise ValueError("Arguements do not exist")
    return parser.parse_args()


def get_cpu_use() -> float:
    """ Percent of utilization """
    return float(psutil.cpu_percent(interval=0.5))

def get_memory_use() -> float:
    """ Percent of utilization """
    return float(psutil.virtual_memory().percent)

def get_storage_use(mount_point: str = "/") -> float:
    """ Percent of utilization """
    return float(psutil.disk_usage(mount_point).percent)

def get_network_use() -> float:
    """ Total network use in Megabytes """
    net = psutil.net_io_counters()
    total_bytes = net.bytes_sent + net.bytes_recv
    return round(total_bytes / (1024 * 1024), 2)

def get_load() -> float:
    """ Load average of system over 1 minute """
    if hasattr(os, "getloadavg"):
        return round(os.getloadavg()[0], 2) # type: ignore
    return round(psutil.cpu_percent(interval=0.1) / 100.0 * (psutil.cpu_count() or 1), 2)

def get_metrics() -> dict[str, float]:
    """Gets a dictionary of the metrics.

        Returns: dict[str, float]: 
    """
    return {
        Metrics.CPU: get_cpu_use(),
        Metrics.MEMORY: get_memory_use(),
        Metrics.STORAGE: get_storage_use(),
        Metrics.NETWORK: get_network_use(),
        Metrics.LOAD: get_load(),
    }

def get_mac_address() -> str:
    # To-do get mac address
    mac = gma()
    if mac is None:
        raise LookupError("Mac-Address cannot be retreived")
    return mac

def send_to_server(mac_address: str, payload: dict, SERVER_URL: str) -> None:
    """Triggers a POST request to deliver a JSON payload to the server."""

    body = {
        "mac_address": mac_address,
        "content": payload
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "curl/7.68.0"  # or 'Mozilla/5.0'
    }

    if not SERVER_URL.endswith('/'):
        SERVER_URL += '/'

    response = requests.post(SERVER_URL, json=body, headers=headers)
    
    if response.status_code == 200:
        print("\nData sent: Response code 200")
    else:
        print(f"Failed to send data: {response.status_code} - {response.text}")


if __name__ == "__main__":    
    args = parse_arguments()
    payload = get_metrics()
    mac_address = get_mac_address()
    send_to_server(mac_address, payload, args.ip_address)
