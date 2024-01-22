"""Tests for the Open Thread Border Router integration."""
BASE_URL = "http://core-silabs-multiprotocol:8081"
CONFIG_ENTRY_DATA_MULTIPAN = {"url": "http://core-silabs-multiprotocol:8081"}
CONFIG_ENTRY_DATA_THREAD = {"url": "/dev/ttyAMA1"}

DATASET_CH15 = bytes.fromhex(
    "0E080000000000010000000300000F35060004001FFFE00208F642646DA209B1D00708FDF57B5A"
    "0FE2AAF60510DE98B5BA1A528FEE049D4B4B01835375030D4F70656E5468726561642048410102"
    "25A40410F5DD18371BFD29E1A601EF6FFAD94C030C0402A0F7F8"
)

DATASET_CH16 = bytes.fromhex(
    "0E080000000000010000000300001035060004001FFFE00208F642646DA209B1C00708FDF57B5A"
    "0FE2AAF60510DE98B5BA1A528FEE049D4B4B01835375030D4F70656E5468726561642048410102"
    "25A40410F5DD18371BFD29E1A601EF6FFAD94C030C0402A0F7F8"
)

DATASET_INSECURE_NW_KEY = bytes.fromhex(
    "0E080000000000010000000300000F35060004001FFFE0020811111111222222220708FDD24657"
    "0A336069051000112233445566778899AABBCCDDEEFF030E4F70656E54687265616444656D6F01"
    "0212340410445F2B5CA6F2A93A55CE570A70EFEECB0C0402A0F7F8"
)

DATASET_INSECURE_PASSPHRASE = bytes.fromhex(
    "0E080000000000010000000300000F35060004001FFFE0020811111111222222220708FDD24657"
    "0A336069051000112233445566778899AABBCCDDEEFA030E4F70656E54687265616444656D6F01"
    "0212340410445F2B5CA6F2A93A55CE570A70EFEECB0C0402A0F7F8"
)

TEST_BORDER_AGENT_ID = bytes.fromhex("230C6A1AC57F6F4BE262ACF32E5EF52C")


ROUTER_DISCOVERY_HASS = {
    "type_": "_meshcop._udp.local.",
    "name": "HomeAssistant OpenThreadBorderRouter #0BBF._meshcop._udp.local.",
    "addresses": [b"\xc0\xa8\x00s"],
    "port": 49153,
    "weight": 0,
    "priority": 0,
    "server": "core-silabs-multiprotocol.local.",
    "properties": {
        b"rv": b"1",
        b"id": b"#\x0cj\x1a\xc5\x7foK\xe2b\xac\xf3.^\xf5,",
        b"vn": b"HomeAssistant",
        b"mn": b"OpenThreadBorderRouter",
        b"nn": b"OpenThread HC",
        b"xp": b"\xe6\x0f\xc7\xc1\x86!,\xe5",
        b"tv": b"1.3.0",
        b"xa": b"\xae\xeb/YKW\x0b\xbf",
        b"sb": b"\x00\x00\x01\xb1",
        b"at": b"\x00\x00\x00\x00\x00\x01\x00\x00",
        b"pt": b"\x8f\x06Q~",
        b"sq": b"3",
        b"bb": b"\xf0\xbf",
        b"dn": b"DefaultDomain",
        b"omr": b"@\xfd \xbe\x89IZ\x00\x01",
    },
    "interface_index": None,
}
