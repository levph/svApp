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

from utils.send_commands import send_commands_ip


def get_rssi_report(ip):
    # enable rssi report
    res = send_commands_ip(methods=["rssi_report_address"], radio_ip=ip, params=[["172.20.2.1", "30000"]])

    # set rssi report timing
    res2 = send_commands_ip(methods=["rssi_report_period"], radio_ip=ip, params=[["500"]])
    lev = 1


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
    node_ids = send_commands_ip(["routing_tree"], radio_ip=s_ip, params=[[]])

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
        devices = send_commands_ip(["read_client_list"], radio_ip=iip, params=[[]])
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
    :param nodelist:
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
    snrs = {tuple(sorted(result[i:i + 2])): result[i + 2]
            for sublist in snr_report
            for entry in sublist
            for result in [entry['result']]
            for i in range(0, len(result), 3)}

    # Converting tuples back to lists
    # result = [list(t) for t in snr_tuples]
    snrs_dict = [{"id1": k[0], "id2": k[1], "snr": v} for k, v in snrs.items()]

    return snrs_dict


# TODO: test and use send command all
def get_batteries(ips):
    # print battery percentage for each
    percents = []

    for radio_ip in ips:
        battery_percentage = send_commands_ip(["battery_percent"], radio_ip=radio_ip, params=[[]])
        print(f'Radio IP: {radio_ip}, Battery: {battery_percentage[0]}')
        percents.append(battery_percentage[0])

    result = [{"ip": ip, "percent": percent} for ip, percent in zip(ips, percents)]
    return result


def set_ptt_groups(ips, num_groups, statuses):
    """
    This method sets ptt group settings for all radios
    :param ips: ips of radios to change group settings
    :param num_groups: amount of groups to set
    :param statuses: statuses of each group
    :return:
    """
    group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(num_groups)]

    # methods = ["ptt_mcast_group"] * len(group_ips)

    # set groups for all radios
    for ip in ips:
        methods = ["ptt_mcast_group"] * len(group_ips)
        res = send_commands_ip(methods=methods, radio_ip=ip, params=group_ips)
        # for g in group_ips:
        #     res = send_commands_ip(["ptt_mcast_group"], ip=ip, params=g)

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

        ptt_str = '_'.join(arr)
        ptt_settings.append([ptt_str])

    for ii in range(len(ips)):
        res = send_commands_ip(["ptt_active_mcast_group"], radio_ip=ips[ii], params=[ptt_settings[ii]])

    return "Success maybe"


def get_basic_set(radio_ip):
    """
    get current settings of frequency, bandwidth, net_id and power of current device
    :param radio_ip:
    :return:
    """
    methods = ["freq", "bw", "power_dBm", "nw_name"]
    params = [[]] * 4

    res = send_commands_ip(methods, radio_ip, params)

    res = {
        "set_net_flag": [],
        "frequency": float(res[0][0]),
        "bw": float(res[1][0]),
        "net_id": res[3][0],
        "power_dBm": float(res[2][0])
    }

    return res

# def test_routing_tree():
#     ip = "172.20.238.213"
#     ip2 = "172.20.241.202"
#     route_tree = send_commands_ip("routing_tree", ip=ip)
#
#     connected_devices = send_commands_ip("read_client_list", ip=ip2)
#
#     net_stat = send_commands_ip("network_status", ip=ip)
#     print(net_stat)
