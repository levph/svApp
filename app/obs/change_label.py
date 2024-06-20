import requests


# This part is changing the current label of a given node in a specific radio
def change_label(radio_ip, nodeid, newlabel):
    url = f"http://{radio_ip}/cgi-bin/save_node_label"

    payload = {'node_id': nodeid,
               'node_label': newlabel}
    files = [

    ]
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

    response = requests.request("POST", url, headers=headers, data=payload, files=files)

    # This part saves the node's label in the radio's flash memory

    url = f"http://{radio_ip}/cgi-bin/save_node_label_flash.sh"

    payload = {}
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

    response = requests.request("GET", url, headers=headers, data=payload)
