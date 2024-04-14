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


class BasicSettings(BaseModel):
    setNetFlag: int
    frequency: int
    bw: int
    netID: int
    powerdBm: int


class Setting(BaseModel):
    key: str
    value: str
