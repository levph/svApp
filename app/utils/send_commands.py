import requests
import json
import asyncio

from pydantic import BaseModel, Field
from typing import Optional
from utils.fa_models import Credentials
from utils import request_builder
from utils.request_builder import Content

lock = asyncio.Lock()


class DeviceSession(BaseModel):
    is_protected: bool = False
    is_different_creds: bool = False
    session: requests.Session = Field(default_factory=requests.Session)

    class Config:
        arbitrary_types_allowed = True


class SessionManager:
    def __init__(self, version: int = 5, credentials: Credentials = Credentials()):
        self.version: int = version
        self.device_sessions: dict[str, DeviceSession] = {}
        self.global_credentials: Credentials = credentials

    def set_credentials(self, credentials: Credentials):
        self.global_credentials = credentials

    def set_version(self, version: int):
        self.version = version

    def create_session(self, ip) -> DeviceSession:
        """
        Method to create session when one doesn't exist
        :param ip:
        :return:
        """
        device_session = DeviceSession()
        self.device_sessions[ip] = device_session
        return device_session

    def get_session(self, ip) -> DeviceSession:
        if ip in self.device_sessions:
            return self.device_sessions[ip]
        session = self.create_session(ip)
        return session

    @staticmethod
    def parse_response(response, bcast, methods):
        # No need to parse bcast since it's write only
        if bcast:
            return "Success"
        response = (response['result'] if len(methods) == 1 else [res['result'] for res in response])
        return response

    # TODO: test this
    def _permission_error_handler(self, radio_ip: str, device_session: DeviceSession, **kwargs):
        # no credentials - fail
        if not self.global_credentials:
            raise PermissionError(f"Failed login for {radio_ip}")

        # try log-in
        if not self.log_in(radio_ip):
            device_session.is_different_creds = True
            raise PermissionError(f"Failed login for {radio_ip}")

        # if login successful - send message again
        return self.sender(device_session.session, **kwargs)

    # TODO: test every case of kwargs
    def _sender_wrapper(self, radio_ip: str, **kwargs):
        """
        Send a request to the specified radio IP using the provided session and content.

        :param radio_ip: The IP address of the radio device.
        :param device_session: The `DeviceSession` object containing the session information.
        :param content: The `Content` object containing the endpoint, payload, and headers for the request.
        :param bcast: A boolean indicating if the request is a broadcast.
        :param len_methods: length of list of method names to be executed.
        :return: The response from the server.
        """

        # send request with retry
        try:
            response = self.sender(**kwargs)
        except PermissionError as e:
            response = self._permission_error_handler(radio_ip, **kwargs)
        except requests.exceptions.Timeout:
            raise TimeoutError("The request timed out")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"An error occurred: {e}")
        except RuntimeError as e:
            raise RuntimeError(f"Runtime error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unknown error: {e}")

        return response

    def send_commands_ip(self, methods: list[str], radio_ip: str, params: list[list], bcast: int = 0,
                         nodelist: list[int] = None,
                         param_flag: int = 0, timeout=None):
        """
        Method able to send one command or multiple to one radio.
        Including error handling
        :param param_flag:
        :param timeout:
        :param nodelist:
        :param bcast:
        :param methods: list(str) of method names
        :param radio_ip: str of radio ip
        :param params: list of params for each method, if no params list of []
        :return: result!
        """

        # get session
        device_session = self.get_session(radio_ip)

        # if device has different creds than global, then don't attempt send
        if device_session.is_different_creds:
            raise PermissionError(f"Can't login for {radio_ip}")

        content = self.format_content(radio_ip, params, methods, bcast, nodelist, param_flag)

        # send request with retry
        response = self._sender_wrapper(radio_ip, session=device_session.session, content=content, bcast=bool(bcast),
                                        multiple_methods=len(methods) > 1, type="json")

        response = self.parse_response(response, bcast, methods)

        return response

    def format_content(self, radio_ip: str, params, methods, bcast, nodelist, param_flag) -> Content:

        headers = {
            'Content-Type': 'application/json'
        }
        param_str = "param" if param_flag else "params"

        if bcast:
            command_list = [{
                "method": methods[i],
                param_str: params[i]

            } for i in range(len(methods))]

            payload = json.dumps({
                "apis": [
                    {
                        "method": "deferred_execution_api",
                        param_str: {
                            "version": "1",
                            "sleep": "0",
                            "api_list": command_list
                        }
                    }
                ],
                "nodeids": nodelist
            })

            api_endpoint = f"http://{radio_ip}/bcast_enc.pyc"
            if self.version == 4:
                api_endpoint = api_endpoint[:-1]  # script has .py suffix in v4

        else:

            command_list = [{
                "jsonrpc": "2.0",
                "method": methods[i],
                "id": i,
                param_str: params[i]

            } for i in range(len(methods))]

            payload = json.dumps(command_list if len(methods) > 1 else command_list[0])
            if methods[0] == "streamscape_data" or len(methods) > 1:
                api_endpoint = f"http://{radio_ip}/cgi-bin/streamscape_api"
            else:
                api_endpoint = f"http://{radio_ip}/streamscape_api"

        content = Content(endpoint=api_endpoint, payload=payload, headers=headers)
        return content

    @staticmethod
    def sender(session: requests.Session, content: Content, bcast: bool = False, multiple_methods: bool = False,
               type: str = "json"):
        """
        This function attempts to send a Silvus API request. Yields errors if necessary
        :param type: JSON or other
        :param multiple_methods:
        :param bcast:
        :param session:
        :param content:
        :return:
        """

        response = session.post(content.endpoint, content.payload, headers=content.headers, timeout=10)
        # response = requests.post(api_endpoint, payload, timeout=10, cookies=COOKIE)

        response.raise_for_status()  # Raise an exception for HTTP errors

        # in case it's a broadcast method
        if bcast and response.text == 'Error. Must be admin user.\n':
            raise PermissionError(f"Device is protected. Please log-in")

        if type == "topology-save":
            return 'JSON Valid' in response.text

        response = response.json()

        # check if there's an internal silvus error
        if 'error' in response or (multiple_methods and any(['error' in res for res in response])):
            if multiple_methods:
                response = [res for res in response if 'error' in res][0]
            if response['error']['message'] == 'Authentication error':
                raise PermissionError(f"Device is protected. Please log-in")
            raise RuntimeError(f"Silvus error {response['error']['code']}: {response['error']['message']}")

        return response  # return the content

    def log_in(self, radio_ip: str, creds: Optional[Credentials] = None) -> bool:
        """
        Method in charge of logging into device
        :param radio_ip:
        :param creds:
        :return:
        """

        un, pw = (creds.username, creds.password) if creds else (
            self.global_credentials.username, self.global_credentials.password)

        device_session = self.get_session(radio_ip)

        # define parameters for log-in query
        login_url = f"http://{radio_ip}/login.sh?username={un}&password={pw}&Submit=1"

        # attempt login
        response = device_session.session.post(login_url)

        # check correct login
        if response.status_code == 200 and 'Invalid Login Authentication.' not in response.text:
            if creds:
                self.global_credentials.username, self.global_credentials.password = (un, pw)
            return True
        else:
            self.clear_session(radio_ip)
            return False

    def read_from_multiple(self, radio_ips, methods, params):
        results: Optional[list] = [-1] * len(radio_ips)
        for ii, ip in enumerate(radio_ips):
            try:
                result = self.send_commands_ip(methods[ii], radio_ip=ip, params=params[ii])
                results[ii] = result
            except Exception as e:
                print(f"Error in multiple sender: {e}")
                results[ii] = [-1]
                continue
        return results

    def send_save_node_label(self, radio_ip, label_string, nodelist):
        """
        Specific method for setting node labels in flash.
        Maybe in future embed into send_commands_ip... for now let it be pls
        :param label_string:
        :param radio_ip:
        :param params:
        :param nodelist:
        :return:
        """
        device_session = self.get_session(radio_ip)

        api_endpoint = f"http://{radio_ip}/bcast_enc.pyc"
        if self.version == 4:
            api_endpoint = api_endpoint[:-1]

        api_list = [
            {
                "method": "save_node_labels_flash",
                "params": ["1", label_string]
            }
        ]

        payload = json.dumps({
            "apis": [
                {
                    "method": "deferred_execution_api",
                    "params": {
                        "version": "1",
                        "sleep": "0",
                        "api_list": api_list
                    }
                }
            ],
            "nodeids": nodelist,
            "override": 1
        })
        content = Content(endpoint=api_endpoint, payload=payload, headers={})
        try:

            response = self.sender(device_session.session, content, bcast=True, multiple_methods=True)
        except PermissionError as e:
            # no credentials - fail
            if not self.global_credentials:
                raise PermissionError(f"Failed login for {radio_ip}")

            # try log-in
            if not self.log_in(radio_ip):
                device_session.is_different_creds = True
                raise PermissionError(f"Failed login for {radio_ip}")

            # if login successful - send message again
            response = self.sender(device_session.session, content)

        except requests.exceptions.Timeout:
            raise TimeoutError("The request timed out")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"An error occurred: {e}")
        except RuntimeError as e:
            raise RuntimeError(f"Runtime error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unknown error: {e}")

        return response  # return the content

    def send_topology(self, radio_ip, action: str = "save", node_db: Optional[dict] = None):
        """
        Update node positions by leveraging the generic send_request method.

        :param radio_ip: IP address of the target device.
        :param action: Action to perform (e.g., "save").
        :param node_db: Node database containing position data.
        :return: Response from the server.
        """
        msg_type = "topology"
        if action == "save":
            msg_type += "-save"
        session = self.get_session(radio_ip)
        content = request_builder.node_position(radio_ip, action, node_db)
        # Send the request using the generic method
        return self._sender_wrapper(radio_ip, session=session.session, content=content, bcast=False,
                                    multiple_methods=False,
                                    type=msg_type)

    def clear_session(self, radio_ip):
        del self.device_sessions[radio_ip]


def main():
    # = "{\\\"323285\\\": \\\"lev100\\\"}"
    lev = 1
    creds = Credentials(username="admin", password="admin")
    session_manager = SessionManager(version=4, credentials=creds)
    response = session_manager.send_commands_ip(["freq"], "172.20.241.202", [[]])

    radio_ips = ["172.20.241.202", "172.20.238.213"]
    methods = [["battery_percent"] for _ in range(len(radio_ips))]
    params = [[[]] for _ in range(len(radio_ips))]

    # battery_percents = session_manager.read_from_multiple(radio_ips, methods, params)
    # print(battery_percents)
    lev = 1
    # battery_percents2 = session_manager.read_from_multiple(radio_ips, methods, params)
    # print(battery_percents2)
    lev = 1


if __name__ == "__main__":
    main()
