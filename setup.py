#!/usr/bin/env python3
"""Home Assistant setup script."""
from datetime import datetime as dt

from setuptools import find_packages, setup

PROJECT_NAME = "Home Assistant"
PROJECT_LICENSE = "Apache License 2.0"
PROJECT_AUTHOR = "The Home Assistant Authors"
PROJECT_COPYRIGHT = f" 2013-{dt.now().year}, {PROJECT_AUTHOR}"

PACKAGES = find_packages(exclude=["tests", "tests.*"])

setup(
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=False,
    test_suite="tests",
    entry_points={"console_scripts": ["hass = homeassistant.__main__:main"]},
)
