import requests


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


def get_version(s_ip):
    """
    Get version of silvus API
    :param s_ip:
    :return:
    """
    res = send_command_ip("version", s_ip)
    return res


def change_led(s_ip, param):
    """
    Toggle given radio led.
    :param s_ip:
    :param param:
    :return:
    """
    data = [str(param)]
    send_command_ip("led_disable", s_ip, data)
    print("LED Toggled")


def net_status(s_ip):
    """
    return devices in network and SNR between them
    :param s_ip:
    :return:
    """
    network_status = send_command_ip("network_status", s_ip)
    return network_status


def list_devices(s_ip):
    network_status = send_command_ip("network_status", s_ip)

    # get ids of all nodes in the network
    network_ids = list(set([int(iid) for ii, iid in enumerate(network_status['result']) if (ii + 1) % 3 != 0]))

    # translate ids of all the nodes to ip
    ips = id_2_ip(network_ids)

    return ips, network_ids, network_status


def get_batteries(ips):
    # print battery percentage for each
    for radio_ip in ips:
        battery_percentage = send_command_ip("battery_percent", radio_ip)

        print(f'Radio IP: {radio_ip}, Battery: {battery_percentage["result"][0]}')


def node_labels(s_ip):
    res = send_command_ip("node_labels", s_ip)
    return res


def save_node_label(s_ip):
    data = {
        "node_id": "61898",
        "node_label": "lev2"
    }
    res = send_command_ip("save_node_label", s_ip, data)
    return res


# TODO: Understand how to apply profile settings not just upload
def upload_settings(s_ip, settings_path):
    """
    Command: add_profile
    Parameter: {“profile_name”:”name”, “profile_file”:”file”}
    Description: Adds the provided profile “profile_file” onto the radio. Saved as “profile_name”.

    :param settings_path:
    :param s_ip:
    :return:
    """

    # Read the contents of the JSON file
    with open(settings_path, 'r') as file:
        profile_content = file.read()
    data = {
        "profile_name": "MyProfileName2",
        "profile_file": profile_content
    }

    result = send_command_ip("add_profile", s_ip, data)
    print("set profile?")
