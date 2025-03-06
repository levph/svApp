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
    url = f"http://localhost:8080/hide/"
    payload = {"device_id": device_id}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def unhide_device(device_id):
    url = f"http://localhost:8080/unhide"
    headers = {"Content-Type": "application/json"}
    payload = {"device_ids": [device_id]}

    response = requests.post(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def log_in():
    url = "http://localhost:8080/log-in"
    payload = {"radio_ip": "172.20.238.213"}
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


def set_ptt():
    url = "http://localhost:8080/set-ptt-groups"
    # payload = {"radio_ip": "172.20.241.202"}
    payload = {"num_groups": 4, "ips": ["172.20.238.213"], "statuses": [[1, 1, 1, 0]]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


def set_ptt_master():
    url = "http://localhost:8080/set-ptt-master"
    # payload = {"radio_ip": "172.20.241.202"}
    payload = {"status": [1, 1, 1, 1]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    print(response.status_code)
    print(response.text)  # Print the response content


if __name__ == '__main__':
    log_in()
    print("Logged in!")
    time.sleep(2)
    before = time.time()
    set_ptt_master()
    print(f"Time taken: {time.time() - before} seconds")

    set_ptt()
    net_data()
    hide_device(323285)
    unhide_device(323285)
    net_data()

