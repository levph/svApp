import requests
import json
import asyncio
from utils.fa_models import Credentials

lock = asyncio.Lock()

COOKIE = None
VERSION = None
CREDENTIALS = None
SSH_CLIENT = None


# TODO: test
# def ssh_multiple_commands(ip, command_template, methods, target_ips, response_pattern):
#     """
#     This method sends messages via the SSH api!
#     :param methods:
#     :param ip: IP of connected device
#     :param command_template:
#     :param target_ips:
#     :param response_pattern:
#     :return:
#     """
#     hostname = ip
#     password = "root"  # hardcoded pw, sue me
#     port = 22
#     username = "root"
#
#     ssh_client = paramiko.SSHClient()
#     ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#
#     try:
#         ssh_client.connect(hostname, port, username, password, timeout=10)
#
#         # Open an interactive shell session
#         shell = ssh_client.invoke_shell()
#         time.sleep(1)  # Wait for the shell prompt to appear
#
#         # Read the initial prompt
#         shell.recv(1024).decode('utf-8')
#
#         results = []
#         for method, target_ip in zip(methods, target_ips):
#             command = command_template.format(target_ip=target_ip, method=method)
#             shell.send(command + "\n")
#             time.sleep(2)  # Wait for the command to execute
#
#             # Read the command output
#             output = ""
#             while True:
#                 if shell.recv_ready():
#                     chunk = shell.recv(1024).decode('utf-8')
#                     output += chunk
#                     time.sleep(0.5)  # Adjust sleep time if necessary
#                     # Check if the expected pattern is in the output
#                     match = re.search(response_pattern, output)
#                     if match:
#                         percent = match.group(1)
#                         results.append(percent)
#                         break
#                 else:
#                     break
#
#         ssh_client.close()
#
#         return results
#
#     except Exception as e:
#         return "Error"


# TODO: handle failed devices and test
def read_from_multiple(radio_ip, radio_ips, methods, params):
    """
    when needed to read from multiple devices, due to device limitations, we need to send messages
    to each device separately.
    :param radio_ip: ip of connected radio
    :param params: list of lists, params for each radio
    :param radio_ips:
    :param methods: list of lists, methods for each radio
    :return:
    """
    global COOKIE, CREDENTIALS

    # save current session's cookie
    cached_cookie = COOKIE

    # set relevant flags
    success_flag = True
    auth_flag = True if CREDENTIALS else False
    results = [None] * len(radio_ips)
    failed_ips = []

    # send messages to each device
    for ii, ip in enumerate(radio_ips):

        # if original device is password protected, assume all other devices are too
        if auth_flag:
            res = api_login(CREDENTIALS.username, CREDENTIALS.password,
                            ip)  # also updates session cookie, works for unlocked devices
            if not res:
                success_flag = False  # need to perform slower SSH broadcast
                failed_ips.append(ip)
                # results.append("-1")  # TODO: add option for global fail format
                continue
        try:
            result = send_commands_ip(methods[ii], radio_ip=ip, params=params[ii])
        except Exception as e:
            if "Authentication error" in e.args[0]:
                # Encountered a password protected device.
                success_flag = False
                failed_ips.append(ip)
                result = None
            else:
                raise RuntimeError(f"An error occurred: {e}")

        if auth_flag:
            exit_session()
        results[ii] = result

    # for now only when one command to all devices, and no params
    if not success_flag:
        # perform ssh broadcasting for failed ips... for now nothing
        indices = [radio_ips.index(iip) for iip in failed_ips]
        failed_methods = [methods[ii][0] for ii in indices]
        failed_params = [params[ii] for ii in indices]
        # SSH details for the main connection

        command_template = "api {target_ip} {method}"

        # Regular expression template to extract the percent value
        response_pattern = r'\["(\d+\.\d+)"\]'

        # Run the command on multiple target IPs
        # ssh_result = ssh_multiple_commands(radio_ip, command_template, failed_methods, failed_ips,
        #                                        response_pattern)
        for ii, idx in enumerate(indices):
            # results[idx] = ssh_result[ii]
            results[idx] = 'nan'

    # restore original session
    COOKIE = cached_cookie
    return results


def set_credentials(credentials: Credentials):
    global CREDENTIALS
    CREDENTIALS = credentials


def set_version(version):
    global VERSION
    VERSION = version


def exit_session():
    """
    Method to zeroize session on application exit
    :return: nothing lol
    """
    global COOKIE, VERSION, CREDENTIALS
    COOKIE = VERSION = None
    CREDENTIALS = Credentials


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
    if VERSION == 4:
        url = url[:-1]  # script has .py suffix in v4

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


def send_save_node_label(radio_ip, label_string, nodelist):
    """
    Specific method for setting node labels in flash
    :param label_string:
    :param radio_ip:
    :param params:
    :param nodelist:
    :return:
    """
    global COOKIE

    api_endpoint = f"http://{radio_ip}/bcast_enc.pyc"
    if VERSION == 4:
        api_endpoint = api_endpoint[:-1]

    api_list = [
        {
            "method": "save_node_labels_flash",
            "params": ["1", label_string]
        }
    ]

    payload = json.dumps({
        "apis": [
            {
                "method": "deferred_execution_api",
                "params": {
                    "version": "1",
                    "sleep": "0",
                    "api_list": api_list
                }
            }
        ],
        "nodeids": nodelist,
        "override": 1
    })

    try:
        response = requests.post(api_endpoint, payload, timeout=10, cookies=COOKIE)
        # response = requests.post(api_endpoint, payload, timeout=10, cookies=COOKIE)
        if "JSONDecodeError" in response.text:
            return "JsonDecodeError"
        response.raise_for_status()  # Raise an exception for HTTP errors
        temp_cookie = response.cookies

        response = response.json()

        # check if there's an internal silvus error
        if 'error' in response:
            raise RuntimeError(f"Silvus error {response['error']['code']}: {response['error']['message']}")

        # save cookie if all else was succesfull
        COOKIE = temp_cookie

        return response  # return the content

    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")
    except Exception as e:
        raise RuntimeError(f"Unknown error: {e}")


# TODO: test all functions
def send_commands_ip(methods, radio_ip, params=None, bcast=0, nodelist=None, param_flag=0, timeout=None):
    """
    Method able to send one command or multiple to one radio.
    Including error handling
    :param timeout:
    :param nodelist:
    :param bcast:
    :param methods: list(str) of method names
    :param radio_ip: str of radio ip
    :param params: list of params for each method, if no params list of []
    :return: result!
    """
    global COOKIE, VERSION
    headers = {
        'Content-Type': 'application/json'
    }
    param_str = "param" if param_flag else "params"

    if bcast:

        command_list = [{
            "method": methods[i],
            param_str: params[i]

        } for i in range(len(methods))]

        payload = json.dumps({
            "apis": [
                {
                    "method": "deferred_execution_api",
                    param_str: {
                        "version": "1",
                        "sleep": "0",
                        "api_list": command_list
                    }
                }
            ],
            "nodeids": nodelist
        })

        api_endpoint = f"http://{radio_ip}/bcast_enc.pyc"
        if VERSION == 4:
            api_endpoint = api_endpoint[:-1]  # script has .py suffix in v4

    else:

        command_list = [{
            "jsonrpc": "2.0",
            "method": methods[i],
            "id": i,
            param_str: params[i]

        } for i in range(len(methods))]

        payload = json.dumps(command_list if len(methods) > 1 else command_list[0])
        if methods[0] == "streamscape_data" or len(methods) > 1:
            api_endpoint = f"http://{radio_ip}/cgi-bin/streamscape_api"
        else:
            api_endpoint = f"http://{radio_ip}/streamscape_api"

    try:
        response = requests.post(api_endpoint, payload, headers=headers, timeout=10, cookies=COOKIE)
        # response = requests.post(api_endpoint, payload, timeout=10, cookies=COOKIE)

        response.raise_for_status()  # Raise an exception for HTTP errors
        temp_cookie = response.cookies

        response = response.json()

        # TODO: test what errors bcast returns
        # check if there's an internal silvus error
        if 'error' in response:
            raise RuntimeError(f"Silvus error {response['error']['code']}: {response['error']['message']}")

        # save cookie if all else was succesfull 
        COOKIE = temp_cookie
        if not bcast:
            response = (response['result'] if len(methods) == 1 else [res['result'] for res in response])
        else:
            # check bcast success
            success_flag = all(item[0]['result'] == [''] for item in response)
            if not success_flag:
                raise RuntimeError('Broadcast Failed')

        return response  # return the content

    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")
    except Exception as e:
        raise RuntimeError(f"Unknown error: {e}")


if __name__ == "__main__":
    # = "{\\\"323285\\\": \\\"lev100\\\"}"

    # label_string = '{\\"323285\\": \\"lev1131\\"}'

    # param = ["1", '{\\"323285\\": \\"lev1131\\"}']
    # send_commands_ip(["save_node_labels_flash"], "172.20.238.213", params=[param], bcast=1, nodelist=[323285])
    # label_string = {"32": "lev1131"}
    nodeids = [324042, 323285]
    names = ["yotam", "hahomo"]
    label_string_inner = f'"{nodeids[0]}": "{names[0]}"'
    label_string = '{' + label_string_inner + '}'
    # label_string = '{"324042": "hsdai", "323285": "lev"}'
    res = send_save_node_label("172.20.241.202", label_string, [323285, 324042])
    print(res)
