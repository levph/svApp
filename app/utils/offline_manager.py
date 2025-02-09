import time

from utils.fa_models import OfflineDevice, Status


class OfflineDevicesManager:
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
        return 20

    # Special Methods
    def __init__(self):
        """
        Initializes a new OfflineDevicesManager with default settings.
        Sets up empty offline devices list and default timeout value.
        """
        self._offline_devices: list[OfflineDevice] = []
        self._timeout = self.default_timeout()

    def __iadd__(self, other: OfflineDevice) -> 'OfflineDevicesManager':
        """
        Implements the += operator to add a new offline device.

        Args:
            other (OfflineIp): The offline device to add

        Returns:
            OfflineDevicesManager: Self reference for method chaining
        """
        self._offline_devices.append(other)
        return self

    # Properties
    @property
    def offline_devices(self) -> list[OfflineDevice]:
        """
        List of currently tracked offline devices.

        Returns:
            List[OfflineIp]: Current offline devices
        """
        return self._offline_devices

    @offline_devices.setter
    def offline_devices(self, devices: list[OfflineDevice]) -> None:
        """
        Updates the list of offline devices.

        Args:
            devices (List[OfflineIp]): New list of offline devices
        """
        self._offline_devices = devices

    # Public Methods
    def delete_expired(self, timestamp: float) -> bool:
        """
        Removes expired offline devices based on the configured timeout.

        Args:
            timestamp (float): Current timestamp to check against

        Returns:
            bool: True if any devices were removed, False otherwise
        """
        prev_len = len(self._offline_devices)
        self._offline_devices = [
            offline for offline in self._offline_devices
            if timestamp - offline.time < self._timeout
        ]
        return prev_len != len(self._offline_devices)

    def add_offline_devices(
            self,
            current_devices_status: list[Status],
            ip_list: list[str],
            timestamp: float
    ) -> list[Status]:
        """
        Processes newly disconnected devices and adds them to the offline list.

        This method:
        1. Checks each device's current status
        2. If a device is no longer in the IP list, marks it as offline
        3. Adds offline devices to the tracking list
        4. Updates the current devices status list

        Args:
            current_devices_status (List[Status]): List of current device statuses
            ip_list (List[str]): List of currently active IP addresses
            timestamp (float): Current timestamp

        Returns:
            List[Status]: Updated list of current device statuses
        """
        # Create a new list instead of modifying while iterating
        remaining_devices = []

        for status in current_devices_status:
            if status.ip not in ip_list:
                setattr(status, 'is_online', False)
                self._offline_devices.append(
                    OfflineIp(status=status, time=timestamp)
                )
            else:
                remaining_devices.append(status)

        return remaining_devices

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
        back_online = []
        processed_offline = []

        for offline in self._offline_devices:
            if offline.status.id in new_ips_map:
                setattr(offline.status, 'is_online', True)
                back_online.append(offline.status)
                del new_ips_map[offline.status.id]
                processed_offline.append(offline)

        # Remove processed devices after iteration
        for offline in processed_offline:
            self._offline_devices.remove(offline)

        return back_online, new_ips_map
