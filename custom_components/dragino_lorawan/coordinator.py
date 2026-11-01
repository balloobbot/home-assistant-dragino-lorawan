"""Dragino device updates."""

import logging
from typing import override

from homeassistant.components.lorawan import device_identifier
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ._vendor.dragino_lorawan import DraginoDevice
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DraginoCoordinator(DataUpdateCoordinator[DraginoDevice]):
    """Coordinate Dragino device updates."""

    def __init__(self, hass: HomeAssistant, device: DraginoDevice) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # DeviceManager owns the coordinator's lifecycle.
            config_entry=None,
            name=device.descriptor.name,
        )
        self.async_set_updated_data(device)
        self._unsubscribe = device.add_update_listener(self._async_device_updated)

    @property
    def device_info(self) -> DeviceInfo:
        """Describe this device for its entities."""
        return DeviceInfo(
            identifiers={device_identifier(DOMAIN, self.data)},
            name=self.data.descriptor.name,
            manufacturer="Dragino",
            model=self.data.model_name,
            model_id=self.data.model_name,
        )

    @callback
    def _async_device_updated(self) -> None:
        """Update entities."""
        self.async_set_updated_data(self.data)

    @override
    async def async_shutdown(self) -> None:
        """Unsubscribe from device updates."""
        self._unsubscribe()
        await super().async_shutdown()
