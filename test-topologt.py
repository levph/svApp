import requests
import json

type = "load"

if type != "save":
    url = "http://172.20.241.202/cgi-bin/nodePositionHandler.pyc"

    payload = {'action': 'load'}
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
else:
    import requests

    url = "http://172.20.241.202/cgi-bin/nodePositionHandler.pyc"

    nodeDB = {
        "324042": {"pos": {"x": -5.798362880357847, "y": -52.7}},
        "324744": {"pos": {"x": 32.718816143150285, "y": -91.934}}
    }
    posJson = {
        "version": 0.1,
        "nodeDB": nodeDB
    }

    posJson = json.dumps(posJson)

    payload = {'action': 'save',
               'posJson': posJson}
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
