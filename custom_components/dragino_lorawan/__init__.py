"""Support Dragino devices over LoRaWAN."""

from homeassistant.components.lorawan import DeviceManager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from lorawan_connection import ConnectionUnavailable

from ._vendor.dragino_lorawan import DraginoDevice, DraginoDevices
from .const import DOMAIN
from .coordinator import DraginoCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
type DraginoConfigEntry = ConfigEntry[DeviceManager[DraginoDevice, DraginoCoordinator]]
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: DraginoConfigEntry) -> None:
    """Set up Dragino devices across the available LoRaWAN connections."""
    manager = entry.runtime_data = DeviceManager(
        hass,
        entry,
        create_collection=DraginoDevices,
        create_coordinator=DraginoCoordinator,
    )
    entry.async_on_unload(manager.close)
    try:
        await manager.async_setup()
    except ConnectionUnavailable as err:
        raise ConfigEntryNotReady(str(err)) from err
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: DraginoConfigEntry) -> None:
    """Unload Dragino LoRaWAN."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
