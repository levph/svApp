from typing import Dict, List, Optional

from utils.fa_models import Status
from utils.helpers import validate_ip_address


class StatusDatabase:
    def __init__(self):
        self.by_ip: dict[str, Status] = dict()
        self.by_node_id: dict[int, Status] = dict()
        self.by_name: dict[str, Status] = dict()
        self._offline_devices: dict[id, float] = dict()

    def __iadd__(self, other: Status | list[Status]) -> "StatusDatabase":
        """
        Overloads the += operator to allow adding a single Status instance or a list of them.
        """
        if isinstance(other, Status):
            self.add_radio(other)
        elif isinstance(other, list):
            for radio in other:
                if isinstance(radio, Status):
                    self.add_radio(radio)
                else:
                    raise TypeError(f"List must contain only Status objects, found {type(radio)}")
        else:
            raise TypeError(f"Expected Status or list[Status], but got {type(other)}")

        return self  # Returning self allows chaining operations

    @property
    def nodes_id(self):
        ids = list(self.by_node_id.keys())
        return ids

    @property
    def radios(self) -> list[Status]:
        return [self.by_node_id[node_id] for node_id in self.nodes_id]

    @property
    def ips(self) -> List[str]:
        return [self.by_node_id[node_id].ip for node_id in self.nodes_id]

    @property
    def names(self) -> List[str]:
        return [self.by_node_id[node_id].name for node_id in self.nodes_id]

    def add_radio(self, radio: Status) -> None:
        self.by_ip[radio.ip] = radio
        self.by_node_id[radio.id] = radio
        self.by_name[radio.name] = radio

    def remove_radio(self, radio: Status | None) -> None:
        if radio is None:
            return

        self.by_ip.pop(radio.ip, None)
        self.by_node_id.pop(radio.id, None)
        self.by_name.pop(radio.name, None)

    def remove_by_ip(self, ip: str) -> None:
        radio = self.by_ip[ip]
        self.remove_radio(radio)

    def remove_by_node_id(self, node_id: int) -> None:
        radio = self.by_node_id[node_id]
        self.remove_radio(radio)

    def remove_by_name(self, name: str) -> None:
        radio = self.by_name[name]
        self.remove_radio(radio)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.by_node_id[item]

        elif isinstance(item, str):
            if validate_ip_address(item):
                return self.by_ip[item]

            return self.by_name[item]

        raise ValueError(f'item is expcted to be node_id (int), IP address (str) or a name (str). Given = {type(item)}')

    def delete_expired(self, timestamp: float):
        expired_ids = [device_id for device_id, disc_time in self._offline_devices.items() if timestamp-disc_time
        pass


if __name__ == '__main__':
    db = StatusDatabase()
    statusim = [Status(ip="aifa", id=123, status=[1], name="lev", percent='-1', is_online=True),
                Status(ip="aifa1", id=1234, status=[1], name="lev1", percent='-1', is_online=True)]
    # db += statusim
    lev = 1
