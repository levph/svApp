from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel


class UserPost(BaseModel):
    name: str
    body: str


class Interval(BaseModel):
    value: int = 2


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




class PTTGroup(BaseModel):
    group_id: int
    group_name: str
    members: list


class NewLabel(BaseModel):
    node_id: str
    label: str


class PttData(BaseModel):
    # query = {'num_groups': 4,
    #          'ips': ['172.20.240.107'],
    #          'statuses': [[1, 1, 0, 0]]
    #          }
    num_groups: int
    ips: list[str]
    statuses: list[list[int]]


class NodeID(BaseModel):
    id: int
    label: str


class Credentials(BaseModel):
    username: str
    password: str


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
