"""Backup manager for the Backup integration."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from securetar import SecureTarFile, atomic_contents_add

from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import json as json_util
from homeassistant.util.dt import now

from .const import EXCLUDE_FROM_BACKUP, LOGGER


@dataclass
class Backup:
    """Backup class."""

    slug: str
    name: str
    date: str
    path: Path
    size: float

    def as_dict(self) -> dict:
        """Return a dict representation of this backup."""
        return {**asdict(self), "path": self.path.as_posix()}


class BackupManager:
    """Backup manager for the Backup integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the backup manager."""
        self.hass = hass
        self.backup_dir = Path(hass.config.path("backups"))
        self.backing_up = False
        self._loaded = False
        self._backups: dict[str, Backup] = {}

    async def load_backups(self) -> None:
        """Load data of stored backup files."""
        backups = {}

        def _read_backup_info(backup_path: Path) -> None:
            with SecureTarFile(backup_path, "r", gzip=False) as backup_file:
                if data_file := backup_file.extractfile("./backup.json"):
                    data = json.loads(data_file.read())
                    backup = Backup(
                        slug=data["slug"],
                        name=data["name"],
                        date=data["date"],
                        path=backup_path,
                        size=round(backup_path.stat().st_size / 1_048_576, 2),
                    )
                    backups[backup.slug] = backup

        await asyncio.gather(
            self.hass.async_add_executor_job(_read_backup_info, backup_path)
            for backup_path in self.backup_dir.glob("*.tar")
        )

        LOGGER.debug("Loaded %s backups", len(backups))
        self._backups = backups
        self._loaded = True

    async def get_backups(self) -> dict[str, Backup]:
        """Return backups."""
        if not self._loaded:
            await self.load_backups()

        return self._backups

    async def get_backup(self, slug: str) -> Backup | None:
        """Return a backup."""
        if not self._loaded:
            await self.load_backups()

        return self._backups.get(slug)

    async def remove_backup(self, slug: str) -> None:
        """Remove a backup."""
        if (backup := await self.get_backup(slug)) is None:
            return

        await self.hass.async_add_executor_job(backup.path.unlink, True)
        LOGGER.debug("Removed backup located at %s", backup.path)
        self._backups.pop(slug)

    async def generate_backup(self) -> Backup:
        """Generate a backup."""
        if self.backing_up:
            raise HomeAssistantError("Backup already in progress")

        try:
            self.backing_up = True
            backup_name = f"Core {HAVERSION}"
            date_str = now().isoformat()
            slug = _generate_slug(date_str, backup_name)

            backup_data = {
                "slug": slug,
                "name": backup_name,
                "date": date_str,
                "type": "partial",
                "folders": ["homeassistant"],
                "homeassistant": {"version": HAVERSION},
                "compressed": True,
            }
            tar_file_path = Path(self.backup_dir, f"{slug}.tar")

            if not self.backup_dir.exists():
                LOGGER.debug("Creating backup directory")
                self.hass.async_add_executor_job(self.backup_dir.mkdir)

            def _create_backup() -> None:
                with TemporaryDirectory() as tmp_dir:
                    tmp_dir_path = Path(tmp_dir)
                    json_util.save_json(
                        tmp_dir_path.joinpath("./backup.json").as_posix(),
                        backup_data,
                    )
                    with SecureTarFile(tar_file_path, "w", gzip=False) as tar_file:
                        with SecureTarFile(
                            tmp_dir_path.joinpath("./homeassistant.tar.gz").as_posix(),
                            "w",
                        ) as core_tar:
                            atomic_contents_add(
                                tar_file=core_tar,
                                origin_path=Path(self.hass.config.path()),
                                excludes=EXCLUDE_FROM_BACKUP,
                                arcname="data",
                            )
                        tar_file.add(tmp_dir_path, arcname=".")

            await self.hass.async_add_executor_job(_create_backup)
            backup = Backup(
                slug=slug,
                name=backup_name,
                date=date_str,
                path=tar_file_path,
                size=round(tar_file_path.stat().st_size / 1_048_576, 2),
            )
            self._backups[slug] = backup
            LOGGER.debug("Generated new backup with slug %s", slug)
            return backup
        finally:
            self.backing_up = False


def _generate_slug(date: str, name: str) -> str:
    """Generate a backup slug."""
    return hashlib.sha1(f"{date} - {name}".lower().encode()).hexdigest()[:8]
