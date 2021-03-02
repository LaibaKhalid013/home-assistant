"""Closures channels module for Zigbee Home Automation."""
import zigpy.zcl.clusters.closures as closures

from homeassistant.core import callback

from .. import registries
from ..const import REPORT_CONFIG_IMMEDIATE, SIGNAL_ATTR_UPDATED
from .base import ClientChannel, ZigbeeChannel


@registries.ZIGBEE_CHANNEL_REGISTRY.register(closures.DoorLock.cluster_id)
class DoorLockChannel(ZigbeeChannel):
    """Door lock channel."""

    _value_attribute = 0
    REPORT_CONFIG = ({"attr": "lock_state", "config": REPORT_CONFIG_IMMEDIATE},)

    async def async_update(self):
        """Retrieve latest state."""
        result = await self.get_attribute_value("lock_state", from_cache=True)
        if result is not None:
            self.async_send_signal(
                f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}", 0, "lock_state", result
            )

    @callback
    def cluster_command(self, tsn, command_id, args):
        """Handle a cluster command received on this cluster."""

        if self._cluster.client_commands is None:
            return

        command_name = self._cluster.client_commands.get(command_id, [command_id])[0]
        if command_name == "operation_event_notification":
            self.zha_send_event(
                command_name,
                {
                    "source": args[0].name,
                    "operation": args[1].name,
                    "code_slot": (args[2] + 1),  # start code slots at 1
                },
            )

    @callback
    def attribute_updated(self, attrid, value):
        """Handle attribute update from lock cluster."""
        attr_name = self.cluster.attributes.get(attrid, [attrid])[0]
        self.debug(
            "Attribute report '%s'[%s] = %s", self.cluster.name, attr_name, value
        )
        if attrid == self._value_attribute:
            self.async_send_signal(
                f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}", attrid, attr_name, value
            )

    async def async_set_user_code(self, code_slot: int, user_code: str) -> None:
        """Set the user code for the code slot."""

        set_pin_code = self.__getattr__("set_pin_code")
        await set_pin_code(
            *(
                code_slot - 1,  # start code slots at 1
                closures.DoorLock.UserStatus.Enabled,
                closures.DoorLock.UserType.Unrestricted,
                user_code,
            ),
        )

    async def async_enable_user_code(self, code_slot: int) -> None:
        """Enable the code slot."""

        set_user_status = self.__getattr__("set_user_status")
        await set_user_status(*(code_slot - 1, closures.DoorLock.UserStatus.Enabled))

    async def async_disable_user_code(self, code_slot: int) -> None:
        """Disable the code slot."""

        set_user_status = self.__getattr__("set_user_status")
        await set_user_status(*(code_slot - 1, closures.DoorLock.UserStatus.Disabled))

    async def async_get_user_code(self, code_slot: int) -> int:
        """Get the user code from the code slot."""

        get_pin_code = self.__getattr__("get_pin_code")
        result = await get_pin_code(*(code_slot - 1,))
        return result

    async def async_clear_user_code(self, code_slot: int) -> None:
        """Clear the code slot."""

        clear_pin_code = self.__getattr__("clear_pin_code")
        await clear_pin_code(*(code_slot - 1,))

    async def async_clear_all_user_codes(self) -> None:
        """Clear all code slots."""

        clear_all_pin_codes = self.__getattr__("clear_all_pin_codes")
        await clear_all_pin_codes(*())

    async def async_set_user_type(self, code_slot: int, user_type: str) -> None:
        """Set user type."""

        set_user_type = self.__getattr__("set_user_type")
        await set_user_type(*(code_slot - 1, user_type))

    async def async_get_user_type(self, code_slot: int) -> str:
        """Get user type."""

        get_user_type = self.__getattr__("get_user_type")
        result = await get_user_type(*(code_slot - 1))
        return result


@registries.ZIGBEE_CHANNEL_REGISTRY.register(closures.Shade.cluster_id)
class Shade(ZigbeeChannel):
    """Shade channel."""


@registries.CLIENT_CHANNELS_REGISTRY.register(closures.WindowCovering.cluster_id)
class WindowCoveringClient(ClientChannel):
    """Window client channel."""


@registries.ZIGBEE_CHANNEL_REGISTRY.register(closures.WindowCovering.cluster_id)
class WindowCovering(ZigbeeChannel):
    """Window channel."""

    _value_attribute = 8
    REPORT_CONFIG = (
        {"attr": "current_position_lift_percentage", "config": REPORT_CONFIG_IMMEDIATE},
    )

    async def async_update(self):
        """Retrieve latest state."""
        result = await self.get_attribute_value(
            "current_position_lift_percentage", from_cache=False
        )
        self.debug("read current position: %s", result)
        if result is not None:
            self.async_send_signal(
                f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}",
                8,
                "current_position_lift_percentage",
                result,
            )

    @callback
    def attribute_updated(self, attrid, value):
        """Handle attribute update from window_covering cluster."""
        attr_name = self.cluster.attributes.get(attrid, [attrid])[0]
        self.debug(
            "Attribute report '%s'[%s] = %s", self.cluster.name, attr_name, value
        )
        if attrid == self._value_attribute:
            self.async_send_signal(
                f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}", attrid, attr_name, value
            )
