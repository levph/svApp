from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional, Dict, Any

from utils.fa_models import BasicSettings, PttData, RadioIP, Credentials, NodeID, Interval, IpCredentials, \
    LogInResponse, ErrorResponse
from utils.get_radio_ip import sniff_target_ip
from utils.api_funcs_ss5 import list_devices, net_status, find_camera_streams_temp, get_batteries, set_ptt_groups, \
    get_basic_set, set_basic_settings, get_radio_label, set_label_id, get_ptt_groups, get_device_battery, get_version
import json
from requests.exceptions import Timeout
from utils.send_commands import api_login, exit_session, set_version, set_credentials, login
import webbrowser

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

# TODO: move to session class (DataClass??)
# global variables
RADIO_IP: str = None  # string
NODE_LIST: list[int]  # int
IP_LIST: list[str]  # strings
NODE_NAMES = [None]
STATUSIM = [None]
VERSION = 5  # assume 5
CAM_DATA = None
CREDENTIALS = None
NET_INTERVAL: int = 2
KNOWN_BATTERIES: dict[str, str] = {}
# DISCONNECT_TIMEOUT = 1 TODO

# Create a lock
lock = asyncio.Lock()


@app.get("/ip")
def find_ip():
    try:
        [radio_ip, _] = sniff_target_ip()
    except Exception as e:
        print("Can't find connected device\n")
        raise ErrorResponse(msg=f"Error when scanning: {e}")

    if not radio_ip:
        print("No Radio connected.\n")
        raise ErrorResponse(msg="Can't find a connected device.")

    # RADIO_IP = radio_ip
    return LogInResponse(type="Success", msg={"ip": radio_ip, "is_protected": 0})


# TODO: fix all other start-up calling instances
@app.post("/log-in")
def log_in(ip_creds: IpCredentials):
    """
    This method is called from log-in screen. Find radio IP and whether it is protected or not.
    Updates relevant global variables.
    :return: json with type and msg fields
    """
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, NODE_NAMES, STATUSIM, CREDENTIALS

    # extract ip from input
    ip = ip_creds.radio_ip
    creds = Credentials()

    # attempt login if credentials were supplied
    if ip_creds.username and ip_creds.password:
        creds.username = ip_creds.username
        creds.password = ip_creds.password
        if not login(radio_ip=ip, creds=creds):
            raise ErrorResponse(msg="Incorrect Credentials", status_code=401)

    # gather initial data
    try:
        version = get_version(ip)

        [ip_list, node_list] = list_devices(ip, version)

        # names are not dynamic, saved in device flash
        nodes_names = get_radio_label(ip)

        set_version(version)

        statusim = get_ptt_groups(ip_list, node_list, nodes_names)
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


@app.post("/log-out")
def log_out():
    """
    Delete type of method to finish current session.
    will zeroize global variables and finish secure session if it exists
    :return: string to indicate successful exit
    """
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, CAM_DATA, CREDENTIALS
    try:

        # delete current session data
        exit_session()

        NODE_LIST = IP_LIST = [None]

        # delete all global variables
        RADIO_IP = VERSION = CAM_DATA = CREDENTIALS = None

        return "Success"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/silvus-tech-gui")
async def open_technical_system():
    """
    This method opens the silvus gui
    :return:
    """
    global RADIO_IP
    url = f"http://{RADIO_IP}"
    webbrowser.open(url, new=0, autoraise=True)


@app.post("/set-label")
def set_label(node: NodeID):
    """
    This method sets label for given device id
    :return:
    """
    global RADIO_IP, NODE_LIST, NODE_NAMES
    try:
        res = set_label_id(RADIO_IP, node.id, node.label, NODE_LIST)
        # id_label = {"ids": ids, "names": names}

        # update local node names
        if node.id in NODE_NAMES["ids"]:
            NODE_NAMES["names"][NODE_NAMES["ids"].index(node.id)] = node.label
        else:
            NODE_NAMES["ids"] += [node.id]
            NODE_NAMES["names"] += [node.label]

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
    global IP_LIST, NODE_LIST, VERSION, RADIO_IP, NODE_NAMES, STATUSIM, KNOWN_BATTERIES

    try:
        async with lock:
            old_ip_list = IP_LIST.copy()

            # update IPs and Nodes in network
            [IP_LIST, NODE_LIST] = list_devices(RADIO_IP, VERSION)
            new_ips = new_ids = []

            change_flag = False
            # if any change in devices happened
            if set(IP_LIST) != set(old_ip_list):

                # flag to alert client of topology change
                change_flag = True

                # add new devices if there are any
                new_stuff = [(ip, iid) for ip, iid in zip(IP_LIST, NODE_LIST) if ip not in old_ip_list]
                if new_stuff:
                    new_ips, new_ids = zip(*new_stuff)
                    new_ips, new_ids = list(new_ips), list(new_ids)

                # get new devices' settings
                new_statusim = []
                if new_ips:
                    new_statusim = get_ptt_groups(new_ips, new_ids, NODE_NAMES)

                # remove disconnected batteries
                KNOWN_BATTERIES = {ip: percent for ip, percent in KNOWN_BATTERIES.items() if ip in IP_LIST}

                # remove disconnected devices and add connected
                STATUSIM = [status for status in STATUSIM if status["ip"] in IP_LIST] + new_statusim

            # get snrs of new devices
            snrs = []
            if len(IP_LIST) > 1:
                snrs = net_status(RADIO_IP)

            ip_id_dict = STATUSIM

            # update percents
            for elem in ip_id_dict:
                elem["percent"] = "-1" if elem["ip"] not in KNOWN_BATTERIES else KNOWN_BATTERIES[elem["ip"]]

        msg = {
            "device_list": ip_id_dict,
            "snr_list": snrs,
            "has_changed": change_flag
        }

        return json.dumps({"type": "net_data", "data": msg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-interval")
def get_interval():
    """
    Endpoint for getting current data update interval
    :return:
    """
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


@app.post("/basic-settings")
async def basic_settings(settings: Optional[BasicSettings] = None):
    """
    :return:
    """
    try:
        if settings:
            async with lock:
                response = set_basic_settings(RADIO_IP, NODE_LIST, settings)

            msg = {"Error"} if "error" in response else {"Success"}

            return msg
        else:
            response = get_basic_set(RADIO_IP)
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/device-battery")
async def device_battery(device_id: int = 0):
    """
    This method returns battery of a given device
    :return:
    """
    global IP_LIST, NODE_LIST, KNOWN_BATTERIES
    try:
        if not device_id:
            raise Exception("No id supplied")
        elif device_id not in NODE_LIST:
            raise Exception(f"{device_id} doesn't exist")

        ip = IP_LIST[NODE_LIST.index(device_id)]
        percent = get_device_battery(ip)
        async with lock:
            KNOWN_BATTERIES[ip] = str(percent)
        return percent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-battery")
async def get_battery():
    """
    routine method to return battery percentage of each device in the network
    :return:
    ips_batteries - list of radio_ip - bettery status
    """
    global RADIO_IP, NODE_LIST, IP_LIST, KNOWN_BATTERIES

    ips_batteries, ips_batteries_new_format = get_batteries(RADIO_IP, IP_LIST)
    async with lock:
        KNOWN_BATTERIES = KNOWN_BATTERIES | ips_batteries_new_format  # latter overrides former (dict union)

    print("Updated battery status")
    print(ips_batteries)
    return json.dumps({"type": "battery", "data": ips_batteries})


async def send_messages(websocket: WebSocket, interval, func):
    """Send messages every 'interval' seconds."""
    global NET_INTERVAL
    while True:
        res = await func()
        await websocket.send_text(f"{res}")
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
    await websocket.accept()
    try:

        # Create tasks for different message frequencies
        task1 = asyncio.create_task(send_messages(websocket, 300, get_battery))
        # task2 = asyncio.create_task(send_messages(websocket, 2, update_vars))
        task3 = asyncio.create_task(send_messages(websocket, 2, net_data))

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
        async with lock:
            global IP_LIST
            ptt_groups = get_ptt_groups(IP_LIST)
        return ptt_groups
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-ptt-groups")
def set_ptt_group(ptt_data: PttData):
    try:
        global RADIO_IP, NODE_LIST, STATUSIM, IP_LIST

        # update STATUSIM global var
        for status in STATUSIM:
            if status["ip"] in ptt_data.ips:
                status["status"] = ptt_data.statuses[ptt_data.ips.index(status["ip"])]

        # find node ids belonging to IPs we want to change
        nodes = [NODE_LIST[IP_LIST.index(ip)] for ip in ptt_data.ips]

        response = set_ptt_groups(RADIO_IP, ptt_data.ips, nodes, ptt_data.num_groups, ptt_data.statuses)
        # TODO: check that response was positive
        return {"message": "ptt group settings set succesfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-camera-links")
async def get_camera():
    # TODO: test camera_finder with cameras (connect different devices, interfaces etc...)
    """
    This endpoint will return the stream URLs of existing cameras in network
    existing URLs include main-stream, sub-stream and audio-stream
    :return:
    """
    global IP_LIST
    try:
        streams = find_camera_streams_temp(IP_LIST)
        # msg = ["Success" if res else "Failed"]
        msg = "Success"
        return {"message": msg, "data": streams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
