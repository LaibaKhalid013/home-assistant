from dataclasses import InitVar, dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ("Device", "MeteoSensor", "Climate", "Remote")


@dataclass
class Device:
    type: str = field(init=False)
    mrdc: str = field(init=False)
    status: str = field(init=False)
    id: str = field(init=False)
    name: Optional[str] = field(init=False)
    time: int = field(init=False)
    timezone: int = field(init=False)
    powermode: str = field(init=False)
    currentvoltage: int = field(init=False)
    firmware: str = field(init=False)
    temperature: int = field(init=False)
    homekit: int = field(init=False)
    ecomode: bool = field(init=False)
    sensormode: int = field(init=False)
    _data: InitVar[Dict[str, str]]

    def __post_init__(self, _data: Dict[str, str]) -> None:
        self.type = _data["Type"]
        self.mrdc = _data["MRDC"]
        self.status = _data["Status"]
        self.id = _data["ID"].upper()
        self.name = _data["Name"]
        self.time = int(_data["Time"])
        self.timezone = int(_data["Timezone"])
        self.powermode = _data["PowerMode"]
        self.currentvoltage = int(_data["CurrentVoltage"])
        self.firmware = str(_data["Firmware"])
        self.temperature = int(_data["Temperature"])
        self.homekit = int(_data["HomeKit"])
        self.ecomode = _data["EcoMode"] == "on"
        self.sensormode = int(_data["SensorMode"])


@dataclass
class MeteoSensor:
    humidity: float = field(init=False)
    pressure: float = field(init=False)
    temperature: float = field(init=False)
    updated: int = field(init=False)
    _data: InitVar[Dict[str, str]]

    def __post_init__(self, _data: Dict[str, str]) -> None:
        self.humidity = float(_data["Humidity"])
        self.pressure = float(_data["Pressure"])
        self.temperature = float(_data["Temperature"])
        self.updated = int(_data["Updated"])


@dataclass
class Functions:
    name: str = field(init=False)
    type: str = field(init=False)
    data_dict: InitVar[Dict[str, Any]]

    def __post_init__(self, data_dict: Dict[str, Any]) -> None:
        self.type = data_dict["Type"]
        self.name = data_dict["Name"]


@dataclass
class Remote:
    type: str = field(init=False)
    name: str = field(init=False)
    updated: int = field(init=False)
    status: Optional[str] = field(init=False)
    laststatus: Optional[str] = field(init=False)
    functions: List[Functions] = field(init=False)
    _data: InitVar[Dict[str, Any]]

    def __post_init__(self, _data: Dict[str, Any]) -> None:
        self.type = _data["Type"]
        self.name = _data["Name"]
        self.updated = int(_data["Updated"])
        self.status = _data.get("Status")
        self.laststatus = _data.get("LastStatus")
        self.functions = [
            Functions(data_dict=function) for function in _data["Functions"]
        ]


@dataclass
class Climate(Remote):
    extra: str = field(init=False)
    hvac_mode: int = field(init=False)
    temperature: int = field(init=False)
    fan_mode: int = field(init=False)
    swing_mode: int = field(init=False)

    def __post_init__(self, _data: Dict[str, Any]) -> None:
        self.extra = _data["Extra"]
        self.hvac_mode = int(_data["Status"][0])
        self.temperature = int(_data["Status"][1], 16)
        self.fan_mode = int(_data["Status"][2])
        self.swing_mode = int(_data["Status"][3])
        super().__post_init__(_data)
