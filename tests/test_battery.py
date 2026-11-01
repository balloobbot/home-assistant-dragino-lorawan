"""Tests for LoRaWAN battery status."""

from dataclasses import replace
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from lorawan_connection import DeviceDescriptor, StatusEvent, UplinkEvent
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.dragino_lorawan._vendor.dragino_lorawan import (
    LDS02,
    LHT65,
    LWL02,
)


@pytest.fixture(params=[LHT65, LDS02, LWL02])
def descriptor(request) -> DeviceDescriptor:
    """Describe each battery-powered model."""
    brand, model = request.param.identifiers["tts"]
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Garden",
        stack="tts",
        brand_id=brand,
        model_id=model,
        application_id="app",
        profile_id="profile",
    )


@pytest.mark.usefixtures("connection_entry")
async def test_battery_status(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
) -> None:
    """Expose LoRaWAN status for every battery-powered model."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == "unknown"
    entity = er.async_get(hass).async_get("sensor.garden_battery")
    assert entity.unique_id == f"network:{descriptor.dev_eui}:battery"
    assert entity.entity_category is er.EntityCategory.DIAGNOSTIC
    event = StatusEvent(
        descriptor=descriptor,
        received_at=datetime.now(UTC),
        battery_level=72,
        battery_level_unavailable=False,
    )
    mock_connection.emit(event)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == "72"
    for updates, expected in [
        ({"battery_level": 0}, "0"),
        ({"external_power_source": True}, "unknown"),
        ({"battery_level_unavailable": True}, "unknown"),
    ]:
        mock_connection.emit(replace(event, **updates))
        await hass.async_block_till_done()
        assert hass.states.get("sensor.garden_battery").state == expected
    await hass.config_entries.async_unload(config_entry.entry_id)


@pytest.mark.usefixtures("connection_entry")
async def test_uplink_battery_fallback(
    hass, config_entry, mock_connection, descriptor
) -> None:
    """Prefer status, preserve zero, and fall back to the profile estimate."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # LHT65 has no voltage-to-percentage calculation in the reference profiles.
    payload = {
        "lht65": (2, "0b88010001f40200000000"),
        "lds02": (10, "0b880100000000000000"),
        "lwl02": (10, "0b8802000000000000"),
    }[descriptor.model_id]
    mock_connection.emit(
        UplinkEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            f_port=payload[0],
            data=bytes.fromhex(payload[1]),
        )
    )
    await hass.async_block_till_done()
    expected = "unknown" if descriptor.model_id == "lht65" else "85"
    assert hass.states.get("sensor.garden_battery").state == expected
    status = StatusEvent(
        descriptor=descriptor,
        received_at=datetime.now(UTC),
        battery_level=0,
        battery_level_unavailable=False,
    )
    mock_connection.emit(status)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == "0"
    mock_connection.emit(replace(status, battery_level=72))
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == "72"
    mock_connection.emit(replace(status, battery_level_unavailable=True))
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_battery").state == expected
    await hass.config_entries.async_unload(config_entry.entry_id)
