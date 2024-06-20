from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional
from utils.fa_models import BasicSettings, PttData, RadioIP, Credentials
from utils import set_basic
from utils.get_radio_ip import sniff_target_ip
from utils.api_funcs_ss5 import list_devices, net_status, find_camera_streams_temp, get_batteries, set_ptt_groups, \
    get_basic_set
import json
from requests.exceptions import Timeout
from utils.send_commands import api_login


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
# TODO:
"""
 check encrypted/log-in protected devices - 
 can you access protected devices when passwords are different?
 or just change all function bcast calls who use other IP api?
 how does encryption affect it?
 Refer to "Password protected API" part in manual
 
 Solve network mapping for radio discovery, better ONVIF discovery, 
 RSSI reports (less latency for SNR), voice recording...
"""
# global variables
RADIO_IP = None
NODE_LIST = None
IP_LIST = None
VERSION = None
CAM_DATA = None


# TODO: fix with new version (in mail haha)
@app.on_event("startup")
async def startup_event():
    """
    Method to run on application startup, find IP of local device, list of nodes in network
    :return:
    """
    global RADIO_IP, NODE_LIST, IP_LIST

    try:
        RADIO_IP = sniff_target_ip()
    except Exception as e:
        # If we got an error then most likely there's no connected Radio
        # TODO: use exception to tell user how to fix it
        print(f"Can't find connected device\n")
        print(e)
    else:
        if not RADIO_IP:
            print(f"No Radio connected.\n")
            return
        # if we found a device

        # get list of devices in network
        print(f"Radio IP set to {RADIO_IP}\n")
        try:
            [IP_LIST, NODE_LIST] = list_devices(RADIO_IP)

        except Timeout:
            print(f"Request timed out. Make sure computer IP is correct")
        
        except Exception as e:
            if "Authentication error" in e.args[0]:
                print(f"This device is password protected. Please log-in")
            print(e)
        else:
            print(f"Node List set to {NODE_LIST}")
            print(f"IP List set to {IP_LIST}\n")


@app.post("/log-in")
async def log_in(credentials: Credentials):
    """
    Future method to allow log in for locked devices
    :param credentials: includes username and password strings
    :return:
    """
    global RADIO_IP
    try:
        username = credentials.username
        pw = credentials.password
        res = api_login(username, pw, RADIO_IP)
        if res:
            msg = "Success"
            # update variables after logging in
            await update_vars()
        else:
            msg = "Fail"
        return msg
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-radio-ip")
async def set_radio_ip(ip: RadioIP):
    """
    set radio ip
    :param ip:
    :return:
    """
    global RADIO_IP, NODE_LIST, IP_LIST
    try:
        RADIO_IP = ip.radio_ip

        # get list of devices in network
        print(f"Radio IP set to {RADIO_IP}\n")
        try:
            # run an api call to make sure IP was inserted correctly
            [IP_LIST, NODE_LIST] = list_devices(RADIO_IP)
        except Exception as e:
            print(f"Error. Please make sure computer IP is correct")
            print(e)
            msg = { "Error. Please make sure computer IP is correct"}
        else:
            print(f"Node List set to {NODE_LIST}")
            print(f"IP List set to {IP_LIST}\n")
            msg = {"radio_ip": RADIO_IP, "node_list": NODE_LIST, "node_ip_list": IP_LIST}

        return msg
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TODO: test after encryption update
@app.get("/net-data")
async def net_data():
    """
    This method returns global variables
    :return:
    """
    global IP_LIST, NODE_LIST

    # TODO: add labels to list

    if IP_LIST and NODE_LIST:
        ip_id_dict = [{"ip": ip, "id": idd} for ip, idd in zip(IP_LIST, NODE_LIST)]

        snrs = net_status(RADIO_IP, NODE_LIST[:-1]) # N-1 queries is enough to know all SNRs

        # snr_dict = [{"ip1": res[0][0], "ip2": res[0][1], "snr": res[1]} for res in snrs]

        msg = {
            "device-list": ip_id_dict,
            "snr-list": snrs
        }

    else:
        msg = "Error, no IPS in network"

    return json.dumps({"type": "net-data", "data": msg})


@app.post("/basic-settings")
async def basic_settings(settings: Optional[BasicSettings] = None):
    """
    :return:
    """
    try:
        if settings:
            response = set_basic.set_basic_settings(RADIO_IP, NODE_LIST, settings)
            msg = {"Error"} if "error" in response else {"Success"}

            return msg
        else:
            response = get_basic_set(RADIO_IP)
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-snrs")
async def net_stat():
    """
    This method will return parameters of network i.e. SNRs between each node
    :return:
    """
    global RADIO_IP, NODE_LIST
    res = net_status(RADIO_IP, NODE_LIST)
    return res


# TODO: test new changes with devices
async def update_vars():
    """
    routine function to update global variables
    This method updates global variables such as current radio IP, lists of IP and ID of existing
    nodes in network
    :return:
    """
    global RADIO_IP, NODE_LIST, IP_LIST
    valid = 1
    RADIO_IP = RADIO_IP if RADIO_IP else sniff_target_ip()
    try:
        [IP_LIST, NODE_LIST] = list_devices(RADIO_IP)
    except Exception as e:
        print(e)
        RADIO_IP, NODE_LIST, IP_LIST = [], [], []
        print(f"Searching for new connected device...")
        await startup_event()
        valid = 1 if RADIO_IP else 0
    else:
        print(f"Radio IP set to {RADIO_IP}")
        print(f"Node List set to {NODE_LIST}")
        print(f"IP List set to {IP_LIST}")

    msg = f"{RADIO_IP} is connected" if valid else f"No Radio is connected"
    msg = {"type": "update", "data": msg}
    return json.dumps(msg)


@app.get("/get-battery")
async def get_battery():
    """
    routine method to return battery percentage of each device in the network
    :return:
    ips_batteries - list of radio_ip - bettery status
    """
    global IP_LIST
    ips_batteries = get_batteries(IP_LIST)
    print("Updated battery status")
    print(ips_batteries)
    return json.dumps({"type": "battery", "data": ips_batteries})


async def send_messages(websocket: WebSocket, interval, func):
    """Send messages every 'interval' seconds."""
    while True:
        res = await func()
        await websocket.send_text(f"{res}")
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
        task1 = asyncio.create_task(send_messages(websocket, 20, get_battery))
        task2 = asyncio.create_task(send_messages(websocket, 9, update_vars))
        task3 = asyncio.create_task(send_messages(websocket, 10, net_data))

        # Wait for both tasks to complete (they won't, unless there's an error)
        await asyncio.gather(task1, task2, task3)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


@app.post("/set-ptt-groups")
async def set_ptt_group(ptt_data: PttData):
    try:
        response = set_ptt_groups(ptt_data.ips, ptt_data.num_groups, ptt_data.statuses)
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
