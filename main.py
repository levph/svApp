from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import asyncio
from datetime import datetime
from models import PTTGroup, Setting, BasicSettings, NewLabel
from utils import set_basic
from utils.get_radio_ip import sniff_target_ip
from utils.net_battery_percent import get_batteries, node_labels, save_node_label, list_devices, get_version, net_status
from utils.change_label import change_label

app = FastAPI()

# global variables
# TODO: check if function calls were successful
# TODO: add documentation :))
RADIO_IP = None
NODE_LIST = None
IP_LIST = None
VERSION = None


@app.on_event("startup")
async def startup_event():
    """
    Method to run on application startup, find IP of local device, list of nodes in network
    :return:
    """
    global RADIO_IP, NODE_LIST, IP_LIST
    RADIO_IP = sniff_target_ip()
    [IP_LIST, NODE_LIST, _] = list_devices(RADIO_IP)
    print(f"Radio IP set to {RADIO_IP}")
    print(f"Node List set to {NODE_LIST}")
    print(f"IP List set to {IP_LIST}")


async def update_vars():
    """
    routine function to update global variables
    This method updates global variables such as current radio IP, lists of IP and ID of existing
    nodes in network
    :return:
    """
    global RADIO_IP, NODE_LIST, IP_LIST
    # TODO: less resource affecting method for finding current radio IP
    #  (no need to always sniff packets, maybe just API request)
    RADIO_IP = sniff_target_ip()
    [IP_LIST, NODE_LIST, _] = list_devices(RADIO_IP)
    print(f"Radio IP set to {RADIO_IP}")
    print(f"Node List set to {NODE_LIST}")
    print(f"IP List set to {IP_LIST}")
    return f"{RADIO_IP} still connected"


# TODO: finish the net stat function to get all snrs effectively
async def net_stat():
    """
    This method will return parameters of network i.e. SNRs between each node
    :return:
    """
    global RADIO_IP, NODE_LIST
    res = net_status(RADIO_IP, NODE_LIST)
    return res


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
        # task2 = asyncio.create_task(send_messages(websocket, 20, get_battery))
        task3 = asyncio.create_task(send_messages(websocket, 10, update_vars))

        # Wait for both tasks to complete (they won't, unless there's an error)
        await asyncio.gather(task1, task3)

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


# TODO: check if request was successful
@app.post("/change_label")
async def set_label(new_label: NewLabel):
    """
    Set UI label for a given radio node_id
    :param new_label:
    :return:
    """
    try:
        global RADIO_IP
        res = change_label(RADIO_IP, new_label.node_id, new_label.label)
        # msg = ["Success" if res else "Failed"]
        msg = "Success"
        return {"message": msg, "data": new_label.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
