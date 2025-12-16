from typing import Optional
from pymodbus.client.tcp import AsyncModbusTcpClient
from enum import IntEnum
from pydantic import BaseModel, Field, model_validator
from typing import ClassVar, Any
import struct

def u16_to_i16(x: int) -> int:
    return struct.unpack(">h", struct.pack(">H", x))[0]

def i16_to_u16(x: int) -> int:
    return struct.unpack(">H", struct.pack(">h", x))[0]

class ThermostatStatus(BaseModel):
    raw: int = Field(..., ge=0, le=0xFFFF)

    temp_control_active: bool = False
    circulation_active: bool = False
    compressor_on: bool = False
    process_control_active: bool = False
    pump_on: bool = False
    cooling_available: bool = False
    keylock_active: bool = False
    pid_auto: bool = False
    error: bool = False
    warning: bool = False
    internal_temp_mode: bool = False
    external_temp_mode: bool = False
    dv_e_grade: bool = False
    no_restart_detected: bool = False
    freeze_protection_active: bool = False

    _BIT_MAP: ClassVar[dict[str, int]] = {
        "temp_control_active": 0,
        "circulation_active": 1,
        "compressor_on": 2,
        "process_control_active": 3,
        "pump_on": 4,
        "cooling_available": 5,
        "keylock_active": 6,
        "pid_auto": 7,
        "error": 8,
        "warning": 9,
        "internal_temp_mode": 10,
        "external_temp_mode": 11,
        "dv_e_grade": 12,
        "no_restart_detected": 14,
        "freeze_protection_active": 15,
    }

    @model_validator(mode="before")
    @classmethod
    def decode_from_raw(cls, data):
        raw = data.get("raw") if isinstance(data, dict) else None
        if raw is None:
            return data

        for field, bit in cls._BIT_MAP.items():
            if field not in data:
                data[field] = bool((raw >> bit) & 1)

        return data

class Registers(IntEnum):
    TEMP_SETPOINT = 0x00
    INTERNAL_TEMP = 0x01
    RETURN_TEMP = 0x02
    PUMP_PRESSURE = 0x03
    POWER = 0x04
    ERROR = 0x05
    WARNING = 0x06
    PROCESS_TEMPERATURE = 0x07
    ACTUAL_VALUE_INTERNAL_TEMP = 0x08
    PROCESS_TEMP_SETTING = 0x09
    THERMOSTAT_STATUS = 0x0A
    FILL_VALUE = 0x0F
    AUTO_PID = 0x12
    TEMP_MODE = 0x13
    TEMP_ACTIVE = 0x14
    COMPRESSOR_MODE = 0x15
    CIRCULATION_ACTIVE = 0x16

class TempControlMode(IntEnum):
    INTERAL = 0
    PROCESS = 1


class CompressorMode(IntEnum):
    AUTOMATIC = 0
    ALWAYS_ON = 1
    ALWAYS_OFF = 2

class PilotOne:
    def __init__(self, host: str, port: int = 502) -> None:
        self._host = host
        self._port = port
        self._client: Optional[AsyncModbusTcpClient] = None
        self._offset = 0

    async def connect(self) -> None:
        self._client = AsyncModbusTcpClient(host=self._host, port=self._port)
        await self._client.connect()

    async def close(self) -> None:
        if self._client:
            self._client.close()

    @staticmethod
    def decode_temp(raw: int) -> float:
        # raw: u16 from Modbus
        value = raw if raw < 0x8000 else raw - 0x10000
        return value * 0.01

    @staticmethod
    def decode_pressure(raw: int) -> float:
        # raw: u16 from Modbus
        value = raw if raw < 0x8000 else raw - 0x10000
        return value * 0.01
    
    
    @staticmethod
    def encode_temp(temp_c: float) -> int:
        value = int(round(temp_c / 0.01))
        if not -32768 <= value <= 32767:
            raise ValueError("Temperature out of range for int16")
        return value & 0xFFFF

    async def get_temp_setpoint(self) -> float:
        """Temp setpoint in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.TEMP_SETPOINT + self._offset, count=1)
            return self.decode_temp(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def set_temp_setpoint(self, temp: float) -> None:
        """Temp setpoint in C"""
        if self._client:
            await self._client.write_register(Registers.TEMP_SETPOINT + self._offset, self.encode_temp(temp))
            return None
        raise RuntimeError("Client not Initialized")


    async def get_internal_temp(self) -> float:
        """Temp setpoint in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.INTERNAL_TEMP + self._offset, count=1)
            return self.decode_temp(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def get_return_temp(self) -> float:
        """Temp setpoint in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.RETURN_TEMP + self._offset, count=1)
            return self.decode_temp(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def get_pump_pressure(self) -> float:
        """Pump pressure in bar"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.PUMP_PRESSURE + self._offset, count=1)
            return self.decode_pressure(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def get_power(self) -> float:
        """Power in W"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.POWER + self._offset, count=1)
            return u16_to_i16(result.registers[0])  
        raise RuntimeError("Client not Initialized")

    async def get_error(self) -> Optional[int]:
        """Error in error code"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.ERROR + self._offset, count=1)
            return u16_to_i16(result.registers[0]) if result.registers[0] != 0 else None
        raise RuntimeError("Client not Initialized")

    async def clear_error(self) -> None:
        """Clear error"""
        if self._client:
            await self._client.write_register(Registers.ERROR + self._offset, i16_to_u16(1))
            return None
        raise RuntimeError("Client not Initialized")

    async def get_warning(self) -> Optional[int]:
        """Warning in warning code"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.WARNING + self._offset, count=1)
            return u16_to_i16(result.registers[0]) if result.registers[0] != 0 else None
        raise RuntimeError("Client not Initialized")
    
    async def clear_warning(self) -> None:
        """Clear warning"""
        if self._client:
            await self._client.write_register(Registers.WARNING + self._offset, i16_to_u16(1))
            return None
        raise RuntimeError("Client not Initialized")

    async def get_process_temperature(self) -> float:
        """Process temperature in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.PROCESS_TEMPERATURE + self._offset, count=1)
            return self.decode_temp(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def get_actual_value_internal_temp(self) -> float:
        """Actual value internal temperature in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.ACTUAL_VALUE_INTERNAL_TEMP + self._offset, count=1)
            return self.decode_temp(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def get_process_temp_setting(self) -> float:
        """Process temperature setting in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.PROCESS_TEMP_SETTING + self._offset, count=1)
            return self.decode_temp(result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def set_process_temp_setting(self, temp: float) -> None:
        """Process temperature setting in C"""
        if self._client:
            await self._client.write_register(Registers.PROCESS_TEMP_SETTING + self._offset, self.encode_temp(temp))
            return None
        raise RuntimeError("Client not Initialized")

    async def get_thermostat_status(self) -> ThermostatStatus:
        """Thermostat status"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.THERMOSTAT_STATUS + self._offset, count=1)
            return ThermostatStatus(raw=result.registers[0])
        raise RuntimeError("Client not Initialized")

    async def get_fill_value(self) -> float:
        """Fill value in C"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.FILL_VALUE + self._offset, count=1)
            return u16_to_i16(result.registers[0])/1000.0
        raise RuntimeError("Client not Initialized")

    async def get_auto_pid(self) -> bool:
        """Auto PID"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.AUTO_PID + self._offset, count=1)
            return result.registers[0] != 0
        raise RuntimeError("Client not Initialized")

    async def set_auto_pid(self, auto_pid: bool) -> None:
        """Auto PID"""
        if self._client:
            await self._client.write_register(Registers.AUTO_PID + self._offset, 1 if auto_pid else 0)
            return None
        raise RuntimeError("Client not Initialized")

    async def get_temp_mode(self) -> bool:
        """Temp mode"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.TEMP_MODE + self._offset, count=1)
            return result.registers[0] != 0
        raise RuntimeError("Client not Initialized")

    async def set_temp_mode(self, temp_mode: TempControlMode) -> None:
        """Temp mode"""
        if self._client:
            await self._client.write_register(Registers.TEMP_MODE + self._offset, temp_mode.value)
            return None
        raise RuntimeError("Client not Initialized")
    
    async def get_temp_active(self) -> bool:
        """Temp active"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.TEMP_ACTIVE + self._offset, count=1)
            return result.registers[0] != 0
        raise RuntimeError("Client not Initialized")
    
    async def set_temp_active(self, temp_active: bool) -> None:
        """Temp active"""
        if self._client:
            await self._client.write_register(Registers.TEMP_ACTIVE + self._offset, 1 if temp_active else 0)
            return None
        raise RuntimeError("Client not Initialized")
    
    async def get_compressor_mode(self) -> CompressorMode:
        """Compressor mode"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.COMPRESSOR_MODE + self._offset, count=1)
            value = result.registers[0]
            if value == 0:
                return CompressorMode.AUTOMATIC
            elif value == 1:
                return CompressorMode.ALWAYS_ON
            elif value == 2:
                return CompressorMode.ALWAYS_OFF
            else:
                raise ValueError("Invalid compressor mode")
        raise RuntimeError("Client not Initialized")

    async def set_compressor_mode(self, compressor_mode: CompressorMode) -> None:
        """Compressor mode"""
        if self._client:
            await self._client.write_register(Registers.COMPRESSOR_MODE + self._offset, compressor_mode.value)
            return None
        raise RuntimeError("Client not Initialized")

    async def get_circulation_active(self) -> bool:
        """Circulation active"""
        if self._client:
            result = await self._client.read_holding_registers(Registers.CIRCULATION_ACTIVE + self._offset, count=1)
            return result.registers[0] != 0
        raise RuntimeError("Client not Initialized")
    
    async def set_circulation_active(self, circulation_active: bool) -> None:
        """Circulation active"""
        if self._client:
            await self._client.write_register(Registers.CIRCULATION_ACTIVE + self._offset, 1 if circulation_active else 0)
            return None
        raise RuntimeError("Client not Initialized")
    
