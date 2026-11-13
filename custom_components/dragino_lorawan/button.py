"""Dragino buttons."""

from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lorawan_connection import DownlinkError

from . import DraginoConfigEntry
from ._vendor.dragino_lorawan import LWL02
from .const import DOMAIN
from .coordinator import DraginoCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DraginoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dragino buttons."""

    @callback
    def added(coordinator: DraginoCoordinator) -> None:
        if isinstance(coordinator.data, LWL02):
            async_add_entities([DraginoRequestReset(coordinator)])

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class DraginoRequestReset(LoRaWANEntity[LWL02], ButtonEntity):
    """Request a reset of the leak counters."""

    coordinator: DraginoCoordinator

    def __init__(self, coordinator: DraginoCoordinator) -> None:
        """Initialize the reset button."""
        super().__init__(
            coordinator,
            ButtonEntityDescription(
                key="request_reset",
                translation_key="request_reset",
                entity_category=EntityCategory.CONFIG,
            ),
        )

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @override
    async def async_press(self) -> None:
        try:
            await self.device.async_reset_count()
        except (DownlinkError, TimeoutError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
