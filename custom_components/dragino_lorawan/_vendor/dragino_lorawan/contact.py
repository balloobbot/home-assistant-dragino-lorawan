"""Dragino door and water leak sensors."""

from datetime import datetime
from typing import override

from lorawan_connection import Device, DeviceDescriptor, DeviceEvent, EventType


class ContactDevice(Device):
    """Door and leak telemetry."""

    model_name: str
    mode: int
    status_mask: int

    def __init__(self, descriptor: DeviceDescriptor) -> None:
        """Initialize readings."""
        super().__init__(descriptor)
        self.active: bool | None = None
        self.alarm: bool | None = None
        self.battery_voltage: float | None = None
        self.event_count: int | None = None
        self.last_duration: int | None = None
        self._updated: datetime | None = None

    @override
    def handle_event(self, event: DeviceEvent) -> None:
        if self.closed or event.type != EventType.UPLINK or event.f_port != 10:
            return
        data = event.data
        if len(data) != 10 or data[2] not in (self.mode, 3):
            return
        if self._updated is not None and event.received_at < self._updated:
            return
        self.active = bool(data[0] & self.status_mask)
        self.battery_voltage = (int.from_bytes(data[:2], "big") & 0x3FFF) / 1000
        self.alarm = bool(data[9] & 1)
        self.event_count = (
            int.from_bytes(data[3:6], "big") if data[2] == self.mode else None
        )
        self.last_duration = (
            int.from_bytes(data[6:9], "big") if data[2] == self.mode else None
        )
        self._updated = event.received_at
        self.notify()


class LDS02(ContactDevice):
    """Dragino LDS02 door sensor."""

    identifiers = {
        "tts": ("dragino", "lds02"),
        "chirpstack": (676, "55deef19-c13c-4b69-a10d-2e89f6398a02"),
    }
    model_name = "LDS02"
    mode = 1
    status_mask = 0x80


class LWL02(ContactDevice):
    """Dragino LWL02 water leak sensor."""

    identifiers = {
        "tts": ("dragino", "lwl02"),
        "chirpstack": (676, "b9a99932-c5e0-40fb-a673-85c24640cf7c"),
    }
    model_name = "LWL02"
    mode = 2
    status_mask = 0x40
