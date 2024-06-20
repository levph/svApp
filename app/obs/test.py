"""
network battery levels script V0.000001

1.change radio_ip to the connected radio's IP
2.run the script

will print each device's IP and battery level

"""

import requests

# Replace with the actual IP address of your StreamCaster radio
subnet = '172.20.' # subnet of radio network
radio_ip = '172.20.238.213' # IP of connected radio
api_endpoint = f'http://{radio_ip}/streamscape_api'


# Function to send command to radio
def send_command(method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": "1"
    }
    response = requests.post(api_endpoint, json=payload)
    return response.json()


def send_command_ip(method, ip, params=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": "1"
    }
    api_endpoint_tmp = f'http://{ip}/streamscape_api'
    response = requests.post(api_endpoint_tmp, json=payload)
    return response.json()


# TODO: make more generic (not only 255.255.0.0)
def id_2_ip(id_list):
    last_bytes = [(node // 256, node % 256) for node in id_list]
    iips = [subnet + str(b[0]) + "." + str(b[1]) for b in last_bytes]
    return iips


# Example: Get network status
network_status = send_command("network_status")

# get ids of all nodes in the network
network_ids = list(set([int(iid) for ii, iid in enumerate(network_status['result']) if (ii + 1) % 3 != 0]))

# translate ids of all the nodes to ip
ips = id_2_ip(network_ids)

# print battery percentage for each
for radio_ip in ips:
    battery_percentage = send_command_ip("battery_percent", radio_ip)

    print(f'Radio IP: {radio_ip}, Battery: {battery_percentage["result"][0]}')

