"""Fixtures for Dragino LoRaWAN."""

from collections.abc import AsyncGenerator
from pathlib import Path

from homeassistant.components.lorawan import async_register_connection
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from lorawan_connection import DeviceDescriptor
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.dragino_lorawan._vendor.dragino_lorawan import LHT65
from custom_components.dragino_lorawan.const import DOMAIN


@pytest.fixture
def descriptor() -> DeviceDescriptor:
    """Describe a device using its catalog identity."""
    brand_id, model_id = LHT65.identifiers["tts"]
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Garden",
        application_id="application",
        profile_id="local-profile",
        stack="tts",
        brand_id=brand_id,
        model_id=model_id,
    )


@pytest.fixture
def mock_connection(descriptor: DeviceDescriptor) -> MockConnection:
    """Provide a connection with one device."""
    return MockConnection([descriptor], stack_type="tts")


@pytest.fixture
async def connection_entry(
    hass: HomeAssistant, mock_connection: MockConnection
) -> AsyncGenerator[MockConfigEntry]:
    """Register a LoRaWAN connection."""
    assert await async_setup_component(hass, "lorawan", {})
    entry = MockConfigEntry(domain="test_connection", entry_id="network")
    entry.add_to_hass(hass)
    unregister = await async_register_connection(
        hass, entry, connection=mock_connection
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    for flow in hass.config_entries.flow.async_progress():
        hass.config_entries.flow.async_abort(flow["flow_id"])
    yield entry
    unregister()
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create the device integration entry."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, title="Dragino")
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def hass_config_dir(tmp_path: Path) -> str:
    """Keep each test configuration isolated."""
    return str(tmp_path)
