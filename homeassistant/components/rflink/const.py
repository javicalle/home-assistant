"""Constants used by RFLink integration."""

import voluptuous as vol

import homeassistant.helpers.config_validation as cv

# #### ATTRIBUTES ####
ATTR_EVENT = "event"
ATTR_STATE = "state"

# #### CONFIGURATIONS ####
CONF_ALIASES = "aliases"
CONF_GROUP_ALIASES = "group_aliases"
CONF_GROUP = "group"
CONF_NOGROUP_ALIASES = "nogroup_aliases"
CONF_DEVICE_DEFAULTS = "device_defaults"
CONF_DEVICE_ID = "device_id"
CONF_DEVICES = "devices"
CONF_AUTOMATIC_ADD = "automatic_add"
CONF_FIRE_EVENT = "fire_event"
CONF_IGNORE_DEVICES = "ignore_devices"
CONF_RECONNECT_INTERVAL = "reconnect_interval"
CONF_SIGNAL_REPETITIONS = "signal_repetitions"
CONF_WAIT_FOR_ACK = "wait_for_ack"
CONF_OFF_DELAY = "off_delay"
CONF_SENSOR_TYPE = "sensor_type"
# Defaults
DEFAULT_FORCE_UPDATE = False
DEFAULT_RECONNECT_INTERVAL = 10
DEFAULT_SIGNAL_REPETITIONS = 1
CONNECTION_TIMEOUT = 10

# #### SERVICE ####
SERVICE_DIM = "dim"
SERVICE_SEND_COMMAND = "send_command"

# #### Received EVENTS attributes ####
EVENT_BUTTON_PRESSED = "button_pressed"
EVENT_KEY_COMMAND = "command"
EVENT_KEY_ID = "id"
EVENT_KEY_SENSOR = "sensor"
EVENT_KEY_UNIT = "unit"
EVENT_KEY_VALUE = "value"
EVENT_KEY_VERSION = "version"

# #### Sending COMMAND attributes ####
COMMAND_PROTOCOL = "protocol"
COMMAND_ID = "id"
COMMAND_SWITCH = "switch"
COMMAND_COMMAND = "command"
# RFLink command VALUES
COMMAND_ON = "on"
COMMAND_OFF = "off"
COMMAND_UP = "up"
COMMAND_DOWN = "down"
COMMAND_STOP = "stop"
COMMAND_ALLON = "allon"
COMMAND_ALLOFF = "alloff"

# #### Entity TYPES #####
TYPE_DIMMABLE = "dimmable"
TYPE_HYBRID = "hybrid"
TYPE_SWITCHABLE = "switchable"
TYPE_TOGGLE = "toggle"
TYPE_STANDARD = "standard"
TYPE_INVERTED = "inverted"

# #### REGISTER #####
DATA_DEVICE_REGISTER = "rflink_device_register"
DATA_ENTITY_LOOKUP = "rflink_entity_lookup"
DATA_ENTITY_GROUP_LOOKUP = "rflink_entity_group_only_lookup"
# Signals
SIGNAL_AVAILABILITY = "rflink_device_available"
SIGNAL_HANDLE_EVENT = "rflink_handle_event_{}"

# #### Integration constants ####
DOMAIN = "rflink"
RFLINK_GROUP_COMMANDS = [COMMAND_ALLON, COMMAND_ALLOFF]
TMP_ENTITY = "tmp.{}"
PARALLEL_UPDATES = 0

# #### SCHEMES ####
DEVICE_DEFAULTS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_FIRE_EVENT, default=False): cv.boolean,
        vol.Optional(
            CONF_SIGNAL_REPETITIONS, default=DEFAULT_SIGNAL_REPETITIONS
        ): vol.Coerce(int),
    }
)

SENSOR_ICONS = {
    "humidity": "mdi:water-percent",
    "battery": "mdi:battery",
    "temperature": "mdi:thermometer",
}
