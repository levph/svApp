import requests
import time


def net_data():
    url = "http://localhost:8080/net-data"
    # payload = {"radio_ip": "172.20.241.202"}
    payload = {}
    headers = {"Content-Type": "application/json"}

    response = requests.get(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def hide_device(device_id):
    url = f"http://localhost:8080/hide/{device_id}"
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def unhide_device(device_id):
    url = f"http://localhost:8080/unhide/{device_id}"
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def set_label(node_id: int, label: str):
    url = "http://localhost:8080/set-label"
    payload = {"id": node_id, "label": label}
    # payload = {}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def log_in():
    url = "http://localhost:8080/log-in"
    payload = {"radio_ip": "172.20.241.202"}
    # payload = {}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def get_hidden():
    url = "http://localhost:8080/hidden"
    # payload = {"radio_ip": "172.20.241.202"}
    payload = {}
    headers = {"Content-Type": "application/json"}

    response = requests.get(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


if __name__ == '__main__':
    log_in()
    print("Logged in!")
    time.sleep(2)

    set_label(324042, "test2")

    net_data()
    print("Net-data")
    time.sleep(3)
    hide_device(324042)
    print("Hidden device 324042")
    time.sleep(2)
    net_data()
    print("Net data without it")
    time.sleep(1)
    get_hidden()
    print("^hidden devices")
    time.sleep(1)
    unhide_device(324042)
    print("Unhidden")
    time.sleep(1)
    net_data()
    print("Back in action?")
