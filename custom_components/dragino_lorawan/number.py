"""Dragino numbers."""

from typing import override

from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
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
    """Set up Dragino numbers."""

    @callback
    def added(coordinator: DraginoCoordinator) -> None:
        if isinstance(coordinator.data, LWL02):
            async_add_entities([DraginoReportingInterval(coordinator)])

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class DraginoReportingInterval(LoRaWANEntity[LWL02], NumberEntity):
    """Request the periodic reporting interval."""

    coordinator: DraginoCoordinator

    def __init__(self, coordinator: DraginoCoordinator) -> None:
        """Initialize the interval control."""
        super().__init__(
            coordinator,
            NumberEntityDescription(
                key="reporting_interval",
                translation_key="reporting_interval",
                entity_category=EntityCategory.CONFIG,
                native_unit_of_measurement=UnitOfTime.SECONDS,
                native_min_value=1,
                native_max_value=0xFFFFFF,
                native_step=1,
                mode=NumberMode.BOX,
            ),
        )

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @override
    async def async_set_native_value(self, value: float) -> None:
        if value % 1:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="interval_whole_seconds"
            )
        try:
            await self.device.async_set_reporting_interval(int(value))
        except (DownlinkError, TimeoutError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
        self._attr_native_value = value
        self.async_write_ha_state()
