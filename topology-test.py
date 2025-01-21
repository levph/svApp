import requests
import json


def send_request(action, node_db):
    """
    Send a POST request with configurable action and nodeDB.

    :param action: The action to perform (e.g., "save", "update").
    :param node_db: A dictionary containing node positions.
    """
    # Define the URL
    url = "http://172.20.241.202/cgi-bin/nodePositionHandler.pyc"

    # Define the headers
    headers = {
        "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryvonoWFP0xDp5EfNG",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Prepare the form data dynamically
    pos_json = json.dumps({"version": 0.1, "nodeDB": node_db})
    data = (
        "------WebKitFormBoundaryvonoWFP0xDp5EfNG\r\n"
        f'Content-Disposition: form-data; name="action"\r\n\r\n{action}\r\n'
        "------WebKitFormBoundaryvonoWFP0xDp5EfNG\r\n"
        f'Content-Disposition: form-data; name="posJson"\r\n\r\n{pos_json}\r\n'
        "------WebKitFormBoundaryvonoWFP0xDp5EfNG--\r\n"
    )

    # Send the POST request
    response = requests.post(url, headers=headers, data=data, verify=False)

    # Print the response
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")


# Example usage
if __name__ == "__main__":
    # Example configuration
    action = "save"
    node_db = {
        "324042": {"pos": {"x": -5.798362880357847, "y": -50.70484496919661}},
        "324744": {"pos": {"x": 32.718816143150285, "y": -91.93450138872643}},
    }

    send_request(action, node_db)
