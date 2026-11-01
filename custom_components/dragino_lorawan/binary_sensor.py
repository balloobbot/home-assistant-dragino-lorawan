"""Dragino binary sensors."""

from typing import TYPE_CHECKING, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.lorawan import LoRaWANEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DraginoConfigEntry
from ._vendor.dragino_lorawan import LDS02, LWL02, DraginoDevice
from .coordinator import DraginoCoordinator
from .entity import DraginoEntity, async_setup_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DraginoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dragino binary sensors."""
    async_setup_entities(
        hass,
        entry,
        async_add_entities,
        lambda coordinator: [
            DraginoDigitalInput(coordinator, channel) for channel in (1, 2)
        ],
    )

    @callback
    def added(coordinator: DraginoCoordinator) -> None:
        if isinstance(coordinator.data, (LDS02, LWL02)):
            async_add_entities(
                [
                    ContactSensor(
                        coordinator,
                        BinarySensorEntityDescription(
                            key="contact"
                            if isinstance(coordinator.data, LDS02)
                            else "moisture",
                            device_class=(
                                BinarySensorDeviceClass.DOOR
                                if isinstance(coordinator.data, LDS02)
                                else BinarySensorDeviceClass.MOISTURE
                            ),
                        ),
                    )
                ]
            )

        if isinstance(coordinator.data, LDS02):
            async_add_entities(
                [
                    ContactSensor(
                        coordinator,
                        BinarySensorEntityDescription(
                            key="alarm",
                            translation_key="door_open_alarm",
                            device_class=BinarySensorDeviceClass.PROBLEM,
                        ),
                    )
                ]
            )

    entry.async_on_unload(entry.runtime_data.subscribe_coordinator_added(added))


class DraginoDigitalInput(DraginoEntity, BinarySensorEntity):
    """Read a digital input level; counting modes do not report levels."""

    def __init__(self, coordinator: DraginoCoordinator, channel: int) -> None:
        """Bind a digital input channel."""
        super().__init__(
            coordinator, BinarySensorEntityDescription(key="digital_input"), channel
        )

    @property
    @override
    def is_on(self) -> bool | None:
        return self.device.digital_inputs[self.channel]


class ContactSensor(LoRaWANEntity[DraginoDevice], BinarySensorEntity):
    """Represent a door opening or water leak."""

    coordinator: DraginoCoordinator

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @property
    @override
    def is_on(self) -> bool | None:
        device = self.device
        if TYPE_CHECKING:
            assert isinstance(device, (LDS02, LWL02))
        return device.alarm if self.entity_description.key == "alarm" else device.active
