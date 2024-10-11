"""Test Home Assistant secret substitution in YAML files."""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from homeassistant.config import YAML_CONFIG_FILE, load_yaml_config_file
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import yaml
from homeassistant.util.yaml import loader as yaml_loader

from tests.common import get_test_config_dir, patch_yaml_files


@dataclass(frozen=True)
class YamlFile:
    """Represents a .yaml file used for testing."""

    path: Path
    contents: str


def load_config_file(config_file_path: Path, files: list[YamlFile]):
    """Patch secret files and return the loaded config file."""
    patch_files = {x.path.as_posix(): x.contents for x in files}
    with patch_yaml_files(patch_files):
        return load_yaml_config_file(
            config_file_path.as_posix(),
            yaml_loader.Secrets(Path(get_test_config_dir())),
        )


@pytest.fixture
def filepaths() -> dict[str, Path]:
    """Return a dictionary of filepaths for testing."""
    config_dir = Path(get_test_config_dir())
    return {
        "config": config_dir,
        "sub_folder": config_dir / "subFolder",
        "unrelated": config_dir / "unrelated",
    }


@pytest.fixture
def default_config(filepaths) -> YamlFile:
    """Return the default config file for testing."""
    return YamlFile(
        path=filepaths["config"] / YAML_CONFIG_FILE,
        contents=(
            "http:\n"
            "  api_password: !secret http_pw\n"
            "component:\n"
            "  username: !secret comp1_un\n"
            "  password: !secret comp1_pw\n"
            ""
        ),
    )


@pytest.fixture
def default_secrets(filepaths) -> YamlFile:
    """Return the default secrets file for testing."""
    return YamlFile(
        path=filepaths["config"] / yaml.SECRET_YAML,
        contents=(
            "http_pw: pwhttp\n"
            "comp1_un: un1\n"
            "comp1_pw: pw1\n"
            "stale_pw: not_used\n"
            "logger: debug\n"
        ),
    )


def test_secrets_from_yaml(default_config, default_secrets) -> None:
    """Did secrets load ok."""
    loaded_file = load_config_file(
        default_config.path, [default_config, default_secrets]
    )
    expected = {"api_password": "pwhttp"}
    assert expected == loaded_file["http"]

    expected = {"username": "un1", "password": "pw1"}
    assert expected == loaded_file["component"]


def test_secrets_from_parent_folder(filepaths, default_config, default_secrets) -> None:
    """Test loading secrets from parent folder."""
    config_file = YamlFile(
        path=filepaths["sub_folder"] / "sub.yaml",
        contents=default_config.contents,
    )
    loaded_file = load_config_file(config_file.path, [config_file, default_secrets])
    expected = {"api_password": "pwhttp"}

    assert expected == loaded_file["http"]


def test_secret_overrides_parent(filepaths, default_config, default_secrets) -> None:
    """Test loading current directory secret overrides the parent."""
    config_file = YamlFile(
        path=filepaths["sub_folder"] / "sub.yaml", contents=default_config.contents
    )
    sub_secrets = YamlFile(
        path=filepaths["sub_folder"] / yaml.SECRET_YAML, contents="http_pw: override"
    )

    loaded_file = load_config_file(
        config_file.path, [config_file, default_secrets, sub_secrets]
    )

    expected = {"api_password": "override"}
    assert loaded_file["http"] == expected


def test_secrets_from_unrelated_fails(filepaths, default_secrets) -> None:
    """Test loading secrets from unrelated folder fails."""
    config_file = YamlFile(
        path=filepaths["sub_folder"] / "sub.yaml",
        contents="http:\n  api_password: !secret test",
    )
    unrelated_secrets = YamlFile(
        path=filepaths["unrelated"] / yaml.SECRET_YAML, contents="test: failure"
    )
    with pytest.raises(HomeAssistantError, match="Secret test not defined"):
        load_config_file(
            config_file.path, [config_file, default_secrets, unrelated_secrets]
        )


def test_secrets_logger_removed(filepaths, default_secrets) -> None:
    """Ensure logger: debug was removed."""
    config_file = YamlFile(
        path=filepaths["config"] / YAML_CONFIG_FILE,
        contents="api_password: !secret logger",
    )
    with pytest.raises(HomeAssistantError, match="Secret logger not defined"):
        load_config_file(config_file.path, [config_file, default_secrets])


@patch("homeassistant.util.yaml.loader._LOGGER.error")
def test_bad_logger_value(mock_error, filepaths) -> None:
    """Ensure logger: debug was removed."""
    config_file = YamlFile(
        path=filepaths["config"] / YAML_CONFIG_FILE, contents="api_password: !secret pw"
    )
    secrets_file = YamlFile(
        path=filepaths["config"] / yaml.SECRET_YAML, contents="logger: info\npw: abc"
    )
    load_config_file(config_file.path, [config_file, secrets_file])
    assert mock_error.call_count == 1, "Expected an error about logger: value"


def test_secrets_are_not_dict(filepaths, default_config) -> None:
    """Did secrets handle non-dict file."""
    non_dict_secrets = YamlFile(
        path=filepaths["config"] / yaml.SECRET_YAML,
        contents="- http_pw: pwhttp\n  comp1_un: un1\n  comp1_pw: pw1\n",
    )
    with pytest.raises(HomeAssistantError, match="Secrets is not a dictionary"):
        load_config_file(default_config.path, [default_config, non_dict_secrets])
