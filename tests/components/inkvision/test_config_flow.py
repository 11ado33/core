"""Tests for the inkVision config flow."""

from ipaddress import ip_address
from unittest.mock import MagicMock

from pyinkvision import InkVisionConnectionError, InkVisionResponseError
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.inkvision.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import HOST, MAC

ZEROCONF_DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address(HOST),
    ip_addresses=[ip_address(HOST)],
    hostname="homebrainz.local.",
    name="atmos-clock._http._tcp.local.",
    port=80,
    type="_http._tcp.local.",
    properties={"mac": "58:8C:81:41:C6:10"},
)


@pytest.mark.usefixtures("mock_setup_entry", "mock_inkvision_client")
async def test_user_flow(hass: HomeAssistant) -> None:
    """Test adding a device by its address."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Atmos Smart Clock"
    assert result["data"] == {CONF_HOST: HOST}
    assert result["result"].unique_id == MAC


@pytest.mark.usefixtures("mock_setup_entry")
@pytest.mark.parametrize(
    ("reply", "error"),
    [
        pytest.param(
            InkVisionConnectionError("timeout"), "cannot_connect", id="timeout"
        ),
        pytest.param(
            InkVisionResponseError("invalid JSON", 200),
            "not_inkvision_device",
            id="invalid_reply",
        ),
        pytest.param({"device": "Something"}, "not_inkvision_device", id="no_mac"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_inkvision_client: MagicMock,
    reply: Exception | dict[str, str],
    error: str,
) -> None:
    """Test the errors of the user step, and recovering from them."""
    # The first status request gets the reply, the next one the fixture.
    mock_inkvision_client.get_status.side_effect = [
        reply,
        mock_inkvision_client.get_status.return_value,
    ]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_setup_entry", "mock_inkvision_client")
async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test adding a device that is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_setup_entry", "mock_inkvision_client")
async def test_zeroconf_flow(hass: HomeAssistant) -> None:
    """Test adding a discovered device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"] == {"name": "Atmos Smart Clock"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Atmos Smart Clock"
    assert result["data"] == {CONF_HOST: HOST}
    assert result["result"].unique_id == MAC


@pytest.mark.usefixtures("mock_setup_entry", "mock_inkvision_client")
async def test_zeroconf_updates_host(hass: HomeAssistant) -> None:
    """Test that discovering a configured device updates its address."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=MAC, data={CONF_HOST: "192.168.1.2"}, version=3
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == HOST


@pytest.mark.parametrize(
    ("side_effect", "reason"),
    [
        pytest.param(
            InkVisionConnectionError("timeout"), "cannot_connect", id="timeout"
        ),
        pytest.param(
            InkVisionResponseError("invalid JSON", 200),
            "not_inkvision_device",
            id="invalid_reply",
        ),
    ],
)
async def test_zeroconf_errors(
    hass: HomeAssistant,
    mock_inkvision_client: MagicMock,
    side_effect: Exception,
    reason: str,
) -> None:
    """Test discovering a device that can't be set up."""
    mock_inkvision_client.get_status.side_effect = side_effect

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason
