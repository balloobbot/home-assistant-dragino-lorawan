"""Tests for device readings and lifecycle."""

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.components.lorawan import async_register_connection
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from lorawan_connection import (
    AddedEvent,
    ConnectionUnavailable,
    DeviceDescriptor,
    RemovedEvent,
    UpdatedEvent,
    UplinkEvent,
)
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry


@pytest.mark.usefixtures("connection_entry", "entity_registry_enabled_by_default")
async def test_readings(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
) -> None:
    """Decode an uplink and create entities with Core's default names and IDs."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    expected = {
        "temperature": "28.29",
        "humidity": "88.6",
        "external_temperature": "27.81",
        "battery_voltage": "3.062",
    }
    for key in expected:
        assert hass.states.get(f"sensor.garden_{key}").state == "unknown"
    mock_connection.emit(
        UplinkEvent(
            received_at=datetime.now(UTC),
            descriptor=descriptor,
            f_port=2,
            data=bytes.fromhex("cbf60b0d0376010add7fff"),
        )
    )
    await hass.async_block_till_done()
    for key, value in expected.items():
        assert hass.states.get(f"sensor.garden_{key}").state == value
        entity = er.async_get(hass).async_get(f"sensor.garden_{key}")
        assert entity.unique_id == f"network:{descriptor.dev_eui}:{key}"
        device = dr.async_get(hass).async_get(entity.device_id)
        assert device.model_id == "LHT65"
        assert device.manufacturer == "Dragino"
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert all(
        state.state == "unavailable"
        for state in hass.states.async_all()
        if state.entity_id.startswith("sensor.garden_")
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_connection.emit(RemovedEvent(descriptor=descriptor))
    await hass.async_block_till_done()
    assert not dr.async_entries_for_config_entry(
        dr.async_get(hass), config_entry.entry_id
    )
    assert not er.async_entries_for_config_entry(
        er.async_get(hass), config_entry.entry_id
    )
    await hass.config_entries.async_unload(config_entry.entry_id)


@pytest.mark.usefixtures("connection_entry")
async def test_later_device(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
) -> None:
    """Add devices after setup and update their names."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    added = replace(descriptor, dev_eui="0201010101010102", name="Second")
    mock_connection.emit(AddedEvent(descriptor=added))
    await hass.async_block_till_done()
    entity = er.async_get(hass).async_get("sensor.second_temperature")
    assert entity is not None
    mock_connection.emit(UpdatedEvent(descriptor=replace(added, name="Renamed")))
    await hass.async_block_till_done()
    assert (
        config_entry.runtime_data.coordinators[
            ("network", added.dev_eui)
        ].data.descriptor.name
        == "Renamed"
    )
    await hass.config_entries.async_unload(config_entry.entry_id)


async def test_reconnect(
    hass: HomeAssistant,
    connection_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
) -> None:
    """Resume readings after a replacement connection is registered."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_connection.disconnect()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_temperature").state == "unavailable"
    replacement = MockConnection([descriptor], stack_type="tts")
    unregister = await async_register_connection(
        hass, connection_entry, connection=replacement
    )
    await hass.async_block_till_done()
    replacement.emit(
        UplinkEvent(
            received_at=datetime.now(UTC),
            descriptor=descriptor,
            f_port=2,
            data=bytes.fromhex("cbf60b0d0376010add7fff"),
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_temperature").state == "28.29"
    await hass.config_entries.async_unload(config_entry.entry_id)
    unregister()


@pytest.mark.usefixtures("connection_entry")
async def test_setup_retry(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_connection: MockConnection
) -> None:
    """Retry setup when subscribing to the connection fails."""
    with patch.object(
        mock_connection,
        "async_subscribe",
        side_effect=ConnectionUnavailable("Connection lost"),
    ):
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    await hass.config_entries.async_unload(config_entry.entry_id)


@pytest.mark.usefixtures("connection_entry")
async def test_optional_probes(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Disable optional LHT65 probes until the user enables them."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    for key in ("illuminance", "external_voltage", "external_count", "battery_voltage"):
        entity = er.async_get(hass).async_get(f"sensor.garden_{key}")
        assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    await hass.config_entries.async_unload(config_entry.entry_id)
