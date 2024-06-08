import requests
import json


def check_response(response_json):
    """
    Error handling for silvus response
    :param response_json:
    :return:
    """
    error_msg = {'jsonrpc': '2.0', 'error': {'code': -32600, 'message': 'Invalid Request'}, 'id': None}
    good_message = 1

    result = [1, response_json['result']] if 'result' in response_json else [-1, response_json['error']]

    return result


def send_commands_ip(methodss, iip, params=None):
    command_list = [{
        "jsonrpc": "2.0",
        "method": methodss[i],
        "id": i,
        "params": params[i]
    } for i in range(len(methodss))]

    payload = json.dumps(command_list if len(methodss) > 1 else command_list[0])

    api_endpoint = f'http://{iip}/streamscape_api' if len(methodss) < 2 else f"http://{iip}/cgi-bin/streamscape_api"

    try:
        response = requests.post(api_endpoint, payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        response = response.json()

        if 'error' in response:
            raise RuntimeError(f"Silvus error {response['error']['code']}: {response['error']['message']}")

        response = (response['result'] if len(methodss) == 1 else [ress['result'] for ress in response])

        return response  # return the content
    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")


methods = ["version"]
params = [[]]
res = send_commands_ip(methods, "172.20.240.107", params)

version = res[0]

methods = ["freq", "bw", "power_dBm", "nw_name"]
params = [[]] * 4

res = send_commands_ip(methods, "172.20.240.107", params)
lev = 1
