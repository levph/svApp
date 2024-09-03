from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional

from utils.fa_models import BasicSettings, PttData, NodeID, Interval, IpCredentials, LogInResponse, ErrorResponse
from utils.get_radio_ip import sniff_target_ip
from utils.api_funcs_ss5 import RadioManager
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

radio_manager = RadioManager()  # Instantiate the RadioManager class

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

    return LogInResponse(type="Success", msg={"ip": radio_ip, "is_protected": 0})


@app.post("/log-in")
def log_in(ip_creds: IpCredentials):
    """
    This method is called from log-in screen. Find radio IP and whether it is protected or not.
    Updates relevant global variables.
    :return: json with type and msg fields
    """
    return radio_manager.log_in(ip_creds)


@app.post("/log-out")
def log_out():
    """
    Delete type of method to finish current session.
    will zeroize global variables and finish secure session if it exists
    :return: string to indicate successful exit
    """
    return radio_manager.log_out()


@app.get("/silvus-tech-gui")
async def open_technical_system():
    """
    This method opens the silvus gui
    :return:
    """
    url = radio_manager.get_silvus_gui_url()
    webbrowser.open(url, new=0, autoraise=True)


@app.post("/set-label")
def set_label(node: NodeID):
    """
    This method sets label for given device id
    :return:
    """
    return radio_manager.set_label(node)


@app.get("/net-data")
async def net_data():
    """
    This method returns global variables
    assumes at least one radio is connected! will be fixed later
    :return:
    """
    return await radio_manager.get_net_data()


@app.get("/data-interval")
def get_interval():
    """
    Endpoint for getting current data update interval
    :return:
    """
    return radio_manager.get_interval()


@app.post("/data-interval")
def change_interval(interval: Interval):
    """
    This method changes the net-data update interval
    :param interval:
    :return:
    """
    return radio_manager.change_interval(interval)


@app.post("/basic-settings")
async def basic_settings(settings: Optional[BasicSettings] = None):
    """
    :return:
    """
    return await radio_manager.basic_settings(settings)


@app.get("/device-battery")
async def device_battery(device_id: int = 0):
    """
    This method returns battery of a given device
    :return:
    """
    return await radio_manager.get_device_battery(device_id)


@app.get("/get-battery")
async def get_battery():
    """
    routine method to return battery percentage of each device in the network
    :return:
    ips_batteries - list of radio_ip - bettery status
    """
    return await radio_manager.get_battery()


async def send_messages(websocket: WebSocket, interval, func):
    """Send messages every 'interval' seconds."""
    global NET_INTERVAL
    while True:
        res = await func()
        await websocket.send_text(f"{res}")
        interval = interval if func == radio_manager.get_battery else NET_INTERVAL
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
        task1 = asyncio.create_task(send_messages(websocket, 300, radio_manager.get_battery))
        task3 = asyncio.create_task(send_messages(websocket, 2, radio_manager.get_net_data))

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
            return await radio_manager.get_ptt_groups()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-ptt-groups")
def set_ptt_group(ptt_data: PttData):
    return radio_manager.set_ptt_groups(ptt_data)


@app.get("/get-camera-links")
async def get_camera():
    """
    This endpoint will return the stream URLs of existing cameras in network
    existing URLs include main-stream, sub-stream and audio-stream
    :return:
    """
    return await radio_manager.get_camera_links()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
