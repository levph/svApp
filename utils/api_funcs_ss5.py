"""
This file lists some of the API functions for Silvus app backend

File structure:
- send command ip
- send broadcast
...

functions to start:
- list devices
- save node labels
- report? understand how to
-
"""

import requests
import json


def send_command_ip(method, ip, params=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": "1"
    }
    api_endpoint = f'http://{ip}/streamscape_api'
    # TODO: add error handling as explain in API manual
    try:
        response = requests.post(api_endpoint, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()  # Return the content if successful
    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")


def test_routing_tree():
    ip = "172.20.238.213"
    ip2 = "172.20.241.202"
    route_tree = send_command_ip("routing_tree", ip=ip)

    connected_devices = send_command_ip("read_client_list", ip=ip2)

    