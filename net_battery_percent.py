import requests

radio_ip = ""
api_endpoint = ""


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


def id_2_ip(id_list):
    last_bytes = [(node // 256, node % 256) for node in id_list]
    iips = ["172.20." + str(b[0]) + "." + str(b[1]) for b in last_bytes]
    return iips


def get_batteries(s_ip):
    global radio_ip, api_endpoint
    radio_ip = s_ip
    api_endpoint = f'http://{radio_ip}/streamscape_api'

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

