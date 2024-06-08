import requests
import json


def send_commands_ip(methods, radio_ip, params=None, timeout=None):
    """
    Method able to send one command or multiple to one radio.
    Including error handling
    :param methods: list(str) of method names
    :param radio_ip: str of radio ip
    :param params: list of params for each method, if no params list of []
    :return: result!
    """
    command_list = [{
        "jsonrpc": "2.0",
        "method": methods[i],
        "id": i,
        "params": params[i]

    } for i in range(len(methods))]

    payload = json.dumps(command_list if len(methods) > 1 else command_list[0])

    api_endpoint = f'http://{radio_ip}/streamscape_api' if len(
        methods) < 2 else f"http://{radio_ip}/cgi-bin/streamscape_api"

    try:
        response = requests.post(api_endpoint, payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        response = response.json()

        # check if there's an internal silvus error
        if 'error' in response:
            raise RuntimeError(f"Silvus error {response['error']['code']}: {response['error']['message']}")

        response = (response['result'] if len(methods) == 1 else [res['result'] for res in response])

        return response  # return the content

    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")


def send_command_ip(method, ip, params=None):
    """
    Deprecated method to send only one command to given ip
    :param method: name of method
    :param ip: ip of device
    :param params: parameters
    :return: result
    """
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
