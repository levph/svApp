from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import asyncio
from datetime import datetime
from models import PTTGroup, Setting, BasicSettings, NewLabel
from utils.set_basic import set_basic_settings
from utils.get_radio_ip import sniff_target_ip
from utils.net_battery_percent import get_batteries, node_labels, save_node_label, list_devices, get_version, net_status
from utils.change_label import change_label

app = FastAPI()

# global variables
# TODO: update global variables in functions
# TODO: check if function calls were successful
RADIO_IP = None
NODE_LIST = None
VERSION = None


@app.on_event("startup")
async def startup_event():
    global RADIO_IP, NODE_LIST
    RADIO_IP = sniff_target_ip()
    [_, NODE_LIST, _] = list_devices(RADIO_IP)
    print(f"Radio IP set to {RADIO_IP}")
    print(f"Node List set to {NODE_LIST}")


# TODO: finish websocket stuff
async def net_stat():
    global RADIO_IP
    res = net_status(RADIO_IP)


async def send_messages(websocket: WebSocket, interval, func):
    """Send messages every 'interval' seconds."""
    while True:
        res = await func()
        await websocket.send_text(f"{res}")
        await asyncio.sleep(interval)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Create tasks for different message frequencies
        task1 = asyncio.create_task(send_messages(websocket, 10, "Message every 10 seconds"))
        task2 = asyncio.create_task(send_messages(websocket, 60, "Message every 60 seconds"))

        # Wait for both tasks to complete (they won't, unless there's an error)
        await asyncio.gather(task1, task2)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


@app.post("/set_basic_settings")
async def set_basic_settings(settings: BasicSettings):
    try:
        response = set_basic_settings(RADIO_IP, NODE_LIST, settings)
        # TODO: check that response was positive
        return {"message": "Basic Settings set successfully", "data": settings.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TODO: check if request was successful
@app.post("/change_label")
async def set_label(new_label: NewLabel):
    try:
        global RADIO_IP
        res = change_label(RADIO_IP, new_label.node_id, new_label.label)
        # msg = ["Success" if res else "Failed"]
        msg = "Success"
        return {"message": msg, "data": new_label.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set_setting")
async def set_setting(setting: Setting):
    # Access the data with setting.key and setting.value
    # Implement your logic to apply the setting
    return {"message": "Setting applied successfully", "data": setting.dict()}
