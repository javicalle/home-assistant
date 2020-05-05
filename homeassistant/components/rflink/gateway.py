"""Handle RFLink gateways."""
import asyncio
import logging

import async_timeout
from rflink.protocol import create_rflink_connection
from serial import SerialException

from homeassistant.const import (
    CONF_COMMAND,
    CONF_HOST,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import CoreState, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import HomeAssistantType

from .const import (
    CONF_DEVICE_ID,
    CONF_IGNORE_DEVICES,
    CONF_RECONNECT_INTERVAL,
    CONF_WAIT_FOR_ACK,
    CONNECTION_TIMEOUT,
    DATA_DEVICE_REGISTER,
    DATA_ENTITY_GROUP_LOOKUP,
    DATA_ENTITY_LOOKUP,
    EVENT_KEY_COMMAND,
    EVENT_KEY_ID,
    EVENT_KEY_SENSOR,
    RFLINK_GROUP_COMMANDS,
    SIGNAL_AVAILABILITY,
    SIGNAL_HANDLE_EVENT,
    TMP_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


def identify_event_type(event):
    """Look at event to determine type of device.

    Async friendly.
    """
    if EVENT_KEY_COMMAND in event:
        return EVENT_KEY_COMMAND
    if EVENT_KEY_SENSOR in event:
        return EVENT_KEY_SENSOR
    return "unknown"


class RflinkGateway:
    """RFLink gateway operations."""

    def __init__(self, hass: HomeAssistantType, config,) -> None:
        """Gateway initialization."""
        self._hass = hass
        # TCP port when host configured, otherwise serial port
        self._port = config[CONF_PORT]
        # When connecting to tcp host instead of serial port (optional)
        self._host = config.get(CONF_HOST)
        self._wait_for_ack = config.get(CONF_WAIT_FOR_ACK)
        self._reconnect_interval = config.get(CONF_RECONNECT_INTERVAL)
        self._ignore_devices = config.get(CONF_IGNORE_DEVICES)
        self._protocol = None

    def set_rflink_protocol(self, protocol, wait_ack=None):
        """Set the Rflink asyncio protocol as a class variable."""
        _LOGGER.debug("Setting protocol & wait_ack %s", wait_ack)
        self._protocol = protocol
        if wait_ack is not None:
            self._wait_for_ack = wait_ack

    def is_connected(self):
        """Return connection status."""
        _LOGGER.debug("is_connected: %s", bool(self._protocol))
        return bool(self._protocol)

    async def async_send_command(self, call):
        """Send Rflink command."""
        _LOGGER.debug("Rflink command for %s", str(call.data))
        if not (
            await self.send_command(
                call.data.get(CONF_DEVICE_ID), call.data.get(CONF_COMMAND)
            )
        ):
            _LOGGER.error("Failed Rflink command for %s", str(call.data))

    async def send_command(self, device_id, action):
        """Send device command to Rflink and wait for acknowledgement."""
        # return await self._protocol.send_command_ack(device_id, action)
        if not self.is_connected():
            raise HomeAssistantError("Cannot send command, not connected!")

        if self._wait_for_ack:
            # Puts command on outgoing buffer then waits for Rflink to confirm
            # the command has been send out in the ether.
            await self._protocol.send_command_ack(device_id, action)
        else:
            # Puts command on outgoing buffer and returns straight away.
            # Rflink protocol/transport handles asynchronous writing of buffer
            # to serial/tcp device. Does not wait for command send
            # confirmation.
            self._protocol.send_command(device_id, action)

    @callback
    def event_callback(self, event):
        """Handle incoming Rflink events.

        Rflink events arrive as dictionaries of varying content
        depending on their type. Identify the events and distribute
        accordingly.
        """
        event_type = identify_event_type(event)
        _LOGGER.debug("event of type %s: %s", event_type, event)

        # Don't propagate non entity events (eg: version string, ack response)
        if event_type not in self._hass.data[DATA_ENTITY_LOOKUP]:
            _LOGGER.debug("unhandled event of type: %s", event_type)
            return

        # Lookup entities who registered this device id as device id or alias
        event_id = event.get(EVENT_KEY_ID)

        is_group_event = (
            event_type == EVENT_KEY_COMMAND
            and event[EVENT_KEY_COMMAND] in RFLINK_GROUP_COMMANDS
        )
        if is_group_event:
            entity_ids = self._hass.data[DATA_ENTITY_GROUP_LOOKUP][event_type].get(
                event_id, []
            )
        else:
            entity_ids = self._hass.data[DATA_ENTITY_LOOKUP][event_type][event_id]

        _LOGGER.debug("entity_ids: %s", entity_ids)
        if entity_ids:
            # Propagate event to every entity matching the device id
            for entity in entity_ids:
                _LOGGER.debug("passing event to %s", entity)
                async_dispatcher_send(
                    self._hass, SIGNAL_HANDLE_EVENT.format(entity), event
                )
        elif not is_group_event:
            # If device is not yet known, register with platform (if loaded)
            if event_type in self._hass.data[DATA_DEVICE_REGISTER]:
                _LOGGER.debug("device_id not known, adding new device")
                # Add bogus event_id first to avoid race if we get another
                # event before the device is created
                # Any additional events received before the device has been
                # created will thus be ignored.
                self._hass.data[DATA_ENTITY_LOOKUP][event_type][event_id].append(
                    TMP_ENTITY.format(event_id)
                )
                self._hass.async_create_task(
                    self._hass.data[DATA_DEVICE_REGISTER][event_type](event)
                )
            else:
                _LOGGER.debug("device_id not known and automatic add disabled")

    @callback
    def reconnect(self, exc=None):
        """Schedule reconnect after connection has been unexpectedly lost."""
        # Reset protocol binding before starting reconnect
        self._protocol = None

        async_dispatcher_send(self._hass, SIGNAL_AVAILABILITY, False)

        # If HA is not stopping, initiate new connection
        if self._hass.state != CoreState.stopping:
            _LOGGER.warning("disconnected from Rflink, reconnecting")
            self._hass.async_create_task(self.connect())

    async def connect(self):
        """Set up connection and hook it into HA for reconnect/shutdown."""
        _LOGGER.info("Initiating Rflink connection")

        # Rflink create_rflink_connection decides based on the value of host
        # (string or None) if serial or tcp mode should be used

        # Initiate serial/tcp connection to Rflink gateway
        connection = create_rflink_connection(
            port=self._port,
            host=self._host,
            event_callback=self.event_callback,
            disconnect_callback=self.reconnect,
            loop=self._hass.loop,
            ignore=self._ignore_devices,
        )

        try:
            with async_timeout.timeout(CONNECTION_TIMEOUT):
                transport, protocol = await connection

        except (
            SerialException,
            ConnectionRefusedError,
            TimeoutError,
            OSError,
            asyncio.TimeoutError,
        ) as exc:
            reconnect_interval = self._reconnect_interval
            _LOGGER.exception(
                "Error connecting to Rflink, reconnecting in %s", reconnect_interval
            )
            # Connection to Rflink device is lost, make entities unavailable
            async_dispatcher_send(self._hass, SIGNAL_AVAILABILITY, False)

            self._hass.loop.call_later(self._reconnect_interval, self.reconnect, exc)
            return

        # There is a valid connection to a Rflink device now so
        # mark entities as available
        async_dispatcher_send(self._hass, SIGNAL_AVAILABILITY, True)

        # Bind protocol to command class to allow entities to send commands
        self._protocol = protocol

        # handle shutdown of Rflink asyncio transport
        self._hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, lambda x: transport.close()
        )

        _LOGGER.info("Connected to Rflink")
