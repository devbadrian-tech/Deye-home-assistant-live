"""One serialized poll shared by every entity."""
from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import DeyeClient
from .const import DEFAULT_INTERVAL, DOMAIN
from .protocol import ProtocolError

_LOGGER = logging.getLogger(__name__)


class DeyeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        options = {**entry.data, **entry.options}
        self.serial = entry.unique_id
        self.interval = options.get("scan_interval", DEFAULT_INTERVAL)
        self.client = DeyeClient(
            options["host"], options.get("port", 502), options.get("unit", 1),
            expected_serial=self.serial,
            invert_grid=options.get("invert_grid", False),
            invert_battery=options.get("invert_battery", False),
        )
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=self.interval))

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.poll)
        except (OSError, ProtocolError, ValueError) as err:
            raise UpdateFailed(f"No fresh reading from the logger: {err}") from err
