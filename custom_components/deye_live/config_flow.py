"""UI setup validates both the inverter identity and real power registers."""
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .client import DeyeClient
from .const import DEFAULT_INTERVAL, DOMAIN
from .protocol import ProtocolError


def schema(defaults):
    return vol.Schema({
        vol.Required("host", default=defaults.get("host", "")): str,
        vol.Required("port", default=defaults.get("port", 502)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required("unit", default=defaults.get("unit", 1)): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        vol.Required("scan_interval", default=defaults.get("scan_interval", DEFAULT_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
        vol.Required("invert_grid", default=defaults.get("invert_grid", False)): bool,
        vol.Required("invert_battery", default=defaults.get("invert_battery", False)): bool,
    })


async def validate(hass, data, serial=None):
    client = DeyeClient(data["host"].strip(), data["port"], data["unit"], expected_serial=serial)
    return await hass.async_add_executor_job(client.poll)


class DeyeFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                result = await validate(self.hass, user_input)
            except OSError:
                errors["base"] = "cannot_connect"
            except (ProtocolError, ValueError):
                errors["base"] = "unsupported_device"
            else:
                await self.async_set_unique_id(result["serial"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Deye Live {result['serial'][-4:]}",
                                               data={**user_input, "host": user_input["host"].strip()})
        return self.async_show_form(step_id="user", data_schema=schema(user_input or {}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DeyeOptionsFlow()


class DeyeOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        defaults = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            try:
                await validate(self.hass, user_input, self.config_entry.unique_id)
            except OSError:
                errors["base"] = "cannot_connect"
            except (ProtocolError, ValueError):
                errors["base"] = "unsupported_device"
            else:
                return self.async_create_entry(title="", data={**user_input, "host": user_input["host"].strip()})
        return self.async_show_form(step_id="init", data_schema=schema(user_input or defaults), errors=errors)
