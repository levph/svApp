from enum import Enum
from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel


class UserPost(BaseModel):
    name: str
    body: str


class PTTGroup(BaseModel):
    group_id: int
    group_name: str
    members: list


class NewLabel(BaseModel):
    node_id: str
    label: str


class PttData(BaseModel):
    # {"num_groups": 4,
    #  "ips": ["172.20.241.202", "172.20.238.213"],
    #  "statuses": [[1, 1, 0, 0], [1, 0, 1, 0]]
    #  }
    num_groups: int
    ips: list[str]
    statuses: list[list[int]]


class Interval(BaseModel):
    value: int = 2


class NodeID(BaseModel):
    id: int
    label: str


class IpCredentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    radio_ip: str


class ErrorResponse(HTTPException):
    def __init__(self, msg: str, status_code: int = 500):
        details = {"type": "Fail", "msg": msg}
        super().__init__(status_code=status_code, detail=details)


class LogInResponse(BaseModel):
    type: str
    msg: str | dict


class NodePos(BaseModel):
    id: int
    ip: str
    pos: tuple[float, float]


class Topology(BaseModel):
    device_list: list[NodePos]


class Status(BaseModel):
    ip: str
    id: int
    status: list[int]
    name: str
    percent: str = "-1"
    is_online: bool


class NetDataMsg(BaseModel):
    device_list: list[Status]
    snr_list: list[dict]


class SocketMsg(BaseModel):
    type: str
    data: NetDataMsg | dict[str, str]
    has_changed: Optional[bool] = None


class DiscoveryResult(BaseModel):
    """base model to store discovery results."""
    ip_address: Optional[str] = None
    version: Optional[int] = None
    discovery_time: Optional[float] = None


class Credentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

    def is_empty(self) -> bool:
        """
        Returns True if both username and password are either None or empty strings.
        """
        return not self.username and not self.password


class NodeNames(BaseModel):
    ids: list[int] = []
    names: list[str] = []


class CamStream(BaseModel):
    uri: str
    audio: int


class Camera(BaseModel):
    ip: str
    device_ip: str
    device_id: int
    main_stream: CamStream
    sub_stream: CamStream


class BasicSettings(BaseModel):
    set_net_flag: int
    frequency: float
    bw: str
    net_id: str
    power_dBm: str


class RadioIP(BaseModel):
    radio_ip: str


class Setting(BaseModel):
    key: str
    value: str


class OfflineIp(BaseModel):
    status: Status
    time: float


class ResponseType(str, Enum):
    """Enumeration for response types."""
    SUCCESS = "Success"
    ERROR = "Error"


class DeviceInfo(BaseModel):
    """Model for device information."""
    ip: str
    is_protected: int = 0


class RadioDiscoveryResponse(BaseModel):
    """Base model for radio discovery responses."""
    type: ResponseType
    msg: dict | DeviceInfo


class ErrorDetail(BaseModel):
    """Model for error details."""
    error: str
    details: Optional[str] = None


class RadioDiscoveryError(Exception):
    """Custom exception for radio discovery errors."""
    pass


RADIO_DISCOVERY_RESPONSES = {
        200: {
            "description": "Successfully discovered radio device",
            "model": RadioDiscoveryResponse
        },
        404: {
            "description": "No radio device found",
            "model": RadioDiscoveryResponse
        },
        500: {
            "description": "Internal server error",
            "model": RadioDiscoveryResponse
        }
    }

