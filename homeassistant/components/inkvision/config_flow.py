"""Config flow for inkVision."""

from typing import Any, override

import probatio
from pyinkvision import (
    InkVisionClient,
    InkVisionConnectionError,
    InkVisionResponseError,
)

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = probatio.Schema({probatio.Required(CONF_HOST): str})


class NotInkVisionDevice(Exception):
    """The device doesn't answer like an inkVision device."""


class InkVisionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for inkVision."""

    # Matches the entries of the custom integration this one replaces, so they
    # load without a migration.
    VERSION = 3

    _host: str
    _name: str

    async def _async_get_device(self, host: str) -> tuple[str, str]:
        """Return the name and MAC address of the device at host."""
        client = InkVisionClient(host, async_get_clientsession(self.hass))
        status = await client.get_status()
        name = status.get("device")
        mac = status.get("mac_address")
        if not isinstance(name, str) or not isinstance(mac, str):
            raise NotInkVisionDevice
        return name, format_mac(mac)

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                name, mac = await self._async_get_device(user_input[CONF_HOST])
            except InkVisionConnectionError:
                errors["base"] = "cannot_connect"
            except InkVisionResponseError, NotInkVisionDevice:
                errors["base"] = "not_inkvision_device"
            else:
                await self.async_set_unique_id(mac, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @override
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.host
        try:
            name, mac = await self._async_get_device(host)
        except InkVisionConnectionError:
            return self.async_abort(reason="cannot_connect")
        except InkVisionResponseError, NotInkVisionDevice:
            return self.async_abort(reason="not_inkvision_device")

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._host = host
        self._name = name
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name, data={CONF_HOST: self._host}
            )

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._name},
        )
