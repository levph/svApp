import time

from utils.fa_models import OfflineDevice, Status
from utils.radio_status_database import StatusDatabase


class OfflineDevicesManager(StatusDatabase):
    """
    Manages the lifecycle of offline network devices, including tracking their status,
    handling reconnections, and managing device timeouts.

    This class provides functionality to:
    - Track devices that go offline
    - Remove expired offline devices
    - Handle device reconnections
    - Maintain device status information

    Attributes:
        _offline_devices (List[OfflineIp]): List of currently offline devices
        _timeout (int): Time in seconds after which offline devices are considered expired
    """

    # Class Methods
    @classmethod
    def default_timeout(cls) -> int:
        """
        Returns the default timeout period for offline devices.

        Returns:
            int: Default timeout in seconds (20)
        """
        return 3

    # Special Methods
    def __init__(self):
        """
        Initializes a new OfflineDevicesManager with default settings.
        Sets up empty offline devices list and default timeout value.
        """
        super().__init__()
        self._timeout: int = self.default_timeout()
        self._disconnect_times: dict[int, float] = {}

    # Public Methods
    def delete_expired(self, timestamp: float) -> bool:
        """
        Removes expired offline devices based on the configured timeout.

        Args:
            timestamp (float): Current timestamp to check against

        Returns:
            bool: True if any devices were removed, False otherwise
        """
        prev_len = len(self.nodes_id)
        expired_radios = [radio for radio in self.radios if
                          timestamp - radio.disconnect_time > self._timeout]

        for expired in expired_radios:
            self.remove_radio(expired)

        return prev_len != len(self.nodes_id)

    def add_offline_devices(
            self,
            current_statuses: StatusDatabase,
            new_ip_list: list[str],
            timestamp: float
    ) -> None:
        """
        Processes newly disconnected devices and adds them to the offline list.

        This method:
        1. Checks each device's current status
        2. If a device is no longer in the IP list, marks it as offline
        3. Adds offline devices to the tracking list
        4. Updates the current devices status list

        Args:
            current_statuses (List[Status]): List of current device status (before update)
            new_ip_list (List[str]): List of currently active IP addresses
            timestamp (float): Current timestamp

        """

        for radio in current_statuses.radios:
            if radio.ip not in new_ip_list:
                radio.is_online = False
                self._add_offline(radio, timestamp)
                current_statuses.remove_radio(radio)

    def pop_reconnected(
            self,
            new_ips_map: dict[int, str]
    ) -> tuple[list[Status], dict[int, str]]:
        """
        Identifies and processes devices that have reconnected to the network.

        This method:
        1. Checks offline devices against new IP mappings
        2. Updates status for reconnected devices
        3. Removes reconnected devices from offline tracking
        4. Updates the IP mapping to remove processed devices

        Args:
            new_ips_map (Dict[str, str]): Mapping of device IDs to new IP addresses

        Returns:
            Tuple[List[Status], Dict[str, str]]:
                - List of devices that have reconnected
                - Updated IP mapping with processed devices removed
        """

        back_online = [radio for radio in self.radios if radio.id in new_ips_map]
        for back_online_radio in back_online:
            radio = self.remove_radio(back_online_radio)

            self._recover_radio(radio)
            new_ips_map.pop(radio.id)

        return back_online, new_ips_map

    # Private
    def _add_offline(self, radio: Status, timestamp) -> None:
        radio.disconnect_time = timestamp
        super().add_radio(radio)

    @staticmethod
    def _recover_radio(radio: Status):
        radio.is_online = True
        radio.disconnect_time = -1.0

# if __name__ == '__main__':
#     db = StatusDatabase()
#     statusim = [Status(ip="172.20.238.213", id=123, status=[1], name="lev", percent='-1', is_online=True),
#                 Status(ip="172.20.241.202", id=1234, status=[1], name="lev1", percent='-1', is_online=True)]
#     db += statusim
#
#     offline_db = OfflineDevicesManager()
#     offline_db.add_offline_devices(db, ["172.20.241.202"], time.time())
#
#     # time.sleep(2)
#     # timestamp1 = time.time()
#     # offline_db.delete_expired(timestamp1)
#
#     new_ips_map = {statusim[0].id: statusim[0].ip}
#
#     back_online, tbd = offline_db.pop_reconnected(new_ips_map)
#     db += back_online
#     lev = 1
