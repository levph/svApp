import requests
import json
from utils.send_commands import SessionManager
from typing import Optional
from utils.fa_models import Credentials, NodeNames, IpCredentials, ErrorResponse, Status


class RadioManager:
    def __init__(self):
        self.radio_ip: Optional[str] = None
        self.session_manager: SessionManager = SessionManager()
        self.node_list: list[int] = []
        self.ip_list: list[str] = []
        self.node_names: dict[int, str] = {}
        self.statusim: list[Status] = []
        self.version: int = 5  # default
        self.cam_data = None
        self.credentials: Optional[Credentials] = None
        self.net_interval: int = 2
        self.known_batteries = {}

    def log_in(self, ip_creds: IpCredentials):

        # extract ip from input
        ip = ip_creds.radio_ip
        creds = Credentials()

        # attempt login if credentials were supplied
        if ip_creds.username and ip_creds.password:
            creds.username = ip_creds.username
            creds.password = ip_creds.password
            if not self.session_manager.log_in(radio_ip=ip, creds=creds):
                raise ErrorResponse(msg="Incorrect Credentials", status_code=401)

        # gather initial data
        try:
            version = self.get_version(ip)

            [ip_list, node_list] = self.list_devices(ip, version)

            # names are not dynamic, saved in device flash
            nodes_names = self.get_radio_label(ip)

            self.set_version(version)

            statusim = self.get_ptt_groups(ip_list, node_list, nodes_names)
        except (Timeout, TimeoutError):
            print(f"Invalid IP")
            return LogInResponse(type="Fail", msg="Timeout. Incorrect computer/radio IP")

        except Exception as e:
            if "Authentication error" in e.args[0]:
                print(f"This device is password protected. Please log-in")
                return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 1})
            else:
                raise ErrorResponse(msg=f"Unknown Error: {e}")

        RADIO_IP = ip
        NODE_NAMES = nodes_names
        NODE_LIST = node_list
        STATUSIM = statusim
        IP_LIST = ip_list
        VERSION = version
        CREDENTIALS = creds

        return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 0})


    def log_out(self):
            # Add the log_out logic here
            pass

    def get_silvus_gui_url(self):
        return f"http://{self.radio_ip}"

    def set_label(self, node):
        try:
            res = self.set_label_id(self.radio_ip, node.id, node.label, self.node_list)
            self.node_names[node.id] = node.label

            return {"Success"} if res else {"Fail"}
        except Exception as e:
            raise Exception(f"Error in setting label: {str(e)}")

    async def get_net_data(self):
        try:
            old_ip_list = self.ip_list.copy()
            self.ip_list, self.node_list = self.list_devices(self.radio_ip, self.version)
            new_ips, new_ids = [], []

            change_flag = False
            if set(self.ip_list) != set(old_ip_list):
                change_flag = True
                new_stuff = [(ip, iid) for ip, iid in zip(self.ip_list, self.node_list) if ip not in old_ip_list]
                if new_stuff:
                    new_ips, new_ids = zip(*new_stuff)
                    new_ips, new_ids = list(new_ips), list(new_ids)

                new_statusim = []
                if new_ips:
                    new_statusim = self.get_ptt_groups(new_ips, new_ids, self.node_names)

                self.known_batteries = {ip: percent for ip, percent in self.known_batteries.items() if
                                        ip in self.ip_list}
                self.statusim = [status for status in self.statusim if status["ip"] in self.ip_list] + new_statusim

            snrs = []
            if len(self.ip_list) > 1:
                snrs = self.net_status(self.radio_ip)

            ip_id_dict = self.statusim
            for elem in ip_id_dict:
                elem["percent"] = "-1" if elem["ip"] not in self.known_batteries else self.known_batteries[elem["ip"]]

            msg = {
                "device_list": ip_id_dict,
                "snr_list": snrs,
                "has_changed": change_flag
            }

            return json.dumps({"type": "net_data", "data": msg})
        except Exception as e:
            raise Exception(f"Error in fetching net data: {str(e)}")

    def get_interval(self):
        return {"interval": self.net_interval}

    def change_interval(self, interval):
        self.net_interval = int(interval.value)
        return {"message": f"net-data interval set to {interval.value}"}

    async def basic_settings(self, settings):
        if settings:
            response = self.set_basic_settings(self.radio_ip, self.node_list, settings)
            return {"Error"} if "error" in response else {"Success"}
        else:
            return self.get_basic_set(self.radio_ip)

    async def get_device_battery(self, device_id):
        if not device_id:
            raise Exception("No id supplied")
        elif device_id not in self.node_list:
            raise Exception(f"{device_id} doesn't exist")

        ip = self.ip_list[self.node_list.index(device_id)]
        percent = self.get_device_battery_percent(ip)
        self.known_batteries[ip] = str(percent)
        return percent

    async def get_battery(self):
        ips_batteries, ips_batteries_new_format = self.get_batteries(self.radio_ip, self.ip_list)
        self.known_batteries.update(ips_batteries_new_format)
        return json.dumps({"type": "battery", "data": ips_batteries})

    def set_ptt_groups(self, ptt_data):
        try:
            for status in self.statusim:
                if status["ip"] in ptt_data.ips:
                    status["status"] = ptt_data.statuses[ptt_data.ips.index(status["ip"])]

            nodes = [self.node_list[self.ip_list.index(ip)] for ip in ptt_data.ips]
            self.set_ptt_groups_impl(self.radio_ip, ptt_data.ips, nodes, ptt_data.num_groups, ptt_data.statuses)
            return {"message": "ptt group settings set successfully"}
        except Exception as e:
            raise Exception(f"Error in setting PTT groups: {str(e)}")

    async def get_camera_links(self):
        streams = self.find_camera_streams_temp(self.ip_list, self.node_list)
        return {"message": "Success", "data": streams}

    @staticmethod
    def get_radio_label(radio_ip):
        labels = send_commands_ip(["node_labels"], radio_ip=radio_ip, params=[[]])
        ids_labels = [(int(k), v) for k, v in labels.items()]
        if not ids_labels:
            return {}

        ids, names = zip(*ids_labels)
        ids, names = list(ids), list(names)
        node_names = dict(zip(ids, names))

        return node_names

    def node_id_to_ip_v4(self, id_list):
        last_bytes = [(node // 256, node % 256) for node in id_list]
        iips = ["172.20." + str(b[0]) + "." + str(b[1]) for b in last_bytes]
        return iips

    def node_id_to_ip(self, nodelist, version):
        base_ip = "172.16.0.0"
        ips = []

        if version == 4:
            ips = self.node_id_to_ip_v4(nodelist)
        else:
            for node_id in nodelist:
                if node_id < 0 or node_id >= (1 << 20):
                    raise ValueError("Node ID must be a 20-bit number (0 to 1048575).")

                base_ip_octets = [int(octet) for octet in base_ip.split('.')]
                base_ip_bin = ''.join(format(octet, '08b') for octet in base_ip_octets)
                network_prefix = base_ip_bin[:12]
                node_id_bin = format(node_id, '020b')
                ip_bin = network_prefix + node_id_bin
                octets = [ip_bin[i:i + 8] for i in range(0, 32, 8)]
                ip_address = '.'.join(str(int(octet, 2)) for octet in octets)
                ips.append(ip_address)

        return ips

    def list_devices(self, s_ip, version):
        node_ids = send_commands_ip(["routing_tree"], radio_ip=s_ip, params=[[]])
        ips = self.node_id_to_ip(node_ids, version)
        return ips, node_ids

    def find_camera_streams_temp(self, iplist, idlist):
        cameras = []
        for iip, iid in zip(iplist, idlist):
            devices = send_commands_ip(["read_client_list"], radio_ip=iip, params=[[]])
            filtered_devices = [device for device in devices if device['ip'] not in iplist]
            for device in filtered_devices:
                ip = device['ip']
                try:
                    response = requests.get(f"http://{ip}", timeout=3)
                    if response.headers['Server'] != "IPCamera-Webs":
                        continue
                except Exception as e:
                    continue

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

    def net_status(self, radio_ip):
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
                        pair = tuple(sorted([nodeFrom, nodeTo]))
                        if pair in min_snr:
                            min_snr[pair] = min(min_snr[pair], snr)
                        else:
                            min_snr[pair] = snr

            snr_res = [{"id1": k[0], "id2": k[1], "snr": v} for k, v in min_snr.items()]
            return snr_res

        response = send_commands_ip(["streamscape_data"], radio_ip, [[]])
        return extract_snr(response)

    def get_device_battery_percent(self, ip: str) -> dict[str, str]:
        battery_percent = send_commands_ip(["battery_percent"], ip, params=[[]])[0]
        battery_percent = str(round(float(battery_percent)))
        return {"percent": battery_percent}

    def get_batteries(self, radio_ip, radio_ips):
        percents = []
        methods = [["battery_percent"] for _ in range(len(radio_ips))]
        params = [[[]] for _ in range(len(radio_ips))]

        battery_percents = read_from_multiple(radio_ip, radio_ips, methods, params)
        result = [{"ip": ip, "percent": str(round(float(percent[0])))} for ip, percent in
                  zip(radio_ips, battery_percents)]
        result_new_format = {d['ip']: d['percent'] for d in result}
        return result, result_new_format

    @staticmethod
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

    def set_ptt_groups_impl(self, radio_ip, ips, nodelist, num_groups, statuses):
        group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(num_groups)]
        methods = ["ptt_mcast_group"] * len(group_ips) + ["setenvlinsingle"]
        params = group_ips + ["ptt_mcast_group"]
        send_commands_ip(methods=methods, radio_ip=radio_ip, params=params, bcast=1, nodelist=nodelist)

        ptt_settings = []
        for status in statuses:
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
            send_commands_ip(["ptt_active_mcast_group"], radio_ip=radio_ip, params=[ptt_settings[ii]], bcast=1,
                             nodelist=[nodelist[ii]])

        send_commands_ip(["setenvlinsingle"], radio_ip=radio_ip, params=[["ptt_active_mcast_group"]], bcast=1,
                         nodelist=nodelist)

    def set_label_id(self, radio_ip, node_id, label, nodelist):
        current_names = send_commands_ip(["node_labels"], radio_ip, params=[[]])
        current_names[str(node_id)] = label
        current_names = json.dumps(current_names)
        res = send_save_node_label(radio_ip, current_names, nodelist)
        return res[0][0]['result'] == ['']

    def get_basic_set(self, radio_ip):
        methods = ["freq", "bw", "power_dBm", "nw_name", "enable_max_power"]
        params = [[]] * 5
        res = send_commands_ip(methods, radio_ip, params)

        enable_max = int(res[4][0])
        power = "Enable Max Power" if enable_max else str(res[2][0])

        return {
            "set_net_flag": [],
            "frequency": float(res[0][0]),
            "bw": float(res[1][0]),
            "net_id": res[3][0],
            "power_dBm": power
        }

    def set_basic_settings(self, radio_ip, nodelist, settings):
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
            response = send_commands_ip(methods=methods, radio_ip=radio_ip, params=params, bcast=1, nodelist=nodelist)
        else:
            response = send_commands_ip(methods=methods, radio_ip=radio_ip, params=params)

        return response

    def get_version(self, radio_ip: str):
        response = send_commands_ip(methods=["build_tag"], radio_ip=radio_ip, params=[[]])[0]
        return 4 if "v4" in response else 5
