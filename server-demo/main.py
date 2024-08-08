import random
import asyncio
import json
from typing import Optional, List, Dict, TypedDict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fa_models import BasicSettings, PttData, RadioIP, Credentials, NodeID, Interval
from requests.exceptions import Timeout
from dataclasses import dataclass


class SubDevice(TypedDict):
    ip: str
    id: int
    status: list[int]
    name: str
    percent: str


@dataclass
class Device:
    """Class for keeping track of a silvus radio params"""
    ip: str
    saved_labels: dict[str, list[str]]
    devices: list[SubDevice]
    # cameras:
    # credentials: List[str, str]


class MeshNetworkAPI:
    def __init__(self):
        self.app = FastAPI()
        self.setup_middleware()
        self.lock = asyncio.Lock()

        self.radio = Device
        self.version = 5
        self.cam_data = None
        self.net_interval = 2
        self.num_devices = 2

        self.setup_routes()

    def setup_middleware(self):
        origins = ["http://localhost", "http://localhost:5173"]
        self.app.add_middleware(CORSMiddleware,
                                allow_origins=origins,
                                allow_credentials=True,
                                allow_methods=["*"],
                                allow_headers=["*"])

    def setup_routes(self):
        self.app.post("/start-up")(self.start_up)
        self.app.post("/log-out")(self.log_out)
        self.app.post("/log-in")(self.log_in)
        self.app.post("/set-radio-ip")(self.set_radio_ip)
        self.app.post("/change-interval")(self.change_interval)
        self.app.post("/set-label")(self.set_label)
        self.app.get("/net-data")(self.net_data)
        self.app.post("/basic-settings")(self.basic_settings)
        self.app.get("/get-battery")(self.get_battery)
        self.app.websocket("/ws")(self.websocket_endpoint)
        self.app.post("/get-ptt-groups")(self.get_ptt_group)
        self.app.post("/set-ptt-groups")(self.set_ptt_group)
        self.app.get("/get-camera-links")(self.get_camera)

    def start_up(self):
        try:
            response = {"type": None, "msg": None}
            radio_ip, version = "172.20.238.213", 4

            ip_list, node_list = [
                ["172.20.238.213", "172.20.241.202", "172.20.123.123", "172.20.101.112", "172.20.208.99",
                 "172.20.71.67",
                 "172.20.94.103", "172.20.1.250", "172.20.83.30", "172.20.179.212", "172.20.23.206", "172.20.192.230",
                 "172.20.181.146", "172.20.124.179", "172.20.241.182", "172.20.19.39", "172.20.72.37", "172.20.36.110",
                 "172.20.84.201", "172.20.94.201", "172.20.57.137", "172.20.6.128", "172.20.5.146", "172.20.148.143",
                 "172.20.139.53", "172.20.9.42", "172.20.210.154", "172.20.97.208", "172.20.111.159", "172.20.231.32",
                 "172.20.225.76", "172.20.15.91", "172.20.35.79", "172.20.221.203", "172.20.77.53", "172.20.122.82",
                 "172.20.249.45", "172.20.29.229", "172.20.234.16", "172.20.88.240"],
                [65535, 64433, 65534, 65533, 13048, 43550, 46378, 65317, 15225, 17677, 27828, 53743, 48413, 61683,
                 47019,
                 39967, 55708, 29787, 7228, 37755, 46722, 14253, 56980, 26682, 39034, 15680, 11283, 8446, 64255, 20343,
                 56705, 33389, 44419, 63570, 31716, 10854, 7180, 80, 41137, 6767]
            ]

            ip_list = ip_list[:self.num_devices]
            node_list = node_list[:self.num_devices]

            node_names = {"ids": node_list, "names": [f"radio{i}" for i in range(len(ip_list))]}

            devices = [
                SubDevice(ip=ip_list[i],
                          id=node_list[i],
                          status=[1] + [0] * 15,
                          name=node_names["names"][i],
                          percent="100")

                for i in range(len(ip_list))
            ]

            self.radio = Device(ip=radio_ip, saved_labels=node_names, devices=devices)

            response["type"] = "Success"
            response["msg"] = {"ip": radio_ip, "is_protected": 0}

            return response

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def log_out(self):
        try:
            self.node_list = self.ip_list = [None]
            self.radio_ip = self.version = self.cam_data = self.credentials = None
            return "Success"
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def log_in(self, credentials: Credentials):
        try:
            self.credentials = credentials
            res = 1
            if res:
                msg = "Success"
                _ = self.start_up()
            else:
                self.log_out()
                msg = "Fail"
            return msg
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def set_radio_ip(self, ip: RadioIP):
        try:
            self.radio_ip = ip.radio_ip
            res = self.start_up()
            if res["type"] == "Fail":
                self.log_out()
            return res
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def change_interval(self, interval: Interval):
        self.net_interval = interval.interval

    def set_label(self, node: NodeID):
        try:
            res = 1
            return {"Success"} if res else {"Fail"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def net_data(self):
        try:
            snrs = [
                {
                    "id1": str(self.node_list[i]),
                    "id2": str(self.node_list[i + 1]),
                    "snr": random.randint(80, 100)
                }
                for i in range(len(self.node_list) - 1)
            ]

            ip_id_dict = self.statusim

            msg = {
                "device_list": ip_id_dict,
                "snr_list": snrs,
                "has_changed": False
            }

            return json.dumps({"type": "net_data", "data": msg})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def basic_settings(self, settings: Optional[BasicSettings] = None):
        try:
            if settings:
                response = "Success"
                msg = {"Error"} if "error" in response else {"Success"}
                return msg
            else:
                response = {
                    "set_net_flag": [],
                    "frequency": 2480.0,
                    "bw": 2.5,
                    "net_id": "noam_ha_melech",
                    "power_dBm": "enable_max"
                }
                return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_battery(self):
        ips_batteries = [
            {
                "ip": self.ip_list[i],
                "percent": str(random.randint(10, 100))
            }
            for i in range(len(self.ip_list))
        ]

        print("Updated battery status")
        print(ips_batteries)
        return json.dumps({"type": "battery", "data": ips_batteries})

    async def send_messages(self, websocket: WebSocket, interval, func):
        while True:
            res = await func()
            await websocket.send_text(f"{res}")
            await asyncio.sleep(interval)

    async def websocket_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        try:
            task1 = asyncio.create_task(self.send_messages(websocket, 300, self.get_battery))
            task3 = asyncio.create_task(self.send_messages(websocket, self.net_interval, self.net_data))
            await asyncio.gather(task1, task3)
        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await websocket.close()

    async def get_ptt_group(self):
        try:
            ptt_groups = []
            return ptt_groups
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
