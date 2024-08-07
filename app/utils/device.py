from typing import Optional


class Device:

    def __init__(self, ip: str, username: Optional[str] = None, password: Optional[str] = None):
        """

        :param ip:
        :param username:
        :param password:
        """
        self.ip = ip
        self._cookie: Optional[str] = None
        if username and password:
            pass

    @staticmethod
    def send_message(self):
        lev = 1
        return lev


