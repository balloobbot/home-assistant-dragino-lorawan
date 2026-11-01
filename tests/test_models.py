"""Tests for Dragino payloads."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from lorawan_connection import DeviceDescriptor, UplinkEvent
from lorawan_connection.mock import MockConnection
import pytest

from custom_components.dragino_lorawan._vendor.dragino_lorawan import (
    LHT65,
    DraginoDevices,
)


async def test_lht65_payload(descriptor: DeviceDescriptor) -> None:
    """Decode the TTN example and ignore malformed or older readings."""
    connection = MockConnection([descriptor], stack_type="tts")
    collection = DraginoDevices(connection)
    await collection.async_setup()
    device = collection.devices[descriptor.dev_eui]
    event = UplinkEvent(
        received_at=datetime.now(UTC),
        descriptor=descriptor,
        f_port=2,
        data=bytes.fromhex("cbf60b0d0376010add7fff"),
    )
    connection.emit(event)
    assert device.temperature == 28.29
    assert device.humidity == 88.6
    assert device.external_temperature == 27.81
    assert device.battery_voltage == 3.062
    connection.emit(replace(event, data=b"\x01"))
    connection.emit(replace(event, f_port=99))
    connection.emit(
        replace(
            event, received_at=event.received_at - timedelta(seconds=1), data=bytes(11)
        )
    )
    assert device.temperature == 28.29
    collection.close()


@pytest.mark.parametrize(
    ("payload", "key", "expected"),
    [
        ("cbeaff9c026d01ff387fff", "external_temperature", -2),
        ("cbf60b0d0376817fff7fff", "external_temperature", None),
        ("cbf60b0d03760500647fff", "illuminance", 100),
        ("cbf60b0d0376060bb87fff", "external_voltage", 3),
        ("cbf60b0d0376080000000a", "external_count", 10),
    ],
)
def test_extensions(payload: str, key: str, expected: float | None) -> None:
    """Decode external probes and disconnected sensors."""
    assert LHT65.decode(bytes.fromhex(payload))[key] == expected


def test_history() -> None:
    """Ignore datalog replies."""
    assert LHT65.decode(bytes.fromhex("cbea0105026d4101aa7fff")) == {}


@pytest.mark.parametrize("payload", ["01", "cbf60b0d037601", "cbf60b0d0fff010add7fff"])
def test_invalid_payload(payload: str) -> None:
    """Reject incomplete frames and invalid humidity."""
    with pytest.raises(ValueError):
        LHT65.decode(bytes.fromhex(payload))
