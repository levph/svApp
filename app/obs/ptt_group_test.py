import requests
import json

query = {'num_groups': 4,
         'ips': ['172.20.240.107'],
         'statuses': [[1, 1, 0, 0]]
         }


# note! always at least one active group
def send_commands_ip(methodss, iip, params=None):
    command_list = json.dumps([{
        "jsonrpc": "2.0",
        "method": methodss[i],
        "id": i,
        "params": params[i]
    } for i in range(len(methodss))])

    payload = {
        "version": "2.0",
        "sleep": "0",
        "api_list": command_list
    }

    api_endpoint = f'http://{iip}/streamscape_api'

    try:
        response = requests.post(api_endpoint, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()['result']  # Return the content if successful
    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")


def send_command_ip(method, ip, params=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": "1"
    }
    api_endpoint = f'http://{ip}/streamscape_api'
    try:
        response = requests.post(api_endpoint, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()['result']  # Return the content if successful
    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")


num_groups = query['num_groups']
ips = query['ips']
statuses = query['statuses']

group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(num_groups)]

methods = ["ptt_mcast_group"] * len(group_ips)

# set groups for all radios
for ip in ips:
    for g in group_ips:
        lev = 3
        # res = send_command_ip("ptt_mcast_group", ip, g)

ptt_settings = []

# set status strings for each, including reset! (making other groups inactive)
for status in statuses:
    # classify each group
    listen = []
    talk = []
    monitor = []
    for ii, g in enumerate(status):
        if g == 1:
            listen.append(str(ii))
            talk.append(str(ii))
        elif g == 2:
            listen.append(str(ii))
            monitor.append(str(ii))

    listen = ','.join(listen)
    talk = ','.join(talk)
    monitor = ','.join(monitor)

    arr = [listen, talk, monitor] if monitor else [listen, talk]
    # arr = [listen, talk, monitor]

    ptt_str = '_'.join(arr)
    ptt_settings.append(ptt_str)

for ii in range(len(ips)):
    res = send_command_ip("ptt_active_mcast_group", ips[ii], ptt_settings[ii])
