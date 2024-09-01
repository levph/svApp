import random

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional
from fa_models import BasicSettings, PttData, RadioIP, Credentials, NodeID, Interval, LogInResponse, ErrorResponse, \
    IpCredentials
import json
from requests.exceptions import Timeout

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173"
]

app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

# global variables
RADIO_IP = None  # string
NODE_LIST = [None]  # int
IP_LIST = [None]  # strings
NODE_NAMES = [None]
STATUSIM = [None]
VERSION = 5  # assume 5
CAM_DATA = None
CREDENTIALS = None

### CHOOSE NET UPDATE INTERVAL IN SECONDS
NET_INTERVAL: int = 2

### CHOOSE AMOUNT OF DEVICES (MAX 40)
NUM_DEVICES: int = 2

# Create a lock
lock = asyncio.Lock()


@app.get("/ip")
def find_ip():
    global RADIO_IP, VERSION

    RADIO_IP = "172.20.238.213"
    result = random.choice([-1, 0, 1])
    # fail
    if result == -1:
        raise ErrorResponse(msg="Error Message")
    elif result == 0:
        return LogInResponse(type="Success", msg={"ip": RADIO_IP, "is_protected": 1})
    else:
        return LogInResponse(type="Success", msg={"ip": RADIO_IP, "is_protected": 0})


def setup():
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, NODE_NAMES, STATUSIM, NUM_DEVICES
    [RADIO_IP, VERSION] = ["172.20.238.213", 4]

    [IP_LIST, NODE_LIST] = [
        ["172.20.238.213", "172.20.241.202", "172.20.123.123", "172.20.101.112", "172.20.208.99", "172.20.71.67",
         "172.20.94.103", "172.20.1.250", "172.20.83.30", "172.20.179.212", "172.20.23.206", "172.20.192.230",
         "172.20.181.146", "172.20.124.179", "172.20.241.182", "172.20.19.39", "172.20.72.37", "172.20.36.110",
         "172.20.84.201", "172.20.94.201", "172.20.57.137", "172.20.6.128", "172.20.5.146", "172.20.148.143",
         "172.20.139.53", "172.20.9.42", "172.20.210.154", "172.20.97.208", "172.20.111.159", "172.20.231.32",
         "172.20.225.76", "172.20.15.91", "172.20.35.79", "172.20.221.203", "172.20.77.53", "172.20.122.82",
         "172.20.249.45", "172.20.29.229", "172.20.234.16", "172.20.88.240"],
        [65535, 64433, 65534, 65533, 13048, 43550, 46378, 65317, 15225, 17677, 27828, 53743, 48413, 61683, 47019,
         39967, 55708, 29787, 7228, 37755, 46722, 14253, 56980, 26682, 39034, 15680, 11283, 8446, 64255, 20343,
         56705, 33389, 44419, 63570, 31716, 10854, 7180, 80, 41137, 6767]
    ]

    ####### HERE YOU CAN CHANGE HOW MANY DEVICES TO CHOOSE ####
    IP_LIST = IP_LIST[:NUM_DEVICES]
    NODE_LIST = NODE_LIST[:NUM_DEVICES]

    # names are not dynamic, saved in device flash
    NODE_NAMES = {"ids": NODE_LIST, "names": [f"radio{i}" for i in range(len(IP_LIST))]}

    STATUSIM = [
        {
            "ip": IP_LIST[i],
            "id": NODE_LIST[i],
            "status": [1] + [0] * 15,
            "name": NODE_NAMES["names"][i]
        }
        for i in range(len(IP_LIST))
    ]


@app.post("/log-in")
def log_in(ip_creds: IpCredentials):
    """
    This method is called from log-in screen. Find radio IP and whether it is protected or not.
    Updates relevant global variables.
    :return: json with type and msg fields
    """
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, NODE_NAMES, STATUSIM

    # extract ip from input
    ip = ip_creds.radio_ip

    setup()
    protected_flag = 0

    # attempt login if credentials were supplied
    if ip_creds.username and ip_creds.password:
        if ip_creds.username != "admin" or ip_creds.password != "Noam1":
            raise ErrorResponse(msg="Incorrect Credentials", status_code=401)

    # if no credentials and different IP, randomly draw if it's protected
    elif ip != RADIO_IP:
        if ip not in IP_LIST:
            raise ErrorResponse(msg="IP doesn't exist")
        protected_away = random.choice([True, False])
        if protected_away:
            return LogInResponse(type="Success", msg={"ip": ip, "is_protected": 1})

    RADIO_IP = ip
    return LogInResponse(type="Success", msg={"ip": RADIO_IP, "is_protected": 0})


@app.post("/start-up")
def start_up():
    """
    This method is called from log-in screen. Find radio IP and whether it is protected or not.
    Updates relevant global variables.
    :return: json with type and msg fields
    """
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, NODE_NAMES, STATUSIM, NUM_DEVICES
    try:
        response = {"type": None, "msg": None}
        [RADIO_IP, VERSION] = ["172.20.238.213", 4]

        [IP_LIST, NODE_LIST] = [
            ["172.20.238.213", "172.20.241.202", "172.20.123.123", "172.20.101.112", "172.20.208.99", "172.20.71.67",
             "172.20.94.103", "172.20.1.250", "172.20.83.30", "172.20.179.212", "172.20.23.206", "172.20.192.230",
             "172.20.181.146", "172.20.124.179", "172.20.241.182", "172.20.19.39", "172.20.72.37", "172.20.36.110",
             "172.20.84.201", "172.20.94.201", "172.20.57.137", "172.20.6.128", "172.20.5.146", "172.20.148.143",
             "172.20.139.53", "172.20.9.42", "172.20.210.154", "172.20.97.208", "172.20.111.159", "172.20.231.32",
             "172.20.225.76", "172.20.15.91", "172.20.35.79", "172.20.221.203", "172.20.77.53", "172.20.122.82",
             "172.20.249.45", "172.20.29.229", "172.20.234.16", "172.20.88.240"],
            [65535, 64433, 65534, 65533, 13048, 43550, 46378, 65317, 15225, 17677, 27828, 53743, 48413, 61683, 47019,
             39967, 55708, 29787, 7228, 37755, 46722, 14253, 56980, 26682, 39034, 15680, 11283, 8446, 64255, 20343,
             56705, 33389, 44419, 63570, 31716, 10854, 7180, 80, 41137, 6767]
        ]

        ####### HERE YOU CAN CHANGE HOW MANY DEVICES TO CHOOSE ####
        IP_LIST = IP_LIST[:NUM_DEVICES]
        NODE_LIST = NODE_LIST[:NUM_DEVICES]

        # names are not dynamic, saved in device flash
        NODE_NAMES = {"ids": NODE_LIST, "names": [f"radio{i}" for i in range(len(IP_LIST))]}

        STATUSIM = [
            {
                "ip": IP_LIST[i],
                "id": NODE_LIST[i],
                "status": [1] + [0] * 15,
                "name": NODE_NAMES["names"][i]
            }
            for i in range(len(IP_LIST))
        ]

        response["type"] = "Success"
        response["msg"] = {"ip": RADIO_IP, "is_protected": 0}

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log-out")
def log_out():
    """
    Delete type of method to finish current session.
    will zeroize global variables and finish secure session if it exists
    :return: string to indicate successful exit
    """
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, CAM_DATA, CREDENTIALS
    try:

        NODE_LIST = IP_LIST = [None]

        # delete all global variables
        RADIO_IP = VERSION = CAM_DATA = CREDENTIALS = None

        return "Success"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-radio-ip")
def set_radio_ip(ip: RadioIP):
    """
    set radio ip
    :param ip:
    :return:
    """
    global RADIO_IP, NODE_LIST, IP_LIST
    try:
        # set radio IP to input ip
        RADIO_IP = ip.radio_ip

        # perform startup method (which will test connectivity and update settings)
        res = start_up()

        if res["type"] == "Fail":
            # delete current session if wrong IP
            log_out()

        # return result which can be successful or error
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-interval")
def get_interval():
    try:
        global NET_INTERVAL
        interval = Interval(value=NET_INTERVAL)
        return interval
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/data-interval")
def change_interval(interval: Interval):
    """
    This method changes the net-data update interval
    :param interval:
    :return:
    """
    global NET_INTERVAL
    try:
        NET_INTERVAL = int(interval.value)
        return {f"net-data interval set to {interval}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/device-battery")
async def device_battery(device_id: int = None):
    """
    This method returns battery of a given device
    :return:
    """
    try:
        if device_id is None:
            raise Exception("No device id supplied")
        return {"percent": random.choice([-2, -1, 15, 30, 80]), "device_id": device_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-label")
def set_label(node: NodeID):
    """
    This method sets label for given device id
    :return:
    """
    global RADIO_IP, NODE_LIST
    try:
        # TODO: implement
        res = 1
        return {"Success"} if res else {"Fail"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/net-data")
async def net_data():
    """
    This method returns global variables
    assumes at least one radio is connected! will be fixed later
    :return:
    """
    global IP_LIST, NODE_LIST, VERSION, RADIO_IP, NODE_NAMES, STATUSIM

    try:

        snrs = [
            {
                "id1": str(NODE_LIST[i]),
                "id2": str(NODE_LIST[i + 1]),
                "snr": random.randint(80, 100)
            }
            for i in range(len(NODE_LIST) - 1)
        ]

        ip_id_dict = STATUSIM

        msg = {
            "device_list": ip_id_dict,
            "snr_list": snrs,
            "has_changed": False
        }

        return json.dumps({"type": "net_data", "data": msg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/basic-settings")
async def basic_settings(settings: Optional[BasicSettings] = None):
    """
    :return:
    """
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


@app.get("/get-battery")
async def get_battery():
    """
    routine method to return battery percentage of each device in the network
    :return:
    ips_batteries - list of radio_ip - bettery status
    """
    global RADIO_IP, NODE_LIST, IP_LIST

    ips_batteries = [
        {
            "ip": IP_LIST[i],
            "percent": str(random.randint(10, 100))
        }
        for i in range(len(IP_LIST))
    ]

    print("Updated battery status")
    print(ips_batteries)
    return json.dumps({"type": "battery", "data": ips_batteries})


async def send_messages(websocket: WebSocket, interval, func):
    """Send messages every 'interval' seconds."""
    # global BAT_INTERVAL, NET_INTERVAL
    global NET_INTERVAL
    while True:
        res = await func()
        await websocket.send_text(f"{res}")
        # interval = BAT_INTERVAL if func == get_battery else DATA_INTERVAL
        interval = interval if func == get_battery else NET_INTERVAL
        await asyncio.sleep(interval)


# TODO: add parameters to ws (so user could control frequency)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    This method automates routine data sending to front
    such as battery percentages every X seconds, network SNRs, update global variables...
    :param websocket:
    :return:
    """

    global NET_INTERVAL

    await websocket.accept()
    try:

        # Create tasks for different message frequencies
        task1 = asyncio.create_task(send_messages(websocket, 300, get_battery))
        # task2 = asyncio.create_task(send_messages(websocket, 2, update_vars))
        task3 = asyncio.create_task(send_messages(websocket, NET_INTERVAL, net_data))

        # Wait for both tasks to complete (they won't, unless there's an error)
        await asyncio.gather(task1, task3)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


@app.post("/get-ptt-groups")
async def get_ptt_group():
    try:
        ptt_groups = []
        return ptt_groups
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-ptt-groups")
def set_ptt_group(ptt_data: PttData):
    try:
        global RADIO_IP, NODE_LIST, STATUSIM

        # update STATUSIM global var
        for status in STATUSIM:
            if status["ip"] in ptt_data.ips:
                status["status"] = ptt_data.statuses[ptt_data.ips.index(status["ip"])]

        return {"message": "ptt group settings set succesfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-camera-links")
async def get_camera():
    """
    This endpoint will return the stream URLs of existing cameras in network
    existing URLs include main-stream, sub-stream and audio-stream
    :return:
    """
    global IP_LIST
    try:

        streams = [
            {
                "camera": {
                    "ip": "172.20.245.66",
                    "device_ip": "172.20.241.202",
                    "device_id": 64433,
                    "main_stream": {
                        "uri": "rtsp://172.20.245.66:554/av0_0",
                        "audio": 1
                    },
                    "sub_stream": {
                        "uri": "rtsp://172.20.245.66:554/av0_1",
                        "audio": 1
                    }
                }
            },
            {
                "camera": {
                    "ip": "172.20.245.67",
                    "device_ip": "172.20.238.213",
                    "device_id": 65535,
                    "main_stream": {
                        "uri": "rtsp://172.20.245.67:554/av0_0",
                        "audio": 1
                    },
                    "sub_stream": {
                        "uri": "rtsp://172.20.245.67:554/av0_1",
                        "audio": 1
                    }
                }
            }
        ]

        msg = "Success"
        return {"message": msg, "data": streams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
