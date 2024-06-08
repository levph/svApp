import requests
import json


def set_single(radio_ip, f, bw, net_id, power):
    url = "http://" + str(radio_ip) + "/cgi-bin/streamscape_api"

    payload = json.dumps([
        {
            "jsonrpc": "2.0",
            "method": "nw_name",
            "id": 1,
            "params": [
                net_id
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "power_dBm",
            "id": 2,
            "params": [
                power
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "freq_bw",
            "id": 3,
            "params": [
                f,
                bw
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 4,
            "params": [
                "freq"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 5,
            "params": [
                "bw"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 6,
            "params": [
                "nw_name"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 7,
            "params": [
                "power_dBm"
            ]
        }
    ])
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text

def broadcast_net_stat(radio_ip,nodelist):
    url = f'http://{radio_ip}/bcast_enc.py'
    payload = f''

def send_broadcast(radio_ip, f, bw, net_id, power, nodelist):
    # url = "http://172.20.241.202/bcast_enc.py"

    url = f'http://{radio_ip}/bcast_enc.py'
    payload = f'{"apis":[{"method": "net_status"}],"nodeids":{nodelist}}'

    nw_name_value = net_id  # Variable you want to insert
    power_value = power  # Another variable
    freq_value = f
    bw_value = bw
    nodeids = nodelist  # List of node IDs

    # Constructing the payload using f-strings
    payload = f'{{"apis":[{{"method":"deferred_execution_api","params":{{"version":"1","sleep":"3","api_list":[{{"method":"nw_name","params":["{nw_name_value}"]}},{{"method":"power_mw","params":["{power_value}"]}},{{"method":"freq_bw","params":["{freq_value}","{bw_value}"]}},{{"method":"setenvlinsingle","params":["nw_name"]}},{{"method":"setenvlinsingle","params":["power_mw"]}},{{"method":"setenvlinsingle","params":["freq_bw"]}}]}}}}],"nodeids":{nodeids}}}'

    headers = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
        'X-Requested-With': 'XMLHttpRequest'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text


def set_basic_settings(radio_ip, nodelist, settings):
    set_net = settings.set_net_flag
    f = str(settings.frequency)
    bw = str(settings.bw)
    net_id = str(settings.netID)
    power = str(settings.powerdBm)

    if set_net:
        response = send_broadcast(radio_ip, f, bw, net_id, power, nodelist)
    else:
        response = set_single(radio_ip, f, bw, net_id, power)

    return response
