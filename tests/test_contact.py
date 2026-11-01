"""Tests for door and water leak sensors."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from lorawan_connection import DeviceDescriptor, RemovedEvent, UplinkEvent
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.dragino_lorawan._vendor.dragino_lorawan import LDS02, LWL02


@pytest.fixture(params=[LDS02, LWL02])
def model(request):
    """Exercise both sensor models."""
    return request.param


@pytest.fixture(params=["tts", "chirpstack"])
def descriptor(model, request) -> DeviceDescriptor:
    """Use the official catalog identity on each backend."""
    stack = request.param
    brand, model_id = model.identifiers[stack]
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Garden",
        stack=stack,
        brand_id=brand,
        model_id=model_id,
        application_id="app",
        profile_id="profile",
    )


@pytest.fixture
def mock_connection(descriptor: DeviceDescriptor) -> MockConnection:
    """Provide the selected backend."""
    return MockConnection([descriptor], stack_type=descriptor.stack)


@pytest.mark.usefixtures("connection_entry")
async def test_contact_entities(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
    model,
) -> None:
    """Discover entities and decode the ChirpStack catalog examples."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    binary = (
        "binary_sensor.garden_door"
        if model is LDS02
        else "binary_sensor.garden_moisture"
    )
    assert hass.states.get(binary).state == "unknown"
    payload = bytes.fromhex(
        "0b8801001bb300000000" if model is LDS02 else "0c1e0200000400000000"
    )
    event = UplinkEvent(
        descriptor=descriptor, received_at=datetime.now(UTC), f_port=10, data=payload
    )
    mock_connection.emit(event)
    await hass.async_block_till_done()
    assert hass.states.get(binary).state == "off"
    if model is LDS02:
        assert hass.states.get("binary_sensor.garden_door_open_alarm").state == "off"
    assert hass.states.get("sensor.garden_battery_voltage").state == (
        "2.952" if model is LDS02 else "3.102"
    )
    assert hass.states.get("sensor.garden_event_count").state == (
        "7091" if model is LDS02 else "4"
    )
    assert hass.states.get("sensor.garden_last_event_duration").state == "0"
    entity = er.async_get(hass).async_get(binary)
    assert (
        entity.unique_id
        == f"network:{descriptor.dev_eui}:{'contact' if model is LDS02 else 'moisture'}"
    )
    active = (
        bytes([payload[0] | model.status_mask])
        + payload[1:6]
        + bytes.fromhex("00000501")
    )
    mock_connection.emit(
        replace(
            event, data=active, received_at=event.received_at + timedelta(seconds=1)
        )
    )
    # Invalid and delayed frames must not overwrite a newer reading.
    for invalid in (
        replace(event, data=active, f_port=2),
        replace(event, data=b""),
        replace(event, data=active[:9]),
        replace(event, data=active[:2] + b"\x09" + active[3:]),
        event,
    ):
        mock_connection.emit(invalid)
    await hass.async_block_till_done()
    assert hass.states.get(binary).state == "on"
    assert hass.states.get("sensor.garden_last_event_duration").state == "5"
    if model is LDS02:
        assert hass.states.get("binary_sensor.garden_door_open_alarm").state == "on"
    mock_connection.emit(
        replace(
            event,
            data=active[:2] + b"\x03" + active[3:],
            received_at=event.received_at + timedelta(seconds=2),
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_event_count").state == "unknown"
    assert hass.states.get(binary).state == "on"
    mock_connection.emit(RemovedEvent(descriptor=descriptor))
    await hass.async_block_till_done()
    assert hass.states.get(binary) is None
    await hass.config_entries.async_unload(config_entry.entry_id)
