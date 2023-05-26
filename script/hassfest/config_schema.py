"""Generate config flow file."""
from __future__ import annotations

import ast

from .model import Config, Integration


def _has_assignment(module: ast.Module, name: str) -> bool:
    """Test if the module assigns to a name."""
    for item in module.body:
        if type(item) not in (ast.Assign, ast.AnnAssign, ast.AugAssign):
            continue
        if type(item) == ast.Assign:
            for target in item.targets:
                if target.id == name:
                    return True
            continue
        if item.target.id == name:
            return True
    return False


def _has_function(
    module: ast.Module, _type: ast.AsyncFunctionDef | ast.FunctionDef, name: str
) -> bool:
    """Test if the module defines a function."""
    for item in module.body:
        if type(item) == _type and item.name == name:
            return True
    return False


def _has_import(module: ast.Module, name: str) -> bool:
    """Test if the module imports to a name."""
    for item in module.body:
        if type(item) not in (ast.Import, ast.ImportFrom):
            continue
        for alias in item.names:
            if alias.asname == name or (alias.asname is None and alias.name == name):
                return True
    return False


def _validate_integration(config: Config, integration: Integration) -> None:
    """Validate integration has has a configuration schema."""
    init_file = integration.path / "__init__.py"

    if not init_file.is_file():
        # Virtual integrations don't have any implementation
        return

    init = ast.parse(init_file.read_text())

    # No YAML Support
    if not _has_function(
        init, ast.AsyncFunctionDef, "async_setup"
    ) and not _has_function(init, ast.FunctionDef, "setup"):
        return

    # No schema
    if not (
        _has_assignment(init, "CONFIG_SCHEMA")
        or _has_assignment(init, "PLATFORM_SCHEMA")
        or _has_assignment(init, "PLATFORM_SCHEMA_BASE")
        or _has_import(init, "CONFIG_SCHEMA")
        or _has_import(init, "PLATFORM_SCHEMA")
        or _has_import(init, "PLATFORM_SCHEMA_BASE")
    ):
        return

    if config.specific_integrations:
        notice_method = integration.add_warning
    else:
        notice_method = integration.add_error

    notice_method(
        "config_schema",
        "Integrations which implement 'async_setup' or 'setup' must "
        "define either 'CONFIG_SCHEMA', 'PLATFORM_SCHEMA' or 'PLATFORM_SCHEMA_BASE'. "
        "If the integration has no configuration parameters or can not be setup from "
        "YAML, import one of CONFIG_SCHEMA_... from "
        "homeassistant.helpers.config_validation as CONFIG_SCHEMA",
    )


def validate(integrations: dict[str, Integration], config: Config) -> None:
    """Validate integrations have configuration schemas."""
    for domain in sorted(integrations):
        integration = integrations[domain]
        _validate_integration(config, integration)
