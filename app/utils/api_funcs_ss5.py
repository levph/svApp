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
from utils.send_commands import send_commands_ip, read_from_multiple, send_save_node_label


def get_radio_label(radio_ip):
    labels = send_commands_ip(["node_labels"], radio_ip=radio_ip, params=[[]])
    # id_label = [{'id': int(k), 'name': v} for k, v in labels.items()]

    # add new devices if there are any
    ids_labels = [(int(k), v) for k, v in labels.items()]
    if ids_labels:
        ids, names = zip(*ids_labels)
        ids, names = list(ids), list(names)
    else:
        ids = names = []
    # ids, names = zip(*[(int(k), v) for k, v in labels.items()])
    # ids, names = list(ids), list(names)

    id_label = {"ids": ids, "names": names}

    return id_label


def node_id_to_ip_v4(id_list):
    last_bytes = [(node // 256, node % 256) for node in id_list]
    iips = ["172.20." + str(b[0]) + "." + str(b[1]) for b in last_bytes]
    return iips


def node_id_to_ip(nodelist, version):
    """
    This method converts node ids to node ips in SW V5
    The network base address is 172.16.0.0.
    node ID is corresponding to last 20 bits of the IP.
    Node IP is essentialy = base_ip + nodeID

    :param version: int version of firmware
    :param nodelist: list of integers indicating network node IDs
    :return: ips: list of corresponding node IPs
    """
    base_ip = "172.16.0.0"
    ips = []

    if version == 4:
        ips = node_id_to_ip_v4(nodelist)
    else:  # v5
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


def list_devices(s_ip, version):
    node_ids = send_commands_ip(["routing_tree"], radio_ip=s_ip, params=[[]])

    # translate ids of all the nodes to ip
    ips = node_id_to_ip(node_ids, version)

    return ips, node_ids


def find_camera_streams_temp(iplist,idlist):
    """
    this method is temporary and assumes all cameras are silvus cameras
    with specific URLs for RTSP streams!

    :param iplist: lists of device IPs in network
    :return:
    """

    cameras = []

    # find connected devices in each node
    for iip, iid in zip(iplist, idlist):
        devices = send_commands_ip(["read_client_list"], radio_ip=iip, params=[[]])
        filtered_devices = [device for device in devices if device['ip'] not in iplist]
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
                'device_ip': iip,
                'device_id': iid,
                'main_stream': {
                    'uri': f"rtsp://{ip}:554/av0_0",
                    'audio': 1
                },
                'sub_stream': {
                    'uri': f"rtsp://{ip}:554/av0_1",
                    'audio': 1
                }
            }
            cameras.append(camera)

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


def net_status(radio_ip):
    """
    return devices in network and SNR between them
    :param nodelist:
    :param radio_ip:
    :param s_ip:
    :return:
    """

    def extract_snr(data):
        node_iids = []
        min_snr = {}
        for node in data:
            node_iids.append(int(node["id"]))
            for adjacency in node.get("adjacencies", []):
                nodeTo = adjacency["nodeTo"]
                nodeFrom = adjacency["nodeFrom"]
                snr_key = f"$snr_{nodeFrom}_{nodeTo}"
                if snr_key in adjacency["data"]:
                    snr = int(adjacency["data"][snr_key])

                    # Create a sorted tuple to ensure (a, b) is the same as (b, a)
                    pair = tuple(sorted([nodeFrom, nodeTo]))

                    # Update the minimum SNR value for the pair
                    if pair in min_snr:
                        min_snr[pair] = min(min_snr[pair], snr)
                    else:
                        min_snr[pair] = snr

        snr_res = [{"id1": k[0], "id2": k[1], "snr": v} for k, v in min_snr.items()]

        return snr_res

    response = send_commands_ip(["streamscape_data"], radio_ip, [[]])
    return extract_snr(response)


def get_device_battery(ip: str) -> dict[str, str]:
    battery_percent = send_commands_ip(["battery_percent"], ip, params=[[]])[0]
    battery_percent = str(round(float(battery_percent)))
    return {"percent": battery_percent}


def get_batteries(radio_ip, radio_ips):
    """
    This method returns battery percent for each device in the network
    :param radio_ips: ips of devices to test
    :return:
    """
    percents = []
    methods = [["battery_percent"] for _ in range(len(radio_ips))]
    params = [[[]] for _ in range(len(radio_ips))]

    battery_percents = read_from_multiple(radio_ip, radio_ips, methods, params)

    # for status in statusim:
    #     status['percent'] = battery_percents[radio_ips.index(status["ip"])][0]

    result = [{"ip": ip, "percent": str(round(float(percent[0])))} for ip, percent in zip(radio_ips, battery_percents)]
    result_new_format = {d['ip']: d['percent'] for d in result}
    return result, result_new_format


def get_ptt_groups(ips, ids, names):
    group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(15)]
    statuses = [[] for _ in range(len(ips))]
    global_max_group = 0
    for radio_index, radio_ip in enumerate(ips):
        ptt_groups = send_commands_ip(["ptt_active_mcast_group"], radio_ip=radio_ip, params=[[]], param_flag=1)[0]
        states = ptt_groups.split('_')
        listen = states[0].split(',')
        talk = states[1].split(',')

        monitor = [] if len(states) < 3 else states[2].split(',')
        max_group = int(max(listen + talk + monitor)) + 1
        global_max_group = max(max_group, global_max_group)
        for i in range(max_group):
            str_i = str(i)
            if str_i in listen:
                if str_i in talk:  # active
                    statuses[radio_index].append(1)
                elif str_i in monitor:  # monitor
                    statuses[radio_index].append(2)
                # should not get here
            else:  # inactive or does not exist
                statuses[radio_index].append(0)

    res = []
    for ip, iid, status in zip(ips, ids, statuses):
        if iid in names["ids"]:
            name = names["names"][names["ids"].index(iid)]
        else:
            name = ip
        res.append({"ip": ip, "id": iid, "status": status, "name": name})

    return res
    # return {'num_groups': max_group, 'ips': ips, 'statuses': statuses}


def set_ptt_groups(radio_ip, ips, nodelist, num_groups, statuses):
    """
    This method sets ptt group settings for all radios
    :param ips: ips of radios to change group settings
    :param num_groups: amount of groups to set
    :param statuses: statuses of each group
    :return:
    """

    # set group mcast IPs for all radios in network
    group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(num_groups)]
    methods = ["ptt_mcast_group"] * len(group_ips) + ["setenvlinsingle"]
    params = group_ips + ["ptt_mcast_group"]
    res = send_commands_ip(methods=methods, radio_ip=radio_ip, params=params, bcast=1, nodelist=nodelist)

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

    for ii in range(len(nodelist)):
        # send to each radio its ptt settings
        res = send_commands_ip(["ptt_active_mcast_group"], radio_ip=radio_ip, params=[ptt_settings[ii]], bcast=1,
                               nodelist=[nodelist[ii]])

    # save settings for all
    res = send_commands_ip(["setenvlinsingle"], radio_ip=radio_ip, params=[["ptt_active_mcast_group"]], bcast=1, nodelist=nodelist)
    return "Success maybe"


def set_label_id(radio_ip, node_id, label, nodelist):
    # get names saved in radio who's ip is radio_ip
    current_names = send_commands_ip(["node_labels"], radio_ip, params=[[]])

    # change label of node_id
    current_names[str(node_id)] = label

    # convert to acceptable format
    current_names = json.dumps(current_names)

    # use designated api method
    res = send_save_node_label(radio_ip, current_names, nodelist)

    return res[0][0]['result'] == ['']


def get_basic_set(radio_ip):
    """
    get current settings of frequency, bandwidth, net_id and power of current device
    :param radio_ip:
    :return:
    """
    methods = ["freq", "bw", "power_dBm", "nw_name", "enable_max_power"]
    params = [[]] * 5

    res = send_commands_ip(methods, radio_ip, params)

    enable_max = int(res[4][0])

    power = "Enable Max Power" if enable_max else str(res[2][0])

    res = {
        "set_net_flag": [],
        "frequency": float(res[0][0]),
        "bw": float(res[1][0]),
        "net_id": res[3][0],
        "power_dBm": power
    }

    return res


def set_basic_settings(radio_ip, nodelist, settings):
    """
    This method sets basic settings either for one radio or entire network.
    Automatically sets max_link_distance to 5000
    :param radio_ip: radio ip
    :param nodelist: list of nodes in network
    :param settings: struct containing freq, bw, net_id and power settings
    :return:
    """
    set_net = settings.set_net_flag
    f = str(settings.frequency)
    bw = str(settings.bw)
    net_id = str(settings.net_id)
    power = str(settings.power_dBm)

    if power == "Enable Max Power":
        enable_max = "1"
        power = "36"
    else:
        enable_max = "0"

    methods = ["nw_name", "max_link_distance", "power_dBm", "freq_bw", "enable_max_power"] + ["setenvlinsingle"] * 5
    params = [[net_id], ["5000"], [power], [f, bw], [enable_max]] + [[name] for name in methods[:5]]

    if set_net:
        # set settings for entire network
        response = send_commands_ip(methods=methods, radio_ip=radio_ip, params=params, bcast=1, nodelist=nodelist)
    else:
        # set settings only for current radio
        response = send_commands_ip(methods=methods, radio_ip=radio_ip, params=params)

    return response


def get_version(radio_ip: str):
    response = send_commands_ip(methods=["build_tag"], radio_ip=radio_ip, params=[[]])[0]
    return 4 if "v4" in response else 5