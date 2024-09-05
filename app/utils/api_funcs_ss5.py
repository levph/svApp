import requests
import json

from requests import Timeout

from utils.send_commands import SessionManager
from typing import Optional
from utils.fa_models import Credentials, NodeNames, IpCredentials, ErrorResponse, Status, LogInResponse, NodeID, \
    NetDataMsg, SocketMsg, Interval


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
        self.known_batteries: dict[str, str] = {}

    def log_in(self, ip_creds: IpCredentials) -> LogInResponse | ErrorResponse:

        # extract ip from input
        ip = ip_creds.radio_ip
        creds = Credentials()

        # attempt login if credentials were supplied
        if ip_creds.username and ip_creds.password:
            creds.username = ip_creds.username
            creds.password = ip_creds.password
            if not self.session_manager.log_in(radio_ip=ip, creds=creds):
                raise ErrorResponse(msg="Incorrect Credentials", status_code=401)
            # global credentials in session_manager are set now

        # gather initial data
        try:
            version = self.get_version(ip)

            [ip_list, node_list] = self.list_devices(ip, version)

            # names are not dynamic, saved in device flash
            nodes_names = self.get_radio_label(ip)

            self.session_manager.set_version(version)

            statusim = self.get_ptt_groups(ip_list, node_list, nodes_names)
        except (Timeout, TimeoutError):
            print(f"Invalid IP")
            raise ErrorResponse(msg="Timeout. Incorrect computer/radio IP")
        except PermissionError as e:
            # TODO: check if we get Permission error or just exception
            print(f"This device is password protected. Please log-in")
            return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 1})
        except Exception as e:
            if "Authentication error" in e.args[0]:
                print(f"This device is password protected. Please log-in")
                return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 1})
            else:
                raise ErrorResponse(msg=f"Unknown Error: {e}")

        self.radio_ip = ip
        self.node_names = nodes_names
        self.node_list = node_list
        self.statusim = statusim
        self.ip_list = ip_list
        self.version = version
        self.credentials = creds

        return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 0})

    def log_out(self):

        self.radio_ip: None
        self.session_manager = SessionManager()
        self.node_list = []
        self.ip_list = []
        self.node_names = {}
        self.statusim = []
        self.version = 5  # default
        self.cam_data = None
        self.credentials = None
        self.net_interval = 2
        self.known_batteries = {}

        return {"Success"}

    def get_silvus_gui_url(self) -> str:
        return f"http://{self.radio_ip}"

    def set_label(self, node: NodeID) -> set[str]:
        res = self.set_label_id(self.radio_ip, node.id, node.label, self.node_list)
        self.node_names[node.id] = node.label

        return {"Success"} if res else {"Fail"}

    async def get_net_data(self):
        # TODO:
        """
        only update globally in the end
        use classes instead of complicated messages
        documentation
        :return:
        """
        try:
            known_batteries = self.known_batteries
            statusim = self.statusim
            # old_ip_list = self.ip_list.copy()
            ip_list, node_list = self.list_devices(self.radio_ip, self.version)
            new_ips, new_ids = [], []

            change_flag = False
            # check if there was change in iplist
            if set(self.ip_list) != set(ip_list):
                change_flag = True
                new_stuff = [(ip, iid) for ip, iid in zip(ip_list, node_list) if ip not in self.ip_list]
                if new_stuff:
                    new_ips, new_ids = zip(*new_stuff)
                    new_ips, new_ids = list(new_ips), list(new_ids)

                new_statusim = []
                if new_ips:
                    new_statusim = self.get_ptt_groups(new_ips, new_ids, self.node_names)

                known_batteries = {ip: percent for ip, percent in known_batteries.items() if
                                   ip in ip_list}
                statusim = [status for status in statusim if status.ip in ip_list] + new_statusim

            snrs = []
            if len(self.ip_list) > 1:
                snrs = self.net_status()

            for status in statusim:
                if status.ip in known_batteries:
                    status.percent = known_batteries[status.ip]

            msg = NetDataMsg(device_list=statusim, snr_list=snrs)

            self.set_statusim(statusim)
            self.set_batteries(known_batteries)
            self.set_ip_list(ip_list)
            self.set_node_list(node_list)

            return SocketMsg(type="net_data", data=msg, has_changed=change_flag)
        except Exception as e:
            raise ErrorResponse(msg=f"Error in fetching net data: {str(e)}")

    def set_node_list(self, nodelist: list[int]):
        self.node_list = nodelist

    def set_ip_list(self, iplist: list[str]):
        self.ip_list = iplist

    def set_batteries(self, batteries: dict[str, str]):
        self.known_batteries = batteries

    def set_statusim(self, statusim: list[Status]):
        self.statusim = statusim

    def get_interval(self) -> Interval:
        return Interval(value=self.net_interval)

    def change_interval(self, interval: Interval):
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

    def get_radio_label(self, radio_ip):
        # TODO: check message output
        labels = self.session_manager.send_commands_ip(methods=["node_labels"], radio_ip=radio_ip, params=[[]])
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
        # TODO: check output
        node_ids = self.session_manager.send_commands_ip(methods=["routing_tree"], radio_ip=s_ip, params=[[]])
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

    def net_status(self):
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

        response = self.session_manager.send_commands_ip(methods=["streamscape_data"], radio_ip=self.radio_ip,
                                                         params=[[]])
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

    def get_ptt_groups(self, ips: list[str], ids: list[int], names: dict[int, str]):
        group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(15)]
        statuses = [[] for _ in range(len(ips))]
        global_max_group = 0
        for radio_index, radio_ip in enumerate(ips):
            # TODO: check output
            ptt_groups = self.session_manager.send_commands_ip(methods=["ptt_active_mcast_group"], radio_ip=radio_ip,
                                                               params=[[]],
                                                               param_flag=1)[0]
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
            if iid in names:
                name = names[iid]
            else:
                name = ip
            # TODO: check that:
            res.append(Status(ip=ip, id=iid, status=status, name=name, percent="-1"))

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

    def set_label_id(self, radio_ip: str, node_id: int, label: str, nodelist: list[int]) -> bool:
        current_names = self.session_manager.send_commands_ip(methods=["node_labels"], radio_ip=radio_ip, params=[[]])
        current_names[str(node_id)] = label
        current_names = json.dumps(current_names)
        res = self.session_manager.send_save_node_label(radio_ip, current_names, nodelist)
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

        # TODO: check if i need to take response[0] or like this
        response = self.session_manager.send_commands_ip(methods=["freq"], radio_ip="172.20.241.202", params=[[]])

        return 4 if "v4" in response else 5
