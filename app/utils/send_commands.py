import requests
import json
import asyncio

lock = asyncio.Lock()

COOKIE = None


def api_login(un, pw, radio_ip):
    """
    Login function
    """
    global COOKIE

    # define parameters for log-in query
    login_url = f"http://{radio_ip}/login.sh?username={un}&password={pw}&Submit=1"

    response = requests.post(login_url)  # , data=payload)
    if response.status_code == 200:
        try:
            COOKIE = response.cookies
            res = send_commands_ip(["routing_tree"], radio_ip=radio_ip, params=[[]])
            # if we got a response then log in is succesful 
            return True
        except Exception as e:
            # if we got some sort of error then log in wasn't succesful 
            return False
    else:
        return False


# TODO: test!!! add error handling and generic sending for special URLs
def send_net_stat(radio_ip, nodelist):
    global COOKIE

    url = f'http://{radio_ip}/bcast_enc.pyc'

    payload = f'{{"apis":[{{"method":"network_status","params":{{}}}}],"nodeids":{nodelist}}}'

    headers = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
        'X-Requested-With': 'XMLHttpRequest'
    }

    response = requests.post(url, headers=headers, data=payload, timeout=10, cookies=COOKIE)
    if response.status_code == 200:
        COOKIE = response.cookies
    return response


def send_commands_ip(methods, radio_ip, params=None, timeout=None):
    """
    Method able to send one command or multiple to one radio.
    Including error handling
    :param methods: list(str) of method names
    :param radio_ip: str of radio ip
    :param params: list of params for each method, if no params list of []
    :return: result!
    """
    global COOKIE
    command_list = [{
        "jsonrpc": "2.0",
        "method": methods[i],
        "id": i,
        "params": params[i]

    } for i in range(len(methods))]

    payload = json.dumps(command_list if len(methods) > 1 else command_list[0])
    if methods[0] == "streamscape_data" or len(methods) > 1:
        api_endpoint = f"http://{radio_ip}/cgi-bin/streamscape_api"
    else:
        api_endpoint = f"http://{radio_ip}/streamscape_api"

    try:
        response = requests.post(api_endpoint, payload, timeout=10, cookies=COOKIE)
        # response = requests.post(api_endpoint, payload, timeout=10, cookies=COOKIE)

        response.raise_for_status()  # Raise an exception for HTTP errors
        temp_cookie = response.cookies
        response = response.json()

        # check if there's an internal silvus error
        if 'error' in response:
            raise RuntimeError(f"Silvus error {response['error']['code']}: {response['error']['message']}")

        # save cookie if all else was succesfull 
        COOKIE = temp_cookie
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
