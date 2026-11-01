"""Tests for LT-22222-L inputs and outputs."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from lorawan_connection import (
    AckEvent,
    DeviceDescriptor,
    Downlink,
    DownlinkError,
    RemovedEvent,
    UplinkEvent,
)
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.dragino_lorawan._vendor.dragino_lorawan import LT22222


@pytest.fixture
def descriptor() -> DeviceDescriptor:
    """Describe an LT-22222-L on ChirpStack."""
    brand_id, model_id = LT22222.identifiers["chirpstack"]
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Garden",
        application_id="application",
        profile_id="profile",
        stack="chirpstack",
        brand_id=brand_id,
        model_id=model_id,
    )


@pytest.fixture
def mock_connection(descriptor: DeviceDescriptor) -> MockConnection:
    """Provide a ChirpStack connection."""
    return MockConnection([descriptor], stack_type="chirpstack")


@pytest.fixture
async def setup_device(
    hass: HomeAssistant,
    connection_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
) -> None:
    """Set up the Dragino entities."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("setup_device")
@pytest.mark.parametrize(
    ("entity", "service", "payload"),
    [
        ("relay_1", "turn_on", "030111"),
        ("relay_2", "turn_off", "031100"),
        ("digital_output_1", "turn_on", "02011111"),
        ("digital_output_2", "turn_off", "02110011"),
    ],
)
async def test_commands(
    hass: HomeAssistant,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
    entity: str,
    service: str,
    payload: str,
) -> None:
    """Wait for acknowledgement and keep state based on telemetry."""

    async def send(downlink: Downlink) -> str:
        assert downlink.data.hex() == payload
        assert downlink.f_port == 2
        assert downlink.confirmed
        mock_connection.emit(
            AckEvent(
                received_at=datetime.now(UTC),
                descriptor=descriptor,
                queue_item_id="command",
                acknowledged=True,
            )
        )
        return "command"

    with patch.object(mock_connection, "async_send_downlink", side_effect=send):
        await hass.services.async_call(
            "switch", service, {"entity_id": f"switch.garden_{entity}"}, blocking=True
        )
    assert hass.states.get(f"switch.garden_{entity}").state == "unknown"
    mock_connection.emit(
        UplinkEvent(
            received_at=datetime.now(UTC),
            descriptor=descriptor,
            f_port=2,
            data=bytes.fromhex("04ab04ac13101300df0041"),
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get("switch.garden_relay_1").state == "on"
    assert hass.states.get("sensor.garden_voltage_1").state == "1.195"
    assert hass.states.get("sensor.garden_current_1").state == "4.88"
    assert hass.states.get("binary_sensor.garden_digital_input_1").state == "on"
    mock_connection.emit(RemovedEvent(descriptor=descriptor))
    await hass.async_block_till_done()
    assert hass.states.get("switch.garden_relay_1") is None


@pytest.mark.usefixtures("setup_device")
async def test_command_failure(
    hass: HomeAssistant, mock_connection: MockConnection
) -> None:
    """Translate a rejected downlink into a service error."""
    with (
        patch.object(
            mock_connection,
            "async_send_downlink",
            side_effect=DownlinkError("Read-only API key"),
        ),
        pytest.raises(HomeAssistantError, match="Unable to send"),
    ):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.garden_relay_1"}, blocking=True
        )


@pytest.mark.usefixtures("setup_device")
async def test_timeout(hass: HomeAssistant) -> None:
    """Stop waiting when no acknowledgement arrives."""
    with (
        patch(
            "custom_components.dragino_lorawan.switch.timeout",
            return_value=asyncio.timeout(0),
        ),
        pytest.raises(HomeAssistantError, match="Timed out"),
    ):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.garden_relay_1"}, blocking=True
        )
