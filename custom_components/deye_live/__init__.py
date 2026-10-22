"""Local, read-only Deye telemetry and its bundled dashboard card."""
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import CARD_URL, DOMAIN
from .coordinator import DeyeCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass, config):
    await hass.http.async_register_static_paths([
        StaticPathConfig("/deye_live", str(Path(__file__).parent / "www"), False)
    ])
    frontend.add_extra_js_url(hass, CARD_URL)
    return True


async def async_setup_entry(hass, entry):
    coordinator = DeyeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
