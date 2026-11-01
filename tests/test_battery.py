"""Tests for LoRaWAN battery status."""

from dataclasses import replace
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from lorawan_connection import DeviceDescriptor, StatusEvent
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
    """Expose status percentages without guessing from voltage."""
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
