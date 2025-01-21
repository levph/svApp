import json
from typing import Optional

from pydantic import BaseModel


class Content(BaseModel):
    endpoint: str
    payload: str | dict
    headers: dict


def position_endpoint(ip: str, version: int) -> str:
    """

    :param ip:
    :param version:
    :return:
    """
    return f"http://{ip}/cgi-bin/nodePositionHandler.py{'c' if version == 5 else ''}"


def _build_load_request(radio_ip: str, version: int) -> Content:
    url = position_endpoint(radio_ip, version)
    payload = {'action': 'load'}
    headers = {}
    return Content(endpoint=url, payload=payload, headers=headers)


def _build_save_request(radio_ip: str, node_db, version: int):
    url = position_endpoint(radio_ip, version)
    pos_json = json.dumps({
        "version": 0.1,
        "nodeDB": node_db
    })

    payload = {'action': 'save',
               'posJson': pos_json}
    headers = {}
    return Content(endpoint=url, payload=payload, headers=headers)


def node_position(radio_ip: str, action: str, node_db: Optional[dict] = None, version: int = 5) -> Content:
    """
    Request builder for node position and topology API requests.
    :param version:
    :param radio_ip:
    :param action:
    :param node_db: example = {
        "324042": {"pos": {"x": -5.798362880357847, "y": -50.70484496919661}},
        "324744": {"pos": {"x": 32.718816143150285, "y": -91.93450138872643}},
    }
    :return:
    """

    if action == "load":
        return _build_load_request(radio_ip, version)
    elif action == "save":
        return _build_save_request(radio_ip, node_db, version)

    raise ValueError("Incorrect action")


def build_json_rpc_payload(methods: list[str], params: list[list]) -> str:
    """
    Build a JSON-RPC payload for API requests.
    """
    command_list = [
        {"jsonrpc": "2.0", "method": methods[i], "id": i, "params": params[i]}
        for i in range(len(methods))
    ]
    return json.dumps(command_list if len(methods) > 1 else command_list[0])


def build_broadcast_payload(methods: list[str], params: list[list], node_ids: list[int]) -> str:
    """
    Build a broadcast payload for sending commands to multiple nodes.
    """
    api_list = [{"method": methods[i], "params": params[i]} for i in range(len(methods))]
    return json.dumps({"apis": [{"method": "deferred_execution_api", "params": {"version": "1", "api_list": api_list}}],
                       "nodeids": node_ids})
