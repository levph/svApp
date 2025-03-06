import asyncio
import json
import time

import requests
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from requests import Timeout
from utils.fa_models import *
from utils.send_commands import SessionManager
from utils.offline_manager import OfflineDevicesManager
from utils.radio_status_database import StatusDatabase


class RadioManager:

    @classmethod
    def default_version(cls) -> int:
        return 5

    @classmethod
    def default_net_interval(cls) -> int:
        return 2

    def __init__(self):
        self._radio_ip: Optional[str] = None
        self._session_manager: SessionManager = SessionManager()
        self._offline_devices: OfflineDevicesManager = OfflineDevicesManager()
        self._hidden_devices: list[int] = []
        self._node_list: list[int] = []
        self._node_names: dict[int, str] = {}
        self._statusim: StatusDatabase = StatusDatabase()
        self._version: int = self.default_version()
        self.cam_data = None
        self._credentials: Optional[Credentials] = None
        self._net_interval: int = self.default_net_interval()
        self._known_batteries: dict[str, str] = {}
        self._hidden_flag: bool = False

    @property
    def hidden_devices(self) -> HiddenDevices:
        """
        List of currently tracked hidden devices.

        Returns:
            HiddenDevices: BaseModel object with hidden devices list
        """
        return HiddenDevices(device_list=self._statuses_by_id(self._hidden_devices))

    def _attempt_log_in(self, ip: str, username: str, password: str) -> Credentials:
        # attempt login if credentials were supplied
        creds = Credentials()

        if username and password:
            creds.username = username
            creds.password = password
            if not self._session_manager.log_in(radio_ip=ip, creds=creds):
                raise ErrorResponse(msg="Incorrect Credentials", status_code=401)
            # global credentials in session_manager are set now

        return creds

    def _init_network_params(self, ip):
        try:
            version = self.get_version(ip)

            [ip_list, node_list] = self.list_devices(ip, version)

            # names are not dynamic, saved in device flash
            nodes_names = self.get_radio_label(ip)

            self._session_manager.set_version(version)

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

        # set members if successful
        self._node_names = nodes_names
        self._statusim += statusim
        self._version = version

    def log_in(self, ip_creds: IpCredentials) -> LogInResponse | ErrorResponse:
        """
        Attempt login to device,
        if successful, get all initial data from network
        :param ip_creds:
        :return:
        """
        # extract ip from input
        ip = ip_creds.radio_ip

        creds = self._attempt_log_in(ip, ip_creds.username, ip_creds.password)

        # gather initial data
        self._init_network_params(ip)

        self._radio_ip = ip
        self._credentials = creds

        return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 0})

    def log_out(self) -> None:

        self._radio_ip: None
        self._session_manager = SessionManager()
        self._node_names = {}
        self._statusim = None
        self._version = self.default_version()
        self.cam_data = None
        self._credentials = None
        self._net_interval = self.default_net_interval()
        self._known_batteries = {}

    def hide(self, device_id: int) -> None:
        """

        :param device_id:
        :return:
        """
        if device_id not in self._statusim.nodes_id:
            raise HTTPException(status_code=404, detail=f"Node {device_id} doesn't exist")

        self._hidden_devices.append(device_id)
        self._hidden_flag = True
        return

    def unhide(self, device_ids: list[int]) -> None:
        """
        Unhides device by id
        :param device_ids:
        :param self:
        :return:
        """
        self._hidden_devices = [device for device in self._hidden_devices if device not in device_ids]
        self._hidden_flag = True

    def save_topology(self, topology: Topology):
        """
        Save topology to device flash memory
        :param topology:
        :return:
        """
        node_db = {}
        for node in topology.device_list:
            node_db[str(node.id)] = {"pos": {"x": node.pos[0], "y": node.pos[1]}}

        res = self._session_manager.send_topology(self._radio_ip, action="save", node_db=node_db)

        return {"Success"} if res else {"Fail"}

    def _format_topology(self, node_db: dict) -> Topology:
        """
        Parse topology from device flash memory
        :param node_db:
        :return:
        """
        node_list = []
        for node_id, pos in node_db.items():
            node_ip = self.node_id_to_ip([int(node_id)], self._version)[0]
            node_list.append(NodePos(id=int(node_id), ip=node_ip, pos=(pos["pos"]["x"], pos["pos"]["y"])))

        return Topology(device_list=node_list)

    def get_topology(self) -> Topology:
        """
        Get topology of network
        :return:
        """
        # load saved topology from connected device memory
        res = self._session_manager.send_topology(self._radio_ip, action="load")

        # if no topology was found
        if not res:
            return Topology(device_list=[])

        node_db = res["nodeDB"]
        return self._format_topology(node_db)

    def get_silvus_gui_url(self) -> str:
        """
        Return URL of technician mode
        :return:
        """
        return GUI_URL.format(self._radio_ip)

    def set_label(self, node: NodeID) -> None:
        """
        Change label of single device in current radio
        :param node:
        :return:
        """
        res = self.set_label_id(node.id, node.label)

        if not res:
            raise HTTPException(status_code=404, detail=f"Node {node.id} doesn't exist")

        # update name in all variables
        self._node_names[node.id] = node.label
        self._statusim[node.id].name = node.label

    async def run_task(self, websocket: WebSocket, func, interval: int):
        """Run the specified function at a given interval and send results via WebSocket."""
        while True:
            result = await func()  # Run the function
            await websocket.send_text(result.json())  # Send the result over WebSocket
            interval = interval if func == self.get_battery else self._net_interval
            await asyncio.sleep(interval)  # Wait for the next interval

    async def websocket_handler(self, websocket: WebSocket):
        """Handles the WebSocket connection and runs tasks at intervals."""
        await websocket.accept()
        try:
            # Create tasks for both functions running at different intervals
            task1 = asyncio.create_task(self.run_task(websocket, self.get_battery, 300))
            task2 = asyncio.create_task(self.run_task(websocket, self.get_net_data, self._net_interval))

            # Wait for tasks to complete (they will run indefinitely unless there's an error)
            await asyncio.gather(task1, task2)
        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await websocket.close()

    async def get_net_data(self):
        """
        Retrieves and processes network data for connected devices, managing their online/offline status
        and related metrics.

        This method performs several key operations:
        1. Discovers currently connected devices on the network
        2. Tracks devices that go offline and handles reconnections
        3. Maintains battery status for known devices
        4. Collects signal-to-noise ratio (SNR) data for connected devices

        Returns:
            SocketMsg: Contains processed network data including:
                - List of all devices (online and offline)
                - SNR measurements between devices
                - Change status flag indicating network topology changes

        Raises:
            ErrorResponse: If there's an error during network data collection
        """
        try:
            # Get current state
            prev_ips = self._statusim.ips
            known_batteries = self._known_batteries.copy()
            current_statusim = self._statusim  # TODO: Understand how to copy
            net_change_flag = self._hidden_flag
            self._hidden_flag = False
            timestamp = time.time()

            # Discover current network topology
            ip_list, node_list = self.list_devices(self._radio_ip, self._version)
            current_ip_mapping = {node: ip for node, ip in zip(node_list, ip_list)}

            # remove expired ips, if any, update change flag accordingly
            net_change_flag |= self._offline_devices.delete_expired(timestamp)

            # check if there was change in iplist
            if set(prev_ips) != set(ip_list):
                net_change_flag = True
                current_statusim, known_batteries = self._process_network_changes(current_ip_mapping, current_statusim,
                                                                                  timestamp, known_batteries, prev_ips)

            # get snrs between devices
            snrs = self.net_status() if len(prev_ips) > 1 else []
            device_list = self._create_device_list(current_statusim.radios, known_batteries)
            msg = NetDataMsg(device_list=device_list, snr_list=snrs)

            self._statusim = current_statusim
            self._known_batteries = known_batteries

            return SocketMsg(type="net_data", data=msg, has_changed=net_change_flag)
        except Exception as e:
            raise ErrorResponse(msg=f"Error in fetching net data: {str(e)}")

    def _process_network_changes(self, current_ip_mapping: dict[int, str], current_statusim: StatusDatabase,
                                 timestamp: time.time, known_batteries: dict, prev_ips: list[str]) -> tuple[
        StatusDatabase, dict]:
        """
        Processes changes in network topology, handling newly connected, reconnected and disconnected devices.
        :param current_ip_mapping:
        :param current_statusim:
        :param timestamp:
        :param known_batteries:
        :return:
        """
        # extract new devices
        new_ip_mapping = {iid: ip for iid, ip in current_ip_mapping.items() if ip not in prev_ips}

        # add ips that disconnected now, change their online status to false
        self._offline_devices.add_offline_devices(current_statusim,
                                                  list(current_ip_mapping.values()), timestamp)

        if new_ip_mapping:
            back_online, new_ip_mapping = self._offline_devices.pop_reconnected(new_ip_mapping)
            current_statusim += back_online + self.get_ptt_groups(ips=list(new_ip_mapping.values()),
                                                                  ids=list(new_ip_mapping.keys()),
                                                                  names=self._node_names)

        # forget disconnected devices' batteries
        known_batteries = {ip: percent for ip, percent in known_batteries.items() if
                           ip in current_ip_mapping.values()}

        return current_statusim, known_batteries

    def _create_device_list(self, current_statusim: list[Status], known_batteries: dict) -> list[Status]:
        """
        Creates a comprehensive list of all devices with their current status.

        :param current_statusim:
        :param known_batteries:
        :return:
        """
        # add offline status to device list
        device_list = current_statusim + [offline_status for offline_status in self._offline_devices.radios]

        # TODO: handle devices better, known_batteries is ugly
        for status in device_list:
            if status.ip in known_batteries:
                status.percent = known_batteries[status.ip]

        return self._remove_hidden(device_list)

    def _remove_hidden(self, device_list: list[Status]) -> list[Status]:
        """
        removes hidden devices from device list
        :param device_list:
        :return: filtered device_list
        """
        return [device for device in device_list if device.id not in self._hidden_devices]

    def get_interval(self) -> Interval:
        return Interval(value=self._net_interval)

    def change_interval(self, interval: Interval):
        self._net_interval = int(interval.value)
        return {"message": f"net-data interval set to {interval.value}"}

    async def basic_settings(self, settings: Optional[BasicSettings]):
        if settings:
            response = self.set_basic_settings(settings)
            return {"Error"} if "error" in response else {"Success"}
        else:
            return self.get_basic_set()

    async def get_device_battery(self, device_id: int) -> dict[str, str]:
        """
        Get battery of a specific device
        :param device_id:
        :return:
        """
        if not device_id:
            raise ErrorResponse(msg="No id supplied")
        elif device_id not in self._statusim.nodes_id:
            raise ErrorResponse(msg=f"{device_id} doesn't exist")

        # find corresponding ip
        ip = self._statusim[device_id].ip

        # get battery percentage and format correctly
        battery_percent = self._session_manager.send_commands_ip(["battery_percent"], ip, params=[[]])[0]
        battery_percent = str(round(float(battery_percent)))

        # update known batteries
        self._known_batteries[ip] = battery_percent

        return {"percent": battery_percent}

    async def get_battery(self) -> SocketMsg:
        """
        WS method to get all batteries in network
        :return:
        """
        ips_batteries = self.get_batteries()
        self._known_batteries.update(ips_batteries)
        return SocketMsg(type="battery", data=ips_batteries)

    def set_ptt_groups(self, ptt_data: PttData):
        """
        Change ptt group settings of multiple devices
        :param ptt_data:
        :return:
        """
        try:
            nodes = [self._statusim[ip].id for ip in ptt_data.ips]
            self.set_ptt_groups_impl(nodelist=nodes, num_groups=ptt_data.num_groups, statuses=ptt_data.statuses)

            for ip, status in zip(ptt_data.ips, ptt_data.statuses):
                self._statusim[ip].status = status

        except Exception as e:
            raise ErrorResponse(msg=f"Error in setting PTT groups: {str(e)}")

    def set_ptt_group_master(self, ptt_data: PttDataSingle):

        status = ptt_data.status
        num_groups = len(status)
        ptt_settings = self._ptt_data_format([status])[0]
        group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(num_groups)]
        methods = ["ptt_mcast_group"] * len(group_ips) + ["setenvlinsingle", "ptt_active_mcast_group", "setenvlinsingle"]
        params = group_ips + [["ptt_mcast_group"]] + [ptt_settings] + [["ptt_active_mcast_group"]]

        self._session_manager.send_commands_ip(methods=methods, radio_ip=self._radio_ip, params=params)

        self._statusim[self._radio_ip].status = ptt_data.status

    async def get_camera_links(self):
        """
        Get links of all cameras connected in network (only tested with obscura)
        :return:
        """
        try:
            streams = self.find_camera_streams_temp()
            return {"message": "Success", "data": streams}
        except Exception as e:
            raise ErrorResponse(msg=f"Error with camera finder: {e}")

    def get_radio_label(self, radio_ip) -> dict[int, str]:
        """
        Get radio labels saved in radio flash memory
        :param radio_ip:
        :return:
        """
        labels = self._session_manager.send_commands_ip(methods=["node_labels"], radio_ip=radio_ip, params=[[]])
        ids_labels = [(int(k), v) for k, v in labels.items()]
        if not ids_labels:
            return {}

        node_names = dict(ids_labels)

        return node_names

    @staticmethod
    def node_id_to_ip_v4(id_list):
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

    def list_devices(self, s_ip, version) -> tuple[list[str], list[int]]:
        """
        Find IP and ID of every device in network
        :param s_ip:
        :param version:
        :return:
        """
        # TODO: check output
        node_ids = self._session_manager.send_commands_ip(methods=["routing_tree"], radio_ip=s_ip, params=[[]])
        ips = self.node_id_to_ip(node_ids, version)
        return ips, node_ids

    def find_camera_streams_temp(self) -> list[Camera] | ErrorResponse:
        """
        Find all cameras connected in network
        :return:
        """
        cameras = []
        num_devices = len(self._statusim.nodes_id)
        network_ips = self._statusim.ips

        methods = [["read_client_list"] for _ in range(num_devices)]
        params = [[[]] for _ in range(num_devices)]

        # get list of IPs connected to each device
        devices = self._session_manager.read_from_multiple(radio_ips=network_ips, methods=methods,
                                                           params=params)

        if len(devices) != num_devices:
            return ErrorResponse("Problem with cameras. Try again")

        for radio_devices, network_radio in zip(devices, self._statusim.radios):
            if radio_devices == [-1]:
                continue

            # filter ips already existing in network
            filtered_devices = [device for device in radio_devices if device['ip'] not in network_ips]
            for device in filtered_devices:
                ip = device['ip']
                try:
                    # funny check to see if it's a camera
                    response = requests.get(f"http://{ip}", timeout=3)
                    if response.headers['Server'] != "IPCamera-Webs":  # OBSCURA camera stamp
                        continue  # onwards to next device if not camera
                except Exception as e:
                    continue

                main_stream = CamStream(uri=f"rtsp://{ip}:554/av0_0", audio=1)
                sub_stream = CamStream(uri=f"rtsp://{ip}:554/av0_1", audio=1)
                camera = Camera(ip=ip, device_ip=network_radio.ip, device_id=network_radio.id, main_stream=main_stream,
                                sub_stream=sub_stream)
                cameras.append(camera)

        return cameras

    def net_status(self) -> list[dict]:
        """
        Return list of snrs between devices in network
        :return:
        """

        def extract_snr(data):
            min_snr = {}
            for node in data:
                if int(node["id"]) in self._hidden_devices:
                    continue
                for adjacency in node.get("adjacencies", []):
                    nodeTo = adjacency["nodeTo"]
                    nodeFrom = adjacency["nodeFrom"]
                    # ignore edges containing hidden devices
                    if int(nodeTo) in self._hidden_devices or int(nodeFrom) in self._hidden_devices:
                        continue
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

        response = self._session_manager.send_commands_ip(methods=["streamscape_data"], radio_ip=self._radio_ip,
                                                          params=[[]])
        return extract_snr(response)

    def get_batteries(self) -> dict[str, str]:
        """
        Broadcast battery sampling to entire network and return current percentages
        :return:
        """
        num_devices = len(self._statusim.nodes_id)
        methods = [["battery_percent"] for _ in range(num_devices)]
        params = [[[]] for _ in range(num_devices)]

        battery_percents = self._session_manager.read_from_multiple(radio_ips=self._statusim.ips, methods=methods,
                                                                    params=params)
        result = {ip: str(round(float(percent[0]))) for ip, percent in
                  zip(self._statusim.ips, battery_percents)}
        return result

    def get_ptt_groups(self, ips: list[str], ids: list[int], names: dict[int, str]):
        """
        Get full status of each device asked for!
        :param ips: list of devices ip to sample
        :param ids: list of devices id to sample
        :param names: list of names in connected device flash mem
        :return:
        """
        # group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(15)]
        statuses = [[] for _ in range(len(ips))]
        global_max_group = 0
        # parser for silvus ptt group!
        for radio_index, radio_ip in enumerate(ips):
            ptt_groups = self._session_manager.send_commands_ip(methods=["ptt_active_mcast_group"], radio_ip=radio_ip,
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
            res.append(Status(ip=ip, id=iid, status=status, name=name, is_online=True))

        return res

    @staticmethod
    def _ptt_data_format(status_list: list[list[int]]) -> list:
        ptt_settings = []
        for status in status_list:
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

        return ptt_settings

    def set_ptt_groups_impl(self, nodelist: list[int], num_groups: int, statuses):
        """
        Helper to set_ptt_group method. See definition in caller
        :param nodelist:
        :param num_groups:
        :param statuses:
        :return:
        """
        group_ips = [[str(i), f"239.0.0.{10 + i}"] for i in range(num_groups)]
        methods = ["ptt_mcast_group"] * len(group_ips) + ["setenvlinsingle"]
        params = group_ips + [["ptt_mcast_group"]]
        self._session_manager.send_commands_ip(methods=methods, radio_ip=self._radio_ip, params=params, bcast=1,
                                               nodelist=nodelist)

        ptt_settings = self._ptt_data_format(statuses)

        for ii in range(len(nodelist)):
            self._session_manager.send_commands_ip(["ptt_active_mcast_group"], radio_ip=self._radio_ip,
                                                   params=[ptt_settings[ii]], bcast=1, nodelist=[nodelist[ii]])

        res = self._session_manager.send_commands_ip(["setenvlinsingle"], radio_ip=self._radio_ip,
                                                     params=[["ptt_active_mcast_group"]], bcast=1,
                                                     nodelist=nodelist)

        return res

    def set_label_id(self, node_id: int, label: str) -> bool:
        """
        Weird implementation of changing device flash with new label -
        setting new label to device
        :param radio_ip:
        :param node_id:
        :param label:
        :param nodelist:
        :return:
        """
        current_names = self._session_manager.send_commands_ip(methods=["node_labels"], radio_ip=self._radio_ip,
                                                               params=[[]])
        current_names[str(node_id)] = label
        current_names = json.dumps(current_names)
        res = self._session_manager.send_save_node_label(self._radio_ip, current_names, self._statusim.nodes_id)
        return res[0][0]['result'] == ['']

    def get_basic_set(self) -> BasicSettings:
        """
        Get basic settings of current device
        :return:
        """
        methods = ["freq", "bw", "power_dBm", "nw_name", "enable_max_power"]
        params = [[]] * 5
        res = self._session_manager.send_commands_ip(methods=methods, radio_ip=self._radio_ip, params=params)

        enable_max = int(res[4][0])
        power = "Enable Max Power" if enable_max else str(res[2][0])

        return BasicSettings(set_net_flag=0, frequency=float(res[0][0]), bw=res[1][0], net_id=res[3][0],
                             power_dBm=power)

    def set_basic_settings(self, settings: BasicSettings):
        """
        Setting basic settings to connected device / all devices
        Forces link-distance=5000
        :param settings:
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
            response = self._session_manager.send_commands_ip(methods=methods, radio_ip=self._radio_ip, params=params,
                                                              bcast=1, nodelist=self._statusim.nodes_id)
        else:
            response = self._session_manager.send_commands_ip(methods=methods, radio_ip=self._radio_ip, params=params)

        return response

    def get_version(self, radio_ip: str):
        """
        Find out firmware version of network
        :param radio_ip:
        :return:
        """
        response = self._session_manager.send_commands_ip(methods=["build_tag"], radio_ip=radio_ip, params=[[]])[0]
        return 4 if "v4" in response else 5

    def _statuses_by_id(self, ids: list[int]):
        return [self._statusim[node_id] for node_id in ids]
