from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional
from fa_models import BasicSettings, PttData, RadioIP, Credentials, NodeID
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

# Create a lock
lock = asyncio.Lock()


@app.post("/start-up")
def start_up():
    """
    This method is called from log-in screen. Find radio IP and whether it is protected or not.
    Updates relevant global variables.
    :return: json with type and msg fields
    """
    global RADIO_IP, NODE_LIST, IP_LIST, VERSION, NODE_NAMES, STATUSIM
    try:
        response = {"type": None, "msg": None}
        [RADIO_IP, VERSION] = ["172.20.238.213", 4]

        [IP_LIST, NODE_LIST] = [["172.20.238.213", "172.20.241.202", "172.20.123.123", "172.20.101.112"], [65535, 64433, 65534, 65533]]

        # names are not dynamic, saved in device flash
        NODE_NAMES = {"ids": NODE_LIST, "names": ["radio1", "radio2", "radio3", "radio4"]}

        STATUSIM = [
            {
                "ip": IP_LIST[0],
                "id": NODE_LIST[0],
                "status": [1] + [0] * 15,
                "name": NODE_NAMES["names"][0]
            },
            {
                "ip": IP_LIST[1],
                "id": NODE_LIST[1],
                "status": [1] + [0] * 15,
                "name": NODE_NAMES["names"][1]
            },
            {
                "ip": IP_LIST[2],
                "id": NODE_LIST[2],
                "status": [1] + [0] * 15,
                "name": NODE_NAMES["names"][2]
            },
            {
                "ip": IP_LIST[1],
                "id": NODE_LIST[1],
                "status": [1] + [0] * 15,
                "name": NODE_NAMES["names"][2]
            }
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


@app.post("/log-in")
def log_in(credentials: Credentials):
    """
    method to allow log in for locked devices
    assumes Radio IP is already set
    :param credentials: includes username and password strings
    :return:
    """
    global RADIO_IP, CREDENTIALS
    try:
        CREDENTIALS = credentials
        res = 1
        # set_credentials(credentials)
        #
        # username = credentials.username
        # pw = credentials.password
        # res = api_login(username, pw, RADIO_IP)
        if res:
            msg = "Success"
            # update variables after logging in
            _ = start_up()
        else:
            log_out()
            msg = "Fail"
        return msg

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
                "id1": str(NODE_LIST[0]),
                "id2": str(NODE_LIST[1]),
                "snr": 100
            },
            {
                "id1": str(NODE_LIST[1]),
                "id2": str(NODE_LIST[2]),
                "snr": 100
            },
            {
                "id1": str(NODE_LIST[2]),
                "id2": str(NODE_LIST[3]),
                "snr": 100
            }
        ]

        ip_id_dict = STATUSIM

        msg = {
            "device-list": ip_id_dict,
            "snr-list": snrs
        }

        return json.dumps({"type": "net-data", "data": msg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/basic-settings")
async def basic_settings(settings: Optional[BasicSettings] = None):
    """
    :return:
    """
    try:
        if settings:
            response="Success"
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
            "ip": IP_LIST[0],
            "percent": "100"
        },
        {
            "ip": IP_LIST[1],
            "percent": "20"
        }
    ]

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

        streams= [
            {
                "camera": {
                    "ip": "172.20.245.66",
                    "connected_to": "172.20.241.202",
                    "main_stream": {
                        "uri": "rtsp://172.20.245.66:554/av0_0",
                        "audio": 1
                    },
                    "sub_stream": {
                        "uri": "rtsp://172.20.245.66:554/av0_1",
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
