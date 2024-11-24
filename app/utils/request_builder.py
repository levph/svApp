import json
from typing import Optional

from pydantic import BaseModel


class Content(BaseModel):
    endpoint: str
    payload: str
    headers: dict


def node_position(radio_ip: str, action: str, node_db: Optional[dict] = None) -> Content:
    """
    Request builder for node position and topology API requests.
    :param radio_ip:
    :param action:
    :param node_db: example = {
        "324042": {"pos": {"x": -5.798362880357847, "y": -50.70484496919661}},
        "324744": {"pos": {"x": 32.718816143150285, "y": -91.93450138872643}},
    }
    :return:
    """
    if node_db is None:
        node_db = {}

    # build the api endpoint
    api_endpoint = f"http://{radio_ip}/cgi-bin/nodePositionHandler.pyc"

    # Build the payload
    boundary = "----WebKitFormBoundaryvonoWFP0xDp5EfNG"
    pos_json = json.dumps({"version": 0.1, "nodeDB": node_db})
    payload = (
        f"{boundary}\r\n"
        f'Content-Disposition: form-data; name="action"\r\n\r\n{action}\r\n'
        f"{boundary}\r\n"
    )
    if action == "save":
        payload += (
            f'Content-Disposition: form-data; name="posJson"\r\n\r\n{pos_json}\r\n'
            f"{boundary}--\r\n"
        )

    # Define headers
    headers = {
        "Connection": "keep-alive",
        "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryvonoWFP0xDp5EfNG",
        "X-Requested-With": "XMLHttpRequest",
    }

    return Content(endpoint=api_endpoint, payload=payload, headers=headers)


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


def build_multipart_payload(action: str, node_db: dict) -> str:
    """
    Build a multipart/form-data payload for topology requests.
    """
    boundary = "----WebKitFormBoundaryvonoWFP0xDp5EfNG"
    pos_json = json.dumps({"version": 0.1, "nodeDB": node_db})
    return (
        f"{boundary}\r\n"
        f'Content-Disposition: form-data; name="action"\r\n\r\n{action}\r\n'
        f"{boundary}\r\n"
        f'Content-Disposition: form-data; name="posJson"\r\n\r\n{pos_json}\r\n'
        f"{boundary}--\r\n"
    )


def build_headers(boundary: str, radio_ip: str) -> dict:
    """
    Build headers for multipart/form-data requests.
    """
    return {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Origin": f"http://{radio_ip}",
        "Referer": f"http://{radio_ip}/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }


def get_command_handler(command_type: str):
    """
    Retrieve the appropriate handler function for the given command type.
    """
    command_handlers = {
        "json_rpc": _handle_json_rpc,
        "broadcast": _handle_broadcast,
        "topology": _handle_topology,
    }
    if command_type not in command_handlers:
        raise ValueError(f"Unknown command type: {command_type}")
    return command_handlers[command_type]


def _handle_json_rpc(methods, radio_ip, params, **kwargs):
    payload = build_json_rpc_payload(methods, params)
    headers = {"Content-Type": "application/json"}
    endpoint = f"http://{radio_ip}/cgi-bin/streamscape_api"
    return payload, headers, endpoint


def _handle_broadcast(methods, radio_ip, params, **kwargs):
    if "nodelist" not in kwargs:
        raise ValueError("Broadcast requests require a node list.")
    payload = build_broadcast_payload(methods, params, kwargs["nodelist"])
    headers = {"Content-Type": "application/json"}
    endpoint = f"http://{radio_ip}/cgi-bin/bcast_enc.pyc"
    return payload, headers, endpoint


def _handle_topology(methods, radio_ip, params, **kwargs):
    if "action" not in kwargs or "node_db" not in kwargs:
        raise ValueError("Topology requests require 'action' and 'node_db'.")
    boundary = "----WebKitFormBoundaryvonoWFP0xDp5EfNG"
    payload = build_multipart_payload(kwargs["action"], kwargs["node_db"])
    headers = build_headers(boundary, radio_ip)
    endpoint = f"http://{radio_ip}/cgi-bin/nodePositionHandler.pyc"
    return payload, headers, endpoint
