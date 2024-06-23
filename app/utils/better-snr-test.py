import requests
import json
from utils.send_commands import send_commands_ip
from utils.get_radio_ip import sniff_target_ip
from utils.api_funcs_ss5 import node_id_to_ip

# radio_ip = sniff_target_ip()
radio_ip = "172.20.241.202"
'''
{
  "type": "net-data",
  "data": {
    "device-list": [
      {
        "ip": "172.20.238.213",
        "id": 323285
      },
      {
        "ip": "172.20.241.202",
        "id": 324042
      }
    ],
    "snr-list": [
      {
        "id1": "323285",
        "id2": "324042",
        "snr": "80"
      }
    ]
  }
}
'''


def extract_snr(data):
    node_ids = []
    min_snr = {}
    for node in data:
        node_ids.append(int(node["id"]))
        for adjacency in node.get("adjacencies", []):
            nodeTo = adjacency["nodeTo"]
            nodeFrom = adjacency["nodeFrom"]
            snr_key = f"$snr_{nodeFrom}_{nodeTo}"
            if snr_key in adjacency["data"]:
                snr = int(adjacency["data"][snr_key])

                # Create a sorted tuple to ensure (a, b) is the same as (b, a)
                pair = tuple(sorted([nodeFrom, nodeTo]))

                # Update the minimum SNR value for the pair
                if pair in min_snr:
                    min_snr[pair] = min(min_snr[pair], snr)
                else:
                    min_snr[pair] = snr

    snr_res = [{"id1": k[0], "id2": k[1], "snr": v} for k, v in min_snr.items()]
    ips = node_id_to_ip(node_ids)

    return ips, node_ids, snr_res


response = send_commands_ip(["streamscape_data"], radio_ip, [[]])

ips, node_ids, snr_res = extract_snr(response)

