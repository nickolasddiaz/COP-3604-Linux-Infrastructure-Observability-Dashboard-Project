import requests

from metrics import Metrics

SERVER_URL = "http://127.0.0.1:8000"

def get_metrics() -> dict[str, float]:
    """Gets a dictionary of the metrics.

        Returns: dict[str, float]: 
    """

    # To-do add more metrics and create functions to get them
    return {
        Metrics.CPU: 90,
        Metrics.MEMORY: 1000,
        Metrics.STORAGE: 50,
    }

def get_mac_address() -> str:
    # To-do get mac address
    return "test_mac_address"

def send_to_server(mac_address: str, payload: dict) -> None:
    """Triggers a POST request to deliver a JSON payload to the server."""


    payload = {
        "mac_address": mac_address,
        "content": payload
    }

    response = requests.post(f"{SERVER_URL}/metrics", json=payload)
    
    if response.status_code == 200:
        print("\n--- [POST] Response From Server After Sending ---")
        print(response.json())
    else:
        print(f"Failed to send data: {response.status_code}")


if __name__ == "__main__":
    payload = get_metrics()
    mac_address = get_mac_address()
    send_to_server(mac_address, payload)