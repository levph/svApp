from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import asyncio
from utils.fa_models import BasicSettings, NewLabel
from utils import set_basic
from utils.get_radio_ip import sniff_target_ip
from utils.api_funcs_ss5 import list_devices, net_status, find_camera_streams_temp, get_batteries

app = FastAPI()

# global variables
# TODO: check if function calls were successful
# TODO: add documentation :))
RADIO_IP = None
NODE_LIST = None
IP_LIST = None
VERSION = None
CAM_DATA = None


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
        except Exception as e:
            print(f"Error. Please make sure computer IP is correct")
            print(e)
        else:
            print(f"Node List set to {NODE_LIST}")
            print(f"IP List set to {IP_LIST}\n")


@app.get("/net_data")
async def net_data():
    """
    This method returns global variables
    :return:
    """
    msg = {
        "radio_ip": RADIO_IP,
        "node_ids": NODE_LIST,
        "node_ips": IP_LIST
    }
    return msg


@app.get("/get_snrs")
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

    return msg


@app.get("/get_battery")
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
    return ips_batteries


async def send_messages(websocket: WebSocket, interval, func):
    """Send messages every 'interval' seconds."""
    while True:
        res = await func()
        await websocket.send_text(f"{res}")
        await asyncio.sleep(interval)


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
        task2 = asyncio.create_task(send_messages(websocket, 10, update_vars))

        # Wait for both tasks to complete (they won't, unless there's an error)
        await asyncio.gather(task1, task2)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


# TODO: set link distance to 5000 too!
@app.post("/set_basic_settings")
async def set_basic_settings(settings: BasicSettings):
    """
    this method applies basic settings (frequency, power, bandwidth, netID)
    :param settings:
    :return:
    """
    try:
        response = set_basic.set_basic_settings(RADIO_IP, NODE_LIST, settings)
        # TODO: check that response was positive
        return {"message": "Basic Settings set successfully", "data": settings.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_camera_links")
async def get_camera():
    # TODO: test camera_finder with cameras (connect different devices, interfaces etc...)
    # TODO: add substreams and audio streams
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
