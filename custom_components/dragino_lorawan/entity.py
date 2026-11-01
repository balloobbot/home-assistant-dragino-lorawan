"""Dragino entities."""

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, override

from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DraginoConfigEntry
from ._vendor.dragino_lorawan import LT22222, DraginoDevice
from .coordinator import DraginoCoordinator


@callback
def async_setup_entities(
    hass: HomeAssistant,
    entry: DraginoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[DraginoCoordinator], list[DraginoEntity]],
) -> None:
    """Add entities for existing and future models."""

    @callback
    def added(coordinator: DraginoCoordinator) -> None:
        if isinstance(coordinator.data, LT22222):
            async_add_entities(factory(coordinator))

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class DraginoEntity(LoRaWANEntity[DraginoDevice]):
    """Represent an LT-22222-L channel."""

    coordinator: DraginoCoordinator

    def __init__(
        self,
        coordinator: DraginoCoordinator,
        description: EntityDescription,
        channel: int,
    ) -> None:
        """Initialize a channel entity."""
        super().__init__(
            coordinator,
            replace(
                description,
                key=f"{description.key}_{channel}",
                translation_key=description.key,
                translation_placeholders={"channel": str(channel)},
            ),
        )
        self.channel = channel

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @property
    @override
    def device(self) -> LT22222:
        """Return the LT-22222-L device."""
        device = self.coordinator.data
        if TYPE_CHECKING:
            assert isinstance(device, LT22222)
        return device
