"""
This file lists some of the API functions for Silvus app backend

File structure:
- send command ip
- send broadcast
...

functions to start:
- list devices
- save node labels
- report? understand how to
-
"""

import requests
import json
import socket
from onvif import ONVIFCamera, exceptions
from zeep.transports import Transport
from onvif.client import zeep
from urllib.parse import urlparse


def send_command_all(radio_ip, nodelist, method, params=None):
    url = f'http://{radio_ip}/bcast_enc.pyc'

    payload = f'{{"apis":[{{"method":"","params":{{}}}}],"nodeids":{nodelist}}}'

    headers = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
        'X-Requested-With': 'XMLHttpRequest'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    data = json.loads(response.text)
    return data


def send_command_ip(method, ip, params=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": "1"
    }
    api_endpoint = f'http://{ip}/streamscape_api'
    # TODO: add error handling as explain in API manual
    try:
        response = requests.post(api_endpoint, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()['result']  # Return the content if successful
    except requests.exceptions.Timeout:
        raise TimeoutError("The request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")


def get_rssi_report(ip):
    # enable rssi report
    res = send_command_ip(method="rssi_report_address", ip=ip, params=["172.20.2.1", "30000"])

    # set rssi report timing
    res2 = send_command_ip(method="rssi_report_period", ip=ip, params=["500"])
    lev = 1

    def parse_rssi_report(data):
        # Assuming data is a JSON string
        report = json.loads(data)
        return report

    def start_rssi_listener(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))

        while True:
            data, addr = sock.recvfrom(1024)
            snr_values = parse_rssi_report(data)
            print(f"Received SNR values: {snr_values}")

    start_rssi_listener("172.20.2.1", 30000)


def node_id_to_ip(nodelist):
    """
    This method converts node ids to node ips in SW V5
    The network base address is 172.16.0.0.
    node ID is corresponding to last 20 bits of the IP.
    Node IP is essentialy = base_ip + nodeID

    :param nodelist: list of integers indicating network node IDs
    :return: ips: list of corresponding node IPs
    """
    base_ip = "172.16.0.0"
    ips = []

    for node_id in nodelist:
        # Ensure node_id is within the valid range for a 20-bit number
        if node_id < 0 or node_id >= (1 << 20):
            raise ValueError("Node ID must be a 20-bit number (0 to 1048575).")

        # Convert base IP to binary and extract the network part
        base_ip_octets = [int(octet) for octet in base_ip.split('.')]
        base_ip_bin = ''.join(format(octet, '08b') for octet in base_ip_octets)

        # Extract the network prefix (first 12 bits)
        network_prefix = base_ip_bin[:12]

        # Convert node ID to a 20-bit binary string
        node_id_bin = format(node_id, '020b')

        # Combine the network prefix and the node ID
        ip_bin = network_prefix + node_id_bin

        # Split the 32-bit binary string into four 8-bit segments
        octets = [ip_bin[i:i + 8] for i in range(0, 32, 8)]

        # Convert each 8-bit segment to a decimal number
        ip_address = '.'.join(str(int(octet, 2)) for octet in octets)

        ips.append(ip_address)

    return ips


def list_devices(s_ip):
    node_ids = send_command_ip("routing_tree", ip=s_ip)

    # translate ids of all the nodes to ip
    ips = node_id_to_ip(node_ids)

    return ips, node_ids


def find_camera_streams_temp(iplist):
    """
    this method is temporary and assumes all cameras are silvus cameras
    with specific URLs for RTSP streams!

    :param iplist: lists of device IPs in network
    :return:
    """

    cameras = []

    # find connected devices in each node
    for iip in iplist:
        devices = send_command_ip("read_client_list", ip=iip)
        filtered_devices = [device for device in devices if not device['mac'].startswith('c4:7c:8d')]
        for device in filtered_devices:
            ip = device['ip']

            # check if it's an ONVIF camera
            try:
                response = requests.get(f"http://{ip}", timeout=3)

                # check if it's a silvus IP camera
                if response.headers['Server'] != "IPCamera-Webs":
                    continue

            except Exception as e:
                continue

            # define camera object if it's a camera
            camera = {
                'ip': ip,
                'connected_to': iip,
                'main_stream': {
                    'uri': f"rtsp://{ip}:554/av0_0",
                    'audio': 1
                },
                'sub_stream': {
                    'uri': f"rtsp://{ip}:554/av0_1",
                    'audio': 1
                }
            }
            cameras.append({f'camera': camera})

    return cameras


# def find_camera_streams(iplist):
#     """
#     Finding all cameras in network and returns stream IPs
#     :param iplist:
#     :return:
#     """
#     # definitions
#     username = 'admin'
#     password = 'admin'
#     port = 2000  # assume ONVIF port is always 2000
#
#     cameras = []
#
#     # for request timeout
#     transport = Transport(timeout=5)
#
#     # find connected devices in each node
#     for iip in iplist:
#         devices = send_command_ip("read_client_list", ip=iip)
#         filtered_devices = [device for device in devices if not device['mac'].startswith('c4:7c:8d')]
#         for device in filtered_devices:
#             ip = device['ip']
#
#             # check if it's an ONVIF camera
#             try:
#                 # TODO: timeout if camera ip not in subnet
#                 camera = ONVIFCamera(ip, port, username, password, transport=transport)
#
#                 # Test a simple ONVIF request
#                 camera.devicemgmt.GetHostname()
#             except Exception as e:
#                 continue
#                 try:
#                     response = requests.get(f"http://{ip}")
#
#                 except Exception as e2:
#
#                     # if we got an exception then it's not a camera
#                     continue
#
#             # Get the media service
#             media_service = camera.create_media_service()
#
#             # Get all profiles
#             profiles = media_service.GetProfiles()
#
#             # Create the StreamSetup object
#             stream_setup = {
#                 'Stream': 'RTP-Unicast',  # or 'RTP-Multicast' if using multicast
#                 'Transport': {
#                     'Protocol': 'RTSP'
#                 }
#             }
#
#             # Extract RTSP stream URIs from each profile
#             stream_uris = []
#             audio = []
#             for profile in profiles:
#                 try:
#                     # Get the stream URI for the profile
#                     stream_uri_response = media_service.GetStreamUri({
#                         'StreamSetup': stream_setup,
#                         'ProfileToken': profile.token
#                     })
#                     stream_uris.append(stream_uri_response.Uri)
#
#                     # Get VideoSourceConfiguration
#                     video_source_config = media_service.GetVideoSourceConfiguration(
#                         {'ConfigurationToken': profile.VideoSourceConfiguration.token})
#
#                     # Get AudioSourceConfiguration if available
#                     try:
#                         audio_source_config = media_service.GetAudioSourceConfiguration(
#                             {'ConfigurationToken': profile.AudioSourceConfiguration.token})
#                         audio.append(1)
#                     except:
#                         print(f"No Audio Source Configuration for {profile.Name}")
#                         audio.append(0)
#
#                 except exceptions.ONVIFError as e:
#                     print(f"Failed to get stream URI for profile {profile.Name}: {e}")
#
#             # After finding all profiles
#             camera = {
#                 'connected_to': iip,
#                 'main_stream': {
#                     'uri': stream_uris[0],
#                     'audio': audio[0]
#                 },
#                 'sub_stream': {
#                     'uri': stream_uris[1],
#                     'audio': audio[1]
#                 }
#             }
#             cameras.append(camera)
#
#     print(cameras)
#
#     # connected_devices = send_command_all(method="read_client_list", radio_ip=sip, nodelist=nodelist)
#     # check each device if it's a camera
#     ...
#
#     return 1


# TODO: test
def net_status(radio_ip, nodelist):
    """
    return devices in network and SNR between them
    :param radio_ip:
    :param s_ip:
    :return:
    """
    url = f'http://{radio_ip}/bcast_enc.pyc'

    payload = f'{{"apis":[{{"method":"network_status","params":{{}}}}],"nodeids":{nodelist}}}'

    headers = {
        'Accept': '*/*',
        'Content-Type': 'text/plain',
        'X-Requested-With': 'XMLHttpRequest'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    snr_report = json.loads(response.text)

    # Extracting unique [id, id, value] tuples from the result arrays
    snr_tuples = set((tuple(sorted([result[i], result[i + 1]])), result[i + 2])
                     for sublist in snr_report
                     for entry in sublist
                     for result in [entry['result']]
                     for i in range(0, len(result), 3))

    # Converting tuples back to lists
    result = [list(t) for t in snr_tuples]

    return result


# TODO: test and use send command all
def get_batteries(ips):
    # print battery percentage for each
    percents = []

    for radio_ip in ips:
        battery_percentage = send_command_ip("battery_percent", radio_ip)
        print(f'Radio IP: {radio_ip}, Battery: {battery_percentage[0]}')
        percents.append(battery_percentage[0])

    result = [{"ip": ip, "%": percent} for ip, percent in zip(ips, percents)]
    return result


def test_routing_tree():
    ip = "172.20.238.213"
    ip2 = "172.20.241.202"
    route_tree = send_command_ip("routing_tree", ip=ip)

    connected_devices = send_command_ip("read_client_list", ip=ip2)

    net_stat = send_command_ip("network_status", ip=ip)
    print(net_stat)

    # rssi_report = get_rssi_report(ip)

