"""Tests for the config flow."""

from dataclasses import replace
from unittest.mock import patch

from homeassistant.components.lorawan import LoRaWANDiscoveryInfo
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from lorawan_connection import AddedEvent, DeviceDescriptor, RemovedEvent
from lorawan_connection.mock import MockConnection
import pytest

from custom_components.dragino_lorawan.const import DOMAIN


@pytest.mark.usefixtures("connection_entry")
@pytest.mark.parametrize(
    ("source", "data"),
    [(SOURCE_USER, None), (SOURCE_INTEGRATION_DISCOVERY, LoRaWANDiscoveryInfo())],
)
async def test_setup(
    hass: HomeAssistant, source: str, data: LoRaWANDiscoveryInfo | None
) -> None:
    """Confirm setup and prevent duplicate entries."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": source}, data=data
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    with patch(
        "custom_components.dragino_lorawan.async_setup_entry", return_value=None
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    assert result["result"].unique_id == DOMAIN
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["reason"] == "single_instance_allowed"


async def test_no_connections(hass: HomeAssistant) -> None:
    """Require a configured LoRaWAN connection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["reason"] == "no_lorawan_connections"


@pytest.mark.usefixtures("connection_entry")
async def test_unsupported_device(
    hass: HomeAssistant, mock_connection: MockConnection, descriptor: DeviceDescriptor
) -> None:
    """A matching name or local profile does not identify a supported model."""
    mock_connection.emit(RemovedEvent(descriptor=descriptor))
    mock_connection.emit(
        AddedEvent(descriptor=replace(descriptor, model_id="custom-profile"))
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["reason"] == "no_supported_devices"


@pytest.mark.usefixtures("connection_entry")
async def test_discovery(
    hass: HomeAssistant, mock_connection: MockConnection, descriptor: DeviceDescriptor
) -> None:
    """Discover the custom integration through its manifest matcher."""
    mock_connection.emit(
        AddedEvent(descriptor=replace(descriptor, dev_eui="0201010101010102"))
    )
    await hass.async_block_till_done()
    assert any(
        flow["handler"] == DOMAIN for flow in hass.config_entries.flow.async_progress()
    )
