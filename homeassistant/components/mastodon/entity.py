"""Base class for Mastodon entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN, INSTANCE_VERSION
from .coordinator import MastodonConfigEntry, MastodonCoordinator
from .utils import construct_mastodon_username


class MastodonEntity(CoordinatorEntity[MastodonCoordinator]):
    """Defines a base Mastodon entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MastodonCoordinator,
        description: EntityDescription,
        data: MastodonConfigEntry,
    ) -> None:
        """Initialize Mastodon entity."""
        super().__init__(coordinator)
        unique_id = data.unique_id
        assert unique_id is not None
        self._attr_unique_id = f"{unique_id}_{description.key}"

        name = "Mastodon"
        if data.title != DEFAULT_NAME:
            name = f"Mastodon {data.title}"

        full_account_name = construct_mastodon_username(
            data.runtime_data.instance, data.runtime_data.account
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="Mastodon gGmbH",
            model=full_account_name,
            sw_version=data.runtime_data.instance[INSTANCE_VERSION],
            name=name,
        )

        self.entity_description = description
