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
            "method": "max_link_distance",
            "id": 2,
            "params": [
                "5000"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "power_dBm",
            "id": 4,
            "params": [
                power
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "freq_bw",
            "id": 5,
            "params": [
                f,
                bw
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 6,
            "params": [
                "freq"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 7,
            "params": [
                "bw"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 8,
            "params": [
                "nw_name"
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "setenvlinsingle",
            "id": 9,
            "params": [
                "power_dBm"
            ]
        }
    ])

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)

    return response.text


def send_broadcast(radio_ip, f, bw, net_id, power, nodelist):
    url = f"http://{radio_ip}/bcast_enc.pyc"

    payload = json.dumps({
        "apis": [
            {
                "method": "deferred_execution_api",
                "params": {
                    "version": "1",
                    "sleep": "0",
                    "api_list": [
                        {
                            "method": "nw_name",
                            "params": [
                                net_id
                            ]
                        },
                        {
                            "method": "max_link_distance",
                            "params": [
                                "5000"
                            ]
                        },
                        {
                            "method": "power_dBm",
                            "params": [
                                power
                            ]
                        },
                        {
                            "method": "freq_bw",
                            "params": [
                                f,
                                bw
                            ]
                        },
                        {
                            "method": "setenvlinsingle",
                            "params": [
                                "nw_name"
                            ]
                        },
                        {
                            "method": "setenvlinsingle",
                            "params": [
                                "max_link_distance"
                            ]
                        },
                        {
                            "method": "setenvlinsingle",
                            "params": [
                                "power_mw"
                            ]
                        },
                        {
                            "method": "setenvlinsingle",
                            "params": [
                                "freq_bw"
                            ]
                        }
                    ]
                }
            }
        ],
        "nodeids": nodelist
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text


def set_basic_settings(radio_ip, nodelist, settings):
    set_net = settings.set_net_flag
    f = str(settings.frequency)
    bw = str(settings.bw)
    net_id = str(settings.net_id)
    power = str(settings.power_dBm)

    if set_net:
        response = send_broadcast(radio_ip, f, bw, net_id, power, nodelist)
    else:
        response = set_single(radio_ip, f, bw, net_id, power)

    return response
