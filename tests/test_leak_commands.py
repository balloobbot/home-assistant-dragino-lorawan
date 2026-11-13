"""LWL02 configuration downlinks."""

from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from lorawan_connection import DeviceDescriptor, Downlink, DownlinkError, UplinkEvent
from lorawan_connection.mock import MockConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.dragino_lorawan._vendor.dragino_lorawan import LWL02


@pytest.fixture(params=["tts", "chirpstack"])
def descriptor(request: pytest.FixtureRequest) -> DeviceDescriptor:
    """Describe an LWL02 on either backend."""
    stack = request.param
    brand, model = LWL02.identifiers[stack]
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Garden",
        stack=stack,
        brand_id=brand,
        model_id=model,
        application_id="app",
        profile_id="profile",
    )


@pytest.fixture
def mock_connection(descriptor: DeviceDescriptor) -> MockConnection:
    """Provide the selected backend."""
    return MockConnection([descriptor], stack_type=descriptor.stack)


@pytest.fixture
async def setup_device(
    hass: HomeAssistant,
    connection_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
    entity_registry_enabled_by_default: None,
) -> None:
    """Set up the leak sensor."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("setup_device")
@pytest.mark.parametrize(
    ("platform", "service", "entity", "data", "payload", "expected_interval"),
    [
        (
            "number",
            "set_value",
            "reporting_interval",
            {"value": 900},
            "01000384",
            "900.0",
        ),
        ("number", "set_value", "reporting_interval", {"value": 1}, "01000001", "1.0"),
        (
            "number",
            "set_value",
            "reporting_interval",
            {"value": 16777215},
            "01ffffff",
            "16777215.0",
        ),
        ("button", "press", "request_reset", {}, "a601", "unknown"),
    ],
)
async def test_queue_command(
    hass: HomeAssistant,
    mock_connection: MockConnection,
    descriptor: DeviceDescriptor,
    platform: str,
    service: str,
    entity: str,
    data: dict[str, int],
    payload: str,
    expected_interval: str,
) -> None:
    """Queue exact bytes without waiting for an ACK or clearing readings locally."""
    entity_id = f"{platform}.garden_{entity}"
    registry_entry = er.async_get(hass).async_get(entity_id)
    assert registry_entry.entity_category is er.EntityCategory.CONFIG
    assert registry_entry.unique_id == f"network:{descriptor.dev_eui}:{entity}"
    assert hass.states.get("number.garden_reporting_interval").state == "unknown"
    mock_connection.emit(
        UplinkEvent(
            descriptor=descriptor,
            received_at=datetime.now(UTC),
            f_port=10,
            data=bytes.fromhex("0c1e0200000400000500"),
        )
    )
    await hass.async_block_till_done()

    async def send(downlink: Downlink) -> str:
        assert downlink.data.hex() == payload
        assert downlink.f_port == 1
        assert not downlink.confirmed
        return "queued"

    with patch.object(
        mock_connection, "async_send_downlink", side_effect=send
    ) as send_mock:
        await hass.services.async_call(
            platform, service, {"entity_id": entity_id, **data}, blocking=True
        )
    send_mock.assert_awaited_once()
    assert hass.states.get("sensor.garden_event_count").state == "4"
    assert hass.states.get("sensor.garden_last_event_duration").state == "5"
    assert (
        hass.states.get("number.garden_reporting_interval").state == expected_interval
    )


@pytest.mark.usefixtures("setup_device")
@pytest.mark.parametrize("error", [DownlinkError("Read-only key"), TimeoutError()])
@pytest.mark.parametrize(
    ("platform", "service", "entity", "data"),
    [
        ("number", "set_value", "reporting_interval", {"value": 900}),
        ("button", "press", "request_reset", {}),
    ],
)
async def test_queue_failure(
    hass: HomeAssistant,
    mock_connection: MockConnection,
    error: Exception,
    platform: str,
    service: str,
    entity: str,
    data: dict[str, int],
) -> None:
    """A rejected request leaves the interval unset."""
    with (
        patch.object(mock_connection, "async_send_downlink", side_effect=error),
        pytest.raises(HomeAssistantError, match="Unable to send"),
    ):
        await hass.services.async_call(
            platform,
            service,
            {"entity_id": f"{platform}.garden_{entity}", **data},
            blocking=True,
        )
    assert hass.states.get("number.garden_reporting_interval").state == "unknown"


@pytest.mark.usefixtures("setup_device")
@pytest.mark.parametrize("value", [0, 16777216, 1.5])
async def test_invalid_interval(
    hass: HomeAssistant, mock_connection: MockConnection, value: float
) -> None:
    """Reject unrepresentable intervals before queueing a command."""
    with (
        patch.object(mock_connection, "async_send_downlink") as send,
        pytest.raises(ServiceValidationError),
    ):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.garden_reporting_interval", "value": value},
            blocking=True,
        )
    send.assert_not_awaited()
