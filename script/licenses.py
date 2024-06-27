"""Tool to check the licenses."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys

from awesomeversion import AwesomeVersion


@dataclass
class PackageDefinition:
    """Package definition."""

    license: str
    name: str
    version: AwesomeVersion

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> PackageDefinition:
        """Create a package definition from a dictionary."""
        return cls(
            license=data["License"],
            name=data["Name"],
            version=AwesomeVersion(data["Version"]),
        )


OSI_APPROVED_LICENSES = {
    "Academic Free License (AFL)",
    "Apache Software License",
    "Apple Public Source License",
    "Artistic License",
    "Attribution Assurance License",
    "BSD License",
    "Boost Software License 1.0 (BSL-1.0)",
    "CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)",
    "Common Development and Distribution License 1.0 (CDDL-1.0)",
    "Common Public License",
    "Eclipse Public License 1.0 (EPL-1.0)",
    "Eclipse Public License 2.0 (EPL-2.0)",
    "Educational Community License, Version 2.0 (ECL-2.0)",
    "Eiffel Forum License",
    "European Union Public Licence 1.0 (EUPL 1.0)",
    "European Union Public Licence 1.1 (EUPL 1.1)",
    "European Union Public Licence 1.2 (EUPL 1.2)",
    "GNU Affero General Public License v3",
    "GNU Affero General Public License v3 or later (AGPLv3+)",
    "GNU Free Documentation License (FDL)",
    "GNU General Public License (GPL)",
    "GNU General Public License v2 (GPLv2)",
    "GNU General Public License v2 or later (GPLv2+)",
    "GNU General Public License v3 (GPLv3)",
    "GNU General Public License v3 or later (GPLv3+)",
    "GNU Lesser General Public License v2 (LGPLv2)",
    "GNU Lesser General Public License v2 or later (LGPLv2+)",
    "GNU Lesser General Public License v3 (LGPLv3)",
    "GNU Lesser General Public License v3 or later (LGPLv3+)",
    "GNU Library or Lesser General Public License (LGPL)",
    "Historical Permission Notice and Disclaimer (HPND)",
    "IBM Public License",
    "ISC License (ISCL)",
    "Intel Open Source License",
    "Jabber Open Source License",
    "MIT License",
    "MIT No Attribution License (MIT-0)",
    "MITRE Collaborative Virtual Workspace License (CVW)",
    "MirOS License (MirOS)",
    "Motosoto License",
    "Mozilla Public License 1.0 (MPL)",
    "Mozilla Public License 1.1 (MPL 1.1)",
    "Mozilla Public License 2.0 (MPL 2.0)",
    "Mulan Permissive Software License v2 (MulanPSL-2.0)",
    "NASA Open Source Agreement v1.3 (NASA-1.3)",
    "Nethack General Public License",
    "Nokia Open Source License",
    "Open Group Test Suite License",
    "Open Software License 3.0 (OSL-3.0)",
    "PostgreSQL License",
    "Python License (CNRI Python License)",
    "Python Software Foundation License",
    "Qt Public License (QPL)",
    "Ricoh Source Code Public License",
    "SIL Open Font License 1.1 (OFL-1.1)",
    "Sleepycat License",
    "Sun Industry Standards Source License (SISSL)",
    "Sun Public License",
    "The Unlicense (Unlicense)",
    "Universal Permissive License (UPL)",
    "University of Illinois/NCSA Open Source License",
    "Vovida Software License 1.0",
    "W3C License",
    "X.Net License",
    "Zero-Clause BSD (0BSD)",
    "Zope Public License",
    "zlib/libpng License",
    "Apache License",
    "MIT",
    "apache-2.0",
    "GPL-3.0",
    "GPLv3+",
    "MPL2",
    "MPL-2.0",
    "Apache 2",
    "LGPL v3",
    "BSD",
    "GNU-3.0",
    "GPLv3",
    "Eclipse Public License v2.0",
    "ISC",
    "GPL-2.0-only",
    "mit",
    "GNU General Public License v3",
    "Unlicense",
    "Apache-2",
    "GPLv2",
}

EXCEPTIONS = {
    "PyMicroBot",  # https://github.com/spycle/pyMicroBot/pull/3
    "PySwitchmate",  # https://github.com/Danielhiversen/pySwitchmate/pull/16
    "PyXiaomiGateway",  # https://github.com/Danielhiversen/PyXiaomiGateway/pull/201
    "aioautomower",  # https://github.com/Thomas55555/aioautomower/issues/356
    "aiocomelit",  # https://github.com/chemelli74/aiocomelit/pull/138
    "aioecowitt",  # https://github.com/home-assistant-libs/aioecowitt/pull/180
    "aiohttp-fast-url-dispatcher",  # https://github.com/bdraco/aiohttp-fast-url-dispatcher/pull/10
    "aiohttp-isal",  # https://github.com/bdraco/aiohttp-isal/pull/5
    "aiohttp-zlib-ng",  # https://github.com/bdraco/aiohttp-zlib-ng/pull/9
    "aioopenexchangerates",  # https://github.com/MartinHjelmare/aioopenexchangerates/pull/94
    "aiooui",  # https://github.com/Bluetooth-Devices/aiooui/pull/8
    "aioruuvigateway",  # https://github.com/akx/aioruuvigateway/pull/6
    "aiovodafone",  # https://github.com/chemelli74/aiovodafone/pull/131
    "aiowebostv",  # https://github.com/home-assistant-libs/aiowebostv/pull/327
    "aioymaps",  # https://github.com/devbis/aioymaps/pull/3
    "airthings-ble",  # https://github.com/Airthings/airthings-ble/pull/42
    "airtouch5py",  # https://github.com/danzel/airtouch5py/pull/3
    "amberelectric",  # https://github.com/madpilot/amberelectric.py/pull/11
    "apple_weatherkit",  # https://github.com/tjhorner/python-weatherkit/pull/3
    "apsystems-ez1",  # https://github.com/SonnenladenGmbH/APsystems-EZ1-API/pull/26
    "async-interrupt",  # https://github.com/bdraco/async_interrupt/pull/4
    "commentjson",  # https://github.com/vaidik/commentjson/pull/55
    "crownstone-cloud",  # https://github.com/crownstone/crownstone-lib-python-cloud/pull/5
    "crownstone-core",  # https://github.com/crownstone/crownstone-lib-python-core/pull/6
    "crownstone-sse",  # https://github.com/crownstone/crownstone-lib-python-sse/pull/2
    "crownstone-uart",  # https://github.com/crownstone/crownstone-lib-python-uart/pull/12
    "DTLSSocket",  # https://git.fslab.de/jkonra2m/tinydtls-cython/-/blob/master/LICENSE?ref_type=heads
    "eliqonline",  # https://github.com/molobrakos/eliqonline/pull/17
    "enocean",  # https://github.com/kipe/enocean/pull/142
    "gardena-bluetooth",  # https://github.com/elupus/gardena-bluetooth/pull/11
    "govee-local-api",  # https://github.com/Galorhallen/govee-local-api/pull/35
    "heatmiserV3",  # https://github.com/andylockran/heatmiserV3/pull/94
    "huum",  # https://github.com/frwickst/pyhuum/pull/8
    "imutils",  # https://github.com/PyImageSearch/imutils/pull/292
    "kiwiki_client",  # https://github.com/c7h/kiwiki_client/pull/6
    "krakenex",  # https://github.com/veox/python3-krakenex/pull/145
    "ld2410-ble",  # https://github.com/930913/ld2410-ble/pull/7
    "maxcube-api",  # https://github.com/uebelack/python-maxcube-api/pull/48
    "nessclient",  # https://github.com/nickw444/nessclient/pull/65
    "neurio",  # https://github.com/jordanh/neurio-python/pull/13
    "nextcloudmonitor",  # https://github.com/meichthys/nextcloud_monitor/pull/9
    "nsw-fuel-api-client",  # https://github.com/nickw444/nsw-fuel-api-client/pull/14
    "pigpio",  # https://github.com/joan2937/pigpio/pull/608
    "pyEmby",  # https://github.com/mezz64/pyEmby/pull/12
    "pyTibber",  # https://github.com/Danielhiversen/pyTibber/pull/294
    "pyaprilaire",  # https://github.com/chamberlain2007/pyaprilaire/pull/16
    "pybbox",  # https://github.com/HydrelioxGitHub/pybbox/pull/5
    "pyeconet",  # https://github.com/w1ll1am23/pyeconet/pull/41
    "pylutron-caseta",  # https://github.com/gurumitts/pylutron-caseta/pull/168
    "pynx584",  # https://github.com/kk7ds/pynx584/pull/87
    "pysabnzbd",  # https://github.com/jeradM/pysabnzbd/pull/6
    "pyswitchbee",  # https://github.com/jafar-atili/pySwitchbee/pull/5
    "pyvera",  # https://github.com/maximvelichko/pyvera/pull/164
    "pyxeoma",  # https://github.com/jeradM/pyxeoma/pull/11
    "repoze.lru",  #
    "ring-doorbell",  # https://github.com/tchellomello/python-ring-doorbell/pull/386
    "russound",  # https://github.com/laf/russound/pull/14   # codespell:ignore laf
    "ruuvitag-ble",  # https://github.com/Bluetooth-Devices/ruuvitag-ble/pull/10
    "sense-energy",  # https://github.com/scottbonline/sense/pull/67
    "sensirion-ble",  # https://github.com/akx/sensirion-ble/pull/9
    "sharp_aquos_rc",  # https://github.com/jmoore987/sharp_aquos_rc/pull/14
    "tapsaff",  # https://github.com/bazwilliams/python-taps-aff/pull/5
    "tellduslive",  # https://github.com/molobrakos/tellduslive/pull/24
    "tellsticknet",  # https://github.com/molobrakos/tellsticknet/pull/33
    "unifi-discovery",  # https://github.com/uilibs/unifi-discovery/pull/37
    "webrtc_noise_gain",  # https://github.com/rhasspy/webrtc-noise-gain/pull/24
    "xiaomi-ble",  # https://github.com/Bluetooth-Devices/xiaomi-ble/pull/81
    "zeversolar",  # https://github.com/kvanzuijlen/zeversolar/pull/46
}

TODO = {
    "BlinkStick": AwesomeVersion(
        "1.2.0"
    ),  # Proprietary license https://github.com/arvydas/blinkstick-python
    "PyMVGLive": AwesomeVersion(
        "1.1.4"
    ),  # No license and archived https://github.com/pc-coholic/PyMVGLive
    "aiocache": AwesomeVersion(
        "0.12.2"
    ),  # https://github.com/aio-libs/aiocache/blob/master/LICENSE all rights reserved?
    "aiohappyeyeballs": AwesomeVersion("2.3.2"),  # Need to dive into this
    "asterisk_mbox": AwesomeVersion("0.5.0"),  # I think we deprecated this
    "asyncarve": AwesomeVersion("0.0.9"),  # No public repository
    "asyncio": AwesomeVersion("3.4.3"),  # Python core
    "chacha20poly1305": AwesomeVersion("0.0.3"),  # I think LGPLv2+
    "chacha20poly1305-reuseable": AwesomeVersion("0.12.1"),  # has 2 licenses
    "concord232": AwesomeVersion(
        "0.15"
    ),  # No license https://github.com/JasonCarter80/concord232/issues/19
    "dovado": AwesomeVersion(
        "0.4.1"
    ),  # No license https://github.com/molobrakos/dovado/issues/4
    "genie_partner_sdk": AwesomeVersion("1.0.2"),  # pain
    "iso4217": AwesomeVersion("1.11.20220401"),  # Public domain?
    "mficlient": AwesomeVersion(
        "0.3.0"
    ),  # No license https://github.com/kk7ds/mficlient/issues/4
    "panasonic_viera": AwesomeVersion("0.3.6"),  # Has update available
    "pizzapi": AwesomeVersion("0.0.3"),  # Has update available
    "pubnub": AwesomeVersion(
        "8.0.0"
    ),  # Proprietary license https://github.com/pubnub/python/blob/master/LICENSE
    "pyElectra": AwesomeVersion(
        "1.2.3"
    ),  # No License https://github.com/jafar-atili/pyElectra/issues/3
    "pyflic": AwesomeVersion("2.0.3"),  # No OSI approved license CC0-1.0 Universal)
    "pymitv": AwesomeVersion("1.4.3"),  # Not sure why pip-licenses doesn't pick this up
    "refoss_ha": AwesomeVersion(
        "1.2.1"
    ),  # No License https://github.com/ashionky/refoss_ha/issues/4
    "ttls": AwesomeVersion(
        "1.5.1"
    ),  # Proprietary license https://github.com/jschlyter/ttls/issues/39
    "uvcclient": AwesomeVersion(
        "0.11.0"
    ),  # No License https://github.com/kk7ds/uvcclient/issues/7
    "vincenty": AwesomeVersion("0.1.4"),  # Public domain?
}


def main() -> int:
    """Run the main script."""
    raw_licenses = json.load(open("licenses.json"))
    package_definitions = [PackageDefinition.from_dict(data) for data in raw_licenses]
    exit_code = 0
    for package in package_definitions:
        previous_unapproved_version = TODO.get(package.name)
        approved = False
        for approved_license in OSI_APPROVED_LICENSES:
            if approved_license in package.license:
                approved = True
                break
        if previous_unapproved_version is not None:
            if previous_unapproved_version < package.version:
                if approved:
                    print(
                        f"Approved license detected for {package.name}@{package.version}: {package.license}"
                    )
                    print("Please remove the package from the TODO list.")
                    print("")
                else:
                    print(
                        f"We could not detect an OSI-approved license for {package.name}@{package.version}: {package.license}"
                    )
                    print("")
                exit_code = 1
        elif not approved and package.name not in EXCEPTIONS:
            print(
                f"We could not detect an OSI-approved license for {package.name}@{package.version}: {package.license}"
            )
            print("")
            exit_code = 1
        elif approved and package.name in EXCEPTIONS:
            print(
                f"Approved license detected for {package.name}@{package.version}: {package.license}"
            )
            print(f"Please remove the package from the EXCEPTIONS list: {package.name}")
            print("")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    if exit_code == 0:
        print("All licenses are approved!")
    sys.exit(exit_code)
