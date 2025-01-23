"""
Lizi v1.1.1 - Server home page


"""
from typing import Optional
from logging import getLogger

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from utils.fa_models import *
from utils.get_radio_ip import RadioIpSniffer
from utils.api_funcs_ss5 import RadioManager
import webbrowser

# configure logging
logger = getLogger(__name__)

# FastAPI app configuration
app = FastAPI(
    title="Radio Discovery API",
    description="API for discovering radio devices on the network",
    version="1.1.1"
)

origins = [
    "http://localhost",
    "http://localhost:5173"
]

app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

# TODO: add DI
radio_manager = RadioManager()  # Instantiate the RadioManager class
radio_sniffer = RadioIpSniffer()  # Instantiate the RadioIpSniffer class


@app.get(
    "/ip",
    response_model=RadioDiscoveryResponse,
    responses=RADIO_DISCOVERY_RESPONSES
)
async def find_ip() -> RadioDiscoveryResponse:
    """
    Discover radio device IP address and return details.
    """
    try:
        discovery_result = radio_sniffer.discover_radio()

        if not discovery_result.ip_address:
            raise ErrorResponse(msg="Couldn't find device", status_code=status.HTTP_404_NOT_FOUND,
                                err_type="DeviceNotFound")

        return RadioDiscoveryResponse(type=ResponseType.SUCCESS,
                                      msg=DeviceInfo(ip=discovery_result.ip_address, is_protected=0))

    except RadioDiscoveryError as e:
        raise ErrorResponse(msg=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR_NOT_FOUND,
                            err_type="DiscoveryError")
    except HTTPException:
        raise
    except Exception as e:
        raise ErrorResponse(msg=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR_NOT_FOUND,
                            err_type="InternalError")


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


@app.get("/hidden")
def get_hidden():
    return radio_manager.hidden_devices


@app.post("/hide/{device_id}")
def hide_device(device_id: int):
    radio_manager.hide(device_id)


@app.get("/silvus-tech-gui")
async def open_technical_system():
    """
    This method opens the silvus gui
    :return:
    """
    url = radio_manager.get_silvus_gui_url()
    webbrowser.open(url, new=0, autoraise=True)


@app.get("/topology")
def load_topology() -> Topology:
    """
    This method attempts to load a save topology structure from device flash memory
    :return:
    """
    return radio_manager.get_topology()


@app.post("/topology")
def save_topology(topology: Topology):
    return radio_manager.save_topology(topology)


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
def get_interval() -> Interval:
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


# Minimal WebSocket route
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket route, delegates handling to ApiService."""
    await radio_manager.websocket_handler(websocket)


@app.post("/get-ptt-groups")
async def get_ptt_group():
    """
    ASSUME NOT USED
    :return:
    """
    try:
        return await radio_manager.get_ptt_groups()
    except Exception as e:
        raise ErrorResponse(msg=str(e))


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
