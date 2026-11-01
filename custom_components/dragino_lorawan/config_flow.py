"""Dragino config flow."""

from typing import Any, override

from homeassistant.components.lorawan import (
    LoRaWANDiscoveryInfo,
    NoConnectionsError,
    NoSupportedDevicesError,
    async_validate_devices,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from ._vendor.dragino_lorawan import DraginoDevices
from .const import DOMAIN


class DraginoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure Dragino LoRaWAN."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user setup."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm(user_input)

    @override
    async def async_step_integration_discovery(
        self, discovery_info: LoRaWANDiscoveryInfo | dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle LoRaWAN discovery."""
        return await self.async_step_user()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm device setup."""
        try:
            await async_validate_devices(
                self.hass,
                create_collection=DraginoDevices,
                is_supported=lambda device: isinstance(device, DraginoDevices.DEVICES),
            )
        except NoConnectionsError:
            return self.async_abort(reason="no_lorawan_connections")
        except NoSupportedDevicesError:
            return self.async_abort(reason="no_supported_devices")
        if user_input is not None:
            return self.async_create_entry(title="Dragino", data={})
        return self.async_show_form(step_id="confirm")
